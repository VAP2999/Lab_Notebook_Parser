"""
demo.py — Run the lab notebook parser and display a formatted extraction summary.

Usage:
    python demo.py                              # uses ANTHROPIC_API_KEY env var
    python demo.py --image path/to/image.jpg    # custom image path
    python demo.py --output path/to/out.json    # custom output path
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from parser import extract_from_image


# ── Display ────────────────────────────────────────────────────────────────────

def print_summary(data: dict) -> None:
    """Print a human-readable tiered summary of the extracted notebook data."""
    sep = "─" * 60

    print(f"\n{'═' * 60}")
    print("  LAB NOTEBOOK PARSER — EXTRACTION SUMMARY")
    print(f"{'═' * 60}\n")

    meta = data["page_metadata"]
    print(f"📄 Page {meta['page_number']}  |  {meta['date']}  |  continued from p.{meta.get('continued_from_page', '?')}")
    print(f"   Project: {meta['project_title']}\n")

    # Tier 1 — Plain Text
    print(sep)
    print("TIER 1 — PLAIN TEXT (sample)")
    print(sep)
    lines = data["raw_text_full"].strip().split("\n")
    for line in lines[:8]:
        print(f"  {line}")
    print(f"  ... ({len(lines)} lines total)\n")

    # Tier 2 — Special Symbols & Units
    print(sep)
    print("TIER 2 — SPECIAL SYMBOLS & UNITS")
    print(sep)
    run = data["deposition_run"]
    print(f"  Applied potential:    {run['applied_potential_V']} V vs {run['reference']}")
    print(f"  Current density:      {run['current_density_mA_per_cm2']} mA/cm²")
    print(f"  Electrode area:       {run['electrode_area_cm2']} cm²")
    print(f"  Duration:             {run['duration_min']} min = {run['duration_s']} s")
    print(f"  Rotation speed (ω):   {run['rotation_speed_rpm']} rpm")
    print(f"  Charge (Q):           {run['calculated_charge_C']} C")
    print(f"  Moles deposited:      {run['moles_deposited_mol']}")
    print(f"  Mass deposited:       {run['mass_deposited_g']}")
    print()
    print("  Temperature ramp:")
    for row in data["temperature_test"]["time_temperature_table"]:
        print(f"    {row['time']:>12}  →  {row['temperature_C']}°C")
    print()

    # Tier 3 — Chemistry
    print(sep)
    print("TIER 3 — CHEMISTRY")
    print(sep)
    elec = data["electrolyte"]
    print(f"  Electrolyte: {elec['description']}")
    for comp in elec["components"]:
        print(f"    • {comp['name']}  [{comp.get('concentration', '—')}]")
    for add in elec["additives"]:
        print(f"    + Additive: {add['name']} ({add['amount']})  — {add['preparation']}")
    print()
    print("  Electrodes:")
    es = data["electrode_setup"]
    print(f"    WE:  {es['working_electrode']['material']} {es['working_electrode']['type']}  ({es['working_electrode']['area']})")
    print(f"    CE:  {es['counter_electrode']}")
    print(f"    RE:  {es['reference_electrode']}")
    print(f"    Atm: {es.get('atmosphere', '—')},  {es.get('water_content', '—')}")
    print()
    print("  Reactions / equations:")
    for eq in data["electrochemistry_equations"]:
        print(f"    {eq}")
    print()
    print("  Chemical structures identified:")
    for struct in data["chemical_structures"]:
        smiles = struct.get("smiles") or "—"
        print(f"    [{struct['type']}] {struct['name']}")
        print(f"      SMILES: {smiles}")
        print(f"      Role:   {struct['role_in_experiment']}")
    print()

    # Tier 4 — Experiment Interpretation
    print(sep)
    print("TIER 4 — EXPERIMENT INTERPRETATION")
    print(sep)
    print(f"  Goal:    {data['goal']}")
    print(f"  Run ID:  {data['deposition_run']['run_id']}")
    print()
    print("  Observations:")
    for obs in data["observations_and_results"]:
        print(f"    • {obs}")
    print()

    # Ambiguous readings
    if data.get("ambiguous_readings"):
        print(sep)
        print("⚠  AMBIGUOUS READINGS (flagged)")
        print(sep)
        for amb in data["ambiguous_readings"]:
            print(f"  [{amb['location']}]")
            print(f"    Raw:  \"{amb['raw_text']}\"")
            print(f"    → {amb['interpretation']}")
        print()

    # Extraction metadata
    if "_extraction_metadata" in data:
        m = data["_extraction_metadata"]
        print(sep)
        print(f"  Model: {m['model']}  |  Tokens: {m['input_tokens']} in / {m['output_tokens']} out")

    print(f"{'═' * 60}\n")


# ── Entry Point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Lab Notebook Parser")
    parser.add_argument(
        "--image",
        default="data/Example_Lab_Notebook_Page.jpg",
        help="Path to the lab notebook image (default: data/Example_Lab_Notebook_Page.jpg)",
    )
    parser.add_argument(
        "--output",
        default="output/parsed_notebook.json",
        help="Where to save the JSON output (default: output/parsed_notebook.json)",
    )
    args = parser.parse_args()

    data = extract_from_image(args.image)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✓ Full JSON saved → {args.output}\n")

    print_summary(data)


if __name__ == "__main__":
    main()