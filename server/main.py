import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
from contextlib import asynccontextmanager
from config.loader import load_config
from config import get_config
from data import Data
import logging

# 日志初始化（略，同原逻辑）
config = get_config()
data_store = Data(config)

try:
    config = load_config()
except SystemExit:
    # load_config() 已处理错误并退出
    raise
except Exception as e:
    print(f"配置加载失败: {e}")
    sys.exit(1)


# 生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动
    yield
    # 关闭
    logging.info("Shutting down...")


app = FastAPI(lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        config.main.cors_origins
        if isinstance(config.main.cors_origins, list)
        else ["*"]
    ),
    allow_methods=["*"],
    allow_headers=["*"],
)

# # 静态文件（简化）
# app.mount("/static", StaticFiles(directory="static"), name="static")


from routes.status import router as status_router
from routes.device import router as device_router

app.include_router(status_router)
app.include_router(device_router)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        reload=True,
        host=config.main.host,
        port=config.main.port,
        # reload=config.main.debug,
        ssl_keyfile=config.main.ssl_key if config.main.https else None,
        ssl_certfile=config.main.ssl_cert if config.main.https else None,
    )
