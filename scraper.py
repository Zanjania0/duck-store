import asyncio
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
    "MIN_DISCOUNT_PERCENT": 50.0,
    "TARGET_DEALS_COUNT": 200,
    "MAX_SCROLL_ATTEMPTS": 80,
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


def detect_rarity_badge(number_str: str) -> str:
    try:
        num = int(re.sub(r"\D", "", str(number_str)))
    except ValueError:
        return ""
    s = str(num)
    if num < 100:
        return "👑 زیر 100"
    if num < 1000:
        return "💎 زیر 1000"
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
        return "🔁 متقارن"
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


def generate_duck_store_html(deals: List[Dict[str, Any]]):
    """تولید وب‌اپلیکیشن پیشرفته Duck Store با پروفایل و خدمات سفارشی"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    collections_map = {}
    for d in deals:
        c_name = d.get("gift_title", "NFT Gift")
        if c_name not in collections_map:
            collections_map[c_name] = {
                "name": c_name,
                "image": d.get("image_url", "https://marketapp.org/favicon.ico"),
                "count": 0,
            }
        collections_map[c_name]["count"] += 1

    collections_list = sorted(
        list(collections_map.values()), key=lambda x: str(x["name"])
    )
    rare_count = sum(1 for d in deals if d.get("rarity"))

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
            --bg-deep: #07080f;
            --glass-card: rgba(13, 14, 26, 0.75);
            --glass-border: rgba(255, 255, 255, 0.08);
            --accent-gold: #fbbf24;
            --accent-purple: #8b5cf6;
            --accent-cyan: #38bdf8;
        }
        body {
            font-family: 'Vazirmatn', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-deep);
            background-image: 
                radial-gradient(circle at 10% 10%, rgba(30, 58, 138, 0.3) 0%, transparent 45%),
                radial-gradient(circle at 90% 15%, rgba(124, 58, 237, 0.25) 0%, transparent 45%),
                radial-gradient(circle at 50% 90%, rgba(14, 165, 233, 0.18) 0%, transparent 50%);
            color: #f8fafc;
            -webkit-tap-highlight-color: transparent;
            -webkit-touch-callout: none;
        }
        .app-card {
            background: var(--glass-card);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid var(--glass-border);
            border-radius: 24px;
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .app-card:hover {
            border-color: rgba(251, 191, 36, 0.4);
            box-shadow: 0 15px 35px -10px rgba(0, 0, 0, 0.7), 0 0 20px rgba(139, 92, 246, 0.15);
        }
        .dock-bar {
            background: rgba(10, 12, 22, 0.88);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 30px;
        }
        .nav-btn.active {
            color: var(--accent-gold);
        }
        .nav-btn.active .nav-icon {
            transform: translateY(-2px);
            filter: drop-shadow(0 0 8px rgba(251, 191, 36, 0.5));
        }
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.15); border-radius: 9999px; }
    </style>
</head>
<body class="min-h-screen pb-32 select-none">

    <!-- هدر اپلیکیشن -->
    <header class="sticky top-0 z-30 bg-[#07080f]/85 backdrop-blur-xl border-b border-white/5 px-4 sm:px-6 py-3.5">
        <div class="max-w-5xl mx-auto flex items-center justify-between">
            <div class="flex items-center gap-3">
                <div class="w-11 h-11 rounded-[16px] bg-gradient-to-tr from-amber-400 via-amber-500 to-purple-600 flex items-center justify-center text-xl shadow-lg shadow-amber-500/20">
                    🦆
                </div>
                <div>
                    <h1 class="text-sm font-black text-white tracking-tight flex items-center gap-1.5">
                        <span>Duck Store</span>
                        <span class="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
                    </h1>
                    <p id="headerGreeting" class="text-[11px] text-amber-300/80 font-medium">مرجع خدمات تلگرام</p>
                </div>
            </div>

            <a id="headerSupportLink" href="https://t.me/Zanjani_a" class="px-3.5 py-1.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-slate-200 border border-white/10 text-xs font-bold transition flex items-center gap-2">
                <i class="fa-brands fa-telegram text-sky-400 text-sm"></i>
                <span>پشتیبانی</span>
            </a>
        </div>
    </header>

    <!-- محفظه صفحات اصلی (Views) -->
    <main class="max-w-5xl mx-auto px-4 sm:px-6 mt-4">

        <!-- 🏠 ۱. تب خانه (ویترین و پیشنهادات) -->
        <section id="view-home" class="space-y-4">
            <!-- بنر خوش‌آمدگویی -->
            <div class="app-card p-5 border-amber-500/20 bg-gradient-to-r from-amber-500/10 via-purple-500/5 to-transparent flex items-center justify-between">
                <div>
                    <span class="text-[10px] font-black text-amber-400 uppercase tracking-wider">مرکز تخصصی تلگرام</span>
                    <h3 class="text-xs sm:text-sm font-black text-white mt-1">خدمات مستقیم و تحویل آنی</h3>
                    <p class="text-[11px] text-slate-400 mt-0.5">اجاره گیفت، پرمیوم، استارز و بوست کانال</p>
                </div>
                <div class="w-12 h-12 rounded-2xl bg-amber-400/10 border border-amber-400/20 flex items-center justify-center text-2xl shadow-inner">
                    ⚡
                </div>
            </div>

            <!-- بنر اطلاعیه ادمین -->
            <div id="promoBanner" class="hidden app-card p-3.5 border-purple-500/20 bg-purple-500/5 flex items-center justify-between">
                <div class="flex items-center gap-2">
                    <i class="fa-solid fa-bullhorn text-purple-400 text-xs"></i>
                    <span id="promoBannerText" class="text-xs font-bold text-purple-200"></span>
                </div>
                <button id="promoActionBtn" class="text-xs font-black text-amber-400 hover:underline">دیدن &larr;</button>
            </div>

            <!-- کارت‌های میانبر به سایر بخش‌ها -->
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div id="shortcutGifts" class="app-card p-4 cursor-pointer flex flex-col justify-between space-y-2">
                    <span class="text-2xl">🎁</span>
                    <div>
                        <h4 class="text-xs font-black text-white">اجاره گیفت</h4>
                        <p class="text-[10px] text-slate-400 mt-0.5">__TOTAL_COUNT__ مورد فعال</p>
                    </div>
                </div>
                <div id="shortcutPremium" class="app-card p-4 cursor-pointer flex flex-col justify-between space-y-2 border-purple-500/20">
                    <span class="text-2xl">👑</span>
                    <div>
                        <h4 class="text-xs font-black text-white">تلگرام پرمیوم</h4>
                        <p class="text-[10px] text-purple-300 mt-0.5">اشتراک قانونی</p>
                    </div>
                </div>
                <div id="shortcutStars" class="app-card p-4 cursor-pointer flex flex-col justify-between space-y-2 border-amber-500/20">
                    <span class="text-2xl">⭐</span>
                    <div>
                        <h4 class="text-xs font-black text-white">استارز تلگرام</h4>
                        <p class="text-[10px] text-amber-300 mt-0.5">شارژ سریع</p>
                    </div>
                </div>
                <div id="shortcutServices" class="app-card p-4 cursor-pointer flex flex-col justify-between space-y-2 border-cyan-500/20">
                    <span class="text-2xl">🚀</span>
                    <div>
                        <h4 class="text-xs font-black text-white">بوست و خدمات</h4>
                        <p class="text-[10px] text-cyan-300 mt-0.5">خدمات سفارشی</p>
                    </div>
                </div>
            </div>

            <!-- پیش‌نمایش تازه‌ترین‌ها -->
            <div class="pt-2">
                <div class="flex items-center justify-between mb-3">
                    <h3 class="text-xs font-bold text-slate-300 flex items-center gap-1.5">
                        <i class="fa-solid fa-fire text-amber-400"></i>
                        <span>تازه‌ترین گیفت‌های ویژه</span>
                    </h3>
                    <button id="seeAllDealsBtn" class="text-[11px] font-bold text-amber-400 hover:underline">مشاهده همه &larr;</button>
                </div>
                <div id="homeRecentDeals" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5"></div>
            </div>
        </section>

        <!-- 🎁 ۲. تب گیفت‌ها (فروشگاه اصلی) -->
        <section id="view-gifts" class="hidden space-y-4">
            <!-- نوار فیلتر و جستجو -->
            <div class="app-card p-3 sm:p-4 flex flex-col sm:flex-row items-center justify-between gap-3">
                <div class="relative w-full sm:w-72">
                    <i class="fa-solid fa-magnifying-glass absolute right-4 top-3 text-slate-500 text-xs"></i>
                    <input type="text" id="searchInput" placeholder="جستجوی نام یا شماره گیفت..." 
                           class="w-full bg-[#050711] border border-white/10 rounded-2xl pr-10 pl-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-400 transition">
                </div>

                <div class="flex items-center gap-2 w-full sm:w-auto overflow-x-auto pb-1 sm:pb-0">
                    <button id="openColModalBtn" class="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold bg-white/[0.04] text-slate-200 border border-white/10 whitespace-nowrap">
                        <i class="fa-solid fa-layer-group text-amber-400 text-xs"></i>
                        <span id="selectedColText">کالکشن‌ها</span>
                        <i class="fa-solid fa-chevron-down text-[9px] text-slate-500 mr-0.5"></i>
                    </button>
                    <button id="filterBtnAll" class="type-btn active px-3.5 py-2 rounded-xl text-xs font-black bg-amber-400 text-slate-950 whitespace-nowrap shadow-md">همه (__TOTAL_COUNT__)</button>
                    <button id="filterBtnRare" class="type-btn px-3.5 py-2 rounded-xl text-xs font-bold bg-white/[0.04] text-slate-300 border border-white/10 whitespace-nowrap">💎 کمیاب‌ها (__RARE_COUNT__)</button>
                    <button id="filterBtnFavs" class="type-btn px-3.5 py-2 rounded-xl text-xs font-bold bg-white/[0.04] text-slate-300 border border-white/10 whitespace-nowrap flex items-center gap-1.5">
                        <i class="fa-solid fa-heart text-rose-500 text-xs"></i> (<span id="favCount">0</span>)
                    </button>
                </div>
            </div>

            <!-- گرید کارت‌های گیفت -->
            <div id="dealsGrid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 min-h-[300px]"></div>
        </section>

        <!-- ⚡ ۳. تب خدمات تلگرام (پرمیوم، استارز و خدمات پویا/بوست) -->
        <section id="view-services" class="hidden max-w-xl mx-auto space-y-4">
            <!-- زیرتب‌های خدمات -->
            <div class="flex items-center gap-1.5 bg-[#0e101f] p-1.5 rounded-2xl border border-white/10 overflow-x-auto">
                <button id="subtabBtn-prem" class="subtab-btn active flex-1 py-2 px-3 rounded-xl text-xs font-black bg-amber-400 text-slate-950 whitespace-nowrap transition">👑 تلگرام پرمیوم</button>
                <button id="subtabBtn-stars" class="subtab-btn flex-1 py-2 px-3 rounded-xl text-xs font-bold text-slate-400 hover:text-white whitespace-nowrap transition">⭐ استارز</button>
                <button id="subtabBtn-custom" class="subtab-btn flex-1 py-2 px-3 rounded-xl text-xs font-bold text-slate-400 hover:text-white whitespace-nowrap transition">🚀 بوست و خدمات</button>
            </div>

            <!-- بخش ۱: پرمیوم -->
            <div id="serviceSec-prem" class="app-card p-5 space-y-4 border-purple-500/20">
                <div class="flex items-center justify-between">
                    <div>
                        <h3 class="text-sm font-black text-white">اشتراک تلگرام پرمیوم</h3>
                        <p class="text-[11px] text-slate-400 mt-0.5">بدون نیاز به پسورد اکانت، فعال‌سازی قانونی</p>
                    </div>
                    <span class="text-[10px] px-2.5 py-1 rounded-full font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">تخفیف ویژه</span>
                </div>

                <div class="space-y-2.5" id="premiumOptionsList"></div>

                <div class="pt-3 border-t border-white/5 flex items-center justify-between">
                    <div>
                        <p class="text-[11px] text-slate-400">مبلغ اشتراک:</p>
                        <p id="selectedPremiumFinalToman" class="text-base font-black text-purple-400">0 تومان</p>
                    </div>
                    <button id="orderPremiumBtn" class="py-3 px-6 rounded-2xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:opacity-90 text-white font-black text-xs transition shadow-lg shadow-purple-600/25 flex items-center gap-2">
                        <span>خرید پرمیوم</span>
                        <i class="fa-solid fa-arrow-left text-xs"></i>
                    </button>
                </div>
            </div>

            <!-- بخش ۲: استارز -->
            <div id="serviceSec-stars" class="hidden space-y-4">
                <div class="app-card p-5 space-y-3 border-amber-500/20">
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

                <div class="app-card p-5 space-y-3">
                    <h3 class="text-xs font-bold text-slate-400">پکیج‌های سریع استارز:</h3>
                    <div id="starsPackagesList" class="space-y-2"></div>

                    <div class="pt-3 border-t border-white/5 flex items-center justify-between">
                        <div>
                            <p class="text-[11px] text-slate-400">مبلغ قابل پرداخت:</p>
                            <p id="selectedStarsFinalToman" class="text-base font-black text-amber-400">0 تومان</p>
                        </div>
                        <button id="orderStarsBtn" class="py-3 px-6 rounded-2xl bg-gradient-to-r from-amber-400 to-yellow-500 text-slate-950 font-black text-xs transition shadow-lg shadow-amber-500/20 flex items-center gap-2">
                            <span>خرید استارز</span>
                            <i class="fa-solid fa-arrow-left text-xs"></i>
                        </button>
                    </div>
                </div>
            </div>

            <!-- بخش ۳: خدمات پویا و بوست کانال -->
            <div id="serviceSec-custom" class="hidden space-y-4">
                <div id="customServicesContainer" class="space-y-4"></div>
            </div>
        </section>

        <!-- 👤 ۴. تب پروفایل کاربر (User Profile) -->
        <section id="view-profile" class="hidden max-w-xl mx-auto space-y-4">
            <!-- کارت کاربری تلگرام -->
            <div class="app-card p-6 flex items-center gap-4 border-amber-500/20">
                <div class="w-16 h-16 rounded-2xl bg-gradient-to-tr from-amber-400 via-purple-500 to-indigo-600 flex items-center justify-center text-2xl font-black text-slate-950 shadow-lg shadow-amber-500/20">
                    <span id="profileAvatarInitial">🦆</span>
                </div>
                <div class="space-y-1">
                    <h3 id="profileFullName" class="text-base font-black text-white">کاربر تلگرام</h3>
                    <p id="profileUsername" class="text-xs text-amber-400 font-bold">@username</p>
                    <p id="profileUserId" class="text-[10px] text-slate-400">آیدی کاربری: -</p>
                </div>
            </div>

            <!-- خلاصه آمار حساب -->
            <div class="grid grid-cols-2 gap-3 text-xs">
                <div class="app-card p-4 flex flex-col justify-between space-y-1">
                    <span class="text-slate-400 font-bold">گیفت‌های ذخیره‌شده</span>
                    <span id="profileFavsCount" class="text-lg font-black text-rose-400">0 عدد</span>
                </div>
                <div class="app-card p-4 flex flex-col justify-between space-y-1">
                    <span class="text-slate-400 font-bold">اقلام سبد خرید</span>
                    <span id="profileCartCount" class="text-lg font-black text-cyan-400">0 مورد</span>
                </div>
            </div>

            <!-- گزینه‌ها و لینک‌ها -->
            <div class="app-card p-4 space-y-2 text-xs font-bold">
                <a id="profileSupportBtn" href="https://t.me/Zanjani_a" class="p-3 rounded-xl bg-white/[0.03] hover:bg-white/[0.08] flex items-center justify-between transition">
                    <div class="flex items-center gap-3">
                        <i class="fa-brands fa-telegram text-sky-400 text-sm"></i>
                        <span>ارتباط مستقیم با پشتیبانی Duck Store</span>
                    </div>
                    <i class="fa-solid fa-chevron-left text-[10px] text-slate-500"></i>
                </a>
                <button id="profileShareBtn" class="w-full p-3 rounded-xl bg-white/[0.03] hover:bg-white/[0.08] flex items-center justify-between transition text-right">
                    <div class="flex items-center gap-3">
                        <i class="fa-solid fa-share-nodes text-amber-400 text-sm"></i>
                        <span>اشتراک‌گذاری فروشگاه با دوستان</span>
                    </div>
                    <i class="fa-solid fa-chevron-left text-[10px] text-slate-500"></i>
                </button>
            </div>
        </section>

    </main>

    <!-- 🛍️ پاپ‌آپ سبد خرید (Interactive Cart Drawer) -->
    <div id="cartPopupDrawer" class="fixed inset-x-4 bottom-24 max-w-lg mx-auto z-40 app-card p-4 shadow-2xl border-amber-500/40 bg-[#0d0e1b]/95 backdrop-blur-2xl transition-all duration-300 transform translate-y-48 opacity-0 space-y-3">
        <div class="flex items-center justify-between border-b border-white/5 pb-2.5">
            <div class="flex items-center gap-2.5">
                <div class="w-8 h-8 rounded-xl bg-amber-400 text-slate-950 flex items-center justify-center font-black text-xs">
                    <span id="cartDrawerCount">0</span>
                </div>
                <div>
                    <h4 class="text-xs font-black text-white">سبد اجاره گیفت</h4>
                    <p id="cartDrawerTotal" class="text-[11px] font-black text-amber-400">0 تومان</p>
                </div>
            </div>
            <div class="flex items-center gap-2">
                <button id="drawerClearBtn" class="text-[11px] text-rose-400 hover:text-rose-300 font-bold px-2 py-1">پاک کردن</button>
                <button id="drawerToggleListBtn" class="w-7 h-7 rounded-lg bg-white/5 text-slate-300 flex items-center justify-center text-xs">
                    <i id="drawerToggleIcon" class="fa-solid fa-chevron-up"></i>
                </button>
            </div>
        </div>

        <!-- لیست قابل باز شدن آیتم‌ها -->
        <div id="cartDrawerItems" class="hidden space-y-2 max-h-40 overflow-y-auto pt-1"></div>

        <!-- کادر کوپن تخفیف -->
        <div class="flex items-center gap-2 bg-[#050711] p-1.5 rounded-xl border border-white/5">
            <input type="text" id="couponInput" maxlength="20" placeholder="کد تخفیف..." class="bg-transparent text-xs text-white px-3 py-1.5 flex-1 focus:outline-none uppercase font-bold placeholder-slate-600">
            <button id="applyCouponBtn" class="px-3.5 py-1.5 bg-amber-400 hover:bg-amber-300 text-slate-950 text-xs font-black rounded-lg transition">اعمال</button>
        </div>

        <!-- دکمه نهایی ثبت فاکتور -->
        <button id="checkoutCartBtn" class="w-full py-3 bg-gradient-to-r from-amber-400 via-amber-500 to-yellow-500 hover:opacity-90 text-slate-950 font-black text-xs rounded-xl transition shadow-lg shadow-amber-500/20 flex items-center justify-center gap-2">
            <span>ثبت و ارسال سفارش به تلگرام</span>
            <i class="fa-solid fa-paper-plane text-xs"></i>
        </button>
    </div>

    <!-- منوی شناور ناوبری پایینی -->
    <nav class="fixed bottom-3 inset-x-4 max-w-md mx-auto z-40 dock-bar px-3 py-2 flex items-center justify-around shadow-2xl">
        <button id="nav-home" class="nav-btn active flex flex-col items-center gap-1 text-[10px] font-bold text-slate-400 transition">
            <i class="fa-solid fa-house nav-icon text-sm"></i>
            <span>خانه</span>
        </button>
        <button id="nav-gifts" class="nav-btn flex flex-col items-center gap-1 text-[10px] font-bold text-slate-400 transition">
            <i class="fa-solid fa-gift nav-icon text-sm"></i>
            <span>گیفت‌ها</span>
        </button>
        <button id="nav-services" class="nav-btn flex flex-col items-center gap-1 text-[10px] font-bold text-slate-400 transition">
            <i class="fa-solid fa-bolt nav-icon text-sm"></i>
            <span>خدمات</span>
        </button>
        <button id="nav-profile" class="nav-btn flex flex-col items-center gap-1 text-[10px] font-bold text-slate-400 transition">
            <i class="fa-solid fa-user nav-icon text-sm"></i>
            <span>پروفایل</span>
        </button>
    </nav>

    <!-- مودال انتخاب کالکشن -->
    <div id="collectionModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md hidden">
        <div class="app-card w-full max-w-md rounded-[28px] overflow-hidden shadow-2xl flex flex-col max-h-[80vh] border-purple-500/20">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-white/10">
                <button id="closeCollectionModalBtn" class="w-7 h-7 rounded-full bg-white/5 text-slate-400 hover:text-white flex items-center justify-center transition">
                    <i class="fa-solid fa-xmark text-xs"></i>
                </button>
                <h3 class="text-xs font-black text-white">کالکشن‌های گیفت</h3>
                <div class="w-7"></div>
            </div>
            <div class="p-3 border-b border-white/10 flex items-center justify-between text-xs">
                <button id="selectAllColsBtn" class="text-amber-400 font-bold">انتخاب همه</button>
                <button id="clearColsBtn" class="text-slate-400 hover:text-rose-400">لغو همه</button>
            </div>
            <div id="modalCollectionsList" class="p-3 space-y-1.5 overflow-y-auto flex-1"></div>
            <div class="p-3 border-t border-white/10 bg-[#07080f]">
                <button id="applyColsModalBtn" class="w-full py-2.5 bg-amber-400 text-slate-950 text-xs font-black rounded-xl transition">
                    اعمال فیلتر (<span id="modalSelectedCountBadge">همه</span>)
                </button>
            </div>
        </div>
    </div>

    <script>
        function escapeHtml(str) {
            if (!str) return '';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }

        let tgUser = null;
        if (window.Telegram && window.Telegram.WebApp) {
            try {
                window.Telegram.WebApp.ready();
                window.Telegram.WebApp.expand();
                if (window.Telegram.WebApp.MainButton) window.Telegram.WebApp.MainButton.hide();
                tgUser = window.Telegram.WebApp.initDataUnsafe?.user || null;
            } catch (e) {}
        }

        function triggerHaptic(type = 'light') {
            try {
                if (window.Telegram?.WebApp?.HapticFeedback) {
                    if (type === 'selection') window.Telegram.WebApp.HapticFeedback.selectionChanged();
                    else window.Telegram.WebApp.HapticFeedback.impactOccurred(type);
                }
            } catch (e) {}
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

        const DEALS = Array.isArray(__DEALS_JSON__) ? __DEALS_JSON__ : [];
        const COLLECTIONS = Array.isArray(__COLLECTIONS_JSON__) ? __COLLECTIONS_JSON__ : [];
        const WORKER_URL = "__WORKER_URL__";

        const DEFAULT_SETTINGS = {
            ratePerStar: 1450,
            giftMonthlyPrice: 160000,
            prem3: 620000,
            prem6: 950000,
            prem12: 1690000,
            adminTg: 'Zanjani_a',
            announcementText: 'تخفیف ویژه سفارشات فعال شد',
            announcementActive: true,
            couponCode: 'DUCK',
            couponPercent: 10,
            tabGiftsActive: true,
            tabStarsActive: true,
            tabPremiumActive: true,
            customServices: [
                {
                    id: 'boost',
                    title: 'بوست کانال (Channel Boost)',
                    icon: 'fa-bolt',
                    description: 'افزایش لول کانال جهت فعال‌سازی استوری و لینک‌های ویژه',
                    packages: [
                        { name: 'بوست ۱ روزه (Level 1)', price: 45000, tag: 'تستی' },
                        { name: 'بوست ۷ روزه (Level 1)', price: 180000, tag: 'محبوب' },
                        { name: 'بوست ۱۴ روزه (Level 1)', price: 340000, tag: 'پیشنهادی' },
                        { name: 'بوست ۳۰ روزه (Level 1)', price: 620000, tag: 'ویژه' }
                    ]
                }
            ]
        };

        let SETTINGS = { ...DEFAULT_SETTINGS };
        let currentView = 'home';
        let currentServicesTab = 'prem';
        let selectedType = 'all';
        let selectedCollections = new Set();
        let tempSelectedCollections = new Set();

        let appliedCouponCode = null;
        let appliedDiscountPercent = 0;
        let selectedStarsCount = 50;
        let selectedPremiumMonths = 12;

        const STARS_PACKAGES = [50, 75, 100, 150, 250, 350, 500, 1000, 2500, 5000];

        let favorites = [];
        try {
            const f = JSON.parse(localStorage.getItem('duck_favs'));
            if (Array.isArray(f)) favorites = f.filter(x => typeof x === 'string');
        } catch (e) {}

        let cart = [];
        try {
            const c = JSON.parse(localStorage.getItem('duck_cart'));
            if (Array.isArray(c)) cart = c.filter(x => x && typeof x === 'object' && x.name);
        } catch (e) {}

        let currentFilteredDeals = [];

        function switchView(viewName) {
            triggerHaptic('selection');
            currentView = viewName;
            ['home', 'gifts', 'services', 'profile'].forEach(v => {
                const sec = document.getElementById(`view-${v}`);
                if (sec) sec.classList.add('hidden');
                const nav = document.getElementById(`nav-${v}`);
                if (nav) nav.classList.remove('active');
            });

            const activeSec = document.getElementById(`view-${viewName}`);
            if (activeSec) activeSec.classList.remove('hidden');
            const activeNav = document.getElementById(`nav-${viewName}`);
            if (activeNav) activeNav.classList.add('active');

            if (viewName === 'profile') renderProfileView();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }

        function switchServicesTab(tab) {
            triggerHaptic('selection');
            currentServicesTab = tab;
            ['prem', 'stars', 'custom'].forEach(t => {
                const sec = document.getElementById(`serviceSec-${t}`);
                if (sec) sec.classList.add('hidden');
                const btn = document.getElementById(`subtabBtn-${t}`);
                if (btn) {
                    btn.className = 'subtab-btn flex-1 py-2 px-3 rounded-xl text-xs font-bold text-slate-400 hover:text-white whitespace-nowrap transition';
                }
            });

            const activeSec = document.getElementById(`serviceSec-${tab}`);
            if (activeSec) activeSec.classList.remove('hidden');
            const activeBtn = document.getElementById(`subtabBtn-${tab}`);
            if (activeBtn) {
                activeBtn.className = 'subtab-btn active flex-1 py-2 px-3 rounded-xl text-xs font-black bg-amber-400 text-slate-950 whitespace-nowrap transition';
            }
        }

        async function fetchCloudSettings() {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 3500);
                const res = await fetch(`${WORKER_URL}/api/settings`, { signal: controller.signal });
                clearTimeout(timeoutId);
                if (res.ok) {
                    const parsed = await res.json();
                    if (parsed && typeof parsed === 'object') {
                        SETTINGS = { ...DEFAULT_SETTINGS, ...parsed };
                        updateUIWithLatestSettings();
                    }
                }
            } catch (err) {}
        }

        function updateUIWithLatestSettings() {
            try {
                const adminUser = escapeHtml((SETTINGS.adminTg || 'Zanjani_a').replace('@', '').trim());
                const supportLink = document.getElementById('headerSupportLink');
                if (supportLink) supportLink.href = `https://t.me/${adminUser}`;
                const profileSupport = document.getElementById('profileSupportBtn');
                if (profileSupport) profileSupport.href = `https://t.me/${adminUser}`;

                const promo = document.getElementById('promoBanner');
                if (promo) {
                    if (SETTINGS.announcementActive && SETTINGS.announcementText) {
                        const promoText = document.getElementById('promoBannerText');
                        if (promoText) promoText.innerText = SETTINGS.announcementText;
                        promo.classList.remove('hidden');
                    } else {
                        promo.classList.add('hidden');
                    }
                }

                renderCards(getFilteredDeals());
                renderHomeDeals();
                renderStarsPackages();
                renderPremiumOptions();
                renderCustomServices();
                updateCartPopup();
            } catch (e) {}
        }

        // ================= رندر خدمات سفارشی داینامیک =================
        function renderCustomServices() {
            const container = document.getElementById('customServicesContainer');
            if (!container) return;

            const list = Array.isArray(SETTINGS.customServices) && SETTINGS.customServices.length > 0 
                ? SETTINGS.customServices 
                : DEFAULT_SETTINGS.customServices;

            container.innerHTML = list.map(cat => `
                <div class="app-card p-5 space-y-3.5 border-cyan-500/20">
                    <div class="flex items-center gap-2.5 border-b border-white/5 pb-2.5">
                        <div class="w-8 h-8 rounded-xl bg-cyan-400/10 text-cyan-400 flex items-center justify-center text-sm">
                            <i class="fa-solid ${escapeHtml(cat.icon || 'fa-bolt')}"></i>
                        </div>
                        <div>
                            <h4 class="text-xs font-black text-white">${escapeHtml(cat.title)}</h4>
                            <p class="text-[10px] text-slate-400 mt-0.5">${escapeHtml(cat.description || '')}</p>
                        </div>
                    </div>
                    <div class="space-y-2">
                        ${(cat.packages || []).map((pkg, i) => `
                            <div class="p-3 rounded-2xl bg-white/[0.02] border border-white/5 flex items-center justify-between">
                                <div>
                                    <span class="text-xs font-bold text-white">${escapeHtml(pkg.name)}</span>
                                    ${pkg.tag ? `<span class="text-[9px] px-2 py-0.5 rounded-full bg-cyan-400/10 text-cyan-300 font-bold mr-1.5">${escapeHtml(pkg.tag)}</span>` : ''}
                                </div>
                                <div class="flex items-center gap-3">
                                    <span class="text-xs font-black text-cyan-400">${Number(pkg.price || 0).toLocaleString('en-US')} ت</span>
                                    <button onclick="orderCustomPackage('${escapeHtml(cat.title)}', '${escapeHtml(pkg.name)}', ${pkg.price})" class="px-3 py-1 rounded-xl bg-cyan-400 hover:bg-cyan-300 text-slate-950 font-black text-[11px] transition">
                                        سفارش
                                    </button>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `).join('');
        }

        function orderCustomPackage(catTitle, pkgName, price) {
            triggerHaptic('heavy');
            const adminUser = escapeHtml((SETTINGS.adminTg || 'Zanjani_a').replace('@', '').trim());
            const buyer = getBuyerDetailsText();
            const nl = String.fromCharCode(10);
            const msg = encodeURIComponent(
                "سلام، متقاضی سفارش خدمت زیر هستم:" + nl + nl +
                buyer + nl + nl +
                "دسته: " + catTitle + nl +
                "پکیج: " + pkgName + nl +
                "مبلغ: " + Number(price || 0).toLocaleString('en-US') + " تومان"
            );
            openTgLink(`https://t.me/${adminUser}?text=${msg}`);
        }

        // ================= رندر پروفایل =================
        function renderProfileView() {
            if (tgUser) {
                const name = `${tgUser.first_name || ''} ${tgUser.last_name || ''}`.trim() || 'کاربر تلگرام';
                document.getElementById('profileFullName').innerText = name;
                document.getElementById('profileUsername').innerText = tgUser.username ? `@${tgUser.username}` : 'بدون یوزرنیم';
                document.getElementById('profileUserId').innerText = `آیدی کاربری: ${tgUser.id}`;
                document.getElementById('profileAvatarInitial').innerText = (tgUser.first_name || 'U').charAt(0).toUpperCase();
            }
            document.getElementById('profileFavsCount').innerText = `${favorites.length} عدد`;
            document.getElementById('profileCartCount').innerText = `${cart.length} مورد`;
        }

        // ================= پاپ‌آپ سبد خرید هوشمند =================
        function toggleCart(item) {
            if (!item || !item.name) return;
            triggerHaptic('selection');
            const idx = cart.findIndex(c => c && c.name === item.name);
            if (idx > -1) {
                cart.splice(idx, 1);
            } else {
                cart.push(item);
            }
            localStorage.setItem('duck_cart', JSON.stringify(cart));
            updateCartPopup(true); // هنگام افزودن، پاپ‌آپ بالا می‌آید
            renderCards(getFilteredDeals());
            renderCartDrawerItems();
        }

        function updateCartPopup(shouldShow = false) {
            const popup = document.getElementById('cartPopupDrawer');
            if (!popup) return;
            const count = cart.length;
            document.getElementById('cartDrawerCount').innerText = count;

            const basePrice = Number(SETTINGS.giftMonthlyPrice) || 160000;
            const rawTotal = count * basePrice;
            const finalTotal = appliedDiscountPercent > 0 ? Math.round(rawTotal * (1 - appliedDiscountPercent / 100)) : rawTotal;
            document.getElementById('cartDrawerTotal').innerText = `${finalTotal.toLocaleString('en-US')} تومان`;

            if (count > 0 && (shouldShow || currentView === 'gifts' || currentView === 'home')) {
                popup.classList.remove('translate-y-48', 'opacity-0');
                popup.classList.add('translate-y-0', 'opacity-100');
            } else {
                popup.classList.remove('translate-y-0', 'opacity-100');
                popup.classList.add('translate-y-48', 'opacity-0');
            }
        }

        function renderCartDrawerItems() {
            const container = document.getElementById('cartDrawerItems');
            if (!container) return;
            if (cart.length === 0) {
                container.innerHTML = '<p class="text-[11px] text-slate-500 text-center py-2">سبد خالی است</p>';
            } else {
                container.innerHTML = cart.map((item, i) => `
                    <div class="p-2 rounded-xl bg-white/[0.03] border border-white/5 flex items-center justify-between text-xs">
                        <span class="font-bold text-slate-300 truncate max-w-[200px]">${i + 1}. ${escapeHtml(item.name)}</span>
                        <button onclick="toggleCartByIndex(${DEALS.findIndex(d => d.name === item.name)})" class="text-rose-400 hover:text-rose-300 px-2 py-0.5">
                            <i class="fa-solid fa-xmark"></i>
                        </button>
                    </div>
                `).join('');
            }
        }

        function clearCart() {
            triggerHaptic('light');
            cart = [];
            appliedCouponCode = null;
            appliedDiscountPercent = 0;
            localStorage.setItem('duck_cart', JSON.stringify(cart));
            updateCartPopup();
            renderCartDrawerItems();
            renderCards(getFilteredDeals());
        }

        function checkoutCart() {
            triggerHaptic('heavy');
            if (cart.length === 0) return alert('سبد خرید شما خالی است!');
            const adminUser = escapeHtml((SETTINGS.adminTg || 'Zanjani_a').replace('@', '').trim());
            const basePrice = Number(SETTINGS.giftMonthlyPrice) || 160000;
            const rawTotal = cart.length * basePrice;
            const finalTotal = appliedDiscountPercent > 0 ? Math.round(rawTotal * (1 - appliedDiscountPercent / 100)) : rawTotal;
            const buyer = getBuyerDetailsText();
            const nl = String.fromCharCode(10);
            const itemsList = cart.map((c, i) => `${i + 1}. 🎁 ${c.name} (${c.tg_link || 'https://t.me'})`).join(nl);
            const coupon = appliedCouponCode ? (nl + `کد تخفیف: ${appliedCouponCode} (${appliedDiscountPercent}%)`) : '';

            const msg = encodeURIComponent(
                "سلام، درخواست اجاره گیفت دارم:" + nl + nl +
                buyer + nl + nl +
                "اقلام سفارش (" + cart.length + " عدد):" + nl +
                itemsList + nl + nl +
                "مبلغ نهایی: " + finalTotal.toLocaleString('en-US') + " تومان / ماه" +
                coupon
            );
            openTgLink(`https://t.me/${adminUser}?text=${msg}`);
        }

        function applyCoupon() {
            triggerHaptic('medium');
            const input = (document.getElementById('couponInput')?.value || '').trim().toUpperCase();
            if (SETTINGS.couponCode && input === SETTINGS.couponCode.toUpperCase()) {
                appliedCouponCode = input;
                appliedDiscountPercent = Number(SETTINGS.couponPercent) || 10;
                alert(`کد تخفیف ${appliedDiscountPercent}٪ اعمال شد`);
            } else {
                alert('کد تخفیف نامعتبر است');
            }
            updateCartPopup();
        }

        // ================= استارز و پرمیوم =================
        function renderStarsPackages() {
            const container = document.getElementById('starsPackagesList');
            if (!container) return;
            container.innerHTML = STARS_PACKAGES.map(qty => {
                const totalToman = (qty * Number(SETTINGS.ratePerStar || 1450)).toLocaleString('en-US');
                const isSelected = selectedStarsCount === qty;
                return `
                <div data-stars-qty="${qty}" class="stars-pkg-btn p-3 rounded-2xl bg-white/[0.02] border ${isSelected ? 'border-amber-400 bg-amber-400/10' : 'border-white/5'} flex items-center justify-between cursor-pointer transition">
                    <span class="text-xs font-bold text-white">${qty} Stars</span>
                    <span class="text-xs font-black text-amber-400">${totalToman} ت</span>
                </div>
                `;
            }).join('');

            container.querySelectorAll('.stars-pkg-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const qty = Number(e.currentTarget.getAttribute('data-stars-qty'));
                    triggerHaptic('selection');
                    selectedStarsCount = qty;
                    renderStarsPackages();
                });
            });
            updateStarsFinalPrice();
        }

        function updateStarsFinalPrice() {
            const total = (selectedStarsCount * Number(SETTINGS.ratePerStar || 1450)).toLocaleString('en-US');
            const target = document.getElementById('selectedStarsFinalToman');
            if (target) target.innerText = `${total} تومان`;
        }

        function orderStars() {
            triggerHaptic('heavy');
            const adminUser = escapeHtml((SETTINGS.adminTg || 'Zanjani_a').replace('@', '').trim());
            const total = (selectedStarsCount * Number(SETTINGS.ratePerStar || 1450)).toLocaleString('en-US');
            const buyer = getBuyerDetailsText();
            const nl = String.fromCharCode(10);
            const msg = encodeURIComponent(
                "سلام، درخواست خرید استارز تلگرام دارم:" + nl + nl +
                buyer + nl + nl +
                "تعداد استارز: " + selectedStarsCount + " Stars" + nl +
                "مبلغ قابل پرداخت: " + total + " تومان"
            );
            openTgLink(`https://t.me/${adminUser}?text=${msg}`);
        }

        function renderPremiumOptions() {
            const container = document.getElementById('premiumOptionsList');
            if (!container) return;
            const options = [
                { months: 12, label: '۱۲ ماهه (1 Year)', discount: '-52%', price: Number(SETTINGS.prem12) || 1690000 },
                { months: 6, label: '۶ ماهه (6 Months)', discount: '-47%', price: Number(SETTINGS.prem6) || 950000 },
                { months: 3, label: '۳ ماهه (3 Months)', discount: '-20%', price: Number(SETTINGS.prem3) || 620000 }
            ];

            container.innerHTML = options.map(opt => {
                const isSelected = selectedPremiumMonths === opt.months;
                const totalToman = opt.price.toLocaleString('en-US');
                return `
                <div data-prem-months="${opt.months}" class="prem-plan-btn p-3.5 rounded-2xl bg-white/[0.02] border ${isSelected ? 'border-purple-400 bg-purple-500/10' : 'border-white/5'} flex items-center justify-between cursor-pointer transition">
                    <div>
                        <span class="text-xs font-bold text-white">${escapeHtml(opt.label)}</span>
                        <span class="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 font-bold mr-2">${escapeHtml(opt.discount)}</span>
                    </div>
                    <span class="text-xs font-black text-purple-300">${totalToman} ت</span>
                </div>
                `;
            }).join('');

            container.querySelectorAll('.prem-plan-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const months = Number(e.currentTarget.getAttribute('data-prem-months'));
                    triggerHaptic('selection');
                    selectedPremiumMonths = months;
                    renderPremiumOptions();
                });
            });
            updatePremiumFinalPrice();
        }

        function updatePremiumFinalPrice() {
            let price = Number(SETTINGS.prem12) || 1690000;
            if (selectedPremiumMonths === 6) price = Number(SETTINGS.prem6) || 950000;
            if (selectedPremiumMonths === 3) price = Number(SETTINGS.prem3) || 620000;
            const target = document.getElementById('selectedPremiumFinalToman');
            if (target) target.innerText = `${price.toLocaleString('en-US')} تومان`;
        }

        function orderPremium() {
            triggerHaptic('heavy');
            const adminUser = escapeHtml((SETTINGS.adminTg || 'Zanjani_a').replace('@', '').trim());
            let planName = '1 ساله';
            let price = Number(SETTINGS.prem12) || 1690000;
            if (selectedPremiumMonths === 6) { planName = '6 ماهه'; price = Number(SETTINGS.prem6) || 950000; }
            if (selectedPremiumMonths === 3) { planName = '3 ماهه'; price = Number(SETTINGS.prem3) || 620000; }
            const total = price.toLocaleString('en-US');
            const buyer = getBuyerDetailsText();
            const nl = String.fromCharCode(10);
            const msg = encodeURIComponent(
                "سلام، درخواست خرید تلگرام پرمیوم دارم:" + nl + nl +
                buyer + nl + nl +
                "نوع اشتراک: " + planName + nl +
                "مبلغ قابل پرداخت: " + total + " تومان"
            );
            openTgLink(`https://t.me/${adminUser}?text=${msg}`);
        }

        function getBuyerDetailsText() {
            if (!tgUser) return "خریدار: کاربر وب";
            const name = escapeHtml(`${tgUser.first_name || ''} ${tgUser.last_name || ''}`.trim() || 'کاربر تلگرام');
            const uname = tgUser.username ? `@${escapeHtml(tgUser.username)}` : 'بدون یوزرنیم';
            return `خریدار: ${name} (${uname} - آیدی: ${tgUser.id})`;
        }

        // ================= رندر کارت‌ها و خانه =================
        function renderHomeDeals() {
            const container = document.getElementById('homeRecentDeals');
            if (!container) return;
            const topDeals = DEALS.slice(0, 6);
            container.innerHTML = topDeals.map((d, i) => `
                <div class="app-card p-3 flex items-center justify-between">
                    <div class="flex items-center gap-3">
                        <img src="${escapeHtml(d.image_url || 'https://marketapp.org/favicon.ico')}" class="w-12 h-12 rounded-xl object-contain bg-black/40 p-1" onerror="this.src='https://marketapp.org/favicon.ico'">
                        <div>
                            <h4 class="text-xs font-bold text-white">${escapeHtml(d.name)}</h4>
                            <span class="text-[10px] text-amber-400 font-bold">${Number(SETTINGS.giftMonthlyPrice || 160000).toLocaleString('en-US')} ت/ماه</span>
                        </div>
                    </div>
                    <button data-home-idx="${i}" class="home-add-btn px-3 py-1.5 rounded-xl bg-amber-400/10 text-amber-300 border border-amber-400/20 text-xs font-bold hover:bg-amber-400 hover:text-slate-950 transition">
                        + سبد
                    </button>
                </div>
            `).join('');

            container.querySelectorAll('.home-add-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const idx = Number(e.currentTarget.getAttribute('data-home-idx'));
                    if (topDeals[idx]) toggleCart(topDeals[idx]);
                });
            });
        }

        function renderCards(items) {
            currentFilteredDeals = Array.isArray(items) ? items : [];
            const container = document.getElementById('dealsGrid');
            if (!container) return;

            if (currentFilteredDeals.length === 0) {
                container.innerHTML = '<div class="col-span-full py-16 text-center text-slate-400 font-bold">گیفتی با این مشخصات پیدا نشد.</div>';
                return;
            }

            const giftPriceFormatted = Number(SETTINGS.giftMonthlyPrice || 160000).toLocaleString('en-US');

            let html = '';
            for (let idx = 0; idx < currentFilteredDeals.length; idx++) {
                const deal = currentFilteredDeals[idx];
                if (!deal) continue;

                const rarityBadge = deal.rarity 
                    ? `<span class="absolute top-2.5 left-2.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30 backdrop-blur-md">${escapeHtml(deal.rarity)}</span>` 
                    : '';
                
                const isFav = favorites.includes(deal.name);
                const isInCart = cart.some(c => c && c.name === deal.name);

                html += `
                <div class="app-card overflow-hidden flex flex-col justify-between ${isInCart ? 'border-amber-400 bg-amber-500/5' : ''}">
                    <div>
                        <div class="relative w-full h-44 bg-gradient-to-b from-white/[0.04] to-transparent flex items-center justify-center overflow-hidden border-b border-white/5">
                            ${rarityBadge}
                            <button data-fav-idx="${idx}" class="fav-btn absolute top-2.5 right-2.5 w-8 h-8 rounded-full bg-black/40 backdrop-blur-md flex items-center justify-center text-sm transition hover:scale-110 ${isFav ? 'text-rose-500' : 'text-slate-400 hover:text-white'}">
                                <i class="${isFav ? 'fa-solid' : 'fa-regular'} fa-heart"></i>
                            </button>
                            <img src="${escapeHtml(deal.image_url || 'https://marketapp.org/favicon.ico')}" alt="${escapeHtml(deal.name)}" class="w-28 h-28 object-contain drop-shadow-[0_10px_20px_rgba(0,0,0,0.8)]" onerror="this.src='https://marketapp.org/favicon.ico'">
                        </div>
                        <div class="p-3.5 space-y-2">
                            <h3 class="font-bold text-xs text-white truncate text-center">${escapeHtml(deal.name)}</h3>
                            <div class="flex justify-between items-center text-[11px] bg-black/30 p-2 rounded-xl border border-white/5">
                                <span class="text-slate-400">اجاره ماهانه:</span>
                                <span class="font-black text-amber-300">${giftPriceFormatted} ت</span>
                            </div>
                        </div>
                    </div>
                    <div class="p-3.5 pt-0 grid grid-cols-2 gap-2">
                        <a href="${escapeHtml(deal.tg_link || 'https://t.me')}" target="_blank" class="py-2 rounded-xl bg-white/[0.04] text-slate-300 text-xs font-bold text-center border border-white/10">مشاهده</a>
                        <button data-cart-idx="${idx}" class="cart-btn py-2 rounded-xl ${isInCart ? 'bg-amber-400 text-slate-950 font-black' : 'bg-white text-slate-950 font-bold'} text-xs text-center transition">
                            ${isInCart ? 'انتخاب شد' : 'اجاره'}
                        </button>
                    </div>
                </div>
                `;
            }
            container.innerHTML = html;

            container.querySelectorAll('.fav-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const idx = Number(e.currentTarget.getAttribute('data-fav-idx'));
                    const deal = currentFilteredDeals[idx];
                    if (deal && deal.name) {
                        triggerHaptic('medium');
                        const fIdx = favorites.indexOf(deal.name);
                        if (fIdx > -1) favorites.splice(fIdx, 1);
                        else favorites.push(deal.name);
                        localStorage.setItem('duck_favs', JSON.stringify(favorites));
                        updateFavCount();
                        renderCards(getFilteredDeals());
                    }
                });
            });

            container.querySelectorAll('.cart-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const idx = Number(e.currentTarget.getAttribute('data-cart-idx'));
                    const deal = currentFilteredDeals[idx];
                    if (deal) toggleCart(deal);
                });
            });
        }

        function toggleCartByIndex(idx) {
            if (DEALS[idx]) toggleCart(DEALS[idx]);
        }

        function updateFavCount() {
            const el = document.getElementById('favCount');
            if (el) el.innerText = favorites.length;
        }

        function openModal() {
            triggerHaptic('light');
            tempSelectedCollections = new Set(selectedCollections);
            const m = document.getElementById('collectionModal');
            if (m) m.classList.remove('hidden');
            renderModalCollections();
        }

        function closeModal() {
            triggerHaptic('light');
            const m = document.getElementById('collectionModal');
            if (m) m.classList.add('hidden');
        }

        function renderModalCollections() {
            const container = document.getElementById('modalCollectionsList');
            if (!container) return;
            container.innerHTML = COLLECTIONS.map((col, idx) => {
                const isSelected = tempSelectedCollections.has(col.name);
                return `
                <div data-col-idx="${idx}" class="col-item-row p-2.5 rounded-xl border ${isSelected ? 'border-amber-400 bg-amber-500/10' : 'border-white/5'} flex items-center justify-between cursor-pointer">
                    <span class="text-xs font-bold text-slate-200">${escapeHtml(col.name)}</span>
                    <span class="text-[10px] text-slate-400">${Number(col.count) || 0}</span>
                </div>
                `;
            }).join('');

            container.querySelectorAll('.col-item-row').forEach(row => {
                row.addEventListener('click', (e) => {
                    const idx = Number(e.currentTarget.getAttribute('data-col-idx'));
                    const col = COLLECTIONS[idx];
                    if (col && col.name) {
                        triggerHaptic('selection');
                        if (tempSelectedCollections.has(col.name)) tempSelectedCollections.delete(col.name);
                        else tempSelectedCollections.add(col.name);
                        renderModalCollections();
                    }
                });
            });
        }

        function applyCollectionModal() {
            selectedCollections = new Set(tempSelectedCollections);
            const label = document.getElementById('selectedColText');
            if (label) {
                label.innerText = selectedCollections.size === 0 ? 'کالکشن‌ها' : `${selectedCollections.size} کالکشن`;
            }
            closeModal();
            applyFilters();
        }

        function getFilteredDeals() {
            try {
                const query = (document.getElementById('searchInput')?.value || '').trim().toLowerCase();
                return DEALS.filter(d => {
                    if (!d) return false;
                    const dName = String(d.name || '').toLowerCase();
                    const dNum = String(d.number || '').toLowerCase();
                    const dTitle = String(d.gift_title || '').toLowerCase();

                    if (query && !dName.includes(query) && !dNum.includes(query) && !dTitle.includes(query)) {
                        return false;
                    }
                    if (selectedType === 'rare' && !d.rarity) return false;
                    if (selectedType === 'favs' && !favorites.includes(d.name)) return false;
                    if (selectedCollections.size > 0 && selectedCollections.size < COLLECTIONS.length) {
                        if (!selectedCollections.has(d.gift_title)) return false;
                    }
                    return true;
                });
            } catch (err) {
                return DEALS;
            }
        }

        function applyFilters() {
            renderCards(getFilteredDeals());
        }

        function setupEventListeners() {
            // ناوبری اصلی پایین
            document.getElementById('nav-home')?.addEventListener('click', () => switchView('home'));
            document.getElementById('nav-gifts')?.addEventListener('click', () => switchView('gifts'));
            document.getElementById('nav-services')?.addEventListener('click', () => switchView('services'));
            document.getElementById('nav-profile')?.addEventListener('click', () => switchView('profile'));

            // زیرتب‌های خدمات
            document.getElementById('subtabBtn-prem')?.addEventListener('click', () => switchServicesTab('prem'));
            document.getElementById('subtabBtn-stars')?.addEventListener('click', () => switchServicesTab('stars'));
            document.getElementById('subtabBtn-custom')?.addEventListener('click', () => switchServicesTab('custom'));

            // میانبرهای صفحه خانه
            document.getElementById('shortcutGifts')?.addEventListener('click', () => switchView('gifts'));
            document.getElementById('shortcutPremium')?.addEventListener('click', () => { switchView('services'); switchServicesTab('prem'); });
            document.getElementById('shortcutStars')?.addEventListener('click', () => { switchView('services'); switchServicesTab('stars'); });
            document.getElementById('shortcutServices')?.addEventListener('click', () => { switchView('services'); switchServicesTab('custom'); });
            document.getElementById('seeAllDealsBtn')?.addEventListener('click', () => switchView('gifts'));
            document.getElementById('promoActionBtn')?.addEventListener('click', () => switchView('gifts'));

            // پاپ‌آپ کشویی سبد خرید
            document.getElementById('drawerToggleListBtn')?.addEventListener('click', () => {
                const list = document.getElementById('cartDrawerItems');
                const icon = document.getElementById('drawerToggleIcon');
                if (list) {
                    list.classList.toggle('hidden');
                    renderCartDrawerItems();
                    if (icon) {
                        icon.classList.toggle('fa-chevron-up');
                        icon.classList.toggle('fa-chevron-down');
                    }
                }
            });
            document.getElementById('drawerClearBtn')?.addEventListener('click', clearCart);
            document.getElementById('checkoutCartBtn')?.addEventListener('click', checkoutCart);
            document.getElementById('applyCouponBtn')?.addEventListener('click', applyCoupon);

            // کالکشن‌ها
            document.getElementById('openColModalBtn')?.addEventListener('click', openModal);
            document.getElementById('closeCollectionModalBtn')?.addEventListener('click', closeModal);
            document.getElementById('selectAllColsBtn')?.addEventListener('click', () => {
                COLLECTIONS.forEach(c => { if (c && c.name) tempSelectedCollections.add(c.name); });
                renderModalCollections();
            });
            document.getElementById('clearColsBtn')?.addEventListener('click', () => {
                tempSelectedCollections.clear();
                renderModalCollections();
            });
            document.getElementById('applyColsModalBtn')?.addEventListener('click', applyCollectionModal);

            // فیلترهای بالا
            const filterMap = [
                { id: 'filterBtnAll', type: 'all' },
                { id: 'filterBtnRare', type: 'rare' },
                { id: 'filterBtnFavs', type: 'favs' }
            ];
            filterMap.forEach(item => {
                document.getElementById(item.id)?.addEventListener('click', (e) => {
                    triggerHaptic('selection');
                    selectedType = item.type;
                    document.querySelectorAll('.type-btn').forEach(b => {
                        b.classList.remove('bg-amber-400', 'text-slate-950');
                        b.classList.add('bg-white/[0.04]', 'text-slate-300');
                    });
                    e.currentTarget.classList.remove('bg-white/[0.04]', 'text-slate-300');
                    e.currentTarget.classList.add('bg-amber-400', 'text-slate-950');
                    applyFilters();
                });
            });

            // سرویس‌ها
            document.getElementById('orderPremiumBtn')?.addEventListener('click', orderPremium);
            document.getElementById('orderStarsBtn')?.addEventListener('click', orderStars);

            // جستجو
            let searchTimer = null;
            document.getElementById('searchInput')?.addEventListener('input', () => {
                clearTimeout(searchTimer);
                searchTimer = setTimeout(applyFilters, 100);
            });

            // محاسبه استارز
            document.getElementById('customStarsInput')?.addEventListener('input', (e) => {
                const val = parseInt(e.target.value);
                if (val && val >= 50) {
                    selectedStarsCount = val;
                    const total = (val * Number(SETTINGS.ratePerStar || 1450)).toLocaleString('en-US');
                    const priceEl = document.getElementById('customStarsPrice');
                    if (priceEl) priceEl.innerText = `${total} تومان`;
                    document.getElementById('customStarsCalcBox')?.classList.remove('hidden');
                } else {
                    document.getElementById('customStarsCalcBox')?.classList.add('hidden');
                }
                updateStarsFinalPrice();
            });

            // دکمه اشتراک‌گذاری پروفایل
            document.getElementById('profileShareBtn')?.addEventListener('click', () => {
                if (navigator.share) {
                    navigator.share({
                        title: 'Duck Store',
                        text: 'مرجع گیفت، استارز و پرمیوم تلگرام',
                        url: window.location.href
                    }).catch(() => {});
                } else {
                    alert('لینک فروشگاه کپی شد');
                }
            });
        }

        function initApp() {
            setupEventListeners();
            applyFilters();
            renderHomeDeals();
            renderStarsPackages();
            renderPremiumOptions();
            renderCustomServices();
            updateFavCount();
            updateCartPopup();
            fetchCloudSettings();
            if (tgUser) {
                const el = document.getElementById('headerGreeting');
                if (el) el.innerText = `${tgUser.first_name || 'کاربر'} 👋`;
            }
        }

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initApp);
        } else {
            initApp();
        }
    </script>
</body>
</html>"""

    html_content = (
        html_template.replace("__TIMESTAMP__", timestamp)
        .replace("__TOTAL_COUNT__", str(len(deals)))
        .replace("__RARE_COUNT__", str(rare_count))
        .replace("__DEALS_JSON__", deals_json)
        .replace("__COLLECTIONS_JSON__", collections_json)
        .replace("__WORKER_URL__", CONFIG["WORKER_URL"])
    )

    try:
        with open(CONFIG["EXPORT_HTML"], "w", encoding="utf-8") as f:
            f.write(html_content)
    except Exception as e:
        print(f"❌ خطا در ذخیره HTML: {e}")

    try:
        with open(CONFIG["EXPORT_JSON"], "w", encoding="utf-8") as f:
            json.dump(deals, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ خطا در ذخیره JSON: {e}")


def send_telegram_package(deals: List[Dict[str, Any]]):
    token = CONFIG.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = CONFIG.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    gh_repo = CONFIG.get("GITHUB_REPOSITORY", "")
    pages_url = "https://zanjania0.github.io/duck-store/"
    if "/" in gh_repo and len(gh_repo.split("/")) >= 2:
        parts = gh_repo.split("/")
        pages_url = f"https://{parts[0]}.github.io/{parts[1]}/"

    rare_count = sum(1 for d in deals if d.get("rarity"))
    full_text = (
        f"🦆 <b>گزارش جدید فروشگاه Duck Store</b>\n"
        f"📅 <i>{timestamp}</i>\n\n"
        f"🌐 <b>لینک ورود به مینی‌اپ:</b>\n👉 <a href='{pages_url}'>{pages_url}</a>\n\n"
        f"🎯 موجودی کل: {len(deals)} مورد (کمیاب: {rare_count})\n"
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
        except Exception as e:
            print(f"❌ خطا در تلگرام: {e}")


def send_telegram_csv_attachment(
    file_path: str, token: str, chat_id: str, caption: str
):
    if not os.path.exists(file_path):
        return
    boundary = "----DuckStoreBoundaryXYZ"
    try:
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
        with urllib.request.urlopen(req, timeout=30):
            pass
    except Exception as e:
        print(f"❌ خطا در ارسال اکسل: {e}")


# ==========================================
# ⚡ موتور اسکرپر پایدار
# ==========================================
async def main():
    deals_found: List[Dict[str, Any]] = []
    seen_links: Set[str] = set()
    browser = None

    print("\n" + "═" * 65)
    print("  🦆 DUCK STORE TURBO SCRAPER (STABLE ENGINE) 🦆")
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
            try:
                browser = await p.chromium.launch(headless=True, args=launch_args)
            except Exception:
                browser = await p.chromium.launch(
                    headless=True, channel="chrome", args=launch_args
                )

            page = await browser.new_page()

            print("🌐 در حال بارگذاری مارکت...")
            await page.goto(
                CONFIG["TARGET_URL"], wait_until="domcontentloaded", timeout=60000
            )
            await page.wait_for_timeout(3000)

            scroll_attempts = 0
            last_count = 0
            no_new_counter = 0

            while (
                len(deals_found) < CONFIG["TARGET_DEALS_COUNT"]
                and scroll_attempts < CONFIG["MAX_SCROLL_ATTEMPTS"]
            ):
                scroll_attempts += 1
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
                    href = c.get("href", "")
                    if not href:
                        continue

                    full_link = (
                        href
                        if href.startswith("http")
                        else f"{CONFIG['BASE_DOMAIN']}{href if href.startswith('/') else '/' + href}"
                    )
                    if full_link in seen_links:
                        continue

                    text = c.get("text", "")
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
                                name_candidates[0]
                                if name_candidates
                                else "NFT Gift"
                            )
                            deal = {
                                "name": f"{gift_name} #{item_num}",
                                "gift_title": gift_name,
                                "number": str(item_num),
                                "discount": f"-{discount_val}%",
                                "discount_num": discount_val,
                                "price_per_day": "0.01",
                                "days_range": days_range,
                                "tg_link": generate_tg_nft_link(
                                    gift_name, item_num
                                ),
                                "market_link": full_link,
                                "image_url": c.get("img")
                                or "https://marketapp.org/favicon.ico",
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

                if len(deals_found) == last_count:
                    no_new_counter += 1
                    if no_new_counter >= 8:
                        break
                else:
                    no_new_counter = 0
                    last_count = len(deals_found)

                await page.evaluate("window.scrollBy(0, window.innerHeight * 3);")
                await page.wait_for_timeout(350)

        finally:
            if browser:
                await browser.close()

        sorted_deals = list(reversed(deals_found))

        generate_duck_store_html(sorted_deals)

        try:
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
        except Exception as e:
            print(f"❌ خطا در نوشتن CSV: {e}")

        print("\n⚡ فروشگاه Duck Store با موفقیت آماده و منتشر شد!")
        send_telegram_package(sorted_deals)


if __name__ == "__main__":
    asyncio.run(main())
