import json
import os

SYSTEM_PROMPT = """\
You are an invoice data extraction assistant.
Given raw text from a PDF invoice, extract the following fields and return
ONLY a valid JSON object — no markdown, no explanation:

{
  "invoice_number": "string",
  "vendor_name": "string",
  "invoice_date": "string",
  "due_date": "string",
  "subtotal": 0.0,
  "tax": 0.0,
  "total_amount": 0.0,
  "currency": "USD"
}

Rules:
- Use empty string "" for text fields you cannot find.
- Use 0.0 for numeric fields you cannot find.
- Use "USD" as the default currency if not specified.
- Return ONLY the JSON object.
"""


def extract_with_ai(text: str) -> dict | None:
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        return None

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )

        raw = response.choices[0].message.content.strip()

        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]
        raw = raw.strip()

        data = json.loads(raw)

        # Ensure all expected keys exist with correct types
        return {
            "invoice_number": str(data.get("invoice_number", "")),
            "vendor_name": str(data.get("vendor_name", "")),
            "invoice_date": str(data.get("invoice_date", "")),
            "due_date": str(data.get("due_date", "")),
            "subtotal": float(data.get("subtotal", 0)),
            "tax": float(data.get("tax", 0)),
            "total_amount": float(data.get("total_amount", 0)),
            "currency": str(data.get("currency", "USD")),
        }

    except Exception:
        return None
