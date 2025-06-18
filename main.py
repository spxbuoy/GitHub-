import os
import json
import base64
import requests
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

API_ID = 123456  # Replace with your API ID
API_HASH = "your_api_hash"  # Replace with your API Hash
BOT_TOKEN = "your_bot_token"  # Replace with your Bot Token

ADMINS = [123456789]  # Replace with your Telegram user ID(s)

DATA_FILE = "data.json"

# Load/Save Functions
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"tokens": {}, "banned": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump({"tokens": user_tokens, "banned": list(banned_users)}, f)

# Load existing data
data = load_data()
user_tokens = data.get("tokens", {})
banned_users = set(data.get("banned", []))

app = Client("github_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Helper: Check admin
def is_admin(user_id):
    return user_id in ADMINS

# Helper: Check ban
@app.on_message(filters.private)
async def check_ban(client, msg):
    if msg.from_user.id in banned_users:
        return await msg.reply("🚫 You are banned from using this bot.")

# /start
@app.on_message(filters.command("start"))
async def start(_, msg: Message):
    await msg.reply(
        "**👋 Welcome to GitHub Manager Bot!**\n\n"
        "Here’s what I can do:\n"
        "• `/settoken <token>` – Connect GitHub\n"
        "• `/repos` – List your repositories\n"
        "• `/create <name>` – Create a new repo\n"
        "• `/createas <user_id> <repo>` – Admin create repo for user\n"
        "• `/delete <name>` – Delete a repo\n"
        "• Send file – Upload to repo\n"
        "• `/ban <user_id>` – Admin only\n"
        "• `/unban <user_id>` – Admin only",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 View Commands", callback_data="help")]
        ])
    )

@app.on_callback_query()
async def button_handler(_, cb):
    if cb.data == "help":
        await cb.message.edit(
            "**📘 Commands Help**\n\n"
            "`/settoken` - Save GitHub Token\n"
            "`/repos` - List Repositories\n"
            "`/create` - Create Repo\n"
            "`/delete` - Delete Repo\n"
            "`/ban` / `/unban` - Admin\n"
            "`/createas` - Admin create repo for user\n"
            "Upload files - Send any file to upload to repo",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back")]
            ])
        )
    elif cb.data == "back":
        await start(_, cb.message)

# /settoken
@app.on_message(filters.command("settoken"))
async def set_token(_, msg: Message):
    if len(msg.command) < 2:
        return await msg.reply("Usage: `/settoken YOUR_GITHUB_TOKEN`")
    token = msg.command[1]
    user_tokens[str(msg.from_user.id)] = token
    save_data()
    await msg.reply("✅ GitHub token saved!")

# Admin: View user repos
@app.on_message(filters.command("viewrepos") & filters.user(ADMINS))
async def admin_view_user_repos(_, msg: Message):
    if len(msg.command) < 2:
        return await msg.reply("Usage: `/viewrepos user_id`")
    
    user_id = msg.command[1]
    token = user_tokens.get(str(user_id))
    
    if not token:
        return await msg.reply("❌ That user has not set a token.")

    headers = {"Authorization": f"token {token}"}
    res = requests.get("https://api.github.com/user/repos", headers=headers)
    
    if res.status_code != 200:
        return await msg.reply("❌ Failed to fetch repos for user.")
    
    repos = [r["name"] for r in res.json()]
    await msg.reply(f"📦 Repos for `{user_id}`:\n" + "\n".join(f"• `{r}`" for r in repos) or "No repos.")
    

# /repos
@app.on_message(filters.command("repos"))
async def list_repos(_, msg: Message):
    token = user_tokens.get(str(msg.from_user.id))
    if not token:
        return await msg.reply("❌ Use `/settoken` first.")
    headers = {"Authorization": f"token {token}"}
    res = requests.get("https://api.github.com/user/repos", headers=headers)
    if res.status_code != 200:
        return await msg.reply("❌ Could not fetch repositories.")
    repos = [r["name"] for r in res.json()]
    await msg.reply("📦 Your Repos:\n" + "\n".join(f"• `{r}`" for r in repos) or "You have none.")

# /create
@app.on_message(filters.command("create"))
async def create_repo(_, msg: Message):
    if msg.from_user.id in banned_users:
        return await msg.reply("🚫 You are banned.")
    if len(msg.command) < 2:
        return await msg.reply("Usage: `/create repo_name`")
    token = user_tokens.get(str(msg.from_user.id))
    if not token:
        return await msg.reply("❌ Use `/settoken` first.")
    repo = msg.command[1]
    headers = {"Authorization": f"token {token}"}
    data = {"name": repo, "auto_init": True}
    res = requests.post("https://api.github.com/user/repos", headers=headers, json=data)
    if res.status_code == 201:
        await msg.reply(f"✅ Repo `{repo}` created!")
    else:
        await msg.reply(f"❌ Failed to create: {res.json().get('message')}")

# /createas <user_id> <repo_name>
@app.on_message(filters.command("createas") & filters.user(ADMINS))
async def create_as(_, msg: Message):
    if len(msg.command) < 3:
        return await msg.reply("Usage: `/createas user_id repo_name`")
    uid, repo = msg.command[1], msg.command[2]
    token = user_tokens.get(str(uid))
    if not token:
        return await msg.reply("❌ That user has not set token.")
    headers = {"Authorization": f"token {token}"}
    data = {"name": repo, "auto_init": True}
    res = requests.post("https://api.github.com/user/repos", headers=headers, json=data)
    if res.status_code == 201:
        await msg.reply(f"✅ Repo `{repo}` created for user `{uid}`!")
    else:
        await msg.reply(f"❌ GitHub error: {res.json().get('message')}")

# /delete
@app.on_message(filters.command("delete"))
async def delete_repo(_, msg: Message):
    if len(msg.command) < 2:
        return await msg.reply("Usage: `/delete repo_name`")
    token = user_tokens.get(str(msg.from_user.id))
    if not token:
        return await msg.reply("❌ Use `/settoken` first.")
    headers = {"Authorization": f"token {token}"}
    username = requests.get("https://api.github.com/user", headers=headers).json().get("login")
    res = requests.delete(f"https://api.github.com/repos/{username}/{msg.command[1]}", headers=headers)
    if res.status_code == 204:
        await msg.reply("🗑️ Repository deleted.")
    else:
        await msg.reply("❌ Failed to delete.")

# File Upload
@app.on_message(filters.document)
async def upload_file(_, msg: Message):
    token = user_tokens.get(str(msg.from_user.id))
    if not token:
        return await msg.reply("❌ Use `/settoken` first.")
    file_path = await msg.download()
    await msg.reply("📝 Send: `repo_name/path/to/filename.py`")

    next_msg = await app.listen(msg.chat.id)
    target_path = next_msg.text.strip()
    repo_name, file_in_repo = target_path.split("/", 1)

    with open(file_path, "rb") as f:
        content = f.read()
    content_b64 = base64.b64encode(content).decode()

    headers = {
        "Authorization": f"token {token}",
        "Content-Type": "application/json"
    }
    username = requests.get("https://api.github.com/user", headers=headers).json().get("login")
    url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{file_in_repo}"
    data = {
        "message": f"Upload {file_in_repo}",
        "content": content_b64
    }
    res = requests.put(url, json=data, headers=headers)
    os.remove(file_path)
    if res.status_code in [200, 201]:
        await msg.reply("✅ File uploaded.")
    else:
        await msg.reply("❌ Failed to upload file.")

# /ban & /unban
@app.on_message(filters.command("ban") & filters.user(ADMINS))
async def ban_user(_, msg: Message):
    if len(msg.command) < 2:
        return await msg.reply("Usage: `/ban user_id`")
    try:
        user_id = int(msg.command[1])
        banned_users.add(user_id)
        save_data()
        await msg.reply(f"✅ Banned `{user_id}`.")
    except:
        await msg.reply("❌ Invalid ID.")

@app.on_message(filters.command("unban") & filters.user(ADMINS))
async def unban_user(_, msg: Message):
    if len(msg.command) < 2:
        return await msg.reply("Usage: `/unban user_id`")
    try:
        user_id = int(msg.command[1])
        banned_users.discard(user_id)
        save_data()
        await msg.reply(f"✅ Unbanned `{user_id}`.")
    except:
        await msg.reply("❌ Invalid ID.")

app.run()
