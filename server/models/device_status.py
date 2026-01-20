from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from enum import Enum


class BatteryStatus(str, Enum):
    """电量状态"""

    charging = "True"
    discharging = "False"
    unknown = "Unknown"


class IsActive(str, Enum):
    """设备活动状态"""

    active = "Using"
    inactive = "Inactive"
    locked = "Locked"
    shutdown = "Shutdown"
    unknown = "Unknown"


class AppInfo(BaseModel):
    name: str
    title: Optional[str] = None  # 窗口标题（可选）
    pid: Optional[int] = None


class DeviceStatus(BaseModel):

    device_id: str
    device_name: str
    is_active: IsActive = IsActive.unknown
    timestamp: float  # 客户端时间戳（用于计算延迟）

    # 电量信息
    battery_percent: Optional[int] = None  # 0-100
    battery_status: Optional[BatteryStatus] = BatteryStatus.unknown

    # 应用信息
    active_app: Optional[AppInfo] = None

    # 自定义扩展字段
    custom: Optional[Dict[str, Any]] = None
