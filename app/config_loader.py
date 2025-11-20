import json
import os
from threading import Lock

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "data", "wine_config.json")
_config_lock = Lock()

def load_wine_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_wine_config(data):
    with _config_lock:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
