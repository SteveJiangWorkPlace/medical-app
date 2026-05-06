import fitz


def extract_pdf_text(path: str) -> str:
    parts: list[str] = []
    with fitz.open(path) as document:
        for page_index, page in enumerate(document, start=1):
            text = page.get_text("text").strip()
            if text:
                parts.append(f"[Page {page_index}]\n{text}")
    return "\n\n".join(parts)
