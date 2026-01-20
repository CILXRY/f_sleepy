# config/loader.py
import os
import sys
import yaml
from pathlib import Path
from .schema import AppConfig
from .default_config import DEFAULT_CONFIG_YAML

CONFIG_FILE = Path("config.yaml")
EXAMPLE_FILE = Path("config.example.yaml")


def load_config() -> AppConfig:
    # 情况 1: config.yaml 不存在
    if not CONFIG_FILE.exists():
        print(f"❌ 找不到配置文件: {CONFIG_FILE}")
        print(f"📝 正在生成示例配置: {EXAMPLE_FILE}")

        # 写入带注释的示例
        EXAMPLE_FILE.write_text(DEFAULT_CONFIG_YAML, encoding="utf-8")

        # 同时生成一个可直接运行的最小 config.yaml
        print(f"⚙️  生成默认配置: {CONFIG_FILE}")
        CONFIG_FILE.write_text(DEFAULT_CONFIG_YAML, encoding="utf-8")

        print("\n✅ 已创建默认配置！")
        print(f"👉 请根据需要编辑 {CONFIG_FILE}，然后重新启动程序。")
        print("💡 提示：至少修改 `main.secret` 以保证安全！\n")
        sys.exit(1)  # 退出，让用户先配置

    # 情况 2: config.yaml 存在，但解析失败
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        if raw is None:
            raise ValueError("配置文件为空")
        return AppConfig(**raw)
    except (yaml.YAMLError, ValueError, TypeError) as e:
        print(f"❌ 配置文件 {CONFIG_FILE} 格式错误:")
        print(f"   {e}")
        print(f"\n📝 正在生成参考示例: {EXAMPLE_FILE}")
        EXAMPLE_FILE.write_text(DEFAULT_CONFIG_YAML, encoding="utf-8")
        print(f"\n🔧 请对照 {EXAMPLE_FILE} 修正你的配置，然后重试。\n")
        sys.exit(1)
    except Exception as e:
        print(f"💥 未知配置错误: {e}")
        sys.exit(1)
