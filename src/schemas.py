from pydantic import BaseModel
from typing import List, Optional


class PageMetadata(BaseModel):
    page_number: int
    date: str
    project_title: str
    continued_from_page: Optional[int] = None


class Component(BaseModel):
    name: str
    concentration: Optional[str] = None
    solvent: Optional[str] = None
    ratio: Optional[str] = None


class Additive(BaseModel):
    name: str
    amount: str
    preparation: str


class Electrolyte(BaseModel):
    description: str
    components: List[Component]
    total_volume: str
    additives: List[Additive]


class Electrode(BaseModel):
    material: str
    type: str
    area: str


class ElectrodeSetup(BaseModel):
    working_electrode: Electrode
    counter_electrode: str
    reference_electrode: str
    atmosphere: Optional[str] = None
    water_content: Optional[str] = None


class DepositionRun(BaseModel):
    run_id: str
    applied_potential_V: float
    reference: str
    duration_min: float
    duration_s: float
    rotation_speed_rpm: int
    current_density_mA_per_cm2: float
    electrode_area_cm2: float
    calculated_current_A: str
    calculated_charge_C: float
    moles_deposited_mol: str
    mass_deposited_g: str


class ChemicalStructure(BaseModel):
    name: str
    type: str
    smiles: Optional[str] = None
    description: str
    role_in_experiment: str


class TemperatureRow(BaseModel):
    time: str
    temperature_C: float


class TemperatureTest(BaseModel):
    description: str
    time_temperature_table: List[TemperatureRow]


class AmbiguousReading(BaseModel):
    location: str
    raw_text: str
    interpretation: str


class LabNotebookPageSchema(BaseModel):
    page_metadata: PageMetadata
    goal: str
    electrolyte: Electrolyte
    electrode_setup: ElectrodeSetup
    deposition_run: DepositionRun
    electrochemistry_equations: List[str]
    chemical_structures: List[ChemicalStructure]
    temperature_test: TemperatureTest
    observations_and_results: List[str]
    raw_text_full: str
    ambiguous_readings: List[AmbiguousReading]