import random
import json
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Optional
from config import config

@dataclass
class UserGameState:
    user_id: int
    chat_id: int
    secret: str = ""
    guesses: list[str] = field(default_factory=list)
    mode: str = "solo"  # solo, daily, group
    lang: str = "id"
    length: int = 5
    hard_mode: bool = False
    colorblind: bool = False
    streak: int = 0
    last_play_date: str = ""
    daily_word: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

class WordList:
    def __init__(self):
        self._words_id: dict[int, list[str]] = {}
        self._words_en: dict[int, list[str]] = {}
        self._loaded = False

    def load(self):
        if self._loaded:
            return
        for length in range(config.MIN_LENGTH, config.MAX_LENGTH + 1):
            self._words_id[length] = []
            self._words_en[length] = []
        
        # Load ID words
        if config.WORDS_ID_FILE.exists():
            with open(config.WORDS_ID_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    word = line.strip().upper()
                    if word and word.isalpha() and config.MIN_LENGTH <= len(word) <= config.MAX_LENGTH:
                        self._words_id[len(word)].append(word)
        
        # Load EN words
        if config.WORDS_EN_FILE.exists():
            with open(config.WORDS_EN_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    word = line.strip().upper()
                    if word and word.isalpha() and config.MIN_LENGTH <= len(word) <= config.MAX_LENGTH:
                        self._words_en[len(word)].append(word)
        
        self._loaded = True
        print(f"Loaded ID words: {sum(len(v) for v in self._words_id.values())}")
        print(f"Loaded EN words: {sum(len(v) for v in self._words_en.values())}")

    def get_random(self, lang: str, length: int) -> str:
        self.load()
        words = self._words_id[length] if lang == "id" else self._words_en[length]
        if not words:
            raise ValueError(f"No words for lang={lang}, length={length}")
        return random.choice(words)

    def is_valid(self, word: str, lang: str) -> bool:
        self.load()
        word = word.upper()
        words = self._words_id[len(word)] if lang == "id" else self._words_en[len(word)]
        return word in words

    def get_all(self, lang: str, length: int) -> list[str]:
        self.load()
        return self._words_id[length] if lang == "id" else self._words_en[length]

wordlist = WordList()

class GameEngine:
    GREEN = "🟩"
    YELLOW = "🟨"
    GRAY = "⬜"
    BLUE = "🟦"
    ORANGE = "🟧"

    def __init__(self):
        self.games: dict[int, UserGameState] = {}
        self.stats: dict[int, dict] = {}
        self.daily_word: dict[str, str] = {}  # "YYYY-MM-DD-lang-length" -> word
        self._load_persisted()

    def _load_persisted(self):
        if config.GAMES_FILE.exists():
            with open(config.GAMES_FILE, 'r') as f:
                data = json.load(f)
                for uid, gdata in data.items():
                    self.games[int(uid)] = UserGameState.from_dict(gdata)
        if config.STATS_FILE.exists():
            with open(config.STATS_FILE, 'r') as f:
                self.stats = {int(k): v for k, v in json.load(f).items()}
        if config.DAILY_WORD_FILE.exists():
            with open(config.DAILY_WORD_FILE, 'r') as f:
                self.daily_word = json.load(f)

    def _save_games(self):
        data = {str(k): v.to_dict() for k, v in self.games.items()}
        config.GAMES_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def _save_stats(self):
        config.STATS_FILE.write_text(json.dumps(self.stats, ensure_ascii=False, indent=2))

    def _save_daily(self):
        config.DAILY_WORD_FILE.write_text(json.dumps(self.daily_word, ensure_ascii=False, indent=2))

    def _get_daily_key(self, lang: str, length: int) -> str:
        today = date.today().isoformat()
        return f"{today}-{lang}-{length}"

    def get_daily_word(self, lang: str, length: int) -> str:
        key = self._get_daily_key(lang, length)
        if key not in self.daily_word:
            self.daily_word[key] = wordlist.get_random(lang, length)
            self._save_daily()
        return self.daily_word[key]

    def new_game(self, user_id: int, chat_id: int, mode: str = "solo", 
                 lang: str = "id", length: int = 5, hard_mode: bool = False, 
                 colorblind: bool = False) -> UserGameState:
        if mode == "daily":
            secret = self.get_daily_word(lang, length)
        else:
            secret = wordlist.get_random(lang, length)
        
        # Load existing stats for streak
        stat = self.stats.get(user_id, {"streak": 0, "last_play": "", "games": 0, "wins": 0})
        last_play = stat.get("last_play", "")
        today = date.today().isoformat()
        
        streak = stat.get("streak", 0)
        if last_play:
            from datetime import timedelta
            last_date = date.fromisoformat(last_play)
            if last_date == date.today() - timedelta(days=1):
                pass  # streak continues
            elif last_date < date.today() - timedelta(days=1):
                streak = 0  # broken
        
        game = UserGameState(
            user_id=user_id,
            chat_id=chat_id,
            secret=secret,
            mode=mode,
            lang=lang,
            length=length,
            hard_mode=hard_mode,
            colorblind=colorblind,
            streak=streak,
            last_play_date=last_play,
            daily_word=secret if mode == "daily" else ""
        )
        self.games[user_id] = game
        self._save_games()
        return game

    def get_game(self, user_id: int) -> Optional[UserGameState]:
        return self.games.get(user_id)

    def make_guess(self, user_id: int, guess: str) -> tuple[list[str], bool, bool]:
        """Returns (result_grid, is_valid, is_win)"""
        game = self.games.get(user_id)
        if not game:
            return [], False, False
        
        guess = guess.upper().strip()
        if len(guess) != game.length or not guess.isalpha():
            return [], False, False
        
        if not wordlist.is_valid(guess, game.lang):
            return [], False, False
        
        # Hard mode validation
        if game.hard_mode and game.guesses:
            if not self._valid_hard_mode(guess, game.guesses[-1], game.secret):
                return [], False, False
        
        result = self._evaluate_guess(guess, game.secret)
        game.guesses.append(guess)
        game.updated_at = datetime.now().isoformat()
        
        is_win = guess == game.secret
        is_game_over = is_win or len(game.guesses) >= config.MAX_GUESSES
        
        if is_game_over:
            self._update_stats(user_id, is_win)
            if user_id in self.games:
                del self.games[user_id]
        
        self._save_games()
        return result, True, is_win

    def _valid_hard_mode(self, guess: str, last_guess: str, secret: str) -> bool:
        # Green letters must stay in same position
        for i, (g, s) in enumerate(zip(last_guess, secret)):
            if g == s and guess[i] != g:
                return False
        # Yellow letters must appear somewhere
        for i, (g, s) in enumerate(zip(last_guess, secret)):
            if g != s and g in secret:
                if g not in guess:
                    return False
        return True

    def _evaluate_guess(self, guess: str, secret: str) -> list[str]:
        result = [self.GRAY] * len(guess)
        secret_chars = list(secret)
        guess_chars = list(guess)
        
        # First pass: greens
        for i, (g, s) in enumerate(zip(guess_chars, secret_chars)):
            if g == s:
                result[i] = self.GREEN
                secret_chars[i] = None
                guess_chars[i] = None
        
        # Second pass: yellows
        for i, g in enumerate(guess_chars):
            if g is None:
                continue
            if g in secret_chars:
                result[i] = self.YELLOW
                secret_chars[secret_chars.index(g)] = None
        
        return result

    def _update_stats(self, user_id: int, won: bool):
        today = date.today().isoformat()
        stat = self.stats.get(user_id, {"streak": 0, "last_play": "", "games": 0, "wins": 0})
        stat["games"] = stat.get("games", 0) + 1
        if won:
            stat["wins"] = stat.get("wins", 0) + 1
            # Update streak
            last = stat.get("last_play", "")
            if last:
                from datetime import timedelta
                last_date = date.fromisoformat(last)
                if last_date == date.today() - timedelta(days=1):
                    stat["streak"] = stat.get("streak", 0) + 1
                elif last_date < date.today() - timedelta(days=1):
                    stat["streak"] = 1
                else:
                    stat["streak"] = stat.get("streak", 0)  # same day
            else:
                stat["streak"] = 1
        else:
            # Lost - check if streak should break
            last = stat.get("last_play", "")
            if last:
                from datetime import timedelta
                last_date = date.fromisoformat(last)
                if last_date < date.today() - timedelta(days=1):
                    stat["streak"] = 0
        stat["last_play"] = today
        self.stats[user_id] = stat
        self._save_stats()

    def get_stats(self, user_id: int) -> dict:
        return self.stats.get(user_id, {"games": 0, "wins": 0, "streak": 0, "last_play": ""})

    def get_leaderboard(self, period: str = "all", limit: int = 10) -> list[tuple[int, dict]]:
        """period: daily, weekly, all"""
        today = date.today()
        filtered = []
        for uid, stat in self.stats.items():
            if period == "daily" and stat.get("last_play") != today.isoformat():
                continue
            if period == "weekly":
                last = stat.get("last_play", "")
                if last:
                    last_date = date.fromisoformat(last)
                    if (today - last_date).days > 7:
                        continue
                else:
                    continue
            filtered.append((uid, stat))
        
        # Sort by wins desc, then streak desc, then games asc
        filtered.sort(key=lambda x: (-x[1].get("wins", 0), -x[1].get("streak", 0), x[1].get("games", 0)))
        return filtered[:limit]

    def use_hint(self, user_id: int) -> Optional[str]:
        game = self.games.get(user_id)
        if not game:
            return None
        # Reveal a random unrevealed position
        revealed = set()
        for guess in game.guesses:
            for i, (g, s) in enumerate(zip(guess, game.secret)):
                if g == s:
                    revealed.add(i)
        unrevealed = [i for i in range(len(game.secret)) if i not in revealed]
        if not unrevealed:
            return None
        pos = random.choice(unrevealed)
        return game.secret[pos]

engine = GameEngine()