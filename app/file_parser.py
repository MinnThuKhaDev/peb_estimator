"""
Offline file parsing: extracts raw text from xlsx / PDF / text files, and makes a
best-effort, purely regex-based guess at a few key building parameters. No AI/network
call is used here - this always works offline. It is intentionally conservative: it
only fills a value when it's fairly confident, and everything must be reviewed by hand.
"""
import io
import re

import openpyxl
import pdfplumber


def xlsx_to_text(content: bytes) -> str:
    wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    out = []
    for ws in wb.worksheets:
        out.append(f"--- Sheet: {ws.title} ---")
        for row in ws.iter_rows(values_only=True):
            cells = [str(c) for c in row if c is not None and str(c).strip() != ""]
            if cells:
                out.append(", ".join(cells))
    return "\n".join(out)


def pdf_to_text(content: bytes) -> str:
    chunks = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            chunks.append(page.extract_text() or "")
    return "\n".join(chunks)


def extract_text(filename: str, content: bytes) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "pdf":
        return pdf_to_text(content)
    if ext in ("xlsx", "xls"):
        return xlsx_to_text(content)
    if ext in ("png", "jpg", "jpeg"):
        return (
            "[Image file - offline text extraction isn't available without OCR. "
            "Use the AI Assistant tab (needs an API key) to read images, or install "
            "pytesseract locally for offline OCR.]"
        )
    if ext == "dwg":
        return (
            "[DWG file received and stored for reference/download. DWG is Autodesk's "
            "closed binary CAD format, so no text or geometry can be extracted from it "
            "here (offline or by the AI assistant). If you need parameters pulled from "
            "the drawing, export a DXF (open text-based CAD format), PDF, or image "
            "instead and upload that.]"
        )
    try:
        return content.decode(errors="ignore")
    except Exception:
        return ""


_LABELS = {
    "width": r"width\D{0,15}([\d]+\.?[\d]*)",
    "length": r"length\D{0,15}([\d]+\.?[\d]*)",
    "eave_height": r"(?:e\.?h\.?\s*\(m\)|eave height)\D{0,15}([\d]+\.?[\d]*)",
    "wind_speed": r"wind speed\D{0,15}([\d]+\.?[\d]*)",
    "live_load": r"live load\D{0,15}([\d]+\.?[\d]*)",
}


def regex_extract(text: str) -> dict:
    text_low = text.lower()
    out = {}
    for key, pattern in _LABELS.items():
        m = re.search(pattern, text_low)
        if m:
            try:
                out[key] = float(m.group(1))
            except ValueError:
                pass

    m = re.search(r"seismic\D{0,10}(zone\s*\d+|[ivx]+)", text_low)
    if m:
        out["seismic_zone"] = m.group(1).strip()

    if "enclosure" in text_low or "enclosed" in text_low or "open" in text_low:
        if re.search(r"\bopen\b", text_low) and "enclosed" not in text_low:
            out["enclosure"] = "Open"
        elif "partially enclosed" in text_low:
            out["enclosure"] = "Partially Enclosed"
        elif "enclosed" in text_low:
            out["enclosure"] = "Enclosed"

    m = re.search(r"frame type\D{0,10}([a-z0-9]{2,6})", text_low)
    if m:
        out["frame_type"] = m.group(1).upper()

    return out
