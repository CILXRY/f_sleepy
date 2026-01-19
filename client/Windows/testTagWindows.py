import win32gui
import win32process
import psutil
import os

def get_window_exe(hwnd):
    try:
        # 获取窗口所属的进程 ID
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        # 通过 PID 获取进程对象
        proc = psutil.Process(pid)
        # 获取可执行文件路径
        return proc.exe()
    except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
        return None

def enum_visible_windows():
    windows = []
    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title.strip():
                exe = get_window_exe(hwnd)
                windows.append({
                    'hwnd': hwnd,
                    'title': title,
                    'exe': exe or 'Unknown'
                })
        return True
    win32gui.EnumWindows(callback, None)
    return windows

# 使用示例
for win in enum_visible_windows():
    print(f"[{os.path.basename(win['exe'])}] {win['title']}")