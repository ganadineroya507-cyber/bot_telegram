import os
import sqlite3
import time
import random
import asyncio
from datetime import datetime

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ===== CONFIG =====
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8466239666"))

WHATSAPP = "https://chat.whatsapp.com/TU_LINK_AQUI"

# ===== ECONOMÍA =====
REWARD_AD = 0.000125
REWARD_TASK = 0.0035
BONUS = 0.03
MIN_RETIRO = 1
LIMITE_ADS = 100

# ===== LINKS =====
TASKS = [
    "https://omg10.com/4/10904191",
    "https://omg10.com/4/10904194",
    "https://omg10.com/4/10904192",
    "https://omg10.com/4/10904190",
    "https://omg10.com/4/10904189",
    "https://omg10.com/4/10904188",
    "https://omg10.com/4/10904193",
    "https://omg10.com/4/10904195",
    "https://omg10.com/4/10904196",
    "https://omg10.com/4/10904836"
]

ADS = [
    "https://theoreticalassertshame.com/yx0a5f37?key=292b2444288218b819570c449013aa72",
    "https://theoreticalassertshame.com/fuf8cjkg?key=30325938fd8887ac577057a3084780ad",
    "https://theoreticalassertshame.com/m96bxwhv0?key=aca07b0fb605c3cbaf5684855c18444d",
    "https://theoreticalassertshame.com/d5up4rzfmd?key=577be8abdeeea6b9ce2ab09a17989f6e",
    "https://theoreticalassertshame.com/ka4rk9wi?key=522dca01b077daf8d0e7c351aa405240",
    "https://theoreticalassertshame.com/jhdiprui?key=16b72e824b8f6f017159222e7e932a54",
    "https://theoreticalassertshame.com/dcx23snw?key=b6261e043fdc5fdbc3680edfa31ece84",
    "https://theoreticalassertshame.com/i41pw8tym?key=6de2ae6618162841dfc95130df72f97c",
    "https://theoreticalassertshame.com/ktdvs4u1q?key=34d9ea14248859c7791f862687cee605",
    "https://theoreticalassertshame.com/vqhunt3n38?key=c2f1c6a34412a17ecbe13b8c6e5baa40",
    "https://theoreticalassertshame.com/j2j6ejcx?key=e2fb6ca1a20fa321865f79cf1e41f03c"
]

# ===== DB =====
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 0,
    ads_today INTEGER DEFAULT 0,
    last_ad INTEGER DEFAULT 0,
    last_bonus TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS withdrawals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    wallet TEXT,
    status TEXT
)
""")

conn.commit()

# ===== MENU =====
menu = ReplyKeyboardMarkup([
    ["💰 Balance", "📺 Ver anuncios"],
    ["📋 Tareas", "🎁 Bono"],
    ["💸 Retirar", "👥 Grupo"]
], resize_keyboard=True)

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    await update.message.reply_text("🔥 BOT ACTIVO $$$", reply_markup=menu)

# ===== GRUPO =====
async def grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"👥 Grupo:\n{WHATSAPP}")

# ===== BALANCE =====
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bal = cursor.execute(
        "SELECT balance FROM users WHERE user_id=?",
        (update.effective_user.id,)
    ).fetchone()[0]

    await update.message.reply_text(f"💰 ${bal:.6f}")

# ===== ADS =====
async def ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    ads_today, last_ad = cursor.execute(
        "SELECT ads_today,last_ad FROM users WHERE user_id=?",
        (user_id,)
    ).fetchone()

    if ads_today >= LIMITE_ADS:
        return await update.message.reply_text("❌ Límite diario")

    if time.time() - last_ad < 10:
        return await update.message.reply_text("⏳ Espera")

    wait = random.choice([15, 30])
    ad = random.choice(ADS)

    context.user_data["time"] = time.time()
    context.user_data["wait"] = wait

    cursor.execute(
        "UPDATE users SET last_ad=? WHERE user_id=?",
        (int(time.time()), user_id)
    )
    conn.commit()

    await update.message.reply_text(f"🔗 {ad}\n⏳ Espera {wait}s y escribe OK")

# ===== CONFIRM =====
async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() != "ok":
        return

    start_time = context.user_data.get("time")
    wait = context.user_data.get("wait")

    if not start_time or time.time() - start_time < wait:
        return await update.message.reply_text("⏳ Espera el tiempo completo")

    user_id = update.effective_user.id

    cursor.execute(
        "UPDATE users SET balance=balance+?, ads_today=ads_today+1 WHERE user_id=?",
        (REWARD_AD, user_id)
    )
    conn.commit()

    context.user_data.clear()
    await update.message.reply_text(f"💸 +{REWARD_AD}")

# ===== TAREAS =====
async def tareas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "📋 TAREAS:\n\n"
    for i, t in enumerate(TASKS, 1):
        msg += f"{i}. {t}\n\n"
    await update.message.reply_text(msg)

# ===== BONUS =====
async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    today = str(datetime.now().date())

    last = cursor.execute(
        "SELECT last_bonus FROM users WHERE user_id=?",
        (user_id,)
    ).fetchone()[0]

    if last == today:
        return await update.message.reply_text("❌ Ya reclamado")

    cursor.execute(
        "UPDATE users SET balance=balance+?, last_bonus=? WHERE user_id=?",
        (BONUS, today, user_id)
    )
    conn.commit()

    await update.message.reply_text(f"🎁 +{BONUS}")

# ===== RETIRO =====
async def retirar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    bal = cursor.execute(
        "SELECT balance FROM users WHERE user_id=?",
        (user_id,)
    ).fetchone()[0]

    if bal < MIN_RETIRO:
        return await update.message.reply_text("❌ Mínimo $1")

    context.user_data["retiro"] = True
    await update.message.reply_text("Envía tu wallet")

# ===== WALLET =====
async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("retiro"):
        return

    user_id = update.effective_user.id

    bal = cursor.execute(
        "SELECT balance FROM users WHERE user_id=?",
        (user_id,)
    ).fetchone()[0]

    cursor.execute(
        "INSERT INTO withdrawals (user_id,amount,wallet,status) VALUES (?,?,?,?)",
        (user_id, bal, update.message.text, "pendiente")
    )

    cursor.execute("UPDATE users SET balance=0 WHERE user_id=?", (user_id,))
    conn.commit()

    context.user_data.clear()
    await update.message.reply_text("✅ Retiro enviado")

# ===== ADMIN =====
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    users = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    await update.message.reply_text(f"👑 Usuarios: {users}")

# ===== HANDLER =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if "Balance" in text:
        await balance(update, context)
    elif "Ver anuncios" in text:
        await ads(update, context)
    elif "Tareas" in text:
        await tareas(update, context)
    elif "Bono" in text:
        await bonus(update, context)
    elif "Retirar" in text:
        await retirar(update, context)
    elif "Grupo" in text:
        await grupo(update, context)
    else:
        await confirm(update, context)

# ===== MAIN =====
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    print("🤖 BOT corriendo...")
    await app.run_polling()

# ===== RUN =====
if __name__ == "__main__":
    asyncio.run(main())
