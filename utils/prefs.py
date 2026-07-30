import json
from pathlib import Path
from config import config

USER_PREFS_FILE = config.DATA_DIR / "user_prefs.json"

# In-memory cache
USER_PREFS: dict[int, dict] = {}

def _load():
    global USER_PREFS
    if USER_PREFS_FILE.exists():
        with open(USER_PREFS_FILE, 'r') as f:
            USER_PREFS = {int(k): v for k, v in json.load(f).items()}

def _save():
    USER_PREFS_FILE.write_text(json.dumps(USER_PREFS, ensure_ascii=False, indent=2))

def get_prefs(user_id: int) -> dict:
    if not USER_PREFS:
        _load()
    return USER_PREFS.get(user_id, {
        "lang": "id",
        "mode": "solo",
        "length": 5,
        "hard_mode": False,
        "colorblind": False,
    })

def set_pref(user_id: int, key: str, value):
    if not USER_PREFS:
        _load()
    if user_id not in USER_PREFS:
        USER_PREFS[user_id] = {
            "lang": "id", "mode": "solo", "length": 5,
            "hard_mode": False, "colorblind": False,
        }
    USER_PREFS[user_id][key] = value
    _save()

def get_lang(user_id: int) -> str:
    return get_prefs(user_id).get("lang", "id")

_load()