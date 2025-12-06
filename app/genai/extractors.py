# app/genai/extractors.py
from typing import Optional, Dict, Any
import fitz  # PyMuPDF
from io import BytesIO
from PIL import Image
import pytesseract
import re

from .client import get_llm
from langchain_core.messages import SystemMessage, HumanMessage


def _extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    """
    Try to extract text with PyMuPDF (works for text PDFs).
    If result is small/empty, return empty string (so caller may fallback to OCR).
    """
    txt_chunks = []
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page in doc:
            text = page.get_text("text")
            if text:
                txt_chunks.append(text)
    except Exception:
        return ""

    full = "\n".join(txt_chunks).strip()
    return full


def _extract_images_from_pdf_bytes(file_bytes: bytes) -> list:
    """
    Extract images from PDF (as PIL.Image) for OCR fallback.
    """
    images = []
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page in doc:
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image = Image.open(BytesIO(image_bytes)).convert("RGB")
                images.append(image)
    except Exception:
        pass
    return images


def _ocr_images(images: list) -> str:
    """
    Run pytesseract OCR on a list of PIL images and return aggregated text.
    """
    texts = []
    for img in images:
        try:
            text = pytesseract.image_to_string(img)
            if text:
                texts.append(text)
        except Exception:
            continue
    return "\n".join(texts).strip()


def _clean_amount(amount_raw: str) -> Optional[float]:
    if amount_raw is None:
        return None
    s = str(amount_raw)
    # remove currency symbols and commas
    s = re.sub(r"[^\d\.\-]", "", s)
    try:
        return float(s)
    except Exception:
        return None


def parse_invoice_with_llm(extracted_text: str) -> Optional[Dict[str, Any]]:
    """
    Call Groq LLM (via LangChain ChatGroq) to extract structured fields from a blob of invoice text.
    Returns a dict with keys:
      - gstin (string or null)
      - pan (string or null)
      - vendor_name (string or null)
      - invoice_number (string or null)
      - invoice_date (YYYY-MM-DD or null)
      - amount (float or null)
      - currency (optional)
      - raw_text (original)
    If LLM not configured, return None.
    """
    llm = get_llm()
    if llm is None:
        return None

    # System prompt: instruct to output only JSON with specific keys
    system_prompt = (
        "You are an extraction assistant. Given a blob of text from an invoice, "
        "extract the following fields and return a JSON object EXACTLY with these keys: "
        "gstin, pan, vendor_name, invoice_number, invoice_date, amount, currency, raw_text. "
        "If a field is not found, use null. Date must be in YYYY-MM-DD when possible. "
        "Amount should be a numeric value (no commas). Output ONLY the JSON, nothing else."
    )

    user_prompt = (
        "Invoice text:\n\n"
        f"{extracted_text}\n\n"
        "Return the JSON now."
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    response = llm.invoke(messages)
    text = response.content.strip()

    # Attempt to parse JSON from the model output
    import json
    try:
        # Some models sometimes wrap JSON in markdown; try to extract the first {...}
        json_start = text.find("{")
        json_end = text.rfind("}") + 1
        if json_start == -1 or json_end == -1:
            data = json.loads(text)
        else:
            json_blob = text[json_start:json_end]
            data = json.loads(json_blob)
    except Exception:
        # Failed to parse LLM output
        return None

    # Basic normalization
    if "amount" in data:
        amt = data.get("amount")
        try:
            data["amount"] = float(str(amt).replace(",", "").strip()) if amt is not None else None
        except Exception:
            data["amount"] = _clean_amount(amt)

    # ensure keys exist
    keys = ["gstin", "pan", "vendor_name", "invoice_number", "invoice_date", "amount", "currency", "raw_text"]
    for k in keys:
        if k not in data:
            data[k] = None

    return data


def extract_invoice_fields_from_pdf_bytes(file_bytes: bytes, ocr_if_empty: bool = True) -> Dict[str, Any]:
    """
    Full pipeline:
    1) try PyMuPDF text extraction
    2) if empty and ocr_if_empty True: extract images & run pytesseract
    3) pass text to LLM for JSON extraction
    Returns dict with fields or raises ValueError on failure (or returns partial dict).
    """
    text = _extract_text_from_pdf_bytes(file_bytes)
    used_ocr = False
    if not text and ocr_if_empty:
        images = _extract_images_from_pdf_bytes(file_bytes)
        if images:
            text = _ocr_images(images)
            used_ocr = True

    result = parse_invoice_with_llm(text if text else "")
    if result is None:
        # fall back to best-effort regex parsing for amount/invoice number as a last resort
        return {"gstin": None, "pan": None, "vendor_name": None, "invoice_number": None, "invoice_date": None, "amount": None, "currency": None, "raw_text": text, "ocr_used": used_ocr}

    result["raw_text"] = text
    result["ocr_used"] = used_ocr
    return result
