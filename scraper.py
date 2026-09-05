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
    """تولید وب‌سایت با معماری ماژولار، پروفایل کاربری و خدمات سفارشی ادمین"""
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
    <title>فروشگاه خدمات تلگرام</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #090a0f;
            --card-base: #11131c;
            --card-border: rgba(255, 255, 255, 0.06);
            --gold-accent: #f59e0b;
        }
        body {
            font-family: 'Vazirmatn', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-base);
            color: #f3f4f6;
            -webkit-tap-highlight-color: transparent;
            -webkit-touch-callout: none;
        }
        .store-card {
            background: var(--card-base);
            border: 1px solid var(--card-border);
            border-radius: 24px;
            transition: all 0.25s ease;
        }
        .store-card:hover {
            border-color: rgba(245, 158, 11, 0.35);
        }
        .dock-bar {
            background: rgba(14, 17, 26, 0.92);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 28px;
        }
        .nav-btn.active {
            background: #1e2233;
            color: #f59e0b;
        }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #222638; border-radius: 9999px; }
    </style>
</head>
<body class="min-h-screen pb-36 select-none">

    <!-- هدر سایت -->
    <header class="sticky top-0 z-30 bg-[#090a0f]/90 backdrop-blur-md border-b border-white/5 px-4 py-3">
        <div class="max-w-xl mx-auto flex items-center justify-between">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-2xl bg-gradient-to-tr from-amber-500 to-yellow-400 text-black flex items-center justify-center font-black text-xl shadow-lg shadow-amber-500/20">
                    👑
                </div>
                <div>
                    <h1 class="text-xs text-gray-400 font-bold uppercase tracking-wider">DUCK STORE</h1>
                    <p id="topGreeting" class="text-sm font-black text-white">مرجع خدمات تلگرام</p>
                </div>
            </div>

            <a id="headerSupportLink" href="https://t.me/Zanjani_a" class="px-3 py-1.5 rounded-xl bg-[#161926] text-gray-200 border border-white/10 text-xs font-bold transition flex items-center gap-1.5">
                <i class="fa-brands fa-telegram text-blue-400"></i>
                <span>پشتیبانی</span>
            </a>
        </div>
    </header>

    <!-- محفظه صفحات اصلی (Views) -->
    <main class="max-w-xl mx-auto px-4 mt-4 space-y-4">

        <!-- 🏠 تب اول: خانه و دسته‌بندی خدمات -->
        <section id="view-home" class="space-y-4">
            <!-- بنر مناسبتی -->
            <div id="promoBanner" class="hidden store-card p-4 border-amber-500/30 bg-gradient-to-r from-amber-500/10 to-transparent flex items-center justify-between">
                <div class="flex items-center gap-2">
                    <i class="fa-solid fa-bullhorn text-amber-400 text-xs"></i>
                    <span id="promoBannerText" class="text-xs font-bold text-amber-200"></span>
                </div>
            </div>

            <!-- گرید دسته‌بندی خدمات -->
            <div>
                <h3 class="text-sm font-black text-white mb-3 flex items-center gap-2">
                    <span>دسته‌بندی خدمات</span>
                </h3>
                <div class="grid grid-cols-3 gap-2.5">
                    <div onclick="openCategoryTab('gift')" class="store-card p-3.5 flex flex-col items-center justify-center text-center cursor-pointer hover:border-amber-500/50">
                        <span class="text-3xl mb-1.5">🎁</span>
                        <span class="text-xs font-bold text-white">Gift</span>
                    </div>
                    <div onclick="openCategoryTab('stars')" class="store-card p-3.5 flex flex-col items-center justify-center text-center cursor-pointer hover:border-amber-500/50">
                        <span class="text-3xl mb-1.5">⭐</span>
                        <span class="text-xs font-bold text-white">Stars</span>
                    </div>
                    <div onclick="openCategoryTab('premium')" class="store-card p-3.5 flex flex-col items-center justify-center text-center cursor-pointer hover:border-amber-500/50">
                        <span class="text-3xl mb-1.5">💎</span>
                        <span class="text-xs font-bold text-white">Premium</span>
                    </div>
                    <div onclick="openCategoryTab('boost')" class="store-card p-3.5 flex flex-col items-center justify-center text-center cursor-pointer hover:border-amber-500/50">
                        <span class="text-3xl mb-1.5">🚀</span>
                        <span class="text-xs font-bold text-white">Boost</span>
                    </div>
                    <div onclick="openCategoryTab('account')" class="store-card p-3.5 flex flex-col items-center justify-center text-center cursor-pointer hover:border-amber-500/50">
                        <span class="text-3xl mb-1.5">📲</span>
                        <span class="text-xs font-bold text-white">Account</span>
                    </div>
                    <div onclick="openCategoryTab('channel')" class="store-card p-3.5 flex flex-col items-center justify-center text-center cursor-pointer hover:border-amber-500/50">
                        <span class="text-3xl mb-1.5">📢</span>
                        <span class="text-xs font-bold text-white">Channel</span>
                    </div>
                </div>
            </div>

            <!-- خدمات ویژه -->
            <div class="space-y-2.5 pt-1">
                <h3 class="text-sm font-black text-white mb-2">خدمات ویژه</h3>
                
                <div class="store-card p-3.5 flex items-center justify-between">
                    <div class="flex items-center gap-3">
                        <div class="w-11 h-11 rounded-2xl bg-[#181b26] flex items-center justify-center text-xl">💎</div>
                        <div>
                            <h4 class="text-xs font-black text-white">Telegram Premium</h4>
                            <p class="text-[10px] text-gray-400">اشتراک رسمی ۳، ۶ و ۱۲ ماهه</p>
                        </div>
                    </div>
                    <button onclick="openCategoryTab('premium')" class="px-3.5 py-1.5 rounded-xl bg-amber-400 text-black font-black text-xs">مشاهده</button>
                </div>

                <div class="store-card p-3.5 flex items-center justify-between">
                    <div class="flex items-center gap-3">
                        <div class="w-11 h-11 rounded-2xl bg-[#181b26] flex items-center justify-center text-xl">⭐</div>
                        <div>
                            <h4 class="text-xs font-black text-white">Telegram Stars</h4>
                            <p class="text-[10px] text-gray-400">تحویل سریع استارز تلگرام</p>
                        </div>
                    </div>
                    <button onclick="openCategoryTab('stars')" class="px-3.5 py-1.5 rounded-xl bg-amber-400 text-black font-black text-xs">مشاهده</button>
                </div>

                <div class="store-card p-3.5 flex items-center justify-between">
                    <div class="flex items-center gap-3">
                        <div class="w-11 h-11 rounded-2xl bg-[#181b26] flex items-center justify-center text-xl">🎁</div>
                        <div>
                            <h4 class="text-xs font-black text-white">Telegram Gift</h4>
                            <p class="text-[10px] text-gray-400">اجاره گیفت با تخفیف ۵۰٪</p>
                        </div>
                    </div>
                    <button onclick="openCategoryTab('gift')" class="px-3.5 py-1.5 rounded-xl bg-amber-400 text-black font-black text-xs">مشاهده</button>
                </div>
            </div>
        </section>

        <!-- 🎁 تب دوم: مارکت گیفت‌ها -->
        <section id="view-gifts" class="hidden space-y-3">
            <div class="store-card p-3 flex items-center justify-between gap-2">
                <div class="relative flex-1">
                    <i class="fa-solid fa-magnifying-glass absolute right-3 top-2.5 text-gray-500 text-xs"></i>
                    <input type="text" id="searchInput" placeholder="جستجوی نام یا شماره..." 
                           class="w-full bg-[#090a0f] border border-white/5 rounded-xl pr-8 pl-3 py-1.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-amber-400">
                </div>
                <button onclick="openModal()" class="px-3 py-1.5 rounded-xl bg-[#161926] text-xs font-bold text-gray-200 border border-white/5 flex items-center gap-1 whitespace-nowrap">
                    <span id="selectedColText">کالکشن‌ها</span>
                    <i class="fa-solid fa-chevron-down text-[9px] text-gray-400"></i>
                </button>
            </div>

            <div class="flex items-center gap-2 overflow-x-auto pb-1">
                <button onclick="filterType('all', this)" class="type-btn active px-3.5 py-1.5 rounded-xl text-xs font-black bg-amber-400 text-black whitespace-nowrap">همه (__TOTAL_COUNT__)</button>
                <button onclick="filterType('rare', this)" class="type-btn px-3 py-1.5 rounded-xl text-xs font-bold bg-[#161926] text-gray-300 whitespace-nowrap">💎 کمیاب‌ها</button>
                <button onclick="filterType('favs', this)" class="type-btn px-3 py-1.5 rounded-xl text-xs font-bold bg-[#161926] text-gray-300 whitespace-nowrap flex items-center gap-1">
                    <i class="fa-solid fa-heart text-rose-500 text-[10px]"></i> (<span id="favCount">0</span>)
                </button>
            </div>

            <div id="dealsGrid" class="grid grid-cols-2 gap-3"></div>
        </section>

        <!-- ⚡ تب سوم: خدمات اختصاصی و سفارشی ادمین -->
        <section id="view-services" class="hidden space-y-4">
            <!-- زیرتب‌های خدمات -->
            <div class="flex items-center gap-2 overflow-x-auto pb-1">
                <button onclick="switchServiceSubTab('stars')" id="subtab-stars" class="service-subtab-btn px-3.5 py-2 rounded-xl text-xs font-black bg-amber-400 text-black whitespace-nowrap">استارز</button>
                <button onclick="switchServiceSubTab('premium')" id="subtab-premium" class="service-subtab-btn px-3.5 py-2 rounded-xl text-xs font-bold bg-[#161926] text-gray-300 whitespace-nowrap">پرمیوم</button>
                <button onclick="switchServiceSubTab('boost')" id="subtab-boost" class="service-subtab-btn px-3.5 py-2 rounded-xl text-xs font-bold bg-[#161926] text-gray-300 whitespace-nowrap">بوست کانال</button>
                <button onclick="switchServiceSubTab('account')" id="subtab-account" class="service-subtab-btn px-3.5 py-2 rounded-xl text-xs font-bold bg-[#161926] text-gray-300 whitespace-nowrap">اکانت مجازی</button>
                <button onclick="switchServiceSubTab('channel')" id="subtab-channel" class="service-subtab-btn px-3.5 py-2 rounded-xl text-xs font-bold bg-[#161926] text-gray-300 whitespace-nowrap">خدمات کانال</button>
            </div>

            <!-- بخش استارز -->
            <div id="subview-stars" class="space-y-3">
                <div class="store-card p-4 space-y-3">
                    <h4 class="text-xs font-bold text-gray-300">⭐ خرید استارز به تعداد دلخواه:</h4>
                    <input type="number" id="customStarsInput" min="50" placeholder="تعداد استارز (حداقل ۵۰)..." class="w-full bg-[#090a0f] border border-white/5 rounded-xl px-3 py-2.5 text-xs text-white font-bold">
                    <div id="customStarsCalcBox" class="p-2.5 rounded-xl bg-white/[0.03] flex items-center justify-between hidden">
                        <span class="text-xs text-gray-400">مبلغ نهایی:</span>
                        <span id="customStarsPrice" class="text-xs font-black text-amber-400">0 تومان</span>
                    </div>
                </div>
                <div id="starsPackagesList" class="space-y-2"></div>
                <button onclick="orderStars()" class="w-full py-3 bg-amber-400 text-black font-black text-xs rounded-xl shadow-lg shadow-amber-400/20">خرید استارز</button>
            </div>

            <!-- بخش پرمیوم -->
            <div id="subview-premium" class="hidden space-y-3">
                <div id="premiumOptionsList" class="space-y-2.5"></div>
                <button onclick="orderPremium()" class="w-full py-3 bg-amber-400 text-black font-black text-xs rounded-xl shadow-lg shadow-amber-400/20">خرید تلگرام پرمیوم</button>
            </div>

            <!-- بخش محصولات داینامیک ادمین (بوست، اکانت، ممبر) -->
            <div id="subview-custom" class="hidden space-y-2.5">
                <div id="customServicesContainer" class="space-y-2.5"></div>
            </div>
        </section>

        <!-- 👤 تب چهارم: پروفایل کاربری (مطابق عکس اول) -->
        <section id="view-profile" class="hidden space-y-4">
            <div class="store-card p-6 flex flex-col items-center text-center space-y-4">
                <!-- آواتار نشان شطرنج / پروفایل -->
                <div class="w-24 h-24 rounded-full bg-gradient-to-b from-[#e5c07b] to-[#b38938] flex items-center justify-center shadow-xl shadow-amber-500/10 border-2 border-amber-400/20">
                    <span id="profileAvatarIcon" class="text-4xl">♟️</span>
                </div>

                <div>
                    <h2 id="profileName" class="text-lg font-black text-white">کاربر مهمان</h2>
                    <p id="profileUsername" class="text-xs text-gray-400 dir-ltr mt-0.5">@Guest</p>
                </div>

                <div class="w-full pt-4 border-t border-white/5 space-y-3 text-xs">
                    <div class="flex items-center justify-between">
                        <span class="text-gray-400">شناسه کاربر:</span>
                        <span id="profileUserId" class="font-bold text-white font-mono">000000000</span>
                    </div>
                    <div class="flex items-center justify-between">
                        <span class="text-gray-400">وضعیت حساب:</span>
                        <span class="px-2.5 py-0.5 rounded-md text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">فعال</span>
                    </div>
                    <div class="flex items-center justify-between">
                        <span class="text-gray-400">سفارش‌های من:</span>
                        <span id="profileCartCount" class="font-bold text-amber-400">0 قلم در سبد</span>
                    </div>
                </div>

                <a id="profileSupportBtn" href="https://t.me/Zanjani_a" class="w-full py-3 rounded-xl bg-[#161926] text-gray-200 border border-white/5 font-bold text-xs flex items-center justify-center gap-2">
                    <i class="fa-brands fa-telegram text-blue-400"></i>
                    <span>ارتباط با پشتیبانی</span>
                </a>
            </div>
        </section>

    </main>

    <!-- 🛍️ نوار پاپ‌آپ شناور سبد خرید -->
    <div id="floatingCartBar" class="fixed bottom-20 inset-x-4 max-w-xl mx-auto z-40 bg-[#121520]/95 backdrop-blur-xl border border-amber-500/40 p-3.5 rounded-2xl shadow-2xl transition-all duration-300 transform translate-y-36 opacity-0 space-y-2.5">
        <div class="flex items-center justify-between">
            <div class="flex items-center gap-2.5">
                <div class="w-8 h-8 rounded-xl bg-amber-400 text-black flex items-center justify-center font-black text-xs">
                    <span id="cartCountBadge">0</span>
                </div>
                <div>
                    <span class="text-[11px] text-gray-400 block">سبد خرید شما:</span>
                    <span id="cartTotalPrice" class="text-xs font-black text-amber-400">0 تومان</span>
                </div>
            </div>
            <div class="flex items-center gap-2">
                <button onclick="clearCart()" class="p-2 text-gray-400 hover:text-rose-400 text-xs">
                    <i class="fa-solid fa-trash-can"></i>
                </button>
                <button onclick="checkoutCart()" class="py-2 px-4 rounded-xl bg-gradient-to-r from-amber-400 to-yellow-500 text-black text-xs font-black flex items-center gap-1.5 shadow-md shadow-amber-500/20">
                    <span>ثبت نهایی</span>
                    <i class="fa-solid fa-arrow-left text-[10px]"></i>
                </button>
            </div>
        </div>
    </div>

    <!-- منوی پایینی داگ استور (Bottom Navigation Dock) -->
    <nav class="fixed bottom-3 inset-x-4 max-w-xl mx-auto z-40 dock-bar px-2 py-1.5 flex items-center justify-around">
        <button onclick="switchView('home')" id="nav-home" class="nav-btn active px-4 py-2 rounded-2xl flex flex-col items-center gap-1 text-[10px] font-bold text-gray-400 transition">
            <i class="fa-solid fa-house text-sm"></i>
            <span>خانه</span>
        </button>
        <button onclick="switchView('gifts')" id="nav-gifts" class="nav-btn px-4 py-2 rounded-2xl flex flex-col items-center gap-1 text-[10px] font-bold text-gray-400 transition">
            <i class="fa-solid fa-gift text-sm"></i>
            <span>گیفت‌ها</span>
        </button>
        <button onclick="switchView('services')" id="nav-services" class="nav-btn px-4 py-2 rounded-2xl flex flex-col items-center gap-1 text-[10px] font-bold text-gray-400 transition">
            <i class="fa-solid fa-bolt text-sm"></i>
            <span>خدمات</span>
        </button>
        <button onclick="switchView('profile')" id="nav-profile" class="nav-btn px-4 py-2 rounded-2xl flex flex-col items-center gap-1 text-[10px] font-bold text-gray-400 transition">
            <i class="fa-solid fa-user text-sm"></i>
            <span>حساب</span>
        </button>
    </nav>

    <!-- مودال کالکشن -->
    <div id="collectionModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm hidden">
        <div class="store-card w-full max-w-md rounded-3xl overflow-hidden flex flex-col max-h-[80vh]">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-white/5">
                <button onclick="closeModal()" class="w-7 h-7 rounded-full bg-white/5 text-gray-400 flex items-center justify-center"><i class="fa-solid fa-xmark text-xs"></i></button>
                <h3 class="text-xs font-black text-white">انتخاب کالکشن‌ها</h3>
                <div class="w-7"></div>
            </div>
            <div class="p-3 border-b border-white/5 flex items-center justify-between text-xs">
                <button onclick="selectAllCollections()" class="text-amber-400 font-bold">انتخاب همه</button>
                <button onclick="clearCollectionSelection()" class="text-gray-400 hover:text-rose-400">پاک کردن</button>
            </div>
            <div id="modalCollectionsList" class="p-3 space-y-1.5 overflow-y-auto flex-1"></div>
            <div class="p-3 border-t border-white/5 bg-[#090a0f]">
                <button onclick="applyCollectionModal()" class="w-full py-2.5 bg-amber-400 text-black text-xs font-black rounded-xl">اعمال فیلتر</button>
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
                    document.getElementById('profileUserId').innerText = tgUser.id || '---';
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
            announcementText: 'تخفیف ویژه سفارشات فعال شد',
            announcementActive: true,
            couponCode: 'DUCK',
            couponPercent: 10,
            customServices: [
                { id: "boost-1", category: "boost", title: "بوست ۱ لول (۷ روزه)", price: 45000, desc: "تحویل سریع با لینک کانال" },
                { id: "boost-2", category: "boost", title: "بوست ۴ لول (۱ ماهه)", price: 180000, desc: "پایداری بالا" },
                { id: "acc-1", category: "account", title: "اکانت مجازی آمریکا (+1)", price: 85000, desc: "شماره اختصاصی بدون ریپورت" },
                { id: "ch-1", category: "channel", title: "۱۰۰۰ ممبر واقعی کانال", price: 95000, desc: "کیفیت بالا با ریزش کم" }
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

        // جابجایی بین صفحات اصلی
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

        // کلیک روی دسته‌های صفحه اصلی
        function openCategoryTab(cat) {
            if (cat === 'gift') {
                switchView('gifts');
            } else if (cat === 'stars' || cat === 'premium') {
                switchView('services');
                switchServiceSubTab(cat);
            } else {
                switchView('services');
                switchServiceSubTab(cat);
            }
        }

        // زیرتب‌های صفحه خدمات
        function switchServiceSubTab(tab) {
            triggerHaptic('selection');
            currentServiceSubTab = tab;
            document.querySelectorAll('.service-subtab-btn').forEach(btn => {
                btn.classList.remove('bg-amber-400', 'text-black', 'font-black');
                btn.classList.add('bg-[#161926]', 'text-gray-300', 'font-bold');
            });

            const activeBtn = document.getElementById(`subtab-${tab}`);
            if (activeBtn) {
                activeBtn.classList.add('bg-amber-400', 'text-black', 'font-black');
                activeBtn.classList.remove('bg-[#161926]', 'text-gray-300');
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
                <div onclick="selectStarsPackage(${qty})" class="store-card p-3 flex items-center justify-between cursor-pointer hover:border-amber-400">
                    <span class="text-xs font-bold text-white">⭐ ${qty} Stars</span>
                    <span class="text-xs font-black text-amber-400">${totalToman} ت</span>
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
                <div onclick="selectPremiumPlan(${opt.months})" class="store-card p-3.5 flex items-center justify-between cursor-pointer ${isSelected ? 'border-amber-400 bg-amber-400/5' : ''}">
                    <span class="text-xs font-bold text-white">${opt.label}</span>
                    <span class="text-xs font-black text-amber-400">${opt.price.toLocaleString('en-US')} تومان</span>
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

        // ================= خدمات سفارشی ادمین (بوست، اکانت، کانال) =================
        function renderCustomServices(category) {
            const container = document.getElementById('customServicesContainer');
            const list = (SETTINGS.customServices || []).filter(s => s.category === category);

            if (list.length === 0) {
                container.innerHTML = '<p class="text-xs text-gray-500 text-center py-6">موردی برای این بخش تعریف نشده است.</p>';
                return;
            }

            container.innerHTML = list.map(item => `
                <div class="store-card p-3.5 flex items-center justify-between">
                    <div>
                        <h4 class="text-xs font-bold text-white">${item.title}</h4>
                        <p class="text-[10px] text-gray-400 mt-0.5">${item.desc || ''}</p>
                        <span class="text-xs font-black text-amber-400 mt-1 block">${Number(item.price).toLocaleString('en-US')} تومان</span>
                    </div>
                    <button onclick='addToCartCustom(${JSON.stringify(item)})' class="px-3.5 py-1.5 rounded-xl bg-amber-400 text-black font-black text-xs hover:bg-amber-300">
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
                container.innerHTML = '<div class="col-span-full py-12 text-center text-gray-500 text-xs">گیفتی پیدا نشد.</div>';
                return;
            }

            const giftPriceFormatted = Number(SETTINGS.giftMonthlyPrice || 160000).toLocaleString('en-US');

            container.innerHTML = items.map(deal => {
                const isFav = favorites.includes(deal.name);
                const isInCart = cart.some(c => c.name === deal.name);

                return `
                <div class="store-card overflow-hidden flex flex-col justify-between ${isInCart ? 'border-amber-400 bg-amber-400/5' : ''}">
                    <div>
                        <div class="relative w-full h-36 bg-[#161926] flex items-center justify-center border-b border-white/5">
                            ${deal.rarity ? `<span class="absolute top-2 left-2 px-2 py-0.5 rounded-md text-[9px] font-bold bg-black/60 text-amber-400 border border-amber-400/30">${deal.rarity}</span>` : ''}
                            <button onclick="toggleFavorite('${deal.name}')" class="absolute top-2 right-2 w-7 h-7 rounded-full bg-black/40 flex items-center justify-center text-xs ${isFav ? 'text-rose-500' : 'text-gray-400'}">
                                <i class="fa-solid fa-heart"></i>
                            </button>
                            <img src="${deal.image_url}" alt="${deal.name}" class="w-24 h-24 object-contain" onerror="this.src='https://marketapp.org/favicon.ico'">
                        </div>
                        <div class="p-2.5">
                            <h4 class="text-xs font-bold text-white truncate text-center">${deal.name}</h4>
                            <span class="text-xs font-black text-amber-400 text-center block mt-1">${giftPriceFormatted} ت/ماه</span>
                        </div>
                    </div>
                    <div class="p-2.5 pt-0 grid grid-cols-2 gap-1.5">
                        <a href="${deal.tg_link}" target="_blank" class="py-1.5 text-center text-gray-300 bg-white/5 rounded-lg text-xs font-bold">دیدن</a>
                        <button onclick='toggleCartGift(${JSON.stringify(deal)})' class="py-1.5 text-center ${isInCart ? 'bg-amber-400 text-black font-black' : 'bg-white text-black font-bold'} rounded-lg text-xs">
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

        // پاپ‌آپ خودکار سبد خرید در صورت داشتن آیتم
        function updateCartUI() {
            const bar = document.getElementById('floatingCartBar');
            const count = cart.length;
            document.getElementById('cartCountBadge').innerText = count;
            document.getElementById('profileCartCount').innerText = `${count} قلم در سبد`;

            let total = 0;
            cart.forEach(item => { total += Number(item.price || 0); });
            document.getElementById('cartTotalPrice').innerText = `${total.toLocaleString('en-US')} تومان`;

            // اگر آیتمی در سبد باشد، پاپ‌آپ اتوماتیک بالا می‌آید
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
                <div onclick="toggleModalCollection('${col.name}')" class="p-2.5 rounded-xl border ${isSelected ? 'border-amber-400 bg-amber-400/10' : 'border-white/5'} flex items-center justify-between cursor-pointer">
                    <span class="text-xs font-bold text-white">${col.name}</span>
                    <span class="text-[10px] text-gray-400">${col.count}</span>
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
                b.classList.remove('bg-amber-400', 'text-black', 'font-black');
                b.classList.add('bg-[#161926]', 'text-gray-300', 'font-bold');
            });
            if (btn) {
                btn.classList.remove('bg-[#161926]', 'text-gray-300');
                btn.classList.add('bg-amber-400', 'text-black', 'font-black');
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

        // لود اولیه
        updateUI();
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
    try:
        with urllib.request.urlopen(req, timeout=30): pass
    except Exception: pass


# ==========================================
# ⚡ موتور اسکرپر
# ==========================================
async def main():
    deals_found: List[Dict[str, Any]] = []
    seen_links: Set[str] = set()

    print("\n" + "═" * 65)
    print("  🦆 DUCK STORE TURBO SCRAPER (200 ITEMS + STABLE ENGINE) 🦆")
    print("═" * 65 + "\n")

    launch_args = ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-accelerated-2d-canvas", "--no-first-run", "--no-zygote"]

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True, args=launch_args)
        except Exception:
            browser = await p.chromium.launch(headless=True, channel="chrome", args=launch_args)

        page = await browser.new_page()
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
                            if not l.startswith("Days:") and not l.startswith("-") and not l.startswith("#")
                            and l.lower() not in ["per day", "min. price"] and not re.match(r"^\d+(\.\d+)?$", l)
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

                        if len(deals_found) >= CONFIG["TARGET_DEALS_COUNT"]: break
                else:
                    seen_links.add(full_link)

            if len(deals_found) >= CONFIG["TARGET_DEALS_COUNT"]: break
            await page.evaluate("window.scrollBy(0, window.innerHeight * 3);")
            await page.wait_for_timeout(350)

        await browser.close()
        sorted_deals = list(reversed(deals_found))

        generate_duck_store_html(sorted_deals)

        with open(CONFIG["EXPORT_CSV"], "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["ردیف", "کالکشن", "نام گیفت", "شماره", "تخفیف", "کمیابی", "لینک تلگرام", "لینک MarketApp"])
            for idx, d in enumerate(sorted_deals, 1):
                writer.writerow([idx, d["gift_title"], d["name"], d["number"], d["discount"], d["rarity"] or "معمولی", d["tg_link"], d["market_link"]])

        print("\n⚡ فروشگاه Duck Store با دیزاین جدید و سیستم ماژولار تولید شد!")
        send_telegram_package(sorted_deals)


if __name__ == "__main__":
    asyncio.run(main())
