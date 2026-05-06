# RAG Metadata Taxonomy

Use these fields for unstructured RAG sources so retrieval can distinguish industry-level material, brand-level material, news, official websites, expert interviews, and other evidence types.

## Core Fields

| Field | Purpose | Typical Values |
| --- | --- | --- |
| `source_category` | What kind of source this is | `industry_report`, `company_report`, `industry_news`, `company_website`, `expert_interview`, `policy_document`, `procurement_notice`, `academic_literature`, `financial_report`, `other` |
| `source_channel` | Where the material came from | `broker_research`, `consulting_report`, `news_media`, `company_official`, `government_platform`, `academic_database`, `conference`, `internal_note`, `manual_upload`, `other` |
| `publisher` | Publishing organization or platform | `派尔特官网`, `证券公司研究所`, `国家医保局` |
| `publisher_type` | Publisher class | `brand`, `industry_org`, `media`, `government`, `broker`, `consulting`, `academic`, `internal`, `other` |
| `author` | Author, analyst, or interviewer | Free text |
| `source_url` | Original URL when available | URL string |
| `content_scope` | What the content mainly covers | `industry`, `brand`, `product`, `policy`, `market_access`, `pricing`, `technology`, `channel`, `other` |
| `research_type` | Evidence generation method | `primary`, `secondary`, `mixed`, `official_disclosure`, `news`, `opinion`, `other` |
| `evidence_level` | Evidence strength | `official`, `high`, `medium`, `low`, `unknown` |
| `geographic_scope` | Region covered | `China`, `global`, `京津冀`, `US`, `EU` |

## Examples

Industry report:

```json
{
  "source_category": "industry_report",
  "source_channel": "broker_research",
  "publisher": "某证券研究所",
  "publisher_type": "broker",
  "content_scope": "industry",
  "research_type": "secondary",
  "evidence_level": "high",
  "medical_device_field": "吻合器"
}
```

Brand expert interview:

```json
{
  "source_category": "expert_interview",
  "source_channel": "internal_note",
  "publisher_type": "internal",
  "content_scope": "brand",
  "research_type": "primary",
  "evidence_level": "medium",
  "company_name": "派尔特",
  "medical_device_field": "吻合器"
}
```

Company website:

```json
{
  "source_category": "company_website",
  "source_channel": "company_official",
  "publisher": "派尔特",
  "publisher_type": "brand",
  "content_scope": "brand",
  "research_type": "official_disclosure",
  "evidence_level": "official",
  "company_name": "派尔特"
}
```

Industry news:

```json
{
  "source_category": "industry_news",
  "source_channel": "news_media",
  "publisher_type": "media",
  "content_scope": "industry",
  "research_type": "news",
  "evidence_level": "medium"
}
```
