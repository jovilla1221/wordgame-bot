import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).parent

@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_IDS: list[int] = None
    DATA_DIR: Path = BASE_DIR / "data"
    GAMES_FILE: Path = BASE_DIR / "data" / "games.json"
    STATS_FILE: Path = BASE_DIR / "data" / "stats.json"
    WORDS_ID_FILE: Path = BASE_DIR / "data" / "words_id.txt"
    WORDS_EN_FILE: Path = BASE_DIR / "data" / "words_en.txt"
    DAILY_WORD_FILE: Path = BASE_DIR / "data" / "daily_word.json"
    DEFAULT_LENGTH: int = 5
    MAX_LENGTH: int = 6
    MIN_LENGTH: int = 4
    MAX_GUESSES: int = 6
    HINT_COST: int = 5
    DAILY_RESET_HOUR: int = 0  # UTC 00:00 = WIB 07:00
    
    def __post_init__(self):
        if self.ADMIN_IDS is None:
            admin_str = os.getenv("ADMIN_IDS", "")
            self.ADMIN_IDS = [int(x) for x in admin_str.split(",") if x.strip()]
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

config = Config()