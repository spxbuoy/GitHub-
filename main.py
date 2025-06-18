import os
import json
import base64
import requests
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.filters import create

# Your credentials
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

# /start
@app.on_message(filters.command("start") & not_banned)
async def start(_, msg: Message):
    await msg.reply(
        "**👋 Welcome to GitHub Manager Bot!**\n\n"
        "Commands:\n"
• Connect your GitHub account
• Browse and manage repositories
• Create and delete repositories
• Upload files and manage repository contents
• View issues and pull requests
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 Commands", callback_data="help")]
        ])
    )

# Button handler
@app.on_callback_query()
async def button_handler(_, cb):
    if cb.data == "help":
        await cb.message.edit(
            "**📘 𝐂𝐨𝐦𝐦𝐚𝐧𝐝𝐬 𝐇𝐞𝐥𝐩**\n\n"
            "`/settoken` - Link GitHub token\n"
            "`/repos` - List repos\n"
            "`/create` - Create repo\n"
            "`/delete` - Delete repo\n"
            "`/createas` - Admin create repo\n"
            "`/ban` / `/unban` - Admin only\n"
            "`/users` - Admin only",
            bᎾᏆ bᎽ:@SpiluxX
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back")]
            ])
        )
    elif cb.data == "back":
        await start(_, cb.message)

# /settoken
@app.on_message(filters.command("settoken") & not_banned)
async def set_token(_, msg: Message):
    if len(msg.command) < 2:
        return await msg.reply("Usage: `/settoken <your_github_token>`")
    user_tokens[str(msg.from_user.id)] = msg.command[1]
    save_data()
    await msg.reply("✅ GitHub token saved!")

# /repos
@app.on_message(filters.command("repos") & not_banned)
async def list_repos(_, msg: Message):
    token = user_tokens.get(str(msg.from_user.id))
    if not token:
        return await msg.reply("❌ Use `/settoken` first.")
    headers = {"Authorization": f"token {token}"}
    res = requests.get("https://api.github.com/user/repos", headers=headers)
    if res.status_code != 200:
        return await msg.reply("❌ Failed to fetch repositories.")
    repos = [r["name"] for r in res.json()]
    await msg.reply("📦 Your Repositories:\n" + "\n".join(f"• `{r}`" for r in repos) or "No repos found.")

# /create
@app.on_message(filters.command("create") & not_banned)
async def create_repo(_, msg: Message):
    if len(msg.command) < 2:
        return await msg.reply("Usage: `/create repo_name`")
    token = user_tokens.get(str(msg.from_user.id))
    if not token:
        return await msg.reply("❌ Use `/settoken` first.")
    headers = {"Authorization": f"token {token}"}
    data = {"name": msg.command[1], "auto_init": True}
    res = requests.post("https://api.github.com/user/repos", json=data, headers=headers)
    if res.status_code == 201:
        await msg.reply(f"✅ Repository `{msg.command[1]}` created!")
    else:
        await msg.reply("❌ Failed to create repository.")

# /delete
@app.on_message(filters.command("delete") & not_banned)
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
        await msg.reply("❌ Failed to delete repository.")

# /createas (admin)
@app.on_message(filters.command("createas") & filters.user(ADMINS))
async def create_as(_, msg: Message):
    if len(msg.command) < 3:
        return await msg.reply("Usage: `/createas user_id repo_name`")
    uid, repo = msg.command[1], msg.command[2]
    token = user_tokens.get(str(uid))
    if not token:
        return await msg.reply("❌ User has no token.")
    headers = {"Authorization": f"token {token}"}
    data = {"name": repo, "auto_init": True}
    res = requests.post("https://api.github.com/user/repos", json=data, headers=headers)
    if res.status_code == 201:
        await msg.reply(f"✅ Created `{repo}` for user `{uid}`.")
    else:
        await msg.reply("❌ Failed to create repo.")

# /ban (admin)
@app.on_message(filters.command("ban") & filters.user(ADMINS))
async def ban_user(_, msg: Message):
    if len(msg.command) < 2:
        return await msg.reply("Usage: `/ban user_id`")
    user_id = int(msg.command[1])
    banned_users.add(user_id)
    save_data()
    await msg.reply(f"🚫 Banned user `{user_id}`.")

@app.on_message(filters.command("download") & not_banned)
async def download_repo(_, msg: Message):
    if len(msg.command) < 2:
        return await msg.reply("Usage: `/download repo_name`")
    token = user_tokens.get(str(msg.from_user.id))
    if not token:
        return await msg.reply("❌ Use `/settoken` first.")
    
    headers = {"Authorization": f"token {token}"}
    username = requests.get("https://api.github.com/user", headers=headers).json().get("login")
    zip_url = f"https://github.com/{username}/{msg.command[1]}/archive/refs/heads/main.zip"
    
    try:
        file = requests.get(zip_url)
        with open("repo.zip", "wb") as f:
            f.write(file.content)
        await msg.reply_document("repo.zip", caption="📦 Here's your repository.")
        os.remove("repo.zip")
    except:
        await msg.reply("❌ Could not download repo.")
        

# /unban (admin)
@app.on_message(filters.command("unban") & filters.user(ADMINS))
async def unban_user(_, msg: Message):
    if len(msg.command) < 2:
        return await msg.reply("Usage: `/unban user_id`")
    user_id = int(msg.command[1])
    banned_users.discard(user_id)
    save_data()
    await msg.reply(f"✅ Unbanned user `{user_id}`.")

# /users (admin)
@app.on_message(filters.command("users") & filters.user(ADMINS))
async def list_users(_, msg: Message):
    if not user_tokens:
        return await msg.reply("No users have set a token yet.")
    text = "**👥 Users with tokens:**\n"
    for uid in user_tokens:
        text += f"• `{uid}`\n"
    await msg.reply(text)

# File upload
@app.on_message(filters.document & not_banned)
async def upload_file(_, msg: Message):
    token = user_tokens.get(str(msg.from_user.id))
    if not token:
        return await msg.reply("❌ Use `/settoken` first.")
    file_path = await msg.download()
    await msg.reply("📥 Now send: `repo_name/path/to/filename.ext`")

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

# Start bot
print("✅ SPILUX GITHUB BOT ONLINE")
app.run()
            
