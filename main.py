import os
import json
import base64
import requests
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from pyrogram.filters import create

# Credentials
API_ID = 22222258
API_HASH = "60ea076de059a85ccfd68516df08b951"
BOT_TOKEN = "7812101523:AAHk0_gwisGRD5ThBRtApTcaFT6uVt3cq_w"
ADMINS = [7213451334]

# Data file
DATA_FILE = "data.json"

# Load/save data
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

# Not banned filter
def check_not_banned(_, __, msg):
    return msg.from_user.id not in banned_users

not_banned = create(check_not_banned)

# Pyrogram client
app = Client("github_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Utility to get active token
def get_active_token(user_id):
    tokens = user_tokens.get(str(user_id), {})
    active = tokens.get("active")
    return active if active else (next(iter(t for t in tokens if t != "active"), None))

# /start
@app.on_message(filters.command("start") & not_banned)
async def start(_, msg: Message):
    await msg.reply(
        "**👋 Welcome to GitHub Manager Bot!**",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📌 Set Token", callback_data="settoken")],
            [InlineKeyboardButton("🔄 Switch Token", callback_data="switch")],
            [InlineKeyboardButton("📦 Create Repo", callback_data="create")],
            [InlineKeyboardButton("🗑️ Delete Repo", callback_data="delete")],
            [InlineKeyboardButton("🧾 List Repos", callback_data="repos")]
        ])
    )

# Handle button interactions
@app.on_callback_query()
async def handle_buttons(_, cb):
    user_id = str(cb.from_user.id)

    if cb.data == "settoken":
        await cb.message.reply("🔑 Send your GitHub token:", reply_markup=ForceReply())

    elif cb.data == "create":
        await cb.message.reply("🆕 Send the name of the repository to create:", reply_markup=ForceReply())

    elif cb.data == "delete":
        await cb.message.reply("🗑️ Send the name of the repository to delete:", reply_markup=ForceReply())

    elif cb.data == "switch":
        tokens = user_tokens.get(user_id, {})
        if not tokens:
            return await cb.message.reply("❌ No tokens saved yet.")
        buttons = [InlineKeyboardButton(t[:8] + "...", callback_data=f"switch:{t}") for t in tokens if t != "active"]
        await cb.message.reply("🔄 Choose a token:", reply_markup=InlineKeyboardMarkup.from_column(buttons))

    elif cb.data == "repos":
        token = get_active_token(cb.from_user.id)
        if not token:
            return await cb.message.reply("❌ Set your token first.")
        headers = {"Authorization": f"token {token}"}
        res = requests.get("https://api.github.com/user/repos", headers=headers)
        if res.status_code != 200:
            return await cb.message.reply("❌ Failed to fetch repos.")
        repos = res.json()
        if not repos:
            return await cb.message.reply("📂 No repositories found.")
        buttons = [InlineKeyboardButton(r["name"], callback_data=f"dl:{r['name']}") for r in repos]
        await cb.message.reply("📦 Your repositories:", reply_markup=InlineKeyboardMarkup.from_column(buttons))

    elif cb.data.startswith("switch:"):
        token = cb.data.split(":", 1)[1]
        user_tokens[user_id]["active"] = token
        save_data()
        await cb.message.edit("✅ Switched token.")

    elif cb.data.startswith("dl:"):
        repo_name = cb.data.split(":", 1)[1]
        token = get_active_token(cb.from_user.id)
        headers = {"Authorization": f"token {token}"}
        username = requests.get("https://api.github.com/user", headers=headers).json().get("login")
        zip_url = f"https://github.com/{username}/{repo_name}/archive/refs/heads/main.zip"
        try:
            file = requests.get(zip_url)
            with open("repo.zip", "wb") as f:
                f.write(file.content)
            await cb.message.reply_document("repo.zip", caption=f"📦 `{repo_name}` repo ZIP")
            os.remove("repo.zip")
        except:
            await cb.message.reply("❌ Could not download repo.")

# Listen for replies from ForceReply
@app.on_message(filters.reply & not_banned)
async def handle_reply(_, msg: Message):
    user_id = str(msg.from_user.id)
    previous = msg.reply_to_message.text

    if "token" in previous.lower():
        token = msg.text.strip()
        user_tokens.setdefault(user_id, {})
        user_tokens[user_id][token] = {}
        user_tokens[user_id]["active"] = token
        save_data()
        await msg.reply("✅ Token saved and activated.")

    elif "create" in previous.lower():
        token = get_active_token(user_id)
        if not token:
            return await msg.reply("❌ Set your token first.")
        headers = {"Authorization": f"token {token}"}
        data = {"name": msg.text.strip(), "auto_init": True}
        res = requests.post("https://api.github.com/user/repos", json=data, headers=headers)
        if res.status_code == 201:
            await msg.reply("✅ Repository created!")
        else:
            await msg.reply("❌ Failed to create repository.")

    elif "delete" in previous.lower():
        token = get_active_token(user_id)
        if not token:
            return await msg.reply("❌ Set your token first.")
        headers = {"Authorization": f"token {token}"}
        username = requests.get("https://api.github.com/user", headers=headers).json().get("login")
        repo = msg.text.strip()
        res = requests.delete(f"https://api.github.com/repos/{username}/{repo}", headers=headers)
        if res.status_code == 204:
            await msg.reply("🗑️ Repository deleted.")
        else:
            await msg.reply("❌ Failed to delete repository.")

# Start bot
print("✅ SPILUX GITHUB BOT ONLINE")
app.run()
