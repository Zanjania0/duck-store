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
    "MIN_DISCOUNT_PERCENT": 50.0,
    "TARGET_DEALS_COUNT": 200,
    "BASE_DOMAIN": "https://marketapp.org",
    "EXPORT_CSV": "discounts.csv",
    "EXPORT_HTML": "index.html",
    "EXPORT_JSON": "discounts.json",
    # ⚠️ آدرس ورکر کلادفلر خود را که در مرحله قبل ساختید اینجا جایگزین کنید:
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
        return "👑 زیر ۱۰۰ (نایاب)"
    if num < 1000:
        return f"💎 زیر ۱۰۰۰ (#{num})"
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


def generate_duck_store_html(deals: List[Dict[str, Any]]):
    """تولید وب‌سایت فروشگاهی Duck Store متصل به Cloudflare Worker"""
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Duck Store | فروشگاه تلگرام</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;600;700;900&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Vazirmatn', sans-serif;
            background-color: #0c0f17;
            color: #f3f4f6;
            -webkit-tap-highlight-color: transparent;
        }
        .stars-card {
            background: #141722;
            border: 1px solid rgba(255, 255, 255, 0.07);
            border-radius: 24px;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .stars-card:hover {
            transform: translateY(-4px);
            border-color: rgba(255, 184, 46, 0.35);
        }
        .price-badge-gold {
            background: #382404;
            color: #ffb82e;
            border: 1px solid rgba(255, 184, 46, 0.25);
        }
        .modal-bg {
            background: #12141a;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .collection-item {
            background: #1a1d26;
            border: 1px solid rgba(255, 255, 255, 0.05);
            transition: all 0.2s ease;
        }
        .collection-item:hover {
            background: #232733;
            border-color: rgba(59, 130, 246, 0.4);
        }
        .select-row {
            background: #151924;
            border: 1px solid rgba(255, 255, 255, 0.07);
            transition: all 0.2s ease;
        }
        .select-row.active {
            border-color: #3b82f6;
            background: #1b2234;
        }
        ::-webkit-scrollbar {
            width: 6px;
        }
        ::-webkit-scrollbar-track {
            background: #0c0f17;
        }
        ::-webkit-scrollbar-thumb {
            background: #222738;
            border-radius: 4px;
        }
    </style>
</head>
<body class="min-h-screen pb-28">
    <!-- هدر سایت -->
    <header class="sticky top-0 z-40 bg-[#10131d]/95 backdrop-blur-md border-b border-gray-800/80">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-18 py-3 flex items-center justify-between">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-2xl bg-gradient-to-tr from-amber-500 to-orange-500 flex items-center justify-center text-xl shadow-lg shadow-orange-500/20">
                    🦆
                </div>
                <div>
                    <h1 class="text-base sm:text-lg font-black text-white">Duck Store</h1>
                    <p class="text-[11px] text-gray-400">مرجع گیفت، استارز و پرمیوم</p>
                </div>
            </div>
            <div class="flex items-center gap-2">
                <!-- لینک به پنل ادمین امن -->
                <a href="admin.html" class="w-9 h-9 rounded-xl bg-[#1d2232] hover:bg-[#272e44] text-gray-300 hover:text-amber-400 flex items-center justify-center border border-gray-700/60 transition shadow-sm" title="پنل مدیریت قیمت‌ها">
                    <i class="fa-solid fa-gear text-sm"></i>
                </a>
                <a id="headerSupportLink" href="https://t.me/Zanjani_a" target="_blank" class="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold bg-[#1d2232] hover:bg-[#272e44] text-gray-200 border border-gray-700/60 transition shadow-sm">
                    <i class="fa-brands fa-telegram text-blue-400"></i>
                    <span>پشتیبانی</span>
                </a>
            </div>
        </div>

        <!-- تب‌های ۳ گانه -->
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center gap-2 py-2 border-t border-gray-800/40 overflow-x-auto">
            <button onclick="switchMainTab('gifts')" id="tabBtn-gifts" class="main-tab-btn active px-4 py-2 rounded-xl text-xs font-black bg-amber-500 text-black transition flex items-center gap-1.5 whitespace-nowrap">
                <i class="fa-solid fa-gift"></i> اجاره گیفت
            </button>
            <button onclick="switchMainTab('stars')" id="tabBtn-stars" class="main-tab-btn px-4 py-2 rounded-xl text-xs font-bold bg-[#171b26] text-gray-300 hover:bg-[#22283a] transition flex items-center gap-1.5 whitespace-nowrap">
                <i class="fa-solid fa-star text-amber-400"></i> استارز تلگرام
            </button>
            <button onclick="switchMainTab('premium')" id="tabBtn-premium" class="main-tab-btn px-4 py-2 rounded-xl text-xs font-bold bg-[#171b26] text-gray-300 hover:bg-[#22283a] transition flex items-center gap-1.5 whitespace-nowrap">
                <i class="fa-solid fa-crown text-purple-400"></i> تلگرام پرمیوم
            </button>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-6">
        <!-- تب گیفت -->
        <section id="section-gifts" class="block">
            <div class="bg-[#141722] p-3 rounded-2xl border border-gray-800/80 mb-6 flex flex-col sm:flex-row items-center justify-between gap-3">
                <div class="relative w-full sm:w-80">
                    <i class="fa-solid fa-magnifying-glass absolute right-3.5 top-3 text-gray-500 text-xs"></i>
                    <input type="text" id="searchInput" placeholder="جستجوی نام یا شماره گیفت..." 
                           class="w-full bg-[#0d1017] border border-gray-800 rounded-xl pr-10 pl-4 py-2 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-amber-500 transition">
                </div>

                <div class="flex items-center gap-2 w-full sm:w-auto overflow-x-auto pb-1 sm:pb-0">
                    <button onclick="openModal()" class="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold bg-[#1d2232] hover:bg-[#272e44] text-gray-200 border border-gray-700/60 transition whitespace-nowrap">
                        <i class="fa-solid fa-layer-group text-amber-400 text-xs"></i>
                        <span id="selectedColText">کالکشن‌ها</span>
                        <i class="fa-solid fa-chevron-down text-[9px] text-gray-400 mr-0.5"></i>
                    </button>
                    <button onclick="filterType('all')" class="type-btn active px-3.5 py-2 rounded-xl text-xs font-bold bg-amber-500 text-black transition whitespace-nowrap">همه (__TOTAL_COUNT__)</button>
                    <button onclick="filterType('rare')" class="type-btn px-3.5 py-2 rounded-xl text-xs font-bold bg-[#1d2232] text-gray-300 hover:bg-[#272e44] transition whitespace-nowrap">💎 کمیاب‌ها (__RARE_COUNT__)</button>
                    <button onclick="filterType('favs')" class="type-btn px-3.5 py-2 rounded-xl text-xs font-bold bg-[#1d2232] text-gray-300 hover:bg-[#272e44] transition whitespace-nowrap flex items-center gap-1.5">
                        <i class="fa-solid fa-heart text-rose-500 text-xs"></i> (<span id="favCount">0</span>)
                    </button>
                </div>
            </div>

            <div id="dealsGrid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5"></div>
        </section>

        <!-- تب استارز -->
        <section id="section-stars" class="hidden max-w-xl mx-auto space-y-6">
            <div class="bg-[#141722] p-5 rounded-3xl border border-gray-800">
                <h3 class="text-sm font-bold text-gray-200 mb-3 flex items-center gap-2">
                    <i class="fa-solid fa-star text-amber-400"></i> تعداد استارز دلخواه
                </h3>
                <div class="relative">
                    <div class="absolute right-3.5 top-3.5 text-amber-400 text-base">⭐</div>
                    <input type="number" id="customStarsInput" min="50" max="10000000" placeholder="تعداد استارز (از ۵۰ تا ۱۰,۰۰۰,۰۰۰)..." 
                           class="w-full bg-[#0d1017] border border-gray-700/80 rounded-2xl pr-11 pl-4 py-3.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-amber-500 transition font-bold">
                </div>
                <div id="customStarsCalcBox" class="mt-3 p-3.5 rounded-2xl bg-[#1b202e] border border-gray-700/50 flex items-center justify-between hidden">
                    <span class="text-xs text-gray-400">مبلغ نهایی:</span>
                    <span id="customStarsPrice" class="text-sm font-black text-amber-400">۰ تومان</span>
                </div>
            </div>

            <div class="bg-[#141722] p-5 rounded-3xl border border-gray-800 space-y-3">
                <h3 class="text-xs font-bold text-gray-400 mb-2">یا انتخاب پکیج آماده:</h3>
                <div id="starsPackagesList" class="space-y-2.5"></div>

                <div class="pt-4 border-t border-gray-800/80 flex items-center justify-between">
                    <div>
                        <p class="text-xs text-gray-400">مبلغ قابل پرداخت:</p>
                        <p id="selectedStarsFinalToman" class="text-lg font-black text-amber-400">۰ تومان</p>
                    </div>
                    <button onclick="orderStars()" class="py-3 px-6 rounded-2xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-black font-black text-xs transition shadow-lg shadow-orange-500/20 flex items-center gap-2">
                        <span>خرید استارز</span>
                        <i class="fa-solid fa-bolt text-xs"></i>
                    </button>
                </div>
            </div>
        </section>

        <!-- تب پرمیوم -->
        <section id="section-premium" class="hidden max-w-xl mx-auto space-y-6">
            <div class="bg-[#141722] p-6 rounded-3xl border border-gray-800 space-y-4">
                <div class="flex items-center justify-between">
                    <h3 class="text-sm font-bold text-gray-200 flex items-center gap-2">
                        <i class="fa-solid fa-crown text-purple-400"></i> انتخاب مدت زمان اشتراک
                    </h3>
                    <span class="px-2.5 py-0.5 rounded-lg text-[11px] font-extrabold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                        تخفیف ویژه
                    </span>
                </div>

                <div class="space-y-3" id="premiumOptionsList"></div>

                <div class="pt-4 border-t border-gray-800/80 flex items-center justify-between">
                    <div>
                        <p class="text-xs text-gray-400">مبلغ اشتراک پرمیوم:</p>
                        <p id="selectedPremiumFinalToman" class="text-lg font-black text-purple-400">۰ تومان</p>
                    </div>
                    <button onclick="orderPremium()" class="py-3 px-6 rounded-2xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-black text-xs transition shadow-lg shadow-purple-600/25 flex items-center gap-2">
                        <span>خرید پرمیوم</span>
                        <i class="fa-solid fa-crown text-xs"></i>
                    </button>
                </div>
            </div>
        </section>
    </main>

    <!-- 🛍️ نوار شناور سبد خرید -->
    <div id="floatingCartBar" class="fixed bottom-4 inset-x-4 max-w-lg mx-auto z-40 bg-[#161b26]/95 backdrop-blur-md border border-amber-500/40 p-3.5 rounded-2xl shadow-2xl flex items-center justify-between transition-all duration-300 transform translate-y-28 opacity-0">
        <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl bg-amber-500 text-black flex items-center justify-center font-black text-sm">
                <span id="cartCountBadge">0</span>
            </div>
            <div>
                <p class="text-xs font-bold text-white">سبد اجاره گیفت</p>
                <p id="cartTotalPrice" class="text-xs text-amber-400 font-black">۰ تومان</p>
            </div>
        </div>
        <div class="flex items-center gap-2">
            <button onclick="clearCart()" class="p-2 text-gray-400 hover:text-rose-400 text-xs transition" title="خالی کردن سبد">
                <i class="fa-solid fa-trash-can"></i>
            </button>
            <button onclick="checkoutCart()" class="py-2.5 px-4 rounded-xl bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white text-xs font-black transition shadow-lg shadow-blue-500/25 flex items-center gap-1.5">
                <span>ثبت سفارش</span>
                <i class="fa-solid fa-arrow-left text-[11px]"></i>
            </button>
        </div>
    </div>

    <!-- مودال انتخاب کالکشن -->
    <div id="collectionModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm hidden">
        <div class="modal-bg w-full max-w-md rounded-3xl overflow-hidden shadow-2xl flex flex-col max-h-[85vh]">
            <div class="px-6 py-4 flex items-center justify-between border-b border-gray-800">
                <button onclick="closeModal()" class="w-7 h-7 rounded-full bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white flex items-center justify-center transition">
                    <i class="fa-solid fa-xmark text-xs"></i>
                </button>
                <h3 class="text-sm font-black text-white">انتخاب کالکشن</h3>
                <div class="w-7"></div>
            </div>

            <div class="p-3.5 border-b border-gray-800/50">
                <div class="relative">
                    <input type="text" id="modalSearchInput" placeholder="جستجوی کالکشن..." 
                           class="w-full bg-[#1a1d26] border border-gray-700 rounded-xl pr-4 pl-9 py-2 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-amber-500 transition">
                    <i class="fa-solid fa-magnifying-glass absolute left-3.5 top-2.5 text-gray-400 text-xs"></i>
                </div>
            </div>

            <div id="modalCollectionsList" class="p-3.5 space-y-2 overflow-y-auto flex-1"></div>

            <a id="modalSupportLink" href="https://t.me/Zanjani_a" target="_blank" class="w-full py-3 bg-[#0088cc] hover:bg-[#0077b5] text-white text-xs font-bold text-center transition flex items-center justify-center gap-1.5">
                <i class="fa-brands fa-telegram text-sm"></i> پشتیبانی Duck Store
            </a>
        </div>
    </div>

    <script>
        if (window.Telegram && window.Telegram.WebApp) {
            window.Telegram.WebApp.ready();
            window.Telegram.WebApp.expand();
        }

        function triggerHaptic(type = 'light') {
            if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.HapticFeedback) {
                if (type === 'selection') window.Telegram.WebApp.HapticFeedback.selectionChanged();
                else window.Telegram.WebApp.HapticFeedback.impactOccurred(type);
            }
        }

        const DEALS = __DEALS_JSON__;
        const COLLECTIONS = __COLLECTIONS_JSON__;
        
        // 🌐 آدرس ورکر اختصاصی Cloudflare
        const WORKER_URL = "__WORKER_URL__";

        const DEFAULT_SETTINGS = {
            ratePerStar: 1450,
            prem3: 620000,
            prem6: 950000,
            prem12: 1690000,
            giftMonthlyPrice: 160000,
            adminTg: 'Zanjani_a'
        };

        let SETTINGS = { ...DEFAULT_SETTINGS };

        let currentMainTab = 'gifts';
        let selectedType = 'all';
        let selectedCollection = 'all';
        let selectedStarsCount = 50;
        let selectedPremiumMonths = 12;

        const STARS_PACKAGES = [50, 75, 100, 150, 250, 350, 500, 1000, 2500, 5000];

        let favorites = JSON.parse(localStorage.getItem('duck_favs') || '[]');
        let cart = JSON.parse(localStorage.getItem('duck_cart') || '[]');

        // دریافت زنده قیمت‌ها از Cloudflare Worker
        async function fetchCloudSettings() {
            try {
                const res = await fetch(`${WORKER_URL}/api/settings`);
                if (res.ok) {
                    const parsed = await res.json();
                    if (parsed && typeof parsed === 'object') {
                        SETTINGS = { ...DEFAULT_SETTINGS, ...parsed };
                    }
                }
            } catch (err) {
                console.warn('استفاده از نرخ‌های پیش‌فرض به دلیل عدم دسترسی به سرور');
            }
            updateUIWithLatestSettings();
        }

        function updateUIWithLatestSettings() {
            const adminUser = SETTINGS.adminTg || 'Zanjani_a';
            document.getElementById('headerSupportLink').href = `https://t.me/${adminUser}`;
            document.getElementById('modalSupportLink').href = `https://t.me/${adminUser}`;
            renderCards(getFilteredDeals());
            renderStarsPackages();
            renderPremiumOptions();
            updateCartUI();
        }

        function switchMainTab(tab) {
            triggerHaptic('selection');
            currentMainTab = tab;
            ['gifts', 'stars', 'premium'].forEach(t => {
                document.getElementById(`section-${t}`).classList.add('hidden');
                document.getElementById(`tabBtn-${t}`).classList.remove('active', 'bg-amber-500', 'text-black');
                document.getElementById(`tabBtn-${t}`).classList.add('bg-[#171b26]', 'text-gray-300');
            });

            document.getElementById(`section-${tab}`).classList.remove('hidden');
            const btn = document.getElementById(`tabBtn-${tab}`);
            btn.classList.add('active', 'bg-amber-500', 'text-black');
            btn.classList.remove('bg-[#171b26]', 'text-gray-300');
            updateCartUI();
        }

        // ================= استارز =================
        function renderStarsPackages() {
            const container = document.getElementById('starsPackagesList');
            container.innerHTML = STARS_PACKAGES.map(qty => {
                const totalToman = (qty * SETTINGS.ratePerStar).toLocaleString('fa-IR');
                const isSelected = selectedStarsCount === qty;
                return `
                <div onclick="selectStarsPackage(${qty})" class="select-row p-3.5 rounded-2xl flex items-center justify-between cursor-pointer ${isSelected ? 'active' : ''}">
                    <div class="flex items-center gap-3">
                        <div class="w-5 h-5 rounded-full border-2 flex items-center justify-center ${isSelected ? 'border-amber-400 bg-amber-400' : 'border-gray-600'}">
                            ${isSelected ? '<div class="w-2 h-2 rounded-full bg-black"></div>' : ''}
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="text-base">⭐</span>
                            <span class="text-sm font-black text-white">${qty} Stars</span>
                        </div>
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
                const total = (val * SETTINGS.ratePerStar).toLocaleString('fa-IR');
                document.getElementById('customStarsPrice').innerText = `${total} تومان`;
                document.getElementById('customStarsCalcBox').classList.remove('hidden');
                document.querySelectorAll('#starsPackagesList .select-row').forEach(el => el.classList.remove('active'));
            } else {
                document.getElementById('customStarsCalcBox').classList.add('hidden');
            }
            updateStarsFinalPrice();
        });

        function updateStarsFinalPrice() {
            const total = (selectedStarsCount * SETTINGS.ratePerStar).toLocaleString('fa-IR');
            document.getElementById('selectedStarsFinalToman').innerText = `${total} تومان`;
        }

        function orderStars() {
            triggerHaptic('heavy');
            const total = (selectedStarsCount * SETTINGS.ratePerStar).toLocaleString('fa-IR');
            const msg = encodeURIComponent(`سلام، من متقاضی خرید استارز تلگرام از Duck Store هستم:\\n\\n⭐ تعداد استارز: ${selectedStarsCount} Stars\\n💳 مبلغ قابل پرداخت: ${total} تومان`);
            window.open(`https://t.me/${SETTINGS.adminTg}?text=${msg}`, '_blank');
        }

        // ================= پرمیوم =================
        function renderPremiumOptions() {
            const container = document.getElementById('premiumOptionsList');
            const options = [
                { months: 12, label: '۱ ساله (1 Year)', discount: '-52%', price: SETTINGS.prem12 },
                { months: 6, label: '۶ ماهه (6 Months)', discount: '-47%', price: SETTINGS.prem6 },
                { months: 3, label: '۳ ماهه (3 Months)', discount: '-20%', price: SETTINGS.prem3 }
            ];

            container.innerHTML = options.map(opt => {
                const isSelected = selectedPremiumMonths === opt.months;
                const totalToman = opt.price.toLocaleString('fa-IR');
                return `
                <div onclick="selectPremiumPlan(${opt.months})" class="select-row p-4 rounded-2xl flex items-center justify-between cursor-pointer ${isSelected ? 'active' : ''}">
                    <div class="flex items-center gap-3">
                        <div class="w-5 h-5 rounded-full border-2 flex items-center justify-center ${isSelected ? 'border-purple-400 bg-purple-400' : 'border-gray-600'}">
                            ${isSelected ? '<div class="w-2 h-2 rounded-full bg-black"></div>' : ''}
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="text-sm font-black text-white">${opt.label}</span>
                            <span class="px-2 py-0.5 rounded-md text-[10px] font-black bg-blue-500/20 text-blue-400 border border-blue-500/30">${opt.discount}</span>
                        </div>
                    </div>
                    <span class="text-xs font-black text-purple-400">${totalToman} t</span>
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
            document.getElementById('selectedPremiumFinalToman').innerText = `${price.toLocaleString('fa-IR')} تومان`;
        }

        function orderPremium() {
            triggerHaptic('heavy');
            let planName = '۱ ساله';
            let price = SETTINGS.prem12;
            if (selectedPremiumMonths === 6) { planName = '۶ ماهه'; price = SETTINGS.prem6; }
            if (selectedPremiumMonths === 3) { planName = '۳ ماهه'; price = SETTINGS.prem3; }
            const total = price.toLocaleString('fa-IR');
            const msg = encodeURIComponent(`سلام، من متقاضی خرید تلگرام پرمیوم از Duck Store هستم:\\n\\n👑 نوع اشتراک: ${planName}\\n💳 مبلغ: ${total} تومان`);
            window.open(`https://t.me/${SETTINGS.adminTg}?text=${msg}`, '_blank');
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
            if (existingIdx > -1) {
                cart.splice(existingIdx, 1);
            } else {
                cart.push(item);
            }
            localStorage.setItem('duck_cart', JSON.stringify(cart));
            updateCartUI();
            renderCards(getFilteredDeals());
        }

        function updateCartUI() {
            const bar = document.getElementById('floatingCartBar');
            const count = cart.length;
            document.getElementById('cartCountBadge').innerText = count;
            const total = (count * SETTINGS.giftMonthlyPrice).toLocaleString('fa-IR');
            document.getElementById('cartTotalPrice').innerText = `${total} تومان / ماه`;

            if (count > 0 && currentMainTab === 'gifts') {
                bar.classList.remove('translate-y-28', 'opacity-0');
                bar.classList.add('translate-y-0', 'opacity-100');
            } else {
                bar.classList.remove('translate-y-0', 'opacity-100');
                bar.classList.add('translate-y-28', 'opacity-0');
            }
        }

        function clearCart() {
            triggerHaptic('light');
            cart = [];
            localStorage.setItem('duck_cart', JSON.stringify(cart));
            updateCartUI();
            renderCards(getFilteredDeals());
        }

        function checkoutCart() {
            triggerHaptic('heavy');
            if (cart.length === 0) return;
            const totalToman = (cart.length * SETTINGS.giftMonthlyPrice).toLocaleString('fa-IR');
            const itemsList = cart.map((c, i) => `${i + 1}. 🎁 ${c.name} (${c.tg_link})`).join('\\n');
            const message = encodeURIComponent(`سلام، من درخواست اجاره این گیفت‌ها را از Duck Store دارم:\\n\\n${itemsList}\\n\\n💰 تعداد: ${cart.length} عدد\\n💳 مبلغ کل: ${totalToman} تومان / ماه`);
            window.open(`https://t.me/${SETTINGS.adminTg}?text=${message}`, '_blank');
        }

        function renderCards(items) {
            const container = document.getElementById('dealsGrid');
            if (items.length === 0) {
                container.innerHTML = '<div class="col-span-full py-16 text-center text-gray-400">گیفتی با این مشخصات پیدا نشد.</div>';
                return;
            }

            const giftPriceFormatted = SETTINGS.giftMonthlyPrice.toLocaleString('fa-IR');

            container.innerHTML = items.map((deal) => {
                const rarityBadge = deal.rarity ? `<span class="absolute top-2.5 left-2.5 px-2.5 py-0.5 rounded-lg text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 backdrop-blur-md">${deal.rarity}</span>` : '';
                const isFav = favorites.includes(deal.name);
                const isInCart = cart.some(c => c.name === deal.name);

                return `
                <div class="stars-card overflow-hidden flex flex-col justify-between ${isInCart ? 'border-amber-500 bg-[#171b28]' : ''}">
                    <div>
                        <div class="relative w-full h-48 bg-gradient-to-b from-[#22283a] to-[#161a26] flex items-center justify-center overflow-hidden border-b border-gray-800/60 rounded-t-3xl">
                            ${rarityBadge}
                            
                            <button onclick="toggleFavorite('${deal.name}')" class="absolute top-2.5 right-2.5 w-8 h-8 rounded-full bg-black/50 backdrop-blur-md flex items-center justify-center text-sm transition hover:scale-110 ${isFav ? 'text-rose-500' : 'text-gray-400 hover:text-white'}">
                                <i class="${isFav ? 'fa-solid' : 'fa-regular'} fa-heart"></i>
                            </button>

                            <img src="${deal.image_url}" alt="${deal.name}" class="w-32 h-32 object-contain filter drop-shadow-[0_10px_20px_rgba(0,0,0,0.6)] transform hover:scale-108 transition duration-300" onerror="this.src='https://marketapp.org/favicon.ico'">
                        </div>

                        <div class="p-4">
                            <h3 class="font-bold text-sm text-center text-white mb-3 truncate">${deal.name}</h3>

                            <div class="flex flex-col items-center mb-4">
                                <span class="price-badge-gold px-4 py-1.5 rounded-full text-xs font-black shadow-sm">
                                    ${giftPriceFormatted} تومان / ماه
                                </span>
                            </div>

                            <div class="space-y-2 text-xs text-gray-400 bg-[#0d1017]/80 p-3 rounded-xl border border-gray-800/60">
                                <div class="flex justify-between items-center text-[11px]">
                                    <span class="text-gray-500">کالکشن:</span>
                                    <span class="font-semibold text-gray-200">${deal.gift_title}</span>
                                </div>
                                <div class="flex justify-between items-center text-[11px]">
                                    <span class="text-gray-500">مدت اجاره:</span>
                                    <span class="font-semibold text-gray-200">${deal.days_range} روز</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="p-4 pt-0 grid grid-cols-2 gap-2">
                        <a href="${deal.tg_link}" target="_blank" onclick="triggerHaptic('light')" class="py-2.5 px-3 rounded-xl bg-[#1e2330] hover:bg-[#282f42] text-gray-300 text-xs font-bold text-center transition border border-gray-700/50 flex items-center justify-center gap-1">
                            مشاهده
                        </a>
                        <button onclick='toggleCart(${JSON.stringify(deal)})' class="py-2.5 px-3 rounded-xl ${isInCart ? 'bg-amber-500 text-black font-black' : 'bg-white hover:bg-gray-100 text-black font-black'} text-xs text-center transition shadow-md flex items-center justify-center gap-1">
                            <i class="fa-solid ${isInCart ? 'fa-check' : 'fa-plus'} text-xs"></i>
                            ${isInCart ? 'انتخاب شد' : 'اجاره'}
                        </button>
                    </div>
                </div>
                `;
            }).join('');
        }

        function renderModalCollections(query = '') {
            const container = document.getElementById('modalCollectionsList');
            const filtered = COLLECTIONS.filter(c => c.name.toLowerCase().includes(query.toLowerCase()));

            let html = `
                <div onclick="selectCollection('all')" class="collection-item p-3 rounded-2xl flex items-center justify-between cursor-pointer ${selectedCollection === 'all' ? 'border-amber-500/80 bg-[#232733]' : ''}">
                    <span class="text-xs font-bold text-gray-200">همه کالکشن‌ها</span>
                    <span class="w-8 h-8 rounded-full bg-amber-500/10 text-amber-400 flex items-center justify-center text-xs font-bold">${DEALS.length}</span>
                </div>
            `;

            html += filtered.map(col => `
                <div onclick="selectCollection('${col.name}')" class="collection-item p-3 rounded-2xl flex items-center justify-between cursor-pointer ${selectedCollection === col.name ? 'border-amber-500/80 bg-[#232733]' : ''}">
                    <span class="text-xs font-bold text-gray-200">${col.name}</span>
                    <div class="flex items-center gap-2">
                        <span class="text-[11px] text-gray-400 bg-gray-900 px-2 py-0.5 rounded-md">${col.count}</span>
                        <img src="${col.image}" alt="${col.name}" class="w-8 h-8 rounded-full object-contain p-1 bg-gray-900 border border-gray-700/60 shadow" onerror="this.src='https://marketapp.org/favicon.ico'">
                    </div>
                </div>
            `).join('');

            container.innerHTML = html;
        }

        function openModal() {
            triggerHaptic('light');
            document.getElementById('collectionModal').classList.remove('hidden');
            renderModalCollections();
        }

        function closeModal() {
            triggerHaptic('light');
            document.getElementById('collectionModal').classList.add('hidden');
        }

        function selectCollection(colName) {
            triggerHaptic('selection');
            selectedCollection = colName;
            document.getElementById('selectedColText').innerText = colName === 'all' ? 'کالکشن‌ها' : colName;
            closeModal();
            applyFilters();
        }

        document.getElementById('modalSearchInput').addEventListener('input', (e) => {
            renderModalCollections(e.target.value.trim());
        });

        document.getElementById('collectionModal').addEventListener('click', (e) => {
            if (e.target.id === 'collectionModal') closeModal();
        });

        function filterType(type) {
            triggerHaptic('selection');
            selectedType = type;
            document.querySelectorAll('.type-btn').forEach(btn => {
                btn.classList.remove('bg-amber-500', 'text-black');
                btn.classList.add('bg-[#1d2232]', 'text-gray-300');
            });
            event.target.classList.remove('bg-[#1d2232]', 'text-gray-300');
            event.target.classList.add('bg-amber-500', 'text-black');
            applyFilters();
        }

        function getFilteredDeals() {
            const query = document.getElementById('searchInput').value.trim().toLowerCase();
            return DEALS.filter(d => {
                const matchQuery = d.name.toLowerCase().includes(query) || d.number.includes(query) || d.gift_title.toLowerCase().includes(query);
                if (!matchQuery) return false;
                if (selectedType === 'rare' && d.rarity === '') return false;
                if (selectedType === 'favs' && !favorites.includes(d.name)) return false;
                if (selectedCollection !== 'all' && d.gift_title !== selectedCollection) return false;
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
        f"🦆 <b>گزارش موجودی جدید ۲۰۰ گیفت در Duck Store</b>\n"
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
    print("  🦆 DUCK STORE TURBO SCRAPER (200 ITEMS + CLOUDFLARE) 🦆")
    print("═" * 65 + "\n")

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
        except Exception:
            browser = await p.chromium.launch(headless=True, channel="chrome")

        page = await browser.new_page()
        print("🌐 بارگذاری اولیه صفحه...")
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

        sorted_deals = sorted(
            deals_found,
            key=lambda x: (
                x["gift_title"],
                int(re.sub(r"\D", "", x["number"]))
                if re.sub(r"\D", "", x["number"])
                else 0,
            ),
        )

        generate_duck_store_html(sorted_deals)

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
            f"\n⚡ فروشگاه Duck Store با اتصال به Cloudflare آماده شد!"
        )
        send_telegram_package(sorted_deals)


if __name__ == "__main__":
    asyncio.run(main())
