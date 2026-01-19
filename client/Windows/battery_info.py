"""
电池信息获取模块
负责获取系统电池状态信息
"""

import psutil


def get_battery_info():
    """
    获取电池信息
    Returns:
        tuple: (电池百分比, 充电状态)
    """
    try:
        # 电池信息变量
        battery = psutil.sensors_battery()
        if battery is None:
            return 0, "未知"

        percent = battery.percent
        power_plugged = battery.power_plugged
        # 获取充电状态
        status = "⚡" if power_plugged else ""
        return percent, status
    except Exception as e:
        print(f"获取电池信息失败: {e}")
        return 0, "未知"
