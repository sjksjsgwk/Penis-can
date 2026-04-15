import os
import random
import time
import psycopg2

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ================= ENV =================
TOKEN = os.getenv("TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMINS = list(map(int, os.getenv("ADMINS", "123456789").split(",")))

# ================= DB =================
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    size INT DEFAULT 5,
    money INT DEFAULT 1000,
    last_grow BIGINT DEFAULT 0,
    last_coin BIGINT DEFAULT 0
)
""")
conn.commit()

# ================= MEMORY =================
pending_vs = {}

# ================= USER =================
def get_user(user):
    cursor.execute("SELECT * FROM users WHERE user_id=%s", (user.id,))
    data = cursor.fetchone()

    if not data:
        cursor.execute(
            "INSERT INTO users (user_id, username) VALUES (%s, %s)",
            (user.id, user.username)
        )
        conn.commit()
        return get_user(user)

    return data

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
🤖 BOT AKTİF

📌 Komutlar:
/profil
/boyum
/uzat
/coin
/vs
/siralama
""")

# ================= PROFİL =================
async def profil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.reply_to_message.from_user if update.message.reply_to_message else update.effective_user
    d = get_user(user)

    await update.message.reply_text(
        f"""👤 PROFİL

📛 @{user.username or 'Anonim'}
📏 Boy: {d[2]} cm
💰 Coin: {d[3]}"""
    )

# ================= BOY =================
async def boyum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = get_user(update.effective_user)
    await update.message.reply_text(f"📏 Boyun: {d[2]} cm")

# ================= UZAT =================
async def uzat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    d = get_user(user)

    now = int(time.time())

    # 6 saat cooldown
    if now - d[4] < 21600:
        kalan = 21600 - (now - d[4])
        return await update.message.reply_text(
            f"⏳ Bekle: {kalan//3600} saat {(kalan%3600)//60} dk"
        )

    gain = random.randint(5, 10)

    cursor.execute("""
        UPDATE users SET size=size+%s, last_grow=%s
        WHERE user_id=%s
    """, (gain, now, user.id))

    conn.commit()

    await update.message.reply_text(f"📈 +{gain} cm kazandın!")

# ================= COIN =================
async def coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    d = get_user(user)

    now = int(time.time())

    if now - d[5] < 3600:
        return await update.message.reply_text("⏳ 1 saat bekle")

    reward = random.randint(50, 200)

    cursor.execute("""
        UPDATE users SET money=money+%s, last_coin=%s
        WHERE user_id=%s
    """, (reward, now, user.id))

    conn.commit()

    await update.message.reply_text(f"💰 +{reward} coin")

# ================= SIRALAMA =================
async def siralama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("""
        SELECT username, size FROM users
        ORDER BY size DESC LIMIT 15
    """)
    rows = cursor.fetchall()

    text = "🏆 TOP 15\n\n"
    for i, r in enumerate(rows, 1):
        text += f"{i}. {r[0] or 'Anonim'} - {r[1]} cm\n"

    await update.message.reply_text(text)

# ================= VS =================
async def vs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply at")

    try:
        miktar = int(context.args[0])
        if miktar < 10 or miktar > 1000000:
            return await update.message.reply_text("❌ 10 - 1.000.000 arası")
    except:
        return await update.message.reply_text("Kullanım: /vs 100")

    u1 = update.effective_user
    u2 = update.message.reply_to_message.from_user

    d1 = get_user(u1)
    d2 = get_user(u2)

    if d1[2] < miktar or d2[2] < miktar:
        return await update.message.reply_text("❌ Yetersiz cm")

    key = f"{u1.id}_{u2.id}"

    pending_vs[key] = {
        "u1": u1.id,
        "u2": u2.id,
        "m": miktar
    }

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Kabul", callback_data=f"ok_{key}"),
            InlineKeyboardButton("Red", callback_data=f"no_{key}")
        ]
    ])

    await update.message.reply_text(
        f"""⚔️ VS DAVETİ

👤 {u1.username or 'Anonim'} vs {u2.username or 'Anonim'}
💰 Bahis: {miktar} cm""",
        reply_markup=kb
    )

# ================= CALLBACK =================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = q.data

    if data.startswith("ok_"):
        key = data[3:]
        v = pending_vs.get(key)

        if not v:
            return await q.edit_message_text("❌ Süre doldu")

        if q.from_user.id != v["u2"]:
            return await q.answer("Sana ait değil", show_alert=True)

        u1, u2, m = v["u1"], v["u2"], v["m"]

        winner = random.choice([u1, u2])
        loser = u2 if winner == u1 else u1

        cursor.execute("UPDATE users SET size=size+%s WHERE user_id=%s", (m, winner))
        cursor.execute("UPDATE users SET size=size-%s WHERE user_id=%s", (m, loser))
        conn.commit()

        del pending_vs[key]

        await q.edit_message_text(f"⚔️ VS BİTTİ!\n💰 {m} cm değişti")

    elif data.startswith("no_"):
        key = data[3:]
        if key in pending_vs:
            del pending_vs[key]

        await q.edit_message_text("❌ reddedildi")

# ================= APP =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("profil", profil))
app.add_handler(CommandHandler("boyum", boyum))
app.add_handler(CommandHandler("uzat", uzat))
app.add_handler(CommandHandler("coin", coin))
app.add_handler(CommandHandler("vs", vs))
app.add_handler(CommandHandler("siralama", siralama))
app.add_handler(CallbackQueryHandler(button))

print("Bot çalışıyor...")
app.run_polling()
