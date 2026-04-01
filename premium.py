import asyncio
import random
import string
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

# ===== CONFIG =====
TOKEN = "8238022695:AAFv1kUvd-Ta0JoyUbf5ybPle4r3fsqT1J8"
DB_CHANNEL_ID = -1003604913684        # Storage channel (bot admin)
LOG_CHANNEL_ID = -1003720874644       # Log channel
FORCE_JOIN_CHANNEL = "@all_viral_linkv1"   # Channel username
ADMIN_ID = 5830927118                  # Your Telegram ID
AUTO_DELETE_MINUTES = 10
WELCOME_PHOTO = "https://i.imgur.com/4M34hi2.jpeg"

# ===== SQLite Setup =====
conn = sqlite3.connect("bot_data.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS short_links (
    short_code TEXT PRIMARY KEY,
    msg_ids TEXT
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
)
""")
conn.commit()

# ===== Runtime batch storage =====
batch_data = {}  # user_id -> list of DB msg_ids

# ===== Utils =====
def generate_short_code(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

async def is_joined(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        m = await context.bot.get_chat_member(FORCE_JOIN_CHANNEL, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

async def send_force_join(chat_id, context):
    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{FORCE_JOIN_CHANNEL.replace('@','')}")],
        [InlineKeyboardButton("🔄 Check Join", callback_data="check_join")]
    ]
    await context.bot.send_message(
        chat_id=chat_id,
        text="Join our group first then click ✅ check join  🥇 আমাদের চ্যানেল এ জয়েন করুন । তারপর ✅ check join ক্লিক করুন ",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def auto_delete_user_file(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int):
    await asyncio.sleep(AUTO_DELETE_MINUTES * 60)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"🗑️ Auto-deleted MsgID {message_id} from user {chat_id}"
        )
    except:
        pass

WARNING_TEXT = """
❗️❗️❗️IMPORTANT❗️️❗️❗️

ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ɪɴ 10 Minutes 🫥 (ᴅᴜᴇ ᴛᴏ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs).

ᴘʟᴇᴀsᴇ ғᴏʀᴡᴀʀᴅ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴛᴏ ʏᴏᴜʀ sᴀᴠᴇᴅ ᴍᴇssᴀɢᴇs ᴏʀ ᴀɴʏ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛ ᴛᴏ ᴀᴠᴏɪᴅ ʟᴏsɪɴɢ
"""

# ===== /start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    # Save user
    c.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (user_id,))
    conn.commit()

    # Force join check
    if not await is_joined(context, user_id):
        await send_force_join(user_id, context)
        return

    args = context.args
    if args:
        code = args[0]
        c.execute("SELECT msg_ids FROM short_links WHERE short_code=?", (code,))
        row = c.fetchone()
        if row:
            msg_ids = list(map(int, row[0].split(",")))
            # Send files
            for mid in msg_ids:
                sent = await context.bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=DB_CHANNEL_ID,
                    message_id=mid,
                    protect_content=True
                )
                asyncio.create_task(auto_delete_user_file(context, user_id, sent.message_id))
            # Warning text (copy/quote allowed)
            await context.bot.send_message(chat_id=user_id, text=WARNING_TEXT)
            return

    # Normal welcome UI
    keyboard = [
        [InlineKeyboardButton("📦 Start Upload", callback_data="upload")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help"),
         InlineKeyboardButton("👑 About", callback_data="about")]
    ]
    text = f"""
✨ *Premium File Store Bot*

👤 User : {user.first_name}
🆔 ID : `{user_id}`

This bot lets you upload files and create a secure, shareable link in just a few steps. Here’s how it works:

1️⃣ Send /upload or /batch to start uploading.
2️⃣ Upload or forward the files you’d like to share — documents, photos, videos, or any Telegram-supported file.
3️⃣ When finished, send /make_link to receive your shareable link.

✅ Fast, simple, and secure file sharing!
"""
    await context.bot.send_photo(
        chat_id=user_id,
        photo=WELCOME_PHOTO,
        caption=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await context.bot.send_message(
        chat_id=LOG_CHANNEL_ID,
        text=f"✅ User started bot: {user.first_name} | ID: {user_id}"
    )

# ===== Buttons =====
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id

    if q.data == "check_join":
        if await is_joined(context, user_id):
            await q.message.edit_text("✅ Join verified! এখন bot ব্যবহার করতে পারবেন.")
        else:
            await q.answer("❌Join our group first then click ✅ check join  🥇 আমাদের চ্যানেল এ জয়েন করুন । তারপর ✅ check join ক্লিক করুন "
        , show_alert=True)

    elif q.data == "upload":
        batch_data[user_id] = []
        await q.message.reply_text("📂 Batch mode started. Files পাঠান, শেষে /done দিন.")

    elif q.data == "help":
        await q.message.reply_text("📦 Files পাঠান → /done → bot short link দেবে.")

    elif q.data == "about":
        await q.message.reply_text("👑 Premium File Store Bot\nTemporary protected files.")

# ===== Save files =====
async def save_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in batch_data:
        return
    stored = await context.bot.forward_message(
        chat_id=DB_CHANNEL_ID,
        from_chat_id=update.message.chat_id,
        message_id=update.message.message_id
    )
    batch_data[user_id].append(stored.message_id)
    await context.bot.send_message(
        chat_id=LOG_CHANNEL_ID,
        text=f"📤 User {user_id} uploaded file | MsgID: {stored.message_id}"
    )

# ===== /done create link =====
async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in batch_data or not batch_data[user_id]:
        await update.message.reply_text("❌ No files uploaded.")
        return

    msg_ids = batch_data[user_id]
    code = generate_short_code()
    msg_ids_str = ",".join(map(str, msg_ids))

    c.execute("INSERT INTO short_links(short_code,msg_ids) VALUES(?,?)", (code, msg_ids_str))
    conn.commit()

    username = (await context.bot.get_me()).username
    link = f"https://t.me/{username}?start={code}"

    await update.message.reply_text(f"✅ Batch link created:\n🔗 {link}")
    await context.bot.send_message(
        chat_id=LOG_CHANNEL_ID,
        text=f"📦 Link generated by {user_id}: {link}"
    )
    del batch_data[user_id]

# ===== Admin commands =====
async def users_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    c.execute("SELECT COUNT(*) FROM users")
    await update.message.reply_text(f"👥 Total Users: {c.fetchone()[0]}")

async def user_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    c.execute("SELECT user_id FROM users")
    ids = "\n".join(str(r[0]) for r in c.fetchall())
    await update.message.reply_text(f"📜 User IDs:\n{ids}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    msg = " ".join(context.args)
    if not msg:
        await update.message.reply_text("Usage: /broadcast message")
        return
    c.execute("SELECT user_id FROM users")
    users = [r[0] for r in c.fetchall()]
    sent = 0
    for u in users:
        try:
            await context.bot.send_message(chat_id=u, text=msg)
            sent += 1
        except:
            pass
    await update.message.reply_text(f"✅ Broadcast sent to {sent} users")

# ===== App =====
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(CommandHandler("done", done))
app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, save_file))
app.add_handler(CommandHandler("users", users_count))
app.add_handler(CommandHandler("ids", user_ids))
app.add_handler(CommandHandler("broadcast", broadcast))

print("Bot running...")
app.run_polling()