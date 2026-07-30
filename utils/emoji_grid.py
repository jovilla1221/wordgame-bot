from game.engine import engine, GameEngine

def render_grid(guesses: list[str], secret: str, colorblind: bool = False, 
                show_secret: bool = False) -> str:
    """Render emoji grid for guesses"""
    GREEN = "🟦" if colorblind else "🟩"
    YELLOW = "🟧" if colorblind else "🟨"
    GRAY = "⬜"
    
    lines = []
    for guess in guesses:
        result = []
        secret_chars = list(secret)
        guess_chars = list(guess)
        
        # First pass: greens
        for i, (g, s) in enumerate(zip(guess_chars, secret_chars)):
            if g == s:
                result.append(GREEN)
                secret_chars[i] = None
                guess_chars[i] = None
            else:
                result.append(None)
        
        # Second pass: yellows/grays
        for i, g in enumerate(guess_chars):
            if g is None:
                continue
            if g in secret_chars:
                result[i] = YELLOW
                secret_chars[secret_chars.index(g)] = None
            else:
                result[i] = GRAY
        
        lines.append("".join(result))
    
    # Add empty rows for remaining guesses
    max_guesses = 6
    for _ in range(len(guesses), max_guesses):
        lines.append(GRAY * len(secret))
    
    if show_secret:
        lines.append(f"\nKata: {secret}")
    
    return "\n".join(lines)

def format_stats(stats: dict, lang: str = "id") -> str:
    texts = {
        "id": {
            "games": "Permainan", "wins": "Menang", "winrate": "Winrate",
            "streak": "Streak", "best_streak": "Best Streak", "last_play": "Main Terakhir"
        },
        "en": {
            "games": "Games", "wins": "Wins", "winrate": "Winrate",
            "streak": "Streak", "best_streak": "Best Streak", "last_play": "Last Played"
        }
    }
    t = texts.get(lang, texts["id"])
    
    games = stats.get("games", 0)
    wins = stats.get("wins", 0)
    winrate = (wins / games * 100) if games > 0 else 0
    streak = stats.get("streak", 0)
    best_streak = stats.get("best_streak", 0)
    last_play = stats.get("last_play", "-")
    
    return (
        f"📊 <b>{t['games']}</b>: {games}\n"
        f"🏆 <b>{t['wins']}</b>: {wins}\n"
        f"📈 <b>{t['winrate']}</b>: {winrate:.1f}%\n"
        f"🔥 <b>{t['streak']}</b>: {streak}\n"
        f"⭐ <b>{t['best_streak']}</b>: {best_streak}\n"
        f"📅 <b>{t['last_play']}</b>: {last_play}"
    )

def format_leaderboard(entries: list[tuple[int, dict]], period: str, 
                       lang: str = "id", bot_username: str = "") -> str:
    texts = {
        "id": {"daily": "Harian", "weekly": "Mingguan", "all": "All Time",
               "rank": "Rank", "user": "User", "wins": "Win", "streak": "Streak"},
        "en": {"daily": "Daily", "weekly": "Weekly", "all": "All Time",
               "rank": "Rank", "user": "User", "wins": "Win", "streak": "Streak"},
    }
    t = texts.get(lang, texts["id"])
    
    period_name = t.get(period, period)
    lines = [f"🏆 <b>Leaderboard {period_name}</b>\n"]
    
    if not entries:
        lines.append("Belum ada data" if lang == "id" else "No data yet")
        return "\n".join(lines)
    
    for i, (uid, stat) in enumerate(entries, 1):
        wins = stat.get("wins", 0)
        streak = stat.get("streak", 0)
        # Can't get username from ID alone, show ID
        lines.append(f"{i}. <code>{uid}</code> — 🏆{wins} 🔥{streak}")
    
    return "\n".join(lines)

def format_game_state(game, lang: str = "id", show_keyboard: bool = True) -> tuple[str, dict]:
    """Format current game state for display. Returns (text, revealed_dict)"""
    texts = {
        "id": {"guess": "Tebakan", "attempts": "Percobaan", "hint": "Hint"},
        "en": {"guess": "Guess", "attempts": "Attempts", "hint": "Hint"},
    }
    t = texts.get(lang, texts["id"])
    
    grid = render_grid(game.guesses, game.secret, game.colorblind)
    
    # Build revealed letters dict for keyboard
    revealed = {}
    for guess in game.guesses:
        secret_chars = list(game.secret)
        guess_chars = list(guess)
        
        # First pass: greens
        for i, (g, s) in enumerate(zip(guess_chars, secret_chars)):
            if g == s:
                revealed[g] = "🟦" if game.colorblind else "🟩"
                secret_chars[i] = None
                guess_chars[i] = None
        
        # Second pass: yellows
        for i, g in enumerate(guess_chars):
            if g is None:
                continue
            if g in secret_chars:
                if revealed.get(g) != ("🟦" if game.colorblind else "🟩"):
                    revealed[g] = "🟧" if game.colorblind else "🟨"
                secret_chars[secret_chars.index(g)] = None
            elif g not in revealed:
                revealed[g] = "⬜"
    
    text = (
        f"🎯 <b>{t['guess']}</b> ({len(game.secret)} huruf)\n"
        f"{grid}\n"
        f"{t['attempts']}: {len(game.guesses)}/{6}"
    )
    
    if game.mode == "daily":
        text = f"📅 <b>Daily Challenge</b>\n" + text
    
    return text, revealed

def format_share_result(game, lang: str = "id") -> str:
    """Format result for sharing"""
    texts = {
        "id": {"wordle": "Wordle", "guess": "Tebakan", "share": "Bagikan hasilmu!"},
        "en": {"wordle": "Wordle", "guess": "Guess", "share": "Share your result!"},
    }
    t = texts.get(lang, texts["id"])
    
    grid = render_grid(game.guesses, game.secret, game.colorblind)
    result = "MENANG! 🎉" if game.guesses[-1] == game.secret else "KALAH 😢"
    
    return (
        f"{t['wordle']} {len(game.secret)} huruf {result}\n"
        f"{t['guess']}: {len(game.guesses)}/6\n\n"
        f"{grid}\n\n"
        f"{t['share']}"
    )