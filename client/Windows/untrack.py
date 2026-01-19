async def re_get_media_info():
    """
    使用 pywinrt 获取 Windows SMTC 媒体信息 (正在播放的音乐等)
    Returns:
        tuple: (是否正在播放, 标题, 艺术家, 专辑)
    """
    # 首先尝试使用 pywinrt - 这是最可靠的通用方法
    try:
        # 获取媒体会话管理器
        manager = await media.GlobalSystemMediaTransportControlsSessionManager.request_async()  # type: ignore
        session = manager.get_current_session()

        if not session:
            debug("[get_media_info] No active media session found via pywinrt")
        else:
            # 获取播放状态
            info = session.get_playback_info()
            is_playing = info.playback_status == media.GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING  # type: ignore

            # 获取媒体属性
            props = await session.try_get_media_properties_async()

            title = props.title or "" if props else ""  # type: ignore
            artist = props.artist or "" if props else ""  # type: ignore
            album = props.album_title or "" if props else ""  # type: ignore

            if "未知唱片集" in album or "<" in album and ">" in album:
                album = ""

            # 如果通过 pywinrt 成功获取到媒体信息，且有标题或艺术家，则返回这些信息
            if is_playing and (title or artist):
                debug(
                    f"[get_media_info] pywinrt success: {is_playing}, {title}, {artist}, {album}"
                )
                return is_playing, title, artist, album
            else:
                debug(
                    f"[get_media_info] pywinrt returned no meaningful data: {is_playing}, {title}, {artist}, {album}"
                )

    except Exception as primary_error:
        debug(f"主要媒体信息获取方式(pywinrt)失败: {primary_error}")

    # 如果pywinrt方法失败或没有返回有意义的数据，则尝试检测特定应用程序（如网易云音乐）
    try:
        import psutil

        def get_window_exe(hwnd):
            """获取窗口对应的可执行文件路径"""
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                proc = psutil.Process(pid)
                return proc.exe()
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                return None

        def enum_visible_windows():
            """枚举所有可见窗口及其可执行文件"""
            windows = []

            def callback(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title.strip():
                        exe = get_window_exe(hwnd)
                        windows.append(
                            {"hwnd": hwnd, "title": title, "exe": exe or "Unknown"}
                        )
                return True

            win32gui.EnumWindows(callback, None)
            return windows

        # 获取所有可见窗口
        debug("[get_media_info] Enumerating visible windows...")
        all_windows = enum_visible_windows()

        # 调试：输出所有窗口信息
        debug(f"[get_media_info] Total visible windows: {len(all_windows)}")
        for win in all_windows[:10]:  # 只显示前10个窗口以避免过多输出
            debug(
                f"[get_media_info] Window: title='{win['title']}', exe='{win['exe']}'"
            )

        if len(all_windows) > 10:
            debug(f"[get_media_info] ... and {len(all_windows)-10} more windows")

        # 查找网易云音乐窗口
        cloudmusic_found = False
        for win in all_windows:
            exe_path = win["exe"]
            exe_name = (
                exe_path.split("\\")[-1].lower() if exe_path != "Unknown" else "unknown"
            )
            debug(
                f"[get_media_info] Checking window: '{win['title']}', exe: '{exe_name}'"
            )

            if "cloudmusic.exe" in exe_name:
                cloudmusic_found = True
                debug(
                    f"[get_media_info] Found NetEase Cloud Music window: {win['title']}, exe: {exe_path}"
                )

                # 提取窗口标题中的音乐信息
                # 网易云音乐的窗口标题通常是 "歌曲名 - 艺术家 - 网易云音乐" 或 "歌曲名 - 网易云音乐"
                # ✅ 新的：只看 exe 名，不依赖窗口标题含“网易云音乐”
                title_text = win["title"].strip()
                # 过滤掉主界面、空标题等非播放状态
                if (
                    not title_text
                    or title_text
                    in {
                        "网易云音乐",
                        "发现音乐",
                        "私人FM",
                        "我的音乐",
                        "最近播放",
                        "每日推荐",
                        "歌单",
                        "排行榜",
                        "关注",
                        "朋友",
                        "视频",
                        "播客",
                        "正在启动...",
                        "迷你播放器",
                        "桌面歌词",
                    }
                    or title_text.startswith(("搜索", "创建歌单", "登录"))
                ):
                    debug(
                        f"[get_media_info] Skipping CloudMusic window (blacklisted or invalid): '{title_text}'"
                    )
                    continue  # 👈 这里跳过了！

                # 按 " - " 分割标题（格式通常是：歌曲名 - 艺术家）
                parts = [p.strip() for p in title_text.split(" - ") if p.strip()]
                if not parts:
                    continue

                title = parts[0]
                artist = parts[1] if len(parts) > 1 else "未知艺术家"
                album = parts[2] if len(parts) > 2 else ""

                debug(
                    f"[get_media_info] NetEase Cloud Music (via exe): '{title}' by '{artist}'"
                )
                return True, title, artist, album  # 👈 必须返回 True！

    except Exception as proc_error:
        debug(f"Process detection error: {proc_error}")
        import traceback

        debug(f"Full traceback: {traceback.format_exc()}")

    # 如果所有方法都失败了，返回默认值
    debug("[get_media_info] All methods failed, returning default values")
    return False, "", "", ""