import os
import random
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("TOKEN")
ADMINS = list(map(int, os.getenv("ADMINS", "123456789").split(",")))

# ================= RAM DATABASE =================
users = {}
pending_vs = {}

# ================= USER =================
def get_user(user):
    if user.id not in users:
        users[user.id] = {
            "name": user.username or "Anonim",
            "size": 5,
            "money": 1000,
            "last_grow": 0,
            "last_coin": 0
        }
    return users[user.id]

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 BOT AKTİF\n\n"
        "/profil\n/uzat\n/coin\n/vs\n/siralama"
    )

# ================= PROFİL =================
async def profil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.reply_to_message.from_user if update.message.reply_to_message else update.effective_user
    d = get_user(user)

    await update.message.reply_text(
        f"👤 @{user.username or 'Anonim'}\n📏 Boy: {d['size']} cm\n💰 Coin: {d['money']}"
    )

# ================= UZAT =================
async def uzat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    d = get_user(user)

    now = int(time.time())

    if now - d["last_grow"] < 21600:
        kalan = 21600 - (now - d["last_grow"])
        return await update.message.reply_text(
            f"⏳ 6 saat bekle ({kalan//3600}s {(kalan%3600)//60}dk)"
        )

    gain = random.randint(5, 10)
    d["size"] += gain
    d["last_grow"] = now

    await update.message.reply_text(f"📈 +{gain} cm kazandın!")

# ================= COIN =================
async def coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    d = get_user(user)

    now = int(time.time())

    if now - d["last_coin"] < 3600:
        kalan = 3600 - (now - d["last_coin"])
        return await update.message.reply_text(
            f"⏳ 1 saat bekle ({kalan//60} dk)"
        )

    reward = random.randint(50, 200)
    d["money"] += reward
    d["last_coin"] = now

    await update.message.reply_text(f"💰 +{reward} coin kazandın!")

# ================= SIRALAMA =================
async def siralama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top = sorted(users.items(), key=lambda x: x[1]["size"], reverse=True)[:15]

    text = "🏆 TOP 15\n\n"
    for i, (uid, d) in enumerate(top, 1):
        text += f"{i}. {d['name']} - {d['size']} cm\n"

    await update.message.reply_text(text)

# ================= VS =================
async def vs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("Birine reply at!")

    try:
        miktar = int(context.args[0])
    except:
        return await update.message.reply_text("Kullanım: /vs 100")

    if miktar < 10 or miktar > 1000000:
        return await update.message.reply_text("❌ 10 - 1.000.000 arası")

    u1 = update.effective_user
    u2 = update.message.reply_to_message.from_user

    key = f"{u1.id}_{u2.id}"

    pending_vs[key] = {
        "u1": u1.id,
        "u2": u2.id,
        "m": miktar
    }

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Kabul", callback_data=f"ok_{key}"),
            InlineKeyboardButton("❌ Red", callback_data=f"no_{key}")
        ]
    ])

    await update.message.reply_text(
        f"⚔️ VS DAVETİ\n💰 Bahis: {miktar}",
        reply_markup=kb
    )

# ================= BUTTON =================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = q.data

    if data.startswith("ok_"):
        key = data[3:]
        v = pending_vs.get(key)

        if not v:
            return await q.edit_message_text("❌ Süre doldu")

        u1, u2, m = v["u1"], v["u2"], v["m"]

        winner = random.choice([u1, u2])
        loser = u2 if winner == u1 else u1

        get_user(type("U", (), {"id": winner}))
        get_user(type("U", (), {"id": loser}))

        users[winner]["size"] += m
        users[loser]["size"] -= m

        del pending_vs[key]

        await q.edit_message_text("⚔️ VS BİTTİ!")

    elif data.startswith("no_"):
        key = data[3:]
        if key in pending_vs:
            del pending_vs[key]

        await q.edit_message_text("❌ reddedildi")

# ================= BOT =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("profil", profil))
app.add_handler(CommandHandler("uzat", uzat))
app.add_handler(CommandHandler("coin", coin))
app.add_handler(CommandHandler("siralama", siralama))
app.add_handler(CommandHandler("vs", vs))
app.add_handler(CallbackQueryHandler(button))

print("BOT BAŞLADI")
app.run_polling()
