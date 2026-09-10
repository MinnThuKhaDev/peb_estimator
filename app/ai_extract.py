"""
Optional server-side call to the Anthropic API to draft building parameters + engineering
notes from an uploaded PIF/PPD/EST file (xlsx, pdf, image, or text). Requires
ANTHROPIC_API_KEY in .env. The API key never touches the browser - this module runs
only on your own machine/server.

Output is always framed as a DRAFT for a licensed engineer to review - never a final
design.
"""
import base64
import json
import os
import re

import requests
from dotenv import load_dotenv

from . import file_parser

load_dotenv()

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"

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


def extract_with_ai(filename: str, content: bytes, note: str | None = None) -> dict:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise AIConfigError(
            "AI Assistant is not configured. Add ANTHROPIC_API_KEY to your .env file to "
            "enable it (see .env.example). Every other feature works fully offline without it."
        )

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    blocks = []

    if ext == "pdf":
        blocks.append({
            "type": "document",
            "source": {"type": "base64", "media_type": "application/pdf",
                       "data": base64.b64encode(content).decode()},
        })
    elif ext in ("png", "jpg", "jpeg"):
        mt = "image/png" if ext == "png" else "image/jpeg"
        blocks.append({
            "type": "image",
            "source": {"type": "base64", "media_type": mt, "data": base64.b64encode(content).decode()},
        })
    elif ext in ("xlsx", "xls"):
        text = file_parser.xlsx_to_text(content)
        blocks.append({"type": "text", "text": "Spreadsheet content:\n\n" + text[:15000]})
    else:
        text = content.decode(errors="ignore")
        blocks.append({"type": "text", "text": "File content:\n\n" + text[:15000]})

    prompt = INSTRUCTION + (f"\n\nAdditional context from the user: {note}" if note else "")
    blocks.append({"type": "text", "text": prompt})

    resp = requests.post(
        API_URL,
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": MODEL, "max_tokens": 1500, "messages": [{"role": "user", "content": blocks}]},
        timeout=90,
    )
    resp.raise_for_status()
    data = resp.json()
    text_out = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")

    fields, notes = None, text_out
    m = re.search(r"JSON:\s*(\{.*?\})\s*(.*)", text_out, re.S)
    if m:
        try:
            fields = json.loads(m.group(1))
        except Exception:
            fields = None
        notes = m.group(2).strip()

    return {"fields": fields, "notes": notes, "raw": text_out}
