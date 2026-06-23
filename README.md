# Lab Notebook Parser

A domain-aware parser that extracts structured, machine-readable JSON from handwritten materials science lab notebook pages using Vision-Language Models (VLMs).

Built as a take-home assignment for LabAlly to digitize dense experimental records (Li electrodeposition, glyme electrolytes) by combining VLM vision capabilities with strict schema validation and scientific post-processing.

---

## Why Standard OCR Fails

Off-the-shelf OCR (Tesseract, Google Cloud Vision) is optimized for printed, flat text. Handwritten scientific notebooks break it in three specific ways:

**Glyph ambiguity** — a researcher's `1`, `l`, and `I` can be identical strokes; `z` written without a crossbar looks like `2`. Standard OCR misreads `n = Q / zF` as `n = Q / 2F`.

**Semantically load-bearing shorthand** — superscripts, subscripts, and symbols (`mA/cm²`, `2θ = 2.1°`, `ω = 1600 rpm`) carry critical scientific meaning. OCR strips formatting or outputs corrupt Unicode.

**Non-textual content** — hand-drawn skeletal chemical structures (crown ethers, salt anions) require organic chemistry domain knowledge to interpret, name, and convert to SMILES notation.

This parser uses a VLM backbone (`claude-sonnet-4-6` or `gemini-2.5-flash`) which reads handwriting in scientific context and identifies chemical structures visually — solving all three problems in a single pass.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 Input: Image file                        │
└──────────────────────────┬──────────────────────────────┘
                           │ base64 / raw bytes
                           ▼
┌─────────────────────────────────────────────────────────┐
│              Dynamic VLM Routing Layer                  │
│                                                         │
│  • Checks ANTHROPIC_API_KEY first, GEMINI_API_KEY next  │
│  • Exponential backoff retry (1s, 2s, 4s, 8s, 16s)     │
│  • Schema-enforced prompt — no open-ended summarization │
└──────────────────────────┬──────────────────────────────┘
                           │ raw JSON string
                           ▼
┌─────────────────────────────────────────────────────────┐
│                Post-Processing Layer                    │
│                                                         │
│  • Normalize units: cm2 → cm², degC → °C               │
│  • Standardize sci notation: 1.5e-4 → 1.5E-4           │
│  • Strip markdown fences if model wraps output          │
│  • JSON recovery fallback on partial parse failures     │
└──────────────────────────┬──────────────────────────────┘
                           │ normalized dict
                           ▼
┌─────────────────────────────────────────────────────────┐
│              Pydantic Validation Layer                  │
│                                                         │
│  • Strict type enforcement via LabNotebookPageSchema    │
│  • Optional fields marked explicitly (no silent nulls)  │
└──────────────────────────┬──────────────────────────────┘
                           │ validated dict
                           ▼
┌─────────────────────────────────────────────────────────┐
│              Output: Structured JSON                    │
└─────────────────────────────────────────────────────────┘
```

### Key design decisions

**Single-pass extraction with schema-first prompting** — rather than asking the model to "summarize the experiment," the prompt supplies the exact JSON schema. This constrains the output space, reduces hallucination, and makes parsing deterministic.

**SMILES generation with null fallback** — hand-drawn structures are identified visually and converted to SMILES. If a structure is ambiguous, the model returns `null` for SMILES and provides a text description instead. This protects downstream pipelines from garbage data.

**Ambiguity flagging** — unclear handwritten values are explicitly flagged in `ambiguous_readings` rather than silently guessed. This is critical in a lab context where wrong data is worse than missing data.

**Provider priority** — `ANTHROPIC_API_KEY` is checked first. If absent, `GEMINI_API_KEY` is used. Both providers share the same prompt and output schema so results are consistent regardless of backend.

---

## Repository Structure

```
labnotebook-parser/
├── src/
│   ├── __init__.py
│   ├── parser.py       # Core orchestration, VLM routing, retry logic, post-processing
│   ├── prompts.py      # System prompt and extraction prompt
│   └── schemas.py      # Pydantic models for type-safe output validation
├── data/
│   └── Example_Lab_Notebook_Page.jpg
├── tests/
│   ├── __init__.py
│   └── test_parser.py
├── output/             # JSON outputs written here (git-ignored)
├── demo.py             # CLI entry point
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Setup

```bash
git clone https://github.com/VAP2999/labnotebook-parser.git
cd labnotebook-parser

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

---

## Usage

### Run with Anthropic Claude (recommended)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python demo.py
```

### Run with Google Gemini

```bash
export GEMINI_API_KEY="your-gemini-key"
python demo.py
```

### Custom image or output path

```bash
python demo.py --image path/to/notebook_page.jpg --output path/to/result.json
```

### Use as a library

```python
from src.parser import extract_from_image

result = extract_from_image("data/Example_Lab_Notebook_Page.jpg")

print(result["goal"])
print(result["deposition_run"]["calculated_charge_C"])
print(result["chemical_structures"][0]["smiles"])
print(result["raw_text_full"])
```

---

## Output Schema

| Field | Type | Description |
|---|---|---|
| `page_metadata` | object | Page number, date, project title, continuation link |
| `goal` | string | Stated experimental goal |
| `electrolyte` | object | Components, concentrations, volumes, additives |
| `electrode_setup` | object | WE/CE/RE materials, area, atmosphere |
| `deposition_run` | object | Applied potential, current, charge, moles, mass |
| `electrochemistry_equations` | list[str] | All equations written on the page |
| `chemical_structures` | list[dict] | Name, type, SMILES, description per drawn structure |
| `temperature_test` | object | Time → temperature table |
| `observations_and_results` | list[str] | Film observations, XRD peaks, notes |
| `raw_text_full` | string | Complete verbatim transcription, line by line |
| `ambiguous_readings` | list[dict] | Flagged uncertain readings with best-guess interpretations |

---

## Cost Reference (Anthropic claude-sonnet-4-6)

| | Tokens | Rate | Cost |
|---|---|---|---|
| Input (image + prompt) | ~1,850 | $3.00 / 1M | ~$0.006 |
| Output (structured JSON) | ~1,650 | $15.00 / 1M | ~$0.025 |
| **Total per page** | | | **~$0.03** |

At this rate, processing 1,000 notebook pages costs approximately $30.

---

## Extending This

**RDKit validation** — pipe generated SMILES through RDKit to validate valence and render clean 2D structures.

**Confidence scoring** — add a second API pass prompting the model to score its own confidence (0–1) per field, flagging values below a threshold for human review.

**Database adapter** — the Pydantic model dump maps directly to a relational schema (runs table, reagents table, observations table).

**Batch processing** — wrap `extract_from_image()` in a loop over a directory to process full notebook archives.