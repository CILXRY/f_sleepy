from pydantic import BaseModel, Field
from typing import List, Union, Optional

class StatusItem(BaseModel):
    id: int
    name: str
    color: str = "#000000"
    icon: str = "💤"
    description: str = ""

class MainConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8080
    secret: str = "change-me"
    debug: bool = False
    https: bool = False
    ssl_key: Optional[str] = None
    ssl_cert: Optional[str] = None
    cors_origins: Union[str, List[str]] = "*"

class PageConfig(BaseModel):
    title: str = "Sleepy"
    theme: str = "default"

class StatusConfig(BaseModel):
    default: int = 0
    status_list: List[StatusItem]

class AppConfig(BaseModel):
    main: MainConfig
    page: PageConfig
    status: StatusConfig