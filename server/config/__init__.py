from functools import lru_cache
from .loader import load_config

@lru_cache()
def get_config():
    return load_config()