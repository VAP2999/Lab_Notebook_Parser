"""
Lab Notebook Parser — Core Module

Extracts structured data from handwritten chemistry lab notebook pages
using a Vision-Language Model (VLM) with tiered extraction and post-processing.

Supports Anthropic Claude (claude-sonnet-4-6) or Google Gemini (gemini-2.5-flash)
depending on which API key is set in the environment. Includes exponential backoff
retry logic on transient API failures.
"""

import os
import base64
import json
import re
import sys
import time
from pathlib import Path

try:
    from prompts import SYSTEM_PROMPT, EXTRACTION_PROMPT
    from schemas import LabNotebookPageSchema
except ImportError:
    try:
        from src.prompts import SYSTEM_PROMPT, EXTRACTION_PROMPT
        from src.schemas import LabNotebookPageSchema
    except ImportError:
        sys.path.append(str(Path(__file__).parent))
        from prompts import SYSTEM_PROMPT, EXTRACTION_PROMPT
        from schemas import LabNotebookPageSchema


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_image_as_base64(image_path: str) -> tuple[str, str]:
    """Load an image file and return (base64_data, media_type)."""
    path = Path(image_path)
    media_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    media_type = media_type_map.get(path.suffix.lower(), "image/jpeg")
    with open(path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return data, media_type


def post_process(raw: dict) -> dict:
    """
    Normalize units, fix common OCR artifacts, and standardize scientific notation.
    Validates the result against the Pydantic schema before returning.
    """
    text = json.dumps(raw)

    # Normalize degree symbols
    text = re.sub(r'(?<!\w)deg\s*C\b', '°C', text)
    text = re.sub(r'(?<!\w)degC\b', '°C', text)

    # Standardize scientific notation (e.g. 1.5e-4 → 1.5E-4)
    text = re.sub(r'(\d+\.\d+)[eE](-?\d+)', lambda m: f"{m.group(1)}E{m.group(2)}", text)

    # Normalize unit abbreviations
    unit_replacements = {
        r'\bmA/cm2\b': 'mA/cm²',
        r'\bcm2\b': 'cm²',
        r'\bv/v\b': 'v/v',
    }
    for pattern, replacement in unit_replacements.items():
        text = re.sub(pattern, replacement, text)

    processed_dict = json.loads(text)
    validated = LabNotebookPageSchema(**processed_dict)
    return validated.model_dump()


# ── Retry Logic ────────────────────────────────────────────────────────────────

def retry_with_backoff(api_call_func):
    """
    Decorator that retries an API call up to 5 times with exponential backoff
    (delays: 1s, 2s, 4s, 8s, 16s). Raises RuntimeError after all attempts fail.
    """
    def wrapper(*args, **kwargs):
        delays = [1, 2, 4, 8, 16]
        for attempt, delay in enumerate(delays):
            try:
                return api_call_func(*args, **kwargs)
            except Exception as e:
                if attempt == len(delays) - 1:
                    raise RuntimeError(
                        f"API call failed after {len(delays)} attempts. "
                        f"Original error: {e}"
                    ) from e
                time.sleep(delay)
    return wrapper


# ── Provider Callers ───────────────────────────────────────────────────────────

@retry_with_backoff
def extract_with_claude(image_path: str, api_key: str) -> tuple[str, dict]:
    """Send image to Anthropic Claude (claude-sonnet-4-6) and return raw JSON text + metadata."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    image_data, media_type = load_image_as_base64(image_path)

    print("[2/4] Sending to Claude Sonnet 4.6 Vision API...")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": EXTRACTION_PROMPT,
                    },
                ],
            }
        ],
    )

    raw_text = response.content[0].text.strip()
    metadata = {
        "model": "claude-sonnet-4-6",
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
    return raw_text, metadata


@retry_with_backoff
def extract_with_gemini(image_path: str, api_key: str) -> tuple[str, dict]:
    """Send image to Google Gemini (gemini-2.5-flash) and return raw JSON text + metadata."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    path = Path(image_path)
    image_bytes = path.read_bytes()
    mime_type = "image/jpeg" if path.suffix.lower() in [".jpg", ".jpeg"] else "image/png"

    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        response_mime_type="application/json",
        temperature=0.1,
    )

    print("[2/4] Sending to Gemini 2.5 Flash Vision API...")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[image_part, EXTRACTION_PROMPT],
        config=config,
    )

    raw_text = response.text.strip()
    metadata = {
        "model": "gemini-2.5-flash",
        "input_tokens": getattr(response.usage_metadata, "prompt_token_count", 0),
        "output_tokens": getattr(response.usage_metadata, "candidates_token_count", 0),
    }
    return raw_text, metadata


# ── Orchestration ──────────────────────────────────────────────────────────────

def extract_from_image(image_path: str, api_key: str | None = None) -> dict:
    """
    Main extraction entry point.

    Detects which API key is available (ANTHROPIC_API_KEY takes priority over
    GEMINI_API_KEY) and routes accordingly. Raises ValueError if neither is set.

    Args:
        image_path: Path to the lab notebook image file.
        api_key:    Optional Anthropic API key override (falls back to env var).

    Returns:
        Validated structured dict matching LabNotebookPageSchema.
    """
    anthropic_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")

    print(f"[1/4] Loading image: {image_path}")

    if anthropic_key:
        raw_text, metadata = extract_with_claude(image_path, anthropic_key)
    elif gemini_key:
        raw_text, metadata = extract_with_gemini(image_path, gemini_key)
    else:
        raise ValueError(
            "No API key found. Set ANTHROPIC_API_KEY or GEMINI_API_KEY "
            "in your environment before running."
        )

    print("[3/4] Parsing response...")
    raw_text = re.sub(r'^```(?:json)?\s*', '', raw_text)
    raw_text = re.sub(r'\s*```$', '', raw_text)

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as e:
        print(f"  WARNING: JSON parse failed, attempting recovery... ({e})")
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
        else:
            raise ValueError("Could not extract valid JSON from model response.") from e

    print("[4/4] Post-processing and validating...")
    result = post_process(parsed)
    result["_extraction_metadata"] = {
        **metadata,
        "image_path": str(image_path),
    }

    return result


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python parser.py <image_path> [output_json_path]")
        sys.exit(1)

    image_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "output/parsed_notebook.json"

    result = extract_from_image(image_path)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Saved structured output → {output_path}")
    print(f"  Tokens used: {result['_extraction_metadata']['input_tokens']} in / "
          f"{result['_extraction_metadata']['output_tokens']} out")


if __name__ == "__main__":
    main()