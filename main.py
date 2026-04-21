import os
import sqlite3
import time
import random
import threading
from datetime import datetime
from flask import Flask, redirect
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ===== CONFIG =====
TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if ADMIN_ID:
    ADMIN_ID = int(ADMIN_ID)

# 👉 TU GRUPO DE WHATSAPP
WHATSAPP = "https://chat.whatsapp.com/TU_LINK_AQUI"

# ===== CONFIG ECONOMÍA =====
REWARD_AD = 0.000125
REWARD_TASK = 0.0035
BONUS = 0.03
MIN_RETIRO = 1
MAX_RETIRO = 10
LIMITE_ADS = 100

# ===== LINKS =====
TASKS = [
    "https://omg10.com/4/10904191",
    "https://omg10.com/4/10904194",
]

ADS = [
    "https://theoreticalassertshame.com/yx0a5f37?key=292b2444288218b819570c449013aa72",
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
    last_task INTEGER DEFAULT 0,
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

    await update.message.reply_text(
        "🔥 BIENVENIDO AL BOT $$$\n\nGana dinero viendo anuncios 🚀",
        reply_markup=menu
    )

# ===== GRUPO =====
async def grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"👥 Únete al grupo:\n{WHATSAPP}")

# ===== BALANCE =====
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bal = cursor.execute("SELECT balance FROM users WHERE user_id=?", (update.effective_user.id,)).fetchone()[0]
    await update.message.reply_text(f"💰 ${bal:.6f}")

# ===== ADS =====
async def ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ads_today, last_ad = cursor.execute(
        "SELECT ads_today,last_ad FROM users WHERE user_id=?", (user_id,)
    ).fetchone()

    if ads_today >= LIMITE_ADS:
        return await update.message.reply_text("❌ Límite diario")

    if time.time() - last_ad < 10:
        return await update.message.reply_text("⏳ Espera")

    wait = random.choice([15, 30])
    ad = random.choice(ADS)

    context.user_data["time"] = time.time()
    context.user_data["wait"] = wait

    cursor.execute("UPDATE users SET last_ad=? WHERE user_id=?", (int(time.time()), user_id))
    conn.commit()

    await update.message.reply_text(f"🔗 {ad}\n⏳ Espera {wait}s y escribe OK")

# ===== CONFIRM =====
async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() != "ok":
        return

    start = context.user_data.get("time")
    wait = context.user_data.get("wait")

    if not start:
        return

    if time.time() - start < wait:
        return await update.message.reply_text("⏳ Aún no")

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
        "SELECT last_bonus FROM users WHERE user_id=?", (user_id,)
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
        "SELECT balance FROM users WHERE user_id=?", (user_id,)
    ).fetchone()[0]

    if bal < MIN_RETIRO:
        return await update.message.reply_text("❌ Mínimo $1")

    context.user_data["retiro"] = True
    await update.message.reply_text("Envía wallet")

# ===== WALLET =====
async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("retiro"):
        return

    user_id = update.effective_user.id
    bal = cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,)).fetchone()[0]

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
    await update.message.reply_text(f"👑 Admin\nUsuarios: {users}")

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
        await wallet(update, context)

# ===== WEB =====
web = Flask(__name__)

@web.route("/")
def panel():
    return "BOT ONLINE"

def run_web():
    web.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# ===== BOT =====
def run_bot():
    if not TOKEN:
        print("❌ TOKEN no encontrado")
        return

    app_bot = ApplicationBuilder().token(TOKEN).build()

    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("admin", admin))
    app_bot.add_handler(MessageHandler(filters.TEXT, handle_message))

    print("🤖 BOT iniciado")
    app_bot.run_polling()

# ===== RUN =====
threading.Thread(target=run_bot).start()
threading.Thread(target=run_web).start()
