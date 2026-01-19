"""
媒体信息获取模块
负责获取Windows系统的媒体播放信息
"""

from typing import Tuple
import winrt.windows.media.control as media  # type: ignore


async def get_media_info() -> Tuple[bool, str, str, str]:
    """获取 Windows 媒体播放信息"""
    try:
        # 获取媒体会话管理器
        manager = (
            await media.GlobalSystemMediaTransportControlsSessionManager.request_async()
        )
        session = manager.get_current_session()

        if not session:
            return False, "", "", ""

        # 获取播放状态
        info = session.get_playback_info()
        is_playing = (
            info.playback_status
            == media.GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING
        )

        # 获取媒体属性
        props = await session.try_get_media_properties_async()

        title = props.title or "" if props else ""
        artist = props.artist or "" if props else ""
        album = props.album_title or "" if props else ""

        # 过滤无效专辑名
        if "未知唱片集" in album or ("<" in album and ">" in album):
            album = ""

        return is_playing, title, artist, album

    except Exception as e:
        print(f"获取媒体信息失败: {e}")
        return False, "", "", ""


def format_prefix_media_info(title: str) -> str:
    """格式化前缀模式的媒体信息"""
    if title:
        return f"[♪{title}]"
    else:
        return "[♪]"


def format_standalone_media_info(title: str, artist: str, album: str) -> str:
    """格式化独立设备模式的媒体信息"""
    parts = []
    if title:
        parts.append(f"♪{title}")
    if artist and artist != title:
        parts.append(artist)
    if album and album != title and album != artist:
        parts.append(album)

    return " - ".join(parts) if parts else "♪播放中"
