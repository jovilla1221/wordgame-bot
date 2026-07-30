from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from config import config

FORCE_SUB_CHANNEL = "@botunlverse"
FORCE_SUB_CHANNEL_ID = None  # Will be resolved at runtime

JOIN_KEYBOARD = None  # Built dynamically after channel resolution


async def resolve_channel_id(bot: Bot) -> int | str:
    """Resolve channel username to numeric ID"""
    global FORCE_SUB_CHANNEL_ID
    if FORCE_SUB_CHANNEL_ID:
        return FORCE_SUB_CHANNEL_ID
    try:
        chat = await bot.get_chat(FORCE_SUB_CHANNEL)
        FORCE_SUB_CHANNEL_ID = chat.id
        return chat.id
    except Exception as e:
        print(f"[ForceSub] Failed to resolve {FORCE_SUB_CHANNEL}: {e}")
        return FORCE_SUB_CHANNEL  # Fallback to username


async def is_subscribed(bot: Bot, user_id: int) -> bool:
    """Check if user is member of force-sub channel"""
    channel = await resolve_channel_id(bot)
    try:
        member = await bot.get_chat_member(channel, user_id)
        return member.status in {
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR,
            ChatMemberStatus.RESTRICTED,
        }
    except Exception:
        return False


def build_join_keyboard(channel_username: str = FORCE_SUB_CHANNEL):
    """Build force-sub prompt keyboard"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Join Channel", url=f"https://t.me/{channel_username.lstrip('@')}")],
        [InlineKeyboardButton(text="✅ Sudah Join", callback_data="check_sub")],
    ])


async def require_sub_message(bot: Bot, user_id: int, chat_id: int, 
                               text: str = None, lang: str = "id") -> bool:
    """
    Check subscription, send prompt if not subscribed.
    Returns True if subscribed (can proceed), False if prompt sent.
    """
    if await is_subscribed(bot, user_id):
        return True
    
    if text is None:
        texts = {
            "id": "🔒 <b>Join channel dulu untuk main!</b>\n\nKlik tombol di bawah, lalu tekan \"Sudah Join\".",
            "en": "🔒 <b>Join channel first to play!</b>\n\nClick button below, then press \"Already Joined\".",
        }
        text = texts.get(lang, texts["id"])
    
    channel = await resolve_channel_id(bot)
    kb = build_join_keyboard(channel if isinstance(channel, str) else FORCE_SUB_CHANNEL)
    
    await bot.send_message(chat_id, text, reply_markup=kb)
    return False


async def require_sub_callback(bot: Bot, callback, lang: str = "id") -> bool:
    """
    Check subscription for callback queries.
    Returns True if subscribed, False if blocked (shows alert).
    """
    if await is_subscribed(bot, callback.from_user.id):
        return True
    
    texts = {
        "id": "❌ Belum join channel! Klik \"Sudah Join\" setelah join.",
        "en": "❌ Not joined yet! Click \"Already Joined\" after joining.",
    }
    await callback.answer(texts.get(lang, texts["id"]), show_alert=True)
    return False