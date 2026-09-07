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
    "TELEGRAM_CHANNEL_LINK": "https://t.me/duck_storee",
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
<title>Duck Store | خدمات تلگرام</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#08090b; --glass:rgba(255,255,255,.045); --glass2:rgba(255,255,255,.075);
  --border:rgba(255,255,255,.09); --border2:rgba(255,255,255,.18);
  --text:#f3f3f5; --dim:#98979f; --faint:#5c5b63;
  --good:#3ddc97; --r-lg:22px; --r-md:16px;
}
*{-webkit-tap-highlight-color:transparent;}
html,body{background:var(--bg);}
body{
  font-family:'Vazirmatn',sans-serif; color:var(--text); -webkit-touch-callout:none; user-select:none;
  background: radial-gradient(circle at 12% -10%, rgba(255,255,255,.05) 0%, transparent 45%), var(--bg);
  min-height:100vh;
}
.glass{ background:var(--glass); border:1px solid var(--border); backdrop-filter:blur(22px); border-radius:26px; }
.glass2{ background:var(--glass2); border:1px solid var(--border2); backdrop-filter:blur(28px); }
.glass-tight{ border-radius:var(--r-md); }
.btn-inv{ background:var(--text); color:#0a0a0b; font-weight:800; border-radius:9999px; }
.btn-ghost{ background:var(--glass); border:1px solid var(--border2); color:var(--text); border-radius:9999px; }
.chip{ border-radius:9999px; font-weight:800; font-size:11px; padding:8px 15px; border:1px solid var(--border); background:var(--glass); color:var(--dim); white-space:nowrap; }
.chip.active{ background:var(--text); color:#0a0a0b; border-color:var(--text); }
.nav-tab{ color:var(--faint); }
.nav-tab.active{ color:var(--text); }
.gift-card{ background:var(--glass); border:1px solid var(--border); border-radius:var(--r-lg); overflow:hidden; }
.badge-disc{ background:rgba(61,220,151,.16); color:var(--good); font-weight:800; font-size:10px; border:1px solid rgba(61,220,151,.25); border-radius:8px; padding:2px 7px; }
.sheet-backdrop{ background:rgba(4,4,5,.75); backdrop-filter:blur(8px); }
.toast-wrap{ position:fixed; top:14px; left:50%; transform:translateX(-50%); z-index:90; width:calc(100% - 32px); max-width:420px; }
.toast{ background:#131418; border:1px solid var(--border2); border-radius:16px; padding:11px 16px; font-size:12px; font-weight:700; color:var(--text); }
input[type=number]::-webkit-inner-spin-button, input[type=number]::-webkit-outer-spin-button { -webkit-appearance:none; margin:0; }
</style>
</head>
<body class="min-h-screen pb-44 select-none">

<div class="toast-wrap" id="toastWrap"></div>

<!-- هدر -->
<header class="sticky top-0 z-30 px-4 py-3 bg-[#08090b]/85 backdrop-blur-xl border-b border-white/5">
  <div class="max-w-xl mx-auto flex items-center justify-between">
    <div class="flex items-center gap-3">
      <div class="w-10 h-10 rounded-2xl glass2 flex items-center justify-center text-lg">🦆</div>
      <div>
        <h1 class="text-[10px] font-black uppercase tracking-widest text-slate-400">DUCK STORE</h1>
        <p id="topGreeting" class="text-sm font-black">مرجع خدمات تلگرام</p>
      </div>
    </div>
    <div class="flex items-center gap-2">
      <!-- دکمه گردونه شانس -->
      <button onclick="openSpinModal()" class="px-3 py-1.5 rounded-xl bg-amber-400/10 text-amber-300 border border-amber-400/20 text-xs font-black flex items-center gap-1.5">
        <i class="fa-solid fa-dice text-amber-400"></i>
        <span>گردونه شانس</span>
      </button>
      <a href="https://t.me/Zanjani_a" class="w-9 h-9 rounded-full btn-ghost flex items-center justify-center">
        <i class="fa-brands fa-telegram text-sky-400 text-sm"></i>
      </a>
    </div>
  </div>
</header>

<main class="max-w-xl mx-auto px-4 mt-4 space-y-4">

<!-- ۱. صفحه خانه -->
<section id="view-home" class="space-y-4">
  <div class="grid grid-cols-3 gap-2.5 text-center">
    <div class="glass glass-tight p-3"><p class="text-lg font-black">__TOTAL_COUNT__</p><p class="text-[10px] text-slate-400">گیفت فعال</p></div>
    <div class="glass glass-tight p-3"><p class="text-lg font-black text-emerald-400">-50%</p><p class="text-[10px] text-slate-400">حداقل تخفیف</p></div>
    <div class="glass glass-tight p-3"><p class="text-lg font-black">کارت‌به‌کارت</p><p class="text-[10px] text-slate-400">فاکتور هوشمند</p></div>
  </div>

  <div>
    <div class="flex items-center justify-between mb-2.5 px-1">
      <h3 class="text-sm font-black">دسترسی سریع</h3>
    </div>
    <div class="grid grid-cols-4 gap-2.5">
      <button onclick="goServices('stars')" class="glass glass-tight p-3 flex flex-col items-center gap-1.5"><span class="text-xl">⭐</span><span class="text-[10px] font-bold">استارز</span></button>
      <button onclick="goServices('premium')" class="glass glass-tight p-3 flex flex-col items-center gap-1.5"><span class="text-xl">💎</span><span class="text-[10px] font-bold">پرمیوم</span></button>
      <button onclick="switchView('market')" class="glass glass-tight p-3 flex flex-col items-center gap-1.5"><span class="text-xl">🎁</span><span class="text-[10px] font-bold">گیفت</span></button>
      <button onclick="goServices('custom_0')" class="glass glass-tight p-3 flex flex-col items-center gap-1.5"><span class="text-xl">🚀</span><span class="text-[10px] font-bold">خدمات</span></button>
    </div>
  </div>

  <div>
    <h3 class="text-sm font-black mb-2.5 px-1">تازه‌ترین گیفت‌ها</h3>
    <div id="homeGiftScroll" class="flex gap-2.5 overflow-x-auto pb-1 -mx-4 px-4"></div>
  </div>
</section>

<!-- ۲. بازار گیفت‌ها -->
<section id="view-market" class="hidden space-y-3">
  <div class="glass glass-tight p-3 flex items-center gap-2">
    <div class="relative flex-1">
      <i class="fa-solid fa-magnifying-glass absolute right-3 top-2.5 text-xs text-slate-500"></i>
      <input type="text" id="searchInput" placeholder="جستجوی نام یا شماره گیفت..." class="w-full bg-transparent rounded-xl pr-8 pl-2 py-1.5 text-xs">
    </div>
    <button onclick="openModal()" class="px-3 py-1.5 rounded-xl btn-ghost text-xs font-bold whitespace-nowrap"><span id="selectedColText">کالکشن‌ها</span> ▾</button>
  </div>

  <div class="flex items-center gap-2 overflow-x-auto pb-1">
    <button onclick="filterType('all', this)" class="type-btn chip active">همه (__TOTAL_COUNT__)</button>
    <button onclick="filterType('rare', this)" class="type-btn chip">💎 کمیاب‌ها (__RARE_COUNT__)</button>
    <button onclick="filterType('favs', this)" class="type-btn chip">❤️ نشان‌شده‌ها (<span id="favCount">0</span>)</button>
  </div>

  <div id="dealsGrid" class="grid grid-cols-2 gap-3"></div>
</section>

<!-- ۳. خدمات داینامیک -->
<section id="view-services" class="hidden space-y-4">
  <div id="servicesTabsBar" class="flex items-center gap-1.5 overflow-x-auto pb-1">
    <button onclick="switchServiceSubTab('stars')" id="subtab-stars" class="service-subtab-btn chip active">استارز</button>
    <button onclick="switchServiceSubTab('premium')" id="subtab-premium" class="service-subtab-btn chip">پرمیوم</button>
  </div>

  <div id="subview-stars" class="space-y-3">
    <div class="glass glass-tight p-4 space-y-3">
      <h4 class="text-xs font-bold">⭐ استارز دلخواه تلگرام</h4>
      <div class="flex items-center gap-2">
        <input type="number" id="customStarsInput" min="50" placeholder="حداقل ۵۰ عدد..." class="flex-1 glass glass-tight px-3.5 py-2 text-xs font-bold">
        <button onclick="submitCustomStars()" class="px-4 py-2 rounded-xl btn-inv text-xs whitespace-nowrap">صدور فاکتور</button>
      </div>
      <div id="customStarsCalcBox" class="p-2.5 rounded-xl hidden items-center justify-between bg-white/[0.04]">
        <span class="text-xs text-slate-400">مبلغ واریزی:</span>
        <span id="customStarsPrice" class="text-xs font-black text-amber-400">0 تومان</span>
      </div>
    </div>
    <div id="starsPackagesList" class="space-y-2"></div>
  </div>

  <div id="subview-premium" class="hidden space-y-2.5">
    <div id="premiumOptionsList" class="space-y-2.5"></div>
  </div>

  <div id="subview-custom" class="hidden space-y-3">
    <div id="customCategoryItemsList" class="space-y-3"></div>
  </div>
</section>

<!-- ۴. سبد خرید -->
<section id="view-cart" class="hidden space-y-4">
  <div class="glass glass-tight p-4 space-y-3">
    <div class="flex items-center justify-between border-b pb-3 border-white/10">
      <h3 class="text-sm font-black">سبد خرید (<span id="cartCountHeader">0</span>)</h3>
      <button onclick="clearCart()" class="text-xs text-rose-400">خالی کردن</button>
    </div>

    <div id="cartItemsList" class="space-y-2.5 max-h-64 overflow-y-auto"></div>
    <div id="cartEmptyState" class="hidden text-center py-8 text-xs text-slate-400">سبد خرید شما خالی است</div>

    <div class="pt-3 border-t border-white/10 flex items-center justify-between">
      <div>
        <p class="text-[10px] text-slate-400">مبلغ نهایی سفارش:</p>
        <p id="cartTotal" class="text-base font-black text-cyan-400">0 تومان</p>
      </div>
      <button onclick="checkoutCart()" class="py-3 px-6 rounded-2xl btn-inv text-xs font-black">صدور فاکتور کارت‌به‌کارت</button>
    </div>
  </div>
</section>

<!-- ۵. پروفایل کاربر (شامل لینک زیرمجموعه‌گیری و پیگیری سفارشات) -->
<section id="view-profile" class="hidden space-y-4">
  <div class="glass p-6 space-y-5">
    <div class="flex items-center gap-4">
      <div class="w-16 h-16 rounded-full glass2 flex items-center justify-center text-3xl">👤</div>
      <div>
        <h2 id="profileName" class="text-base font-black">کاربر گرامی</h2>
        <p id="profileUsername" class="text-xs text-slate-400">@guest</p>
        <span class="inline-block px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-white/5 text-slate-300 mt-1 border border-white/10">عضو طلایی</span>
      </div>
    </div>

    <!-- بخش زیرمجموعه‌گیری اختصاصی -->
    <div class="p-4 rounded-2xl bg-white/[0.02] border border-cyan-500/20 space-y-2.5 text-xs">
      <div class="flex items-center justify-between">
        <span class="font-bold text-cyan-400 flex items-center gap-1.5"><i class="fa-solid fa-users"></i><span>سیستم زیرمجموعه‌گیری</span></span>
        <span class="text-[11px] font-bold text-slate-300">دعوت‌شده‌ها: <b id="userRefCount" class="text-amber-400">0</b> نفر</span>
      </div>
      <p class="text-[10px] text-slate-400">با دعوت دوستان، اعتبار هدیه و تخفیف ویژه در خریدها دریافت کنید:</p>
      <div class="flex gap-2">
        <input type="text" id="userRefLinkInput" readonly class="glass glass-tight px-2.5 py-1.5 text-xs w-full text-left dir-ltr font-mono text-slate-300">
        <button onclick="copyRefLink()" class="px-3 py-1.5 bg-cyan-400 text-slate-950 rounded-xl font-bold whitespace-nowrap">کپی لینک</button>
      </div>
    </div>

    <!-- پیگیری تاریخچه سفارشات کاربر -->
    <div class="p-4 rounded-2xl bg-white/[0.02] border border-white/5 space-y-3 text-xs">
      <h3 class="font-black text-slate-300 flex items-center gap-1.5"><i class="fa-solid fa-receipt text-purple-400"></i><span>سفارش‌های قبلی من</span></h3>
      <div id="userOrdersHistoryList" class="space-y-2 max-h-48 overflow-y-auto">
        <p class="text-slate-500 text-[11px] text-center py-2">در حال بارگذاری سوابق...</p>
      </div>
    </div>

    <div class="pt-2 space-y-2">
      <a href="https://t.me/duck_storee" class="w-full py-3 rounded-2xl btn-ghost text-xs font-bold flex items-center justify-center gap-2">
        <i class="fa-brands fa-telegram text-sky-400"></i><span>عضویت در کانال رسمی تلگرام</span>
      </a>
    </div>
  </div>
</section>

</main>

<!-- نوار پاپ‌آپ شناور سبد خرید -->
<div id="floatingCartBar" class="fixed bottom-20 inset-x-4 max-w-lg mx-auto z-40 bg-[#0d1017]/95 backdrop-blur-xl border border-cyan-500/40 p-3.5 rounded-[22px] shadow-2xl transition-all duration-300 transform translate-y-44 opacity-0 flex items-center justify-between">
  <div class="flex items-center gap-3">
    <div class="w-10 h-10 rounded-2xl bg-cyan-400 text-black flex items-center justify-center font-black text-sm">
      <span id="floatingCartCount">0</span>
    </div>
    <div>
      <p class="text-xs font-bold text-white">سبد خرید شما</p>
      <p id="floatingCartPrice" class="text-xs text-cyan-400 font-black">0 تومان</p>
    </div>
  </div>
  <div class="flex items-center gap-2">
    <button onclick="switchView('cart')" class="px-3 py-2 rounded-xl btn-ghost text-xs font-bold">نمایش سبد</button>
    <button onclick="checkoutCart()" class="px-4 py-2 rounded-xl btn-inv text-xs font-black">تسویه کارت‌به‌کارت</button>
  </div>
</div>

<!-- نوار ناوبری پایین -->
<nav class="fixed bottom-3 inset-x-4 max-w-xl mx-auto z-40 glass2 px-2 py-2 flex items-center justify-around rounded-[30px]">
  <button onclick="switchView('home')" id="nav-home" class="nav-tab active px-3.5 py-2 flex flex-col items-center gap-1 text-[10px] font-bold"><i class="fa-solid fa-house text-sm"></i><span>خانه</span></button>
  <button onclick="switchView('market')" id="nav-market" class="nav-tab px-3.5 py-2 flex flex-col items-center gap-1 text-[10px] font-bold"><i class="fa-solid fa-gift text-sm"></i><span>گیفت‌ها</span></button>
  <button onclick="switchView('services')" id="nav-services" class="nav-tab px-3.5 py-2 flex flex-col items-center gap-1 text-[10px] font-bold"><i class="fa-solid fa-bolt text-sm"></i><span>خدمات</span></button>
  <button onclick="switchView('cart')" id="nav-cart" class="nav-tab relative px-3.5 py-2 flex flex-col items-center gap-1 text-[10px] font-bold"><i class="fa-solid fa-cart-shopping text-sm"></i><span>سبد</span></button>
  <button onclick="switchView('profile')" id="nav-profile" class="nav-tab px-3.5 py-2 flex flex-col items-center gap-1 text-[10px] font-bold"><i class="fa-solid fa-user text-sm"></i><span>حساب</span></button>
</nav>

<!-- 🎰 مودال گردونه شانس روزانه -->
<div id="spinModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 sheet-backdrop hidden">
  <div class="glass2 w-full max-w-xs rounded-[28px] p-6 text-center space-y-4 bg-[#10121a]">
    <div class="text-4xl animate-bounce">🎰</div>
    <div>
      <h3 class="text-sm font-black text-white">گردونه شانس روزانه</h3>
      <p class="text-[11px] text-slate-400 mt-1">هر ۲۴ ساعت یک شانس برای دریافت تخفیف ویژه دارید!</p>
    </div>
    <div id="spinWheelVisual" class="w-32 h-32 rounded-full border-4 border-amber-400 mx-auto flex items-center justify-center text-xs font-bold text-amber-300 bg-amber-500/10 shadow-lg">
      🎁 جایزه مخفی
    </div>
    <button id="spinActionBtn" onclick="runDailySpin()" class="w-full py-3 bg-amber-400 text-slate-950 font-black rounded-xl text-xs">چرخاندن گردونه</button>
    <button onclick="closeSpinModal()" class="text-xs text-slate-400 hover:underline">بستن</button>
  </div>
</div>

<!-- مودال جزئیات گیفت -->
<div id="quickViewSheet" class="fixed inset-0 z-50 flex items-center justify-center p-4 sheet-backdrop hidden">
  <div class="glass2 w-full max-w-sm rounded-[28px] overflow-hidden flex flex-col shadow-2xl p-0 bg-[#111317]">
    <div class="relative w-full h-56 flex items-center justify-center" id="qvImageWrap">
      <button onclick="closeQuickView()" class="absolute top-3 left-3 w-8 h-8 rounded-full bg-black/50 text-white flex items-center justify-center z-10"><i class="fa-solid fa-xmark text-xs"></i></button>
      <span id="qvDiscountBadge" class="absolute bottom-3 right-3 badge-disc"></span>
      <img id="qvImage" src="" class="w-36 h-36 object-contain">
    </div>
    <div class="p-5 space-y-4 text-right">
      <div>
        <h3 id="qvTitle" class="text-base font-black"></h3>
        <p id="qvNumber" class="text-xs text-slate-400 mt-0.5"></p>
      </div>
      <div class="p-3.5 rounded-2xl bg-[#181a20] flex items-center justify-between border border-white/5">
        <span class="text-xs text-slate-400 font-bold">مبلغ اجاره ماهانه</span>
        <span id="qvPrice" class="text-sm font-black text-amber-400"></span>
      </div>
      <div class="flex items-center gap-2">
        <button onclick="addQVToCart()" class="flex-1 py-3.5 btn-inv text-xs flex items-center justify-center gap-1.5"><i class="fa-solid fa-cart-shopping"></i><span id="qvAddCartText">افزودن به سبد</span></button>
        <a id="qvTgLink" href="#" target="_blank" class="flex-1 py-3.5 btn-ghost text-xs font-bold text-center">مشاهده در تلگرام</a>
      </div>
    </div>
  </div>
</div>

<!-- مودال کالکشن همراه با دکمه شکار گیفت 🔔 -->
<div id="collectionModal" class="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 sheet-backdrop hidden">
  <div class="glass2 w-full sm:max-w-md rounded-t-[28px] sm:rounded-[28px] overflow-hidden flex flex-col max-h-[78vh] bg-[#0c0d10]">
    <div class="px-5 py-4 flex items-center justify-between border-b border-white/10">
      <button onclick="closeModal()" class="w-7 h-7 rounded-full btn-ghost flex items-center justify-center"><i class="fa-solid fa-xmark text-xs"></i></button>
      <h3 class="text-xs font-black">کالکشن‌ها و شکار گیفت</h3>
      <div class="w-7"></div>
    </div>
    <div id="modalCollectionsList" class="p-3 space-y-1.5 overflow-y-auto flex-1"></div>
    <div class="p-3 border-t border-white/10">
      <button onclick="closeModal();" class="w-full py-2.5 btn-inv text-xs">بستن</button>
    </div>
  </div>
</div>

<script>
let tgUser = null;
function getTgUser() {
  if (tgUser) return tgUser;
  if (window.Telegram?.WebApp?.initDataUnsafe?.user) {
    tgUser = window.Telegram.WebApp.initDataUnsafe.user;
    return tgUser;
  }
  return null;
}

if (window.Telegram && window.Telegram.WebApp) {
  try {
    window.Telegram.WebApp.ready();
    window.Telegram.WebApp.expand();
    getTgUser();
  } catch(e) {}
}

function toast(msg) {
  const wrap = document.getElementById('toastWrap');
  const el = document.createElement('div');
  el.className = 'toast';
  el.innerHTML = `<span>${msg}</span>`;
  wrap.appendChild(el);
  setTimeout(() => el.remove(), 2500);
}

const WORKER_URL = "__WORKER_URL__";
const DEALS = Array.isArray(__DEALS_JSON__) ? __DEALS_JSON__ : [];
const COLLECTIONS = Array.isArray(__COLLECTIONS_JSON__) ? __COLLECTIONS_JSON__ : [];

let SETTINGS = {
  ratePerStar: 1450, prem3: 620000, prem6: 950000, prem12: 1690000, giftMonthlyPrice: 160000,
  customServices: []
};

let favorites = JSON.parse(localStorage.getItem('duck_favs_v4') || '[]');
let cart = JSON.parse(localStorage.getItem('duck_cart_v4') || '[]');
let selectedType = 'all';
let activeQVDeal = null;

function fmtMoney(n) { return Math.round(Number(n)||0).toLocaleString('en-US'); }

function switchView(view) {
  ['home','market','services','cart','profile'].forEach(v => {
    document.getElementById('view-' + v).classList.toggle('hidden', v !== view);
    document.getElementById('nav-' + v).classList.toggle('active', v === view);
  });
  if (view === 'cart') renderCart();
  if (view === 'profile') loadUserData();
  window.scrollTo({top:0, behavior:'instant'});
}
function goServices(subtab) {
  switchView('services');
  switchServiceSubTab(subtab);
}

function renderHome() {
  const scrollHtml = DEALS.slice(0, 10).map(d => `
    <div class="glass rounded-2xl overflow-hidden flex-shrink-0 w-32 cursor-pointer" onclick="openQuickView('${d.name}')">
      <div class="w-32 h-32 flex items-center justify-center p-2" style="background:${d.bg_color || '#1b1d28'}">
        <img src="${d.image_url}" class="w-24 h-24 object-contain">
      </div>
      <div class="p-2 text-right">
        <p class="text-[10px] font-black truncate">${d.gift_title}</p>
        <span class="badge-disc mt-1 inline-block">${d.discount}</span>
      </div>
    </div>`).join('');
  document.getElementById('homeGiftScroll').innerHTML = scrollHtml;
}

function dealCardHtml(d, idx) {
  const isFav = favorites.includes(d.name);
  const bg = d.bg_color || '#1e2433';
  const priceFormatted = fmtMoney(SETTINGS.giftMonthlyPrice || 160000);
  return `
  <div class="gift-card cursor-pointer" onclick="openQuickView('${d.name}')">
    <div class="relative w-full aspect-square flex items-center justify-center overflow-hidden" style="background-color:${bg};">
      <button onclick="event.stopPropagation(); toggleFavorite('${d.name}')" class="absolute top-2.5 left-2.5 w-7 h-7 rounded-full bg-black/40 text-xs flex items-center justify-center">
        <i class="fa-solid fa-heart" style="color:${isFav ? '#f4685f' : 'rgba(255,255,255,.6)'}"></i>
      </button>
      <span class="absolute bottom-2.5 right-2.5 badge-disc">${d.discount || '-50%'}</span>
      <img src="${d.image_url}" class="w-28 h-28 object-contain">
    </div>
    <div class="p-3 text-right">
      <p class="text-xs font-black truncate">${d.gift_title}</p>
      <p class="text-[10px] text-slate-400 mt-1 dir-ltr text-right">#${d.number}</p>
      <p class="text-[10px] font-bold mt-2 text-slate-400">از <span class="text-white font-black">${priceFormatted}</span> تومان/ماه</p>
    </div>
  </div>`;
}

function renderCards(list) {
  document.getElementById('dealsGrid').innerHTML = list.map(dealCardHtml).join('');
}

function getFilteredDeals() {
  const q = (document.getElementById('searchInput')?.value || '').trim().toLowerCase();
  return DEALS.filter(d => {
    if (!d.name.toLowerCase().includes(q) && !d.number.includes(q)) return false;
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
  if (idx >= 0) favorites.splice(idx, 1);
  else favorites.push(name);
  localStorage.setItem('duck_favs_v4', JSON.stringify(favorites));
  renderCards(getFilteredDeals());
  document.getElementById('favCount').innerText = favorites.length;
}

function openQuickView(name) {
  const d = DEALS.find(x => x.name === name);
  if (!d) return;
  activeQVDeal = d;
  document.getElementById('qvImageWrap').style.backgroundColor = d.bg_color || '#1e2433';
  document.getElementById('qvImage').src = d.image_url;
  document.getElementById('qvTitle').innerText = d.gift_title;
  document.getElementById('qvNumber').innerText = `شماره #${d.number}`;
  document.getElementById('qvDiscountBadge').innerText = d.discount || '-50%';
  document.getElementById('qvTgLink').href = d.tg_link;
  document.getElementById('qvPrice').innerText = fmtMoney(SETTINGS.giftMonthlyPrice) + ' تومان';
  document.getElementById('quickViewSheet').classList.remove('hidden');
}

function closeQuickView() {
  document.getElementById('quickViewSheet').classList.add('hidden');
}

function addQVToCart() {
  if (!activeQVDeal) return;
  cart.push({ name: activeQVDeal.name, price: Number(SETTINGS.giftMonthlyPrice) });
  localStorage.setItem('duck_cart_v4', JSON.stringify(cart));
  toast('به سبد خرید اضافه شد');
  closeQuickView();
  updateFloatingCart();
}

function updateFloatingCart() {
  const bar = document.getElementById('floatingCartBar');
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
    <div class="glass glass-tight p-3 flex items-center justify-between">
      <p class="text-xs font-bold">${c.name}</p>
      <button onclick="cart.splice(${i},1);localStorage.setItem('duck_cart_v4',JSON.stringify(cart));renderCart();updateFloatingCart();" class="text-rose-400">✕</button>
    </div>
  `).join('');
  const total = cart.reduce((s, c) => s + (Number(c.price)||0), 0);
  document.getElementById('cartTotal').innerText = fmtMoney(total) + ' تومان';
}

function clearCart() {
  cart = [];
  localStorage.setItem('duck_cart_v4', JSON.stringify(cart));
  renderCart();
  updateFloatingCart();
}

// ثبت سفارش به ربات تلگرام
async function submitOrderToBot(items, totalPrice, itemsText) {
  const u = getTgUser();
  if (!u) {
    alert("⚠️ لطفاً مینی‌اپ را داخل ربات تلگرام باز کنید.");
    return;
  }

  const payload = {
    userId: u.id,
    userName: `${u.first_name || ''} ${u.last_name || ''}`.trim() || u.username,
    items: items,
    itemsText: itemsText,
    totalPrice: totalPrice
  };

  try {
    toast("در حال صدور فاکتور...");
    const res = await fetch(`${WORKER_URL}/api/order/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      alert("✅ فاکتور و شماره کارت در چت ربات برای شما ارسال شد!\nلطفاً پس از واریز، عکس فیش را بفرستید.");
      if (window.Telegram?.WebApp?.close) window.Telegram.WebApp.close();
    } else {
      alert("خطا در صدور فاکتور.");
    }
  } catch(e) {
    alert("خطای اتصال به سرور.");
  }
}

function checkoutCart() {
  if (cart.length === 0) return alert("سبد خرید خالی است!");
  const total = cart.reduce((s, c) => s + (Number(c.price)||0), 0);
  const itemsText = cart.map((c, i) => `${i + 1}. 🎁 ${c.name}`).join("\n");
  submitOrderToBot(cart, total, itemsText);
}

function submitCustomStars() {
  const qty = parseInt(document.getElementById('customStarsInput').value, 10) || 0;
  if (qty < 50) return alert("حداقل ۵۰ استارز وارد کنید");
  const total = qty * (Number(SETTINGS.ratePerStar) || 1450);
  submitOrderToBot([{ name: `${qty} استارز تلگرام`, price: total }], total, `⭐ بسته ${qty} عددی استارز تلگرام`);
}

function submitStarsPackage(qty) {
  const total = qty * (Number(SETTINGS.ratePerStar) || 1450);
  submitOrderToBot([{ name: `${qty} استارز تلگرام`, price: total }], total, `⭐ بسته ${qty} عددی استارز تلگرام`);
}

function submitPremiumOrder(label, price) {
  submitOrderToBot([{ name: `اشتراک تلگرام پرمیوم ${label}`, price: price }], price, `👑 اشتراک ${label} تلگرام پرمیوم`);
}

function submitCustomServiceOrder(catTitle, itemName, unitPrice, inputId, minQ, promptId, promptLabel) {
  const input = document.getElementById(inputId);
  let qty = parseInt(input ? input.value : minQ, 10) || minQ;
  if (qty < minQ) qty = minQ;

  let extra = "";
  if (promptLabel) {
    const pEl = document.getElementById(promptId);
    const pVal = pEl ? pEl.value.trim() : "";
    if (!pVal) {
      alert(`لطفاً فیلد «${promptLabel}» را تکمیل کنید.`);
      if (pEl) pEl.focus();
      return;
    }
    extra = `\n📌 ${promptLabel}: ${pVal}`;
  }

  const total = qty * unitPrice;
  submitOrderToBot([{ name: `${itemName} (${qty} عدد)`, price: total }], total, `🚀 ${catTitle} - ${itemName}\nتعداد: ${qty} عدد${extra}`);
}

// رندر خدمات سفارشی
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

function switchServiceSubTab(tab) {
  document.querySelectorAll('.service-subtab-btn').forEach(btn => btn.classList.remove('active'));
  document.getElementById('subtab-' + tab)?.classList.add('active');
  const isCustom = String(tab).startsWith('custom_');
  document.getElementById('subview-stars').classList.toggle('hidden', tab !== 'stars');
  document.getElementById('subview-premium').classList.toggle('hidden', tab !== 'premium');
  document.getElementById('subview-custom').classList.toggle('hidden', !isCustom);
  if (isCustom) renderCustomCategory(parseInt(tab.replace('custom_', ''), 10) || 0);
}

function renderCustomCategory(idx) {
  const cat = (SETTINGS.customServices || [])[idx];
  if (!cat) return;
  const listContainer = document.getElementById('customCategoryItemsList');
  listContainer.innerHTML = (cat.items || []).map((item, i) => {
    const minQ = Math.max(1, Number(item.minQty) || 1);
    const price = Number(item.price) || 0;
    const inputId = `qty_${idx}_${i}`;
    const totalId = `total_${idx}_${i}`;
    const promptId = `prompt_${idx}_${i}`;
    const hasPrompt = item.inputPrompt && item.inputPrompt.trim() !== '';

    return `
      <div class="glass glass-tight p-4 space-y-3">
        <div class="flex items-center justify-between">
          <div><h4 class="text-xs font-black">${item.name}</h4><p class="text-[10px] text-slate-400">${item.duration || ''}</p></div>
          <span class="text-xs font-black text-amber-400">${fmtMoney(price)} ت</span>
        </div>
        ${hasPrompt ? `
          <div class="pt-1">
            <label class="block text-[10px] text-slate-400 mb-1 font-bold">${item.inputPrompt}:</label>
            <input id="${promptId}" type="text" placeholder="اینجا وارد کنید..." class="w-full bg-[#050711] border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white">
          </div>
        ` : ''}
        <div class="pt-3 border-t border-white/5 flex items-center justify-between">
          <div class="flex items-center gap-1.5 glass glass-tight px-2 py-1">
            <button onclick="let el=document.getElementById('${inputId}');let v=Math.max(${minQ},(parseInt(el.value)||${minQ})-1);el.value=v;document.getElementById('${totalId}').innerText=fmtMoney(v*${price})+' ت';" class="w-6 h-6 rounded bg-white/10">-</button>
            <input id="${inputId}" type="number" value="${minQ}" min="${minQ}" oninput="let v=Math.max(${minQ},parseInt(this.value)||${minQ});document.getElementById('${totalId}').innerText=fmtMoney(v*${price})+' ت';" class="w-10 text-center bg-transparent text-xs font-bold">
            <button onclick="let el=document.getElementById('${inputId}');let v=(parseInt(el.value)||${minQ})+1;el.value=v;document.getElementById('${totalId}').innerText=fmtMoney(v*${price})+' ت';" class="w-6 h-6 rounded bg-white/10">+</button>
            <span class="text-[9px] text-slate-400 mr-1">حداقل: ${minQ}</span>
          </div>
          <div class="flex items-center gap-2">
            <span id="${totalId}" class="text-xs font-black text-cyan-400">${fmtMoney(price * minQ)} ت</span>
            <button onclick="submitCustomServiceOrder('${cat.title}', '${item.name}', ${price}, '${inputId}', ${minQ}, '${promptId}', '${item.inputPrompt || ''}')" class="px-3.5 py-1.5 btn-inv text-xs">سفارش</button>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function renderStarsPackages() {
  const packs = [50, 100, 250, 500, 1000, 2500, 5000];
  document.getElementById('starsPackagesList').innerHTML = packs.map(p => `
    <div class="glass glass-tight p-3.5 flex items-center justify-between">
      <span class="text-xs font-bold">${p} Stars</span>
      <div class="flex items-center gap-2">
        <span class="text-xs font-black text-amber-400">${fmtMoney(p * Number(SETTINGS.ratePerStar))} ت</span>
        <button onclick="submitStarsPackage(${p})" class="px-3 py-1.5 btn-ghost text-xs font-bold">خرید</button>
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
    <div class="glass glass-tight p-3.5 flex items-center justify-between">
      <span class="text-xs font-bold">پرمیوم ${p.label}</span>
      <div class="flex items-center gap-2">
        <span class="text-xs font-black text-purple-400">${fmtMoney(p.price)} ت</span>
        <button onclick="submitPremiumOrder('${p.label}', ${p.price})" class="px-3 py-1.5 btn-ghost text-xs font-bold">خرید</button>
      </div>
    </div>
  `).join('');
}

// کالکشن‌ها همراه با زنگوله شکار گیفت 🔔
function openModal() {
  document.getElementById('collectionModal').classList.remove('hidden');
  renderModalCollections();
}
function closeModal() {
  document.getElementById('collectionModal').classList.add('hidden');
}
function renderModalCollections() {
  document.getElementById('modalCollectionsList').innerHTML = COLLECTIONS.map(col => `
    <div class="p-2.5 rounded-xl border flex items-center justify-between border-white/5 bg-[#12141a]">
      <div class="flex items-center gap-3">
        <img src="${col.image}" class="w-8 h-8 rounded-lg object-contain bg-white/5 p-1">
        <span class="text-xs font-bold">${col.name}</span>
      </div>
      <div class="flex items-center gap-2">
        <button onclick="toggleAlert('${col.name}')" class="px-2.5 py-1 rounded-lg bg-amber-400/10 text-amber-300 text-[10px] font-bold">
          <i class="fa-solid fa-bell"></i> شکار گیفت
        </button>
      </div>
    </div>
  `).join('');
}

async function toggleAlert(colName) {
  const u = getTgUser();
  if (!u) return alert("لطفاً داخل تلگرام باز کنید");
  try {
    const res = await fetch(`${WORKER_URL}/api/alert/toggle`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ userId: u.id, collection: colName })
    });
    const d = await res.json();
    if (d.active) toast(`اعلان شکار برای ${colName} فعال شد!`);
    else toast(`اعلان ${colName} غیرفعال شد.`);
  } catch(e) {}
}

// دریافت سوابق و رفرال کاربر
async function loadUserData() {
  const u = getTgUser();
  if (!u) return;

  const botName = "DuckStoreBot";
  const refLink = `https://t.me/${botName}?start=ref_${u.id}`;
  const refInput = document.getElementById("userRefLinkInput");
  if (refInput) refInput.value = refLink;

  try {
    const res = await fetch(`${WORKER_URL}/api/user-data?userId=${u.id}`);
    if (res.ok) {
      const data = await res.json();
      document.getElementById("userRefCount").innerText = data.refCount || 0;

      const oList = document.getElementById("userOrdersHistoryList");
      if (!data.orders || data.orders.length === 0) {
        oList.innerHTML = '<p class="text-slate-500 text-[11px] text-center py-2">هنوز سفارشی ثبت نکرده‌اید.</p>';
      } else {
        oList.innerHTML = data.orders.map(o => {
          const statusBadge = o.status === "approved"
            ? '<span class="text-emerald-400 font-bold">✅ تایید شد</span>'
            : (o.status === "rejected" ? '<span class="text-rose-400 font-bold">❌ رد شد</span>' : '<span class="text-amber-400 font-bold">⏳ در انتظار فیش</span>');
          return `
            <div class="p-2.5 rounded-xl bg-black/40 border border-white/5 space-y-1">
              <div class="flex justify-between items-center">
                <span class="font-mono font-bold">${o.id}</span>
                ${statusBadge}
              </div>
              <p class="text-slate-400 text-[10px]">${fmtMoney(o.totalPrice)} تومان</p>
            </div>
          `;
        }).join('');
      }
    }
  } catch(e) {}
}

function copyRefLink() {
  const input = document.getElementById("userRefLinkInput");
  if (input) {
    navigator.clipboard.writeText(input.value);
    toast("لینک دعوت اختصاصی شما کپی شد!");
  }
}

// گردونه شانس
function openSpinModal() {
  document.getElementById("spinModal").classList.remove("hidden");
}
function closeSpinModal() {
  document.getElementById("spinModal").classList.add("hidden");
}
async function runDailySpin() {
  const u = getTgUser();
  if (!u) return alert("لطفاً در تلگرام وارد شوید");
  const btn = document.getElementById("spinActionBtn");
  btn.disabled = true;
  btn.innerText = "در حال چرخیدن...";

  try {
    const res = await fetch(`${WORKER_URL}/api/spin-wheel`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ userId: u.id })
    });
    const d = await res.json();
    if (res.ok) {
      const prizes = ["کد تخفیف ۱۵٪: DUCK15", "کد تخفیف ۱۰٪: DUCK", "اعتبار هدیه", "۵٪ تخفیف پرمیوم"];
      const win = prizes[Math.floor(Math.random() * prizes.length)];
      document.getElementById("spinWheelVisual").innerText = win;
      alert(`🎉 تبریک! جایزه شما:\n${win}`);
    } else {
      alert(d.error || "خطا در گردونه");
    }
  } catch(e) {
    alert("خطای ارتباط با سرور");
  } finally {
    btn.disabled = false;
    btn.innerText = "چرخاندن گردونه";
  }
}

async function fetchCloudSettings() {
  try {
    const res = await fetch(`${WORKER_URL}/api/settings`);
    if (res.ok) {
      const data = await res.json();
      SETTINGS = { ...SETTINGS, ...data };
    }
  } catch(e) {}
  renderCards(getFilteredDeals());
  renderStarsPackages();
  renderPremiumOptions();
  renderServicesNavigation();
  updateFloatingCart();

  const u = getTgUser();
  if (u) {
    document.getElementById('profileName').innerText = `${u.first_name || ''} ${u.last_name || ''}`;
    document.getElementById('profileUsername').innerText = u.username ? `@${u.username}` : '';
    document.getElementById('profileUserId').innerText = u.id;
  }
}

renderHome();
fetchCloudSettings();
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
        f"🦆 <b>فروشگاه Duck Store فعال شد</b>\n"
        f"📅 <i>{timestamp}</i>\n\n"
        f"🌐 <b>لینک ورود به مینی‌اپ:</b>\n👉 <a href='{pages_url}'>{pages_url}</a>\n"
        f"🎯 موجودی کل: {len(deals)} مورد (کمیاب: {rare_count})\n"
    )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode({"chat_id": chat_id, "text": full_text, "parse_mode": "HTML"}).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload)
        with urllib.request.urlopen(req, timeout=15): pass
    except Exception: pass


async def main():
    deals_found: List[Dict[str, Any]] = []
    seen_links: Set[str] = set()
    browser = None

    print("\n" + "═" * 65)
    print("  🦆 DUCK STORE TURBO SCRAPER (INTEGRATED ADVANCED SUITE) 🦆")
    print("═" * 65 + "\n")

    launch_args = ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True, args=launch_args)
            page = await browser.new_page()

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
                            lines = [l.strip() for l in text.split("\n") if l.strip()]
                            name_candidates = [l for l in lines if not l.startswith("Days:") and not l.startswith("-") and not l.startswith("#") and l.lower() not in ["per day", "min. price"] and not re.match(r"^\d+(\.\d+)?$", l)]
                            gift_name = name_candidates[0] if name_candidates else "NFT Gift"

                            deal = {
                                "name": f"{gift_name} #{item_num}",
                                "gift_title": gift_name,
                                "number": str(item_num),
                                "discount": f"-{discount_val}%",
                                "tg_link": generate_tg_nft_link(gift_name, item_num),
                                "market_link": full_link,
                                "image_url": c.get("img") or "https://marketapp.org/favicon.ico",
                                "bg_color": "#1e2230",
                                "rarity": detect_rarity_badge(item_num),
                            }
                            seen_links.add(full_link)
                            deals_found.append(deal)
                            if len(deals_found) >= CONFIG["TARGET_DEALS_COUNT"]: break
                    else:
                        seen_links.add(full_link)

                await page.evaluate("window.scrollBy(0, window.innerHeight * 3);")
                await page.wait_for_timeout(350)
        finally:
            if browser: await browser.close()

        sorted_deals = list(reversed(deals_found))
        generate_duck_store_html(sorted_deals)
        print("\n⚡ تمام امکانات جدید با موفقیت بیلد و منتشر شدند!")
        send_telegram_package(sorted_deals)


if __name__ == "__main__":
    asyncio.run(main())
