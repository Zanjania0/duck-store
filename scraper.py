import asyncio
from collections import defaultdict
import csv
from datetime import datetime
import json
import os
import re
import time
from typing import Any, Dict, List, Set
import urllib.parse
import urllib.request
from playwright.async_api import async_playwright

# ==========================================
# ⚙️ تنظیمات اپلیکیشن
# ==========================================
CONFIG = {
    "TARGET_URL": (
        "https://marketapp.org/rent/?tab=market&sort_by=price_per_day_asc"
        "&subtab=gifts&view=grid&min_price=0.01&max_price=0.02"
    ),
    "FRAGMENT_PREMIUM_URL": "https://fragment.com/premium/gift",
    "MIN_DISCOUNT_PERCENT": 50.0,
    "TARGET_DEALS_COUNT": 200,
    "BASE_DOMAIN": "https://marketapp.org",
    "EXPORT_CSV": "discounts.csv",
    "EXPORT_HTML": "index.html",
    "EXPORT_JSON": "discounts.json",
    "WORKER_URL": "https://duck-api.ali-zanjani2007.workers.dev",
    "ADMIN_TELEGRAM_LINK": "https://t.me/Zanjani_a",
    "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN", ""),
    "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID", ""),
    "TELEGRAM_CHANNEL_ID": os.getenv("TELEGRAM_CHANNEL_ID", ""),
    "GITHUB_REPOSITORY": os.getenv("GITHUB_REPOSITORY", ""),
}


# ==========================================
# 📈 موتور هوشمند استعلام قیمت ارز و محاسبه نرخ پرمیوم
# ==========================================
async def fetch_auto_pricing(page) -> Dict[str, int]:
    """استعلام زنده نرخ ارز از نوبیتکس و قیمت‌های فرگمنت با احتساب درصد سود ادمین"""
    print("\n📊 در حال دریافت قیمت‌های زنده و محاسبه خودکار نرخ پرمیوم...")

    # مقادیر پیش‌فرض TON برای ۳، ۶ و ۱۲ ماه در فرگمنت
    ton_amounts = {"prem3": 3.8, "prem6": 5.8, "prem12": 9.9}
    ton_to_usd = 5.4  # مقدار پیش‌فرض در صورت قطعی
    usdt_to_toman = 60000  # مقدار پیش‌فرض تتر به تومان
    profit_percent = 15  # درصد سود پیش‌فرض ادمین

    # ۱. واکشی درصد سود تنظیم‌شده توسط ادمین از Cloudflare KV
    try:
        req = urllib.request.Request(
            f"{CONFIG['WORKER_URL']}/api/settings",
            headers={"User-Agent": "DuckBot/1.0"},
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            settings_data = json.loads(res.read().decode())
            if "profitMargin" in settings_data:
                profit_percent = float(settings_data["profitMargin"])
                print(f"💰 درصد سود ادمین از سرور دریافت شد: {profit_percent}%")
    except Exception as e:
        print(f"⚠️ استفاده از درصد سود پیش‌فرض ({profit_percent}%)")

    # ۲. استعلام زنده قیمت ارز TON به دلار از CoinGecko
    try:
        req = urllib.request.Request(
            "https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd",
            headers={"User-Agent": "DuckBot/1.0"},
        )
        with urllib.request.urlopen(req, timeout=6) as res:
            cg_data = json.loads(res.read().decode())
            ton_to_usd = float(cg_data["the-open-network"]["usd"])
            print(f"💎 نرخ جهانی TON: {ton_to_usd}$")
    except Exception:
        print(f"ℹ️ نرخ TON پیش‌فرض: {ton_to_usd}$")

    # ۳. استعلام نرخ تتر به تومان از صرافی نوبیتکس (Nobitex API)
    try:
        req = urllib.request.Request(
            "https://api.nobitex.ir/v2/orderbook/USDTIRT",
            headers={"User-Agent": "DuckBot/1.0"},
        )
        with urllib.request.urlopen(req, timeout=6) as res:
            nobitex_data = json.loads(res.read().decode())
            last_trade = float(nobitex_data.get("lastTradePrice", 600000))
            usdt_to_toman = last_trade / 10  # تبدیل ریال به تومان
            print(f"💵 نرخ تتر نوبیتکس: {usdt_to_toman:,.0f} تومان")
    except Exception:
        print(f"ℹ️ نرخ تتر پیش‌فرض: {usdt_to_toman:,.0f} تومان")

    # ۴. بررسی صفحه فرگمنت برای مقادیر TON
    try:
        await page.goto(
            CONFIG["FRAGMENT_PREMIUM_URL"],
            wait_until="domcontentloaded",
            timeout=15000,
        )
        await page.wait_for_timeout(2000)
        frag_text = await page.evaluate("() => document.body.innerText")
        m3 = re.search(r"3\s*months.*?(\d+(?:\.\d+)?)\s*TON", frag_text, re.I)
        m6 = re.search(r"6\s*months.*?(\d+(?:\.\d+)?)\s*TON", frag_text, re.I)
        m12 = re.search(
            r"(?:12\s*months|1\s*year).*?(\d+(?:\.\d+)?)\s*TON", frag_text, re.I
        )
        if m3:
            ton_amounts["prem3"] = float(m3.group(1))
        if m6:
            ton_amounts["prem6"] = float(m6.group(1))
        if m12:
            ton_amounts["prem12"] = float(m12.group(1))
        print(f"✅ مقادیر TON فرگمنت: {ton_amounts}")
    except Exception:
        print("ℹ️ استفاده از پایه تعرفه استاندارد فرگمنت")

    # ۵. محاسبه نهایی به تومان با اعمال درصد سود ادمین
    ton_toman_rate = ton_to_usd * usdt_to_toman
    profit_multiplier = 1.0 + (profit_percent / 100.0)

    final_prices = {
        "prem3": int(
            round(ton_amounts["prem3"] * ton_toman_rate * profit_multiplier, -3)
        ),
        "prem6": int(
            round(ton_amounts["prem6"] * ton_toman_rate * profit_multiplier, -3)
        ),
        "prem12": int(
            round(
                ton_amounts["prem12"] * ton_toman_rate * profit_multiplier, -3
            )
        ),
    }

    print(
        f"🎯 قیمت‌های خودکار پرمیوم (تومان): ۳ ماهه={final_prices['prem3']:,} | ۶ ماهه={final_prices['prem6']:,} | ۱ ساله={final_prices['prem12']:,}\n"
    )
    return final_prices


def detect_rarity_badge(number_str: str) -> str:
    try:
        num = int(re.sub(r"\D", "", str(number_str)))
    except ValueError:
        return ""

    s = str(num)
    if num < 100:
        return "👑 زیر 100 (نایاب)"
    if num < 1000:
        return f"💎 زیر 1000 (#{num})"
    if len(s) >= 3 and len(set(s)) == 1:
        return f"✨ رند (#{s})"
    if s in [
        "123",
        "1234",
        "12345",
        "6969",
        "777",
        "888",
        "999",
        "10000",
        "50000",
        "100000",
    ]:
        return f"🎯 خاص (#{s})"
    if len(s) == 4 and s == s[::-1]:
        return f"🔁 متقارن (#{s})"
    return ""


def generate_tg_nft_link(name: str, number: str) -> str:
    words = re.findall(r"[a-zA-Z0-9]+", name)
    slug = "".join(w.capitalize() for w in words)
    clean_num = re.sub(r"\D", "", str(number))
    return (
        f"https://t.me/nft/{slug}-{clean_num}"
        if slug and clean_num
        else "https://t.me"
    )


def generate_duck_store_html(
    deals: List[Dict[str, Any]], auto_prices: Dict[str, int]
):
    """تولید وب‌سایت فروشگاهی Duck Store با استایل لاکچری و مدرن آیفونی (iOS Widget Design)"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    collections_map = {}
    for d in deals:
        c_name = d["gift_title"]
        if c_name not in collections_map:
            collections_map[c_name] = {
                "name": c_name,
                "image": d["image_url"],
                "count": 0,
            }
        collections_map[c_name]["count"] += 1

    collections_list = sorted(
        list(collections_map.values()), key=lambda x: x["name"]
    )
    deals_json = json.dumps(deals, ensure_ascii=False)
    collections_json = json.dumps(collections_list, ensure_ascii=False)
    rare_count = sum(1 for d in deals if d.get("rarity"))

    html_template = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>Duck Store | خدمات پرمیوم تلگرام</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #060913;
            --ios-card: rgba(14, 20, 40, 0.7);
            --ios-border: rgba(255, 255, 255, 0.08);
            --ios-border-glow: rgba(56, 189, 248, 0.25);
        }
        body {
            font-family: 'Vazirmatn', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-base);
            background-image: 
                radial-gradient(circle at 10% 10%, rgba(30, 58, 138, 0.28) 0%, transparent 40%),
                radial-gradient(circle at 90% 25%, rgba(124, 58, 237, 0.22) 0%, transparent 45%),
                radial-gradient(circle at 50% 90%, rgba(14, 165, 233, 0.15) 0%, transparent 50%);
            color: #f8fafc;
            -webkit-tap-highlight-color: transparent;
            -webkit-touch-callout: none;
        }
        .ios-glass-card {
            background: var(--ios-card);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border: 1px solid var(--ios-border);
            border-radius: 28px;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .ios-glass-card:hover {
            border-color: rgba(56, 189, 248, 0.35);
            box-shadow: 0 20px 40px -15px rgba(2, 6, 23, 0.8), 0 0 25px rgba(56, 189, 248, 0.15);
            transform: translateY(-3px);
        }
        .ios-pill-tab {
            background: rgba(15, 23, 42, 0.6);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 9999px;
            padding: 4px;
        }
        .ios-badge {
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(12px);
        }
        .modal-bg {
            background: #090e1f;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.15); border-radius: 9999px; }
    </style>
</head>
<body class="min-h-screen pb-36 select-none">

    <!-- ⏳ اسپلش اسکرین اختصاصی iOS -->
    <div id="loadingScreen" class="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#060913] transition-all duration-500 px-6">
        <div class="relative flex items-center justify-center">
            <div class="w-20 h-20 rounded-[26px] bg-gradient-to-tr from-blue-600 via-indigo-600 to-purple-600 flex items-center justify-center text-4xl shadow-2xl shadow-blue-500/25 animate-pulse">
                🦆
            </div>
            <div class="absolute -inset-3 rounded-[32px] border border-blue-400/20 border-t-cyan-400 animate-spin"></div>
        </div>
        <h2 class="text-white font-black text-lg mt-6 tracking-wide flex items-center gap-2">
            <span>Duck Store</span>
            <span class="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
        </h2>
        <p class="text-slate-400 text-xs mt-2 font-medium">همگام‌سازی لحظه‌ای با نرخ جهانی فرگمنت...</p>
        <div class="w-48 h-1.5 bg-slate-900 rounded-full overflow-hidden mt-6 border border-white/5">
            <div id="loadingProgressBar" class="h-full bg-gradient-to-r from-blue-500 to-cyan-400 transition-all duration-150" style="width: 5%"></div>
        </div>
        <span id="loadingPercent" class="text-[11px] font-bold text-slate-500 mt-2">0%</span>
    </div>

    <!-- 🚀 صفحه Onboarding / معرفی جذاب با دکمه "بزن بریم" -->
    <div id="welcomeScreen" class="fixed inset-0 z-40 hidden flex items-center justify-center bg-[#04060d]/90 backdrop-blur-2xl transition-all duration-500 p-5 opacity-0 scale-95">
        <div class="w-full max-w-sm ios-glass-card p-6 flex flex-col items-center text-center space-y-5 border-blue-500/20 shadow-2xl shadow-blue-950/40">
            <div class="w-16 h-16 rounded-[22px] bg-gradient-to-tr from-blue-500 to-indigo-600 flex items-center justify-center text-3xl shadow-lg shadow-blue-500/20">
                🦆
            </div>
            <div>
                <h2 class="text-lg font-black text-white">به Duck Store خوش اومدی!</h2>
                <p class="text-xs text-cyan-300/80 mt-1 font-semibold">پلتفرم مدرن مبادلات ارز و گیفت تلگرام</p>
            </div>
            <div class="w-full space-y-2.5 text-right text-xs">
                <div class="p-3 rounded-2xl bg-white/[0.03] border border-white/5 flex items-center gap-3">
                    <span class="text-xl">🎁</span>
                    <div>
                        <p class="font-bold text-white">اجاره گیفت‌های ارزشمند</p>
                        <p class="text-[10px] text-slate-400">تخفیف‌های بالای ۵۰٪ و شماره‌های خاص</p>
                    </div>
                </div>
                <div class="p-3 rounded-2xl bg-white/[0.03] border border-white/5 flex items-center gap-3">
                    <span class="text-xl">👑</span>
                    <div>
                        <p class="font-bold text-white">تلگرام پرمیوم لحظه‌ای</p>
                        <p class="text-[10px] text-slate-400">نرخ کاملاً زنده بر اساس بازار فرگمنت</p>
                    </div>
                </div>
                <div class="p-3 rounded-2xl bg-white/[0.03] border border-white/5 flex items-center gap-3">
                    <span class="text-xl">⭐</span>
                    <div>
                        <p class="font-bold text-white">استارز رسمی تلگرام</p>
                        <p class="text-[10px] text-slate-400">تحویل آنی بدون نیاز به لاگین در اکانت</p>
                    </div>
                </div>
            </div>
            <button onclick="enterStore()" class="w-full py-3.5 bg-gradient-to-r from-blue-500 via-indigo-500 to-cyan-400 hover:opacity-90 text-white font-black text-xs rounded-2xl transition shadow-xl shadow-blue-500/25 flex items-center justify-center gap-2">
                <span>بزن بریم</span>
                <i class="fa-solid fa-arrow-left text-xs"></i>
            </button>
        </div>
    </div>

    <!-- 📢 بنر مناسبتی با انیمیشن ملایم -->
    <div id="promoBanner" class="hidden bg-gradient-to-r from-indigo-900/90 via-blue-900/90 to-purple-900/90 border-b border-white/10 text-white text-xs font-semibold py-2.5 px-4 text-center backdrop-blur-md flex items-center justify-center gap-2">
        <i class="fa-solid fa-bolt text-amber-400 text-xs"></i>
        <span id="promoBannerText"></span>
    </div>

    <!-- هدر با سبک مدرن iOS Dashboard -->
    <header class="sticky top-0 z-30 bg-[#060913]/80 backdrop-blur-xl border-b border-white/5">
        <div class="max-w-6xl mx-auto px-4 sm:px-6 h-18 py-3.5 flex items-center justify-between">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-[14px] bg-gradient-to-tr from-blue-500 to-indigo-600 flex items-center justify-center text-xl shadow-lg shadow-blue-500/20">
                    🦆
                </div>
                <div>
                    <h1 class="text-sm sm:text-base font-black text-white tracking-tight">Duck Store</h1>
                    <p id="tgUserGreeting" class="text-[11px] text-slate-400 font-medium">مرجع خدمات تلگرام</p>
                </div>
            </div>

            <div class="flex items-center gap-2">
                <a id="headerSupportLink" href="https://t.me/Zanjani_a" onclick="openTgLink(this.href); return false;" class="px-3.5 py-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-slate-200 border border-white/10 text-xs font-bold transition flex items-center gap-2">
                    <i class="fa-brands fa-telegram text-sky-400"></i>
                    <span>پشتیبانی</span>
                </a>
            </div>
        </div>

        <!-- کنترل تب‌های آیفونی (Pill Navigation) -->
        <div class="max-w-6xl mx-auto px-4 sm:px-6 pb-2.5 overflow-x-auto">
            <div class="ios-pill-tab flex items-center gap-1 w-max min-w-full sm:min-w-0">
                <button onclick="switchMainTab('gifts')" id="tabBtn-gifts" class="flex-1 px-5 py-2 rounded-full text-xs font-black transition flex items-center justify-center gap-1.5 whitespace-nowrap bg-white text-slate-950 shadow-sm">
                    <i class="fa-solid fa-gift"></i>
                    <span class="tab-label">اجاره گیفت</span>
                </button>
                <button onclick="switchMainTab('stars')" id="tabBtn-stars" class="flex-1 px-5 py-2 rounded-full text-xs font-bold transition flex items-center justify-center gap-1.5 whitespace-nowrap text-slate-400 hover:text-white">
                    <i class="fa-solid fa-star text-amber-400"></i>
                    <span class="tab-label">استارز تلگرام</span>
                </button>
                <button onclick="switchMainTab('premium')" id="tabBtn-premium" class="flex-1 px-5 py-2 rounded-full text-xs font-bold transition flex items-center justify-center gap-1.5 whitespace-nowrap text-slate-400 hover:text-white">
                    <i class="fa-solid fa-crown text-purple-400"></i>
                    <span class="tab-label">تلگرام پرمیوم</span>
                </button>
            </div>
        </div>
    </header>

    <main class="max-w-6xl mx-auto px-4 sm:px-6 mt-5">
        
        <!-- ۱. بخش گیفت‌ها -->
        <section id="section-gifts" class="block space-y-4">
            <!-- نوار فیلتر و ابزار مدرن -->
            <div class="ios-glass-card p-3 sm:p-4 flex flex-col sm:flex-row items-center justify-between gap-3">
                <div class="relative w-full sm:w-80">
                    <i class="fa-solid fa-magnifying-glass absolute right-4 top-3.5 text-slate-500 text-xs"></i>
                    <input type="text" id="searchInput" placeholder="جستجوی نام یا شناسه گیفت..." 
                           class="w-full bg-[#060913]/60 border border-white/10 rounded-2xl pr-10 pl-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400 transition">
                </div>

                <div class="flex items-center gap-2 w-full sm:w-auto overflow-x-auto pb-1 sm:pb-0">
                    <button onclick="openModal()" class="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold bg-white/[0.04] hover:bg-white/[0.08] text-slate-200 border border-white/10 transition whitespace-nowrap">
                        <i class="fa-solid fa-layer-group text-cyan-400 text-xs"></i>
                        <span id="selectedColText">کالکشن‌ها</span>
                        <i class="fa-solid fa-chevron-down text-[9px] text-slate-500 mr-0.5"></i>
                    </button>
                    <button onclick="filterType('all', this)" class="type-btn active px-4 py-2 rounded-xl text-xs font-black bg-cyan-400 text-slate-950 transition whitespace-nowrap shadow-lg shadow-cyan-400/20">همه (__TOTAL_COUNT__)</button>
                    <button onclick="filterType('rare', this)" class="type-btn px-3.5 py-2 rounded-xl text-xs font-bold bg-white/[0.04] text-slate-300 hover:text-white border border-white/10 transition whitespace-nowrap">💎 کمیاب‌ها (__RARE_COUNT__)</button>
                    <button onclick="filterType('favs', this)" class="type-btn px-3.5 py-2 rounded-xl text-xs font-bold bg-white/[0.04] text-slate-300 hover:text-rose-400 border border-white/10 transition whitespace-nowrap flex items-center gap-1.5">
                        <i class="fa-solid fa-heart text-rose-500 text-xs"></i> (<span id="favCount">0</span>)
                    </button>
                </div>
            </div>

            <!-- گرید نمایش ویجتی کارت‌ها -->
            <div id="dealsGrid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-5"></div>
        </section>

        <!-- ۲. بخش استارز -->
        <section id="section-stars" class="hidden max-w-xl mx-auto space-y-5">
            <div class="ios-glass-card p-6 space-y-3">
                <h3 class="text-xs font-bold text-slate-300 flex items-center gap-2">
                    <span class="text-amber-400 text-sm">⭐</span>
                    <span>تعداد استارز دلخواه</span>
                </h3>
                <input type="number" id="customStarsInput" min="50" max="10000000" placeholder="حداقل ۵۰ تا ۱۰,۰۰۰,۰۰۰ استارز..." 
                       class="w-full bg-[#060913]/80 border border-white/10 rounded-2xl px-4 py-3.5 text-sm text-white font-bold placeholder-slate-600 focus:outline-none focus:border-amber-400 transition">
                <div id="customStarsCalcBox" class="p-3.5 rounded-2xl bg-white/[0.03] border border-white/5 flex items-center justify-between hidden">
                    <span class="text-xs text-slate-400">مبلغ محاسبه‌شده:</span>
                    <span id="customStarsPrice" class="text-sm font-black text-amber-400">0 تومان</span>
                </div>
            </div>

            <div class="ios-glass-card p-6 space-y-4">
                <h3 class="text-xs font-bold text-slate-400">یا انتخاب پکیج‌های آماده:</h3>
                <div id="starsPackagesList" class="space-y-2.5"></div>

                <div class="pt-4 border-t border-white/5 flex items-center justify-between">
                    <div>
                        <p class="text-[11px] text-slate-400">مبلغ نهایی پرداخت:</p>
                        <p id="selectedStarsFinalToman" class="text-lg font-black text-amber-400">0 تومان</p>
                    </div>
                    <button onclick="orderStars()" class="py-3 px-6 rounded-2xl bg-gradient-to-r from-amber-400 to-amber-500 hover:opacity-90 text-slate-950 font-black text-xs transition shadow-lg shadow-amber-500/20 flex items-center gap-2">
                        <span>خرید استارز</span>
                        <i class="fa-solid fa-bolt text-xs"></i>
                    </button>
                </div>
            </div>
        </section>

        <!-- ۳. بخش پرمیوم (کاملاً خودکار متصل به فرگمنت) -->
        <section id="section-premium" class="hidden max-w-xl mx-auto space-y-5">
            <div class="ios-glass-card p-6 space-y-4">
                <div class="flex items-center justify-between">
                    <h3 class="text-sm font-black text-white flex items-center gap-2">
                        <i class="fa-solid fa-crown text-purple-400 text-sm"></i>
                        <span>اشتراک تلگرام پرمیوم (Fragment Live)</span>
                    </h3>
                    <span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-cyan-400/10 text-cyan-400 border border-cyan-400/20">
                        نرخ لحظه‌ای
                    </span>
                </div>

                <div class="space-y-3" id="premiumOptionsList"></div>

                <div class="pt-4 border-t border-white/5 flex items-center justify-between">
                    <div>
                        <p class="text-[11px] text-slate-400">مبلغ اشتراک پرمیوم:</p>
                        <p id="selectedPremiumFinalToman" class="text-lg font-black text-purple-400">0 تومان</p>
                    </div>
                    <button onclick="orderPremium()" class="py-3 px-6 rounded-2xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:opacity-90 text-white font-black text-xs transition shadow-lg shadow-purple-600/25 flex items-center gap-2">
                        <span>خرید پرمیوم</span>
                        <i class="fa-solid fa-crown text-xs"></i>
                    </button>
                </div>
            </div>
        </section>
    </main>

    <!-- نوار شناور سبد خرید مدرن (Floating Dock) -->
    <div id="floatingCartBar" class="fixed bottom-4 inset-x-4 max-w-lg mx-auto z-40 bg-[#0c1224]/90 backdrop-blur-2xl border border-white/10 p-3.5 rounded-[26px] shadow-2xl shadow-black/80 transition-all duration-300 transform translate-y-48 opacity-0 space-y-3">
        <div class="flex items-center gap-2 bg-[#060913]/80 p-1.5 rounded-2xl border border-white/5">
            <input type="text" id="couponInput" placeholder="کد تخفیف داری؟ وارد کن..." class="bg-transparent text-xs text-white px-3 py-1.5 flex-1 focus:outline-none uppercase font-bold placeholder-slate-500">
            <button onclick="applyCoupon()" class="px-3.5 py-1.5 bg-white/10 hover:bg-white/20 text-white text-xs font-bold rounded-xl transition">اعمال</button>
        </div>

        <div class="flex items-center justify-between pt-1 border-t border-white/5">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-2xl bg-gradient-to-tr from-cyan-400 to-blue-500 text-slate-950 flex items-center justify-center font-black text-sm shadow-md shadow-cyan-500/20">
                    <span id="cartCountBadge">0</span>
                </div>
                <div>
                    <div class="flex items-center gap-2">
                        <p class="text-xs font-bold text-white">سبد اجاره</p>
                        <span id="discountTag" class="hidden px-2 py-0.5 rounded text-[10px] font-black bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">تخفیف اعمال شد</span>
                    </div>
                    <p id="cartTotalPrice" class="text-xs text-cyan-400 font-black">0 تومان</p>
                </div>
            </div>
            <div class="flex items-center gap-2">
                <button onclick="clearCart()" class="p-2 text-slate-400 hover:text-rose-400 text-xs transition" title="خالی کردن">
                    <i class="fa-solid fa-trash-can text-sm"></i>
                </button>
                <button onclick="checkoutCart()" class="py-2.5 px-5 rounded-xl bg-gradient-to-r from-blue-500 to-cyan-400 hover:opacity-90 text-slate-950 text-xs font-black transition shadow-lg shadow-cyan-400/20 flex items-center gap-2">
                    <span>ثبت سفارش</span>
                    <i class="fa-solid fa-arrow-left text-[11px]"></i>
                </button>
            </div>
        </div>
    </div>

    <!-- مودال انتخاب کالکشن -->
    <div id="collectionModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md hidden">
        <div class="modal-bg w-full max-w-md rounded-[32px] overflow-hidden shadow-2xl flex flex-col max-h-[85vh]">
            <div class="px-6 py-4 flex items-center justify-between border-b border-white/10">
                <button onclick="closeModal()" class="w-7 h-7 rounded-full bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white flex items-center justify-center transition">
                    <i class="fa-solid fa-xmark text-xs"></i>
                </button>
                <h3 class="text-sm font-black text-white">انتخاب کالکشن‌ها</h3>
                <div class="w-7"></div>
            </div>

            <div class="p-4 border-b border-white/10 space-y-2.5">
                <div class="relative">
                    <input type="text" id="modalSearchInput" placeholder="جستجوی کالکشن..." 
                           class="w-full bg-[#060913] border border-white/10 rounded-2xl pr-4 pl-9 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400 transition">
                    <i class="fa-solid fa-magnifying-glass absolute left-3.5 top-3 text-slate-500 text-xs"></i>
                </div>
                <div class="flex items-center justify-between px-1 text-xs">
                    <button onclick="selectAllCollections()" class="text-cyan-400 hover:underline text-[11px] font-bold">انتخاب همه</button>
                    <button onclick="clearCollectionSelection()" class="text-slate-400 hover:text-rose-400 text-[11px]">پاک کردن</button>
                </div>
            </div>

            <div id="modalCollectionsList" class="p-4 space-y-2 overflow-y-auto flex-1"></div>

            <div class="p-4 border-t border-white/10 bg-[#060913]/60">
                <button onclick="applyCollectionModal()" class="w-full py-3 bg-gradient-to-r from-blue-500 to-cyan-400 hover:opacity-90 text-slate-950 text-xs font-black rounded-2xl transition shadow-lg shadow-cyan-500/20 flex items-center justify-center gap-2">
                    <span>اعمال فیلتر</span>
                    <span id="modalSelectedCountBadge" class="bg-black/20 px-2 py-0.5 rounded-full text-[11px]">0</span>
                </button>
            </div>
        </div>
    </div>

    <script>
        let tgUser = null;
        if (window.Telegram && window.Telegram.WebApp) {
            window.Telegram.WebApp.ready();
            window.Telegram.WebApp.expand();
            if (window.Telegram.WebApp.MainButton) window.Telegram.WebApp.MainButton.hide();
            tgUser = window.Telegram.WebApp.initDataUnsafe?.user || null;
            if (tgUser) {
                const name = tgUser.first_name || tgUser.username || "کاربر عزیز";
                document.getElementById('tgUserGreeting').innerText = `خوش آمدید، ${name} 👋`;
            }
        }

        function triggerHaptic(type = 'light') {
            if (window.Telegram?.WebApp?.HapticFeedback) {
                if (type === 'selection') window.Telegram.WebApp.HapticFeedback.selectionChanged();
                else window.Telegram.WebApp.HapticFeedback.impactOccurred(type);
            }
        }

        function openTgLink(url) {
            const cleanUrl = url.replace('https://t.me/@', 'https://t.me/');
            if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.openTelegramLink) {
                try {
                    window.Telegram.WebApp.openTelegramLink(cleanUrl);
                    return;
                } catch(e) {}
            }
            try {
                const win = window.open(cleanUrl, '_blank');
                if (!win || win.closed || typeof win.closed === 'undefined') {
                    window.location.href = cleanUrl;
                }
            } catch(e) {
                window.location.href = cleanUrl;
            }
        }

        // انیمیشن اسپلش و هدایت به خوش‌آمدگویی
        let loadingProgress = 5;
        function startLoadingFlow() {
            const bar = document.getElementById('loadingProgressBar');
            const pct = document.getElementById('loadingPercent');
            const interval = setInterval(() => {
                loadingProgress += Math.floor(Math.random() * 15) + 10;
                if (loadingProgress >= 100) {
                    loadingProgress = 100;
                    clearInterval(interval);
                    if (bar) bar.style.width = '100%';
                    if (pct) pct.innerText = '100%';
                    setTimeout(transitionToWelcome, 300);
                } else {
                    if (bar) bar.style.width = loadingProgress + '%';
                    if (pct) pct.innerText = loadingProgress + '%';
                }
            }, 90);
        }

        function transitionToWelcome() {
            const loader = document.getElementById('loadingScreen');
            const welcome = document.getElementById('welcomeScreen');
            if (loader) {
                loader.classList.add('opacity-0', 'pointer-events-none');
                setTimeout(() => { loader.style.display = 'none'; }, 400);
            }
            if (welcome) {
                welcome.classList.remove('hidden');
                setTimeout(() => { welcome.classList.remove('opacity-0', 'scale-95'); }, 50);
            }
        }

        function enterStore() {
            triggerHaptic('heavy');
            const welcome = document.getElementById('welcomeScreen');
            if (welcome) {
                welcome.classList.add('opacity-0', 'scale-95', 'pointer-events-none');
                setTimeout(() => { welcome.style.display = 'none'; }, 400);
            }
        }

        const DEALS = __DEALS_JSON__;
        const COLLECTIONS = __COLLECTIONS_JSON__;
        const WORKER_URL = "__WORKER_URL__";

        // قیمت‌های هوشمند استخراج‌شده از فرگمنت و نوبیتکس
        const AUTO_PRICES = __AUTO_PRICES_JSON__;

        const DEFAULT_SETTINGS = {
            ratePerStar: 1450,
            prem3: AUTO_PRICES.prem3,
            prem6: AUTO_PRICES.prem6,
            prem12: AUTO_PRICES.prem12,
            giftMonthlyPrice: 160000,
            adminTg: 'Zanjani_a',
            announcementText: '🎉 تخفیف ویژه پرمیوم محاسبه‌شده با نرخ زنده فرگمنت',
            announcementActive: true,
            couponCode: 'DUCK',
            couponPercent: 10,
            tabGiftsActive: true,
            tabStarsActive: true,
            tabPremiumActive: true
        };

        let SETTINGS = { ...DEFAULT_SETTINGS };
        let currentMainTab = 'gifts';
        let selectedType = 'all';
        let selectedCollections = new Set();
        let tempSelectedCollections = new Set();
        let appliedCouponCode = null;
        let appliedDiscountPercent = 0;
        let selectedStarsCount = 50;
        let selectedPremiumMonths = 12;

        const STARS_PACKAGES = [50, 75, 100, 150, 250, 350, 500, 1000, 2500, 5000];
        let favorites = JSON.parse(localStorage.getItem('duck_favs') || '[]');
        let cart = JSON.parse(localStorage.getItem('duck_cart') || '[]');

        async function fetchCloudSettings() {
            try {
                const res = await fetch(`${WORKER_URL}/api/settings`);
                if (res.ok) {
                    const parsed = await res.json();
                    if (parsed && typeof parsed === 'object') {
                        SETTINGS = { ...DEFAULT_SETTINGS, ...parsed };
                    }
                }
            } catch (err) {}
            updateUIWithLatestSettings();
        }

        function updateUIWithLatestSettings() {
            const adminUser = (SETTINGS.adminTg || 'Zanjani_a').replace('@', '').trim();
            document.getElementById('headerSupportLink').href = `https://t.me/${adminUser}`;

            const promo = document.getElementById('promoBanner');
            if (SETTINGS.announcementActive && SETTINGS.announcementText) {
                document.getElementById('promoBannerText').innerText = SETTINGS.announcementText;
                promo.classList.remove('hidden');
            } else {
                promo.classList.add('hidden');
            }

            updateTabAvailability();
            renderCards(getFilteredDeals());
            renderStarsPackages();
            renderPremiumOptions();
            updateCartUI();
        }

        function updateTabAvailability() {
            const tabs = [
                { id: 'gifts', active: SETTINGS.tabGiftsActive !== false, label: 'اجاره گیفت' },
                { id: 'stars', active: SETTINGS.tabStarsActive !== false, label: 'استارز تلگرام' },
                { id: 'premium', active: SETTINGS.tabPremiumActive !== false, label: 'تلگرام پرمیوم' }
            ];

            tabs.forEach(t => {
                const btn = document.getElementById(`tabBtn-${t.id}`);
                const labelSpan = btn.querySelector('.tab-label');
                if (!t.active) {
                    btn.classList.add('opacity-40', 'cursor-not-allowed');
                    if (labelSpan && !labelSpan.innerHTML.includes('ناموجود')) {
                        labelSpan.innerHTML = `${t.label} <span class="text-[9px] bg-rose-500/20 text-rose-300 px-1 rounded">ناموجود</span>`;
                    }
                } else {
                    if (t.id !== currentMainTab) btn.classList.remove('opacity-40', 'cursor-not-allowed');
                    if (labelSpan) labelSpan.innerText = t.label;
                }
            });
        }

        function switchMainTab(tab) {
            if (tab === 'gifts' && SETTINGS.tabGiftsActive === false) return alert('⚠️ بخش اجاره گیفت موقتاً غیرفعال است.');
            if (tab === 'stars' && SETTINGS.tabStarsActive === false) return alert('⚠️ بخش استارز موقتاً غیرفعال است.');
            if (tab === 'premium' && SETTINGS.tabPremiumActive === false) return alert('⚠️ بخش پرمیوم موقتاً غیرفعال است.');

            triggerHaptic('selection');
            currentMainTab = tab;

            const tabIds = ['gifts', 'stars', 'premium'];
            tabIds.forEach(t => {
                const sec = document.getElementById(`section-${t}`);
                const btn = document.getElementById(`tabBtn-${t}`);
                if (!sec || !btn) return;

                if (t === tab) {
                    sec.classList.remove('hidden');
                    btn.className = "flex-1 px-5 py-2 rounded-full text-xs font-black transition flex items-center justify-center gap-1.5 whitespace-nowrap bg-white text-slate-950 shadow-md";
                } else {
                    sec.classList.add('hidden');
                    btn.className = "flex-1 px-5 py-2 rounded-full text-xs font-bold transition flex items-center justify-center gap-1.5 whitespace-nowrap text-slate-400 hover:text-white";
                }
            });

            updateCartUI();
        }

        // ================= استارز =================
        function renderStarsPackages() {
            const container = document.getElementById('starsPackagesList');
            container.innerHTML = STARS_PACKAGES.map(qty => {
                const totalToman = (qty * SETTINGS.ratePerStar).toLocaleString('en-US');
                const isSelected = selectedStarsCount === qty;
                return `
                <div onclick="selectStarsPackage(${qty})" class="p-3.5 rounded-2xl bg-white/[0.02] hover:bg-white/[0.05] border ${isSelected ? 'border-amber-400 bg-amber-400/5' : 'border-white/5'} flex items-center justify-between cursor-pointer transition">
                    <div class="flex items-center gap-3">
                        <div class="w-4 h-4 rounded-full border ${isSelected ? 'border-amber-400 bg-amber-400' : 'border-slate-600'}"></div>
                        <span class="text-xs font-bold text-white">${qty} Stars</span>
                    </div>
                    <span class="text-xs font-black text-amber-400">${totalToman} t</span>
                </div>
                `;
            }).join('');
            updateStarsFinalPrice();
        }

        function selectStarsPackage(qty) {
            triggerHaptic('selection');
            selectedStarsCount = qty;
            document.getElementById('customStarsInput').value = '';
            document.getElementById('customStarsCalcBox').classList.add('hidden');
            renderStarsPackages();
        }

        document.getElementById('customStarsInput').addEventListener('input', (e) => {
            const val = parseInt(e.target.value);
            if (val && val >= 50) {
                selectedStarsCount = val;
                const total = (val * SETTINGS.ratePerStar).toLocaleString('en-US');
                document.getElementById('customStarsPrice').innerText = `${total} تومان`;
                document.getElementById('customStarsCalcBox').classList.remove('hidden');
            } else {
                document.getElementById('customStarsCalcBox').classList.add('hidden');
            }
            updateStarsFinalPrice();
        });

        function updateStarsFinalPrice() {
            const total = (selectedStarsCount * SETTINGS.ratePerStar).toLocaleString('en-US');
            document.getElementById('selectedStarsFinalToman').innerText = `${total} تومان`;
        }

        function orderStars() {
            triggerHaptic('heavy');
            const adminUser = (SETTINGS.adminTg || 'Zanjani_a').replace('@', '').trim();
            const total = (selectedStarsCount * SETTINGS.ratePerStar).toLocaleString('en-US');
            const buyerInfo = getBuyerDetailsText();
            const nl = String.fromCharCode(10);
            const msg = encodeURIComponent(
                "سلام، متقاضی خرید استارز هستم:" + nl + nl +
                buyerInfo + nl + nl +
                "تعداد استارز: " + selectedStarsCount + " Stars" + nl +
                "مبلغ پرداختی: " + total + " تومان"
            );
            openTgLink("https://t.me/" + adminUser + "?text=" + msg);
        }

        // ================= پرمیوم هوشمند =================
        function renderPremiumOptions() {
            const container = document.getElementById('premiumOptionsList');
            const options = [
                { months: 12, label: '۱۲ ماهه (1 Year)', discount: '-52%', price: SETTINGS.prem12 },
                { months: 6, label: '۶ ماهه (6 Months)', discount: '-47%', price: SETTINGS.prem6 },
                { months: 3, label: '۳ ماهه (3 Months)', discount: '-20%', price: SETTINGS.prem3 }
            ];

            container.innerHTML = options.map(opt => {
                const isSelected = selectedPremiumMonths === opt.months;
                const totalToman = opt.price.toLocaleString('en-US');
                return `
                <div onclick="selectPremiumPlan(${opt.months})" class="p-4 rounded-2xl bg-white/[0.02] hover:bg-white/[0.05] border ${isSelected ? 'border-purple-400 bg-purple-500/10' : 'border-white/5'} flex items-center justify-between cursor-pointer transition">
                    <div class="flex items-center gap-3">
                        <div class="w-4 h-4 rounded-full border ${isSelected ? 'border-purple-400 bg-purple-400' : 'border-slate-600'}"></div>
                        <span class="text-xs font-bold text-white">${opt.label}</span>
                        <span class="px-2 py-0.5 rounded-md text-[10px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30">${opt.discount}</span>
                    </div>
                    <span class="text-xs font-black text-purple-300">${totalToman} t</span>
                </div>
                `;
            }).join('');
            updatePremiumFinalPrice();
        }

        function selectPremiumPlan(months) {
            triggerHaptic('selection');
            selectedPremiumMonths = months;
            renderPremiumOptions();
        }

        function updatePremiumFinalPrice() {
            let price = SETTINGS.prem12;
            if (selectedPremiumMonths === 6) price = SETTINGS.prem6;
            if (selectedPremiumMonths === 3) price = SETTINGS.prem3;
            document.getElementById('selectedPremiumFinalToman').innerText = `${price.toLocaleString('en-US')} تومان`;
        }

        function orderPremium() {
            triggerHaptic('heavy');
            const adminUser = (SETTINGS.adminTg || 'Zanjani_a').replace('@', '').trim();
            let planName = '1 ساله';
            let price = SETTINGS.prem12;
            if (selectedPremiumMonths === 6) { planName = '6 ماهه'; price = SETTINGS.prem6; }
            if (selectedPremiumMonths === 3) { planName = '3 ماهه'; price = SETTINGS.prem3; }
            const total = price.toLocaleString('en-US');
            const buyerInfo = getBuyerDetailsText();
            const nl = String.fromCharCode(10);
            const msg = encodeURIComponent(
                "سلام، متقاضی خرید تلگرام پرمیوم هستم:" + nl + nl +
                buyerInfo + nl + nl +
                "نوع اشتراک: " + planName + nl +
                "مبلغ استعلامی زنده: " + total + " تومان"
            );
            openTgLink("https://t.me/" + adminUser + "?text=" + msg);
        }

        // ================= گیفت‌ها و سبد خرید =================
        function updateFavCount() {
            document.getElementById('favCount').innerText = favorites.length;
        }

        function toggleFavorite(itemId) {
            triggerHaptic('medium');
            const idx = favorites.indexOf(itemId);
            if (idx > -1) favorites.splice(idx, 1);
            else favorites.push(itemId);
            localStorage.setItem('duck_favs', JSON.stringify(favorites));
            updateFavCount();
            renderCards(getFilteredDeals());
        }

        function toggleCart(item) {
            triggerHaptic('selection');
            const existingIdx = cart.findIndex(c => c.name === item.name);
            if (existingIdx > -1) cart.splice(existingIdx, 1);
            else cart.push(item);
            localStorage.setItem('duck_cart', JSON.stringify(cart));
            updateCartUI();
            renderCards(getFilteredDeals());
        }

        function calculateCartFinalPrice() {
            const rawTotal = cart.length * SETTINGS.giftMonthlyPrice;
            if (appliedDiscountPercent > 0) {
                const discount = (rawTotal * appliedDiscountPercent) / 100;
                return Math.round(rawTotal - discount);
            }
            return rawTotal;
        }

        function updateCartUI() {
            const bar = document.getElementById('floatingCartBar');
            const count = cart.length;
            document.getElementById('cartCountBadge').innerText = count;
            const finalTotal = calculateCartFinalPrice().toLocaleString('en-US');
            document.getElementById('cartTotalPrice').innerText = `${finalTotal} تومان / ماه`;

            if (count > 0 && currentMainTab === 'gifts') {
                bar.classList.remove('translate-y-48', 'opacity-0');
                bar.classList.add('translate-y-0', 'opacity-100');
            } else {
                bar.classList.remove('translate-y-0', 'opacity-100');
                bar.classList.add('translate-y-48', 'opacity-0');
            }
        }

        function clearCart() {
            triggerHaptic('light');
            cart = [];
            appliedCouponCode = null;
            appliedDiscountPercent = 0;
            document.getElementById('discountTag').classList.add('hidden');
            document.getElementById('couponInput').value = '';
            localStorage.setItem('duck_cart', JSON.stringify(cart));
            updateCartUI();
            renderCards(getFilteredDeals());
        }

        function getBuyerDetailsText() {
            if (!tgUser) return "خریدار: کاربر وب";
            const name = `${tgUser.first_name || ''} ${tgUser.last_name || ''}`.trim() || 'کاربر تلگرام';
            const uname = tgUser.username ? `@${tgUser.username}` : 'بدون یوزرنیم';
            return `خریدار: ${name} (${uname} - آیدی: ${tgUser.id})`;
        }

        function checkoutCart() {
            triggerHaptic('heavy');
            if (!cart || cart.length === 0) {
                alert('سبد خرید شما خالی است!');
                return;
            }

            const adminUser = (SETTINGS.adminTg || 'Zanjani_a').replace('@', '').trim();
            const finalTotal = calculateCartFinalPrice().toLocaleString('en-US');
            const buyer = getBuyerDetailsText();
            const nl = String.fromCharCode(10);
            const itemsList = cart.map((c, i) => `${i + 1}. 🎁 ${c.name} (${c.tg_link})`).join(nl);
            const coupon = appliedCouponCode ? (nl + `کد تخفیف: ${appliedCouponCode} (${appliedDiscountPercent}% تخفیف)`) : '';

            const message = encodeURIComponent(
                "سلام، درخواست اجاره گیفت دارم:" + nl + nl +
                buyer + nl + nl +
                "اقلام سفارش (" + cart.length + " عدد):" + nl +
                itemsList + nl + nl +
                "مبلغ نهایی: " + finalTotal + " تومان / ماه" +
                coupon
            );

            openTgLink("https://t.me/" + adminUser + "?text=" + message);
        }

        function renderCards(items) {
            const container = document.getElementById('dealsGrid');
            if (items.length === 0) {
                container.innerHTML = '<div class="col-span-full py-16 text-center text-slate-400">گیفتی با این مشخصات پیدا نشد.</div>';
                return;
            }

            const giftPriceFormatted = SETTINGS.giftMonthlyPrice.toLocaleString('en-US');

            container.innerHTML = items.map((deal) => {
                const rarityBadge = deal.rarity ? `<span class="absolute top-3 left-3 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30 backdrop-blur-md">${deal.rarity}</span>` : '';
                const isFav = favorites.includes(deal.name);
                const isInCart = cart.some(c => c.name === deal.name);

                return `
                <div class="ios-glass-card overflow-hidden flex flex-col justify-between ${isInCart ? 'border-cyan-400 bg-cyan-950/20' : ''}">
                    <div>
                        <div class="relative w-full h-48 bg-gradient-to-b from-white/[0.04] to-transparent flex items-center justify-center overflow-hidden border-b border-white/5 rounded-t-[28px]">
                            ${rarityBadge}
                            <button onclick="toggleFavorite('${deal.name}')" class="absolute top-3 right-3 w-8 h-8 rounded-full bg-black/40 backdrop-blur-md flex items-center justify-center text-sm transition hover:scale-110 ${isFav ? 'text-rose-500' : 'text-slate-400 hover:text-white'}">
                                <i class="${isFav ? 'fa-solid' : 'fa-regular'} fa-heart"></i>
                            </button>
                            <img src="${deal.image_url}" alt="${deal.name}" class="w-32 h-32 object-contain filter drop-shadow-[0_12px_24px_rgba(0,0,0,0.8)] transform hover:scale-105 transition duration-300" onerror="this.src='https://marketapp.org/favicon.ico'">
                        </div>

                        <div class="p-4 space-y-3">
                            <h3 class="font-bold text-sm text-center text-white truncate">${deal.name}</h3>
                            <div class="flex flex-col items-center">
                                <span class="px-3.5 py-1 rounded-full text-xs font-black bg-cyan-400/10 text-cyan-300 border border-cyan-400/20">
                                    ${giftPriceFormatted} تومان / ماه
                                </span>
                            </div>
                            <div class="space-y-1.5 text-xs text-slate-400 bg-black/20 p-2.5 rounded-xl border border-white/5">
                                <div class="flex justify-between items-center text-[11px]">
                                    <span class="text-slate-500">کالکشن:</span>
                                    <span class="font-semibold text-slate-200 truncate">${deal.gift_title}</span>
                                </div>
                                <div class="flex justify-between items-center text-[11px]">
                                    <span class="text-slate-500">مدت اجاره:</span>
                                    <span class="font-semibold text-slate-200">${deal.days_range} روز</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="p-4 pt-0 grid grid-cols-2 gap-2">
                        <a href="${deal.tg_link}" target="_blank" onclick="triggerHaptic('light')" class="py-2 px-3 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 text-xs font-bold text-center transition border border-white/10 flex items-center justify-center">
                            مشاهده
                        </a>
                        <button onclick='toggleCart(${JSON.stringify(deal)})' class="py-2 px-3 rounded-xl ${isInCart ? 'bg-cyan-400 text-slate-950 font-black' : 'bg-white hover:bg-slate-200 text-slate-950 font-black'} text-xs text-center transition shadow-md flex items-center justify-center gap-1">
                            <i class="fa-solid ${isInCart ? 'fa-check' : 'fa-plus'} text-xs"></i>
                            ${isInCart ? 'انتخاب شد' : 'اجاره'}
                        </button>
                    </div>
                </div>
                `;
            }).join('');
        }

        function updateModalBadge() {
            const badge = document.getElementById('modalSelectedCountBadge');
            if (badge) badge.innerText = tempSelectedCollections.size === 0 ? 'همه' : `${tempSelectedCollections.size} مورد`;
        }

        function renderModalCollections(query = '') {
            const container = document.getElementById('modalCollectionsList');
            const filtered = COLLECTIONS.filter(c => c.name.toLowerCase().includes(query.toLowerCase()));

            container.innerHTML = filtered.map(col => {
                const isSelected = tempSelectedCollections.has(col.name);
                return `
                <div onclick="toggleModalCollection('${col.name}')" class="p-3 rounded-2xl flex items-center justify-between cursor-pointer border ${isSelected ? 'border-cyan-400 bg-cyan-950/20' : 'border-white/5 bg-white/[0.02]'} hover:bg-white/[0.05] transition">
                    <div class="flex items-center gap-3">
                        <div class="w-4 h-4 rounded-md border ${isSelected ? 'border-cyan-400 bg-cyan-400 text-slate-950' : 'border-slate-600'} flex items-center justify-center">
                            ${isSelected ? '<i class="fa-solid fa-check text-[10px]"></i>' : ''}
                        </div>
                        <span class="text-xs font-bold text-slate-200">${col.name}</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="text-[11px] text-slate-400 bg-black/40 px-2 py-0.5 rounded-md">${col.count}</span>
                        <img src="${col.image}" alt="${col.name}" class="w-7 h-7 rounded-full object-contain p-1 bg-black/40 border border-white/10" onerror="this.src='https://marketapp.org/favicon.ico'">
                    </div>
                </div>
                `;
            }).join('');
            updateModalBadge();
        }

        function toggleModalCollection(name) {
            triggerHaptic('selection');
            if (tempSelectedCollections.has(name)) tempSelectedCollections.delete(name);
            else tempSelectedCollections.add(name);
            renderModalCollections(document.getElementById('modalSearchInput').value.trim());
        }

        function selectAllCollections() {
            triggerHaptic('light');
            COLLECTIONS.forEach(c => tempSelectedCollections.add(c.name));
            renderModalCollections(document.getElementById('modalSearchInput').value.trim());
        }

        function clearCollectionSelection() {
            triggerHaptic('light');
            tempSelectedCollections.clear();
            renderModalCollections(document.getElementById('modalSearchInput').value.trim());
        }

        function openModal() {
            triggerHaptic('light');
            tempSelectedCollections = new Set(selectedCollections);
            document.getElementById('modalSearchInput').value = '';
            document.getElementById('collectionModal').classList.remove('hidden');
            renderModalCollections();
        }

        function closeModal() {
            triggerHaptic('light');
            document.getElementById('collectionModal').classList.add('hidden');
        }

        function applyCollectionModal() {
            triggerHaptic('medium');
            selectedCollections = new Set(tempSelectedCollections);
            updateHeaderCollectionButton();
            closeModal();
            applyFilters();
        }

        function updateHeaderCollectionButton() {
            const label = document.getElementById('selectedColText');
            if (selectedCollections.size === 0 || selectedCollections.size === COLLECTIONS.length) {
                label.innerText = 'کالکشن‌ها';
            } else if (selectedCollections.size === 1) {
                label.innerText = Array.from(selectedCollections)[0];
            } else {
                label.innerText = `${selectedCollections.size} کالکشن`;
            }
        }

        document.getElementById('modalSearchInput').addEventListener('input', (e) => {
            renderModalCollections(e.target.value.trim());
        });

        document.getElementById('collectionModal').addEventListener('click', (e) => {
            if (e.target.id === 'collectionModal') closeModal();
        });

        function filterType(type, btnElement) {
            triggerHaptic('selection');
            selectedType = type;
            document.querySelectorAll('.type-btn').forEach(btn => {
                btn.classList.remove('bg-cyan-400', 'text-slate-950', 'shadow-lg', 'shadow-cyan-400/20');
                btn.classList.add('bg-white/[0.04]', 'text-slate-300');
            });
            if (btnElement) {
                btnElement.classList.remove('bg-white/[0.04]', 'text-slate-300');
                btnElement.classList.add('bg-cyan-400', 'text-slate-950', 'shadow-lg', 'shadow-cyan-400/20');
            }
            applyFilters();
        }

        function getFilteredDeals() {
            const query = document.getElementById('searchInput').value.trim().toLowerCase();
            return DEALS.filter(d => {
                const matchQuery = d.name.toLowerCase().includes(query) || d.number.includes(query) || d.gift_title.toLowerCase().includes(query);
                if (!matchQuery) return false;
                if (selectedType === 'rare' && d.rarity === '') return false;
                if (selectedType === 'favs' && !favorites.includes(d.name)) return false;
                if (selectedCollections.size > 0 && selectedCollections.size < COLLECTIONS.length) {
                    if (!selectedCollections.has(d.gift_title)) return false;
                }
                return true;
            });
        }

        function applyFilters() {
            renderCards(getFilteredDeals());
        }

        document.getElementById('searchInput').addEventListener('input', applyFilters);
        updateFavCount();
        fetchCloudSettings();
        startLoadingFlow();
    </script>
</body>
</html>"""

    html_content = (
        html_template.replace("__TIMESTAMP__", timestamp)
        .replace("__TOTAL_COUNT__", str(len(deals)))
        .replace("__RARE_COUNT__", str(rare_count))
        .replace("__DEALS_JSON__", deals_json)
        .replace("__COLLECTIONS_JSON__", collections_json)
        .replace("__AUTO_PRICES_JSON__", json.dumps(auto_prices))
        .replace("__WORKER_URL__", CONFIG["WORKER_URL"])
    )

    with open(CONFIG["EXPORT_HTML"], "w", encoding="utf-8") as f:
        f.write(html_content)

    with open(CONFIG["EXPORT_JSON"], "w", encoding="utf-8") as f:
        json.dump(deals, f, ensure_ascii=False, indent=2)


def send_telegram_package(deals: List[Dict[str, Any]]):
    token = CONFIG.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = CONFIG.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    gh_repo = CONFIG.get("GITHUB_REPOSITORY", "")
    pages_url = (
        f"https://{gh_repo.split('/')[0]}.github.io/{gh_repo.split('/')[1]}/"
        if "/" in gh_repo
        else "https://zanjania0.github.io/market-deal-bot/"
    )

    grouped_deals = defaultdict(list)
    for d in deals:
        grouped_deals[d["gift_title"]].append(d)

    rare_count = sum(1 for d in deals if d["rarity"])

    full_text = (
        f"🦆 <b>گزارش موجودی جدید 200 گیفت در Duck Store</b>\n"
        f"📅 <i>{timestamp}</i>\n\n"
        f"🌐 <b>ویترین آنلاین فروشگاه:</b>\n👉 <a href='{pages_url}'>{pages_url}</a>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>تعداد کل:</b> {len(deals)} مورد ({len(grouped_deals)} کالکشن)\n"
        f"💎 <b>موارد کمیاب:</b> {rare_count} مورد\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    item_counter = 1
    for collection_name in sorted(grouped_deals.keys()):
        items = grouped_deals[collection_name]
        full_text += f"📦 <b>━━━ کالکشن {collection_name} ({len(items)} مورد) ━━━</b>\n\n"
        for d in items:
            rarity_badge = f"\n   🏆 <b>{d['rarity']}</b>" if d["rarity"] else ""
            full_text += (
                f"<b>{item_counter}. {d['name']}</b>{rarity_badge}\n"
                f"   🏷️ تخفیف: <code>{d['discount']}</code> | 💰 {d['price_per_day']} TON/روز\n"
                f"   📱 <a href='{d['tg_link']}'>مشاهده در تلگرام</a>\n"
                f"   🛒 <a href='{d['market_link']}'>خرید/اجاره در MarketApp</a>\n\n"
            )
            item_counter += 1

    send_chunks_to_telegram(full_text, token, chat_id)
    send_telegram_csv_attachment(
        CONFIG["EXPORT_CSV"],
        token,
        chat_id,
        f"📊 فایل اکسل 200 گیفت Duck Store ({timestamp})",
    )


def send_chunks_to_telegram(text: str, token: str, chat_id: str):
    chunks = []
    current_chunk = ""
    for paragraph in text.split("\n\n"):
        if len(current_chunk) + len(paragraph) + 2 > 3800:
            chunks.append(current_chunk.strip())
            current_chunk = paragraph + "\n\n"
        else:
            current_chunk += paragraph + "\n\n"
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for part in chunks:
        payload = urllib.parse.urlencode(
            {
                "chat_id": chat_id,
                "text": part,
                "parse_mode": "HTML",
                "disable_web_page_preview": "true",
            }
        ).encode("utf-8")
        try:
            req = urllib.request.Request(url, data=payload)
            with urllib.request.urlopen(req, timeout=15):
                pass
            time.sleep(0.5)
        except Exception:
            pass


def send_telegram_csv_attachment(
    file_path: str, token: str, chat_id: str, caption: str
):
    if not os.path.exists(file_path):
        return
    boundary = "----DuckStoreBoundaryXYZ"
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="document"; filename="duck_store_gifts.csv"\r\n'
        f"Content-Type: text/csv\r\n\r\n"
    ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendDocument",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30):
            pass
    except Exception:
        pass


# ==========================================
# ⚡ موتور اسکرپر
# ==========================================
async def main():
    deals_found: List[Dict[str, Any]] = []
    seen_links: Set[str] = set()

    print("\n" + "═" * 65)
    print("  🦆 DUCK STORE TURBO SCRAPER (AUTO PRICING + IOS THEME) 🦆")
    print("═" * 65 + "\n")

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
        except Exception:
            browser = await p.chromium.launch(headless=True, channel="chrome")

        page = await browser.new_page()

        # ۱. استعلام خودکار نرخ‌های پرمیوم از فرگمنت و نوبیتکس
        auto_prices = await fetch_auto_pricing(page)

        # ۲. اسکرپ ۲۰۰ گیفت از مارکت‌اپ
        print("🌐 بارگذاری اولیه مارکت...")
        await page.goto(
            CONFIG["TARGET_URL"], wait_until="domcontentloaded", timeout=60000
        )
        await page.wait_for_timeout(3000)

        while len(deals_found) < CONFIG["TARGET_DEALS_COUNT"]:
            raw_cards = await page.evaluate(
                """() => {
                const cards = Array.from(document.querySelectorAll("a[href*='/nft/']"));
                return cards.map(c => ({
                    href: c.getAttribute('href') || '',
                    text: c.innerText || '',
                    img: c.querySelector('img') ? c.querySelector('img').src : ''
                }));
            }"""
            )

            for c in raw_cards:
                href = c["href"]
                if not href:
                    continue

                full_link = (
                    href
                    if href.startswith("http")
                    else f"{CONFIG['BASE_DOMAIN']}{href if href.startswith('/') else '/' + href}"
                )
                if full_link in seen_links:
                    continue

                text = c["text"]
                if not text.strip():
                    continue

                discount_match = re.search(r"-(\d+(?:\.\d+)?)%", text)
                if discount_match:
                    discount_val = float(discount_match.group(1))

                    if discount_val >= CONFIG["MIN_DISCOUNT_PERCENT"]:
                        num_match = re.search(r"#(\d+)", text)
                        item_num = num_match.group(1) if num_match else "0"

                        days_match = re.search(
                            r"Days:\s*(\d+\s*–\s*\d+)", text
                        )
                        days_range = (
                            days_match.group(1) if days_match else "1 – 180"
                        )

                        lines = [
                            l.strip() for l in text.split("\n") if l.strip()
                        ]
                        name_candidates = [
                            l
                            for l in lines
                            if not l.startswith("Days:")
                            and not l.startswith("-")
                            and not l.startswith("#")
                            and l.lower() not in ["per day", "min. price"]
                            and not re.match(r"^\d+(\.\d+)?$", l)
                        ]

                        gift_name = (
                            name_candidates[0] if name_candidates else "NFT Gift"
                        )
                        tg_link = generate_tg_nft_link(gift_name, item_num)
                        rarity = detect_rarity_badge(item_num)
                        img_src = (
                            c["img"]
                            if c["img"]
                            else "https://marketapp.org/favicon.ico"
                        )

                        deal = {
                            "name": f"{gift_name} #{item_num}",
                            "gift_title": gift_name,
                            "number": item_num,
                            "discount": f"-{discount_val}%",
                            "discount_num": discount_val,
                            "price_per_day": "0.01",
                            "days_range": days_range,
                            "tg_link": tg_link,
                            "market_link": full_link,
                            "image_url": img_src,
                            "rarity": rarity,
                        }

                        seen_links.add(full_link)
                        deals_found.append(deal)

                        if len(deals_found) >= CONFIG["TARGET_DEALS_COUNT"]:
                            break
                else:
                    seen_links.add(full_link)

            if len(deals_found) >= CONFIG["TARGET_DEALS_COUNT"]:
                break

            await page.evaluate("window.scrollBy(0, window.innerHeight * 3);")
            await page.wait_for_timeout(400)

        await browser.close()

        # 🎯 چیدمان بر اساس جدیدترین‌ها
        sorted_deals = list(reversed(deals_found))

        # ساخت HTML با قیمت‌های خودکار
        generate_duck_store_html(sorted_deals, auto_prices)

        with open(
            CONFIG["EXPORT_CSV"], "w", encoding="utf-8-sig", newline=""
        ) as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "ردیف",
                    "کالکشن",
                    "نام گیفت",
                    "شماره",
                    "تخفیف",
                    "کمیابی",
                    "لینک تلگرام",
                    "لینک MarketApp",
                ]
            )
            for idx, d in enumerate(sorted_deals, 1):
                writer.writerow(
                    [
                        idx,
                        d["gift_title"],
                        d["name"],
                        d["number"],
                        d["discount"],
                        d["rarity"] or "معمولی",
                        d["tg_link"],
                        d["market_link"],
                    ]
                )

        print(
            "\n⚡ فروشگاه Duck Store با دیزاین جدید آیفونی و قیمت‌گذاری خودکار آماده شد!"
        )
        send_telegram_package(sorted_deals)


if __name__ == "__main__":
    asyncio.run(main())
