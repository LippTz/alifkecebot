#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════╗
#   🤖  AlifKecebot — Bot Multifungsi
#   Python 3.13+ & python-telegram-bot v20+
# ╚══════════════════════════════════════════════════════════╝

import os, sys, re, json, time, math, asyncio, threading, logging, io
from datetime import datetime, timedelta
from collections import defaultdict

def install(pkg):
    os.system(f"pip install {pkg} -q --break-system-packages 2>/dev/null || pip install {pkg} -q")

print("🔄 Mengecek library...")

try: import requests
except: print("Installing requests..."); install("requests"); import requests

try: from telegram import Update, ChatPermissions
except:
    print("Installing python-telegram-bot v20...")
    install("python-telegram-bot==20.7")
    from telegram import Update, ChatPermissions

try: from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
except: from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

try: from deep_translator import GoogleTranslator as DeepGoogleTranslator
except: print("Installing deep-translator..."); install("deep-translator"); from deep_translator import GoogleTranslator as DeepGoogleTranslator

try: import yt_dlp
except: print("Installing yt-dlp..."); install("yt-dlp"); import yt_dlp

try: from PIL import Image, ImageDraw, ImageFont
except: print("Installing Pillow..."); install("Pillow"); from PIL import Image, ImageDraw, ImageFont

print("✅ Semua library siap!\n")

# ══════════════════════════════════════════════════════
#  KONFIGURASI
# ══════════════════════════════════════════════════════
# Railway: set via Environment Variables di dashboard
# Lokal/Termux: bisa langsung isi di sini atau set env variable
BOT_TOKEN   = os.getenv("BOT_TOKEN",   "ISI_TOKEN_BOTMU_DI_SINI")
WEATHER_KEY = os.getenv("WEATHER_KEY", "ISI_API_KEY_OPENWEATHERMAP_DI_SINI")
OWNER_ID    = int(os.getenv("OWNER_ID", "0"))

# Railway pakai /tmp, Termux pakai ~/telegram_bot_data
DATA_DIR = os.getenv("DATA_DIR", 
    "/tmp/telegram_bot_data" if os.path.exists("/tmp") and not os.path.exists(os.path.expanduser("~/.termux"))
    else os.path.expanduser("~/telegram_bot_data")
)
REMIND_FILE  = os.path.join(DATA_DIR, "reminders.json")
WELCOME_FILE = os.path.join(DATA_DIR, "welcome.json")
SHOLAT_FILE  = os.path.join(DATA_DIR, "sholat_notif.json")
CUACA_FILE   = os.path.join(DATA_DIR, "cuaca_notif.json")
LOG_FILE     = os.path.join(DATA_DIR, "bot.log")
os.makedirs(DATA_DIR, exist_ok=True)

# ══════════════════════════════════════════════════════
#  LOGGING
# ══════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger("AlifKecebot")

# ══════════════════════════════════════════════════════
#  RATE LIMITER
# ══════════════════════════════════════════════════════
RATE_LIMIT  = 5
RATE_WINDOW = 10
_rate_data  = defaultdict(list)
_rate_lock  = threading.Lock()

def check_rate(user_id):
    now = time.time()
    with _rate_lock:
        _rate_data[user_id] = [t for t in _rate_data[user_id] if now - t < RATE_WINDOW]
        if len(_rate_data[user_id]) >= RATE_LIMIT:
            return False
        _rate_data[user_id].append(now)
        return True

# ══════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════
def load_json(path):
    try:
        with open(path) as f: return json.load(f)
    except: return {}

def save_json(path, data):
    with open(path, "w") as f: json.dump(data, f, indent=2, ensure_ascii=False)

async def is_admin(update, context):
    if update.effective_chat.type == "private": return True
    try:
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        return any(a.user.id == update.effective_user.id for a in admins)
    except: return False

async def send(update, text, parse_mode="Markdown"):
    try: await update.message.reply_text(text, parse_mode=parse_mode)
    except:
        try: await update.message.reply_text(text)
        except: pass

async def rate_guard(update):
    if not check_rate(update.effective_user.id):
        try: await update.message.reply_text("⏳ Pelan-pelan bro! Tunggu 10 detik dulu. 😅")
        except: pass
        return False
    return True

# ══════════════════════════════════════════════════════
#  HELP TEXT
# ══════════════════════════════════════════════════════
HELP_TEXT = (
    "\n╔══════════════════════════╗\n"
    "       🤖 *AlifKecebot* 🤖\n"
    "╚══════════════════════════╝\n\n"
    "Halo! Aku *AlifKecebot*, bot serbaguna siap bantu kamu! 🔥\n\n"
    "🌤 *CUACA & WAKTU*\n"
    "/cuaca `[kota]` — Info cuaca\n"
    "/waktu — Waktu WIB/WITA/WIT\n"
    "/cuacaon `[kota]` — Cuaca otomatis tiap pagi 06:00\n"
    "/cuacaoff — Matikan cuaca otomatis\n"
    "/sholat `[kota]` — Jadwal sholat\n"
    "/sholaton `[kota]` — Notif adzan otomatis\n"
    "/sholatoff — Matikan notif adzan\n\n"
    "🧮 *KALKULATOR*\n"
    "/hitung `[ekspresi]` — Contoh: /hitung 2+2\n"
    "/konversi `[nilai] [dari] [ke]` — /konversi 100 km mil\n\n"
    "⬇️ *DOWNLOADER*\n"
    "/yt `[URL]` — Audio YouTube (mp3)\n"
    "/ig `[URL]` — Video Instagram\n"
    "/tt `[URL]` — Video TikTok (no watermark)\n\n"
    "🔍 *SEARCH & TRANSLATE*\n"
    "/cari `[query]` — Cari via DuckDuckGo\n"
    "/tr `[kode] [teks]` — Contoh: /tr en halo dunia\n\n"
    "⏰ *REMINDER*\n"
    "/ingatkan `[menit] [pesan]` — Reminder sekali\n"
    "/ingatkan `[HH:MM] [pesan]` — Reminder jam tertentu\n"
    "/reminderku — Daftar remindermu\n"
    "/hapusreminder `[id]` — Hapus reminder\n\n"
    "📖 *AL-QURAN & DOA*\n"
    "/quran `[surah]:[ayat]` — Tampilkan ayat\n"
    "/quran `[surah]:[ayat]-[ayat]` — Range ayat (max 5)\n"
    "/doa `[nama]` — Doa harian\n"
    "/listdoa — Daftar semua doa\n"
    "/asmaul `[1-99]` — Asmaul Husna\n\n"
    "🎨 *STICKER MAKER*\n"
    "/sticker — Foto jadi sticker\n"
    "/stikerteks `[teks]` — Teks di TENGAH\n"
    "/stikerteksatas `[teks]` — Teks di ATAS\n"
    "/stikerteksbawah `[teks]` — Teks di BAWAH\n"
    "/stikertekskiri `[teks]` — Teks di KIRI\n"
    "/stikertekskanan `[teks]` — Teks di KANAN\n"
    "/stikerteksmiring `[teks]` — Teks MIRING 30°\n"
    "_Emoji di teks: otomatis dikonversi kalau font tidak support_\n\n"
    "👥 *MANAJEMEN GRUP* (admin only)\n"
    "/setwelcome `[pesan]` — Set pesan sambutan\n"
    "/welcome on/off — Aktifkan/matikan\n"
    "/kick /ban /unban — Reply pesan user\n"
    "/mute `[menit]` /unmute — Bungkam user\n"
    "/info — Info grup\n\n"
    "ℹ️ *LAINNYA*\n"
    "/ping — Cek bot aktif\n"
    "/id — Lihat ID kamu & grup\n"
    "/cutetext `[teks]` — Teks fancy\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "💡 *AlifKecebot* — Dibuat dengan ❤️\n"
    "🕌 _Sholat no 1, jangan sampai kelewat!_\n"
)

async def start(update, context):
    nama = update.effective_user.first_name
    logger.info(f"/start dari {update.effective_user.id} ({nama})")
    await send(update,
        f"Assalamualaikum *{nama}*! 👋\n\n"
        "Perkenalkan aku *AlifKecebot* 🤖\n"
        "Bot serbaguna siap membantu kamu!\n\n"
        "🕌 _Ingat, sholat no 1 ya!_\n\n"
        "Ketik /help untuk lihat semua fitur."
    )

async def help_cmd(update, context):
    if not await rate_guard(update): return
    await send(update, HELP_TEXT)

# ══════════════════════════════════════════════════════
#  CUACA & WAKTU
# ══════════════════════════════════════════════════════
async def cuaca(update, context):
    if not await rate_guard(update): return
    if not context.args:
        await send(update, "❌ Contoh: `/cuaca Jakarta`"); return
    kota = " ".join(context.args)
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={kota}&appid={WEATHER_KEY}&units=metric&lang=id"
        r   = requests.get(url, timeout=10).json()
        if r.get("cod") != 200:
            await send(update, f"❌ Kota *{kota}* tidak ditemukan!"); return
        desc  = r["weather"][0]["description"].title()
        temp  = r["main"]["temp"]
        feels = r["main"]["feels_like"]
        hum   = r["main"]["humidity"]
        wind  = r["wind"]["speed"]
        vis   = r.get("visibility", 0) // 1000
        await send(update,
            f"🌤 *Cuaca di {r['name']}, {r['sys']['country']}*\n\n"
            f"📋 Kondisi   : {desc}\n"
            f"🌡 Suhu      : {temp}°C (terasa {feels}°C)\n"
            f"💧 Kelembapan: {hum}%\n"
            f"💨 Angin     : {wind} m/s\n"
            f"👁 Jarak pandang: {vis} km"
        )
    except Exception as e:
        logger.error(f"cuaca: {e}")
        await send(update, f"❌ Gagal ambil data cuaca: `{str(e)[:80]}`")

async def waktu(update, context):
    if not await rate_guard(update): return
    now  = datetime.utcnow()
    wib  = (now + timedelta(hours=7)).strftime("%H:%M:%S")
    wita = (now + timedelta(hours=8)).strftime("%H:%M:%S")
    wit  = (now + timedelta(hours=9)).strftime("%H:%M:%S")
    tgl  = (now + timedelta(hours=7)).strftime("%A, %d %B %Y")
    await send(update,
        f"🕐 *Waktu Sekarang*\n\n"
        f"📅 {tgl}\n\n"
        f"🟢 WIB  (GMT+7) : `{wib}`\n"
        f"🔵 WITA (GMT+8) : `{wita}`\n"
        f"🔴 WIT  (GMT+9) : `{wit}`"
    )

# ── Cuaca Otomatis ─────────────────────────────────────
cuaca_notif = load_json(CUACA_FILE)

async def cuacaon(update, context):
    if not await rate_guard(update): return
    if not context.args:
        await send(update, "❌ Contoh: `/cuacaon Yogyakarta`"); return
    kota    = " ".join(context.args)
    chat_id = str(update.effective_chat.id)
    cuaca_notif[chat_id] = {"kota": kota.title(), "aktif": True}
    save_json(CUACA_FILE, cuaca_notif)
    await send(update,
        f"✅ *Cuaca Otomatis Aktif!*\n\n"
        f"📍 Kota: *{kota.title()}*\n"
        "🕕 Jadwal: Setiap pagi jam `06:00` WIB\n\n"
        "/cuacaoff untuk menonaktifkan."
    )

async def cuacaoff(update, context):
    if not await rate_guard(update): return
    chat_id = str(update.effective_chat.id)
    if chat_id in cuaca_notif:
        cuaca_notif[chat_id]["aktif"] = False
        save_json(CUACA_FILE, cuaca_notif)
        await send(update, "🔕 Cuaca otomatis dimatikan.")
    else:
        await send(update, "ℹ️ Cuaca otomatis belum diaktifkan.")

async def cuaca_checker(bot):
    terkirim = set()
    while True:
        now_wib = (datetime.utcnow() + timedelta(hours=7)).strftime("%H:%M")
        today   = datetime.now().strftime("%Y-%m-%d")
        if now_wib == "06:00":
            for chat_id, cfg in list(cuaca_notif.items()):
                if not cfg.get("aktif"): continue
                kunci = f"{chat_id}_{today}"
                if kunci in terkirim: continue
                kota = cfg.get("kota", "")
                try:
                    url = f"http://api.openweathermap.org/data/2.5/weather?q={kota}&appid={WEATHER_KEY}&units=metric&lang=id"
                    r   = requests.get(url, timeout=10).json()
                    if r.get("cod") == 200:
                        desc  = r["weather"][0]["description"].title()
                        temp  = r["main"]["temp"]
                        feels = r["main"]["feels_like"]
                        hum   = r["main"]["humidity"]
                        tgl   = datetime.now().strftime("%A, %d %B %Y")
                        await bot.send_message(
                            chat_id=int(chat_id),
                            parse_mode="Markdown",
                            text=(
                                f"🌅 *Selamat Pagi! Laporan Cuaca*\n\n"
                                f"📅 {tgl}\n"
                                f"📍 *{kota}*\n\n"
                                f"📋 {desc}\n"
                                f"🌡 Suhu     : {temp}°C (terasa {feels}°C)\n"
                                f"💧 Kelembapan: {hum}%\n\n"
                                "☀️ _Semangat hari ini! Jangan lupa sholat Subuh!_ 🕌"
                            )
                        )
                        terkirim.add(kunci)
                except Exception as e:
                    logger.error(f"cuaca_checker: {e}")
        for k in list(terkirim):
            if today not in k: terkirim.discard(k)
        await asyncio.sleep(30)

# ══════════════════════════════════════════════════════
#  SHOLAT & ADZAN
# ══════════════════════════════════════════════════════
sholat_notif = load_json(SHOLAT_FILE)

ADZAN_INFO = {
    "Fajr":    ("Subuh",   "🌅", "Fajar telah tiba! Bangkit dan sambut hari dengan sholat Subuh! 💪"),
    "Dhuhr":   ("Dzuhur",  "☀️", "Waktunya istirahat dan tunaikan sholat Dzuhur! 🙏"),
    "Asr":     ("Ashar",   "🌤", "Sore menjelang, yuk sholat Ashar! Jangan tunda-tunda! ⏰"),
    "Maghrib": ("Maghrib", "🌆", "Matahari terbenam! Segera sholat Maghrib, waktunya singkat! 🌇"),
    "Isha":    ("Isya",    "🌙", "Tutup hari dengan sholat Isya. Semoga penuh berkah! ✨"),
}

def get_jadwal_sholat(kota):
    try:
        today = datetime.now().strftime("%d-%m-%Y")
        url   = f"https://api.aladhan.com/v1/timingsByCity/{today}?city={kota}&country=Indonesia&method=11"
        r     = requests.get(url, timeout=10).json()
        if r.get("code") == 200:
            return r["data"]["timings"]
    except: pass
    return None

async def sholat(update, context):
    if not await rate_guard(update): return
    if not context.args:
        await send(update, "❌ Contoh: `/sholat Yogyakarta`"); return
    kota   = " ".join(context.args)
    today  = datetime.now().strftime("%d-%m-%Y")
    jadwal = get_jadwal_sholat(kota)
    if not jadwal:
        await send(update, f"❌ Kota *{kota}* tidak ditemukan!"); return
    t = jadwal
    await send(update,
        f"🕌 *Jadwal Sholat — {kota.title()}*\n"
        f"📅 {today}\n\n"
        f"🌅 Subuh   : `{t['Fajr']}`\n"
        f"🌄 Syuruq  : `{t['Sunrise']}`\n"
        f"☀️ Dzuhur  : `{t['Dhuhr']}`\n"
        f"🌤 Ashar   : `{t['Asr']}`\n"
        f"🌆 Maghrib : `{t['Maghrib']}`\n"
        f"🌙 Isya    : `{t['Isha']}`\n"
        f"🌜 Tengah Malam: `{t['Midnight']}`"
    )

async def sholaton(update, context):
    if not await rate_guard(update): return
    if not context.args:
        await send(update, "❌ Contoh: `/sholaton Yogyakarta`"); return
    kota    = " ".join(context.args)
    chat_id = str(update.effective_chat.id)
    await send(update, f"⏳ Mengecek jadwal sholat *{kota.title()}*...")
    jadwal = get_jadwal_sholat(kota)
    if not jadwal:
        await send(update, f"❌ Kota *{kota}* tidak ditemukan!"); return
    sholat_notif[chat_id] = {"kota": kota.title(), "aktif": True}
    save_json(SHOLAT_FILE, sholat_notif)
    t = jadwal
    await send(update,
        f"✅ *Notifikasi Adzan Aktif!*\n\n"
        f"📍 Kota: *{kota.title()}*\n\n"
        f"🌅 Subuh   : `{t['Fajr']}`\n"
        f"☀️ Dzuhur  : `{t['Dhuhr']}`\n"
        f"🌤 Ashar   : `{t['Asr']}`\n"
        f"🌆 Maghrib : `{t['Maghrib']}`\n"
        f"🌙 Isya    : `{t['Isha']}`\n\n"
        "🔔 *AlifKecebot* akan mengingatkanmu setiap waktu sholat!\n"
        "_Ketik /sholatoff untuk menonaktifkan._"
    )

async def sholatoff(update, context):
    if not await rate_guard(update): return
    chat_id = str(update.effective_chat.id)
    if chat_id in sholat_notif:
        sholat_notif[chat_id]["aktif"] = False
        save_json(SHOLAT_FILE, sholat_notif)
        await send(update, "🔕 Notifikasi adzan dimatikan.")
    else:
        await send(update, "ℹ️ Notifikasi adzan belum diaktifkan.")

async def adzan_checker(bot):
    terkirim = {}
    while True:
        now_str = (datetime.utcnow() + timedelta(hours=7)).strftime("%H:%M")
        today   = datetime.now().strftime("%Y-%m-%d")
        for chat_id, cfg in list(sholat_notif.items()):
            if not cfg.get("aktif"): continue
            kota   = cfg.get("kota", "")
            jadwal = get_jadwal_sholat(kota)
            if not jadwal: continue
            for key, (nama, emot, pesan) in ADZAN_INFO.items():
                wt = jadwal.get(key, "")[:5]
                if wt == now_str:
                    kunci = f"{chat_id}_{key}_{today}"
                    if kunci in terkirim: continue
                    terkirim[kunci] = True
                    try:
                        await bot.send_message(
                            chat_id=int(chat_id),
                            parse_mode="Markdown",
                            text=(
                                f"{emot}{emot}{emot}{emot}{emot}\n\n"
                                f"🕌 *ALLAHU AKBAR!* 🕌\n\n"
                                f"{emot} *Waktu {nama} telah tiba!* {emot}\n\n"
                                f"📍 _{kota}_  🕐 `{wt}` WIB\n\n"
                                f"{pesan}\n\n"
                                "🤲 *_Yuk segera ambil wudhu!_*\n\n"
                                f"{emot}{emot}{emot}{emot}{emot}"
                            )
                        )
                    except Exception as e:
                        logger.error(f"adzan_checker: {e}")
        for k in list(terkirim):
            if today not in k: del terkirim[k]
        await asyncio.sleep(30)

# ══════════════════════════════════════════════════════
#  AL-QURAN & DOA
# ══════════════════════════════════════════════════════
async def quran(update, context):
    if not await rate_guard(update): return
    if not context.args:
        await send(update, "❌ Contoh:\n`/quran 1:1` — Al-Fatihah ayat 1\n`/quran 2:255` — Ayat Kursi\n`/quran 1:1-7` — Range ayat (max 5)"); return
    arg = context.args[0]
    if ":" not in arg:
        await send(update, "❌ Format salah. Contoh: `/quran 2:255`"); return
    try:
        surah_str, ayat_str = arg.split(":", 1)
        surah = int(surah_str)
        if "-" in ayat_str:
            ayat_start, ayat_end = map(int, ayat_str.split("-"))
        else:
            ayat_start = ayat_end = int(ayat_str)
        info_r = requests.get(f"https://api.alquran.cloud/v1/surah/{surah}", timeout=10).json()
        if info_r.get("code") != 200:
            await send(update, f"❌ Surah {surah} tidak ditemukan! (1-114)"); return
        nama_surah = info_r["data"]["englishName"]
        nama_arab  = info_r["data"]["name"]
        msg = f"📖 *{nama_arab} ({nama_surah})*\n\n"
        for ayat in range(ayat_start, min(ayat_end + 1, ayat_start + 5)):
            r_ar = requests.get(f"https://api.alquran.cloud/v1/ayah/{surah}:{ayat}", timeout=10).json()
            r_id = requests.get(f"https://api.alquran.cloud/v1/ayah/{surah}:{ayat}/id.indonesian", timeout=10).json()
            if r_ar.get("code") != 200:
                msg += f"❌ Ayat {ayat} tidak ada.\n"; continue
            msg += f"*Ayat {ayat}:*\n{r_ar['data']['text']}\n\n_{r_id['data']['text'] if r_id.get('code')==200 else '-'}_\n\n"
        await send(update, msg)
    except Exception as e:
        logger.error(f"quran: {e}")
        await send(update, f"❌ Gagal ambil ayat: `{str(e)[:80]}`")

DOA_LIST = {
    "pagi":         {"nama":"Doa Pagi Hari","arab":"أَصْبَحْنَا وَأَصْبَحَ الْمُلْكُ لِلَّهِ وَالْحَمْدُ لِلَّهِ","latin":"Ash-bahnaa wa ash-bahal mulku lillaahi walhamdu lillaah","arti":"Kami berpagi hari dan kerajaan milik Allah, segala puji hanya bagi Allah."},
    "tidur":        {"nama":"Doa Sebelum Tidur","arab":"بِاسْمِكَ اللَّهُمَّ أَمُوتُ وَأَحْيَا","latin":"Bismikallaahumma amuutu wa ahyaa","arti":"Dengan nama-Mu ya Allah, aku mati dan aku hidup."},
    "makansebelum": {"nama":"Doa Sebelum Makan","arab":"اللَّهُمَّ بَارِكْ لَنَا فِيمَا رَزَقْتَنَا وَقِنَا عَذَابَ النَّارِ","latin":"Allaahumma baarik lanaa fiimaa razaqtanaa wa qinaa adzaaban naar","arti":"Ya Allah, berkahilah kami dalam rezeki yang Engkau berikan dan jagalah kami dari siksa neraka."},
    "makansesudah": {"nama":"Doa Sesudah Makan","arab":"الْحَمْدُ لِلَّهِ الَّذِي أَطْعَمَنَا وَسَقَانَا وَجَعَلَنَا مُسْلِمِينَ","latin":"Alhamdulillaahil ladzii ath-amanaa wa saqaanaa wa ja-alanaa muslimiin","arti":"Segala puji bagi Allah yang telah memberi kami makan, minum, dan menjadikan kami muslim."},
    "wudhu":        {"nama":"Doa Setelah Wudhu","arab":"أَشْهَدُ أَنْ لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ","latin":"Asyhadu allaa ilaaha illallaahu wahdahu laa syariika lah","arti":"Aku bersaksi bahwa tidak ada Tuhan selain Allah Yang Maha Esa, tidak ada sekutu bagi-Nya."},
    "bepergian":    {"nama":"Doa Bepergian","arab":"سُبْحَانَ الَّذِي سَخَّرَ لَنَا هَذَا وَمَا كُنَّا لَهُ مُقْرِنِينَ","latin":"Subhaanal ladzii sakhkhara lanaa haadzaa wa maa kunnaa lahu muqriniin","arti":"Maha Suci Allah yang telah menundukkan ini bagi kami, padahal kami sebelumnya tidak mampu."},
    "masukrumah":   {"nama":"Doa Masuk Rumah","arab":"اللَّهُمَّ إِنِّي أَسْأَلُكَ خَيْرَ الْمَوْلَجِ وَخَيْرَ الْمَخْرَجِ","latin":"Allaahumma innii as-aluka khayral mawlaji wa khayral makhraji","arti":"Ya Allah, aku memohon kepada-Mu sebaik-baik tempat masuk dan tempat keluar."},
    "kamarmandi":   {"nama":"Doa Masuk Kamar Mandi","arab":"اللَّهُمَّ إِنِّي أَعُوذُ بِكَ مِنَ الْخُبُثِ وَالْخَبَائِثِ","latin":"Allaahumma innii a-uudzu bika minal khubutsi wal khabaa-its","arti":"Ya Allah, aku berlindung kepada-Mu dari setan laki-laki dan setan perempuan."},
    "hujan":        {"nama":"Doa Ketika Hujan","arab":"اللَّهُمَّ صَيِّباً نَافِعاً","latin":"Allaahumma shayyiban naafi-an","arti":"Ya Allah, jadikanlah hujan ini hujan yang bermanfaat."},
    "belajar":      {"nama":"Doa Sebelum Belajar","arab":"رَبِّ زِدْنِي عِلْمًا وَارْزُقْنِي فَهْمًا","latin":"Rabbi zidnii ilmaa warzuqnii fahmaa","arti":"Ya Tuhanku, tambahkanlah ilmu kepadaku dan berikanlah aku pemahaman."},
}

async def doa(update, context):
    if not await rate_guard(update): return
    if not context.args:
        daftar = ", ".join(f"`{k}`" for k in DOA_LIST)
        await send(update, f"❌ Contoh: `/doa pagi`\n\nTersedia: {daftar}"); return
    key = "".join(context.args).lower()
    if key not in DOA_LIST:
        daftar = ", ".join(f"`{k}`" for k in DOA_LIST)
        await send(update, f"❌ Doa *{key}* tidak ada.\n\nTersedia: {daftar}"); return
    d = DOA_LIST[key]
    await send(update,
        f"🤲 *{d['nama']}*\n\n"
        f"*Arab:*\n{d['arab']}\n\n"
        f"*Latin:*\n_{d['latin']}_\n\n"
        f"*Artinya:*\n{d['arti']}"
    )

async def listdoa(update, context):
    if not await rate_guard(update): return
    msg = "🤲 *Daftar Doa yang Tersedia:*\n\n"
    for k, v in DOA_LIST.items():
        msg += f"• `/doa {k}` — {v['nama']}\n"
    await send(update, msg)

ASMAUL_HUSNA = [
    ("Ar-Rahman","الرَّحْمَنُ","Yang Maha Pengasih"),("Ar-Rahim","الرَّحِيمُ","Yang Maha Penyayang"),
    ("Al-Malik","الْمَلِكُ","Yang Maha Merajai"),("Al-Quddus","الْقُدُّوسُ","Yang Maha Suci"),
    ("As-Salam","السَّلَامُ","Yang Maha Memberi Kesejahteraan"),("Al-Mu'min","الْمُؤْمِنُ","Yang Maha Memberi Keamanan"),
    ("Al-Muhaimin","الْمُهَيْمِنُ","Yang Maha Mengatur"),("Al-Aziz","الْعَزِيزُ","Yang Maha Perkasa"),
    ("Al-Jabbar","الْجَبَّارُ","Yang Memiliki Kegagahan Mutlak"),("Al-Mutakabbir","الْمُتَكَبِّرُ","Yang Maha Megah"),
    ("Al-Khaliq","الْخَالِقُ","Yang Maha Pencipta"),("Al-Bari","الْبَارِئُ","Yang Maha Melepaskan"),
    ("Al-Musawwir","الْمُصَوِّرُ","Yang Maha Membentuk Rupa"),("Al-Ghaffar","الْغَفَّارُ","Yang Maha Pengampun"),
    ("Al-Qahhar","الْقَهَّارُ","Yang Maha Menundukkan"),("Al-Wahhab","الْوَهَّابُ","Yang Maha Pemberi Karunia"),
    ("Al-Razzaq","الرَّزَّاقُ","Yang Maha Pemberi Rezeki"),("Al-Fattah","الْفَتَّاحُ","Yang Maha Pembuka Rahmat"),
    ("Al-Alim","الْعَلِيمُ","Yang Maha Mengetahui"),("Al-Qabidh","الْقَابِضُ","Yang Maha Menyempitkan"),
    ("Al-Basith","الْبَاسِطُ","Yang Maha Melapangkan"),("Al-Khafidh","الْخَافِضُ","Yang Maha Merendahkan"),
    ("Ar-Rafi","الرَّافِعُ","Yang Maha Meninggikan"),("Al-Mu'izz","الْمُعِزُّ","Yang Maha Memuliakan"),
    ("Al-Mudzill","الْمُذِلُّ","Yang Maha Menghinakan"),("As-Sami","السَّمِيعُ","Yang Maha Mendengar"),
    ("Al-Bashir","الْبَصِيرُ","Yang Maha Melihat"),("Al-Hakam","الْحَكَمُ","Yang Maha Menetapkan"),
    ("Al-Adl","الْعَدْلُ","Yang Maha Adil"),("Al-Lathif","اللَّطِيفُ","Yang Maha Lembut"),
    ("Al-Khabir","الْخَبِيرُ","Yang Maha Mengenal"),("Al-Halim","الْحَلِيمُ","Yang Maha Penyantun"),
    ("Al-Adzim","الْعَظِيمُ","Yang Maha Agung"),("Al-Ghafur","الْغَفُورُ","Yang Maha Memberi Pengampunan"),
    ("As-Syakur","الشَّكُورُ","Yang Maha Pembalas Budi"),("Al-Ali","الْعَلِيُّ","Yang Maha Tinggi"),
    ("Al-Kabir","الْكَبِيرُ","Yang Maha Besar"),("Al-Hafidz","الْحَفِيظُ","Yang Maha Menjaga"),
    ("Al-Muqit","الْمُقِيتُ","Yang Maha Pemberi Kecukupan"),("Al-Hasib","الْحَسِيبُ","Yang Maha Membuat Perhitungan"),
    ("Al-Jalil","الْجَلِيلُ","Yang Maha Luhur"),("Al-Karim","الْكَرِيمُ","Yang Maha Pemurah"),
    ("Ar-Raqib","الرَّقِيبُ","Yang Maha Mengawasi"),("Al-Mujib","الْمُجِيبُ","Yang Maha Mengabulkan"),
    ("Al-Wasi","الْوَاسِعُ","Yang Maha Luas"),("Al-Hakim","الْحَكِيمُ","Yang Maha Bijaksana"),
    ("Al-Wadud","الْوَدُودُ","Yang Maha Mengasihi"),("Al-Majid","الْمَجِيدُ","Yang Maha Mulia"),
    ("Al-Ba'its","الْبَاعِثُ","Yang Maha Membangkitkan"),("As-Syahid","الشَّهِيدُ","Yang Maha Menyaksikan"),
    ("Al-Haqq","الْحَقُّ","Yang Maha Benar"),("Al-Wakil","الْوَكِيلُ","Yang Maha Memelihara"),
    ("Al-Qawiyy","الْقَوِيُّ","Yang Maha Kuat"),("Al-Matin","الْمَتِينُ","Yang Maha Kukuh"),
    ("Al-Waliyy","الْوَلِيُّ","Yang Maha Melindungi"),("Al-Hamid","الْحَمِيدُ","Yang Maha Terpuji"),
    ("Al-Muhshi","الْمُحْصِيُ","Yang Maha Menghitung"),("Al-Mubdi","الْمُبْدِئُ","Yang Maha Memulai"),
    ("Al-Mu'id","الْمُعِيدُ","Yang Maha Mengembalikan Kehidupan"),("Al-Muhyi","الْمُحْيِي","Yang Maha Menghidupkan"),
    ("Al-Mumit","الْمُمِيتُ","Yang Maha Mematikan"),("Al-Hayy","الْحَيُّ","Yang Maha Hidup"),
    ("Al-Qayyum","الْقَيُّومُ","Yang Maha Mandiri"),("Al-Wajid","الْوَاجِدُ","Yang Maha Penemu"),
    ("Al-Majid","الْمَاجِدُ","Yang Maha Mulia"),("Al-Wahid","الْوَاحِدُ","Yang Maha Tunggal"),
    ("Al-Ahad","الْاَحَدُ","Yang Maha Esa"),("As-Samad","الصَّمَدُ","Yang Maha Dibutuhkan"),
    ("Al-Qadir","الْقَادِرُ","Yang Maha Menentukan"),("Al-Muqtadir","الْمُقْتَدِرُ","Yang Maha Berkuasa"),
    ("Al-Muqaddim","الْمُقَدِّمُ","Yang Maha Mendahulukan"),("Al-Mu'akhkhir","الْمُؤَخِّرُ","Yang Maha Mengakhirkan"),
    ("Al-Awwal","الْاَوَّلُ","Yang Maha Awal"),("Al-Akhir","الْاٰخِرُ","Yang Maha Akhir"),
    ("Az-Zahir","الظَّاهِرُ","Yang Maha Nyata"),("Al-Bathin","الْبَاطِنُ","Yang Maha Ghaib"),
    ("Al-Wali","الْوَالِي","Yang Maha Memerintah"),("Al-Muta'ali","الْمُتَعَالِي","Yang Maha Tinggi"),
    ("Al-Barr","الْبَرُّ","Yang Maha Penderma"),("At-Tawwab","التَّوَّابُ","Yang Maha Penerima Tobat"),
    ("Al-Muntaqim","الْمُنْتَقِمُ","Yang Maha Pemberi Balasan"),("Al-Afuww","الْعَفُوُّ","Yang Maha Pemaaf"),
    ("Ar-Ra'uf","الرَّؤُوفُ","Yang Maha Pengasuh"),("Malikul-Mulk","مَالِكُ الْمُلْكِ","Yang Maha Penguasa Kerajaan"),
    ("Dzul-Jalali wal-Ikram","ذُوالْجَلَالِ وَالْاِكْرَامِ","Pemilik Kebesaran dan Kemuliaan"),
    ("Al-Muqsith","الْمُقْسِطُ","Yang Maha Pemberi Keadilan"),("Al-Jami","الْجَامِعُ","Yang Maha Mengumpulkan"),
    ("Al-Ghani","الْغَنِيُّ","Yang Maha Kaya"),("Al-Mughni","الْمُغْنِي","Yang Maha Pemberi Kekayaan"),
    ("Al-Mani","الْمَانِعُ","Yang Maha Mencegah"),("Ad-Dharr","الضَّارُّ","Yang Maha Penimpa Kemudharatan"),
    ("An-Nafi","النَّافِعُ","Yang Maha Memberi Manfaat"),("An-Nur","النُّورُ","Yang Maha Bercahaya"),
    ("Al-Hadi","الْهَادِي","Yang Maha Pemberi Petunjuk"),("Al-Badi","الْبَدِيعُ","Yang Maha Pencipta"),
    ("Al-Baqi","الْبَاقِي","Yang Maha Kekal"),("Al-Warith","الْوَارِثُ","Yang Maha Pewaris"),
    ("Ar-Rasyid","الرَّشِيدُ","Yang Maha Pandai"),("As-Sabur","الصَّبُورُ","Yang Maha Sabar"),
]

async def asmaul(update, context):
    if not await rate_guard(update): return
    if not context.args or not context.args[0].isdigit():
        await send(update, "❌ Contoh: `/asmaul 1` sampai `/asmaul 99`"); return
    n = int(context.args[0])
    if not 1 <= n <= 99:
        await send(update, "❌ Nomor harus antara 1-99!"); return
    nama, arab, arti = ASMAUL_HUSNA[n-1]
    await send(update, f"✨ *Asmaul Husna ke-{n}*\n\n*{nama}*\n{arab}\n\n_{arti}_")

# ══════════════════════════════════════════════════════
#  STICKER MAKER
# ══════════════════════════════════════════════════════
EMOJI_TEXT = {
    "😂":"haha","😭":"nangis","🔥":"fire","💀":"skull","❤️":"love",
    "🥰":"sayang","😍":"wow","🤣":"ngakak","😊":"senyum","🙏":"amin",
    "👍":"oke","💪":"kuat","🎉":"hore","✨":"keren","😎":"kece",
    "🤔":"hmm","😅":"hehe","🤩":"mantap","😱":"waduh","🥺":"please",
    "😡":"marah","🤯":"gila","💯":"100","🚀":"gas","⚡":"cepet",
    "🎯":"target","👑":"sultan","💎":"diamond","🌙":"malam","⭐":"bintang",
    "😈":"devil","👻":"hantu","💩":"pup","🤡":"badut","😴":"ngantuk",
    "🍕":"pizza","🍜":"mie","🧋":"boba","☕":"kopi","🐸":"katak",
}

FONT_EMOJI_PATHS = [
    "/system/fonts/NotoColorEmoji.ttf",
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
]

def ada_font_emoji():
    return any(os.path.exists(p) for p in FONT_EMOJI_PATHS)

def konversi_emoji(teks):
    if ada_font_emoji(): return teks
    hasil = teks
    for em, kata in EMOJI_TEXT.items():
        hasil = hasil.replace(em, f"[{kata}]")
    return hasil

def cari_font(ukuran, butuh_emoji=False):
    kandidat = []
    if butuh_emoji: kandidat += FONT_EMOJI_PATHS
    kandidat += [
        "/system/fonts/NotoSansCJK-Regular.ttc",
        "/system/fonts/Roboto-Bold.ttf",
        "/system/fonts/DroidSans-Bold.ttf",
        "/data/data/com.termux/files/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for path in kandidat:
        if os.path.exists(path):
            try: return ImageFont.truetype(path, ukuran)
            except: pass
    return ImageFont.load_default()

def buat_sticker(img_bytes, teks=None, posisi="tengah", miring=False):
    img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    img.thumbnail((512, 512), Image.LANCZOS)
    kanvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    kanvas.paste(img, ((512-img.width)//2, (512-img.height)//2))
    if teks:
        W, H        = 512, 512
        teks_render = konversi_emoji(teks)
        ukuran_f    = max(20, min(72, int(400 / max(len(teks_render), 1))))
        punya_emoji = any(em in teks for em in EMOJI_TEXT)
        font        = cari_font(ukuran_f, butuh_emoji=punya_emoji)
        draw        = ImageDraw.Draw(kanvas)
        try:    bbox = draw.textbbox((0,0), teks_render, font=font)
        except: bbox = (0, 0, len(teks_render)*ukuran_f//2, ukuran_f)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        margin = 20
        if posisi == "atas":    tx, ty = (W-tw)//2, margin
        elif posisi == "bawah": tx, ty = (W-tw)//2, H-th-margin
        elif posisi == "kiri":  tx, ty = margin, (H-th)//2
        elif posisi == "kanan": tx, ty = W-tw-margin, (H-th)//2
        else:                   tx, ty = (W-tw)//2, (H-th)//2
        if miring:
            layer = Image.new("RGBA", (W,H), (0,0,0,0))
            ldraw = ImageDraw.Draw(layer)
            for dx in range(-3,4):
                for dy in range(-3,4): ldraw.text((tx+dx,ty+dy), teks_render, font=font, fill=(0,0,0,200))
            ldraw.text((tx,ty), teks_render, font=font, fill=(255,255,255,255))
            kanvas = Image.alpha_composite(kanvas, layer.rotate(30, resample=Image.BICUBIC, expand=False))
        else:
            for dx in range(-3,4):
                for dy in range(-3,4):
                    if dx or dy: draw.text((tx+dx,ty+dy), teks_render, font=font, fill=(0,0,0,200))
            draw.text((tx,ty), teks_render, font=font, fill=(255,255,255,255))
    out = io.BytesIO()
    kanvas.save(out, format="PNG")
    out.seek(0)
    return out.read()

async def _proses_sticker(update, context, teks=None, posisi="tengah", miring=False):
    foto = None
    if update.message.photo: foto = update.message.photo[-1]
    elif update.message.reply_to_message and update.message.reply_to_message.photo:
        foto = update.message.reply_to_message.photo[-1]
    if not foto:
        await send(update,
            "❌ Cara pakai:\n"
            "1. Kirim foto + ketik perintah di caption\n"
            "2. Atau reply foto lama dengan perintah ini\n\n"
            "_Contoh: kirim foto + caption `/stikerteks Halo 🔥`_"
        ); return
    await send(update, "⏳ Sedang membuat sticker...")
    try:
        file      = await context.bot.get_file(foto.file_id)
        img_bytes = await file.download_as_bytearray()
        loop      = asyncio.get_event_loop()
        sbytes    = await loop.run_in_executor(None, buat_sticker, bytes(img_bytes), teks, posisi, miring)
        sf        = io.BytesIO(sbytes); sf.name = "sticker.png"
        await update.message.reply_sticker(sf)
        logger.info(f"Sticker OK user={update.effective_user.id} posisi={posisi} miring={miring}")
        if teks and any(em in teks for em in EMOJI_TEXT) and not ada_font_emoji():
            await send(update, "💡 _Emoji dikonversi ke teks karena font emoji belum terinstall._")
    except Exception as e:
        logger.error(f"sticker: {e}")
        await send(update, f"❌ Gagal buat sticker: `{str(e)[:100]}`")

async def cmd_sticker(update, context):
    if not await rate_guard(update): return
    await _proses_sticker(update, context)
async def cmd_stikerteks(update, context):
    if not await rate_guard(update): return
    if not context.args: await send(update, "❌ Contoh: `/stikerteks Halo Bro! 🔥`"); return
    await _proses_sticker(update, context, teks=" ".join(context.args), posisi="tengah")
async def cmd_stikerteksatas(update, context):
    if not await rate_guard(update): return
    if not context.args: await send(update, "❌ Contoh: `/stikerteksatas Mantap!`"); return
    await _proses_sticker(update, context, teks=" ".join(context.args), posisi="atas")
async def cmd_stikerteksbawah(update, context):
    if not await rate_guard(update): return
    if not context.args: await send(update, "❌ Contoh: `/stikerteksbawah Keren!`"); return
    await _proses_sticker(update, context, teks=" ".join(context.args), posisi="bawah")
async def cmd_stikertekskiri(update, context):
    if not await rate_guard(update): return
    if not context.args: await send(update, "❌ Contoh: `/stikertekskiri Gas!`"); return
    await _proses_sticker(update, context, teks=" ".join(context.args), posisi="kiri")
async def cmd_stikertekskanan(update, context):
    if not await rate_guard(update): return
    if not context.args: await send(update, "❌ Contoh: `/stikertekskanan Gas!`"); return
    await _proses_sticker(update, context, teks=" ".join(context.args), posisi="kanan")
async def cmd_stikerteksmiring(update, context):
    if not await rate_guard(update): return
    if not context.args: await send(update, "❌ Contoh: `/stikerteksmiring Halo!`"); return
    await _proses_sticker(update, context, teks=" ".join(context.args), posisi="tengah", miring=True)

# ══════════════════════════════════════════════════════
#  KALKULATOR & KONVERSI
# ══════════════════════════════════════════════════════
SAFE_MATH = {"abs":abs,"round":round,"int":int,"float":float,"max":max,"min":min,"sum":sum,
    "sqrt":math.sqrt,"pow":math.pow,"log":math.log,"sin":math.sin,"cos":math.cos,"tan":math.tan,
    "pi":math.pi,"e":math.e,"__builtins__":{}}

async def hitung(update, context):
    if not await rate_guard(update): return
    if not context.args: await send(update, "❌ Contoh: `/hitung 2+2*3` atau `/hitung sqrt(16)`"); return
    expr = " ".join(context.args)
    try:
        hasil = eval(expr, SAFE_MATH)
        await send(update, f"🧮 *Kalkulator*\n\n`{expr}` = `{hasil}`")
    except ZeroDivisionError: await send(update, "❌ Tidak bisa dibagi nol!")
    except: await send(update, f"❌ Ekspresi tidak valid: `{expr}`")

KONVERSI_MAP = {
    ("km","mil"):0.621371,("mil","km"):1.60934,("km","m"):1000,("m","km"):0.001,
    ("m","cm"):100,("cm","m"):0.01,("m","ft"):3.28084,("ft","m"):0.3048,
    ("in","cm"):2.54,("cm","in"):0.393701,("kg","lb"):2.20462,("lb","kg"):0.453592,
    ("kg","g"):1000,("g","kg"):0.001,("g","oz"):0.035274,("oz","g"):28.3495,
    ("km/h","m/s"):0.277778,("m/s","km/h"):3.6,("km/h","mph"):0.621371,("mph","km/h"):1.60934,
    ("gb","mb"):1024,("mb","gb"):1/1024,("mb","kb"):1024,("kb","mb"):1/1024,
    ("tb","gb"):1024,("gb","tb"):1/1024,
}
async def konversi(update, context):
    if not await rate_guard(update): return
    if len(context.args) < 3: await send(update, "❌ Contoh: `/konversi 100 km mil`"); return
    try:
        nilai = float(context.args[0]); dari = context.args[1].lower(); ke = context.args[2].lower()
        if dari=="c" and ke=="f": hasil=nilai*9/5+32
        elif dari=="f" and ke=="c": hasil=(nilai-32)*5/9
        elif dari=="c" and ke=="k": hasil=nilai+273.15
        elif dari=="k" and ke=="c": hasil=nilai-273.15
        elif dari=="f" and ke=="k": hasil=(nilai-32)*5/9+273.15
        elif dari=="k" and ke=="f": hasil=(nilai-273.15)*9/5+32
        elif (dari,ke) in KONVERSI_MAP: hasil=nilai*KONVERSI_MAP[(dari,ke)]
        else: await send(update, f"❌ Konversi `{dari}` ke `{ke}` belum didukung."); return
        await send(update, f"📐 *Konversi*\n\n`{nilai} {dari}` = `{round(hasil,6)} {ke}`")
    except ValueError: await send(update, "❌ Nilai harus angka!")

# ══════════════════════════════════════════════════════
#  DOWNLOADER
# ══════════════════════════════════════════════════════
def download_media(url, fmt="bestaudio/best", ext="mp3"):
    opts = {"format":fmt,"outtmpl":os.path.join(DATA_DIR,"dl_%(title)s.%(ext)s"),
            "quiet":True,"no_warnings":True,"max_filesize":50*1024*1024}
    if ext=="mp3": opts["postprocessors"]=[{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":"128"}]
    with yt_dlp.YoutubeDL(opts) as ydl:
        info=ydl.extract_info(url,download=True); fname=ydl.prepare_filename(info)
        if ext=="mp3": fname=os.path.splitext(fname)[0]+".mp3"
        return fname, info.get("title","Video")

async def yt(update, context):
    if not await rate_guard(update): return
    if not context.args: await send(update, "❌ Contoh: `/yt https://youtube.com/watch?v=...`"); return
    url = context.args[0]; await send(update, "⏳ Mengunduh audio YouTube... Mohon tunggu.")
    try:
        loop=asyncio.get_event_loop(); fname,title=await loop.run_in_executor(None,download_media,url,"bestaudio/best","mp3")
        if os.path.exists(fname):
            with open(fname,"rb") as f: await update.message.reply_audio(f,title=title,caption=f"🎵 {title}")
            os.remove(fname)
        else: await send(update, "❌ File tidak ditemukan.")
    except Exception as e: logger.error(f"yt:{e}"); await send(update, f"❌ Gagal: `{str(e)[:100]}`")

async def ig(update, context):
    if not await rate_guard(update): return
    if not context.args: await send(update, "❌ Contoh: `/ig https://instagram.com/p/...`"); return
    url = context.args[0]; await send(update, "⏳ Mengunduh video Instagram...")
    try:
        loop=asyncio.get_event_loop(); fname,_=await loop.run_in_executor(None,download_media,url,"best","mp4")
        if os.path.exists(fname):
            with open(fname,"rb") as f: await update.message.reply_video(f,caption="📸 Instagram")
            os.remove(fname)
        else: await send(update, "❌ File tidak ditemukan.")
    except Exception as e: logger.error(f"ig:{e}"); await send(update, f"❌ Gagal: `{str(e)[:100]}`")

async def tt(update, context):
    if not await rate_guard(update): return
    if not context.args: await send(update, "❌ Contoh: `/tt https://tiktok.com/@.../video/...`"); return
    url = context.args[0]; await send(update, "⏳ Mengunduh video TikTok (no watermark)...")
    try:
        loop=asyncio.get_event_loop(); fname,_=await loop.run_in_executor(None,download_media,url,"best[ext=mp4]","mp4")
        if os.path.exists(fname):
            with open(fname,"rb") as f: await update.message.reply_video(f,caption="🎵 TikTok")
            os.remove(fname)
        else: await send(update, "❌ File tidak ditemukan.")
    except Exception as e: logger.error(f"tt:{e}"); await send(update, f"❌ Gagal: `{str(e)[:100]}`")

# ══════════════════════════════════════════════════════
#  SEARCH & TRANSLATE
# ══════════════════════════════════════════════════════
async def cari(update, context):
    if not await rate_guard(update): return
    if not context.args: await send(update, "❌ Contoh: `/cari cara buat nasi goreng`"); return
    query = " ".join(context.args)
    try:
        headers={"User-Agent":"Mozilla/5.0"}
        r=requests.get(f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}",headers=headers,timeout=10)
        results=re.findall(r'<a class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>.*?<a class="result__snippet"[^>]*>([^<]*)</a>',r.text,re.DOTALL)
        if not results:
            r2=re.findall(r'href="(https?://[^"]+)"[^>]*>(.+?)</a>',r.text)
            if r2:
                msg=f"🔍 *Hasil: {query}*\n\n"
                for i,(link,judul) in enumerate(r2[:5],1):
                    jc=re.sub(r'<[^>]+>','',judul).strip()
                    if jc: msg+=f"{i}. [{jc}]({link})\n\n"
                await send(update,msg); return
            await send(update,"❌ Tidak ada hasil."); return
        msg=f"🔍 *Hasil: {query}*\n\n"
        for i,(link,judul,snippet) in enumerate(results[:5],1):
            msg+=f"{i}. *{judul.strip()}*\n{snippet.strip()[:100]}\n[Buka]({link})\n\n"
        await send(update,msg)
    except Exception as e: logger.error(f"cari:{e}"); await send(update,f"❌ Gagal: `{str(e)[:100]}`")

LANG_MAP={"id":"Indonesia","en":"Inggris","ja":"Jepang","ko":"Korea","zh":"China","ar":"Arab",
    "fr":"Perancis","de":"Jerman","es":"Spanyol","it":"Italia","pt":"Portugis","ru":"Rusia","th":"Thailand","ms":"Malaysia"}

async def tr(update, context):
    if not await rate_guard(update): return
    if len(context.args)<2: await send(update,"❌ Contoh: `/tr en Halo dunia`\nKode: "+", ".join(LANG_MAP.keys())); return
    dest=context.args[0].lower(); teks=" ".join(context.args[1:])
    if dest=="auto": dest="id"
    try:
        hasil=DeepGoogleTranslator(source="auto",target=dest).translate(teks)
        await send(update,f"🌐 *Translate*\n\n*Teks asal:* {teks}\n*{LANG_MAP.get(dest,dest)}:* {hasil}")
    except Exception as e: logger.error(f"tr:{e}"); await send(update,f"❌ Gagal translate: `{str(e)[:100]}`")

# ══════════════════════════════════════════════════════
#  REMINDER
# ══════════════════════════════════════════════════════
reminders=load_json(REMIND_FILE); reminder_lock=threading.Lock()

def generate_rid(): return str(int(time.time()*1000))[-6:]

async def ingatkan(update, context):
    if not await rate_guard(update): return
    if len(context.args)<2: await send(update,"❌ Contoh:\n`/ingatkan 30 Minum obat`\n`/ingatkan 08:00 Sholat Subuh`"); return
    waktu_arg=context.args[0]; pesan=" ".join(context.args[1:])
    user_id=update.effective_user.id; chat_id=update.effective_chat.id; now=datetime.now()
    if ":" in waktu_arg:
        try:
            jam,menit=map(int,waktu_arg.split(":")); target=now.replace(hour=jam,minute=menit,second=0,microsecond=0)
            if target<=now: target+=timedelta(days=1)
            sisa_detik=(target-now).total_seconds(); waktu_str=target.strftime("%H:%M WIB")
        except: await send(update,"❌ Format jam salah. Contoh: `08:30`"); return
    elif waktu_arg.isdigit():
        menit_int=int(waktu_arg); sisa_detik=menit_int*60; target=now+timedelta(minutes=menit_int)
        waktu_str=f"{menit_int} menit lagi ({target.strftime('%H:%M')})"
    else: await send(update,"❌ Format waktu salah!"); return
    rid=generate_rid()
    with reminder_lock:
        reminders[rid]={"user_id":user_id,"chat_id":chat_id,"pesan":pesan,"target_ts":time.time()+sisa_detik,"waktu_str":waktu_str}
        save_json(REMIND_FILE,reminders)
    await send(update,f"⏰ Reminder diset!\n\n📝 Pesan: *{pesan}*\n🕐 Waktu: {waktu_str}\n🆔 ID: `{rid}`")

async def reminderku(update, context):
    if not await rate_guard(update): return
    uid=update.effective_user.id; aktif={rid:v for rid,v in reminders.items() if v["user_id"]==uid and v["target_ts"]>time.time()}
    if not aktif: await send(update,"📭 Kamu tidak punya reminder aktif."); return
    msg="⏰ *Reminder aktifmu:*\n\n"
    for rid,v in aktif.items():
        sisa=int((v["target_ts"]-time.time())/60); msg+=f"🆔 `{rid}` — *{v['pesan']}* (sisa {sisa} menit)\n"
    await send(update,msg)

async def hapusreminder(update, context):
    if not await rate_guard(update): return
    if not context.args: await send(update,"❌ Contoh: `/hapusreminder 123456`"); return
    rid=context.args[0]; uid=update.effective_user.id
    with reminder_lock:
        if rid in reminders and reminders[rid]["user_id"]==uid:
            del reminders[rid]; save_json(REMIND_FILE,reminders); await send(update,f"✅ Reminder `{rid}` dihapus!")
        else: await send(update,"❌ Reminder tidak ditemukan atau bukan milikmu.")

async def reminder_checker(bot):
    while True:
        now_ts=time.time(); to_del=[]
        with reminder_lock:
            for rid,v in list(reminders.items()):
                if now_ts>=v["target_ts"]:
                    try: await bot.send_message(chat_id=v["chat_id"],text=f"⏰ *REMINDER!*\n\n📝 {v['pesan']}",parse_mode="Markdown")
                    except: pass
                    to_del.append(rid)
            for rid in to_del: del reminders[rid]
            if to_del: save_json(REMIND_FILE,reminders)
        await asyncio.sleep(15)

# ══════════════════════════════════════════════════════
#  MANAJEMEN GRUP
# ══════════════════════════════════════════════════════
welcome_cfg=load_json(WELCOME_FILE)

async def setwelcome(update, context):
    if not await rate_guard(update): return
    if not await is_admin(update,context): await send(update,"❌ Hanya admin!"); return
    if not context.args: await send(update,"❌ Contoh: `/setwelcome Selamat datang {nama} di {grup}!`"); return
    chat_id=str(update.effective_chat.id); pesan=" ".join(context.args)
    welcome_cfg[chat_id]={"aktif":True,"pesan":pesan}; save_json(WELCOME_FILE,welcome_cfg)
    await send(update,f"✅ Welcome message diset!\n\nPreview:\n{pesan}")

async def welcome_toggle(update, context):
    if not await rate_guard(update): return
    if not await is_admin(update,context): await send(update,"❌ Hanya admin!"); return
    if not context.args: await send(update,"❌ `/welcome on` atau `/welcome off`"); return
    chat_id=str(update.effective_chat.id); status=context.args[0].lower()
    if chat_id not in welcome_cfg: welcome_cfg[chat_id]={"aktif":False,"pesan":"Selamat datang {nama} di {grup}!"}
    welcome_cfg[chat_id]["aktif"]=(status=="on"); save_json(WELCOME_FILE,welcome_cfg)
    await send(update,f"✅ Welcome {'diaktifkan' if status=='on' else 'dimatikan'}!")

async def new_member_handler(update, context):
    chat_id=str(update.effective_chat.id); cfg=welcome_cfg.get(chat_id,{})
    if not cfg.get("aktif"): return
    for member in update.message.new_chat_members:
        if member.is_bot: continue
        pesan=cfg.get("pesan","Selamat datang {nama} di {grup}!")
        pesan=pesan.replace("{nama}",f"*{member.first_name}*").replace("{grup}",f"*{update.effective_chat.title or 'grup ini'}*")
        await send(update,f"👋 {pesan}")

async def kick(update, context):
    if not await rate_guard(update): return
    if not await is_admin(update,context): await send(update,"❌ Hanya admin!"); return
    if not update.message.reply_to_message: await send(update,"❌ Reply pesan user yang mau di-kick!"); return
    try:
        user=update.message.reply_to_message.from_user
        await context.bot.ban_chat_member(update.effective_chat.id,user.id)
        await context.bot.unban_chat_member(update.effective_chat.id,user.id)
        await send(update,f"✅ *{user.first_name}* berhasil di-kick!")
    except Exception as e: await send(update,f"❌ Gagal kick: {e}")

async def ban(update, context):
    if not await rate_guard(update): return
    if not await is_admin(update,context): await send(update,"❌ Hanya admin!"); return
    if not update.message.reply_to_message: await send(update,"❌ Reply pesan user yang mau di-ban!"); return
    try:
        user=update.message.reply_to_message.from_user
        await context.bot.ban_chat_member(update.effective_chat.id,user.id)
        await send(update,f"🔨 *{user.first_name}* berhasil di-ban!")
    except Exception as e: await send(update,f"❌ Gagal ban: {e}")

async def unban(update, context):
    if not await rate_guard(update): return
    if not await is_admin(update,context): await send(update,"❌ Hanya admin!"); return
    if not update.message.reply_to_message: await send(update,"❌ Reply pesan user yang mau di-unban!"); return
    try:
        user=update.message.reply_to_message.from_user
        await context.bot.unban_chat_member(update.effective_chat.id,user.id)
        await send(update,f"✅ *{user.first_name}* berhasil di-unban!")
    except Exception as e: await send(update,f"❌ Gagal unban: {e}")

async def mute(update, context):
    if not await rate_guard(update): return
    if not await is_admin(update,context): await send(update,"❌ Hanya admin!"); return
    if not update.message.reply_to_message: await send(update,"❌ Reply pesan user yang mau di-mute!"); return
    try:
        user=update.message.reply_to_message.from_user
        menit=int(context.args[0]) if context.args and context.args[0].isdigit() else 60
        until=datetime.now()+timedelta(minutes=menit)
        await context.bot.restrict_chat_member(update.effective_chat.id,user.id,permissions=ChatPermissions(can_send_messages=False),until_date=until)
        await send(update,f"🔇 *{user.first_name}* di-mute *{menit} menit*!")
    except Exception as e: await send(update,f"❌ Gagal mute: {e}")

async def unmute(update, context):
    if not await rate_guard(update): return
    if not await is_admin(update,context): await send(update,"❌ Hanya admin!"); return
    if not update.message.reply_to_message: await send(update,"❌ Reply pesan user yang mau di-unmute!"); return
    try:
        user=update.message.reply_to_message.from_user
        await context.bot.restrict_chat_member(update.effective_chat.id,user.id,
            permissions=ChatPermissions(can_send_messages=True,can_send_media_messages=True,can_send_other_messages=True,can_add_web_page_previews=True))
        await send(update,f"🔊 *{user.first_name}* berhasil di-unmute!")
    except Exception as e: await send(update,f"❌ Gagal unmute: {e}")

async def info_grup(update, context):
    if not await rate_guard(update): return
    chat=update.effective_chat
    try: count=await context.bot.get_chat_member_count(chat.id)
    except: count="?"
    msg=f"ℹ️ *Info Grup*\n\n📛 Nama   : {chat.title}\n🆔 ID     : `{chat.id}`\n👥 Member : {count}\n📋 Tipe   : {chat.type}"
    if chat.username: msg+=f"\n🔗 Link   : @{chat.username}"
    await send(update,msg)

# ══════════════════════════════════════════════════════
#  LAINNYA
# ══════════════════════════════════════════════════════
async def ping(update, context):
    t1=time.time(); msg=await update.message.reply_text("🏓 Pong!"); t2=time.time()
    await msg.edit_text(f"🏓 Pong!\n⚡ Latency: `{round((t2-t1)*1000)}ms`",parse_mode="Markdown")

async def id_cmd(update, context):
    if not await rate_guard(update): return
    user=update.effective_user; chat=update.effective_chat
    msg=f"👤 *Info ID*\n\nUser ID  : `{user.id}`\nUsername : @{user.username or '-'}\nNama     : {user.first_name}\n"
    if chat.type!="private": msg+=f"\n💬 *Grup*\nChat ID  : `{chat.id}`\nNama Grup: {chat.title}"
    await send(update,msg)

FANCY_MAP={
    'a':'𝒶','b':'𝒷','c':'𝒸','d':'𝒹','e':'𝑒','f':'𝒻','g':'𝑔','h':'𝒽','i':'𝒾','j':'𝒿',
    'k':'𝓀','l':'𝓁','m':'𝓂','n':'𝓃','o':'𝑜','p':'𝓅','q':'𝓆','r':'𝓇','s':'𝓈','t':'𝓉',
    'u':'𝓊','v':'𝓋','w':'𝓌','x':'𝓍','y':'𝓎','z':'𝓏','A':'𝒜','B':'𝐵','C':'𝒞','D':'𝒟',
    'E':'𝐸','F':'𝐹','G':'𝒢','H':'𝐻','I':'𝐼','J':'𝒥','K':'𝒦','L':'𝐿','M':'𝑀','N':'𝒩',
    'O':'𝒪','P':'𝒫','Q':'𝒬','R':'𝑅','S':'𝒮','T':'𝒯','U':'𝒰','V':'𝒱','W':'𝒲','X':'𝒳','Y':'𝒴','Z':'𝒵',
}

async def cutetext(update, context):
    if not await rate_guard(update): return
    if not context.args: await send(update,"❌ Contoh: `/cutetext halo dunia`"); return
    await send(update, f"✨ `{''.join(FANCY_MAP.get(c,c) for c in ' '.join(context.args))}`")

# ══════════════════════════════════════════════════════
#  MESSAGE HANDLER
# ══════════════════════════════════════════════════════

async def handle_text(update, context):
    pass  # games dihapus

#  MAIN
# ══════════════════════════════════════════════════════
async def post_init(application):
    asyncio.create_task(reminder_checker(application.bot))
    asyncio.create_task(adzan_checker(application.bot))
    asyncio.create_task(cuaca_checker(application.bot))
    logger.info("Semua background task aktif!")

def main():
    if BOT_TOKEN == "ISI_TOKEN_BOTMU_DI_SINI":
        print("❌ ERROR: Isi BOT_TOKEN dulu!"); sys.exit(1)
    if OWNER_ID == 0:
        print("⚠️  OWNER_ID belum diisi!")

    logger.info("AlifKecebot starting...")
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    handlers = [
        ("start",            start),
        ("help",             help_cmd),
        ("cuaca",            cuaca),
        ("waktu",            waktu),
        ("cuacaon",          cuacaon),
        ("cuacaoff",         cuacaoff),
        ("sholat",           sholat),
        ("sholaton",         sholaton),
        ("sholatoff",        sholatoff),
        ("quran",            quran),
        ("doa",              doa),
        ("listdoa",          listdoa),
        ("asmaul",           asmaul),
        ("sticker",          cmd_sticker),
        ("stikerteks",       cmd_stikerteks),
        ("stikerteksatas",   cmd_stikerteksatas),
        ("stikerteksbawah",  cmd_stikerteksbawah),
        ("stikertekskiri",   cmd_stikertekskiri),
        ("stikertekskanan",  cmd_stikertekskanan),
        ("stikerteksmiring", cmd_stikerteksmiring),
        ("hitung",           hitung),
        ("konversi",         konversi),
        ("yt",               yt),
        ("ig",               ig),
        ("tt",               tt),
        ("cari",             cari),
        ("tr",               tr),
        ("ingatkan",         ingatkan),
        ("reminderku",       reminderku),
        ("hapusreminder",    hapusreminder),
        ("setwelcome",       setwelcome),
        ("welcome",          welcome_toggle),
        ("kick",             kick),
        ("ban",              ban),
        ("unban",            unban),
        ("mute",             mute),
        ("unmute",           unmute),
        ("info",             info_grup),
        ("ping",             ping),
        ("id",               id_cmd),
        ("cutetext",         cutetext),
    ]

    for cmd, func in handlers:
        app.add_handler(CommandHandler(cmd, func))

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Semua handler terdaftar.")
    print("✅ AlifKecebot berhasil terhubung!")
    print("🤖 Bot berjalan... Tekan Ctrl+C untuk berhenti.\n")

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
