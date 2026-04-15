import sqlite3
import random
import time
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ================= TOKEN =================
TOKEN = os.getenv("TOKEN")

# ================= ADMINS =================
ADMINS = [123456789]  # BURAYA KENDİ TELEGRAM ID

# ================= DATABASE =================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    size INTEGER DEFAULT 5,
    money INTEGER DEFAULT 1000,
    last_grow INTEGER DEFAULT 0
)
""")

conn.commit()

# ================= MEMORY =================
pending_vs = {}

# ================= HELPERS =================
def is_admin(user_id):
    return user_id in ADMINS

def get_user(user):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user.id,))
    data = cursor.fetchone()

    if not data:
        cursor.execute(
            "INSERT INTO users (user_id, username) VALUES (?, ?)",
            (user.id, user.username)
        )
        conn.commit()
        return get_user(user)

    return data

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot aktif! /boyum /vs /profil /siralama")

# ================= PROFİL =================
async def profil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.reply_to_message.from_user if update.message.reply_to_message else update.effective_user
    data = get_user(user)

    name = user.username or "Anonim"

    text = f"""
👤 PROFİL

📛 @{name}
🆔 {user.id}

📏 Boy: {data[2]} cm
💰 Para: {data[3]} coin
"""

    await update.message.reply_text(text)

# ================= SIRALAMA (TOP 15) =================
async def siralama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT username, size FROM users ORDER BY size DESC LIMIT 15")
    rows = cursor.fetchall()

    text = "🏆 TOP 15:\n\n"

    for i, row in enumerate(rows, 1):
        name = row[0] or "Anonim"
        text += f"{i}. {name} — {row[1]} cm\n"

    await update.message.reply_text(text)

# ================= BOY =================
async def boyum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_user(update.effective_user)
    await update.message.reply_text(f"📏 {data[2]} cm | 💰 {data[3]} coin")

# ================= UZAT (6 SAAT / 5-10 CM) =================
async def uzat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = get_user(user)

    now = int(time.time())

    # 6 saat cooldown
    if now - data[4] < 21600:
        kalan = 21600 - (now - data[4])
        saat = kalan // 3600
        dakika = (kalan % 3600) // 60
        return await update.message.reply_text(f"⏳ {saat}h {dakika}m bekle!")

    gain = random.randint(5, 10)

    cursor.execute("""
        UPDATE users SET size=size+?, last_grow=?
        WHERE user_id=?
    """, (gain, now, user.id))

    conn.commit()

    await update.message.reply_text(f"📈 +{gain} cm kazandın!")

# ================= VS (BUTONLU) =================
async def vs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("Birine reply at!")

    try:
        miktar = int(context.args[0])
        if miktar < 10 or miktar > 1000000:
            return await update.message.reply_text("❌ Min 10 | Max 1.000.000")
    except:
        return await update.message.reply_text("Kullanım: /vs 100")

    u1 = update.effective_user
    u2 = update.message.reply_to_message.from_user

    d1 = get_user(u1)
    d2 = get_user(u2)

    if d1[2] < miktar or d2[2] < miktar:
        return await update.message.reply_text("❌ Yetersiz cm!")

    key = f"{u1.id}_{u2.id}"

    pending_vs[key] = {
        "u1": u1.id,
        "u2": u2.id,
        "miktar": miktar
    }

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Kabul", callback_data=f"ok_{key}"),
            InlineKeyboardButton("❌ Reddet", callback_data=f"no_{key}")
        ]
    ])

    text = f"""
⚔️ VS DAVETİ

👤 {u1.username} → {u2.username}
💰 Bahis: {miktar} cm
"""

    await update.message.reply_text(text, reply_markup=keyboard)

# ================= CALLBACK =================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("ok_"):
        key = data.replace("ok_", "")
        vs_data = pending_vs.get(key)

        if not vs_data:
            return await query.edit_message_text("❌ Süre doldu")

        u1 = vs_data["u1"]
        u2 = vs_data["u2"]
        m = vs_data["miktar"]

        if query.from_user.id != u2:
            return await query.answer("Bu sana ait değil!", show_alert=True)

        winner = random.choice([u1, u2])
        loser = u2 if winner == u1 else u1

        cursor.execute("UPDATE users SET size=size+? WHERE user_id=?", (m, winner))
        cursor.execute("UPDATE users SET size=size-? WHERE user_id=?", (m, loser))
        conn.commit()

        del pending_vs[key]

        await query.edit_message_text(f"⚔️ VS BİTTİ!\n🏆 Kazanan: {winner}\n💰 {m} cm değişti!")

    elif data.startswith("no_"):
        key = data.replace("no_", "")
        if key in pending_vs:
            del pending_vs[key]

        await query.edit_message_text("❌ VS reddedildi")

# ================= RUN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("boyum", boyum))
app.add_handler(CommandHandler("uzat", uzat))
app.add_handler(CommandHandler("vs", vs))
app.add_handler(CommandHandler("profil", profil))
app.add_handler(CommandHandler("siralama", siralama))

app.add_handler(CallbackQueryHandler(button))

print("Bot çalışıyor...")
app.run_polling()
