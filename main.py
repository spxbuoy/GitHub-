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
        "**👋 Welcome to GitHub Manager Bot!**",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 Commands", callback_data="commands")]
        ])
    )

@app.on_callback_query()
async def button_handler(_, cb: CallbackQuery):
    user_id = str(cb.from_user.id)

    if cb.data == "commands":
        await cb.message.edit(
            "**Choose a command below:**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Set Token", callback_data="settoken")],
                [InlineKeyboardButton("🔁 Switch Token", callback_data="switch")],
                [InlineKeyboardButton("📦 List Repositories", callback_data="repos")],
                [InlineKeyboardButton("🆕 Create Repository", callback_data="create")],
                [InlineKeyboardButton("🗑️ Delete Repository", callback_data="delete")]
            ])
        )

    elif cb.data == "settoken":
        await cb.message.edit("Send me your GitHub token:")
        token_msg = await app.listen(cb.message.chat.id)
        token = token_msg.text.strip()
        user_tokens.setdefault(user_id, {})
        user_tokens[user_id][token] = {}
        user_tokens[user_id]["active"] = token
        save_data()
        await cb.message.reply("✅ Token saved and activated!")

    elif cb.data == "switch":
        tokens = user_tokens.get(user_id, {})
        if not tokens:
            return await cb.message.edit("❌ No tokens saved.")
        buttons = [InlineKeyboardButton(t[:8] + "...", callback_data=f"switchtoken:{t}") for t in tokens if t != "active"]
        await cb.message.edit("🔁 Choose token:", reply_markup=InlineKeyboardMarkup.from_column(buttons))

    elif cb.data.startswith("switchtoken:"):
        token = cb.data.split(":", 1)[1]
        user_tokens[user_id]["active"] = token
        save_data()
        await cb.message.edit("✅ Token switched.")

    elif cb.data == "create":
        await cb.message.edit("Send the name for the new repository:")
        name_msg = await app.listen(cb.message.chat.id)
        repo_name = name_msg.text.strip()
        token = get_active_token(cb.from_user.id)
        if not token:
            return await cb.message.reply("❌ Set your token first.")
        headers = {"Authorization": f"token {token}"}
        res = requests.post("https://api.github.com/user/repos", json={"name": repo_name, "auto_init": True}, headers=headers)
        if res.status_code == 201:
            await cb.message.reply(f"✅ Repository `{repo_name}` created.")
        else:
            await cb.message.reply("❌ Failed to create repository.")

    elif cb.data == "delete":
        await cb.message.edit("Send the name of the repository to delete:")
        name_msg = await app.listen(cb.message.chat.id)
        repo_name = name_msg.text.strip()
        token = get_active_token(cb.from_user.id)
        if not token:
            return await cb.message.reply("❌ Set your token first.")
        headers = {"Authorization": f"token {token}"}
        username = requests.get("https://api.github.com/user", headers=headers).json().get("login")
        res = requests.delete(f"https://api.github.com/repos/{username}/{repo_name}", headers=headers)
        if res.status_code == 204:
            await cb.message.reply("🗑️ Repository deleted.")
        else:
            await cb.message.reply("❌ Failed to delete repository.")

    elif cb.data == "repos":
        token = get_active_token(cb.from_user.id)
        if not token:
            return await cb.message.reply("❌ Set your token first.")
        headers = {"Authorization": f"token {token}"}
        res = requests.get("https://api.github.com/user/repos", headers=headers)
        if res.status_code != 200:
            return await cb.message.reply("❌ Failed to fetch repositories.")
        repos = [r["name"] for r in res.json()]
        buttons = [InlineKeyboardButton(r, callback_data=f"download:{r}") for r in repos]
        await cb.message.edit("📦 Choose a repository to download:", reply_markup=InlineKeyboardMarkup.from_column(buttons))

    elif cb.data.startswith("download:"):
        repo_name = cb.data.split(":", 1)[1]
        token = get_active_token(cb.from_user.id)
        if not token:
            return await cb.message.reply("❌ Set your token first.")
        headers = {"Authorization": f"token {token}"}
        username = requests.get("https://api.github.com/user", headers=headers).json().get("login")
        zip_url = f"https://github.com/{username}/{repo_name}/archive/refs/heads/main.zip"
        try:
            file = requests.get(zip_url)
            with open("repo.zip", "wb") as f:
                f.write(file.content)
            await cb.message.reply_document("repo.zip", caption=f"📦 Downloaded `{repo_name}`")
            os.remove("repo.zip")
        except:
            await cb.message.reply("❌ Could not download repo.")

def get_active_token(user_id):
    tokens = user_tokens.get(str(user_id), {})
    active = tokens.get("active")
    return active if active else (next((t for t in tokens if t != "active"), None))

print("✅ SPILUX GITHUB BOT ONLINE")
app.run()
