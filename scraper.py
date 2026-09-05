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
    if num < 100: return "👑 زیر 100"
    if num < 1000: return "💎 زیر 1000"
    if len(s) >= 3 and len(set(s)) == 1: return f"✨ رند (#{s})"
    if s in ["123", "1234", "12345", "6969", "777", "888", "999", "10000"]: return f"🎯 خاص (#{s})"
    if len(s) == 4 and s == s[::-1]: return "🔁 متقارن"
    return ""


def generate_tg_nft_link(name: str, number: str) -> str:
    words = re.findall(r"[a-zA-Z0-9]+", name)
    slug = "".join(w.capitalize() for w in words)
    clean_num = re.sub(r"\D", "", str(number))
    return f"https://t.me/nft/{slug}-{clean_num}" if slug and clean_num else "https://t.me"


def generate_duck_store_html(deals: List[Dict[str, Any]]):
    """تولید وب‌سایت با دیزاین فوق مدرن مینیمال مرواریدی/نقره‌ای (Soft Neumorphic Luxury)"""
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

    collections_list = sorted(list(collections_map.values()), key=lambda x: str(x["name"]))
    rare_count = sum(1 for d in deals if d.get("rarity"))

    deals_json = json.dumps(deals, ensure_ascii=False)
    collections_json = json.dumps(collections_list, ensure_ascii=False)

    html_template = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>Pearl Store | خدمات پرمیوم تلگرام</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-canvas: #e9edf3;
            --card-surface: #ffffff;
            --text-main: #191f2c;
            --text-muted: #64748b;
            --neo-shadow: 0 10px 30px -5px rgba(148, 163, 184, 0.3), 0 4px 12px -2px rgba(148, 163, 184, 0.15);
            --neo-convex: 0 8px 20px -3px rgba(148, 163, 184, 0.25);
            --dark-btn: #181d28;
        }
        body {
            font-family: 'Vazirmatn', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-canvas);
            background-image: 
                radial-gradient(circle at 15% 10%, rgba(255, 255, 255, 0.8) 0%, transparent 40%),
                radial-gradient(circle at 85% 25%, rgba(226, 232, 240, 0.6) 0%, transparent 50%),
                radial-gradient(circle at 50% 90%, rgba(255, 255, 255, 0.7) 0%, transparent 50%);
            color: var(--text-main);
            -webkit-tap-highlight-color: transparent;
            -webkit-touch-callout: none;
        }
        .neo-card {
            background: var(--card-surface);
            border-radius: 28px;
            box-shadow: var(--neo-shadow);
            border: 1px solid rgba(255, 255, 255, 0.8);
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .neo-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 16px 36px -6px rgba(148, 163, 184, 0.38);
        }
        .neo-pill {
            background: #ffffff;
            border-radius: 9999px;
            box-shadow: var(--neo-convex);
            border: 1px solid rgba(255, 255, 255, 0.9);
        }
        .neo-well {
            background: #e2e8f0;
            border-radius: 20px;
            box-shadow: inset 2px 2px 5px rgba(148, 163, 184, 0.3), inset -2px -2px 5px rgba(255, 255, 255, 0.8);
        }
        .bottom-dock {
            background: rgba(255, 255, 255, 0.88);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border-radius: 34px;
            box-shadow: 0 12px 40px -8px rgba(100, 116, 139, 0.35);
            border: 1px solid rgba(255, 255, 255, 0.9);
        }
        .nav-tab.active {
            background: var(--dark-btn);
            color: #ffffff;
            box-shadow: 0 8px 18px -2px rgba(24, 29, 40, 0.3);
        }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 9999px; }
    </style>
</head>
<body class="min-h-screen pb-36 select-none">

    <!-- ⏳ اسپلش اسکرین نقره‌ای لوکس -->
    <div id="loadingScreen" class="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#e9edf3] transition-all duration-500 px-6">
        <div class="w-20 h-20 rounded-[28px] bg-white flex items-center justify-center text-4xl shadow-[0_15px_35px_rgba(148,163,184,0.35)] border border-white animate-pulse">
            🦆
        </div>
        <h2 class="text-slate-800 font-black text-base mt-6 tracking-wide flex items-center gap-2">
            <span>PEARL STORE</span>
            <span class="w-2 h-2 rounded-full bg-slate-800 animate-ping"></span>
        </h2>
        <p class="text-slate-500 text-xs mt-1.5 font-medium">در حال همگام‌سازی خدمات تلگرام...</p>
        <div class="w-48 h-1.5 bg-slate-200 rounded-full overflow-hidden mt-5 shadow-inner">
            <div id="loadingProgressBar" class="h-full bg-slate-800 transition-all duration-150" style="width: 5%"></div>
        </div>
        <span id="loadingPercent" class="text-[11px] font-bold text-slate-400 mt-2">0%</span>
    </div>

    <!-- 🚀 صفحه Onboarding / معرفی شبیه عکس ارسالی -->
    <div id="welcomeScreen" class="fixed inset-0 z-40 hidden flex items-center justify-center bg-[#e9edf3]/90 backdrop-blur-xl transition-all duration-500 p-5 opacity-0 scale-95">
        <div class="w-full max-w-sm neo-card p-6 flex flex-col items-center text-center space-y-5">
            <div class="w-16 h-16 rounded-2xl bg-white shadow-md flex items-center justify-center text-3xl border border-slate-100">
                🦆
            </div>
            <div>
                <span class="text-[10px] font-black tracking-widest text-slate-400 uppercase">PEARL STORE</span>
                <h2 class="text-base font-black text-slate-900 mt-0.5">به فروشگاه خدمات تلگرام خوش آمدید</h2>
                <p class="text-xs text-slate-500 mt-1">سریع‌ترین مرجع استارز، پرمیوم، بوست و گیفت</p>
            </div>

            <div class="w-full space-y-2 text-right text-xs">
                <div class="p-3 rounded-2xl bg-[#f4f7fb] border border-slate-200/60 flex items-center gap-3">
                    <span class="text-xl">🎁</span>
                    <div>
                        <p class="font-bold text-slate-800">اجاره گیفت‌های ارزشمند</p>
                        <p class="text-[10px] text-slate-500">تخفیف‌های بالای ۵۰٪ با شماره‌های خاص</p>
                    </div>
                </div>
                <div class="p-3 rounded-2xl bg-[#f4f7fb] border border-slate-200/60 flex items-center gap-3">
                    <span class="text-xl">💎</span>
                    <div>
                        <p class="font-bold text-slate-800">اشتراک پرمیوم و استارز</p>
                        <p class="text-[10px] text-slate-500">تحویل فوری با بهترین نرخ بازار</p>
                    </div>
                </div>
                <div class="p-3 rounded-2xl bg-[#f4f7fb] border border-slate-200/60 flex items-center gap-3">
                    <span class="text-xl">🚀</span>
                    <div>
                        <p class="font-bold text-slate-800">خدمات بوست، اکانت و کانال</p>
                        <p class="text-[10px] text-slate-500">ارتقای سطح و پایداری کانال‌های تلگرامی</p>
                    </div>
                </div>
            </div>

            <button id="enterStoreBtn" class="w-full py-3.5 bg-[#181d28] hover:bg-black text-white font-black text-xs rounded-2xl transition shadow-[0_10px_25px_rgba(24,29,40,0.3)] flex items-center justify-center gap-2">
                <span>بزن بریم</span>
                <i class="fa-solid fa-arrow-left text-xs"></i>
            </button>
        </div>
    </div>

    <!-- هدر سایت -->
    <header class="sticky top-0 z-30 bg-[#e9edf3]/80 backdrop-blur-xl border-b border-slate-200/60 px-4 py-3">
        <div class="max-w-xl mx-auto flex items-center justify-between">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-2xl bg-white text-slate-800 flex items-center justify-center text-xl font-black shadow-[0_6px_16px_rgba(148,163,184,0.3)] border border-white">
                    🦆
                </div>
                <div>
                    <h1 class="text-xs text-slate-400 font-extrabold uppercase tracking-wider">PEARL STORE</h1>
                    <p id="topGreeting" class="text-sm font-black text-slate-800">مرجع خدمات تلگرام</p>
                </div>
            </div>

            <a id="headerSupportLink" href="https://t.me/Zanjani_a" class="px-3.5 py-1.5 rounded-full bg-white text-slate-700 text-xs font-bold border border-slate-200 shadow-sm transition hover:bg-slate-50 flex items-center gap-1.5">
                <i class="fa-brands fa-telegram text-sky-500"></i>
                <span>پشتیبانی</span>
            </a>
        </div>
    </header>

    <!-- محفظه صفحات اصلی (Views) -->
    <main class="max-w-xl mx-auto px-4 mt-4 space-y-4">

        <!-- 🏠 ۱. تب خانه (ویترین و دسته‌بندی‌ها شبیه عکس ۲ و ۳) -->
        <section id="view-home" class="space-y-4">
            
            <!-- بنر مناسبتی (در صورت فعال بودن) -->
            <div id="promoBanner" class="hidden neo-card p-4 bg-gradient-to-r from-amber-50 to-white border-amber-200 flex items-center justify-between">
                <div class="flex items-center gap-2">
                    <i class="fa-solid fa-bullhorn text-amber-500 text-sm"></i>
                    <span id="promoBannerText" class="text-xs font-bold text-slate-700"></span>
                </div>
            </div>

            <!-- دسته‌بندی خدمات (Services Grid شبیه عکس دوم) -->
            <div>
                <div class="flex items-center justify-between mb-3 px-1">
                    <h3 class="text-sm font-black text-slate-800">دسته‌بندی خدمات</h3>
                    <span class="text-[10px] font-bold text-slate-400">PEARL STORE</span>
                </div>

                <div class="grid grid-cols-3 gap-3">
                    <div onclick="openCategoryTab('gift')" class="neo-card p-4 flex flex-col items-center justify-center text-center cursor-pointer">
                        <span class="text-3xl mb-1.5">🎁</span>
                        <span class="text-xs font-black text-slate-800">Gift</span>
                    </div>
                    <div onclick="openCategoryTab('stars')" class="neo-card p-4 flex flex-col items-center justify-center text-center cursor-pointer">
                        <span class="text-3xl mb-1.5">⭐</span>
                        <span class="text-xs font-black text-slate-800">Stars</span>
                    </div>
                    <div onclick="openCategoryTab('premium')" class="neo-card p-4 flex flex-col items-center justify-center text-center cursor-pointer">
                        <span class="text-3xl mb-1.5">💎</span>
                        <span class="text-xs font-black text-slate-800">Premium</span>
                    </div>
                    <div onclick="openCategoryTab('boost')" class="neo-card p-4 flex flex-col items-center justify-center text-center cursor-pointer">
                        <span class="text-3xl mb-1.5">🚀</span>
                        <span class="text-xs font-black text-slate-800">Boost</span>
                    </div>
                    <div onclick="openCategoryTab('account')" class="neo-card p-4 flex flex-col items-center justify-center text-center cursor-pointer">
                        <span class="text-3xl mb-1.5">📲</span>
                        <span class="text-xs font-black text-slate-800">Account</span>
                    </div>
                    <div onclick="openCategoryTab('channel')" class="neo-card p-4 flex flex-col items-center justify-center text-center cursor-pointer">
                        <span class="text-3xl mb-1.5">📢</span>
                        <span class="text-xs font-black text-slate-800">Channel</span>
                    </div>
                </div>
            </div>

            <!-- خدمات ویژه (Featured Services شبیه عکس سوم) -->
            <div class="space-y-2.5 pt-2">
                <div class="flex items-center justify-between px-1 mb-1">
                    <h3 class="text-sm font-black text-slate-800">خدمات ویژه</h3>
                    <span class="text-[10px] font-bold text-slate-400">PEARL SHOP</span>
                </div>
                
                <div class="neo-card p-3.5 flex items-center justify-between">
                    <div class="flex items-center gap-3">
                        <div class="w-11 h-11 rounded-2xl bg-[#eef2f7] flex items-center justify-center text-2xl shadow-inner">💎</div>
                        <div>
                            <h4 class="text-xs font-black text-slate-800">Telegram Premium</h4>
                            <p class="text-[10px] text-slate-500 font-medium">انتخاب و مشاهده قیمت</p>
                        </div>
                    </div>
                    <button onclick="openCategoryTab('premium')" class="px-4 py-2 rounded-xl bg-[#e2cc97] hover:bg-[#d8c086] text-slate-900 font-black text-xs transition shadow-sm">مشاهده</button>
                </div>

                <div class="neo-card p-3.5 flex items-center justify-between">
                    <div class="flex items-center gap-3">
                        <div class="w-11 h-11 rounded-2xl bg-[#eef2f7] flex items-center justify-center text-2xl shadow-inner">⭐</div>
                        <div>
                            <h4 class="text-xs font-black text-slate-800">Telegram Stars</h4>
                            <p class="text-[10px] text-slate-500 font-medium">انتخاب تعداد استارز</p>
                        </div>
                    </div>
                    <button onclick="openCategoryTab('stars')" class="px-4 py-2 rounded-xl bg-[#e2cc97] hover:bg-[#d8c086] text-slate-900 font-black text-xs transition shadow-sm">مشاهده</button>
                </div>

                <div class="neo-card p-3.5 flex items-center justify-between">
                    <div class="flex items-center gap-3">
                        <div class="w-11 h-11 rounded-2xl bg-[#eef2f7] flex items-center justify-center text-2xl shadow-inner">🎁</div>
                        <div>
                            <h4 class="text-xs font-black text-slate-800">Telegram Gift</h4>
                            <p class="text-[10px] text-slate-500 font-medium">انتخاب و اجاره هدیه</p>
                        </div>
                    </div>
                    <button onclick="openCategoryTab('gift')" class="px-4 py-2 rounded-xl bg-[#e2cc97] hover:bg-[#d8c086] text-slate-900 font-black text-xs transition shadow-sm">مشاهده</button>
                </div>

                <div class="neo-card p-3.5 flex items-center justify-between">
                    <div class="flex items-center gap-3">
                        <div class="w-11 h-11 rounded-2xl bg-[#eef2f7] flex items-center justify-center text-2xl shadow-inner">🚀</div>
                        <div>
                            <h4 class="text-xs font-black text-slate-800">Channel Boost</h4>
                            <p class="text-[10px] text-slate-500 font-medium">بوست اختصاصی برای کانال</p>
                        </div>
                    </div>
                    <button onclick="openCategoryTab('boost')" class="px-4 py-2 rounded-xl bg-[#e2cc97] hover:bg-[#d8c086] text-slate-900 font-black text-xs transition shadow-sm">مشاهده</button>
                </div>

                <div class="neo-card p-3.5 flex items-center justify-between">
                    <div class="flex items-center gap-3">
                        <div class="w-11 h-11 rounded-2xl bg-[#eef2f7] flex items-center justify-center text-2xl shadow-inner">📲</div>
                        <div>
                            <h4 class="text-xs font-black text-slate-800">Virtual Account</h4>
                            <p class="text-[10px] text-slate-500 font-medium">خدمات اکانت مجازی</p>
                        </div>
                    </div>
                    <button onclick="openCategoryTab('account')" class="px-4 py-2 rounded-xl bg-[#e2cc97] hover:bg-[#d8c086] text-slate-900 font-black text-xs transition shadow-sm">مشاهده</button>
                </div>

                <div class="neo-card p-3.5 flex items-center justify-between">
                    <div class="flex items-center gap-3">
                        <div class="w-11 h-11 rounded-2xl bg-[#eef2f7] flex items-center justify-center text-2xl shadow-inner">📢</div>
                        <div>
                            <h4 class="text-xs font-black text-slate-800">Channel Services</h4>
                            <p class="text-[10px] text-slate-500 font-medium">ممبر، سین و خدمات اختصاصی</p>
                        </div>
                    </div>
                    <button onclick="openCategoryTab('channel')" class="px-4 py-2 rounded-xl bg-[#e2cc97] hover:bg-[#d8c086] text-slate-900 font-black text-xs transition shadow-sm">مشاهده</button>
                </div>
            </div>
        </section>

        <!-- 🎁 ۲. تب مارکت گیفت‌ها -->
        <section id="view-gifts" class="hidden space-y-3">
            <div class="neo-card p-3 flex items-center justify-between gap-2">
                <div class="relative flex-1">
                    <i class="fa-solid fa-magnifying-glass absolute right-3 top-2.5 text-slate-400 text-xs"></i>
                    <input type="text" id="searchInput" placeholder="جستجوی نام یا شماره گیفت..." 
                           class="w-full bg-[#f1f5f9] border border-slate-200 rounded-xl pr-8 pl-3 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-slate-400">
                </div>
                <button onclick="openModal()" class="px-3 py-1.5 rounded-xl bg-white text-xs font-bold text-slate-700 border border-slate-200 shadow-sm flex items-center gap-1.5 whitespace-nowrap">
                    <span id="selectedColText">کالکشن‌ها</span>
                    <i class="fa-solid fa-chevron-down text-[9px] text-slate-400"></i>
                </button>
            </div>

            <div class="flex items-center gap-2 overflow-x-auto pb-1">
                <button onclick="filterType('all', this)" class="type-btn active px-4 py-1.5 rounded-full text-xs font-black bg-[#181d28] text-white whitespace-nowrap shadow-sm">همه (__TOTAL_COUNT__)</button>
                <button onclick="filterType('rare', this)" class="type-btn px-4 py-1.5 rounded-full text-xs font-bold bg-white text-slate-600 border border-slate-200 whitespace-nowrap shadow-sm">💎 کمیاب‌ها</button>
                <button onclick="filterType('favs', this)" class="type-btn px-4 py-1.5 rounded-full text-xs font-bold bg-white text-slate-600 border border-slate-200 whitespace-nowrap shadow-sm flex items-center gap-1.5">
                    <i class="fa-solid fa-heart text-rose-500 text-[10px]"></i> (<span id="favCount">0</span>)
                </button>
            </div>

            <div id="dealsGrid" class="grid grid-cols-2 gap-3"></div>
        </section>

        <!-- ⚡ ۳. تب خدمات و محصولات سفارشی (Stars, Premium, Boost, Account, Channel) -->
        <section id="view-services" class="hidden space-y-4">
            <!-- زیرتب‌های خدمات -->
            <div class="flex items-center gap-1.5 overflow-x-auto pb-1">
                <button onclick="switchServiceSubTab('stars')" id="subtab-stars" class="service-subtab-btn px-4 py-2 rounded-full text-xs font-black bg-[#181d28] text-white whitespace-nowrap shadow-sm">استارز</button>
                <button onclick="switchServiceSubTab('premium')" id="subtab-premium" class="service-subtab-btn px-4 py-2 rounded-full text-xs font-bold bg-white text-slate-600 border border-slate-200 whitespace-nowrap shadow-sm">پرمیوم</button>
                <button onclick="switchServiceSubTab('boost')" id="subtab-boost" class="service-subtab-btn px-4 py-2 rounded-full text-xs font-bold bg-white text-slate-600 border border-slate-200 whitespace-nowrap shadow-sm">بوست کانال</button>
                <button onclick="switchServiceSubTab('account')" id="subtab-account" class="service-subtab-btn px-4 py-2 rounded-full text-xs font-bold bg-white text-slate-600 border border-slate-200 whitespace-nowrap shadow-sm">اکانت مجازی</button>
                <button onclick="switchServiceSubTab('channel')" id="subtab-channel" class="service-subtab-btn px-4 py-2 rounded-full text-xs font-bold bg-white text-slate-600 border border-slate-200 whitespace-nowrap shadow-sm">خدمات کانال</button>
            </div>

            <!-- بخش استارز -->
            <div id="subview-stars" class="space-y-3">
                <div class="neo-card p-4 space-y-3">
                    <h4 class="text-xs font-bold text-slate-700">⭐ تعداد دلخواه استارز:</h4>
                    <input type="number" id="customStarsInput" min="50" placeholder="تعداد استارز (از ۵۰ به بالا)..." class="w-full bg-[#f1f5f9] border border-slate-200 rounded-xl px-3.5 py-2.5 text-xs text-slate-900 font-bold focus:outline-none">
                    <div id="customStarsCalcBox" class="p-3 rounded-xl bg-slate-100 flex items-center justify-between hidden">
                        <span class="text-xs text-slate-500 font-medium">مبلغ قابل پرداخت:</span>
                        <span id="customStarsPrice" class="text-xs font-black text-slate-900">0 تومان</span>
                    </div>
                </div>
                <div id="starsPackagesList" class="space-y-2"></div>
                <button onclick="orderStars()" class="w-full py-3.5 bg-[#181d28] hover:bg-black text-white font-black text-xs rounded-2xl shadow-md transition">خرید استارز</button>
            </div>

            <!-- بخش پرمیوم -->
            <div id="subview-premium" class="hidden space-y-3">
                <div id="premiumOptionsList" class="space-y-2.5"></div>
                <button onclick="orderPremium()" class="w-full py-3.5 bg-[#181d28] hover:bg-black text-white font-black text-xs rounded-2xl shadow-md transition">خرید تلگرام پرمیوم</button>
            </div>

            <!-- بخش محصولات داینامیک ادمین (بوست، اکانت مجازی، خدمات کانال) -->
            <div id="subview-custom" class="hidden space-y-2.5">
                <div id="customServicesContainer" class="space-y-2.5"></div>
            </div>
        </section>

        <!-- 👤 ۴. تب پروفایل کاربری (دقیقاً مطابق عکس اول ارسالی) -->
        <section id="view-profile" class="hidden space-y-4">
            <div class="neo-card p-6 flex flex-col items-center text-center space-y-4">
                
                <!-- آواتار نشان شطرنج با هاله مرواریدی و طلایی -->
                <div class="w-24 h-24 rounded-full bg-gradient-to-b from-[#e8cf9b] to-[#c7a969] flex items-center justify-center shadow-lg border-4 border-white">
                    <span id="profileAvatarIcon" class="text-4xl filter drop-shadow">♟️</span>
                </div>

                <div>
                    <h2 id="profileName" class="text-base font-black text-slate-900">Ali</h2>
                    <p id="profileUsername" class="text-xs text-slate-500 font-semibold dir-ltr mt-0.5">@Zanjani_a</p>
                </div>

                <div class="w-full pt-4 border-t border-slate-100 space-y-3.5 text-xs">
                    <div class="flex items-center justify-between">
                        <span class="text-slate-700 font-bold">شناسه کاربر</span>
                        <span id="profileUserId" class="font-bold text-slate-900 font-mono tracking-wider">649632759</span>
                    </div>
                    <div class="flex items-center justify-between">
                        <span class="text-slate-700 font-bold">وضعیت حساب</span>
                        <span class="font-bold text-emerald-600">فعال</span>
                    </div>
                    <div class="flex items-center justify-between">
                        <span class="text-slate-700 font-bold">سبد خرید</span>
                        <span id="profileCartCount" class="font-bold text-slate-900">0 قلم در سبد</span>
                    </div>
                </div>

                <a id="profileSupportBtn" href="https://t.me/Zanjani_a" class="w-full py-3 rounded-2xl bg-[#f1f5f9] hover:bg-slate-200 text-slate-800 font-bold text-xs flex items-center justify-center gap-2 border border-slate-200 transition">
                    <i class="fa-brands fa-telegram text-sky-500 text-sm"></i>
                    <span>ارتباط با پشتیبانی</span>
                </a>
            </div>
        </section>

    </main>

    <!-- 🛍️ نوار پاپ‌آپ خودکار سبد خرید -->
    <div id="floatingCartBar" class="fixed bottom-20 inset-x-4 max-w-xl mx-auto z-40 bg-white/95 backdrop-blur-xl border border-slate-200 p-3.5 rounded-2xl shadow-2xl transition-all duration-300 transform translate-y-36 opacity-0 space-y-2">
        <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
                <div class="w-9 h-9 rounded-xl bg-[#181d28] text-white flex items-center justify-center font-black text-xs shadow-md">
                    <span id="cartCountBadge">0</span>
                </div>
                <div>
                    <span class="text-[10px] text-slate-400 font-bold block">سبد خرید شما</span>
                    <span id="cartTotalPrice" class="text-xs font-black text-slate-900">0 تومان</span>
                </div>
            </div>
            <div class="flex items-center gap-2">
                <button onclick="clearCart()" class="p-2 text-slate-400 hover:text-rose-500 text-xs">
                    <i class="fa-solid fa-trash-can"></i>
                </button>
                <button onclick="checkoutCart()" class="py-2.5 px-4 rounded-xl bg-[#181d28] hover:bg-black text-white text-xs font-black flex items-center gap-1.5 shadow-md">
                    <span>ثبت سفارش</span>
                    <i class="fa-solid fa-arrow-left text-[10px]"></i>
                </button>
            </div>
        </div>
    </div>

    <!-- منوی شناور پایینی (Bottom Dock شبیه عکس سوم) -->
    <nav class="fixed bottom-3 inset-x-4 max-w-xl mx-auto z-40 bottom-dock px-3 py-2 flex items-center justify-around">
        <button onclick="switchView('home')" id="nav-home" class="nav-tab active px-5 py-2 rounded-2xl flex flex-col items-center gap-1 text-[10px] font-bold text-slate-500 transition">
            <i class="fa-solid fa-house text-sm"></i>
            <span>خانه</span>
        </button>
        <button onclick="switchView('gifts')" id="nav-gifts" class="nav-tab px-5 py-2 rounded-2xl flex flex-col items-center gap-1 text-[10px] font-bold text-slate-500 transition">
            <i class="fa-solid fa-gift text-sm"></i>
            <span>گیفت‌ها</span>
        </button>
        <button onclick="switchView('services')" id="nav-services" class="nav-tab px-5 py-2 rounded-2xl flex flex-col items-center gap-1 text-[10px] font-bold text-slate-500 transition">
            <i class="fa-solid fa-bolt text-sm"></i>
            <span>سفارش‌ها</span>
        </button>
        <button onclick="switchView('profile')" id="nav-profile" class="nav-tab px-5 py-2 rounded-2xl flex flex-col items-center gap-1 text-[10px] font-bold text-slate-500 transition">
            <i class="fa-solid fa-chess-pawn text-sm"></i>
            <span>حساب</span>
        </button>
    </nav>

    <!-- مودال انتخاب کالکشن -->
    <div id="collectionModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm hidden">
        <div class="neo-card w-full max-w-md rounded-3xl overflow-hidden flex flex-col max-h-[80vh]">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-slate-100">
                <button onclick="closeModal()" class="w-7 h-7 rounded-full bg-slate-100 text-slate-500 flex items-center justify-center"><i class="fa-solid fa-xmark text-xs"></i></button>
                <h3 class="text-xs font-black text-slate-800">کالکشن‌های گیفت</h3>
                <div class="w-7"></div>
            </div>
            <div class="p-3 border-b border-slate-100 flex items-center justify-between text-xs">
                <button onclick="selectAllCollections()" class="text-slate-800 font-bold">انتخاب همه</button>
                <button onclick="clearCollectionSelection()" class="text-slate-400 hover:text-rose-500">پاک کردن</button>
            </div>
            <div id="modalCollectionsList" class="p-3 space-y-1.5 overflow-y-auto flex-1"></div>
            <div class="p-3 border-t border-slate-100 bg-slate-50">
                <button onclick="applyCollectionModal()" class="w-full py-2.5 bg-[#181d28] text-white text-xs font-black rounded-xl">اعمال فیلتر</button>
            </div>
        </div>
    </div>

    <script>
        let tgUser = null;
        if (window.Telegram && window.Telegram.WebApp) {
            try {
                window.Telegram.WebApp.ready();
                window.Telegram.WebApp.expand();
                tgUser = window.Telegram.WebApp.initDataUnsafe?.user || null;
                if (tgUser) {
                    const name = tgUser.first_name || tgUser.username || "کاربر گرامی";
                    document.getElementById('topGreeting').innerText = `سلام ${name} 👋`;
                    document.getElementById('profileName').innerText = `${tgUser.first_name || ''} ${tgUser.last_name || ''}`.trim() || name;
                    document.getElementById('profileUsername').innerText = tgUser.username ? `@${tgUser.username}` : 'بدون یوزرنیم';
                    document.getElementById('profileUserId').innerText = tgUser.id || '649632759';
                }
            } catch(e) {}
        }

        function triggerHaptic(type = 'light') {
            try {
                if (window.Telegram?.WebApp?.HapticFeedback) {
                    if (type === 'selection') window.Telegram.WebApp.HapticFeedback.selectionChanged();
                    else window.Telegram.WebApp.HapticFeedback.impactOccurred(type);
                }
            } catch(e) {}
        }

        function openTgLink(url) {
            const cleanUrl = url.replace('https://t.me/@', 'https://t.me/');
            if (window.Telegram?.WebApp?.openTelegramLink) {
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
            prem3: 620000,
            prem6: 950000,
            prem12: 1690000,
            giftMonthlyPrice: 160000,
            adminTg: 'Zanjani_a',
            announcementText: 'تخفیف ویژه جشنواره آغاز شد',
            announcementActive: true,
            couponCode: 'PEARL',
            couponPercent: 10,
            customServices: [
                { id: "boost-1", category: "boost", title: "بوست ۱ لول (۷ روزه)", price: 45000, desc: "تحویل آنی با لینک کانال" },
                { id: "boost-2", category: "boost", title: "بوست ۴ لول (۱ ماهه)", price: 180000, desc: "پایداری کامل و کیفیت عالی" },
                { id: "acc-1", category: "account", title: "اکانت مجازی اختصاصی آمریکا", price: 85000, desc: "شماره اختصاصی بدون ریپورت" },
                { id: "ch-1", category: "channel", title: "۱۰۰۰ ممبر واقعی کانال", price: 95000, desc: "سرعت بالا با ریزش حداقل" }
            ]
        };

        let SETTINGS = { ...DEFAULT_SETTINGS };
        let currentView = 'home';
        let currentServiceSubTab = 'stars';
        let selectedType = 'all';
        let selectedCollections = new Set();
        let tempSelectedCollections = new Set();

        let selectedStarsCount = 50;
        let selectedPremiumMonths = 12;
        const STARS_PACKAGES = [50, 75, 100, 150, 250, 350, 500, 1000, 2500, 5000];

        let favorites = [];
        try { favorites = JSON.parse(localStorage.getItem('duck_favs') || '[]'); } catch(e){}

        let cart = [];
        try { cart = JSON.parse(localStorage.getItem('duck_cart') || '[]'); } catch(e){}

        function switchView(viewName) {
            triggerHaptic('selection');
            currentView = viewName;
            ['home', 'gifts', 'services', 'profile'].forEach(v => {
                document.getElementById(`view-${v}`).classList.add('hidden');
                document.getElementById(`nav-${v}`).classList.remove('active');
            });
            document.getElementById(`view-${viewName}`).classList.remove('hidden');
            document.getElementById(`nav-${viewName}`).classList.add('active');
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }

        function openCategoryTab(cat) {
            if (cat === 'gift') {
                switchView('gifts');
            } else {
                switchView('services');
                switchServiceSubTab(cat);
            }
        }

        function switchServiceSubTab(tab) {
            triggerHaptic('selection');
            currentServiceSubTab = tab;
            document.querySelectorAll('.service-subtab-btn').forEach(btn => {
                btn.classList.remove('bg-[#181d28]', 'text-white', 'font-black');
                btn.classList.add('bg-white', 'text-slate-600', 'font-bold');
            });

            const activeBtn = document.getElementById(`subtab-${tab}`);
            if (activeBtn) {
                activeBtn.classList.add('bg-[#181d28]', 'text-white', 'font-black');
                activeBtn.classList.remove('bg-white', 'text-slate-600');
            }

            document.getElementById('subview-stars').classList.add('hidden');
            document.getElementById('subview-premium').classList.add('hidden');
            document.getElementById('subview-custom').classList.add('hidden');

            if (tab === 'stars') {
                document.getElementById('subview-stars').classList.remove('hidden');
            } else if (tab === 'premium') {
                document.getElementById('subview-premium').classList.remove('hidden');
            } else {
                document.getElementById('subview-custom').classList.remove('hidden');
                renderCustomServices(tab);
            }
        }

        async function fetchCloudSettings() {
            try {
                const res = await fetch(`${WORKER_URL}/api/settings`);
                if (res.ok) {
                    const data = await res.json();
                    if (data && typeof data === 'object') {
                        SETTINGS = { ...DEFAULT_SETTINGS, ...data };
                    }
                }
            } catch(e) {}
            updateUI();
        }

        function updateUI() {
            const adminUser = (SETTINGS.adminTg || 'Zanjani_a').replace('@', '').trim();
            document.getElementById('headerSupportLink').href = `https://t.me/${adminUser}`;
            document.getElementById('profileSupportBtn').href = `https://t.me/${adminUser}`;

            const promo = document.getElementById('promoBanner');
            if (SETTINGS.announcementActive && SETTINGS.announcementText) {
                document.getElementById('promoBannerText').innerText = SETTINGS.announcementText;
                promo.classList.remove('hidden');
            } else {
                promo.classList.add('hidden');
            }

            renderCards(getFilteredDeals());
            renderStarsPackages();
            renderPremiumOptions();
            updateCartUI();
        }

        // ================= استارز =================
        function renderStarsPackages() {
            const container = document.getElementById('starsPackagesList');
            container.innerHTML = STARS_PACKAGES.map(qty => {
                const totalToman = (qty * SETTINGS.ratePerStar).toLocaleString('en-US');
                return `
                <div onclick="selectStarsPackage(${qty})" class="neo-card p-3 flex items-center justify-between cursor-pointer hover:border-slate-400">
                    <span class="text-xs font-bold text-slate-800">⭐ ${qty} Stars</span>
                    <span class="text-xs font-black text-slate-900">${totalToman} ت</span>
                </div>
                `;
            }).join('');
        }

        function selectStarsPackage(qty) {
            triggerHaptic('selection');
            selectedStarsCount = qty;
            const total = (qty * SETTINGS.ratePerStar).toLocaleString('en-US');
            document.getElementById('customStarsInput').value = qty;
            document.getElementById('customStarsPrice').innerText = `${total} تومان`;
            document.getElementById('customStarsCalcBox').classList.remove('hidden');
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
        });

        function orderStars() {
            triggerHaptic('heavy');
            const adminUser = (SETTINGS.adminTg || 'Zanjani_a').replace('@', '').trim();
            const total = (selectedStarsCount * SETTINGS.ratePerStar).toLocaleString('en-US');
            const nl = String.fromCharCode(10);
            const msg = encodeURIComponent(
                "سلام، درخواست خرید استارز تلگرام دارم:" + nl + nl +
                getBuyerDetailsText() + nl + nl +
                "تعداد: " + selectedStarsCount + " Stars" + nl +
                "مبلغ: " + total + " تومان"
            );
            openTgLink("https://t.me/" + adminUser + "?text=" + msg);
        }

        // ================= پرمیوم =================
        function renderPremiumOptions() {
            const container = document.getElementById('premiumOptionsList');
            const options = [
                { months: 12, label: '۱۲ ماهه (۱ ساله)', price: SETTINGS.prem12 },
                { months: 6, label: '۶ ماهه', price: SETTINGS.prem6 },
                { months: 3, label: '۳ ماهه', price: SETTINGS.prem3 }
            ];

            container.innerHTML = options.map(opt => {
                const isSelected = selectedPremiumMonths === opt.months;
                return `
                <div onclick="selectPremiumPlan(${opt.months})" class="neo-card p-3.5 flex items-center justify-between cursor-pointer ${isSelected ? 'border-slate-900 bg-slate-50' : ''}">
                    <span class="text-xs font-bold text-slate-800">${opt.label}</span>
                    <span class="text-xs font-black text-slate-900">${opt.price.toLocaleString('en-US')} تومان</span>
                </div>
                `;
            }).join('');
        }

        function selectPremiumPlan(m) {
            triggerHaptic('selection');
            selectedPremiumMonths = m;
            renderPremiumOptions();
        }

        function orderPremium() {
            triggerHaptic('heavy');
            const adminUser = (SETTINGS.adminTg || 'Zanjani_a').replace('@', '').trim();
            let price = SETTINGS.prem12;
            let title = '1 ساله';
            if (selectedPremiumMonths === 6) { price = SETTINGS.prem6; title = '6 ماهه'; }
            if (selectedPremiumMonths === 3) { price = SETTINGS.prem3; title = '3 ماهه'; }
            const nl = String.fromCharCode(10);
            const msg = encodeURIComponent(
                "سلام، درخواست خرید تلگرام پرمیوم دارم:" + nl + nl +
                getBuyerDetailsText() + nl + nl +
                "مدت اشتراک: " + title + nl +
                "مبلغ: " + price.toLocaleString('en-US') + " تومان"
            );
            openTgLink("https://t.me/" + adminUser + "?text=" + msg);
        }

        // ================= خدمات سفارشی داینامیک ادمین =================
        function renderCustomServices(category) {
            const container = document.getElementById('customServicesContainer');
            const list = (SETTINGS.customServices || []).filter(s => s.category === category);

            if (list.length === 0) {
                container.innerHTML = '<p class="text-xs text-slate-400 text-center py-6">موردی برای این بخش تعریف نشده است.</p>';
                return;
            }

            container.innerHTML = list.map(item => `
                <div class="neo-card p-3.5 flex items-center justify-between">
                    <div>
                        <h4 class="text-xs font-bold text-slate-900">${item.title}</h4>
                        <p class="text-[10px] text-slate-500 mt-0.5">${item.desc || ''}</p>
                        <span class="text-xs font-black text-slate-800 mt-1 block">${Number(item.price).toLocaleString('en-US')} تومان</span>
                    </div>
                    <button onclick='addToCartCustom(${JSON.stringify(item)})' class="px-3.5 py-1.5 rounded-xl bg-[#181d28] hover:bg-black text-white font-bold text-xs transition">
                        + خرید
                    </button>
                </div>
            `).join('');
        }

        function addToCartCustom(item) {
            triggerHaptic('selection');
            cart.push({ name: item.title, price: Number(item.price), type: 'custom' });
            localStorage.setItem('duck_cart', JSON.stringify(cart));
            updateCartUI();
        }

        // ================= گیفت‌ها و سبد خرید =================
        function renderCards(items) {
            const container = document.getElementById('dealsGrid');
            if (!container) return;
            if (items.length === 0) {
                container.innerHTML = '<div class="col-span-full py-12 text-center text-slate-400 text-xs font-bold">گیفتی پیدا نشد.</div>';
                return;
            }

            const giftPriceFormatted = Number(SETTINGS.giftMonthlyPrice || 160000).toLocaleString('en-US');

            container.innerHTML = items.map(deal => {
                const isFav = favorites.includes(deal.name);
                const isInCart = cart.some(c => c.name === deal.name);

                return `
                <div class="neo-card overflow-hidden flex flex-col justify-between ${isInCart ? 'border-slate-800' : ''}">
                    <div>
                        <div class="relative w-full h-36 bg-[#f4f7fb] flex items-center justify-center border-b border-slate-100">
                            ${deal.rarity ? `<span class="absolute top-2 left-2 px-2 py-0.5 rounded-md text-[9px] font-bold bg-white text-slate-800 shadow-sm border border-slate-200">${deal.rarity}</span>` : ''}
                            <button onclick="toggleFavorite('${deal.name}')" class="absolute top-2 right-2 w-7 h-7 rounded-full bg-white/80 shadow-sm flex items-center justify-center text-xs ${isFav ? 'text-rose-500' : 'text-slate-400'}">
                                <i class="fa-solid fa-heart"></i>
                            </button>
                            <img src="${deal.image_url}" alt="${deal.name}" class="w-24 h-24 object-contain" onerror="this.src='https://marketapp.org/favicon.ico'">
                        </div>
                        <div class="p-2.5">
                            <h4 class="text-xs font-bold text-slate-800 truncate text-center">${deal.name}</h4>
                            <span class="text-xs font-black text-slate-900 text-center block mt-1">${giftPriceFormatted} ت/ماه</span>
                        </div>
                    </div>
                    <div class="p-2.5 pt-0 grid grid-cols-2 gap-1.5">
                        <a href="${deal.tg_link}" target="_blank" class="py-1.5 text-center text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg text-xs font-bold transition">دیدن</a>
                        <button onclick='toggleCartGift(${JSON.stringify(deal)})' class="py-1.5 text-center ${isInCart ? 'bg-rose-500 text-white font-black' : 'bg-[#181d28] hover:bg-black text-white font-bold'} rounded-lg text-xs transition">
                            ${isInCart ? 'حذف' : 'اجاره'}
                        </button>
                    </div>
                </div>
                `;
            }).join('');
        }

        function toggleCartGift(deal) {
            triggerHaptic('selection');
            const idx = cart.findIndex(c => c.name === deal.name);
            if (idx > -1) {
                cart.splice(idx, 1);
            } else {
                cart.push({ name: deal.name, price: Number(SETTINGS.giftMonthlyPrice || 160000), tg_link: deal.tg_link, type: 'gift' });
            }
            localStorage.setItem('duck_cart', JSON.stringify(cart));
            updateCartUI();
            renderCards(getFilteredDeals());
        }

        function toggleFavorite(name) {
            triggerHaptic('medium');
            const idx = favorites.indexOf(name);
            if (idx > -1) favorites.splice(idx, 1);
            else favorites.push(name);
            localStorage.setItem('duck_favs', JSON.stringify(favorites));
            document.getElementById('favCount').innerText = favorites.length;
            renderCards(getFilteredDeals());
        }

        // پاپ‌آپ خودکار سبد خرید
        function updateCartUI() {
            const bar = document.getElementById('floatingCartBar');
            const count = cart.length;
            document.getElementById('cartCountBadge').innerText = count;
            document.getElementById('profileCartCount').innerText = `${count} قلم در سبد`;

            let total = 0;
            cart.forEach(item => { total += Number(item.price || 0); });
            document.getElementById('cartTotalPrice').innerText = `${total.toLocaleString('en-US')} تومان`;

            if (count > 0) {
                bar.classList.remove('translate-y-36', 'opacity-0');
                bar.classList.add('translate-y-0', 'opacity-100');
            } else {
                bar.classList.remove('translate-y-0', 'opacity-100');
                bar.classList.add('translate-y-36', 'opacity-0');
            }
        }

        function clearCart() {
            triggerHaptic('light');
            cart = [];
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
            if (cart.length === 0) return alert('سبد خرید شما خالی است!');
            const adminUser = (SETTINGS.adminTg || 'Zanjani_a').replace('@', '').trim();
            let total = 0;
            const nl = String.fromCharCode(10);
            const list = cart.map((c, i) => {
                total += Number(c.price || 0);
                return `${i + 1}. 🎁 ${c.name} (${Number(c.price).toLocaleString('en-US')} ت)`;
            }).join(nl);

            const msg = encodeURIComponent(
                "سلام، درخواست ثبت سفارش دارم:" + nl + nl +
                getBuyerDetailsText() + nl + nl +
                "اقلام سفارش (" + cart.length + " مورد):" + nl +
                list + nl + nl +
                "مبلغ کل: " + total.toLocaleString('en-US') + " تومان"
            );
            openTgLink("https://t.me/" + adminUser + "?text=" + msg);
        }

        // ================= کالکشن‌ها =================
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
                <div onclick="toggleModalCollection('${col.name}')" class="p-2.5 rounded-xl border ${isSelected ? 'border-slate-900 bg-slate-100' : 'border-slate-200'} flex items-center justify-between cursor-pointer">
                    <span class="text-xs font-bold text-slate-800">${col.name}</span>
                    <span class="text-[10px] text-slate-500">${col.count}</span>
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
            renderCards(getFilteredDeals());
        }

        function filterType(type, btn) {
            triggerHaptic('selection');
            selectedType = type;
            document.querySelectorAll('.type-btn').forEach(b => {
                b.classList.remove('bg-[#181d28]', 'text-white', 'font-black');
                b.classList.add('bg-white', 'text-slate-600', 'font-bold');
            });
            if (btn) {
                btn.classList.remove('bg-white', 'text-slate-600');
                btn.classList.add('bg-[#181d28]', 'text-white', 'font-black');
            }
            renderCards(getFilteredDeals());
        }

        function getFilteredDeals() {
            const q = (document.getElementById('searchInput')?.value || '').trim().toLowerCase();
            return DEALS.filter(d => {
                const match = d.name.toLowerCase().includes(q) || d.number.includes(q) || d.gift_title.toLowerCase().includes(q);
                if (!match) return false;
                if (selectedType === 'rare' && d.rarity === '') return false;
                if (selectedType === 'favs' && !favorites.includes(d.name)) return false;
                if (selectedCollections.size > 0 && selectedCollections.size < COLLECTIONS.length) {
                    if (!selectedCollections.has(d.gift_title)) return false;
                }
                return true;
            });
        }

        document.getElementById('searchInput').addEventListener('input', () => {
            renderCards(getFilteredDeals());
        });

        // ⏳ لودینگ نرم و انتقال به صفحه خوش‌آمدگویی
        let loadingProgress = 5;
        function startLoading() {
            const bar = document.getElementById('loadingProgressBar');
            const pct = document.getElementById('loadingPercent');
            const interval = setInterval(() => {
                loadingProgress += Math.floor(Math.random() * 15) + 10;
                if (loadingProgress >= 100) {
                    loadingProgress = 100;
                    clearInterval(interval);
                    if (bar) bar.style.width = '100%';
                    if (pct) pct.innerText = '100%';
                    setTimeout(() => {
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
                    }, 250);
                } else {
                    if (bar) bar.style.width = `${loadingProgress}%`;
                    if (pct) pct.innerText = `${loadingProgress}%`;
                }
            }, 80);
        }

        document.getElementById('enterStoreBtn').addEventListener('click', () => {
            triggerHaptic('heavy');
            const welcome = document.getElementById('welcomeScreen');
            if (welcome) {
                welcome.classList.add('opacity-0', 'scale-95', 'pointer-events-none');
                setTimeout(() => { welcome.style.display = 'none'; }, 400);
            }
        });

        // لود اولیه
        updateUI();
        fetchCloudSettings();
        startLoading();
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

    with open(CONFIG["EXPORT_HTML"], "w", encoding="utf-8") as f:
        f.write(html_content)

    with open(CONFIG["EXPORT_JSON"], "w", encoding="utf-8") as f:
        json.dump(deals, f, ensure_ascii=False, indent=2)


def send_telegram_package(deals: List[Dict[str, Any]]):
    token = CONFIG.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = CONFIG.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id: return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    gh_repo = CONFIG.get("GITHUB_REPOSITORY", "")
    pages_url = f"https://{gh_repo.split('/')[0]}.github.io/{gh_repo.split('/')[1]}/" if "/" in gh_repo else "https://zanjania0.github.io/duck-store/"

    rare_count = sum(1 for d in deals if d["rarity"])
    full_text = (
        f"🦆 <b>گزارش جدید فروشگاه Duck Store</b>\n"
        f"📅 <i>{timestamp}</i>\n\n"
        f"🌐 <b>ورود به فروشگاه:</b>\n👉 <a href='{pages_url}'>{pages_url}</a>\n\n"
        f"🎯 موجودی گیفت‌های فعال: {len(deals)} مورد (کمیاب: {rare_count})\n"
    )

    send_chunks_to_telegram(full_text, token, chat_id)
    send_telegram_csv_attachment(CONFIG["EXPORT_CSV"], token, chat_id, f"📊 فایل اکسل ۲۰۰ گیفت Duck Store ({timestamp})")


def send_chunks_to_telegram(text: str, token: str, chat_id: str):
    chunks = []
    current_chunk = ""
    for paragraph in text.split("\n\n"):
        if len(current_chunk) + len(paragraph) + 2 > 3800:
            chunks.append(current_chunk.strip())
            current_chunk = paragraph + "\n\n"
        else:
            current_chunk += paragraph + "\n\n"

    if current_chunk.strip(): chunks.append(current_chunk.strip())

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for part in chunks:
        payload = urllib.parse.urlencode({"chat_id": chat_id, "text": part, "parse_mode": "HTML", "disable_web_page_preview": "true"}).encode("utf-8")
        try:
            req = urllib.request.Request(url, data=payload)
            with urllib.request.urlopen(req, timeout=15): pass
            time.sleep(0.5)
        except Exception: pass


def send_telegram_csv_attachment(file_path: str, token: str, chat_id: str, caption: str):
    if not os.path.exists(file_path): return
    boundary = "----DuckStoreBoundaryXYZ"
    try:
        with open(file_path, "rb") as f: file_bytes = f.read()

        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="document"; filename="duck_store_gifts.csv"\r\n'
            f"Content-Type: text/csv\r\n\r\n"
        ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendDocument", data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        with urllib.request.urlopen(req, timeout=30): pass
    except Exception: pass


# ==========================================
# ⚡ موتور اسکرپر
# ==========================================
async def main():
    deals_found: List[Dict[str, Any]] = []
    seen_links: Set[str] = set()
    browser = None

    print("\n" + "═" * 65)
    print("  🦆 PEARL STORE TURBO SCRAPER (SOFT NEUMORPHIC LUXURY) 🦆")
    print("═" * 65 + "\n")

    launch_args = ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-accelerated-2d-canvas", "--no-first-run", "--no-zygote"]

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True, args=launch_args)
            page = await browser.new_page()

            print("🌐 بارگذاری اولیه مارکت...")
            await page.goto(CONFIG["TARGET_URL"], wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)

            scroll_attempts = 0
            while len(deals_found) < CONFIG["TARGET_DEALS_COUNT"] and scroll_attempts < CONFIG["MAX_SCROLL_ATTEMPTS"]:
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
                    if not href: continue

                    full_link = href if href.startswith("http") else f"{CONFIG['BASE_DOMAIN']}{href if href.startswith('/') else '/' + href}"
                    if full_link in seen_links: continue

                    text = c.get("text", "")
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
                                if not l.startswith("Days:") and not l.startswith("-") and not l.startswith("#")
                                and l.lower() not in ["per day", "min. price"] and not re.match(r"^\d+(\.\d+)?$", l)
                            ]

                            gift_name = name_candidates[0] if name_candidates else "NFT Gift"
                            deal = {
                                "name": f"{gift_name} #{item_num}",
                                "gift_title": gift_name,
                                "number": str(item_num),
                                "discount": f"-{discount_val}%",
                                "discount_num": discount_val,
                                "price_per_day": "0.01",
                                "days_range": days_range,
                                "tg_link": generate_tg_nft_link(gift_name, item_num),
                                "market_link": full_link,
                                "image_url": c.get("img") or "https://marketapp.org/favicon.ico",
                                "rarity": detect_rarity_badge(item_num),
                            }

                            seen_links.add(full_link)
                            deals_found.append(deal)

                            if len(deals_found) >= CONFIG["TARGET_DEALS_COUNT"]: break
                    else:
                        seen_links.add(full_link)

                if len(deals_found) >= CONFIG["TARGET_DEALS_COUNT"]: break
                await page.evaluate("window.scrollBy(0, window.innerHeight * 3);")
                await page.wait_for_timeout(350)

        finally:
            if browser:
                await browser.close()

        sorted_deals = list(reversed(deals_found))

        generate_duck_store_html(sorted_deals)

        try:
            with open(CONFIG["EXPORT_CSV"], "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["ردیف", "کالکشن", "نام گیفت", "شماره", "تخفیف", "کمیابی", "لینک تلگرام", "لینک MarketApp"])
                for idx, d in enumerate(sorted_deals, 1):
                    writer.writerow([idx, d["gift_title"], d["name"], d["number"], d["discount"], d["rarity"] or "معمولی", d["tg_link"], d["market_link"]])
        except Exception: pass

        print("\n⚡ فروشگاه با استایل لوکس مرواریدی و سیستم یکپارچه با موفقیت ساخته شد!")
        send_telegram_package(sorted_deals)


if __name__ == "__main__":
    asyncio.run(main())
