import time
import asyncio
from typing import Callable, List, Dict, Any, Set

from models.api import DeviceInfo
from models.device_status import DeviceStatus


class Data:
    def __init__(self, config):
        self.status_id = getattr(config.status, "default", 0)
        self.device_list: List[DeviceInfo] = []
        self.last_updated = time.time()
        self.metrics_resp: Dict[str, Any] = {"switch_count": 0}
        self._listeners: Set[Callable] = set()

    def add_listener(self, callback: Callable):
        self._listeners.add(callback)

    def remove_listener(self, callback: Callable):
        self._listeners.discard(callback)

    async def broadcast_status_update(self):
        """通知所有监听者状态已更新"""
        status_snapshot = {
            "status_id": self.status_id,
            "last_updated": self.last_updated,
            "device_count": len(self.device_list),
        }
        for listener in self._listeners:
            try:
                await listener(status_snapshot)
            except Exception:
                pass  # 忽略断开的连接

    def set_status(self, new_id: int, config) -> bool:
        if 0 <= new_id < len(config.status.status_list):
            self.status_id = new_id
            self.last_updated = time.time()
            self.metrics_resp["switch_count"] += 1
            asyncio.create_task(self.broadcast_status_update())
            return True
        return False

    def update_device(self, report: DeviceStatus):
        entry = DeviceInfo(
            id=report.device_id,
            name=report.device_id,  # 或从 custom 获取
            last_seen=time.time(),
            battery_percent=report.battery_percent,
            battery_status=report.battery_status,
            active_app=report.active_app.dict() if report.active_app else None,
        )

        self.device_list.append(entry)
