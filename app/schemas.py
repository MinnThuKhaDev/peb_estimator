from typing import Optional
from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    width: float
    length: float
    eave_height: float
    wind_speed: float = 130
    live_load: float = 0.57
    seismic_zone: str = ""
    occupancy: str = "II"
    enclosure: str = "Enclosed"
    frame_type: str = ""
    total_weight: float


class ProjectOut(ProjectCreate):
    id: int

    class Config:
        from_attributes = True


class EstimateRequest(BaseModel):
    name: str = "New Project"
    frame_type: str = "CS"
    width: float
    length: float
    eave_height: float
    bay_count: int = 8
    slope_rise: float = 1.5
    slope_run: float = 10
    wind_speed: float = 130
    live_load: float = 0.57
    collateral: float = 0.1
    seismic_zone: str = ""
    occupancy: str = "II"
    enclosure: str = "Enclosed"

    has_mezz: bool = False
    mezz_area: float = 0
    mezz_rate: float = 45

    has_crane: bool = False
    crane_cap: float = 0
    crane_len: float = 0
    crane_rate: float = 3.5

    has_canopy: bool = False
    canopy_area: float = 0
    canopy_rate: float = 8

    pct_bu: float = 38
    pct_dsw: float = 11
    pct_sp: float = 9
    pct_cf: float = 15
    pct_rs: float = 14
    pct_acc: float = 13
