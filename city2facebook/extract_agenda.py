import fitz
import logging

logger = logging.getLogger("fbpost")


def extract_agenda_text(pdf_path: str, max_pages: int = 10) -> str:
    logger.debug(f"Extracting text from PDF: {pdf_path}")
    try:
        doc = fitz.open(pdf_path)
        pages = min(len(doc), max_pages)
        logger.debug(f"PDF has {len(doc)} pages, extracting up to {pages}")
        text_parts = []
        for i in range(pages):
            page = doc[i]
            text = page.get_text("text")
            text_parts.append(text)
        doc.close()
        result = "\n\n".join(text_parts).strip()
        logger.info(f"Extracted {len(result)} chars from {pages} PDF page(s)")
        return result
    except Exception as e:
        logger.error(f"Error extracting agenda PDF: {e}")
        return f"[Error extracting agenda PDF: {e}]"
