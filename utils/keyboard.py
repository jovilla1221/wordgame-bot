from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import config

# Colorblind mode colors
NORMAL_COLORS = ["🟩", "🟨", "⬜"]
COLORBLIND_COLORS = ["🟦", "🟧", "⬜"]

LETTERS = [
    ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
    ["A", "S", "D", "F", "G", "H", "J", "K", "L"],
    ["⏎", "Z", "X", "C", "V", "B", "N", "M", "⌫"]
]

def get_colors(colorblind: bool) -> list[str]:
    return COLORBLIND_COLORS if colorblind else NORMAL_COLORS

def build_keyboard(game_id: str, colorblind: bool = False, 
                   revealed: dict[str, str] = None) -> InlineKeyboardMarkup:
    """Build virtual keyboard with color-coded keys"""
    colors = get_colors(colorblind)
    green, yellow, gray = colors[0], colors[1], colors[2]
    
    if revealed is None:
        revealed = {}
    
    rows = []
    for row_letters in LETTERS:
        row = []
        for letter in row_letters:
            if letter == "⏎":
                row.append(InlineKeyboardButton(
                    text="⏎",
                    callback_data=f"kb:{game_id}:enter"
                ))
            elif letter == "⌫":
                row.append(InlineKeyboardButton(
                    text="⌫",
                    callback_data=f"kb:{game_id}:backspace"
                ))
            else:
                color = revealed.get(letter, gray)
                row.append(InlineKeyboardButton(
                    text=f"{letter} {color}",
                    callback_data=f"kb:{game_id}:{letter}"
                ))
        rows.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_main_menu(user_id: int, lang: str = "id", 
                    has_active_game: bool = False) -> InlineKeyboardMarkup:
    texts = {
        "id": {
            "play": "🎮 Main",
            "mode": "⚙️ Mode",
            "lang": "🌐 Bahasa",
            "leaderboard": "🏆 Leaderboard",
            "stats": "📊 Statistik",
            "settings": "🔧 Pengaturan",
            "help": "❓ Bantuan",
            "daily": "📅 Daily Challenge",
        },
        "en": {
            "play": "🎮 Play",
            "mode": "⚙️ Mode",
            "lang": "🌐 Language",
            "leaderboard": "🏆 Leaderboard",
            "stats": "📊 Stats",
            "settings": "🔧 Settings",
            "help": "❓ Help",
            "daily": "📅 Daily Challenge",
        }
    }
    t = texts.get(lang, texts["id"])
    
    rows = []
    if has_active_game:
        rows.append([
            InlineKeyboardButton(text=t["play"], callback_data=f"menu:play:{user_id}"),
            InlineKeyboardButton(text=t["daily"], callback_data=f"menu:daily:{user_id}"),
        ])
    else:
        rows.append([
            InlineKeyboardButton(text=t["play"], callback_data=f"menu:play:{user_id}"),
            InlineKeyboardButton(text=t["daily"], callback_data=f"menu:daily:{user_id}"),
        ])
    rows.append([
        InlineKeyboardButton(text=t["mode"], callback_data=f"menu:mode:{user_id}"),
        InlineKeyboardButton(text=t["lang"], callback_data=f"menu:lang:{user_id}"),
    ])
    rows.append([
        InlineKeyboardButton(text=t["leaderboard"], callback_data=f"menu:lb:{user_id}"),
        InlineKeyboardButton(text=t["stats"], callback_data=f"menu:stats:{user_id}"),
    ])
    rows.append([
        InlineKeyboardButton(text=t["settings"], callback_data=f"menu:settings:{user_id}"),
        InlineKeyboardButton(text=t["help"], callback_data=f"menu:help:{user_id}"),
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_mode_keyboard(user_id: int, current_mode: str, current_length: int,
                        current_hard: bool, current_colorblind: bool,
                        lang: str = "id") -> InlineKeyboardMarkup:
    texts = {
        "id": {
            "solo": "Solo", "daily": "Daily", "group": "Grup",
            "length": "Panjang", "hard": "Hard Mode", "colorblind": "Colorblind",
            "back": "🔙 Kembali",
        },
        "en": {
            "solo": "Solo", "daily": "Daily", "group": "Group",
            "length": "Length", "hard": "Hard Mode", "colorblind": "Colorblind",
            "back": "🔙 Back",
        }
    }
    t = texts.get(lang, texts["id"])
    
    def mark(text: str, active: bool) -> str:
        return f"✅ {text}" if active else text
    
    rows = []
    rows.append([
        InlineKeyboardButton(text=mark(t["solo"], current_mode == "solo"), 
                           callback_data=f"mode:set:{user_id}:solo"),
        InlineKeyboardButton(text=mark(t["daily"], current_mode == "daily"), 
                           callback_data=f"mode:set:{user_id}:daily"),
        InlineKeyboardButton(text=mark(t["group"], current_mode == "group"), 
                           callback_data=f"mode:set:{user_id}:group"),
    ])
    
    for length in range(config.MIN_LENGTH, config.MAX_LENGTH + 1):
        rows.append([
            InlineKeyboardButton(text=mark(f"{length} Huruf", current_length == length),
                               callback_data=f"mode:len:{user_id}:{length}"),
        ])
    
    rows.append([
        InlineKeyboardButton(text=mark(t["hard"], current_hard),
                           callback_data=f"mode:hard:{user_id}:{int(not current_hard)}"),
        InlineKeyboardButton(text=mark(t["colorblind"], current_colorblind),
                           callback_data=f"mode:cb:{user_id}:{int(not current_colorblind)}"),
    ])
    
    rows.append([
        InlineKeyboardButton(text=t["back"], callback_data=f"mode:back:{user_id}"),
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_lang_keyboard(user_id: int, current_lang: str, lang: str = "id") -> InlineKeyboardMarkup:
    texts = {
        "id": {"id": "🇮🇩 Indonesia", "en": "🇺🇸 English", "back": "🔙 Kembali"},
        "en": {"id": "🇮🇩 Indonesia", "en": "🇺🇸 English", "back": "🔙 Back"},
    }
    t = texts.get(lang, texts["id"])
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ {t['id']}" if current_lang == "id" else t["id"],
                             callback_data=f"lang:set:{user_id}:id")],
        [InlineKeyboardButton(text=f"✅ {t['en']}" if current_lang == "en" else t["en"],
                             callback_data=f"lang:set:{user_id}:en")],
        [InlineKeyboardButton(text=t["back"], callback_data=f"lang:back:{user_id}")],
    ])

def build_settings_keyboard(user_id: int, lang: str = "id") -> InlineKeyboardMarkup:
    texts = {
        "id": {"reset": "🔄 Reset Stats", "back": "🔙 Kembali"},
        "en": {"reset": "🔄 Reset Stats", "back": "🔙 Back"},
    }
    t = texts.get(lang, texts["id"])
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["reset"], callback_data=f"settings:reset:{user_id}")],
        [InlineKeyboardButton(text=t["back"], callback_data=f"settings:back:{user_id}")],
    ])

def build_help_keyboard(user_id: int, lang: str = "id") -> InlineKeyboardMarkup:
    texts = {"id": {"back": "🔙 Kembali"}, "en": {"back": "🔙 Back"}}
    t = texts.get(lang, texts["id"])
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["back"], callback_data=f"help:back:{user_id}")],
    ])

def build_lb_keyboard(user_id: int, current_period: str, lang: str = "id") -> InlineKeyboardMarkup:
    texts = {
        "id": {"daily": "Harian", "weekly": "Mingguan", "all": "All Time", "back": "🔙 Kembali"},
        "en": {"daily": "Daily", "weekly": "Weekly", "all": "All Time", "back": "🔙 Back"},
    }
    t = texts.get(lang, texts["id"])
    
    def mark(text: str, active: bool) -> str:
        return f"✅ {text}" if active else text
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=mark(t["daily"], current_period == "daily"),
                               callback_data=f"lb:period:{user_id}:daily"),
            InlineKeyboardButton(text=mark(t["weekly"], current_period == "weekly"),
                               callback_data=f"lb:period:{user_id}:weekly"),
            InlineKeyboardButton(text=mark(t["all"], current_period == "all"),
                               callback_data=f"lb:period:{user_id}:all"),
        ],
        [InlineKeyboardButton(text=t["back"], callback_data=f"lb:back:{user_id}")],
    ])

def build_game_over_keyboard(user_id: int, won: bool, lang: str = "id") -> InlineKeyboardMarkup:
    texts = {
        "id": {"again": "🔄 Main Lagi", "share": "📤 Bagikan", "lb": "🏆 Leaderboard", "menu": "🏠 Menu"},
        "en": {"again": "🔄 Play Again", "share": "📤 Share", "lb": "🏆 Leaderboard", "menu": "🏠 Menu"},
    }
    t = texts.get(lang, texts["id"])
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t["again"], callback_data=f"game:again:{user_id}"),
            InlineKeyboardButton(text=t["share"], callback_data=f"game:share:{user_id}"),
        ],
        [
            InlineKeyboardButton(text=t["lb"], callback_data=f"game:lb:{user_id}"),
            InlineKeyboardButton(text=t["menu"], callback_data=f"game:menu:{user_id}"),
        ],
    ])