import os
import json
import base64
import requests
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.filters import create

API_ID = 22222258
API_HASH = "60ea076de059a85ccfd68516df08b951"
BOT_TOKEN = "7812101523:AAHk0_gwisGRD5ThBRtApTcaFT6uVt3cq_w"
ADMINS = [7213451334]

DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"tokens": {}, "banned": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump({"tokens": user_tokens, "banned": list(banned_users)}, f)

data = load_data()
user_tokens = data.get("tokens", {})
banned_users = set(data.get("banned", []))

def check_not_banned(_, __, msg):
    return msg.from_user.id not in banned_users

not_banned = create(check_not_banned)

app = Client("github_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start") & not_banned)
async def start(_, msg: Message):
    await msg.reply("👋 Welcome to GitHub Manager Bot!", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("📂 Commands", callback_data="show_commands")]
    ]))

@app.on_callback_query(filters.regex("^show_commands$"))
async def show_commands(_, cb: CallbackQuery):
    buttons = [
        [InlineKeyboardButton("🔑 Set Token", callback_data="set_token")],
        [InlineKeyboardButton("🔀 Switch Token", callback_data="switch_token")],
        [InlineKeyboardButton("📚 My Repos", callback_data="list_repos")],
        [InlineKeyboardButton("📤 Upload File", callback_data="upload_file")],
        [InlineKeyboardButton("🔎 Search User", callback_data="search_user")]
    ]
    if cb.from_user.id in ADMINS:
        buttons.extend([
            [InlineKeyboardButton("👤 Ban", callback_data="ban_user"), InlineKeyboardButton("👥 Unban", callback_data="unban_user")],
            [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
            [InlineKeyboardButton("👁 View User Repos", callback_data="admin_view_user")]
        ])
    await cb.message.edit("📘 Choose a command:", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_message(filters.command("search") & not_banned)
async def search_user(_, msg: Message):
    if len(msg.command) < 2:
        return await msg.reply("Usage: `/search username`")
    username = msg.command[1]
    res = requests.get(f"https://api.github.com/users/{username}/repos")
    if res.status_code != 200:
        return await msg.reply("❌ User not found or error fetching repos.")

    repos = res.json()
    if not repos:
        return await msg.reply("ℹ️ No public repositories found.")

    buttons = [InlineKeyboardButton(repo['name'], url=f"https://github.com/{username}/{repo['name']}/archive/refs/heads/main.zip") for repo in repos]
    reply_markup = InlineKeyboardMarkup.from_column(buttons)
    await msg.reply(f"📁 Repositories by `{username}`:", reply_markup=reply_markup)

print("✅ SPILUX GITHUB BOT ONLINE")
app.run()
