import os
import sqlite3
import time
import random
import uuid
from datetime import datetime
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ===== CONFIG =====
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8466239666"))
BOT_USERNAME = "ammpty507_bot"

WHATSAPP = "https://chat.whatsapp.com/TU_LINK_AQUI"

# ===== ECONOMÍA =====
REWARD_AD = 0.000125
REWARD_TASK = 0.0035
BONUS = 0.03
MIN_RETIRO = 1
LIMITE_ADS = 100
ADS_REQUIRED = 5
REF_BONUS = 0.05

# ===== LINKS =====
TASKS = [
    "https://omg10.com/4/10904191",
    "https://omg10.com/4/10904194",
    "https://omg10.com/4/10904192"
]

ADS = [
    "https://theoreticalassertshame.com/yx0a5f37?key=xxx"
]

# ===== DB =====
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 0,
    ads_today INTEGER DEFAULT 0,
    ads_progress INTEGER DEFAULT 0,
    last_ad INTEGER DEFAULT 0,
    last_task INTEGER DEFAULT 0,
    last_bonus TEXT,
    ref_by INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS ad_tracking (
    id TEXT PRIMARY KEY,
    user_id INTEGER,
    ad TEXT,
    clicked INTEGER DEFAULT 0,
    timestamp INTEGER
)
""")

# NUEVO (NO rompe nada)
cursor.execute("""
CREATE TABLE IF NOT EXISTS task_tracking (
    id TEXT PRIMARY KEY,
    user_id INTEGER,
    link TEXT,
    clicked INTEGER DEFAULT 0,
    timestamp INTEGER
)
""")

conn.commit()

# ===== MENU =====
menu = ReplyKeyboardMarkup([
    ["💰 Balance", "📺 Ver anuncios"],
    ["📋 Tareas", "🎁 Bono"],
    ["🏆 Ranking", "💸 Retirar"],
    ["👥 Grupo"]
], resize_keyboard=True)

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()

    await update.message.reply_text("🔥 BOT ACTIVO $$$", reply_markup=menu)

# ===== ADS =====
async def ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    wait = random.randint(30, 60)
    ad = random.choice(ADS)
    click_id = str(uuid.uuid4())

    cursor.execute("INSERT INTO ad_tracking VALUES (?,?,?,?,?)",
                   (click_id, user_id, ad, 0, int(time.time())))
    conn.commit()

    context.user_data["ad_time"] = time.time()
    context.user_data["ad_wait"] = wait
    context.user_data["ad_id"] = click_id

    await update.message.reply_text(f"📺 {ad}\n⏳ Espera {wait}s y escribe OK")

# ===== CONFIRM ADS =====
async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() != "ok":
        return

    start = context.user_data.get("ad_time")
    wait = context.user_data.get("ad_wait")

    if not start or time.time() - start < wait:
        return await update.message.reply_text("⏳ No cumpliste tiempo")

    cursor.execute("UPDATE users SET balance = balance + ?", (REWARD_AD,))
    conn.commit()

    await update.message.reply_text(f"💰 +{REWARD_AD}")

# ===== TAREAS =====
async def tareas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    task = random.choice(TASKS)
    click_id = str(uuid.uuid4())

    cursor.execute("INSERT INTO task_tracking VALUES (?,?,?,?,?)",
                   (click_id, user_id, task, 0, int(time.time())))
    conn.commit()

    context.user_data["task_time"] = time.time()
    context.user_data["task_id"] = click_id

    await update.message.reply_text(
        f"📋 TAREA:\n{task}\n\n"
        f"🔗 Validar aquí:\nhttp://TU_DOMINIO/track/{click_id}\n\n"
        f"⏳ Espera 40s y escribe OK"
    )

# ===== CONFIRM TAREA =====
async def confirm_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    start = context.user_data.get("task_time")
    task_id = context.user_data.get("task_id")

    if not start or time.time() - start < 40:
        return await update.message.reply_text("⏳ No cumpliste tiempo")

    row = cursor.execute("SELECT clicked FROM task_tracking WHERE id=?", (task_id,)).fetchone()

    if not row or row[0] == 0:
        return await update.message.reply_text("❌ No validaste")

    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?",
                   (REWARD_TASK, user_id))
    conn.commit()

    await update.message.reply_text(f"💸 +{REWARD_TASK}")

# ===== BALANCE =====
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bal = cursor.execute("SELECT balance FROM users WHERE user_id=?",
                         (update.effective_user.id,)).fetchone()[0]
    await update.message.reply_text(f"💰 ${bal:.6f}")

# ===== RETIRO =====
async def retirar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    bal = cursor.execute("SELECT balance FROM users WHERE user_id=?",
                         (user_id,)).fetchone()[0]

    if bal < MIN_RETIRO:
        return await update.message.reply_text("❌ Mínimo no alcanzado")

    cursor.execute("UPDATE users SET balance=0 WHERE user_id=?", (user_id,))
    conn.commit()

    await update.message.reply_text("💸 Retiro procesado")

# ===== BONUS =====
async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    today = str(datetime.now().date())

    last = cursor.execute("SELECT last_bonus FROM users WHERE user_id=?",
                          (user_id,)).fetchone()[0]

    if last == today:
        return await update.message.reply_text("❌ Ya reclamado")

    cursor.execute("UPDATE users SET balance=balance+?, last_bonus=? WHERE user_id=?",
                   (BONUS, today, user_id))
    conn.commit()

    await update.message.reply_text(f"🎁 +{BONUS}")

# ===== HANDLER =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text

    if "Balance" in t:
        await balance(update, context)
    elif "Ver anuncios" in t:
        await ads(update, context)
    elif "Tareas" in t:
        await tareas(update, context)
    elif "Bono" in t:
        await bonus(update, context)
    elif "Retirar" in t:
        await retirar(update, context)
    else:
        if context.user_data.get("task_id"):
            await confirm_task(update, context)
        else:
            await confirm(update, context)

# ===== WEB =====
app_web = Flask(__name__)

@app_web.route("/")
def home():
    return "BOT OK"

@app_web.route("/track/<click_id>")
def track(click_id):
    cursor.execute("UPDATE task_tracking SET clicked=1 WHERE id=?", (click_id,))
    conn.commit()
    return "OK"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=port)

# ===== MAIN FINAL =====
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle))

    from threading import Thread
    Thread(target=run_web, daemon=True).start()

    print("🤖 BOT + PANEL OK")

    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
