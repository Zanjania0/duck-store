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
# 📈 موتور هوشمند محاسبه خودکار نرخ پرمیوم در بک‌اند
# ==========================================
async def calculate_live_pricing(page) -> Dict[str, Any]:
    print("\n" + "═" * 60)
    print("📈 محاسبه خودکار قیمت پرمیوم بر اساس بازار و سود ادمین...")
    print("═" * 60)

    ton_tiers = {"prem3": 3.8, "prem6": 5.8, "prem12": 9.9}
    ton_usd = 5.3
    usdt_toman = 60000
    profit_margin = 15.0

    # ۱. واکشی درصد سود ادمین از Cloudflare Worker
    try:
        req = urllib.request.Request(
            f"{CONFIG['WORKER_URL']}/api/settings",
            headers={"User-Agent": "DuckStoreEngine/2.0"},
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            cloud_settings = json.loads(res.read().decode())
            profit_margin = float(cloud_settings.get("profitMargin", 15.0))
            print(f"💰 درصد سود ادمین اعمال شد: {profit_margin}%")
    except Exception:
        print(f"ℹ️ درصد سود پیش‌فرض: {profit_margin}%")

    # ۲. استعلام زنده نرخ جهانی TON از CoinGecko
    try:
        req = urllib.request.Request(
            "https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd",
            headers={"User-Agent": "DuckStoreEngine/2.0"},
        )
        with urllib.request.urlopen(req, timeout=6) as res:
            cg_data = json.loads(res.read().decode())
            ton_usd = float(cg_data["the-open-network"]["usd"])
    except Exception:
        pass

    # ۳. استعلام نرخ تتر از نوبیتکس
    try:
        req = urllib.request.Request(
            "https://api.nobitex.ir/v2/orderbook/USDTIRT",
            headers={"User-Agent": "DuckStoreEngine/2.0"},
        )
        with urllib.request.urlopen(req, timeout=6) as res:
            nobi = json.loads(res.read().decode())
            usdt_toman = float(nobi.get("lastTradePrice", 600000)) / 10
    except Exception:
        pass

    # ۴. محاسبه مبالغ نهایی به تومان با سود ادمین
    ton_toman = ton_usd * usdt_toman
    profit_factor = 1.0 + (profit_margin / 100.0)

    computed = {
        "prem3": int(round(ton_tiers["prem3"] * ton_toman * profit_factor, -3)),
        "prem6": int(round(ton_tiers["prem6"] * ton_toman * profit_factor, -3)),
        "prem12": int(round(ton_tiers["prem12"] * ton_toman * profit_factor, -3)),
    }

    print(f"🎯 مبالغ پرمیوم به تومان: ۳ ماهه={computed['prem3']:,} | ۶ ماهه={computed['prem6']:,} | ۱ ساله={computed['prem12']:,}\n")
    return computed


def detect_rarity_badge(number_str: str) -> str:
    try:
        num = int(re.sub(r"\D", "", str(number_str)))
    except ValueError:
        return ""
    s = str(num)
    if num < 100: return "👑 زیر 100"
    if num < 1000: return f"💎 زیر 1000"
    if len(s) >= 3 and len(set(s)) == 1: return f"✨ رند (#{s})"
    if s in ["123", "1234", "12345", "6969", "777", "888", "999", "10000"]: return f"🎯 خاص (#{s})"
    if len(s) == 4 and s == s[::-1]: return f"🔁 متقارن"
    return ""


def generate_tg_nft_link(name: str, number: str) -> str:
    words = re.findall(r"[a-zA-Z0-9]+", name)
    slug = "".join(w.capitalize() for w in words)
    clean_num = re.sub(r"\D", "", str(number))
    return f"https://t.me/nft/{slug}-{clean_num}" if slug and clean_num else "https://t.me"


def generate_duck_store_html(deals: List[Dict[str, Any]], pricing: Dict[str, Any]):
    """تولید وب‌سایت با معماری نهایی iOS و حفظ کامل محرمانگی قیمت‌گذاری"""
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

    collections_list = sorted(list(collections_map.values()), key=lambda x: x["name"])
    rare_count = sum(1 for d in deals if d.get("rarity"))

    # تعریف متغیرهای جیسون برای جلوگیری قطعی از NameError
    deals_json = json.dumps(deals, ensure_ascii=False)
    collections_json = json.dumps(collections_list, ensure_ascii=False)

    html_template = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>Duck Store</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-main: #060913;
            --ios-card: rgba(14, 20, 42, 0.72);
            --ios-card-hover: rgba(22, 32, 66, 0.85);
            --ios-border: rgba(255, 255, 255, 0.08);
            --neon-blue: #38bdf8;
            --neon-amber: #fbbf24;
            --neon-purple: #c084fc;
        }
        body {
            font-family: 'Vazirmatn', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-main);
            background-image: 
                radial-gradient(circle at 10% 10%, rgba(30, 58, 138, 0.35) 0%, transparent 45%),
                radial-gradient(circle at 90% 20%, rgba(124, 58, 237, 0.25) 0%, transparent 45%),
                radial-gradient(circle at 50% 95%, rgba(14, 165, 233, 0.2) 0%, transparent 50%);
            color: #f8fafc;
            -webkit-tap-highlight-color: transparent;
            -webkit-touch-callout: none;
        }
        .ios-card {
            background: var(--ios-card);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border: 1px solid var(--ios-border);
            border-radius: 26px;
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .ios-card:hover {
            background: var(--ios-card-hover);
            border-color: rgba(56, 189, 248, 0.3);
            box-shadow: 0 15px 35px -10px rgba(0, 0, 0, 0.6), 0 0 20px rgba(56, 189, 248, 0.12);
        }
        .ios-bottom-dock {
            background: rgba(8, 12, 26, 0.85);
            backdrop-filter: blur(30px);
            -webkit-backdrop-filter: blur(30px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 32px;
        }
        .nav-item.active {
            color: #38bdf8;
        }
        .nav-item.active .nav-icon {
            transform: translateY(-2px);
            filter: drop-shadow(0 0 8px rgba(56, 189, 248, 0.5));
        }
    </style>
</head>
<body class="min-h-screen pb-36 select-none">

    <!-- ۱. هدر اپلیکیشن به سبک iOS -->
    <header class="sticky top-0 z-30 bg-[#060913]/85 backdrop-blur-xl border-b border-white/5 px-4 sm:px-6 py-3.5">
        <div class="max-w-5xl mx-auto flex items-center justify-between">
            <div class="flex items-center gap-3">
                <div class="w-11 h-11 rounded-[16px] bg-gradient-to-tr from-cyan-400 via-blue-500 to-indigo-600 flex items-center justify-center text-xl shadow-lg shadow-cyan-500/20">
                    🦆
                </div>
                <div>
                    <h1 class="text-sm font-black text-white tracking-tight flex items-center gap-1.5">
                        <span>Duck Store</span>
                        <span class="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
                    </h1>
                    <p id="userGreetingText" class="text-[11px] text-slate-400 font-medium">خوش آمدید</p>
                </div>
            </div>

            <a id="headerSupportLink" href="https://t.me/Zanjani_a" onclick="openTgLink(this.href); return false;" class="px-3.5 py-1.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-slate-200 border border-white/10 text-xs font-bold transition flex items-center gap-2">
                <i class="fa-brands fa-telegram text-sky-400 text-sm"></i>
                <span>پشتیبانی</span>
            </a>
        </div>
    </header>

    <!-- ۲. محفظه صفحات اصلی (User Flow Tab Views) -->
    <main class="max-w-5xl mx-auto px-4 sm:px-6 mt-4">

        <!-- 🏠 تب ۱: داشبورد اصلی فروشگاه -->
        <section id="view-dashboard" class="space-y-4">
            <!-- بنر خوش‌آمدگویی VIP -->
            <div class="ios-card p-5 border-blue-500/20 bg-gradient-to-r from-blue-950/40 via-indigo-950/20 to-transparent flex items-center justify-between">
                <div>
                    <span class="text-[10px] font-bold text-cyan-400 uppercase tracking-wider">Duck Store VIP</span>
                    <h3 class="text-xs sm:text-sm font-black text-white mt-1">مرجع رسمی خدمات تلگرام</h3>
                    <p class="text-[11px] text-slate-400 mt-1">تحویل فوری استارز، اجاره گیفت‌های نایاب و پرمیوم قانونی</p>
                </div>
                <div class="w-12 h-12 rounded-2xl bg-cyan-400/10 border border-cyan-400/20 flex items-center justify-center text-2xl shadow-inner">
                    ⚡
                </div>
            </div>

            <!-- بنر اطلاعیه مناسبتی -->
            <div id="promoBanner" class="hidden ios-card p-4 border-amber-500/20 bg-amber-500/5 flex items-center justify-between">
                <div class="flex items-center gap-2.5">
                    <i class="fa-solid fa-bullhorn text-amber-400 text-sm"></i>
                    <span id="promoBannerText" class="text-xs font-bold text-amber-200"></span>
                </div>
                <button onclick="switchView('gifts')" class="text-xs font-black text-amber-400 hover:underline">مشاهده &larr;</button>
            </div>

            <!-- کارت‌های میانبر دسترسی سریع -->
            <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div onclick="switchView('gifts')" class="ios-card p-4 cursor-pointer flex flex-col justify-between space-y-2">
                    <span class="text-2xl">🎁</span>
                    <div>
                        <h4 class="text-xs font-black text-white">اجاره گیفت</h4>
                        <p class="text-[10px] text-slate-400 mt-0.5">__TOTAL_COUNT__ مورد فعال با تخفیف</p>
                    </div>
                </div>
                <div onclick="switchView('premium')" class="ios-card p-4 cursor-pointer flex flex-col justify-between space-y-2 border-purple-500/20">
                    <span class="text-2xl">👑</span>
                    <div>
                        <h4 class="text-xs font-black text-white">تلگرام پرمیوم</h4>
                        <p class="text-[10px] text-purple-300 mt-0.5">فعال‌سازی بدون پسورد اکانت</p>
                    </div>
                </div>
                <div onclick="switchView('stars')" class="ios-card p-4 cursor-pointer flex flex-col justify-between space-y-2 col-span-2 sm:col-span-1 border-amber-500/20">
                    <span class="text-2xl">⭐</span>
                    <div>
                        <h4 class="text-xs font-black text-white">استارز تلگرام</h4>
                        <p class="text-[10px] text-amber-300 mt-0.5">تحویل سریع با بهترین نرخ</p>
                    </div>
                </div>
            </div>

            <!-- پیش‌نمایش جدیدترین فرصت‌ها -->
            <div class="pt-2">
                <div class="flex items-center justify-between mb-3">
                    <h3 class="text-xs font-bold text-slate-300 flex items-center gap-1.5">
                        <i class="fa-solid fa-fire text-amber-400"></i>
                        <span>تازه‌ترین گیفت‌های کشف‌شده</span>
                    </h3>
                    <button onclick="switchView('gifts')" class="text-[11px] font-bold text-cyan-400 hover:underline">مشاهده همه &larr;</button>
                </div>
                <div id="homeRecentDeals" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"></div>
            </div>
        </section>

        <!-- 🎁 تب ۲: کاتالوگ کامل گیفت‌ها -->
        <section id="view-gifts" class="hidden space-y-4">
            <div class="ios-card p-3 sm:p-4 flex flex-col sm:flex-row items-center justify-between gap-3">
                <div class="relative w-full sm:w-72">
                    <i class="fa-solid fa-magnifying-glass absolute right-4 top-3.5 text-slate-500 text-xs"></i>
                    <input type="text" id="searchInput" placeholder="جستجوی نام یا شماره..." 
                           class="w-full bg-[#050711] border border-white/10 rounded-2xl pr-10 pl-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400 transition">
                </div>

                <div class="flex items-center gap-2 w-full sm:w-auto overflow-x-auto pb-1 sm:pb-0">
                    <button onclick="openModal()" class="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold bg-white/[0.04] text-slate-200 border border-white/10 whitespace-nowrap">
                        <i class="fa-solid fa-layer-group text-cyan-400 text-xs"></i>
                        <span id="selectedColText">کالکشن‌ها</span>
                        <i class="fa-solid fa-chevron-down text-[9px] text-slate-500 mr-0.5"></i>
                    </button>
                    <button onclick="filterType('all', this)" class="type-btn active px-3.5 py-2 rounded-xl text-xs font-black bg-cyan-400 text-slate-950 whitespace-nowrap">همه (__TOTAL_COUNT__)</button>
                    <button onclick="filterType('rare', this)" class="type-btn px-3.5 py-2 rounded-xl text-xs font-bold bg-white/[0.04] text-slate-300 border border-white/10 whitespace-nowrap">💎 کمیاب‌ها (__RARE_COUNT__)</button>
                    <button onclick="filterType('favs', this)" class="type-btn px-3.5 py-2 rounded-xl text-xs font-bold bg-white/[0.04] text-slate-300 border border-white/10 whitespace-nowrap flex items-center gap-1.5">
                        <i class="fa-solid fa-heart text-rose-500 text-xs"></i> (<span id="favCount">0</span>)
                    </button>
                </div>
            </div>

            <div id="dealsGrid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"></div>
        </section>

        <!-- 👑 تب ۳: پرمیوم تلگرام -->
        <section id="view-premium" class="hidden max-w-xl mx-auto space-y-4">
            <div class="ios-card p-6 space-y-4 border-purple-500/20">
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2.5">
                        <div class="w-10 h-10 rounded-2xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 text-lg">
                            👑
                        </div>
                        <div>
                            <h3 class="text-sm font-black text-white">اشتراک تلگرام پرمیوم</h3>
                            <p class="text-[11px] text-slate-400">فعال‌سازی قانونی بدون نیاز به ورود به اکانت</p>
                        </div>
                    </div>
                    <span class="text-[10px] px-2.5 py-1 rounded-full font-bold bg-purple-500/10 text-purple-300 border border-purple-500/20">تخفیف ویژه</span>
                </div>

                <div class="space-y-3" id="premiumOptionsList"></div>

                <div class="pt-4 border-t border-white/5 flex items-center justify-between">
                    <div>
                        <p class="text-[11px] text-slate-400">مبلغ قابل پرداخت:</p>
                        <p id="selectedPremiumFinalToman" class="text-base sm:text-lg font-black text-purple-400">0 تومان</p>
                    </div>
                    <button onclick="orderPremium()" class="py-3 px-6 rounded-2xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:opacity-90 text-white font-black text-xs transition shadow-lg shadow-purple-600/25 flex items-center gap-2">
                        <span>خرید پرمیوم</span>
                        <i class="fa-solid fa-arrow-left text-xs"></i>
                    </button>
                </div>
            </div>
        </section>

        <!-- ⭐ تب ۴: استارز تلگرام -->
        <section id="view-stars" class="hidden max-w-xl mx-auto space-y-4">
            <div class="ios-card p-6 space-y-3 border-amber-500/20">
                <h3 class="text-xs font-bold text-slate-300 flex items-center gap-2">
                    <span class="text-amber-400 text-sm">⭐</span>
                    <span>تعداد استارز دلخواه</span>
                </h3>
                <input type="number" id="customStarsInput" min="50" max="10000000" placeholder="حداقل ۵۰ استارز..." 
                       class="w-full bg-[#050711] border border-white/10 rounded-2xl px-4 py-3 text-sm text-white font-bold placeholder-slate-600 focus:outline-none focus:border-amber-400 transition">
                <div id="customStarsCalcBox" class="p-3 rounded-xl bg-white/[0.02] border border-white/5 flex items-center justify-between hidden">
                    <span class="text-xs text-slate-400">مبلغ نهایی:</span>
                    <span id="customStarsPrice" class="text-sm font-black text-amber-400">0 تومان</span>
                </div>
            </div>

            <div class="ios-card p-6 space-y-3">
                <h3 class="text-xs font-bold text-slate-400">پکیج‌های سریع استارز:</h3>
                <div id="starsPackagesList" class="space-y-2.5"></div>

                <div class="pt-4 border-t border-white/5 flex items-center justify-between">
                    <div>
                        <p class="text-[11px] text-slate-400">مبلغ قابل پرداخت:</p>
                        <p id="selectedStarsFinalToman" class="text-base sm:text-lg font-black text-amber-400">0 تومان</p>
                    </div>
                    <button onclick="orderStars()" class="py-3 px-6 rounded-2xl bg-gradient-to-r from-amber-400 to-yellow-500 text-slate-950 font-black text-xs transition shadow-lg shadow-amber-500/20 flex items-center gap-2">
                        <span>خرید استارز</span>
                        <i class="fa-solid fa-arrow-left text-xs"></i>
                    </button>
                </div>
            </div>
        </section>

        <!-- 🛍️ تب ۵: سبد خرید و فاکتور -->
        <section id="view-cart" class="hidden max-w-xl mx-auto space-y-4">
            <div class="ios-card p-6 space-y-4">
                <div class="flex items-center justify-between border-b border-white/5 pb-3">
                    <h3 class="text-sm font-black text-white flex items-center gap-2">
                        <span>🛍️ سبد اجاره گیفت</span>
                        <span id="cartViewCount" class="text-xs px-2 py-0.5 rounded-full bg-cyan-400/10 text-cyan-400">0 مورد</span>
                    </h3>
                    <button onclick="clearCart()" class="text-xs text-rose-400 hover:underline">خالی کردن سبد</button>
                </div>

                <div id="cartItemsList" class="space-y-2.5 max-h-60 overflow-y-auto"></div>

                <div class="flex items-center gap-2 bg-[#050711] p-1.5 rounded-2xl border border-white/5">
                    <input type="text" id="couponInput" placeholder="کد تخفیف (مثلاً DUCK)..." class="bg-transparent text-xs text-white px-3 py-1.5 flex-1 focus:outline-none uppercase font-bold placeholder-slate-600">
                    <button onclick="applyCoupon()" class="px-4 py-1.5 bg-white/10 hover:bg-white/20 text-white text-xs font-bold rounded-xl transition">اعمال</button>
                </div>

                <div class="pt-2 border-t border-white/5 flex items-center justify-between">
                    <div>
                        <div class="flex items-center gap-2">
                            <p class="text-[11px] text-slate-400">مبلغ قابل پرداخت:</p>
                            <span id="discountTag" class="hidden text-[9px] px-2 py-0.5 rounded font-black bg-emerald-500/20 text-emerald-400">تخفیف فعال</span>
                        </div>
                        <p id="cartTotalPrice" class="text-lg font-black text-cyan-400">0 تومان</p>
                    </div>
                    <button onclick="checkoutCart()" class="py-3 px-6 rounded-2xl bg-gradient-to-r from-blue-500 to-cyan-400 text-slate-950 font-black text-xs transition shadow-lg shadow-cyan-400/25 flex items-center gap-2">
                        <span>ارسال سفارش به تلگرام</span>
                        <i class="fa-solid fa-paper-plane text-xs"></i>
                    </button>
                </div>
            </div>
        </section>

    </main>

    <!-- ۳. نوار ناوبری شناور پایینی آیفون (Bottom Navigation Dock) -->
    <nav class="fixed bottom-3 inset-x-4 max-w-md mx-auto z-40 ios-bottom-dock px-3 py-2 flex items-center justify-around shadow-2xl">
        <button onclick="switchView('dashboard')" id="nav-dashboard" class="nav-item active flex flex-col items-center gap-1 text-[10px] font-bold text-slate-400 transition">
            <i class="fa-solid fa-house nav-icon text-sm"></i>
            <span>خانه</span>
        </button>
        <button onclick="switchView('gifts')" id="nav-gifts" class="nav-item flex flex-col items-center gap-1 text-[10px] font-bold text-slate-400 transition">
            <i class="fa-solid fa-gift nav-icon text-sm"></i>
            <span>گیفت‌ها</span>
        </button>
        <button onclick="switchView('premium')" id="nav-premium" class="nav-item flex flex-col items-center gap-1 text-[10px] font-bold text-slate-400 transition">
            <i class="fa-solid fa-crown nav-icon text-sm"></i>
            <span>پرمیوم</span>
        </button>
        <button onclick="switchView('stars')" id="nav-stars" class="nav-item flex flex-col items-center gap-1 text-[10px] font-bold text-slate-400 transition">
            <i class="fa-solid fa-star nav-icon text-sm"></i>
            <span>استارز</span>
        </button>
        <button onclick="switchView('cart')" id="nav-cart" class="nav-item flex flex-col items-center gap-1 text-[10px] font-bold text-slate-400 transition relative">
            <i class="fa-solid fa-cart-shopping nav-icon text-sm"></i>
            <span>سبد</span>
            <span id="dockCartBadge" class="hidden absolute -top-1 -right-1 w-4 h-4 rounded-full bg-cyan-400 text-slate-950 font-black text-[9px] flex items-center justify-center">0</span>
        </button>
    </nav>

    <!-- مودال انتخاب کالکشن -->
    <div id="collectionModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md hidden">
        <div class="modal-bg w-full max-w-md rounded-[28px] overflow-hidden shadow-2xl flex flex-col max-h-[80vh]">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-white/10">
                <button onclick="closeModal()" class="w-7 h-7 rounded-full bg-white/5 text-slate-400 hover:text-white flex items-center justify-center transition">
                    <i class="fa-solid fa-xmark text-xs"></i>
                </button>
                <h3 class="text-xs font-black text-white">کالکشن‌های گیفت</h3>
                <div class="w-7"></div>
            </div>
            <div class="p-3 border-b border-white/10 flex items-center justify-between text-xs">
                <button onclick="selectAllCollections()" class="text-cyan-400 font-bold">انتخاب همه</button>
                <button onclick="clearCollectionSelection()" class="text-slate-400 hover:text-rose-400">لغو همه</button>
            </div>
            <div id="modalCollectionsList" class="p-3 space-y-1.5 overflow-y-auto flex-1"></div>
            <div class="p-3 border-t border-white/10 bg-[#060913]">
                <button onclick="applyCollectionModal()" class="w-full py-2.5 bg-cyan-400 text-slate-950 text-xs font-black rounded-xl transition">
                    اعمال فیلتر (<span id="modalSelectedCountBadge">همه</span>)
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
                document.getElementById('userGreetingText').innerText = `${name} 👋`;
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
            window.location.href = cleanUrl;
        }

        const DEALS = __DEALS_JSON__;
        const COLLECTIONS = __COLLECTIONS_JSON__;
        const WORKER_URL = "__WORKER_URL__";
        const LIVE_PRICING = __LIVE_PRICING_JSON__;

        const DEFAULT_SETTINGS = {
            ratePerStar: 1450,
            prem3: LIVE_PRICING.prem3,
            prem6: LIVE_PRICING.prem6,
            prem12: LIVE_PRICING.prem12,
            giftMonthlyPrice: 160000,
            adminTg: 'Zanjani_a',
            announcementText: 'تخفیف ویژه سفارشات فعال شد',
            announcementActive: true,
            couponCode: 'DUCK',
            couponPercent: 10,
            tabGiftsActive: true,
            tabStarsActive: true,
            tabPremiumActive: true
        };

        let SETTINGS = { ...DEFAULT_SETTINGS };
        let currentView = 'dashboard';
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

        function switchView(viewName) {
            triggerHaptic('selection');
            currentView = viewName;
            ['dashboard', 'gifts', 'premium', 'stars', 'cart'].forEach(v => {
                document.getElementById(`view-${v}`).classList.add('hidden');
                const nav = document.getElementById(`nav-${v}`);
                if (nav) nav.classList.remove('active');
            });

            document.getElementById(`view-${viewName}`).classList.remove('hidden');
            const activeNav = document.getElementById(`nav-${viewName}`);
            if (activeNav) activeNav.classList.add('active');

            if (viewName === 'cart') renderCartView();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }

        async function fetchCloudSettings() {
            try {
                const res = await fetch(`${WORKER_URL}/api/settings`);
                if (res.ok) {
                    const parsed = await res.json();
                    if (parsed && typeof parsed === 'object') {
                        SETTINGS = { ...DEFAULT_SETTINGS, ...parsed, prem3: LIVE_PRICING.prem3, prem6: LIVE_PRICING.prem6, prem12: LIVE_PRICING.prem12 };
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

            renderCards(getFilteredDeals());
            renderHomeDeals();
            renderStarsPackages();
            renderPremiumOptions();
            updateCartBadges();
        }

        function renderHomeDeals() {
            const container = document.getElementById('homeRecentDeals');
            if (!container) return;
            const topDeals = DEALS.slice(0, 6);
            container.innerHTML = topDeals.map(d => `
                <div class="ios-card p-3.5 flex items-center justify-between">
                    <div class="flex items-center gap-3">
                        <img src="${d.image_url}" class="w-12 h-12 rounded-xl object-contain bg-black/40 p-1" onerror="this.src='https://marketapp.org/favicon.ico'">
                        <div>
                            <h4 class="text-xs font-bold text-white">${d.name}</h4>
                            <span class="text-[10px] text-cyan-400 font-bold">${SETTINGS.giftMonthlyPrice.toLocaleString('en-US')} ت/ماه</span>
                        </div>
                    </div>
                    <button onclick="toggleCart(${JSON.stringify(d).replace(/"/g, '&quot;')})" class="px-3 py-1.5 rounded-xl bg-cyan-400/10 text-cyan-300 border border-cyan-400/20 text-xs font-bold hover:bg-cyan-400 hover:text-slate-950 transition">
                        + سبد
                    </button>
                </div>
            `).join('');
        }

        function renderStarsPackages() {
            const container = document.getElementById('starsPackagesList');
            container.innerHTML = STARS_PACKAGES.map(qty => {
                const totalToman = (qty * SETTINGS.ratePerStar).toLocaleString('en-US');
                const isSelected = selectedStarsCount === qty;
                return `
                <div onclick="selectStarsPackage(${qty})" class="p-3.5 rounded-2xl bg-white/[0.02] border ${isSelected ? 'border-amber-400 bg-amber-400/10' : 'border-white/5'} flex items-center justify-between cursor-pointer transition">
                    <span class="text-xs font-bold text-white">${qty} Stars</span>
                    <span class="text-xs font-black text-amber-400">${totalToman} ت</span>
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
                "سلام، درخواست خرید استارز تلگرام دارم:" + nl + nl +
                buyerInfo + nl + nl +
                "تعداد استارز: " + selectedStarsCount + " Stars" + nl +
                "مبلغ قابل پرداخت: " + total + " تومان"
            );
            openTgLink("https://t.me/" + adminUser + "?text=" + msg);
        }

        function renderPremiumOptions() {
            const container = document.getElementById('premiumOptionsList');
            const options = [
                { months: 12, label: '۱۲ ماهه (1 Year)', discount: '-52%', price: LIVE_PRICING.prem12 },
                { months: 6, label: '۶ ماهه (6 Months)', discount: '-47%', price: LIVE_PRICING.prem6 },
                { months: 3, label: '۳ ماهه (3 Months)', discount: '-20%', price: LIVE_PRICING.prem3 }
            ];

            container.innerHTML = options.map(opt => {
                const isSelected = selectedPremiumMonths === opt.months;
                const totalToman = opt.price.toLocaleString('en-US');
                return `
                <div onclick="selectPremiumPlan(${opt.months})" class="p-4 rounded-2xl bg-white/[0.02] border ${isSelected ? 'border-purple-400 bg-purple-500/10' : 'border-white/5'} flex items-center justify-between cursor-pointer transition">
                    <div>
                        <span class="text-xs font-bold text-white">${opt.label}</span>
                        <span class="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 font-bold mr-2">${opt.discount}</span>
                    </div>
                    <span class="text-xs font-black text-purple-300">${totalToman} ت</span>
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
            let price = LIVE_PRICING.prem12;
            if (selectedPremiumMonths === 6) price = LIVE_PRICING.prem6;
            if (selectedPremiumMonths === 3) price = LIVE_PRICING.prem3;
            document.getElementById('selectedPremiumFinalToman').innerText = `${price.toLocaleString('en-US')} تومان`;
        }

        function orderPremium() {
            triggerHaptic('heavy');
            const adminUser = (SETTINGS.adminTg || 'Zanjani_a').replace('@', '').trim();
            let planName = '1 ساله';
            let price = LIVE_PRICING.prem12;
            if (selectedPremiumMonths === 6) { planName = '6 ماهه'; price = LIVE_PRICING.prem6; }
            if (selectedPremiumMonths === 3) { planName = '3 ماهه'; price = LIVE_PRICING.prem3; }
            const total = price.toLocaleString('en-US');
            const buyerInfo = getBuyerDetailsText();
            const nl = String.fromCharCode(10);
            const msg = encodeURIComponent(
                "سلام، درخواست خرید اشتراک تلگرام پرمیوم دارم:" + nl + nl +
                buyerInfo + nl + nl +
                "نوع اشتراک: " + planName + nl +
                "مبلغ قابل پرداخت: " + total + " تومان"
            );
            openTgLink("https://t.me/" + adminUser + "?text=" + msg);
        }

        function toggleCart(item) {
            triggerHaptic('selection');
            const idx = cart.findIndex(c => c.name === item.name);
            if (idx > -1) cart.splice(idx, 1);
            else cart.push(item);
            localStorage.setItem('duck_cart', JSON.stringify(cart));
            updateCartBadges();
            renderCards(getFilteredDeals());
            if (currentView === 'cart') renderCartView();
        }

        function updateCartBadges() {
            const count = cart.length;
            const badge = document.getElementById('dockCartBadge');
            if (badge) {
                badge.innerText = count;
                if (count > 0) badge.classList.remove('hidden');
                else badge.classList.add('hidden');
            }
        }

        function renderCartView() {
            const container = document.getElementById('cartItemsList');
            document.getElementById('cartViewCount').innerText = `${cart.length} مورد`;
            if (cart.length === 0) {
                container.innerHTML = '<p class="text-xs text-slate-500 py-6 text-center font-bold">سبد خرید شما خالی است.</p>';
            } else {
                container.innerHTML = cart.map((item, i) => `
                    <div class="p-2.5 rounded-xl bg-white/[0.03] border border-white/5 flex items-center justify-between">
                        <span class="text-xs font-bold text-slate-200">${i + 1}. ${item.name}</span>
                        <button onclick="toggleCart(${JSON.stringify(item).replace(/"/g, '&quot;')})" class="text-rose-400 text-xs px-2 py-1">
                            <i class="fa-solid fa-xmark"></i>
                        </button>
                    </div>
                `).join('');
            }

            const rawTotal = cart.length * SETTINGS.giftMonthlyPrice;
            const finalTotal = appliedDiscountPercent > 0 ? Math.round(rawTotal * (1 - appliedDiscountPercent / 100)) : rawTotal;
            document.getElementById('cartTotalPrice').innerText = `${finalTotal.toLocaleString('en-US')} تومان`;
        }

        function applyCoupon() {
            triggerHaptic('medium');
            const input = document.getElementById('couponInput').value.trim().toUpperCase();
            if (SETTINGS.couponCode && input === SETTINGS.couponCode.toUpperCase()) {
                appliedCouponCode = input;
                appliedDiscountPercent = SETTINGS.couponPercent || 10;
                document.getElementById('discountTag').classList.remove('hidden');
                alert(`کد تخفیف ${appliedDiscountPercent}٪ اعمال شد`);
            } else {
                alert('کد تخفیف نامعتبر است');
            }
            renderCartView();
        }

        function clearCart() {
            triggerHaptic('light');
            cart = [];
            appliedCouponCode = null;
            appliedDiscountPercent = 0;
            localStorage.setItem('duck_cart', JSON.stringify(cart));
            updateCartBadges();
            renderCartView();
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
            if (cart.length === 0) return alert('سبد خرید شما خالی است!');
            const adminUser = (SETTINGS.adminTg || 'Zanjani_a').replace('@', '').trim();
            const rawTotal = cart.length * SETTINGS.giftMonthlyPrice;
            const finalTotal = appliedDiscountPercent > 0 ? Math.round(rawTotal * (1 - appliedDiscountPercent / 100)) : rawTotal;
            const buyer = getBuyerDetailsText();
            const nl = String.fromCharCode(10);
            const itemsList = cart.map((c, i) => `${i + 1}. 🎁 ${c.name} (${c.tg_link})`).join(nl);
            const coupon = appliedCouponCode ? (nl + `کد تخفیف: ${appliedCouponCode} (${appliedDiscountPercent}%)`) : '';

            const msg = encodeURIComponent(
                "سلام، درخواست اجاره گیفت دارم:" + nl + nl +
                buyer + nl + nl +
                "اقلام سفارش (" + cart.length + " عدد):" + nl +
                itemsList + nl + nl +
                "مبلغ نهایی: " + finalTotal.toLocaleString('en-US') + " تومان / ماه" +
                coupon
            );
            openTgLink("https://t.me/" + adminUser + "?text=" + msg);
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
                const isInCart = cart.some(c => c.name === deal.name);

                return `
                <div class="ios-card overflow-hidden flex flex-col justify-between ${isInCart ? 'border-cyan-400 bg-cyan-950/20' : ''}">
                    <div>
                        <div class="relative w-full h-44 bg-gradient-to-b from-white/[0.04] to-transparent flex items-center justify-center overflow-hidden border-b border-white/5">
                            ${rarityBadge}
                            <img src="${deal.image_url}" alt="${deal.name}" class="w-28 h-28 object-contain drop-shadow-[0_10px_20px_rgba(0,0,0,0.8)]" onerror="this.src='https://marketapp.org/favicon.ico'">
                        </div>
                        <div class="p-3.5 space-y-2">
                            <h3 class="font-bold text-xs text-white truncate text-center">${deal.name}</h3>
                            <div class="flex justify-between items-center text-[11px] bg-black/20 p-2 rounded-xl border border-white/5">
                                <span class="text-slate-400">اجاره ماهانه:</span>
                                <span class="font-black text-cyan-300">${giftPriceFormatted} ت</span>
                            </div>
                        </div>
                    </div>
                    <div class="p-3.5 pt-0 grid grid-cols-2 gap-2">
                        <a href="${deal.tg_link}" target="_blank" onclick="triggerHaptic('light')" class="py-2 rounded-xl bg-white/[0.04] text-slate-300 text-xs font-bold text-center border border-white/10">مشاهده</a>
                        <button onclick='toggleCart(${JSON.stringify(deal)})' class="py-2 rounded-xl ${isInCart ? 'bg-cyan-400 text-slate-950 font-black' : 'bg-white text-slate-950 font-bold'} text-xs text-center transition">
                            ${isInCart ? 'انتخاب شد' : 'اجاره'}
                        </button>
                    </div>
                </div>
                `;
            }).join('');
        }

        function updateFavCount() {
            document.getElementById('favCount').innerText = favorites.length;
        }

        function openModal() {
            triggerHaptic('light');
            tempSelectedCollections = new Set(selectedCollections);
            document.getElementById('collectionModal').classList.remove('hidden');
            renderModalCollections();
        }
        function closeModal() {
            triggerHaptic('light');
            document.getElementById('collectionModal').classList.add('hidden');
        }
        function renderModalCollections() {
            const container = document.getElementById('modalCollectionsList');
            container.innerHTML = COLLECTIONS.map(col => {
                const isSelected = tempSelectedCollections.has(col.name);
                return `
                <div onclick="toggleModalCollection('${col.name}')" class="p-2.5 rounded-xl border ${isSelected ? 'border-cyan-400 bg-cyan-950/20' : 'border-white/5'} flex items-center justify-between cursor-pointer">
                    <span class="text-xs font-bold text-slate-200">${col.name}</span>
                    <span class="text-[10px] text-slate-400">${col.count}</span>
                </div>
                `;
            }).join('');
        }
        function toggleModalCollection(name) {
            triggerHaptic('selection');
            if (tempSelectedCollections.has(name)) tempSelectedCollections.delete(name);
            else tempSelectedCollections.add(name);
            renderModalCollections();
        }
        function selectAllCollections() {
            COLLECTIONS.forEach(c => tempSelectedCollections.add(c.name));
            renderModalCollections();
        }
        function clearCollectionSelection() {
            tempSelectedCollections.clear();
            renderModalCollections();
        }
        function applyCollectionModal() {
            selectedCollections = new Set(tempSelectedCollections);
            document.getElementById('selectedColText').innerText = selectedCollections.size === 0 ? 'کالکشن‌ها' : `${selectedCollections.size} کالکشن`;
            closeModal();
            applyFilters();
        }

        function filterType(type, btn) {
            triggerHaptic('selection');
            selectedType = type;
            document.querySelectorAll('.type-btn').forEach(b => {
                b.classList.remove('bg-cyan-400', 'text-slate-950');
                b.classList.add('bg-white/[0.04]', 'text-slate-300');
            });
            if (btn) {
                btn.classList.remove('bg-white/[0.04]', 'text-slate-300');
                btn.classList.add('bg-cyan-400', 'text-slate-950');
            }
            applyFilters();
        }

        function getFilteredDeals() {
            const query = (document.getElementById('searchInput')?.value || '').trim().toLowerCase();
            return DEALS.filter(d => {
                const match = d.name.toLowerCase().includes(query) || d.number.includes(query) || d.gift_title.toLowerCase().includes(query);
                if (!match) return false;
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
    </script>
</body>
</html>"""

    html_content = (
        html_template.replace("__TIMESTAMP__", timestamp)
        .replace("__TOTAL_COUNT__", str(len(deals)))
        .replace("__RARE_COUNT__", str(rare_count))
        .replace("__DEALS_JSON__", deals_json)
        .replace("__COLLECTIONS_JSON__", collections_json)
        .replace("__LIVE_PRICING_JSON__", json.dumps(pricing))
        .replace("__WORKER_URL__", CONFIG["WORKER_URL"])
    )

    with open(CONFIG["EXPORT_HTML"], "w", encoding="utf-8") as f:
        f.write(html_content)

    with open(CONFIG["EXPORT_JSON"], "w", encoding="utf-8") as f:
        json.dump(deals, f, ensure_ascii=False, indent=2)


def send_telegram_package(deals: List[Dict[str, Any]], pricing: Dict[str, Any]):
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

    rare_count = sum(1 for d in deals if d["rarity"])
    full_text = (
        f"🦆 <b>گزارش جدید فروشگاه Duck Store</b>\n"
        f"📅 <i>{timestamp}</i>\n\n"
        f"🌐 <b>لینک ورود به مینی‌اپ:</b>\n👉 <a href='{pages_url}'>{pages_url}</a>\n\n"
        f"📊 <b>نرخ‌های محاسبه‌شده پرمیوم:</b>\n"
        f"🔹 ۳ ماهه: <code>{pricing['prem3']:,}</code> تومان\n"
        f"🔹 ۶ ماهه: <code>{pricing['prem6']:,}</code> تومان\n"
        f"🔹 ۱ ساله: <code>{pricing['prem12']:,}</code> تومان\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 موجودی کل گیفت‌ها: {len(deals)} مورد (کمیاب: {rare_count})\n"
    )

    send_chunks_to_telegram(full_text, token, chat_id)
    send_telegram_csv_attachment(
        CONFIG["EXPORT_CSV"],
        token,
        chat_id,
        f"📊 فایل اکسل ۲۰۰ گیفت Duck Store ({timestamp})",
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


def send_telegram_csv_attachment(file_path: str, token: str, chat_id: str, caption: str):
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

    launch_args = [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-accelerated-2d-canvas",
        "--no-first-run",
        "--no-zygote",
    ]

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True, args=launch_args)
        except Exception:
            browser = await p.chromium.launch(headless=True, channel="chrome", args=launch_args)

        page = await browser.new_page()

        # ۱. محاسبه زنده قیمت پرمیوم در بک‌اند
        live_pricing = await calculate_live_pricing(page)

        # ۲. اسکرپ ۲۰۰ گیفت از مارکت‌اپ
        print("🌐 بارگذاری اولیه مارکت...")
        await page.goto(CONFIG["TARGET_URL"], wait_until="domcontentloaded", timeout=60000)
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
                if not href: continue

                full_link = href if href.startswith("http") else f"{CONFIG['BASE_DOMAIN']}{href if href.startswith('/') else '/' + href}"
                if full_link in seen_links: continue

                text = c["text"]
                if not text.strip(): continue

                discount_match = re.search(r"-(\d+(?:\.\d+)?)%", text)
                if discount_match:
                    discount_val = float(discount_match.group(1))
                    if discount_val >= CONFIG["MIN_DISCOUNT_PERCENT"]:
                        num_match = re.search(r"#(\d+)", text)
                        item_num = num_match.group(1) if num_match else "0"
                        days_match = re.search(r"Days:\s*(\d+\s*–\s*\d+)", text)
                        days_range = days_match.group(1) if days_match else "1 – 180"

                        lines = [l.strip() for l in text.split("\n") if l.strip()]
                        name_candidates = [
                            l for l in lines
                            if not l.startswith("Days:")
                            and not l.startswith("-")
                            and not l.startswith("#")
                            and l.lower() not in ["per day", "min. price"]
                            and not re.match(r"^\d+(\.\d+)?$", l)
                        ]

                        gift_name = name_candidates[0] if name_candidates else "NFT Gift"
                        deal = {
                            "name": f"{gift_name} #{item_num}",
                            "gift_title": gift_name,
                            "number": item_num,
                            "discount": f"-{discount_val}%",
                            "discount_num": discount_val,
                            "price_per_day": "0.01",
                            "days_range": days_range,
                            "tg_link": generate_tg_nft_link(gift_name, item_num),
                            "market_link": full_link,
                            "image_url": c["img"] if c["img"] else "https://marketapp.org/favicon.ico",
                            "rarity": detect_rarity_badge(item_num),
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
            await page.wait_for_timeout(350)

        await browser.close()

        # سورت بر اساس جدیدترین‌ها
        sorted_deals = list(reversed(deals_found))

        # ساخت صفحه با قیمت‌های زنده و دیزاین جدید
        generate_duck_store_html(sorted_deals, live_pricing)

        with open(CONFIG["EXPORT_CSV"], "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["ردیف", "کالکشن", "نام گیفت", "شماره", "تخفیف", "کمیابی", "لینک تلگرام", "لینک MarketApp"])
            for idx, d in enumerate(sorted_deals, 1):
                writer.writerow([idx, d["gift_title"], d["name"], d["number"], d["discount"], d["rarity"] or "معمولی", d["tg_link"], d["market_link"]])

        print("\n⚡ فروشگاه Duck Store با موفقیت بدون ارور بیلد شد!")
        send_telegram_package(sorted_deals, live_pricing)


if __name__ == "__main__":
    asyncio.run(main())
