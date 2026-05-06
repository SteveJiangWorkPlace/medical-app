import { FormEvent, useEffect, useRef, useState } from "react";
import { Database, Loader2, RotateCcw, Search, Send, Sparkles } from "lucide-react";

type QueryPlan = {
  intent: string;
  dataset: string;
  metric: string | null;
  aggregation: string | null;
  group_by: string[];
  filters: Array<{ field: string; operator: string; value: string | number }>;
  order_by: string | null;
  order: string;
  limit: number;
  clarification_question: string | null;
  assumptions: string[];
};

type QueryExecutionResult = {
  columns: string[];
  rows: Array<Record<string, unknown>>;
  total: number;
};

type FreeformAnswer = {
  question: string;
  session_id: string;
  answer: string;
  query_plan: QueryPlan;
  result: QueryExecutionResult;
  assumptions: string[];
  sources: string[];
  confidence: string;
};

type RAGAnswer = {
  question: string;
  session_id: string;
  answer: string;
  citations: Array<{
    document_id: number;
    chunk_id: number;
    title: string | null;
    snippet: string;
  }>;
  confidence: string;
};

type PriceCatalogSummary = {
  total: number;
  project_count: number;
  procurement_unit_count: number;
  applicant_enterprise_count: number;
  manufacturer_count: number;
  medical_insurance_code_count: number;
  document_count: number;
  industry_report_count: number;
  company_report_count: number;
  interview_record_count: number;
  news_report_count: number;
  min_price: number | null;
  max_price: number | null;
  avg_price: number | null;
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  result?: QueryExecutionResult;
  showTable?: boolean;
  streaming?: boolean;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

const EXAMPLES = [
  "哪家企业平均价格最高？",
  "哪家企业数量最多？",
  "各采购单元平均价格是多少？",
  "价格超过3000的产品有哪些？",
];

export function App() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState(() => createSessionId());
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState<PriceCatalogSummary | null>(null);
  const answerAreaRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    void loadSummary();
  }, []);

  useEffect(() => {
    scrollAnswersToBottom();
  }, [messages, error]);

  async function loadSummary() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/price-catalogs/summary`);
      if (!response.ok) return;
      setSummary((await response.json()) as PriceCatalogSummary);
    } catch {
      setSummary(null);
    }
  }

  function scrollAnswersToBottom() {
    window.requestAnimationFrame(() => {
      const element = answerAreaRef.current;
      if (element) {
        element.scrollTop = element.scrollHeight;
      }
    });
  }

  async function askQuestion(event?: FormEvent) {
    event?.preventDefault();
    const text = question.trim();
    if (!text) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
    };
    const assistantMessageId = crypto.randomUUID();

    setLoading(true);
    setError("");
    setQuestion("");
    setMessages((current) => [
      ...current,
      userMessage,
      { id: assistantMessageId, role: "assistant", content: "正在分析", streaming: true },
    ]);
    try {
      const useRag = shouldUseRag(text);
      const response = await fetch(`${API_BASE_URL}${useRag ? "/api/rag/ask" : "/api/qa/freeform"}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: text,
          session_id: sessionId,
          ...(useRag ? { medical_device_field: "吻合器", company_name: text.includes("派尔特") ? "派尔特" : undefined } : {}),
        }),
      });
      if (!response.ok) {
        throw new Error(`接口返回 ${response.status}`);
      }
      const payload = (await response.json()) as FreeformAnswer | RAGAnswer;
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantMessageId
            ? {
                ...message,
                result: "result" in payload ? payload.result : undefined,
                showTable: "result" in payload ? shouldShowTable(text, payload.result) : false,
              }
            : message,
        ),
      );
      streamAssistantMessage(assistantMessageId, payload.answer);
    } catch (caught) {
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantMessageId
            ? { ...message, content: "这次查询失败了，请稍后再试。", streaming: false }
            : message,
        ),
      );
      setError(caught instanceof Error ? caught.message : "请求失败");
    } finally {
      setLoading(false);
    }
  }

  function clearConversation() {
    setMessages([]);
    setError("");
    setLoading(false);
    setSessionId(createSessionId());
  }

  function streamAssistantMessage(messageId: string, fullText: string) {
    let index = 0;
    setMessages((current) =>
      current.map((message) => (message.id === messageId ? { ...message, content: "", streaming: true } : message)),
    );

    const timer = window.setInterval(() => {
      index += 1;
      setMessages((current) =>
        current.map((message) =>
          message.id === messageId
            ? {
                ...message,
                content: fullText.slice(0, index),
                streaming: index < fullText.length,
              }
            : message,
        ),
      );
      if (index >= fullText.length) {
        window.clearInterval(timer);
      }
    }, 18);
  }

  return (
    <main className="app-shell">
      <section className="workspace">
        <aside className="sidebar">
          <div className="brand">
            <Database size={22} />
            <div>
              <strong>腔镜吻合器集采数据集</strong>
            </div>
          </div>

          <div className="metric-grid">
            <Metric label="集采数据" value={formatMetric(summary?.total, "条")} />
            <Metric label="行业报告" value={formatMetric(summary?.industry_report_count, "篇")} />
            <Metric label="访谈记录" value={formatMetric(summary?.interview_record_count, "篇")} />
            <Metric label="新闻报告" value={formatMetric(summary?.news_report_count, "篇")} />
          </div>

          <div className="examples">
            <div className="section-title">
              <Sparkles size={16} />
              示例问题
            </div>
            {EXAMPLES.map((example) => (
              <button key={example} type="button" onClick={() => setQuestion(example)}>
                {example}
              </button>
            ))}
          </div>
        </aside>

        <section className="qa-panel">
          <div className="answer-area" ref={answerAreaRef}>
            {error && <div className="error-box">{error}</div>}

            {messages.length > 0 && (
              <div className="message-list">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`chat-message ${message.role === "user" ? "user-message" : "assistant-message"}`}
                  >
                    {message.role === "assistant" ? renderFormattedText(message.content) : message.content}
                    {message.streaming && <span className="typing-cursor" />}
                    {message.role === "assistant" && !message.streaming && message.showTable && message.result && (
                      <ResultTable result={message.result} />
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          <form className="ask-box" onSubmit={askQuestion}>
            <Search className="search-icon" size={20} />
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void askQuestion();
                }
              }}
              placeholder="输入你想查询的问题"
              rows={3}
            />
            <button type="submit" disabled={loading || !question.trim()}>
              {loading ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
              查询
            </button>
            <button className="clear-button" type="button" onClick={clearConversation} disabled={loading && messages.length === 0}>
              <RotateCcw size={17} />
              清空
            </button>
          </form>
        </section>
      </section>
    </main>
  );
}

function createSessionId() {
  return `web-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function formatMetric(value: number | undefined, unit = ""): string {
  return value === undefined ? "..." : `${value.toLocaleString("zh-CN")}${unit}`;
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ResultTable({ result }: { result: QueryExecutionResult }) {
  if (result.rows.length === 0 || result.columns.length === 0) return null;
  return (
    <div className="inline-result-table-wrap">
      <table className="inline-result-table">
        <thead>
          <tr>
            {result.columns.map((column) => (
              <th key={column}>{humanColumnName(column)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {result.rows.map((row, index) => (
            <tr key={index}>
              {result.columns.map((column) => (
                <td key={column}>{formatValue(row[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function shouldShowTable(question: string, result: QueryExecutionResult): boolean {
  if (result.rows.length <= 1) return false;
  if (question.match(/表格|列表|列出|列给我|所有|明细|有哪些/)) return true;
  return result.columns.length >= 2 && result.rows.length >= 3;
}

function shouldUseRag(question: string): boolean {
  return /访谈|报告|新闻|资讯|政策|接续|3\+N|全国集采|盘点|技术|专家|怎么看|观点|趋势|格局|原因|为什么|派尔特.*情况|Q3|季度|研发|渠道|出海/.test(question);
}

function humanColumnName(column: string): string {
  const names: Record<string, string> = {
    project_name: "项目",
    medical_device_field: "领域",
    procurement_unit: "采购单元",
    applicant_enterprise: "申报企业",
    manufacturer: "生产企业",
    component_name: "部件名称",
    model: "型号",
    medical_insurance_code: "医保编码",
    linked_price: "联动价",
    price_unit: "单位",
    catalog_count: "条目数",
    avg_linked_price: "平均联动价",
    max_linked_price: "最高联动价",
    min_linked_price: "最低联动价",
  };
  return names[column] ?? column;
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
  return String(value);
}

function renderFormattedText(text: string) {
  const cleaned = text
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/^\s*[-*]\s+/gm, "")
    .replace(/`([^`]+)`/g, "$1");
  const parts = cleaned.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);

  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("*") && part.endsWith("*")) {
      return <em key={index}>{part.slice(1, -1)}</em>;
    }
    return <span key={index}>{part}</span>;
  });
}
