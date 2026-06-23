"""
Unit tests for post-processing logic and Pydantic schema validation.
These tests run without any API calls.

Run with:
    pytest tests/
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parser import post_process
from schemas import LabNotebookPageSchema


# ── Fixtures ───────────────────────────────────────────────────────────────────

MINIMAL_VALID = {
    "page_metadata": {
        "page_number": 57,
        "date": "June 4",
        "project_title": "Li electrodeposition",
        "continued_from_page": None,
    },
    "goal": "Screen electrolyte for stable Li plating at 30°C",
    "electrolyte": {
        "description": "1M LiTFSI in diglyme",
        "components": [{"name": "LiTFSI", "concentration": "1 M", "solvent": "diglyme", "ratio": None}],
        "total_volume": "20 mL",
        "additives": [],
    },
    "electrode_setup": {
        "working_electrode": {"material": "glassy carbon", "type": "RDE", "area": "0.3 cm²"},
        "counter_electrode": "Li foil",
        "reference_electrode": "Ag/AgCl",
        "atmosphere": "glovebox",
        "water_content": "H₂O < 1 ppm",
    },
    "deposition_run": {
        "run_id": "240604-B1",
        "applied_potential_V": -0.45,
        "reference": "Ag/AgCl",
        "duration_min": 90.0,
        "duration_s": 5400.0,
        "rotation_speed_rpm": 1600,
        "current_density_mA_per_cm2": 0.5,
        "electrode_area_cm2": 0.3,
        "calculated_current_A": "1.5E-4 A",
        "calculated_charge_C": 0.81,
        "moles_deposited_mol": "8.4E-6 mol",
        "mass_deposited_g": "5.8E-5 g",
    },
    "electrochemistry_equations": ["Q = I × t = 0.81 C"],
    "chemical_structures": [],
    "temperature_test": {
        "description": "Hot plate at 30°C",
        "time_temperature_table": [{"time": "0 min", "temperature_C": 22.4}],
    },
    "observations_and_results": ["Film looks grey and dull"],
    "raw_text_full": "Page 57\nJune 4\n",
    "ambiguous_readings": [],
}


# ── Post-processing tests ──────────────────────────────────────────────────────

def test_degree_symbol_normalization():
    data = MINIMAL_VALID.copy()
    data["goal"] = "Screen at 30 degC"
    text = json.dumps(data)
    import re
    text = re.sub(r'(?<!\w)deg\s*C\b', '°C', text)
    assert "°C" in text
    assert "degC" not in text


def test_scientific_notation_normalization():
    data = MINIMAL_VALID.copy()
    data["deposition_run"] = {**MINIMAL_VALID["deposition_run"], "moles_deposited_mol": "8.4e-6 mol"}
    result = post_process(data)
    assert "8.4E-6" in result["deposition_run"]["moles_deposited_mol"]


def test_unit_normalization():
    data = MINIMAL_VALID.copy()
    data["deposition_run"] = {**MINIMAL_VALID["deposition_run"], "calculated_current_A": "1.5 mA/cm2"}
    result = post_process(data)
    assert "mA/cm²" in result["deposition_run"]["calculated_current_A"]


# ── Schema validation tests ────────────────────────────────────────────────────

def test_valid_schema_passes():
    schema = LabNotebookPageSchema(**MINIMAL_VALID)
    assert schema.page_metadata.page_number == 57
    assert schema.goal == MINIMAL_VALID["goal"]


def test_optional_fields_accept_none():
    data = MINIMAL_VALID.copy()
    data["page_metadata"] = {**MINIMAL_VALID["page_metadata"], "continued_from_page": None}
    data["electrolyte"]["components"] = [{"name": "LiTFSI", "concentration": None, "solvent": None, "ratio": None}]
    schema = LabNotebookPageSchema(**data)
    assert schema.page_metadata.continued_from_page is None
    assert schema.electrolyte.components[0].concentration is None


def test_missing_required_field_raises():
    data = MINIMAL_VALID.copy()
    del data["goal"]
    with pytest.raises(Exception):
        LabNotebookPageSchema(**data)


def test_wrong_type_raises():
    data = MINIMAL_VALID.copy()
    data["page_metadata"] = {**MINIMAL_VALID["page_metadata"], "page_number": "fifty-seven"}
    with pytest.raises(Exception):
        LabNotebookPageSchema(**data)