from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from game.engine import engine, wordlist
from utils.prefs import get_prefs, set_pref, get_lang
from utils.keyboard import (
    build_main_menu, build_mode_keyboard, build_lang_keyboard,
    build_settings_keyboard, build_help_keyboard, build_keyboard,
    build_lb_keyboard, build_game_over_keyboard
)
from utils.emoji_grid import format_stats, format_game_state, format_leaderboard, format_share_result, render_grid
from utils.forcesub import require_sub_message, require_sub_callback
from config import config
from dataclasses import dataclass, field

router = Router()
TYPING: dict[int, str] = {}

# ─── Group Game State ─────────────────────────────────────

@dataclass
class GroupGame:
    chat_id: int
    creator_id: int
    secret: str
    lang: str = "id"
    length: int = 5
    players: list[int] = field(default_factory=list)
    current_turn: int = 0
    finished: list[dict] = field(default_factory=list)
    guesses: int = 0
    max_guesses: int = 6

    def current_player(self) -> int:
        return self.players[self.current_turn] if self.players else None

    def next_turn(self):
        self.current_turn = (self.current_turn + 1) % len(self.players)

    def is_game_over(self) -> bool:
        return self.guesses >= self.max_guesses or any(f["won"] for f in self.finished)


GROUP_GAMES: dict[int, GroupGame] = {}
GROUP_PENDING: dict[int, list[int]] = {}

# ─── Commands ───────────────────────────────────────────────

@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    lang = get_lang(user_id)
    if not await require_sub_message(message.bot, user_id, message.chat.id, lang=lang):
        return
    texts = {
        "id": "🎮 <b>Hidden Letter Game</b>\n\nTebak kata tersembunyi dalam 6 percobaan!\n\n🟩 Huruf benar di posisi benar\n🟨 Huruf benar di posisi salah\n⬜ Huruf tidak ada\n\nPilih menu di bawah ini:",
        "en": "🎮 <b>Hidden Letter Game</b>\n\nGuess the hidden word in 6 attempts!\n\n🟩 Correct letter in correct position\n🟨 Correct letter in wrong position\n⬜ Letter not in word\n\nChoose a menu below:",
    }
    await message.answer(texts.get(lang, texts["id"]), reply_markup=build_main_menu(user_id, lang))


@router.message(Command("help"))
async def cmd_help(message: Message):
    lang = get_lang(message.from_user.id)
    if not await require_sub_message(message.bot, message.from_user.id, message.chat.id, lang=lang): return
    await _show_help(message, message.from_user.id, edit=False)


@router.message(Command("play"))
async def cmd_play(message: Message):
    lang = get_lang(message.from_user.id)
    if not await require_sub_message(message.bot, message.from_user.id, message.chat.id, lang=lang): return
    await _start_game(message.bot, message.chat.id, message.from_user.id, mode="solo")


@router.message(Command("daily"))
async def cmd_daily(message: Message):
    lang = get_lang(message.from_user.id)
    if not await require_sub_message(message.bot, message.from_user.id, message.chat.id, lang=lang): return
    await _start_game(message.bot, message.chat.id, message.from_user.id, mode="daily")


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    lang = get_lang(message.from_user.id)
    if not await require_sub_message(message.bot, message.from_user.id, message.chat.id, lang=lang): return
    await _show_stats(message, message.from_user.id, edit=False)


@router.message(Command("leaderboard"))
async def cmd_lb(message: Message):
    lang = get_lang(message.from_user.id)
    if not await require_sub_message(message.bot, message.from_user.id, message.chat.id, lang=lang): return
    await _show_leaderboard(message, message.from_user.id, period="all", edit=False)


@router.message(Command("hint"))
async def cmd_hint(message: Message):
    lang = get_lang(message.from_user.id)
    if not await require_sub_message(message.bot, message.from_user.id, message.chat.id, lang=lang): return
    await _use_hint(message, message.from_user.id)


@router.message(Command("group"))
async def cmd_group(message: Message):
    lang = get_lang(message.from_user.id)
    if not await require_sub_message(message.bot, message.from_user.id, message.chat.id, lang=lang): return
    if message.chat.type == "private":
        msg = "Command ini cuma di grup!" if lang == "id" else "This command is only for groups!"
        await message.answer(msg)
        return
    await _start_group_game(message.bot, message.chat.id, message.from_user.id)


@router.message(Command("join"))
async def cmd_join(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    lang = get_lang(user_id)
    if chat_id not in GROUP_PENDING:
        msg = "Tidak ada game grup yang menunggu. /group untuk mulai!" if lang == "id" else "No group game waiting. /group to start!"
        await message.answer(msg)
        return
    if user_id in GROUP_PENDING[chat_id]:
        msg = "Udah join!" if lang == "id" else "Already joined!"
        await message.answer(msg)
        return
    if len(GROUP_PENDING[chat_id]) >= 10:
        msg = "Game penuh (max 10)!" if lang == "id" else "Game full (max 10)!"
        await message.answer(msg)
        return
    GROUP_PENDING[chat_id].append(user_id)
    count = len(GROUP_PENDING[chat_id])
    msg = f"<code>{user_id}</code> join! ({count} pemain)" if lang == "id" else f"<code>{user_id}</code> joined! ({count} players)"
    await message.answer(msg)


@router.message(Command("startgame"))
async def cmd_startgame(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    lang = get_lang(user_id)
    if chat_id not in GROUP_PENDING:
        msg = "Tidak ada game grup yang menunggu. /group untuk mulai!" if lang == "id" else "No group game waiting. /group to start!"
        await message.answer(msg)
        return
    creator = GROUP_PENDING[chat_id][0]
    if user_id != creator:
        msg = "Cuma host yang bisa mulai game!" if lang == "id" else "Only host can start!"
        await message.answer(msg)
        return
    players = GROUP_PENDING[chat_id]
    if len(players) < 2:
        msg = "Minimal 2 pemain!" if lang == "id" else "Minimum 2 players!"
        await message.answer(msg)
        return
    prefs = get_prefs(user_id)
    secret = wordlist.get_random(prefs.get("lang", "id"), prefs.get("length", 5))
    game = GroupGame(
        chat_id=chat_id, creator_id=user_id, secret=secret,
        lang=prefs.get("lang", "id"), length=prefs.get("length", 5), players=players,
    )
    GROUP_GAMES[chat_id] = game
    del GROUP_PENDING[chat_id]
    await _send_group_turn(message.bot, chat_id)


# ─── Force-sub verify ───────────────────────────────────────

@router.callback_query(F.data == "check_sub")
async def cb_check_sub(callback: CallbackQuery):
    from utils.forcesub import is_subscribed
    user_id = callback.from_user.id
    lang = get_lang(user_id)
    if await is_subscribed(callback.bot, user_id):
        texts = {
            "id": "🎮 <b>Hidden Letter Game</b>\n\nTebak kata tersembunyi dalam 6 percobaan!\n\n🟩 Huruf benar di posisi benar\n🟨 Huruf benar di posisi salah\n⬜ Huruf tidak ada\n\nPilih menu di bawah ini:",
            "en": "🎮 <b>Hidden Letter Game</b>\n\nGuess the hidden word in 6 attempts!\n\n🟩 Correct letter in correct position\n🟨 Correct letter in wrong position\n⬜ Letter not in word\n\nChoose a menu below:",
        }
        await callback.message.edit_text(texts.get(lang, texts["id"]), reply_markup=build_main_menu(user_id, lang))
        await callback.answer("✅ OK!")
    else:
        await callback.answer("Belum join channel!" if lang == "id" else "Not joined yet!", show_alert=True)


# ─── Text guess ─────────────────────────────────────────────

@router.message(F.text.regexp(r"^[a-zA-Z]{4,6}$"))
async def handle_text_guess(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    lang = get_lang(user_id)
    if chat_id in GROUP_GAMES:
        await _process_group_guess(message, chat_id, user_id, message.text.upper())
        return
    game = engine.get_game(user_id)
    if not game:
        msg = "Tidak ada game aktif. /play dulu!" if lang == "id" else "No active game. /play first!"
        await message.answer(msg)
        return
    await _process_guess(message.bot, message.chat.id, user_id, message.text.upper())


# ─── Menu callbacks ─────────────────────────────────────────

@router.callback_query(F.data.startswith("menu:"))
async def cb_menu(callback: CallbackQuery):
    parts = callback.data.split(":")
    action = parts[1]
    user_id = int(parts[2])
    lang = get_lang(user_id)
    if callback.from_user.id != user_id:
        await callback.answer("Bukan menu kamu!" if lang == "id" else "Not your menu!", show_alert=True)
        return
    if not await require_sub_callback(callback.bot, callback, lang=lang): return
    if action == "play":
        await callback.message.delete()
        await _start_game(callback.bot, callback.message.chat.id, user_id, mode="solo")
    elif action == "daily":
        await callback.message.delete()
        await _start_game(callback.bot, callback.message.chat.id, user_id, mode="daily")
    elif action == "mode":
        await _show_mode(callback, user_id)
    elif action == "lang":
        await _show_lang(callback, user_id)
    elif action == "lb":
        await _show_leaderboard(callback, user_id, period="all", edit=True)
    elif action == "stats":
        await _show_stats(callback, user_id, edit=True)
    elif action == "settings":
        await _show_settings(callback, user_id)
    elif action == "help":
        await _show_help(callback, user_id, edit=True)
    await callback.answer()


# ─── Mode callbacks ─────────────────────────────────────────

@router.callback_query(F.data.startswith("mode:"))
async def cb_mode(callback: CallbackQuery):
    parts = callback.data.split(":")
    action = parts[1]
    user_id = int(parts[2])
    if callback.from_user.id != user_id:
        await callback.answer("Bukan menu kamu!", show_alert=True)
        return
    prefs = get_prefs(user_id)
    lang = prefs.get("lang", "id")
    if action == "set":
        mode = parts[3]
        set_pref(user_id, "mode", mode)
        await callback.answer(f"Mode: {mode}")
        await _show_mode(callback, user_id)
    elif action == "len":
        length = int(parts[3])
        set_pref(user_id, "length", length)
        await callback.answer(f"Panjang: {length}" if lang == "id" else f"Length: {length}")
        await _show_mode(callback, user_id)
    elif action == "hard":
        val = bool(int(parts[3]))
        set_pref(user_id, "hard_mode", val)
        await callback.answer(f"Hard mode: {'ON' if val else 'OFF'}")
        await _show_mode(callback, user_id)
    elif action == "cb":
        val = bool(int(parts[3]))
        set_pref(user_id, "colorblind", val)
        await callback.answer(f"Colorblind: {'ON' if val else 'OFF'}")
        await _show_mode(callback, user_id)
    elif action == "back":
        await callback.message.edit_text("🎮 <b>Hidden Letter Game</b>", reply_markup=build_main_menu(user_id, lang))
    await callback.answer()


# ─── Lang callbacks ─────────────────────────────────────────

@router.callback_query(F.data.startswith("lang:"))
async def cb_lang(callback: CallbackQuery):
    parts = callback.data.split(":")
    action = parts[1]
    user_id = int(parts[2])
    if callback.from_user.id != user_id:
        await callback.answer("Bukan menu kamu!", show_alert=True)
        return
    if action == "set":
        new_lang = parts[3]
        set_pref(user_id, "lang", new_lang)
        await callback.answer(f"OK: {new_lang.upper()}")
        await _show_lang(callback, user_id)
    elif action == "back":
        lang = get_lang(user_id)
        await callback.message.edit_text("🎮 <b>Hidden Letter Game</b>", reply_markup=build_main_menu(user_id, lang))
    await callback.answer()


# ─── Settings callbacks ─────────────────────────────────────

@router.callback_query(F.data.startswith("settings:"))
async def cb_settings(callback: CallbackQuery):
    parts = callback.data.split(":")
    action = parts[1]
    user_id = int(parts[2])
    if callback.from_user.id != user_id:
        await callback.answer("Bukan menu kamu!", show_alert=True)
        return
    lang = get_lang(user_id)
    if action == "reset":
        if user_id in engine.stats:
            del engine.stats[user_id]
            engine._save_stats()
        await callback.answer("Stats direset!" if lang == "id" else "Stats reset!", show_alert=True)
        await _show_settings(callback, user_id)
    elif action == "back":
        await callback.message.edit_text("🎮 <b>Hidden Letter Game</b>", reply_markup=build_main_menu(user_id, lang))
    await callback.answer()


# ─── Leaderboard callbacks ──────────────────────────────────

@router.callback_query(F.data.startswith("lb:"))
async def cb_lb(callback: CallbackQuery):
    parts = callback.data.split(":")
    action = parts[1]
    user_id = int(parts[2])
    if callback.from_user.id != user_id:
        await callback.answer("Bukan menu kamu!", show_alert=True)
        return
    lang = get_lang(user_id)
    if action == "period":
        period = parts[3]
        await _show_leaderboard(callback, user_id, period=period, edit=True)
    elif action == "back":
        await callback.message.edit_text("🎮 <b>Hidden Letter Game</b>", reply_markup=build_main_menu(user_id, lang))
    await callback.answer()


# ─── Game over callbacks ────────────────────────────────────

@router.callback_query(F.data.startswith("game:"))
async def cb_game(callback: CallbackQuery):
    parts = callback.data.split(":")
    action = parts[1]
    user_id = int(parts[2])
    if callback.from_user.id != user_id:
        await callback.answer("Bukan menu kamu!", show_alert=True)
        return
    lang = get_lang(user_id)
    if action == "again":
        await callback.message.delete()
        prefs = get_prefs(user_id)
        await _start_game(callback.bot, callback.message.chat.id, user_id, mode=prefs.get("mode", "solo"))
    elif action == "share":
        await callback.answer("Copy grid di atas buat share!" if lang == "id" else "Copy the grid above to share!", show_alert=True)
    elif action == "lb":
        await _show_leaderboard(callback, user_id, period="all", edit=True)
    elif action == "menu":
        await callback.message.edit_text("🎮 <b>Hidden Letter Game</b>", reply_markup=build_main_menu(user_id, lang))
    await callback.answer()


# ─── Keyboard callbacks ─────────────────────────────────────

@router.callback_query(F.data.startswith("kb:"))
async def cb_keyboard(callback: CallbackQuery):
    parts = callback.data.split(":")
    game_id = parts[1]
    action = parts[2]
    user_id = int(game_id.split(":")[0])
    if callback.from_user.id != user_id:
        await callback.answer("Bukan game kamu!" if get_lang(callback.from_user.id) == "id" else "Not your game!", show_alert=True)
        return
    game = engine.get_game(user_id)
    if not game:
        await callback.answer("Game selesai!" if get_lang(user_id) == "id" else "Game over!", show_alert=True)
        return
    current = TYPING.get(user_id, "")
    if action == "enter":
        if len(current) != game.length:
            await callback.answer(f"Butuh {game.length} huruf!" if get_lang(user_id) == "id" else f"Need {game.length} letters!", show_alert=True)
            return
        TYPING[user_id] = ""
        await _process_guess(callback.bot, callback.message.chat.id, user_id, current, edit_message=callback.message)
        await callback.answer()
        return
    elif action == "backspace":
        current = current[:-1]
        TYPING[user_id] = current
    else:
        if len(current) >= game.length:
            await callback.answer("Penuh!" if get_lang(user_id) == "id" else "Full!", show_alert=True)
            return
        current += action
        TYPING[user_id] = current
    text, revealed = format_game_state(game, get_lang(user_id))
    typing_display = current + "▢" * (game.length - len(current))
    text += f"\n\n⌨️ <code>{typing_display}</code>"
    game_id_str = f"{user_id}:{game.mode}"
    kb = build_keyboard(game_id_str, game.colorblind, revealed)
    rows = list(kb.inline_keyboard)
    rows.append([InlineKeyboardButton(text="💡 Hint", callback_data=f"hint:{user_id}")])
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    except Exception:
        pass
    await callback.answer()


# ─── Hint callback ──────────────────────────────────────────

@router.callback_query(F.data.startswith("hint:"))
async def cb_hint(callback: CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    if callback.from_user.id != user_id:
        await callback.answer("Bukan game kamu!", show_alert=True)
        return
    await _use_hint(callback, user_id)
    await callback.answer()


# ─── Help back ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("help:"))
async def cb_help(callback: CallbackQuery):
    parts = callback.data.split(":")
    action = parts[1]
    user_id = int(parts[2])
    if callback.from_user.id != user_id:
        await callback.answer("Bukan menu kamu!", show_alert=True)
        return
    lang = get_lang(user_id)
    if action == "back":
        await callback.message.edit_text("🎮 <b>Hidden Letter Game</b>", reply_markup=build_main_menu(user_id, lang))
    await callback.answer()


# ─── Internal helpers ───────────────────────────────────────

async def _start_game(bot: Bot, chat_id: int, user_id: int, mode: str = "solo"):
    prefs = get_prefs(user_id)
    lang = prefs.get("lang", "id")
    length = prefs.get("length", 5)
    hard_mode = prefs.get("hard_mode", False)
    colorblind = prefs.get("colorblind", False)
    if mode == "daily":
        stats = engine.get_stats(user_id)
        from datetime import date
        if stats.get("last_play") == date.today().isoformat():
            existing = engine.get_game(user_id)
            if existing and existing.mode == "daily":
                pass
            else:
                msg = "Sudah main Daily hari ini! Coba /play untuk solo." if lang == "id" else "Already played Daily today! Try /play for solo."
                await bot.send_message(chat_id, msg)
                return
    game = engine.new_game(user_id, chat_id, mode=mode, lang=lang, length=length, hard_mode=hard_mode, colorblind=colorblind)
    TYPING[user_id] = ""
    text, revealed = format_game_state(game, lang)
    game_id = f"{user_id}:{mode}"
    kb = build_keyboard(game_id, colorblind, revealed)
    rows = list(kb.inline_keyboard)
    rows.append([InlineKeyboardButton(text="💡 Hint", callback_data=f"hint:{user_id}")])
    await bot.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


async def _process_guess(bot: Bot, chat_id: int, user_id: int, guess: str, edit_message: Message = None):
    game = engine.get_game(user_id)
    if not game:
        return
    lang = get_lang(user_id)
    result, is_valid, is_win = engine.make_guess(user_id, guess)
    if not is_valid:
        msg = "Kata tidak valid! Coba kata lain." if lang == "id" else "Invalid word! Try another."
        if edit_message:
            await bot.send_message(chat_id, msg)
        else:
            await bot.send_message(chat_id, msg)
        return
    game_after = engine.get_game(user_id)
    is_game_over = game_after is None
    if is_game_over:
        final_guesses = game.guesses
        secret = game.secret
        colorblind = game.colorblind
        grid = render_grid(final_guesses, secret, colorblind, show_secret=not is_win)
        if is_win:
            stats = engine.get_stats(user_id)
            streak = stats.get("streak", 0)
            texts = {
                "id": f"🎉 <b>MENANG!</b> {len(final_guesses)}/6\n🔥 Streak: {streak}\n\n{grid}",
                "en": f"🎉 <b>WIN!</b> {len(final_guesses)}/6\n🔥 Streak: {streak}\n\n{grid}",
            }
        else:
            texts = {
                "id": f"😢 <b>KALAH!</b>\nKata: <b>{secret}</b>\n\n{grid}",
                "en": f"😢 <b>LOSE!</b>\nWord: <b>{secret}</b>\n\n{grid}",
            }
        text = texts.get(lang, texts["id"])
        kb = build_game_over_keyboard(user_id, is_win, lang)
        if edit_message:
            try:
                await edit_message.edit_text(text, reply_markup=kb)
            except Exception:
                await bot.send_message(chat_id, text, reply_markup=kb)
        else:
            await bot.send_message(chat_id, text, reply_markup=kb)
    else:
        text, revealed = format_game_state(game_after, lang)
        game_id = f"{user_id}:{game_after.mode}"
        kb = build_keyboard(game_id, game_after.colorblind, revealed)
        rows = list(kb.inline_keyboard)
        rows.append([InlineKeyboardButton(text="💡 Hint", callback_data=f"hint:{user_id}")])
        if edit_message:
            try:
                await edit_message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
            except Exception:
                await bot.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
        else:
            await bot.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


async def _use_hint(target, user_id: int):
    lang = get_lang(user_id)
    letter = engine.use_hint(user_id)
    if letter is None:
        msg = "Tidak ada game aktif / semua huruf sudah terbuka!" if lang == "id" else "No active game / all letters revealed!"
    else:
        msg = f"💡 Hint: huruf <b>{letter}</b> ada di kata!" if lang == "id" else f"💡 Hint: letter <b>{letter}</b> is in the word!"
    if isinstance(target, Message):
        await target.answer(msg)
    else:
        await target.message.answer(msg)


async def _show_help(target, user_id: int, edit: bool = False):
    lang = get_lang(user_id)
    texts = {
        "id": (
            "❓ <b>Bantuan</b>\n\n"
            "<b>Cara Main</b>\n1. /play untuk mulai\n2. Ketik tebakan ATAU pakai keyboard virtual\n3. Tebak dalam 6 percobaan\n\n"
            "<b>Mode</b>\n• Solo — kata acak tiap game\n• Daily — kata sama semua user, reset tiap hari\n• Grup — gantian tebak di grup\n\n"
            "<b>Fitur</b>\n🟩/🟨/⬜ feedback • 🔥 Streak • 🏆 Leaderboard • 🌐 ID/EN\n📏 4/5/6 huruf • 💪 Hard mode • 👁️ Colorblind • 💡 Hint\n\n"
            "<b>Commands</b>\n/play /daily /group /stats /leaderboard /hint /help"
        ),
        "en": (
            "❓ <b>Help</b>\n\n"
            "<b>How to Play</b>\n1. /play to start\n2. Type guess OR use virtual keyboard\n3. Guess within 6 attempts\n\n"
            "<b>Modes</b>\n• Solo — random word each game\n• Daily — same word for all, resets daily\n• Group — take turns guessing\n\n"
            "<b>Features</b>\n🟩/🟨/⬜ feedback • 🔥 Streak • 🏆 Leaderboard • 🌐 ID/EN\n📏 4/5/6 letters • 💪 Hard mode • 👁️ Colorblind • 💡 Hint\n\n"
            "<b>Commands</b>\n/play /daily /group /stats /leaderboard /hint /help"
        ),
    }
    kb = build_help_keyboard(user_id, lang)
    if edit and hasattr(target, "message"):
        await target.message.edit_text(texts.get(lang, texts["id"]), reply_markup=kb)
    elif isinstance(target, Message):
        await target.answer(texts.get(lang, texts["id"]), reply_markup=kb)
    else:
        await target.message.answer(texts.get(lang, texts["id"]), reply_markup=kb)


async def _show_stats(target, user_id: int, edit: bool = False):
    lang = get_lang(user_id)
    stats = engine.get_stats(user_id)
    text = format_stats(stats, lang)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    back_text = "🔙 Kembali" if lang == "id" else "🔙 Back"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=back_text, callback_data=f"help:back:{user_id}")]])
    if edit and hasattr(target, "message"):
        await target.message.edit_text(text, reply_markup=kb)
    elif isinstance(target, Message):
        await target.answer(text, reply_markup=kb)
    else:
        await target.message.answer(text, reply_markup=kb)


async def _show_leaderboard(target, user_id: int, period: str = "all", edit: bool = False):
    lang = get_lang(user_id)
    entries = engine.get_leaderboard(period=period)
    text = format_leaderboard(entries, period, lang)
    kb = build_lb_keyboard(user_id, period, lang)
    if edit and hasattr(target, "message"):
        await target.message.edit_text(text, reply_markup=kb)
    elif isinstance(target, Message):
        await target.answer(text, reply_markup=kb)
    else:
        await target.message.answer(text, reply_markup=kb)


async def _show_mode(callback: CallbackQuery, user_id: int):
    prefs = get_prefs(user_id)
    lang = prefs.get("lang", "id")
    texts = {"id": "⚙️ <b>Pengaturan Mode</b>\n\nPilih mode, panjang kata, hard mode, colorblind:", "en": "⚙️ <b>Mode Settings</b>\n\nSelect mode, word length, hard mode, colorblind:"}
    await callback.message.edit_text(texts.get(lang, texts["id"]), reply_markup=build_mode_keyboard(user_id, prefs.get("mode", "solo"), prefs.get("length", 5), prefs.get("hard_mode", False), prefs.get("colorblind", False), lang))


async def _show_lang(callback: CallbackQuery, user_id: int):
    prefs = get_prefs(user_id)
    lang = prefs.get("lang", "id")
    texts = {"id": "🌐 <b>Pilih Bahasa</b>", "en": "🌐 <b>Select Language</b>"}
    await callback.message.edit_text(texts.get(lang, texts["id"]), reply_markup=build_lang_keyboard(user_id, lang, lang))


async def _show_settings(callback: CallbackQuery, user_id: int):
    lang = get_lang(user_id)
    texts = {"id": "🔧 <b>Pengaturan</b>\n\nReset statistik game:", "en": "🔧 <b>Settings</b>\n\nReset game statistics:"}
    await callback.message.edit_text(texts.get(lang, texts["id"]), reply_markup=build_settings_keyboard(user_id, lang))


# ─── Group Game Functions ────────────────────────────────────

async def _start_group_game(bot: Bot, chat_id: int, user_id: int):
    lang = get_lang(user_id)
    GROUP_PENDING[chat_id] = [user_id]
    if chat_id in GROUP_GAMES:
        del GROUP_GAMES[chat_id]
    texts = {
        "id": f"🎮 <b>Game Grup Dimulai!</b>\n\nHost: <code>{user_id}</code>\nPemain lain ketik /join untuk ikut!\nHost ketik /startgame untuk mulai\n\nMinimum 2 pemain, maks 10 pemain.",
        "en": f"🎮 <b>Group Game Started!</b>\n\nHost: <code>{user_id}</code>\nOther players type /join to join!\nHost type /startgame to begin\n\nMinimum 2 players, max 10 players.",
    }
    await bot.send_message(chat_id, texts.get(lang, texts["id"]))


async def _send_group_turn(bot: Bot, chat_id: int):
    game = GROUP_GAMES[chat_id]
    player = game.current_player()
    lang = game.lang
    grid_guesses = []
    for f in game.finished:
        grid_guesses.extend(f["guesses"])
    grid_text = ""
    if grid_guesses:
        grid_text = render_grid(grid_guesses, game.secret, False, False) + "\n"
    texts = {
        "id": f"🎮 <b>Game Grup</b> | Giliran: <code>{player}</code>\nTebakan: {game.guesses}/{game.max_guesses}\n\n{grid_text}Ketik tebakan {game.length} huruf!",
        "en": f"🎮 <b>Group Game</b> | Turn: <code>{player}</code>\nGuesses: {game.guesses}/{game.max_guesses}\n\n{grid_text}Type your {game.length}-letter guess!",
    }
    await bot.send_message(chat_id, texts.get(lang, texts["id"]))


async def _process_group_guess(message: Message, chat_id: int, user_id: int, guess: str):
    game = GROUP_GAMES.get(chat_id)
    if not game:
        return
    lang = game.lang
    if user_id != game.current_player():
        msg = "Bukan giliran kamu!" if lang == "id" else "Not your turn!"
        await message.answer(msg)
        return
    if not wordlist.is_valid(guess, game.lang):
        msg = "Kata tidak valid!" if lang == "id" else "Invalid word!"
        await message.answer(msg)
        return
    game.guesses += 1
    won = guess == game.secret
    game.finished.append({"user_id": user_id, "guesses": [guess], "won": won, "attempt": game.guesses})
    grid = render_grid([guess], game.secret, False, False)
    if won:
        texts = {
            "id": f"🎉 <code>{user_id}</code> MENANG! Tebak {game.guesses}/{game.max_guesses}!\nKata: <b>{game.secret}</b>\n\n{grid}",
            "en": f"🎉 <code>{user_id}</code> WON! Guess {game.guesses}/{game.max_guesses}!\nWord: <b>{game.secret}</b>\n\n{grid}",
        }
        await message.answer(texts.get(lang, texts["id"]))
        if user_id not in engine.stats:
            engine.stats[user_id] = {"games": 0, "wins": 0, "streak": 0, "last_play": "", "best_streak": 0}
        engine.stats[user_id]["games"] = engine.stats[user_id].get("games", 0) + 1
        engine.stats[user_id]["wins"] = engine.stats[user_id].get("wins", 0) + 1
        engine._save_stats()
        del GROUP_GAMES[chat_id]
    elif game.guesses >= game.max_guesses:
        texts = {
            "id": f"😢 Game Over! Kata: <b>{game.secret}</b>\n\n{grid}",
            "en": f"😢 Game Over! Word: <b>{game.secret}</b>\n\n{grid}",
        }
        await message.answer(texts.get(lang, texts["id"]))
        del GROUP_GAMES[chat_id]
    else:
        msg = f"<code>{user_id}</code> menebak:\n{grid}"
        await message.answer(msg)
        game.next_turn()
        await _send_group_turn(message.bot, chat_id)


def register_common_handlers(dp):
    dp.include_router(router)
