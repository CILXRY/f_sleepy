from fastapi import APIRouter, Query, Depends, Request, Security
from typing import Optional
import time
from models.api import DeviceInfo, QueryResponse, SetResponse, StatusInfo
from utils import verify_secret
from config import get_config
from data import Data
from fastapi.responses import StreamingResponse
import json
import asyncio

router = APIRouter()

# 依赖项：获取全局实例
def get_data() -> Data:
    # 实际项目中可从 app.state 或 DI 容器获取
    from main import data_store

    return data_store


def get_metadata(config):
    return {
        "version": "0.5.0",
        "title": config.page.title,
        "theme": config.page.theme,
        "cors_origins": config.main.cors_origins,
    }


async def status_event_generator(data: Data):
    """生成 SSE 事件流"""
    queue = asyncio.Queue()

    def on_update(payload):
        # 将更新放入队列
        asyncio.create_task(queue.put(json.dumps(payload)))

    # 注册监听器
    data.add_listener(on_update)
    try:
        # 先发送当前状态
        initial = {
            "status_id": data.status_id,
            "last_updated": data.last_updated,
            "device_count": len(data.device_list)
        }
        yield f"data: {json.dumps(initial)}\n\n"

        # 持续等待新事件
        while True:
            payload = await queue.get()
            yield f"data: {payload}\n\n"
            queue.task_done()
    except asyncio.CancelledError:
        pass
    finally:
        # 取消监听
        data.remove_listener(on_update)


@router.get("/api/status/query", response_model=QueryResponse)
def query_status(
    config=Depends(get_config),
    data: Data = Depends(get_data),
):
    # 获取当前状态信息
    try:
        st_obj = config.status.status_list[data.status_id]
        st_info = StatusInfo(
            id=st_obj.id,
            name=st_obj.name,
            color=st_obj.color,
            icon=st_obj.icon,
            description=st_obj.description,
        )
    except (IndexError, AttributeError):
        st_info = StatusInfo(
            id=-1, name="[未知]", color="#888", icon="❓", description=""
        )

    # 直接使用已经存在的DeviceInfo对象列表，无需重新创建
    devices = data.device_list

    resp = QueryResponse(
        success=True,
        time=time.time(),
        status=st_info,
        device=devices,
        last_updated=data.last_updated,
    )

    return resp


@router.get("/api/status/set", response_model=SetResponse)
async def set_status(
    status: int = Query(..., ge=0),
    _: bool = Security(verify_secret),  # ← 关键：用 Security 而不是 Depends
    config=Depends(get_config),
    data: Data = Depends(get_data),
):
    # 切换状态
    if data.set_status(status, config):
        # 构造新状态信息
        st_obj = config.status.status_list[status]
        new_status = StatusInfo(
            id=st_obj.id,
            name=st_obj.name,
            color=st_obj.color,
            icon=st_obj.icon,
            description=st_obj.description,
        )
        return SetResponse(
            success=True, message="Status updated successfully", new_status=new_status
        )
    else:
        return SetResponse(
            success=False,
            message=f"Invalid status ID: {status}",
            new_status=StatusInfo(id=-1, name="", color="", icon="", description=""),
        )

@router.get("/api/status/events")
async def status_events(
    data: Data = Depends(get_data)
):
    return StreamingResponse(
        status_event_generator(data),
        media_type="text/event-stream"
    )