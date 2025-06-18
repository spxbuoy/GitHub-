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
    await msg.reply(
        "👋 *Welcome to GitHub Manager Bot!*\n\nUse the button below to access commands:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 Commands", callback_data="open_commands")]
        ])
    )

@app.on_callback_query(filters.regex("^open_commands"))
async def command_buttons(_, cb: CallbackQuery):
    await cb.message.edit_text(
        "🔧 *Select a GitHub Action:*",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Create Repo", callback_data="create_repo")],
            [InlineKeyboardButton("🗑️ Delete Repo", callback_data="delete_repo")],
            [InlineKeyboardButton("📦 My Repos", callback_data="list_repos")],
            [InlineKeyboardButton("💾 Set Token", callback_data="set_token")],
            [InlineKeyboardButton("🔁 Switch Token", callback_data="switch_account")],
            [InlineKeyboardButton("📥 Download Repo", callback_data="download_repo")],
            [InlineKeyboardButton("⬆ Upload File", callback_data="upload_file")],
            [InlineKeyboardButton("📃 View Issues", callback_data="view_issues")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_home")]
        ])
    )

@app.on_callback_query(filters.regex("^back_to_home"))
async def go_back(_, cb: CallbackQuery):
    await start(_, cb.message)

@app.on_callback_query(filters.regex("^create_repo"))
async def ask_repo_name(_, cb: CallbackQuery):
    await cb.message.edit_text("📝 Send the name of the repository to create.")
    msg = await app.listen(cb.message.chat.id)
    repo_name = msg.text.strip()
    token = get_active_token(cb.from_user.id)
    if not token:
        return await cb.message.reply("❌ Use /settoken first.")
    headers = {"Authorization": f"token {token}"}
    res = requests.post("https://api.github.com/user/repos", json={"name": repo_name}, headers=headers)
    if res.status_code == 201:
        await msg.reply(f"✅ Repository `{repo_name}` created!")
    else:
        await msg.reply("❌ Failed to create repository.")

@app.on_callback_query(filters.regex("^delete_repo"))
async def prompt_delete(_, cb: CallbackQuery):
    token = get_active_token(cb.from_user.id)
    if not token:
        return await cb.message.reply("❌ Use /settoken first.")
    headers = {"Authorization": f"token {token}"}
    username = requests.get("https://api.github.com/user", headers=headers).json().get("login")
    repos = requests.get("https://api.github.com/user/repos", headers=headers).json()
    btns = [[InlineKeyboardButton(repo['name'], callback_data=f"del:{repo['name']}")] for repo in repos]
    await cb.message.edit("Select repo to delete:", reply_markup=InlineKeyboardMarkup(btns))

@app.on_callback_query(filters.regex("^del:"))
async def confirm_delete(_, cb: CallbackQuery):
    repo = cb.data.split(":")[1]
    token = get_active_token(cb.from_user.id)
    headers = {"Authorization": f"token {token}"}
    username = requests.get("https://api.github.com/user", headers=headers).json().get("login")
    res = requests.delete(f"https://api.github.com/repos/{username}/{repo}", headers=headers)
    if res.status_code == 204:
        await cb.message.edit(f"🗑️ Repository `{repo}` deleted.")
    else:
        await cb.message.edit("❌ Failed to delete repository.")

@app.on_callback_query(filters.regex("^list_repos"))
async def show_repos(_, cb: CallbackQuery):
    token = get_active_token(cb.from_user.id)
    if not token:
        return await cb.message.reply("❌ Use /settoken first.")
    headers = {"Authorization": f"token {token}"}
    repos = requests.get("https://api.github.com/user/repos", headers=headers).json()
    btns = [[InlineKeyboardButton(r['name'], callback_data=f"dl:{r['name']}")] for r in repos]
    await cb.message.edit("📦 Your Repositories:", reply_markup=InlineKeyboardMarkup(btns))

@app.on_callback_query(filters.regex("^dl:"))
async def send_zip(_, cb: CallbackQuery):
    repo = cb.data.split(":")[1]
    token = get_active_token(cb.from_user.id)
    headers = {"Authorization": f"token {token}"}
    username = requests.get("https://api.github.com/user", headers=headers).json().get("login")
    zip_url = f"https://github.com/{username}/{repo}/archive/refs/heads/main.zip"
    file = requests.get(zip_url)
    with open("repo.zip", "wb") as f:
        f.write(file.content)
    await cb.message.reply_document("repo.zip", caption=f"📦 {repo} repo ZIP")
    os.remove("repo.zip")

@app.on_callback_query(filters.regex("^set_token"))
async def ask_token(_, cb: CallbackQuery):
    await cb.message.edit("🔐 Send your GitHub token:")
    msg = await app.listen(cb.message.chat.id)
    user_id = str(cb.from_user.id)
    user_tokens.setdefault(user_id, {})
    token = msg.text.strip()
    user_tokens[user_id][token] = {}
    user_tokens[user_id]["active"] = token
    save_data()
    await msg.reply("✅ Token saved and activated!")

@app.on_callback_query(filters.regex("^switch_account"))
async def switch_account(_, cb: CallbackQuery):
    user_id = str(cb.from_user.id)
    tokens = user_tokens.get(user_id, {})
    buttons = [InlineKeyboardButton(t[:8]+"...", callback_data=f"switch:{t}") for t in tokens if t != "active"]
    await cb.message.edit("🔁 Choose token:", reply_markup=InlineKeyboardMarkup.from_column(buttons))

@app.on_callback_query(filters.regex("^switch:"))
async def switch_token_cb(_, cb: CallbackQuery):
    token = cb.data.split(":")[1]
    user_tokens[str(cb.from_user.id)]["active"] = token
    save_data()
    await cb.message.edit("✅ Switched account!")

def get_active_token(user_id):
    tokens = user_tokens.get(str(user_id), {})
    active = tokens.get("active")
    return active if active else (next(iter(t for t in tokens if t != "active"), None))

print("✅ SPILUX GITHUB BOT ONLINE")
app.run()
