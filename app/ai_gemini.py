"""
AI assistant backed by Google Gemini (has a genuinely free API tier — get a key at
https://aistudio.google.com/app/apikey). Same job as ai_extract.py (Anthropic): read an
uploaded PIF/PPD/EST file and draft building parameters + engineering notes.

Set GEMINI_API_KEY in .env to enable this. If ANTHROPIC_API_KEY is also set, main.py
prefers Gemini (free) and falls back to Anthropic only if you set AI_PROVIDER=anthropic.

Output is always a DRAFT for a licensed engineer to review — never a final design.
"""
import base64
import json
import os
import re

import requests

from . import file_parser

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

INSTRUCTION = """You are drafting a PRELIMINARY, non-certified extraction from a pre-engineered
steel building document (PIF/PPD/EST). This will be reviewed and approved by a licensed
structural engineer before any use - you are only producing a draft starting point, never
a final design.

Task:
1. Extract these building parameters if present (infer conservatively if implied but not
explicit, and say so in the notes): width (m), length (m), eave_height (m), bay_count,
slope_rise, slope_run, wind_speed (km/h), live_load (kN/m2), seismic_zone, occupancy,
enclosure ("Open"/"Partially Enclosed"/"Enclosed"), frame_type, has_mezz (bool),
mezz_area (m2), has_crane (bool), crane_cap (tons), crane_len (m), has_canopy (bool),
canopy_area (m2).
2. Output ONE line starting exactly with "JSON:" followed by a compact JSON object with
those fields (use null for anything unknown - never guess wildly).
3. After that line, write a short "DRAFT ENGINEERING NOTES" section (5-10 bullet points):
frame type/members visible, any load table or reaction data present, anything unusual
that needs the engineer's attention, and anything you couldn't determine.
4. Never state or imply this extraction is approved, certified, or ready to build from -
always call it a draft for engineer review.
"""


class AIConfigError(Exception):
    pass


def _mime_for(ext: str) -> str | None:
    return {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
    }.get(ext)


def extract_with_ai(filename: str, content: bytes, note: str | None = None) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise AIConfigError(
            "AI Assistant is not configured. Add a free GEMINI_API_KEY to your .env file "
            "(get one at https://aistudio.google.com/app/apikey). Every other feature "
            "works fully offline without it."
        )

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    parts = []

    mime = _mime_for(ext)
    if mime:
        parts.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(content).decode()}})
    elif ext in ("xlsx", "xls"):
        text = file_parser.xlsx_to_text(content)
        parts.append({"text": "Spreadsheet content:\n\n" + text[:15000]})
    elif ext == "dwg":
        raise AIConfigError(
            "DWG is a closed binary CAD format and can't be read by the AI assistant. "
            "The file has been stored/attached for reference — please export a PDF or "
            "image of the drawing (or a DXF, which the file parser can read as text) for "
            "AI extraction."
        )
    else:
        text = content.decode(errors="ignore")
        parts.append({"text": "File content:\n\n" + text[:15000]})

    prompt = INSTRUCTION + (f"\n\nAdditional context from the user: {note}" if note else "")
    parts.append({"text": prompt})

    resp = requests.post(
        API_URL,
        params={"key": api_key},
        json={"contents": [{"parts": parts}]},
        timeout=90,
    )
    resp.raise_for_status()
    data = resp.json()
    try:
        text_out = "".join(
            p.get("text", "")
            for p in data["candidates"][0]["content"]["parts"]
        )
    except (KeyError, IndexError):
        text_out = json.dumps(data)

    fields, notes = None, text_out
    m = re.search(r"JSON:\s*(\{.*?\})\s*(.*)", text_out, re.S)
    if m:
        try:
            fields = json.loads(m.group(1))
        except Exception:
            fields = None
        notes = m.group(2).strip()

    return {"fields": fields, "notes": notes, "raw": text_out}
