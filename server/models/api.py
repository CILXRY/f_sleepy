# models/api.py
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class StatusInfo(BaseModel):
    id: int
    name: str
    color: str
    icon: str
    description: str

class DeviceInfo(BaseModel):
    id: str
    name: str
    last_seen: float
    battery_percent: Optional[int] = None
    battery_status: Optional[str] = None
    active_app: Optional[Dict[str, Any]] = None

class QueryResponse(BaseModel):
    success: bool
    time: float
    status: StatusInfo
    device: List[DeviceInfo]
    last_updated: float
    meta: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None

class SetResponse(BaseModel):
    success: bool
    message: str
    new_status: StatusInfo