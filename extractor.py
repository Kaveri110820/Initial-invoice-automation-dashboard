import re

import pymupdf


def extract_text_from_pdf(pdf_path: str) -> str:
    doc = None
    try:
        doc = pymupdf.open(pdf_path)
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        return "\n".join(text_parts)
    except Exception as e:
        return f"[Error reading PDF: {e}]"
    finally:
        if doc:
            doc.close()


def _find(pattern: str, text: str, group: int = 1) -> str:
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(group).strip() if match else ""


def _find_amount(pattern: str, text: str) -> float:
    raw = _find(pattern, text)
    raw = re.sub(r"[^\d.,]", "", raw)
    raw = raw.replace(",", "")
    try:
        return float(raw)
    except ValueError:
        return 0.0


def extract_invoice_data(text: str) -> dict:
    return {
        "invoice_number": _find(
            r"(?:invoice|inv)\s*(?:number|no|#|num)?[ \t:\-#]+([A-Z0-9][\w\-/]+)", text
        ),
        "invoice_date": _find(
            r"(?:invoice\s*date|date\s*of\s*invoice|date)[ \t:\-]*"
            r"(\d{1,2}[\s/\-\.]\w+[\s/\-\.]\d{2,4}|\d{4}[\s/\-\.]\d{1,2}[\s/\-\.]\d{1,2})",
            text,
        ),
        "due_date": _find(
            r"(?:due\s*date|payment\s*due|pay\s*by)[ \t:\-]*"
            r"(\d{1,2}[\s/\-\.]\w+[\s/\-\.]\d{2,4}|\d{4}[\s/\-\.]\d{1,2}[\s/\-\.]\d{1,2})",
            text,
        ),
        "vendor_name": _find(
            r"(?:from|vendor|supplier|bill\s*from|sold\s*by)[ \t:\-]*([A-Z][^\n]{2,60})",
            text,
        ),
        "subtotal": _find_amount(
            r"(?:sub\s*total|subtotal|net\s*amount)[ \t:\-]*[\$€£]?\s*([\d,]+\.?\d*)",
            text,
        ),
        "tax": _find_amount(
            r"(?:tax|vat|gst|hst)[ \t:\-]*[\$€£]?\s*([\d,]+\.?\d*)",
            text,
        ),
        "total_amount": _find_amount(
            r"(?<!sub\s)(?:total\s*(?:amount)?|amount\s*due|balance\s*due|grand\s*total)"
            r"[ \t:\-]*[\$€£]?\s*([\d,]+\.?\d*)",
            text,
        ),
    }
