# coding: utf-8

# region Descriptions, Import and Configs
"""
win_device.py
在 Windows 上获取窗口名称
by: @wyf9, @pwnint, @kmizmal, @gongfuture, @LeiSureLyYrsc
基础依赖: pywin32, httpx
媒体信息依赖:
    - Python≤3.9: winrt
    - Python≥3.10: winrt.windows.media.control, winrt.windows.foundation
 * (如果你嫌麻烦并且不在乎几十m的包占用, 也可以直接装winsdk :)
电池状态依赖: psutil
"""

"""
Forked version from https://github.com/sleepy-project/sleepy/blob/main/client/win_device.py
Rewrite by @CILXRY
"""

import sys
import io
import asyncio
from datetime import datetime
import threading
import win32api  # type: ignore - 勿删，用于强忽略非 windows 系统上 vscode 找不到模块的警告
import win32con  # type: ignore
import win32gui  # type: ignore

from api_client import APIClient
from media_info import (
    get_media_info,
    format_prefix_media_info,
    format_standalone_media_info,
)
from battery_info import get_battery_info
from mouse_tracker import MouseTracker

# 服务地址, 末尾同样不带 /
SERVER: str = "http://localhost:9010"
# 密钥
SECRET: str = "Azi1aZFZ"
# 设备标识符，唯一 (它也会被包含在 api 返回中, 不要包含敏感数据)
DEVICE_ID: str = "CRB"
# 前台显示名称
DEVICE_SHOW_NAME: str = "CandyRedmiBook"
# 检查间隔，以秒为单位
CHECK_INTERVAL: int = 2
# 是否忽略重复请求，即窗口未改变时不发送请求
BYPASS_SAME_REQUEST: bool = True
# 控制台输出所用编码，避免编码出错，可选 utf-8 或 gb18030
ENCODING: str = "utf-8"
# 当窗口标题为其中任意一项时将不更新
SKIPPED_NAMES: set = {
    "",  # 空字符串
    "系统托盘溢出窗口。",
    "新通知",
    "任务切换",
    "快速设置",
    "通知中心",
    "操作中心",
    "日期和时间信息",
    "网络连接",
    "电池信息",
    "搜索",
    "任务视图",
    "任务切换",
    "Program Manager",
    "贴靠助手",  # 桌面组件
    "Flow.Launcher",
    "Snipper - Snipaste",
    "Paster - Snipaste",  # 其他程序
}
# 当窗口标题为其中任意一项时视为未在使用
NOT_USING_NAMES: set = {
    "启动",
    "「开始」菜单",  # 开始菜单
    "我们喜欢这张图片，因此我们将它与你共享。",
    "就像你看到的图像一样？选择以下选项",
    "喜欢这张图片吗?",
    "Windows 默认锁屏界面",  # 锁屏界面
}
# 是否反转窗口标题，以此让应用名显示在最前 (以 ` - ` 分隔)
REVERSE_APP_NAME: bool = False
# 鼠标静止判定时间 (分钟)
MOUSE_IDLE_TIME: int = 5
# 鼠标移动检测的最小距离 (像素)
MOUSE_MOVE_THRESHOLD: int = 10
# 控制日志是否显示更多信息
DEBUG: bool = False
# 代理地址 (<http/socks>://host:port), 设置为空字符串禁用
PROXY: str = ""
# 是否启用媒体信息获取
MEDIA_INFO_ENABLED: bool = True
# 媒体信息显示模式: 'prefix' - 作为前缀添加到当前窗口名称, 'standalone' - 使用独立设备
MEDIA_INFO_MODE: str = "standalone"
# 独立设备模式下的设备ID (仅当 MEDIA_INFO_MODE = 'standalone' 时有效)
MEDIA_DEVICE_ID: str = "media-device"
# 独立设备模式下的显示名称 (仅当 MEDIA_INFO_MODE = 'standalone' 时有效)
MEDIA_DEVICE_SHOW_NAME: str = "正在播放"
# 是否启用电源状态获取
BATTERY_INFO_ENABLED: bool = True

# endregion

# region Rewrite and Init Functions

# stdout = TextIOWrapper(stdout.buffer, encoding=ENCODING)  # https://stackoverflow.com/a/3218048/28091753
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
_print_ = print


def print(msg: str, **kwargs):
    """
    修改后的 `print()` 函数，解决不刷新日志的问题
    - 原: `_print_()`
    """
    msg = str(msg).replace("\u200b", "")
    try:
        _print_(
            f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {msg}',
            flush=True,
            **kwargs,
        )
    except Exception as e:
        _print_(
            f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Log Error: {e}',
            flush=True,
        )


def debug(msg: str, **kwargs):
    """
    显示调试消息
    """
    if DEBUG:
        print(msg, **kwargs)


def reverse_app_name(name: str) -> str:
    """
    反转应用名称 (将末尾的应用名提前)
    如 Before: win_device.py - dev - Visual Studio Code
    After: Visual Studio Code - dev - win_device.py
    """
    lst = name.split(" - ")
    new = []
    for i in lst:
        new = [i] + new
    return " - ".join(new)

# endregion

# 初始化各模块
api_client = APIClient(SERVER, SECRET, PROXY)
mouse_tracker = MouseTracker(MOUSE_IDLE_TIME, MOUSE_MOVE_THRESHOLD, DEBUG)



# ----- Part: Send status

last_window = ""

# ----- Part: Shutdown handler


def on_shutdown(hwnd, msg, wparam, lparam):
    """
    关机监听回调
    """
    if msg == win32con.WM_QUERYENDSESSION:
        print("Received logout event, sending not using...")
        try:
            # 在新的事件循环中运行异步函数
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            resp = loop.run_until_complete(
                api_client.send_status(
                    using=False,
                    status="要关机了喵",
                    device_id=DEVICE_ID,
                    show_name=DEVICE_SHOW_NAME,
                )
            )
            loop.close()
            if resp is not None:  # 添加 None 检查
                debug(f"Response: {resp.status_code} - {resp.json()}")
                if resp.status_code != 200:
                    print(f"Error! Response: {resp.status_code} - {resp.json()}")
        except Exception as e:
            print(f"Exception: {e}")
        return True  # 允许关机或注销
    return 0  # 其他消息


# 注册窗口类
wc = win32gui.WNDCLASS()
wc.lpfnWndProc = on_shutdown  # type: ignore - 设置回调函数
wc.lpszClassName = "ShutdownListener"  # type: ignore
wc.hInstance = win32api.GetModuleHandle(None)  # type: ignore

# 创建窗口类并注册
class_atom = win32gui.RegisterClass(wc)

# 创建窗口
hwnd = win32gui.CreateWindow(
    class_atom,  # className
    "Sleepy Shutdown Listener",  # windowTitle
    0,  # style
    0,  # x
    0,  # y
    0,  # width
    0,  # height
    0,  # parent
    0,  # menu
    wc.hInstance,  # hinstance
    None,  # reserved
)


def message_loop():
    """
    (需异步执行) 用于在后台启动消息循环
    """
    win32gui.PumpMessages()


# 创建并启动线程
message_thread = threading.Thread(target=message_loop, daemon=True)
message_thread.start()

# ----- Part: Mouse idle

cached_window_title = ""  # 缓存窗口标题, 用于恢复


# ----- Part: Main interval check

last_media_playing = False  # 跟踪上一次的媒体播放状态
last_media_content = ""  # 跟踪上一次的媒体内容


async def do_update():
    # 全局变量
    global last_window, cached_window_title, last_media_playing, last_media_content

    # --- 窗口名称 / 媒体信息 (prefix) 部分

    # 获取当前窗口标题和鼠标状态
    current_window = win32gui.GetWindowText(win32gui.GetForegroundWindow())
    # 如果启用了反转应用名称功能，则反转窗口标题
    if REVERSE_APP_NAME and " - " in current_window:
        current_window = reverse_app_name(current_window)
    mouse_idle = mouse_tracker.check_idle()
    debug(f"--- Window: `{current_window}`, mouse_idle: {mouse_idle}")

    # 始终保持同步的状态变量
    window = current_window
    using = True

    # 获取电池信息
    if BATTERY_INFO_ENABLED:
        battery_percent, battery_status = get_battery_info()
        if battery_percent > 0:
            window = f"[🔋{battery_percent}%{battery_status}] {window}"

    # 获取媒体信息
    prefix_media_info = None
    standalone_media_info = None

    if MEDIA_INFO_ENABLED:
        is_playing, title, artist, album = await get_media_info()
        if is_playing and (title or artist):
            # 为 prefix 模式创建格式化后的媒体信息 [♪歌曲名]
            if title:
                prefix_media_info = format_prefix_media_info(title)

            # 为 standalone 模式创建格式化后的媒体信息 ♪歌曲名-歌手-专辑
            standalone_media_info = format_standalone_media_info(title, artist, album)

            print(f"独立媒体信息: {standalone_media_info}")

    # 处理媒体信息 (prefix 模式)
    if MEDIA_INFO_ENABLED and prefix_media_info and MEDIA_INFO_MODE == "prefix":
        # 作为前缀添加到窗口名称
        window = f"{prefix_media_info} {window}"

    # 鼠标空闲状态处理（优先级最高）
    if mouse_idle:
        # 缓存非空闲时的窗口标题
        if not mouse_tracker.is_mouse_idle:
            cached_window_title = current_window
            print("Caching window title before idle")
        # 设置空闲状态
        using = False
        window = ""
    else:
        # 从空闲恢复
        if mouse_tracker.is_mouse_idle:
            window = cached_window_title
            using = True
            print("Restoring window title from idle")

    # 是否需要发送更新
    should_update = (
        mouse_idle != mouse_tracker.is_mouse_idle  # 鼠标状态改变
        or window != last_window  # 窗口改变
        or not BYPASS_SAME_REQUEST  # 强制更新模式
    )

    if should_update:
        # 窗口名称检查 (未使用列表)
        if current_window in NOT_USING_NAMES:
            using = False
            debug(f"* not using: `{current_window}`")

        # 窗口名称检查 (跳过列表)
        if current_window in SKIPPED_NAMES:
            if mouse_idle == mouse_tracker.is_mouse_idle:
                # 鼠标状态未改变 -> 直接跳过
                debug(f"* in skip list: `{current_window}`, skipped")
                return
            else:
                # 鼠标状态改变 -> 将窗口名称设为上次 (非未在使用) 的名称
                debug(
                    f"* in skip list: `{current_window}`, set app name to last window: `{last_window}`"
                )
                window = last_window

        # 发送状态更新
        print(
            f'Sending update: using = {using}, status = "{window}", idle = {mouse_idle}'
        )
        try:
            resp = await api_client.send_status(
                using=using,
                status=window,
                device_id=DEVICE_ID,
                show_name=DEVICE_SHOW_NAME,
            )
            if resp is not None:  # 添加 None 检查
                debug(f"Response: {resp.status_code} - {resp.json()}")
                if resp.status_code != 200 and not DEBUG:
                    print(f"Error! Response: {resp.status_code} - {resp.json()}")
            last_window = window
        except Exception as e:
            print(f"Error: {e}")
    else:
        debug("No state change, skipping window name update")

    # --- 媒体信息 (standalone) 部分

    # 如果使用独立设备模式展示媒体信息
    if MEDIA_INFO_ENABLED and MEDIA_INFO_MODE == "standalone":
        try:
            # 确定当前媒体状态
            current_media_playing = bool(standalone_media_info)
            current_media_content = (
                standalone_media_info if standalone_media_info else ""
            )

            # 检测播放状态或歌曲内容是否变化
            media_changed = (current_media_playing != last_media_playing) or (
                current_media_playing and current_media_content != last_media_content
            )

            if media_changed:
                print(
                    f"Media changed: status: {last_media_playing} -> {current_media_playing}, content: {last_media_content != current_media_content} - `{standalone_media_info}`"
                )

                if current_media_playing:
                    # 从不播放变为播放或歌曲内容变化
                    media_resp = await api_client.send_status(
                        using=True,
                        status=standalone_media_info,
                        device_id=MEDIA_DEVICE_ID,
                        show_name=MEDIA_DEVICE_SHOW_NAME,
                    )
                else:
                    # 从播放变为不播放
                    media_resp = await api_client.send_status(
                        using=False,
                        status="没有媒体播放",
                        device_id=MEDIA_DEVICE_ID,
                        show_name=MEDIA_DEVICE_SHOW_NAME,
                    )
                if media_resp is not None:
                    debug(f"Media Response: {media_resp.status_code}")

                # 更新上一次的媒体状态和内容
                last_media_playing = current_media_playing
                last_media_content = current_media_content
        except Exception as e:
            debug(f"Media Info Error: {e}")


async def main() -> None:
    """
    主程序异步函数
    """
    try:
        while True:
            await do_update()
            await asyncio.sleep(CHECK_INTERVAL)
    except (KeyboardInterrupt, SystemExit, asyncio.CancelledError) as e:
        # 如果中断或被 taskkill 则发送未在使用
        debug(f"Interrupted / Cancelled: {e}")
        try:
            resp = await api_client.send_status(
                using=False,
                status="未在使用",
                device_id=DEVICE_ID,
                show_name=DEVICE_SHOW_NAME,
            )
            if resp is not None:  # 添加 None 检查
                debug(f"Response: {resp.status_code} - {resp.json()}")

                # 如果启用了独立媒体设备，也发送该设备的退出状态
                if MEDIA_INFO_ENABLED and MEDIA_INFO_MODE == "standalone":
                    media_resp = await api_client.send_status(
                        using=False,
                        status="未在使用",
                        device_id=MEDIA_DEVICE_ID,
                        show_name=MEDIA_DEVICE_SHOW_NAME,
                    )
                    if media_resp is not None:  # 添加 None 检查
                        debug(f"Media Response: {media_resp.status_code}")

                if resp.status_code != 200:
                    print(f"Error! Response: {resp.status_code} - {resp.json()}")
        except Exception as e:
            print(f"Error sending not using: {e}")
        finally:
            print(f"Bye.")


if __name__ == "__main__":
    asyncio.run(main())
