import os
import sqlite3
import time
import random
import uuid
import threading
from datetime import datetime

from flask import Flask, redirect
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ===== CONFIG =====
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8466239666"))

BASE_URL = "https://bottelegram-production-5cfc.up.railway.app"
WHATSAPP = "https://chat.whatsapp.com/https://chat.whatsapp.com/GO3mMxh7PN1E2ntKq0KE6x?mode=gi_t"

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

    ref = None
    if context.args:
        try:
            ref = int(context.args[0])
        except:
            pass

    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, ref_by) VALUES (?,?)", (user_id, ref))

        if ref and ref != user_id:
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (REF_BONUS, ref))

    conn.commit()

    await update.message.reply_text(
        f"🔥 BOT ACTIVO $$$\n\nTu link:\nhttps://t.me/TU_BOT?start={user_id}",
        reply_markup=menu
    )

# ===== ADS =====
async def ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    ads_today, last_ad, progress = cursor.execute(
        "SELECT ads_today,last_ad,ads_progress FROM users WHERE user_id=?",
        (user_id,)
    ).fetchone()

    if ads_today >= LIMITE_ADS:
        return await update.message.reply_text("❌ Límite diario")

    if time.time() - last_ad < 10:
        return await update.message.reply_text("⏳ Espera")

    wait = random.randint(35, 108)
    ad = random.choice(ADS)

    click_id = str(uuid.uuid4())

    cursor.execute("""
    INSERT INTO ad_tracking (id, user_id, ad, timestamp)
    VALUES (?,?,?,?)
    """, (click_id, user_id, ad, int(time.time())))
    conn.commit()

    context.user_data["time"] = time.time()
    context.user_data["wait"] = wait
    context.user_data["click_id"] = click_id

    cursor.execute("UPDATE users SET last_ad=? WHERE user_id=?", (int(time.time()), user_id))
    conn.commit()

    track_url = f"{BASE_URL}/track/{click_id}"

    await update.message.reply_text(
        f"🔗 {track_url}\n\n⏳ Espera {wait}s y escribe OK\n\nProgreso: {progress}/{ADS_REQUIRED}"
    )

# ===== CONFIRM =====
async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() != "ok":
        return

    start = context.user_data.get("time")
    wait = context.user_data.get("wait")
    click_id = context.user_data.get("click_id")

    if not start or time.time() - start < wait:
        return await update.message.reply_text("⏳ No completaste el tiempo")

    if not click_id:
        return

    row = cursor.execute("SELECT clicked FROM ad_tracking WHERE id=?", (click_id,)).fetchone()

    if not row:
        return await update.message.reply_text("❌ Error")

    if row[0] == 0:
        return await update.message.reply_text("❌ Debes abrir el link")

    user_id = update.effective_user.id

    cursor.execute("UPDATE users SET ads_progress = ads_progress + 1 WHERE user_id=?", (user_id,))
    progress = cursor.execute("SELECT ads_progress FROM users WHERE user_id=?", (user_id,)).fetchone()[0]

    if progress >= ADS_REQUIRED:
        reward = REWARD_AD * ADS_REQUIRED
        cursor.execute("""
        UPDATE users SET balance = balance + ?, ads_progress = 0, ads_today = ads_today + 1
        WHERE user_id=?
        """, (reward, user_id))

        await update.message.reply_text(f"💸 GANASTE {reward}")
    else:
        await update.message.reply_text(f"✅ ({progress}/{ADS_REQUIRED})")

    conn.commit()
    context.user_data.clear()

# ===== EXTRA =====
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bal = cursor.execute("SELECT balance FROM users WHERE user_id=?", (update.effective_user.id,)).fetchone()[0]
    await update.message.reply_text(f"💰 ${bal:.6f}")

async def grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"👥 {WHATSAPP}")

async def ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top = cursor.execute("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10").fetchall()
    msg = "🏆 TOP:\n\n"
    for i, u in enumerate(top, 1):
        msg += f"{i}. {u[0]} - ${u[1]:.4f}\n"
    await update.message.reply_text(msg)

async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    today = str(datetime.now().date())
    last = cursor.execute("SELECT last_bonus FROM users WHERE user_id=?", (user_id,)).fetchone()[0]

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
    elif "Bono" in t:
        await bonus(update, context)
    elif "Ranking" in t:
        await ranking(update, context)
    elif "Grupo" in t:
        await grupo(update, context)
    else:
        await confirm(update, context)

# ===== WEB =====
app_web = Flask(__name__)

@app_web.route("/track/<click_id>")
def track(click_id):
    row = cursor.execute("SELECT ad FROM ad_tracking WHERE id=?", (click_id,)).fetchone()

    if not row:
        return "Error"

    ad_url = row[0]

    cursor.execute("UPDATE ad_tracking SET clicked=1 WHERE id=?", (click_id,))
    conn.commit()

    return redirect(ad_url)

@app_web.route("/")
def home():
    users = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    clicks = cursor.execute("SELECT COUNT(*) FROM ad_tracking").fetchone()[0]
    clicks_ok = cursor.execute("SELECT COUNT(*) FROM ad_tracking WHERE clicked=1").fetchone()[0]

    return f"""
    <h1>🚀 PANEL</h1>
    <p>Usuarios: {users}</p>
    <p>Clicks: {clicks}</p>
    <p>Clicks reales: {clicks_ok}</p>
    """

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=port)

# ===== MAIN =====
def main():
    import threading

    def run_bot():
        app = ApplicationBuilder().token(TOKEN).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT, handle))

        print("🤖 BOT ACTIVO")
        app.run_polling()

    # hilo bot
    threading.Thread(target=run_bot).start()

    # servidor web (principal)
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=port)
