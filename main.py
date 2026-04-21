import os
import sqlite3
import time
import random
import threading
from datetime import datetime
from flask import Flask, render_template_string, redirect
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if ADMIN_ID:
    ADMIN_ID = int(ADMIN_ID)

# ===== CONFIG =====
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
    ["💸 Retirar"]
], resize_keyboard=True)

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    await update.message.reply_text("🔥 BOT ACTIVO $$$", reply_markup=menu)

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

    await update.message.reply_text(f"🔗 {ad}\n⏳ {wait}s")

# ===== CONFIRM ADS =====
async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start = context.user_data.get("time")
    wait = context.user_data.get("wait")

    if not start:
        return

    if time.time() - start < wait:
        return

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
    msg = "📋 TAREAS DISPONIBLES:\n\n"
    for i, t in enumerate(TASKS, 1):
        msg += f"{i}. {t}\n\n"
    msg += "📩 Envía el número para validar"
    await update.message.reply_text(msg)

# ===== VALIDAR TAREA =====
async def validar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        return

    user_id = update.effective_user.id
    last_task = cursor.execute(
        "SELECT last_task FROM users WHERE user_id=?", (user_id,)
    ).fetchone()[0]

    if time.time() - last_task < 60:
        return await update.message.reply_text("⛔ Espera 1 minuto")

    cursor.execute(
        "UPDATE users SET balance=balance+?, last_task=? WHERE user_id=?",
        (REWARD_TASK, int(time.time()), user_id)
    )
    conn.commit()

    await update.message.reply_text(f"✅ +{REWARD_TASK}")

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
    await update.message.reply_text("Envía método + datos")

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

# ===== MENU =====
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await confirm(update, context)
        await validar(update, context)
        await wallet(update, context)

# ===== PANEL WEB =====
web = Flask(__name__)

@web.route("/")
def panel():
    users = cursor.execute("SELECT * FROM users").fetchall()
    retiros = cursor.execute("SELECT * FROM withdrawals WHERE status='pendiente'").fetchall()

    html = "<h1>PANEL</h1>"

    html += "<h2>Usuarios</h2>"
    for u in users:
        html += f"<p>{u}</p>"

    html += "<h2>Retiros</h2>"
    for r in retiros:
        html += f"<p>{r} <a href='/pagar/{r[0]}'>Pagar</a></p>"

    return html

@web.route("/pagar/<id>")
def pagar(id):
    cursor.execute("UPDATE withdrawals SET status='pagado' WHERE id=?", (id,))
    conn.commit()
    return redirect("/")

def run_web():
    web.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# ===== RUN =====
def main():
    global TOKEN

    if not TOKEN:
        print("❌ TOKEN no encontrado")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))

    threading.Thread(target=run_web).start()

    print("🔥 BOT + PANEL ONLINE")
    app.run_polling()


if __name__ == "__main__":
    main()
