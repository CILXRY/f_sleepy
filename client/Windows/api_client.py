"""
API客户端模块
负责与服务器通信
"""

import httpx


class APIClient:
    def __init__(self, server_url: str, secret: str, proxy: str = ""):
        self.api_endpoint = f"{server_url}/api/device/set"
        self.secret = secret
        self.proxy = proxy

    def create_http_client(self):
        """创建HTTP客户端"""
        if self.proxy:
            return httpx.AsyncClient(proxy=self.proxy, timeout=httpx.Timeout(7.5))
        else:
            return httpx.AsyncClient(timeout=httpx.Timeout(7.5))

    async def send_status(
        self,
        using: bool = True,
        status: str = "",
        device_id: str = "",
        show_name: str = "",
        **kwargs,
    ):
        """
        发送设备状态信息
        """
        json_data = {
            "secret": self.secret,
            "id": device_id,
            "show_name": show_name,
            "using": using,
            "status": status,
        }

        async with self.create_http_client() as client:
            try:
                response = await client.post(
                    url=self.api_endpoint,
                    json=json_data,
                    headers={"Content-Type": "application/json"},
                    **kwargs,
                )
                return response
            except httpx.RequestError as exc:
                print(f"An error occurred while requesting {exc.request.url!r}: {exc}")
                return None
            except httpx.HTTPStatusError as exc:
                print(
                    f"Error response {exc.response.status_code} while requesting {exc.request.url!r}: {exc}"
                )
                return None
