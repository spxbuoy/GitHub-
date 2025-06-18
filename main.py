import os
import json
import requests
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.filters import create
from datetime import datetime

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
        [InlineKeyboardButton("➕ Create Repo", callback_data="create_repo")],
        [InlineKeyboardButton("📤 Upload File", callback_data="upload_file")],
        [InlineKeyboardButton("🔎 Search User", callback_data="search_user")],
        [InlineKeyboardButton("🏓 Ping", callback_data="ping")]
    ]
    if cb.from_user.id in ADMINS:
        buttons.extend([
            [InlineKeyboardButton("👤 Ban", callback_data="ban_user"), InlineKeyboardButton("👥 Unban", callback_data="unban_user")],
            [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
            [InlineKeyboardButton("👁 View User Repos", callback_data="admin_view_user")]
        ])
    await cb.message.edit("📘 Choose a command:", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex("^ping$"))
async def ping(_, cb: CallbackQuery):
    await cb.answer("✅ Pong! Fast.", show_alert=True)

@app.on_callback_query(filters.regex("^set_token$"))
async def ask_token(_, cb: CallbackQuery):
    await cb.message.edit("✍️ Please send your GitHub token now...")
    user_id = cb.from_user.id

    @app.on_message(filters.private & filters.text & filters.user(user_id))
    async def receive_token(_, msg: Message):
        token = msg.text.strip()
        headers = {"Authorization": f"token {token}"}
        r = requests.get("https://api.github.com/user", headers=headers)

        if r.status_code != 200:
            await msg.reply("❌ Invalid token.")
            return

        username = r.json().get("login")
        uid = str(user_id)
        user_tokens.setdefault(uid, {})
        user_tokens[uid][token] = {"username": username}
        user_tokens[uid]["active"] = token
        save_data()

        await msg.reply(f"✅ Token saved for `{username}`")

@app.on_callback_query(filters.regex("^switch_token$"))
async def switch_token(_, cb: CallbackQuery):
    uid = str(cb.from_user.id)
    tokens = user_tokens.get(uid, {})
    if not tokens:
        return await cb.message.edit("❌ No tokens found.")
    buttons = [InlineKeyboardButton(t[:6]+"...", callback_data=f"do_switch:{t}") for t in tokens if t != "active"]
    await cb.message.edit("🔄 Choose a token:", reply_markup=InlineKeyboardMarkup.from_column(buttons))

@app.on_callback_query(filters.regex("^do_switch:"))
async def do_switch(_, cb: CallbackQuery):
    token = cb.data.split(":", 1)[1]
    user_tokens[str(cb.from_user.id)]["active"] = token
    save_data()
    await cb.answer("✅ Switched!", show_alert=True)

@app.on_callback_query(filters.regex("^list_repos$"))
async def list_repos_cb(_, cb: CallbackQuery):
    uid = str(cb.from_user.id)
    token = user_tokens.get(uid, {}).get("active")
    if not token:
        return await cb.message.edit("❌ Set your token first.")
    headers = {"Authorization": f"token {token}"}
    res = requests.get("https://api.github.com/user/repos", headers=headers)
    if res.status_code != 200:
        return await cb.message.edit("❌ Failed to get repos.")
    repos = res.json()
    username = requests.get("https://api.github.com/user", headers=headers).json().get("login")
    buttons = [InlineKeyboardButton(r["name"], url=f"https://github.com/{username}/{r['name']}/archive/refs/heads/main.zip") for r in repos]
    await cb.message.edit("📦 Your Repos:", reply_markup=InlineKeyboardMarkup.from_column(buttons))

@app.on_callback_query(filters.regex("^search_user$"))
async def search_user_cb(_, cb: CallbackQuery):
    await cb.message.edit("🔎 Send the username to search:")

    @app.on_message(filters.private & filters.text & filters.user(cb.from_user.id))
    async def receive_username(_, msg: Message):
        username = msg.text.strip()
        res = requests.get(f"https://api.github.com/users/{username}/repos")
        if res.status_code != 200:
            return await msg.reply("❌ User not found.")
        repos = res.json()
        buttons = [InlineKeyboardButton(repo['name'], url=f"https://github.com/{username}/{repo['name']}/archive/refs/heads/main.zip") for repo in repos]
        await msg.reply(f"📁 Repositories by `{username}`:", reply_markup=InlineKeyboardMarkup.from_column(buttons))

@app.on_callback_query(filters.regex("^create_repo$"))
async def create_repo_cb(_, cb: CallbackQuery):
    await cb.message.edit("📦 Send the name of the repository to create:")

    @app.on_message(filters.private & filters.text & filters.user(cb.from_user.id))
    async def receive_repo_name(_, msg: Message):
        repo_name = msg.text.strip()
        token = user_tokens.get(str(msg.from_user.id), {}).get("active")
        if not token:
            return await msg.reply("❌ No token found.")
        headers = {"Authorization": f"token {token}"}
        res = requests.post("https://api.github.com/user/repos", headers=headers, json={"name": repo_name})
        if res.status_code == 201:
            await msg.reply(f"✅ Repo `{repo_name}` created!")
        else:
            await msg.reply("❌ Failed to create repo.")

print("✅ SPILUX GITHUB BOT ONLINE")
app.run()
