
import logging
import os
import json
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1

API_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
DATA_FILE = "songs.json"
ADMIN_ID = 1918624551

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    await message.reply("👋 Welcome to Squonk Radio V0.4.7!\nUse /setup to link your group.")

@dp.message_handler(commands=["setup"])
async def cmd_setup(message: types.Message):
    if message.chat.type != "private" or message.from_user.id != ADMIN_ID:
        return await message.reply("⛔ Only the admin can use this command in private.")
    await message.reply("📫 Send me `GroupID: <your_group_id>` to register a group.")

@dp.message_handler(lambda msg: msg.text and msg.text.startswith("GroupID:"))
async def handle_group_id(message: types.Message):
    if message.chat.type != "private" or message.from_user.id != ADMIN_ID:
        return
    group_id = message.text.split("GroupID:")[-1].strip()
    data = load_data()
    data[group_id] = []
    save_data(data)
    await message.reply(f"✅ Group ID `{group_id}` registered. Now send me .mp3 files!")

@dp.message_handler(content_types=types.ContentType.DOCUMENT)
async def handle_document(message: types.Message):
    if message.chat.type != "private" or message.from_user.id != ADMIN_ID:
        return
    document = message.document
    if not document.file_name.endswith(".mp3"):
        return await message.reply("⛔ Only .mp3 files are allowed.")
    group_ids = load_data().keys()
    if not group_ids:
        return await message.reply("❗Please first send `GroupID: <your_group_id>`")
    file = await document.download(destination_dir=".")
    audio = MP3(file.name)
    tags = ID3(file.name)
    title = tags.get("TIT2", TIT2(encoding=3, text=document.file_name)).text[0]
    artist = tags.get("TPE1", TPE1(encoding=3, text="Unknown")).text[0]
    data = load_data()
    for gid in group_ids:
        data[gid].append({"file": file.name, "title": title, "artist": artist})
    save_data(data)
    await message.reply(f"✅ Saved `{title}` by `{artist}`.")

@dp.message_handler(commands=["playlist"])
async def cmd_playlist(message: types.Message):
    gid = str(message.chat.id)
    data = load_data()
    if gid not in data or not data[gid]:
        return await message.reply("🪫 Playlist is empty.")
    text = "🎵 Playlist:\n" + "\n".join(f"{i+1}. {s['title']} – {s['artist']}" for i, s in enumerate(data[gid]))
    await message.reply(text)

@dp.message_handler(commands=["play"])
async def cmd_play(message: types.Message):
    gid = str(message.chat.id)
    data = load_data()
    if gid not in data or not data[gid]:
        return await message.reply("❌ No songs found for this group.")
    song = data[gid][0]
    buttons = InlineKeyboardMarkup().add(
        InlineKeyboardButton("▶️ Next", callback_data="next"),
        InlineKeyboardButton("📃 Playlist", callback_data="playlist")
    )
    await bot.send_audio(message.chat.id, audio=open(song["file"], "rb"), caption="🎶 Squonking time!", reply_markup=buttons)

@dp.callback_query_handler(lambda c: c.data in ["next", "playlist"])
async def callbacks(call: types.CallbackQuery):
    gid = str(call.message.chat.id)
    data = load_data()
    if gid not in data or not data[gid]:
        return await call.answer("🪫 No songs found.")
    if call.data == "playlist":
        text = "🎵 Playlist:\n" + "\n".join(f"{i+1}. {s['title']} – {s['artist']}" for i, s in enumerate(data[gid]))
        await call.message.reply(text)
    elif call.data == "next":
        data[gid].append(data[gid].pop(0))
        save_data(data)
        await cmd_play(call.message)

from aiogram import executor
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)
