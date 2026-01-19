"""
鼠标追踪模块
负责检测鼠标活动状态
"""

import time
import win32api  # type: ignore
from pywintypes import error as pywinerror  # type: ignore


class MouseTracker:
    def __init__(self, idle_time_minutes: int = 5, move_threshold: int = 10, debug: bool = False):
        self.mouse_idle_time = idle_time_minutes
        self.mouse_move_threshold = move_threshold
        self.debug = debug
        
        # 鼠标状态相关变量
        self.last_mouse_pos = win32api.GetCursorPos()
        self.last_mouse_move_time = time.time()
        self.is_mouse_idle = False

    def check_idle(self) -> bool:
        """
        检查鼠标是否静止
        返回 True 表示鼠标静止超时
        """
        try:
            current_pos = win32api.GetCursorPos()
        except pywinerror as e:
            print(f"Check mouse pos error: {e}")
            return self.is_mouse_idle

        current_time = time.time()

        # 计算鼠标移动距离的平方（避免开平方运算）
        dx = abs(current_pos[0] - self.last_mouse_pos[0])
        dy = abs(current_pos[1] - self.last_mouse_pos[1])
        distance_squared = dx * dx + dy * dy

        # 阈值的平方，用于比较
        threshold_squared = self.mouse_move_threshold * self.mouse_move_threshold

        # 打印详细的鼠标状态信息（为了保持日志一致性，仍然显示计算后的距离）
        if self.debug:
            distance = distance_squared**0.5 if self.debug else 0  # 仅在需要打印日志时计算
            print(
                f"Mouse: current={current_pos}, last={self.last_mouse_pos}, distance={distance:.1f}px"
            )

        # 如果移动距离超过阈值（使用平方值比较）
        if distance_squared > threshold_squared:
            self.last_mouse_pos = current_pos
            self.last_mouse_move_time = current_time
            if self.is_mouse_idle:
                self.is_mouse_idle = False
                actual_distance = (
                    distance_squared**0.5
                )  # 仅在状态变化时计算实际距离用于日志
                print(
                    f"Mouse wake up: moved {actual_distance:.1f}px > {self.mouse_move_threshold}px"
                )
            else:
                if self.debug:
                    distance = distance_squared**0.5
                    print(f"Mouse moving: {distance:.1f}px > {self.mouse_move_threshold}px")
            return False

        # 检查是否超过静止时间
        idle_time = current_time - self.last_mouse_move_time
        if self.debug:
            print(f"Idle time: {idle_time:.1f}s / {self.mouse_idle_time*60:.1f}s")

        if idle_time > self.mouse_idle_time * 60:
            if not self.is_mouse_idle:
                self.is_mouse_idle = True
                print(f"Mouse entered idle state after {idle_time/60:.1f} minutes")
            return True

        return self.is_mouse_idle  # 保持当前状态

    def reset(self):
        """重置鼠标追踪状态"""
        self.last_mouse_pos = win32api.GetCursorPos()
        self.last_mouse_move_time = time.time()
        self.is_mouse_idle = False