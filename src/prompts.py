SYSTEM_PROMPT = """You are an expert chemistry lab notebook digitizer. 
You will receive a scanned handwritten lab notebook page and must extract ALL 
information into structured JSON. You are highly skilled at:
- Reading messy handwriting and scientific shorthand
- Interpreting chemical formulas, concentrations, and units
- Understanding electrochemistry experimental protocols
- Identifying hand-drawn molecular structures and naming them

Return ONLY valid JSON matching the schema exactly. No markdown, no explanation."""

EXTRACTION_PROMPT = """Analyze this lab notebook page image and extract ALL information 
into this exact JSON schema. Be exhaustive — capture every written word, symbol, 
number, and drawn structure.

IMPORTANT RULES:
1. Preserve scientific notation exactly (e.g., "1.5E-4", "8.4E-6")
2. Use Unicode for special symbols: °C not C, Ω not ohm, θ not theta, λ not lambda
3. For chemical formulas use proper notation: subscripts as Unicode or _n_ notation
4. For hand-drawn structures: identify them and provide SMILES strings if possible
5. Preserve all units exactly as written (mA/cm², rpm, mol/L, v/v, etc.)
6. Note any ambiguous readings with a [?] flag

Return this JSON structure:

{
  "page_metadata": {
    "page_number": <int>,
    "date": "<string>",
    "project_title": "<string>",
    "continued_from_page": <int or null>
  },
  "goal": "<string — the stated experimental goal>",
  "electrolyte": {
    "description": "<full text description>",
    "components": [
      {"name": "<compound name>", "concentration": "<value+units>", "solvent": "<string>", "ratio": "<string or null>"}
    ],
    "total_volume": "<value+units>",
    "additives": [
      {"name": "<compound>", "amount": "<value+units>", "preparation": "<string>"}
    ]
  },
  "electrode_setup": {
    "working_electrode": {"material": "<string>", "type": "<string>", "area": "<value+units>"},
    "counter_electrode": "<string>",
    "reference_electrode": "<string>",
    "atmosphere": "<string or null>",
    "water_content": "<string or null>"
  },
  "deposition_run": {
    "run_id": "<string>",
    "applied_potential_V": <float>,
    "reference": "<string>",
    "duration_min": <float>,
    "duration_s": <float>,
    "rotation_speed_rpm": <int>,
    "current_density_mA_per_cm2": <float>,
    "electrode_area_cm2": <float>,
    "calculated_current_A": "<string — show calculation>",
    "calculated_charge_C": <float>,
    "moles_deposited_mol": "<string in sci notation>",
    "mass_deposited_g": "<string in sci notation>"
  },
  "electrochemistry_equations": [
    "<string — each equation or reaction written on the page>"
  ],
  "chemical_structures": [
    {
      "name": "<compound name>",
      "type": "<crown ether | salt | solvent | other>",
      "smiles": "<SMILES string if determinable>",
      "description": "<text description of drawn structure>",
      "role_in_experiment": "<string>"
    }
  ],
  "temperature_test": {
    "description": "<string>",
    "time_temperature_table": [
      {"time": "<string>", "temperature_C": <float>}
    ]
  },
  "observations_and_results": [
    "<string — each observation, film appearance, XRD note, etc.>"
  ],
  "raw_text_full": "<complete verbatim transcription of all handwritten text on the page, line by line>",
  "ambiguous_readings": [
    {"location": "<description>", "raw_text": "<what was written>", "interpretation": "<best guess>"}
  ]
}"""
