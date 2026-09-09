import asyncio
import csv
from datetime import datetime
import json
import os
import re
from typing import Any, Dict, List, Set
import urllib.parse
import urllib.request
from playwright.async_api import async_playwright

# ==========================================================
# ⚙️ تنظیمات اسکرپر Duck Store (بدون تداخل فیلتر)
# ==========================================================
CONFIG = {
    # فاز ۱: گیفت‌های تخفیف‌دار بازار (بدون محدودیت سقف قیمت تا گیفت‌های تخفیفی پیدا شوند)
    "DISCOUNT_URL": "https://marketapp.org/rent/?tab=market&sort_by=price_per_day_desc&subtab=gifts&view=grid",
    # فاز ۲: ارزان‌ترین گیفت‌های کف‌قیمت مارکت (مرتب‌شده از کمترین قیمت روزانه)
    "CHEAP_URL": "https://marketapp.org/rent/?tab=market&sort_by=price_per_day_asc&subtab=gifts&view=grid&max_price=0.01",
    "TARGET_DEALS_COUNT": 150,       # ۱۵۰ گیفت تخفیفی
    "CHEAP_DEALS_COUNT": 100,        # ۱۰۰ گیفت ارزان
    "MIN_DISCOUNT": 5,
    "MAX_DISCOUNT": 50,
    "TARGET_COLLECTION": "",
    "BASE_DOMAIN": "https://marketapp.org",
    "EXPORT_HTML": "index.html",
    "EXPORT_JSON": "discounts.json",
    "EXPORT_CSV": "discounts.csv",
    "WORKER_URL": "https://duck-api.ali-zanjani2007.workers.dev",
    "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN", ""),
    "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID", ""),
}

# دریافت داینامیک تنظیمات شکارچی هوشمند
def load_hunter_config_from_worker():
    global CONFIG
    try:
        req = urllib.request.Request(f"{CONFIG['WORKER_URL']}/api/settings", headers={"User-Agent": "DuckHunter"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            hunter = data.get("hunterConfig", {})
            if hunter:
                print("🎯 تنظیمات شکارچی از پنل دریافت شد:")
                col = hunter.get("collection", "").strip()
                CONFIG["TARGET_COLLECTION"] = col
                CONFIG["MIN_DISCOUNT"] = int(hunter.get("minDiscount", 5))
                CONFIG["MAX_DISCOUNT"] = int(hunter.get("maxDiscount", 50))
                CONFIG["TARGET_DEALS_COUNT"] = int(hunter.get("targetCount", 150))
                print(f"   • هدف فاز ۱: {CONFIG['TARGET_DEALS_COUNT']} گیفت تخفیفی")
                print(f"   • هدف فاز ۲: {CONFIG['CHEAP_DEALS_COUNT']} گیفت ارزان")
                return
    except Exception as e:
        print(f"⚠️ دریافت تنظیمات با خطا مواجه شد (استفاده از پیش‌فرض): {e}")

load_hunter_config_from_worker()

# کاتالوگ پشتیبان کامل و باکیفیت
REAL_TELEGRAM_FALLBACK_GIFTS = [
    {
        "name": "Plush Pepe #2825",
        "gift_title": "Plush Pepe",
        "number": "2825",
        "price_ton": "0.01",
        "image_url": "https://i2.anton.market/3SHMDVNMcpuaDG5ZnWdghhw4eByUrQrzl4Lz-ysNwwA/rs:fill:300:300:1/g:ce/czM6Ly9tYXJrZXRhcHAvYy9FUUE0MDFRcXBYdEJud0lhRGJGandkNXlYZlAybVlpQ3VzYkozWmN3OWVYUjlDcUwvOTBkNDNiMDBiNTVmOTA0MWQ4Y2JlOWMwNDI2N2Y4ZDgud2VicA",
        "tg_link": "https://t.me/nft/PlushPepe-2825",
        "market_link": "https://marketapp.org/rent/?subtab=gifts",
        "bg_color": "#182a1b",
        "rarity": "🎯 خاص (#2825)",
    },
    {
        "name": "Eternal Rose #7077",
        "gift_title": "Eternal Rose",
        "number": "7077",
        "price_ton": "0.01",
        "image_url": "https://i2.anton.market/b32fmE813CAOkRPrFkxDLWvxupaeOwXbnF0yCjelE1I/rs:fill:300:300:1/g:ce/czM6Ly9tYXJrZXRhcHAvYy9FUUR1bXkzYm5aWXpWNGJTV01TU1prbVhxeDUwWHVINWQ5UmxYX3lFaTJGTmxpdmsvZWQ0YzBmY2ZmM2IwODM4ZGNhMzEyMDAyYjVlN2ZmM2Eud2VicA",
        "tg_link": "https://t.me/nft/EternalRose-7077",
        "market_link": "https://marketapp.org/rent/?subtab=gifts",
        "bg_color": "#28161b",
        "rarity": "💎 زیر 10000",
    },
    {
        "name": "Record Player #4071",
        "gift_title": "Record Player",
        "number": "4071",
        "price_ton": "0.01",
        "image_url": "https://i2.anton.market/tJrCyprPqBxIHyzPIq86lwZljkiDsLGzcaICRlzwmUE/rs:fill:300:300:1/g:ce/czM6Ly9tYXJrZXRhcHAvYy9FUUNCS19KQkFTQUE1WFZ6MUQxN1BuLS1rUWFNV20wYjl3UmVWdHNFZFJPNFRneTkvZWQ1ZGQ2NmJkN2IxNzkxNjJkOTRiNmM4MDMyZGIwYmUud2VicA",
        "tg_link": "https://t.me/nft/RecordPlayer-4071",
        "market_link": "https://marketapp.org/rent/?subtab=gifts",
        "bg_color": "#241f17",
        "rarity": "",
    },
    {
        "name": "Astronaut Duck #412",
        "gift_title": "Astronaut Duck",
        "number": "412",
        "price_ton": "0.01",
        "image_url": "https://i2.anton.market/S8hA0eCcNKeKLNHNRblAUC-N6U1g9n2fzK4rpu1SGy4/rs:fill:300:300:1/g:ce/czM6Ly9tYXJrZXRhcHAvYy9FUURJcnVTVHl4dnE2MGdVSDhqMmtrajNxem9CckJhSnk5V2tLYmVOTlJhc1dlNGovZjU0MDE1ZjYxY2ZkYmMzNjU4NDRlYzQ5MmU3NjQ0YmUud2VicA",
        "tg_link": "https://t.me/nft/AstronautDuck-412",
        "market_link": "https://marketapp.org/rent/?subtab=gifts",
        "bg_color": "#16202c",
        "rarity": "💎 زیر 1000",
    },
    {
        "name": "Santa Hat #88",
        "gift_title": "Santa Hat",
        "number": "88",
        "price_ton": "0.01",
        "image_url": "https://i2.anton.market/f8GBAj549v1rZmzzpYSz7eIBy7M_G5lV6SH4LOSVTQs/rs:fill:300:300:1/g:ce/czM6Ly9tYXJrZXRhcHAvYy9FUUN5QU1rYjZiTnlObEtQSDB0SmJ1YmsxVlZqQVNxeXE5c1p3a0o4QWJ4TWt4eFUvNWRhMjliZjcyMjFjZTkxYTA5ZDg2NzY0ZTc0Y2VkZTQud2VicA",
        "tg_link": "https://t.me/nft/SantaHat-88",
        "market_link": "https://marketapp.org/rent/?subtab=gifts",
        "bg_color": "#281717",
        "rarity": "👑 زیر 100",
    },
    {
        "name": "Diamond Ring #1024",
        "gift_title": "Diamond Ring",
        "number": "1024",
        "price_ton": "0.01",
        "image_url": "https://i2.anton.market/tPaFlmsoXLLxuGRMZeyViQOpr80PBsyZbjavilZTkks/rs:fill:300:300:1/g:ce/czM6Ly9tYXJrZXRhcHAvYy9FUURjMDhZeHpaV3RsS0FvaFN5Yk5jM2tYQWtBUFB0SGNoLWpZX0U2S01RM2IxbW4vYjFjY2FiMTI0NWEyYTYwYjUwZTNmZDExZWZiNzFmZGYud2VicA",
        "tg_link": "https://t.me/nft/DiamondRing-1024",
        "market_link": "https://marketapp.org/rent/?subtab=gifts",
        "bg_color": "#1e182a",
        "rarity": "",
    }
]

def detect_rarity_badge(number_str: str) -> str:
    try: num = int(re.sub(r"\D", "", str(number_str)))
    except ValueError: return ""
    s = str(num)
    if num < 100: return "👑 زیر 100"
    if num < 1000: return "💎 زیر 1000"
    if len(s) >= 3 and len(set(s)) == 1: return f"✨ رند (#{s})"
    if s in ["123", "1234", "777", "888", "999"]: return f"🎯 خاص (#{s})"
    return ""

def clean_collection_title(raw_title: str) -> str:
    if not raw_title: return ""
    t = raw_title.replace("#", "").strip()
    if "%" in t or re.match(r"^[-+~≥>]?[\d\.]+$", t): return ""
    t = re.sub(r"\b(rent|gifts?|market|floor|nft|per day|days|min\. price|price)\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+", " ", t).strip()
    words = [w.capitalize() for w in t.split() if not w.isdigit() and "%" not in w]
    res = " ".join(words)
    return res if (res and len(res) > 1) else ""

def extract_discount_percentage(text: str) -> int:
    disc_match = re.search(r"[-−]?(\d{1,2}(?:\.\d+)?)%", text)
    if disc_match:
        try: return int(float(disc_match.group(1)))
        except Exception: pass

    per_day_match = re.search(r"(?:per day|min\. price|price)[:\s]*([\d\.]+)", text, re.IGNORECASE)
    floor_match = re.search(r"(?:rent floor|floor)[:\s]*([\d\.]+)", text, re.IGNORECASE)
    if per_day_match and floor_match:
        try:
            day_p = float(per_day_match.group(1))
            floor_p = float(floor_match.group(1))
            if floor_p > day_p > 0:
                return round(((floor_p - day_p) / floor_p) * 100)
        except Exception: pass
    return 0

def extract_price_ton(text: str) -> float:
    p_match = re.search(r"([\d\.]+)\s*(?:TON|ton|Per day)", text, re.I)
    if p_match:
        try: return float(p_match.group(1))
        except Exception: pass
    num_match = re.search(r"\b0\.\d+\b", text)
    if num_match:
        try: return float(num_match.group(0))
        except Exception: pass
    return 0.01

def generate_tg_nft_link(name: str, number: str) -> str:
    clean_name = re.sub(r"[^a-zA-Z0-9\s]", "", name)
    slug = "".join(w.capitalize() for w in clean_name.split())
    clean_num = re.sub(r"\D", "", str(number))
    return f"https://t.me/nft/{slug}-{clean_num}" if slug and clean_num else "https://t.me"

def generate_duck_store_html(deals: List[Dict[str, Any]]):
    if not deals or len(deals) == 0:
        deals = REAL_TELEGRAM_FALLBACK_GIFTS

    collections_map = {}
    for d in deals:
        c_name = d.get("gift_title", "").strip() or "Telegram Gift"
        if c_name not in collections_map:
            collections_map[c_name] = {
                "name": c_name,
                "image": d.get("image_url", ""),
                "count": 0,
            }
        collections_map[c_name]["count"] += 1

    collections_list = sorted(list(collections_map.values()), key=lambda x: str(x["name"]))
    rare_count = sum(1 for d in deals if d.get("rarity"))

    deals_json = json.dumps(deals, ensure_ascii=False)
    collections_json = json.dumps(collections_list, ensure_ascii=False)

    html_template = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="referrer" content="no-referrer">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<title>Duck Store | خدمات و گیفت‌های تلگرام</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#08090b; --glass:rgba(255,255,255,.05); --glass2:rgba(255,255,255,.08);
  --border:rgba(255,255,255,.09); --border2:rgba(255,255,255,.18);
  --text:#f3f3f5; --good:#3ddc97; --r-lg:22px; --r-md:16px;
}
*{-webkit-tap-highlight-color:transparent;}
body{
  font-family:'Vazirmatn',sans-serif; color:var(--text); background:var(--bg); min-height:100vh;
  background: radial-gradient(circle at 10% -10%, rgba(56,189,248,.08) 0%, transparent 40%), var(--bg);
}
.glass{ background:var(--glass); border:1px solid var(--border); backdrop-filter:blur(22px); border-radius:24px; }
.glass-tight{ border-radius:var(--r-md); }
.btn-inv{ background:#fff; color:#000; font-weight:800; border-radius:9999px; }
.btn-ghost{ background:var(--glass); border:1px solid var(--border); color:#fff; border-radius:9999px; }
.chip{ border-radius:9999px; font-weight:800; font-size:11px; padding:7px 15px; border:1px solid var(--border); background:var(--glass); color:#94a3b8; white-space:nowrap; }
.chip.active{ background:#fff; color:#000; border-color:#fff; }
.nav-tab{ color:#64748b; }
.nav-tab.active{ color:#fff; }
.sheet-backdrop{ background:rgba(0,0,0,.85); backdrop-filter:blur(10px); }
.toast-wrap{ position:fixed; top:14px; left:50%; transform:translateX(-50%); z-index:999; width:90%; max-width:400px; }
.toast{ background:#161922; border:1px solid rgba(255,255,255,.2); border-radius:14px; padding:10px 16px; font-size:12px; font-weight:700; text-align:center; }
input[type=number]::-webkit-inner-spin-button, input[type=number]::-webkit-outer-spin-button { -webkit-appearance:none; margin:0; }
@keyframes pulseGlow { 0%,100%{box-shadow:0 0 25px rgba(56,189,248,.35);} 50%{box-shadow:0 0 50px rgba(56,189,248,.75);} }
.duck-glow{ animation:pulseGlow 2s infinite ease-in-out; }
</style>
</head>
<body class="min-h-screen pb-44 select-none">

<div class="toast-wrap" id="toastWrap"></div>

<!-- لودینگ -->
<div id="splashScreen" class="fixed inset-0 z-[100] bg-[#07080c] flex flex-col items-center justify-center space-y-5 transition-opacity duration-500">
    <div class="w-24 h-24 rounded-3xl bg-gradient-to-tr from-cyan-500 to-blue-500 text-slate-950 flex items-center justify-center text-5xl font-black shadow-2xl duck-glow">🦆</div>
    <div class="text-center space-y-1">
        <h2 class="text-lg font-black text-white tracking-wider">DUCK STORE</h2>
        <p class="text-xs text-slate-400 font-bold">در حال بارگذاری جدیدترین گیفت‌های تلگرام...</p>
    </div>
    <div class="w-48 h-2 rounded-full bg-white/10 overflow-hidden relative">
        <div id="splashBar" class="h-full bg-gradient-to-r from-cyan-400 to-emerald-400 transition-all duration-300 w-0 rounded-full"></div>
    </div>
    <span id="splashPercent" class="text-xs font-mono font-bold text-cyan-400">0%</span>
</div>

<!-- مودال معرفی -->
<div id="onboardingModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 sheet-backdrop hidden">
    <div class="glass w-full max-w-sm p-6 text-center space-y-4 bg-[#0d1017] border border-cyan-500/30 shadow-2xl rounded-3xl">
        <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-400 to-blue-600 text-slate-950 flex items-center justify-center text-3xl mx-auto shadow-lg">🚀</div>
        <div class="space-y-2">
            <h3 class="text-base font-black text-white">خوش آمدید به Duck Store!</h3>
            <p class="text-xs text-slate-300 leading-relaxed">
                ویترین خرید و اجاره جدیدترین گیفت‌های تلگرام، استارز (حداقل ۵۰ عدد)، پرمیوم و خدمات کانال با تسویه فوری.
            </p>
        </div>
        <div class="p-3 bg-white/[0.03] border border-white/5 rounded-2xl text-[11px] text-slate-400 text-right space-y-1.5">
            <div>⭐ <b>استارز و پرمیوم:</b> تحویل مستقیم روی آیدی تلگرام</div>
            <div>🎁 <b>گیفت‌های NFT:</b> راهنمای ۹ مرحله‌ای اتصال آنی ولت فرگمنت</div>
            <div>🎰 <b>گردونه روزانه:</b> هر روز یک هدیه و کد تخفیف ویژه</div>
        </div>
        <button onclick="dismissOnboarding()" class="w-full py-3.5 bg-gradient-to-r from-cyan-400 to-blue-500 text-slate-950 font-black text-xs rounded-2xl shadow-xl hover:opacity-90 active:scale-95 transition">
            بزن بریم! 🚀
        </button>
    </div>
</div>

<header class="sticky top-0 z-30 px-4 py-3 bg-[#08090b]/90 backdrop-blur-xl border-b border-white/5">
  <div class="max-w-xl mx-auto flex items-center justify-between">
    <div class="flex items-center gap-2.5">
      <div class="w-10 h-10 rounded-2xl bg-cyan-400 text-slate-950 flex items-center justify-center text-xl font-black">🦆</div>
      <div>
        <h1 class="text-[10px] font-black uppercase tracking-widest text-slate-400">DUCK STORE</h1>
        <p class="text-xs font-black">خدمات و گیفت‌های تلگرام</p>
      </div>
    </div>
    <div class="flex items-center gap-2">
      <button onclick="openSpinModal()" class="px-3 py-1.5 rounded-xl bg-amber-400/10 text-amber-300 border border-amber-400/20 text-xs font-bold flex items-center gap-1.5">
        <i class="fa-solid fa-dice text-amber-400"></i><span>گردونه</span>
      </button>
      <a href="https://t.me/Zanjani_a" class="w-8 h-8 rounded-full btn-ghost flex items-center justify-center text-xs text-sky-400">
        <i class="fa-brands fa-telegram"></i>
      </a>
    </div>
  </div>
</header>

<main class="max-w-xl mx-auto px-4 mt-4 space-y-4">

<section id="view-home" class="space-y-4">
  <div class="grid grid-cols-3 gap-2 text-center">
    <div class="glass glass-tight p-3"><p class="text-base font-black">__TOTAL_COUNT__</p><p class="text-[10px] text-slate-400">گیفت فعال</p></div>
    <div class="glass glass-tight p-3"><p class="text-base font-black text-emerald-400">تحویل آنی</p><p class="text-[10px] text-slate-400">اتصال فرگمنت</p></div>
    <div class="glass glass-tight p-3"><p class="text-base font-black text-cyan-400">کارت‌به‌کارت</p><p class="text-[10px] text-slate-400">فاکتور ربات</p></div>
  </div>

  <div>
    <h3 class="text-xs font-black mb-2 px-1 text-slate-300">دسترسی سریع</h3>
    <div class="grid grid-cols-4 gap-2">
      <button onclick="goServices('stars')" class="glass glass-tight p-3 flex flex-col items-center gap-1"><span class="text-xl">⭐</span><span class="text-[10px] font-bold">استارز</span></button>
      <button onclick="goServices('premium')" class="glass glass-tight p-3 flex flex-col items-center gap-1"><span class="text-xl">💎</span><span class="text-[10px] font-bold">پرمیوم</span></button>
      <button onclick="switchView('market')" class="glass glass-tight p-3 flex flex-col items-center gap-1"><span class="text-xl">🎁</span><span class="text-[10px] font-bold">گیفت</span></button>
      <button onclick="goServices('custom_0')" class="glass glass-tight p-3 flex flex-col items-center gap-1"><span class="text-xl">🚀</span><span class="text-[10px] font-bold">خدمات</span></button>
    </div>
  </div>

  <div>
    <h3 class="text-xs font-black mb-2 px-1 text-slate-300">جدیدترین گیفت‌های اضافه‌شده</h3>
    <div id="homeGiftScroll" class="flex gap-2.5 overflow-x-auto pb-1 -mx-4 px-4"></div>
  </div>
</section>

<section id="view-market" class="hidden space-y-3">
  <div class="glass glass-tight p-2.5 flex items-center gap-2">
    <div class="relative flex-1">
      <i class="fa-solid fa-magnifying-glass absolute right-3 top-2.5 text-xs text-slate-500"></i>
      <input type="text" id="searchInput" placeholder="جستجوی نام یا شماره گیفت..." class="w-full bg-transparent pr-8 pl-2 py-1 text-xs outline-none">
    </div>
    <button onclick="openModal()" class="px-3 py-1.5 rounded-xl btn-ghost text-xs font-bold whitespace-nowrap"><span id="selectedColText">کالکشن‌ها</span> ▾</button>
  </div>

  <div class="flex items-center gap-2 overflow-x-auto pb-1">
    <button onclick="filterType('all', this)" class="type-btn chip active">همه (__TOTAL_COUNT__)</button>
    <button onclick="filterType('rare', this)" class="type-btn chip">💎 کمیاب (__RARE_COUNT__)</button>
    <button onclick="filterType('favs', this)" class="type-btn chip">❤️ نشان‌شده‌ها (<span id="favCount">0</span>)</button>
  </div>

  <div id="dealsGrid" class="grid grid-cols-2 gap-3"></div>
</section>

<section id="view-services" class="hidden space-y-4">
  <div id="servicesTabsBar" class="flex items-center gap-1.5 overflow-x-auto pb-1">
    <button onclick="switchServiceSubTab('stars')" id="subtab-stars" class="service-subtab-btn chip active">استارز</button>
    <button onclick="switchServiceSubTab('premium')" id="subtab-premium" class="service-subtab-btn chip">پرمیوم</button>
  </div>

  <!-- بخش استارز (حداقل ۵۰ عدد) -->
  <div id="subview-stars" class="space-y-3">
    <div class="glass glass-tight p-4 space-y-3">
      <div class="flex justify-between items-center">
        <h4 class="text-xs font-black text-amber-300">⭐ خرید استارز تلگرام (حداقل ۵۰ عدد)</h4>
        <span class="text-[10px] text-slate-400">نرخ: <span id="starRateLabel">1,450</span> تومان</span>
      </div>
      <div class="space-y-2">
        <input type="text" id="starsTargetId" placeholder="آیدی اکانت تلگرام یا کانال مقصد (الزامی)..." class="w-full glass glass-tight px-3 py-2 text-xs font-bold text-cyan-300">
        <div class="flex items-center gap-2">
          <input type="number" id="customStarsInput" oninput="calcLiveStarsPrice()" min="50" placeholder="تعداد استارز (حداقل ۵۰)..." class="flex-1 glass glass-tight px-3 py-2 text-xs font-bold">
          <button onclick="submitCustomStars()" class="px-4 py-2 btn-inv text-xs font-bold">ثبت سفارش</button>
        </div>
      </div>
      <div id="starsCalcDisplay" class="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-between text-xs">
        <span class="text-slate-300 font-bold" id="starsStatusLabel">مبلغ محاسبه‌شده:</span>
        <span id="starsLivePriceText" class="font-black text-amber-400 text-sm">۰ تومان</span>
      </div>
    </div>
    <div id="starsPackagesList" class="space-y-2"></div>
  </div>

  <div id="subview-premium" class="hidden space-y-3">
    <div class="glass glass-tight p-3 space-y-1">
      <label class="block text-[10px] text-slate-400 font-bold">آیدی اکانت تلگرام جهت فعال‌سازی پرمیوم:</label>
      <input type="text" id="premiumTargetId" placeholder="مثال: @username" class="w-full glass glass-tight px-3 py-2 text-xs font-bold text-purple-300">
    </div>
    <div id="premiumOptionsList" class="space-y-2.5"></div>
  </div>

  <div id="subview-custom" class="hidden space-y-3">
    <div id="customCategoryItemsList" class="space-y-3"></div>
  </div>
</section>

<section id="view-cart" class="hidden space-y-4">
  <div class="glass glass-tight p-4 space-y-3">
    <div class="flex items-center justify-between border-b pb-3 border-white/10">
      <h3 class="text-xs font-black">سبد خرید (<span id="cartCountHeader">0</span>)</h3>
      <button onclick="clearCart()" class="text-xs text-rose-400 font-bold">خالی کردن</button>
    </div>

    <div id="cartItemsList" class="space-y-2 max-h-56 overflow-y-auto"></div>
    <div id="cartEmptyState" class="hidden text-center py-6 text-xs text-slate-400">سبد خرید شما خالی است</div>

    <div class="pt-2 border-t border-white/10 space-y-2">
        <label class="block text-[10px] text-slate-400 font-bold">کد تخفیف دارید؟</label>
        <div class="flex gap-2">
            <input type="text" id="cartCouponInput" placeholder="کد تخفیف..." class="flex-1 glass glass-tight px-3 py-1.5 text-xs uppercase font-mono">
            <button onclick="applyCartCoupon()" class="px-3.5 py-1.5 bg-amber-400 text-slate-950 font-bold text-xs rounded-xl">اعمال</button>
        </div>
        <p id="couponFeedback" class="text-[10px] hidden font-bold"></p>
    </div>

    <div class="pt-3 border-t border-white/10 flex items-center justify-between">
      <div>
        <p class="text-[10px] text-slate-400">مبلغ نهایی سفارش:</p>
        <p id="cartTotal" class="text-sm font-black text-cyan-400">0 تومان</p>
      </div>
      <button onclick="checkoutCart()" class="py-2.5 px-5 btn-inv text-xs font-bold">صدور فاکتور و پرداخت</button>
    </div>
  </div>
</section>

<section id="view-profile" class="hidden space-y-4">
  <div class="glass p-5 space-y-4">
    <div class="flex items-center gap-3">
      <div class="w-12 h-12 rounded-full glass flex items-center justify-center text-xl">👤</div>
      <div>
        <h2 id="profileName" class="text-sm font-black">کاربر گرامی</h2>
        <p id="profileUsername" class="text-xs text-slate-400">@guest</p>
        <p class="text-[10px] text-cyan-400 font-mono mt-0.5">شناسه: <span id="profileUserId">00000000</span></p>
      </div>
    </div>

    <div class="p-3.5 rounded-xl bg-white/[0.02] border border-white/5 space-y-2 text-xs">
      <h3 class="font-black text-slate-300"><i class="fa-solid fa-receipt ml-1 text-purple-400"></i>پیگیری وضعیت سفارشات من</h3>
      <div id="userOrdersHistoryList" class="space-y-2 max-h-48 overflow-y-auto">
        <p class="text-slate-500 text-[11px] text-center py-2">در حال بارگذاری وضعیت...</p>
      </div>
    </div>

    <div class="pt-2">
      <a href="https://t.me/duck_storee" class="w-full py-3 rounded-2xl btn-ghost text-xs font-bold flex items-center justify-center gap-2">
        <i class="fa-brands fa-telegram text-sky-400"></i><span>عضویت در کانال تلگرام</span>
      </a>
    </div>
  </div>
</section>

</main>

<div id="floatingCartBar" class="fixed bottom-20 inset-x-4 max-w-lg mx-auto z-40 bg-[#0d1017]/95 backdrop-blur-xl border border-cyan-500/40 p-3 rounded-2xl shadow-2xl transition-all duration-300 transform translate-y-44 opacity-0 flex items-center justify-between">
  <div class="flex items-center gap-3">
    <div class="w-8 h-8 rounded-xl bg-cyan-400 text-black flex items-center justify-center font-black text-xs">
      <span id="floatingCartCount">0</span>
    </div>
    <div>
      <p class="text-xs font-bold text-white">سبد خرید شما</p>
      <p id="floatingCartPrice" class="text-xs text-cyan-400 font-black">0 تومان</p>
    </div>
  </div>
  <div class="flex items-center gap-2">
    <button onclick="switchView('cart')" class="px-3 py-1.5 rounded-xl btn-ghost text-xs">نمایش</button>
    <button onclick="checkoutCart()" class="px-3.5 py-1.5 rounded-xl btn-inv text-xs">تسویه</button>
  </div>
</div>

<nav class="fixed bottom-3 inset-x-4 max-w-xl mx-auto z-40 glass px-2 py-2 flex items-center justify-around rounded-full bg-[#0d0f15]/95">
  <button onclick="switchView('home')" id="nav-home" class="nav-tab active px-3 py-1 flex flex-col items-center gap-1 text-[10px] font-bold"><i class="fa-solid fa-house"></i><span>خانه</span></button>
  <button onclick="switchView('market')" id="nav-market" class="nav-tab px-3 py-1 flex flex-col items-center gap-1 text-[10px] font-bold"><i class="fa-solid fa-gift"></i><span>گیفت‌ها</span></button>
  <button onclick="switchView('services')" id="nav-services" class="nav-tab px-3 py-1 flex flex-col items-center gap-1 text-[10px] font-bold"><i class="fa-solid fa-bolt"></i><span>خدمات</span></button>
  <button onclick="switchView('cart')" id="nav-cart" class="nav-tab px-3 py-1 flex flex-col items-center gap-1 text-[10px] font-bold"><i class="fa-solid fa-cart-shopping"></i><span>سبد</span></button>
  <button onclick="switchView('profile')" id="nav-profile" class="nav-tab px-3 py-1 flex flex-col items-center gap-1 text-[10px] font-bold"><i class="fa-solid fa-user"></i><span>حساب</span></button>
</nav>

<div id="spinModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 sheet-backdrop hidden">
  <div class="glass w-full max-w-xs p-5 text-center space-y-3 bg-[#11131a]">
    <div class="text-3xl">🎰</div>
    <h3 class="text-xs font-black">گردونه شانس روزانه</h3>
    <div id="spinWheelVisual" class="w-24 h-24 rounded-full border-2 border-amber-400 mx-auto flex items-center justify-center text-[10px] font-bold text-amber-300 bg-amber-500/10">
      🎁 جایزه مخفی
    </div>
    <button id="spinActionBtn" onclick="runDailySpin()" class="w-full py-2.5 bg-amber-400 text-slate-950 font-black rounded-xl text-xs">چرخاندن گردونه</button>
    <button onclick="closeSpinModal()" class="text-[11px] text-slate-400">بستن</button>
  </div>
</div>

<div id="quickViewSheet" class="fixed inset-0 z-50 flex items-center justify-center p-4 sheet-backdrop hidden">
  <div class="glass w-full max-w-xs p-4 bg-[#11131a] space-y-3 text-right">
    <div class="relative w-full h-44 flex items-center justify-center rounded-xl bg-white/5" id="qvImageWrap">
      <img id="qvImage" src="" class="w-32 h-32 object-contain" onerror="this.src='https://marketapp.org/favicon.ico'">
    </div>
    <div>
      <h3 id="qvTitle" class="text-sm font-black text-white"></h3>
      <p id="qvNumber" class="text-xs text-slate-400 mt-0.5"></p>
    </div>
    <div class="flex items-center justify-between p-2.5 rounded-xl bg-black/40 text-xs">
      <span class="text-slate-400">مبلغ پایه ماهانه:</span>
      <span id="qvPrice" class="font-black text-amber-400"></span>
    </div>
    <div class="flex gap-2">
      <button onclick="addQVToCart()" class="flex-1 py-2.5 btn-inv text-xs font-bold">افزودن به سبد</button>
      <button onclick="openTelegramGift(activeQVDeal?.tg_link)" class="px-3 py-2.5 btn-ghost text-xs font-bold flex items-center justify-center gap-1">
        <i class="fa-brands fa-telegram text-sky-400"></i>
        <span>مشاهده</span>
      </button>
      <button onclick="closeQuickView()" class="px-3 py-2.5 btn-ghost text-xs">✕</button>
    </div>
  </div>
</div>

<div id="collectionModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 sheet-backdrop hidden">
  <div class="glass w-full max-w-sm max-h-[75vh] flex flex-col p-4 bg-[#11131a]">
    <div class="flex justify-between items-center pb-2 border-b border-white/10 text-xs font-bold">
      <span>کالکشن‌های گیفت</span>
      <button onclick="closeModal()">✕</button>
    </div>
    <div id="modalCollectionsList" class="space-y-2 py-3 overflow-y-auto flex-1"></div>
  </div>
</div>

<script>
const DEALS = __DEALS_JSON__;
const COLLECTIONS = __COLLECTIONS_JSON__;

let SETTINGS = {
  ratePerStar: 1450, prem3: 620000, prem6: 950000, prem12: 1690000, giftMonthlyPrice: 160000,
  discountCodes: [],
  spinWheelOptions: [
    { label: "۱۰٪ تخفیف خرید", code: "DUCK10" },
    { label: "۱۵٪ تخفیف پرمیوم", code: "PREM15" },
    { label: "۵۰ هزار تومان هدیه", code: "GIFT50" }
  ],
  customServices: [
    {
      id: "cat_boost", title: "بوست تلگرام",
      items: [{ id: "b1", name: "بوست کانال (سطح ۱)", duration: "۳۰ روزه", price: 65000, minQty: 1, inputPrompt: "لینک بوست یا کانال تلگرام" }]
    }
  ]
};

const WORKER_URL = "__WORKER_URL__";
let favorites = JSON.parse(localStorage.getItem('duck_favs_v11') || '[]');
let cart = JSON.parse(localStorage.getItem('duck_cart_v11') || '[]');
let selectedType = 'all';
let selectedCollection = 'all';
let activeQVDeal = null;
let appliedDiscount = 0;
let currentFilteredDeals = [];

function getTgUser() {
  if (window.Telegram?.WebApp?.initDataUnsafe?.user) {
    return window.Telegram.WebApp.initDataUnsafe.user;
  }
  return { id: "649632759", first_name: "کاربر", last_name: "آزمایشی", username: "guest" };
}

// تابع پروکسی هوشمند برای لود دائمی تصاویر بدون مسدودی Hotlink
function getSafeImg(url) {
  if (!url) return 'https://marketapp.org/favicon.ico';
  if (url.includes('anton.market')) {
    return 'https://wsrv.nl/?url=' + encodeURIComponent(url) + '&w=250&h=250&fit=contain';
  }
  return url;
}

window.addEventListener('DOMContentLoaded', () => {
    const splashBar = document.getElementById("splashBar");
    const splashPercent = document.getElementById("splashPercent");
    const splash = document.getElementById("splashScreen");
    let p = 0;
    const interval = setInterval(() => {
        p += Math.floor(Math.random() * 15) + 12;
        if (p >= 100) {
            p = 100;
            clearInterval(interval);
            if (splashBar) splashBar.style.width = '100%';
            if (splashPercent) splashPercent.innerText = '100%';
            setTimeout(() => {
                if (splash) {
                    splash.classList.add("opacity-0");
                    setTimeout(() => {
                        splash.remove();
                        if (!localStorage.getItem("duck_welcomed_v19")) {
                            document.getElementById("onboardingModal").classList.remove("hidden");
                        }
                    }, 500);
                }
            }, 250);
        } else {
            if (splashBar) splashBar.style.width = p + '%';
            if (splashPercent) splashPercent.innerText = p + '%';
        }
    }, 70);
});

function dismissOnboarding() {
    localStorage.setItem("duck_welcomed_v19", "true");
    document.getElementById("onboardingModal").classList.add("hidden");
}

function toast(msg) {
  const wrap = document.getElementById('toastWrap');
  const el = document.createElement('div');
  el.className = 'toast';
  el.innerText = msg;
  wrap.appendChild(el);
  setTimeout(() => el.remove(), 2500);
}

function fmtMoney(n) { return Math.round(Number(n)||0).toLocaleString('en-US'); }

function calcLiveStarsPrice() {
  const inputEl = document.getElementById('customStarsInput');
  const qty = parseInt(inputEl.value, 10) || 0;
  const rate = Number(SETTINGS.ratePerStar) || 1450;
  const statusLabel = document.getElementById('starsStatusLabel');
  const priceDisplay = document.getElementById('starsLivePriceText');

  if (qty > 0 && qty < 50) {
    statusLabel.innerText = "⚠️ حداقل سفارش ۵۰ استارز:";
    statusLabel.className = "text-rose-400 font-bold";
    priceDisplay.innerText = "حداقل ۵۰ عدد";
    priceDisplay.className = "font-black text-rose-400 text-xs";
    return;
  }

  statusLabel.innerText = "مبلغ محاسبه‌شده:";
  statusLabel.className = "text-slate-300 font-bold";
  priceDisplay.className = "font-black text-amber-400 text-sm";
  const total = qty * rate;
  priceDisplay.innerText = fmtMoney(total) + " تومان";
}

function calcLiveCustomPrice(catIdx, itemIdx) {
  const cat = (SETTINGS.customServices || [])[catIdx];
  if (!cat) return;
  const item = cat.items[itemIdx];
  const minQ = item.minQty || 1;
  const qtyInput = document.getElementById(`customQty_${catIdx}_${itemIdx}`);
  const display = document.getElementById(`customLivePrice_${catIdx}_${itemIdx}`);
  let qty = parseInt(qtyInput.value, 10) || minQ;

  if (qty < minQ) {
    qty = minQ;
    qtyInput.value = minQ;
  }
  const total = qty * Number(item.price);
  if (display) display.innerText = fmtMoney(total) + " تومان";
}

function openTelegramGift(url) {
  if (!url || url === '#' || url === 'https://t.me') {
    toast('لینک تلگرام برای این آیتم در دسترس نیست');
    return;
  }
  if (window.Telegram?.WebApp?.openTelegramLink) {
    window.Telegram.WebApp.openTelegramLink(url);
  } else {
    window.open(url, '_blank');
  }
}

function switchView(view) {
  ['home','market','services','cart','profile'].forEach(v => {
    document.getElementById('view-' + v)?.classList.toggle('hidden', v !== view);
    document.getElementById('nav-' + v)?.classList.toggle('active', v === view);
  });
  if (view === 'cart') renderCart();
  if (view === 'profile') loadUserData();
  if (view === 'market') renderCards(getFilteredDeals());
  window.scrollTo({top:0, behavior:'instant'});
}
function goServices(tab) { switchView('services'); switchServiceSubTab(tab); }

function renderHome() {
  document.getElementById('homeGiftScroll').innerHTML = DEALS.slice(0, 8).map((d, i) => `
    <div class="glass p-2.5 rounded-2xl flex-shrink-0 w-32 cursor-pointer text-right space-y-1.5" onclick="openHomeDeal(${i})">
      <div class="w-full h-24 rounded-xl flex items-center justify-center p-1" style="background:${d.bg_color || '#1b1d28'}">
        <img src="${getSafeImg(d.image_url)}" class="w-20 h-20 object-contain" onerror="this.src='https://marketapp.org/favicon.ico'">
      </div>
      <p class="text-[11px] font-black truncate text-white">${d.gift_title}</p>
      <p class="text-[10px] text-slate-400 dir-ltr text-right">#${d.number}</p>
    </div>
  `).join('');
}

function openHomeDeal(i) { if (DEALS[i]) openQuickView(DEALS[i]); }

function renderCards(list) {
  currentFilteredDeals = list || [];
  const grid = document.getElementById('dealsGrid');
  if (!grid) return;
  if (currentFilteredDeals.length === 0) {
    grid.innerHTML = '<div class="col-span-2 text-center py-10 text-xs text-slate-400 font-bold">گیفتی با این مشخصات یافت نشد.</div>';
    return;
  }
  grid.innerHTML = currentFilteredDeals.map((d, idx) => {
    const isFav = favorites.includes(d.name);
    return `
    <div class="glass p-3 rounded-2xl cursor-pointer text-right space-y-2 relative" onclick="openFilteredDeal(${idx})">
      <button onclick="event.stopPropagation(); toggleFavoriteDeal(${idx})" class="absolute top-2 left-2 w-7 h-7 rounded-full bg-black/40 text-xs flex items-center justify-center z-10">
        <i class="fa-solid fa-heart" style="color:${isFav ? '#f43f5e' : 'rgba(255,255,255,0.4)'}"></i>
      </button>
      <div class="w-full h-28 rounded-xl flex items-center justify-center p-2" style="background:${d.bg_color || '#1b1d28'}">
        <img src="${getSafeImg(d.image_url)}" class="w-24 h-24 object-contain" onerror="this.src='https://marketapp.org/favicon.ico'">
      </div>
      <div>
        <p class="text-xs font-black truncate text-white">${d.gift_title}</p>
        <p class="text-[10px] text-slate-400 dir-ltr text-right mt-0.5">#${d.number}</p>
        <div class="flex items-center justify-between mt-2 pt-1 border-t border-white/5">
          <span class="text-[10px] text-slate-400">اجاره:</span>
          <span class="text-xs font-black text-amber-400">${fmtMoney(SETTINGS.giftMonthlyPrice)} ت</span>
        </div>
      </div>
    </div>`;
  }).join('');
}

function openFilteredDeal(idx) { if (currentFilteredDeals[idx]) openQuickView(currentFilteredDeals[idx]); }
function toggleFavoriteDeal(idx) { if (currentFilteredDeals[idx]) toggleFavorite(currentFilteredDeals[idx].name); }

function getFilteredDeals() {
  const q = (document.getElementById('searchInput')?.value || '').trim().toLowerCase();
  return DEALS.filter(d => {
    const nameMatch = String(d.name || '').toLowerCase().includes(q) || String(d.gift_title || '').toLowerCase().includes(q);
    const numMatch = String(d.number || '').includes(q);
    if (q && !nameMatch && !numMatch) return false;
    if (selectedCollection !== 'all' && d.gift_title !== selectedCollection) return false;
    if (selectedType === 'rare' && !d.rarity) return false;
    if (selectedType === 'favs' && !favorites.includes(d.name)) return false;
    return true;
  });
}

function filterType(type, btn) {
  selectedType = type;
  document.querySelectorAll('.type-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  renderCards(getFilteredDeals());
}

document.getElementById('searchInput')?.addEventListener('input', () => renderCards(getFilteredDeals()));

function toggleFavorite(name) {
  const idx = favorites.indexOf(name);
  if (idx >= 0) favorites.splice(idx, 1); else favorites.push(name);
  localStorage.setItem('duck_favs_v11', JSON.stringify(favorites));
  renderCards(getFilteredDeals());
  const favEl = document.getElementById('favCount');
  if (favEl) favEl.innerText = favorites.length;
}

function openQuickView(d) {
  if (!d) return;
  activeQVDeal = d;
  document.getElementById('qvImageWrap').style.backgroundColor = d.bg_color || '#161d2a';
  document.getElementById('qvImage').src = getSafeImg(d.image_url);
  document.getElementById('qvTitle').innerText = d.gift_title;
  document.getElementById('qvNumber').innerText = `شماره گیفت: #${d.number}`;
  document.getElementById('qvPrice').innerText = fmtMoney(SETTINGS.giftMonthlyPrice) + ' تومان';
  document.getElementById('quickViewSheet').classList.remove('hidden');
}

function closeQuickView() { document.getElementById('quickViewSheet').classList.add('hidden'); }

function addQVToCart() {
  if (!activeQVDeal) return;
  cart.push({ 
    name: activeQVDeal.name, 
    price: Number(SETTINGS.giftMonthlyPrice),
    market_link: activeQVDeal.market_link || activeQVDeal.tg_link || ""
  });
  localStorage.setItem('duck_cart_v11', JSON.stringify(cart));
  toast('به سبد خرید اضافه شد');
  closeQuickView();
  updateFloatingCart();
}

function updateFloatingCart() {
  const bar = document.getElementById('floatingCartBar');
  if (!bar) return;
  const count = cart.length;
  const total = cart.reduce((s, c) => s + (Number(c.price)||0), 0);
  document.getElementById('floatingCartCount').innerText = count;
  document.getElementById('floatingCartPrice').innerText = fmtMoney(total) + ' ت';
  if (count > 0) {
    bar.classList.remove('translate-y-44', 'opacity-0');
    bar.classList.add('translate-y-0', 'opacity-100');
  } else {
    bar.classList.remove('translate-y-0', 'opacity-100');
    bar.classList.add('translate-y-44', 'opacity-0');
  }
}

function renderCart() {
  const list = document.getElementById('cartItemsList');
  const empty = document.getElementById('cartEmptyState');
  document.getElementById('cartCountHeader').innerText = cart.length;
  if (cart.length === 0) {
    list.innerHTML = ''; empty.classList.remove('hidden');
    document.getElementById('cartTotal').innerText = '0 تومان';
    return;
  }
  empty.classList.add('hidden');
  list.innerHTML = cart.map((c, i) => `
    <div class="glass p-2.5 flex items-center justify-between text-xs">
      <span>${c.name}</span>
      <button onclick="cart.splice(${i},1);localStorage.setItem('duck_cart_v11',JSON.stringify(cart));renderCart();updateFloatingCart();" class="text-rose-400 font-bold">✕</button>
    </div>
  `).join('');
  const subtotal = cart.reduce((s, c) => s + (Number(c.price)||0), 0);
  const finalTotal = Math.max(0, subtotal - appliedDiscount);
  document.getElementById('cartTotal').innerText = fmtMoney(finalTotal) + ' تومان' + (appliedDiscount > 0 ? ` (${fmtMoney(appliedDiscount)} تخفیف)` : '');
}

function clearCart() { cart = []; appliedDiscount = 0; localStorage.setItem('duck_cart_v11', JSON.stringify(cart)); renderCart(); updateFloatingCart(); }

function applyCartCoupon() {
    const code = document.getElementById("cartCouponInput").value.trim().toUpperCase();
    const fb = document.getElementById("couponFeedback");
    fb.classList.remove("hidden");

    const validCoupon = (SETTINGS.discountCodes || []).find(c => c.code === code);
    if (!validCoupon) {
        fb.className = "text-[10px] text-rose-400 font-bold";
        fb.innerText = "کد تخفیف معتبر نیست!";
        appliedDiscount = 0;
    } else {
        const subtotal = cart.reduce((s, c) => s + (Number(c.price)||0), 0);
        let disc = Math.round((subtotal * validCoupon.percent) / 100);
        if (validCoupon.maxLimit && disc > validCoupon.maxLimit) disc = validCoupon.maxLimit;
        appliedDiscount = disc;

        fb.className = "text-[10px] text-emerald-400 font-bold";
        fb.innerText = `کد اعمال شد! ${fmtMoney(disc)} تومان تخفیف کسر شد.`;
    }
    renderCart();
}

async function submitOrderToBot(items, totalPrice, itemsText, targetUsername = "") {
  const u = getTgUser();
  const payload = {
    userId: u.id,
    userName: `${u.first_name || ''} ${u.last_name || ''}`.trim() || u.username,
    targetUsername: targetUsername,
    items: items,
    itemsText: itemsText,
    totalPrice: totalPrice
  };
  try {
    toast("در حال صدور فاکتور در ربات...");
    const res = await fetch(`${WORKER_URL}/api/order/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      alert("✅ فاکتور در چت ربات برای شما صادر شد!\\nپس از واریز، عکس فیش را ارسال کنید.");
      clearCart();
    } else {
      alert("خطا در صدور فاکتور.");
    }
  } catch(e) {
    alert("ارتباط با سرور برقرار نشد.");
  }
}

function checkoutCart() {
  if (cart.length === 0) return alert("سبد خالی است");
  const subtotal = cart.reduce((s, c) => s + (Number(c.price)||0), 0);
  const finalTotal = Math.max(0, subtotal - appliedDiscount);
  const itemsText = cart.map((c, i) => `${i + 1}. 🎁 ${c.name}`).join("\\n");
  submitOrderToBot(cart, finalTotal, itemsText);
}

function submitCustomStars() {
  const targetId = document.getElementById("starsTargetId").value.trim();
  if (!targetId) return alert("⚠️ لطفاً آیدی مقصد را وارد کنید.");
  const qty = parseInt(document.getElementById('customStarsInput').value, 10) || 0;
  if (qty < 50) {
    return alert("⚠️ حداقل تعداد مجاز برای خرید استارز ۵۰ عدد است.");
  }
  const total = qty * Number(SETTINGS.ratePerStar);
  submitOrderToBot([{ name: `${qty} استارز تلگرام`, price: total, qty: qty }], total, `⭐ بسته ${qty} عددی استارز\\n📌 مقصد: ${targetId}`, targetId);
}

function submitStarsPackage(qty) {
  const targetId = document.getElementById("starsTargetId").value.trim();
  if (!targetId) return alert("⚠️ لطفاً آیدی مقصد را وارد کنید.");
  if (qty < 50) return alert("⚠️ حداقل خرید ۵۰ استارز است.");
  const total = qty * Number(SETTINGS.ratePerStar);
  submitOrderToBot([{ name: `${qty} استارز تلگرام`, price: total, qty: qty }], total, `⭐ بسته ${qty} عددی استارز\\n📌 مقصد: ${targetId}`, targetId);
}

function submitPremiumOrder(label, price) {
  const targetId = document.getElementById("premiumTargetId").value.trim();
  if (!targetId) return alert("⚠️ لطفاً آیدی اکانت تلگرام مقصد را وارد کنید.");
  submitOrderToBot([{ name: `اشتراک تلگرام پرمیوم ${label}`, price: price }], price, `👑 پرمیوم ${label}\\n📌 اکانت مقصد: ${targetId}`, targetId);
}

function switchServiceSubTab(tab) {
  document.querySelectorAll('.service-subtab-btn').forEach(btn => btn.classList.remove('active'));
  document.getElementById('subtab-' + tab)?.classList.add('active');
  const isCustom = String(tab).startsWith('custom_');
  document.getElementById('subview-stars').classList.toggle('hidden', tab !== 'stars');
  document.getElementById('subview-premium').classList.toggle('hidden', tab !== 'premium');
  document.getElementById('subview-custom').classList.toggle('hidden', !isCustom);
  if (isCustom) renderCustomCategory(parseInt(tab.replace('custom_', ''), 10) || 0);
}

function renderServicesNavigation() {
  const navBar = document.getElementById('servicesTabsBar');
  const customCats = Array.isArray(SETTINGS.customServices) ? SETTINGS.customServices : [];
  let html = `
    <button onclick="switchServiceSubTab('stars')" id="subtab-stars" class="service-subtab-btn chip active">استارز</button>
    <button onclick="switchServiceSubTab('premium')" id="subtab-premium" class="service-subtab-btn chip">پرمیوم</button>
  `;
  customCats.forEach((cat, idx) => {
    html += `<button onclick="switchServiceSubTab('custom_${idx}')" id="subtab-custom_${idx}" class="service-subtab-btn chip">${cat.title || 'سرویس'}</button>`;
  });
  navBar.innerHTML = html;
}

function renderStarsPackages() {
  const packs = [50, 100, 250, 500, 1000, 2500, 5000];
  document.getElementById('starsPackagesList').innerHTML = packs.map(p => `
    <div class="glass glass-tight p-3 flex items-center justify-between text-xs">
      <span class="font-bold">${p} استارز تلگرام</span>
      <div class="flex items-center gap-2">
        <span class="text-amber-400 font-black">${fmtMoney(p * Number(SETTINGS.ratePerStar))} ت</span>
        <button onclick="submitStarsPackage(${p})" class="px-3 py-1 btn-inv text-[11px]">خرید</button>
      </div>
    </div>
  `).join('');
}

function renderPremiumOptions() {
  const plans = [
    { label: '۳ ماهه', price: SETTINGS.prem3 },
    { label: '۶ ماهه', price: SETTINGS.prem6 },
    { label: '۱۲ ماهه', price: SETTINGS.prem12 }
  ];
  document.getElementById('premiumOptionsList').innerHTML = plans.map(p => `
    <div class="glass glass-tight p-3 flex items-center justify-between text-xs">
      <span class="font-bold">اشتراک ${p.label} پرمیوم</span>
      <div class="flex items-center gap-2">
        <span class="text-purple-400 font-black">${fmtMoney(p.price)} ت</span>
        <button onclick="submitPremiumOrder('${p.label}', ${p.price})" class="px-3 py-1 btn-inv text-[11px]">خرید</button>
      </div>
    </div>
  `).join('');
}

function renderCustomCategory(idx) {
  const cat = (SETTINGS.customServices || [])[idx];
  if (!cat) return;
  const listContainer = document.getElementById('customCategoryItemsList');
  listContainer.innerHTML = (cat.items || []).map((item, i) => {
    const minQ = item.minQty || 1;
    return `
    <div class="glass glass-tight p-4 space-y-3 text-xs">
      <div class="flex justify-between items-center">
        <div>
          <span class="font-black text-sm text-white">${item.name}</span>
          ${item.duration ? `<span class="text-[10px] text-slate-400 block mt-0.5">⏱️ ${item.duration}</span>` : ''}
        </div>
        <div class="text-left">
          <span class="text-[10px] text-slate-400">قیمت واحد:</span>
          <span class="text-amber-400 font-black block">${fmtMoney(item.price)} ت</span>
        </div>
      </div>

      <div class="space-y-2 pt-1 border-t border-white/5">
        <label class="block text-[10px] text-slate-400 font-bold">${item.inputPrompt || 'ورودی مورد نیاز'}:</label>
        <input id="prompt_${idx}_${i}" type="text" placeholder="${item.inputPrompt || 'مقدار ورودی...'}" class="w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs text-cyan-300 font-bold">
      </div>

      <div class="flex items-center justify-between gap-3">
        <div class="flex items-center gap-2">
          <span class="text-[10px] text-slate-400 font-bold">تعداد (حداقل ${minQ}):</span>
          <input id="customQty_${idx}_${i}" type="number" min="${minQ}" value="${minQ}" onchange="if(this.value < ${minQ}) this.value = ${minQ}; calcLiveCustomPrice(${idx}, ${i})" oninput="calcLiveCustomPrice(${idx}, ${i})" class="w-20 bg-black/40 border border-white/10 rounded-xl p-1.5 text-center font-bold text-xs">
        </div>
        <div class="text-right">
          <span class="text-[10px] text-slate-400">مجموع: </span>
          <span id="customLivePrice_${idx}_${i}" class="font-black text-amber-400 text-xs">${fmtMoney(item.price * minQ)} تومان</span>
        </div>
      </div>

      <button onclick="orderCustomService(${idx}, ${i})" class="w-full py-2.5 btn-inv text-xs font-black shadow-lg">سفارش فوری</button>
    </div>
  `}).join('');
}

function orderCustomService(catIdx, itemIdx) {
  const cat = SETTINGS.customServices[catIdx];
  const item = cat.items[itemIdx];
  const minQ = item.minQty || 1;
  const inputVal = document.getElementById(`prompt_${catIdx}_${itemIdx}`).value.trim();
  const qtyInput = document.getElementById(`customQty_${catIdx}_${itemIdx}`);
  const qty = parseInt(qtyInput.value, 10) || 0;

  if (!inputVal) return alert(`⚠️ لطفاً "${item.inputPrompt || 'ورودی'}" را وارد کنید.`);
  if (qty < minQ) {
    qtyInput.value = minQ;
    calcLiveCustomPrice(catIdx, itemIdx);
    return alert(`⚠️ حداقل تعداد سفارش برای این خدمت ${minQ} عدد می‌باشد.`);
  }

  const totalPrice = qty * Number(item.price);
  const titleText = `🚀 ${cat.title} - ${item.name} (${qty} عدد)`;
  const descText = `${titleText}\\n📌 پیش‌نیاز/ورودی: ${inputVal}`;

  submitOrderToBot([{ name: titleText, price: totalPrice, qty: qty, targetVal: inputVal }], totalPrice, descText, inputVal);
}

function openModal() { document.getElementById('collectionModal').classList.remove('hidden'); renderModalCollections(); }
function closeModal() { document.getElementById('collectionModal').classList.add('hidden'); }
function renderModalCollections() {
  const container = document.getElementById('modalCollectionsList');
  if (!container) return;

  let html = `
    <div class="p-2.5 rounded-xl border border-white/5 bg-[#12141a] cursor-pointer flex items-center justify-between hover:bg-white/5 transition" onclick="filterByCollection('all')">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-lg bg-cyan-400/10 text-cyan-400 flex items-center justify-center font-bold text-xs">ALL</div>
        <div>
          <span class="text-xs font-bold text-white">همه کالکشن‌ها</span>
          <span class="text-[10px] text-slate-400 block">${DEALS.length} گیفت فعال</span>
        </div>
      </div>
      <span class="text-xs text-cyan-400 font-bold">نمایش همه</span>
    </div>
  `;

  COLLECTIONS.forEach(col => {
    html += `
      <div class="p-2.5 rounded-xl border border-white/5 bg-[#12141a] cursor-pointer flex items-center justify-between hover:bg-white/5 transition" onclick="filterByCollection('${col.name.replace(/'/g, "\\'")}')">
        <div class="flex items-center gap-3">
          <img src="${getSafeImg(col.image)}" class="w-8 h-8 rounded-lg object-contain bg-white/5 p-1" onerror="this.src='https://marketapp.org/favicon.ico'">
          <div>
            <span class="text-xs font-bold text-white">${col.name}</span>
            <span class="text-[10px] text-slate-400 block">${col.count} موجود</span>
          </div>
        </div>
        <button onclick="event.stopPropagation(); toggleAlert('${col.name.replace(/'/g, "\\'")}')" class="px-2.5 py-1 rounded-lg bg-amber-400/10 text-amber-300 text-[10px] font-bold flex items-center gap-1">
          <i class="fa-solid fa-bell"></i>
          <span>شکار</span>
        </button>
      </div>
    `;
  });
  container.innerHTML = html;
}

function filterByCollection(colName) {
  selectedCollection = colName;
  const colText = document.getElementById('selectedColText');
  if (colText) colText.innerText = colName === 'all' ? 'کالکشن‌ها' : colName;
  closeModal();
  renderCards(getFilteredDeals());
}

async function toggleAlert(colName) {
  const u = getTgUser();
  try {
    const res = await fetch(`${WORKER_URL}/api/alert/toggle`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ userId: u.id, collection: colName })
    });
    const d = await res.json();
    if (d.active) toast(`اعلان شکار برای ${colName} فعال شد!`);
    else toast(`اعلان ${colName} غیرفعال شد.`);
  } catch(e) {
    toast(`اعلان شکار برای ${colName} فعال شد!`);
  }
}

async function loadUserData() {
  const u = getTgUser();
  const pName = document.getElementById('profileName');
  const pUser = document.getElementById('profileUsername');
  const pId = document.getElementById('profileUserId');
  if (pName) pName.innerText = `${u.first_name || ''} ${u.last_name || ''}`.trim() || 'کاربر گرامی';
  if (pUser) pUser.innerText = u.username ? `@${u.username}` : '@user';
  if (pId) pId.innerText = u.id;

  try {
    const res = await fetch(`${WORKER_URL}/api/user-data?userId=${u.id}`);
    if (res.ok) {
      const data = await res.json();
      const oList = document.getElementById("userOrdersHistoryList");
      if (!data.orders || data.orders.length === 0) {
        oList.innerHTML = '<p class="text-slate-500 text-[11px] text-center py-2">هنوز سفارشی ثبت نکرده‌اید.</p>';
      } else {
        oList.innerHTML = data.orders.map(o => {
          let badge = '<span class="text-amber-400 font-bold">⏳ در انتظار فیش</span>';
          if (o.status === "processing") badge = '<span class="text-cyan-400 font-bold">⚙️ در حال آماده‌سازی</span>';
          if (o.status === "waiting_fragment") badge = '<span class="text-purple-400 font-bold">🔗 در انتظار لینک فرگمنت</span>';
          if (o.status === "completed") badge = '<span class="text-emerald-400 font-bold">🎉 تحویل داده شد</span>';
          if (o.status === "rejected") badge = '<span class="text-rose-400 font-bold">❌ رد شده</span>';
          return `
            <div class="p-2.5 rounded-xl bg-black/40 border border-white/5 space-y-1">
              <div class="flex justify-between items-center text-[11px]">
                <span class="font-mono font-bold">${o.id}</span>
                ${badge}
              </div>
              <p class="text-slate-400 text-[10px]">${fmtMoney(o.totalPrice)} تومان</p>
            </div>
          `;
        }).join('');
      }
    }
  } catch(e) {}
}

function openSpinModal() { document.getElementById("spinModal").classList.remove("hidden"); }
function closeSpinModal() { document.getElementById("spinModal").classList.add("hidden"); }
async function runDailySpin() {
  const u = getTgUser();
  const btn = document.getElementById("spinActionBtn");
  btn.disabled = true; btn.innerText = "درحال چرخیدن...";
  try {
    const res = await fetch(`${WORKER_URL}/api/spin-wheel`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ userId: u.id })
    });
    const d = await res.json();
    if (res.ok) {
      const slices = SETTINGS.spinWheelOptions || [{ label: "۱۰٪ تخفیف", code: "DUCK10" }];
      const prize = slices[Math.floor(Math.random() * slices.length)];
      document.getElementById("spinWheelVisual").innerText = prize.label;
      alert(`🎉 تبریک! جایزه شما:\\n${prize.label}\\n${prize.code ? 'کد تخفیف: ' + prize.code : ''}`);
      closeSpinModal();
    } else {
      alert(d.error || "خطا در چرخاندن گردونه");
    }
  } catch(e) {
    alert("امکان ارتباط با سرور برقرار نشد.");
  } finally {
    btn.disabled = false; btn.innerText = "چرخاندن گردونه";
  }
}

renderHome();
renderCards(getFilteredDeals());
renderStarsPackages();
renderPremiumOptions();
renderServicesNavigation();
loadUserData();
calcLiveStarsPrice();

(async function() {
  try {
    const res = await fetch(`${WORKER_URL}/api/settings`);
    if (res.ok) {
      const data = await res.json();
      SETTINGS = { ...SETTINGS, ...data };
      document.getElementById('starRateLabel').innerText = fmtMoney(SETTINGS.ratePerStar);
      renderStarsPackages();
      renderPremiumOptions();
      renderServicesNavigation();
      calcLiveStarsPrice();
    }
  } catch(e) {}
})();
</script>
</body>
</html>"""

    html_content = (
        html_template.replace("__TOTAL_COUNT__", str(len(deals)))
        .replace("__RARE_COUNT__", str(rare_count))
        .replace("__DEALS_JSON__", deals_json)
        .replace("__COLLECTIONS_JSON__", collections_json)
        .replace("__WORKER_URL__", CONFIG["WORKER_URL"])
    )

    with open(CONFIG["EXPORT_HTML"], "w", encoding="utf-8") as f:
        f.write(html_content)

    with open(CONFIG["EXPORT_JSON"], "w", encoding="utf-8") as f:
        json.dump(deals, f, ensure_ascii=False, indent=2)

    with open(CONFIG["EXPORT_CSV"], "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f, 
            fieldnames=["name", "gift_title", "number", "price_ton", "rarity", "tg_link", "market_link"]
        )
        writer.writeheader()
        for d in deals:
            writer.writerow({
                "name": d.get("name", ""),
                "gift_title": d.get("gift_title", ""),
                "number": d.get("number", ""),
                "price_ton": d.get("price_ton", "0.01"),
                "rarity": d.get("rarity", ""),
                "tg_link": d.get("tg_link", ""),
                "market_link": d.get("market_link", "https://marketapp.org/rent/?subtab=gifts"),
            })

# ارسال فایل اکسل به چت تلگرام ادمین با متد Multipart
def send_telegram_document(token: str, chat_id: str, file_path: str, caption: str = ""):
    if not os.path.exists(file_path): return
    boundary = "----WebKitFormBoundary" + datetime.now().strftime("%Y%m%d%H%M%S")
    filename = os.path.basename(file_path)

    with open(file_path, "rb") as f:
        file_data = f.read()

    body = bytearray()
    body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n".encode("utf-8"))
    if caption:
        body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption}\r\n".encode("utf-8"))
        body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"parse_mode\"\r\n\r\nHTML\r\n".encode("utf-8"))
    body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"document\"; filename=\"{filename}\"\r\nContent-Type: text/csv; charset=utf-8\r\n\r\n".encode("utf-8"))
    body.extend(file_data)
    body.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))

    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendDocument", data=bytes(body))
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    try:
        with urllib.request.urlopen(req, timeout=30): pass
        print("📊 فایل اکسل موجودی گیفت‌ها با موفقیت به تلگرام ادمین ارسال شد.")
    except Exception as e:
        print(f"⚠️ خطای ارسال فایل اکسل: {e}")

# ارسال گزارش شکار متنی + ارسال همزمان فایل اکسل
def send_telegram_hunter_report(deals: List[Dict[str, Any]]):
    token = CONFIG.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = CONFIG.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id or not deals: return

    timestamp = datetime.now().strftime("%H:%M:%S - %Y/%m/%d")
    target_col = CONFIG.get("TARGET_COLLECTION") or "تمام کالکشن‌ها"

    top_deals_text = ""
    for d in deals[:8]:
        top_deals_text += f"\n• <b>{d['name']}</b> ({d.get('price_ton', '0.01')} TON)\n  👉 <a href='{d['market_link']}'>خرید در مارکت‌اپ</a> | <a href='{d['tg_link']}'>لینک تلگرام</a>"

    full_text = (
        f"🎯 <b>گزارش شکار توربو Duck Store</b>\n"
        f"📅 <i>{timestamp}</i>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔍 <b>فیلتر کالکشن:</b> {target_col}\n"
        f"💰 <b>بازه تخفیف:</b> {CONFIG['MIN_DISCOUNT']}٪ تا {CONFIG['MAX_DISCOUNT']}٪\n"
        f"✅ <b>مجموع کل شکارشده:</b> {len(deals)} عدد\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>جدیدترین گزینه‌های شکارشده:</b>\n"
        f"{top_deals_text}\n\n"
        f"🌐 <i>ویترین فروشگاه به‌روزرسانی شد.</i>"
    )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode({"chat_id": chat_id, "text": full_text, "parse_mode": "HTML", "disable_web_page_preview": "true"}).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload)
        with urllib.request.urlopen(req, timeout=15): pass
    except Exception as e:
        print(f"⚠️ خطا در ارسال گزارش به تلگرام: {e}")

    # ارسال فایل اکسل
    send_telegram_document(token, chat_id, CONFIG["EXPORT_CSV"], "📊 <b>فایل کامل اکسل موجودی گیفت‌های شکارشده</b>")

# تابع استخراج کارت‌ها با پشتیبانی از تمام ساختارهای مارکت‌اپ
async def scrape_cards_from_page(page, target_count, deals_found, seen_links, filter_mode="discount", max_scrolls=35):
    start_time = asyncio.get_event_loop().time()
    max_duration = 130
    scrolls = 0
    consecutive_no_change = 0

    while len(deals_found) < target_count and scrolls < max_scrolls:
        if asyncio.get_event_loop().time() - start_time > max_duration:
            break

        scrolls += 1
        deals_before = len(deals_found)

        raw_cards = await page.evaluate("""() => {
            const cards = [];
            const elements = Array.from(document.querySelectorAll("a, div"));
            for (const el of elements) {
                const text = el.innerText || '';
                if (text.includes('#') && (text.includes('Per day') || text.includes('Days:') || text.includes('Rent floor') || text.includes('Min. price') || text.includes('%') || text.includes('TON') || text.includes('ton'))) {
                    const img = el.querySelector('img');
                    if (img && img.src && (img.src.includes('anton.market') || img.src.includes('marketapp') || img.src.includes('http'))) {
                        if (el.querySelectorAll('img').length === 1) {
                            const href = el.getAttribute('href') || el.querySelector('a')?.getAttribute('href') || '';
                            const alt = img.getAttribute('alt') || img.getAttribute('title') || '';
                            cards.push({ text: text, img: img.src, href: href, alt: alt });
                        }
                    }
                }
            }
            return cards;
        }""")

        for c in raw_cards:
            if len(deals_found) >= target_count: break
            text = c.get("text", "")
            href = c.get("href", "")
            alt_text = c.get("alt", "")

            num_match = re.search(r"#(\d+)", text)
            if not num_match: continue
            item_num = num_match.group(1)

            price_ton = extract_price_ton(text)

            # در فاز تخفیف، اگر تخفیف وجود دارد در بازه باشد؛ اگر کمتر از ۱۰ گیفت پیدا شد فیلتر نرم‌تر می‌شود
            if filter_mode == "discount":
                discount_val = extract_discount_percentage(text)
                if discount_val > 0 and not (CONFIG["MIN_DISCOUNT"] <= discount_val <= CONFIG["MAX_DISCOUNT"]):
                    continue
            elif filter_mode == "cheap":
                if price_ton > 0.01:
                    continue

            gift_name = ""
            if alt_text and len(alt_text) > 1 and "%" not in alt_text:
                c_alt = clean_collection_title(re.sub(r"#\d+", "", alt_text))
                if c_alt and c_alt.lower() not in ["image", "nft", "gift", "telegram gift"]:
                    gift_name = c_alt

            if not gift_name and href:
                slug_match = re.search(r"/([a-zA-Z0-9-]+?)(?:-" + item_num + r"|\b)", href.lower())
                if slug_match:
                    parts = [w for w in slug_match.group(1).split("-") if w not in ["rent", "nft", "gifts", "gift", "market"]]
                    if parts:
                        candidate = " ".join(w.capitalize() for w in parts)
                        if not re.match(r"^[-+~≥>]?[\d\.]+", candidate):
                            gift_name = clean_collection_title(candidate)

            if not gift_name:
                for line in [l.strip() for l in text.split("\n") if l.strip()]:
                    if "%" in line or re.match(r"^[-+~≥>]?[\d\.]+", line): continue
                    if any(b in line.lower() for b in ["per day", "price", "days:", "floor", "ton", "usd", "rent"]): continue
                    candidate = clean_collection_title(line.replace(f"#{item_num}", ""))
                    if candidate:
                        gift_name = candidate
                        break

            if not gift_name: gift_name = "Telegram Gift"

            target_filter = CONFIG.get("TARGET_COLLECTION", "").strip().lower()
            if target_filter and target_filter not in gift_name.lower():
                continue

            full_id = f"{gift_name} #{item_num}"
            if full_id in seen_links: continue

            full_market_link = href if href.startswith("http") else f"{CONFIG['BASE_DOMAIN']}{href if href.startswith('/') else '/' + href}"
            if not href: full_market_link = "https://marketapp.org/rent/?subtab=gifts"

            deal = {
                "name": full_id,
                "gift_title": gift_name,
                "number": str(item_num),
                "price_ton": str(price_ton),
                "tg_link": generate_tg_nft_link(gift_name, item_num),
                "market_link": full_market_link,
                "image_url": c.get("img") or "https://marketapp.org/favicon.ico",
                "bg_color": "#161d2a",
                "rarity": detect_rarity_badge(item_num),
            }
            seen_links.add(full_id)
            deals_found.append(deal)

        if len(deals_found) >= target_count: break

        prev_height = await page.evaluate("document.body.scrollHeight")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        await page.wait_for_timeout(450)
        new_height = await page.evaluate("document.body.scrollHeight")

        if new_height == prev_height and len(deals_found) == deals_before:
            consecutive_no_change += 1
            await page.evaluate("window.scrollBy(0, -250);")
            await page.wait_for_timeout(250)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            await page.wait_for_timeout(450)
            if consecutive_no_change >= 6:
                break
        else:
            consecutive_no_change = 0

        print(f"⏳ پیشرفت: {len(deals_found)} گیفت ثبت شد...")

async def main():
    deals_found: List[Dict[str, Any]] = []
    seen_links: Set[str] = set()
    browser = None

    print("\n" + "═" * 65)
    print("  🚀 DUCK STORE TURBO SCRAPER (150 DISCOUNTED + 100 CHEAP) 🚀")
    print("═" * 65 + "\n")

    launch_args = [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-blink-features=AutomationControlled"
    ]

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=launch_args)
            page = await browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            # فاز ۱: استخراج ۱۵۰ گیفت تخفیفی
            print(f"🚀 فاز ۱: استخراج ۱۵۰ گیفت تخفیف‌دار...")
            await page.goto(CONFIG["DISCOUNT_URL"], wait_until="domcontentloaded", timeout=35000)
            await page.wait_for_timeout(3500)
            await scrape_cards_from_page(page, CONFIG["TARGET_DEALS_COUNT"], deals_found, seen_links, filter_mode="discount", max_scrolls=40)
            print(f"✅ فاز ۱ تکمیل شد: {len(deals_found)} گیفت ثبت شد.")

            # فاز ۲: استخراج ۱۰۰ گیفت کف‌قیمت
            cheap_target_total = len(deals_found) + CONFIG["CHEAP_DEALS_COUNT"]
            print(f"\n🚀 فاز ۲: استخراج ۱۰۰ گیفت کف‌قیمت...")
            await page.goto(CONFIG["CHEAP_URL"], wait_until="domcontentloaded", timeout=35000)
            await page.wait_for_timeout(3500)
            await scrape_cards_from_page(page, cheap_target_total, deals_found, seen_links, filter_mode="cheap", max_scrolls=35)
            print(f"✅ فاز ۲ تکمیل شد: مجموع گیفت‌ها به {len(deals_found)} عدد رسید.")

    except Exception as e:
        print(f"⚠️ وضعیت ارتباط اسکرپر: {e}")
    finally:
        if browser: await browser.close()

    # در صورت قطع اینترنت یا مارکت‌اپ، کاتالوگ پشتیبان کامل و با عکس قرار می‌گیرد
    final_deals = deals_found if len(deals_found) >= 5 else REAL_TELEGRAM_FALLBACK_GIFTS
    final_deals.reverse()

    generate_duck_store_html(final_deals)
    print(f"\n🎉 ویترین فروشگاه آماده شد! تعداد موجودی: {len(final_deals)} عدد")

    # ارسال گزارش متنی + فایل کامل اکسل
    send_telegram_hunter_report(final_deals)

if __name__ == "__main__":
    asyncio.run(main())
