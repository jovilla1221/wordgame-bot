from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from config import config
from game.engine import engine, wordlist
from utils.prefs import get_lang

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


@router.message(Command("addword"))
async def cmd_addword(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Usage: /addword <id|en> <word>")
        return
    lang = parts[1].lower()
    word = parts[2].strip().upper()
    if lang not in ("id", "en"):
        await message.answer("Lang harus id atau en")
        return
    if not word.isalpha() or not (config.MIN_LENGTH <= len(word) <= config.MAX_LENGTH):
        await message.answer(f"Kata harus {config.MIN_LENGTH}-{config.MAX_LENGTH} huruf")
        return
    
    # Append to file
    path = config.WORDS_ID_FILE if lang == "id" else config.WORDS_EN_FILE
    with open(path, "a", encoding="utf-8") as f:
        f.write(word + "\n")
    
    # Reload wordlist
    wordlist._loaded = False
    wordlist.load()
    await message.answer(f"✅ Ditambah: {word} ({lang})")


@router.message(Command("delword"))
async def cmd_delword(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Usage: /delword <id|en> <word>")
        return
    lang = parts[1].lower()
    word = parts[2].strip().upper()
    
    path = config.WORDS_ID_FILE if lang == "id" else config.WORDS_EN_FILE
    if not path.exists():
        await message.answer("File wordlist tidak ada")
        return
    
    lines = path.read_text(encoding="utf-8").splitlines()
    new_lines = [l for l in lines if l.strip().upper() != word]
    if len(new_lines) == len(lines):
        await message.answer(f"Kata {word} tidak ditemukan")
        return
    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    
    wordlist._loaded = False
    wordlist.load()
    await message.answer(f"🗑️ Dihapus: {word} ({lang})")


@router.message(Command("setdaily"))
async def cmd_setdaily(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split(maxsplit=3)
    if len(parts) < 4:
        await message.answer("Usage: /setdaily <id|en> <length> <word>")
        return
    lang = parts[1].lower()
    try:
        length = int(parts[2])
    except ValueError:
        await message.answer("Length harus angka")
        return
    word = parts[3].strip().upper()
    
    if len(word) != length:
        await message.answer(f"Kata harus {length} huruf")
        return
    
    key = engine._get_daily_key(lang, length)
    engine.daily_word[key] = word
    engine._save_daily()
    await message.answer(f"✅ Daily set: {word} ({lang}/{length}) key={key}")


@router.message(Command("wordcount"))
async def cmd_wordcount(message: Message):
    if not is_admin(message.from_user.id):
        return
    wordlist.load()
    lines = ["📊 <b>Wordlist Count</b>\n"]
    for length in range(config.MIN_LENGTH, config.MAX_LENGTH + 1):
        id_count = len(wordlist._words_id.get(length, []))
        en_count = len(wordlist._words_en.get(length, []))
        lines.append(f"{length} huruf: ID={id_count} EN={en_count}")
    await message.answer("\n".join(lines))


def register_admin_handlers(dp):
    dp.include_router(router)