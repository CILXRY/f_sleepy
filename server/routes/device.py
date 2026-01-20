from fastapi import APIRouter, Depends, Security
import time
from models.device_status import DeviceStatus
from models.api import DeviceInfo
from data import Data
from utils import verify_secret

router = APIRouter()


def get_data() -> Data:
    from main import data_store

    return data_store


@router.post("/api/device/report/")
def report_device_status(
    status: DeviceStatus,
    _: bool = Security(verify_secret),
    data: Data = Depends(get_data),
):
    now = time.time()

    dev_entry = DeviceInfo(
        id=status.device_id,
        name=status.device_name,
        last_seen=now,
        battery_percent=status.battery_percent,
        battery_status=status.battery_status,
        active_app=status.active_app.dict() if status.active_app else None,
    )

    # 替换或新增
    for i, dev in enumerate(data.device_list):
        if dev.id == status.device_id:  # 使用 .id 而不是 ["id"]
            data.device_list[i] = dev_entry
            break
    else:
        data.device_list.append(dev_entry)

    return {"success": True, "message": "Device status updated"}
