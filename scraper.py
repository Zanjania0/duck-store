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
    """تولید وب‌سایت فروشگاهی Duck Store با عکس کالکشن‌ها و ناوبری ضدبلاک تلگرام"""
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
<title>Duck Store | خدمات تلگرام</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#08090b;
  --glass:rgba(255,255,255,.045); --glass2:rgba(255,255,255,.075);
  --border:rgba(255,255,255,.09); --border2:rgba(255,255,255,.18);
  --text:#f3f3f5; --dim:#98979f; --faint:#5c5b63;
  --accent:#38bdf8; --good:#3ddc97; --bad:#f4685f;
  --r-xl:28px; --r-lg:22px; --r-md:16px;
}
*{-webkit-tap-highlight-color:transparent;}
html,body{background:var(--bg);}
body{
  font-family:'Vazirmatn',-apple-system,BlinkMacSystemFont,sans-serif;
  color:var(--text); -webkit-touch-callout:none; user-select:none;
  background:
    radial-gradient(circle at 12% -10%, rgba(255,255,255,.05) 0%, transparent 45%),
    radial-gradient(circle at 100% 15%, rgba(255,255,255,.035) 0%, transparent 40%),
    radial-gradient(circle at 50% 110%, rgba(255,255,255,.03) 0%, transparent 50%),
    var(--bg);
  min-height:100vh;
}
::-webkit-scrollbar{width:3px;height:3px;}
::-webkit-scrollbar-thumb{background:rgba(255,255,255,.15);border-radius:9999px;}
.glass{
  background:var(--glass); border:1px solid var(--border);
  -webkit-backdrop-filter:blur(22px); backdrop-filter:blur(22px);
  border-radius:var(--r-xl);
}
.glass2{
  background:var(--glass2); border:1px solid var(--border2);
  -webkit-backdrop-filter:blur(28px); backdrop-filter:blur(28px);
}
.glass-tight{border-radius:var(--r-md);}
.hair{border-top:1px solid var(--border);}
.btn-inv{
  background:var(--text); color:#0a0a0b; font-weight:800;
  border-radius:9999px; transition:transform .15s ease, opacity .15s ease;
}
.btn-inv:active{transform:scale(.97); opacity:.85;}
.btn-ghost{
  background:var(--glass); border:1px solid var(--border2); color:var(--text);
  border-radius:9999px;
}
.btn-ghost:active{background:var(--glass2);}
.chip{
  border-radius:9999px; font-weight:800; font-size:11px; padding:8px 15px;
  border:1px solid var(--border); background:var(--glass); color:var(--dim);
  white-space:nowrap; transition:all .15s ease;
}
.chip.active{background:var(--text); color:#0a0a0b; border-color:var(--text);}
.nav-tab{color:var(--faint); transition:color .2s ease;}
.nav-tab.active{color:var(--text);}
.nav-tab .dot{width:4px;height:4px;border-radius:9999px;background:var(--text);opacity:0;transition:opacity .2s;}
.nav-tab.active .dot{opacity:1;}
.gift-card{
  background:var(--glass); border:1px solid var(--border); border-radius:var(--r-lg);
  overflow:hidden; transition:transform .15s ease, border-color .15s ease;
}
.gift-card:active{transform:scale(.97);}
.badge-disc{
  background:rgba(61,220,151,.16); color:var(--good); font-weight:800; font-size:10px;
  border:1px solid rgba(61,220,151,.25); border-radius:8px; padding:2px 7px;
  backdrop-filter:blur(6px); -webkit-backdrop-filter:blur(6px);
}
.sheet-backdrop{background:rgba(4,4,5,.75); -webkit-backdrop-filter:blur(8px); backdrop-filter:blur(8px);}
.fade-up{animation:fadeUp .3s cubic-bezier(.16,1,.3,1) both;}
@keyframes fadeUp{from{opacity:0; transform:translateY(12px)}to{opacity:1; transform:translateY(0)}}
.toast-wrap{position:fixed; top:14px; left:50%; transform:translateX(-50%); z-index:90; display:flex; flex-direction:column; gap:8px; width:calc(100% - 32px); max-width:420px; pointer-events:none;}
.toast{background:#131418; border:1px solid var(--border2); border-radius:16px; padding:11px 16px; font-size:12px; font-weight:700; color:var(--text); box-shadow:0 12px 30px rgba(0,0,0,.5); display:flex; align-items:center; gap:8px;}
.press:active{transform:scale(.96);}
input[type=number]::-webkit-inner-spin-button, input[type=number]::-webkit-outer-spin-button { -webkit-appearance:none; margin:0; }
</style>
</head>
<body class="min-h-screen pb-44 select-none">

<div class="toast-wrap" id="toastWrap"></div>

<!-- ۱. اسپلش لودینگ -->
<div id="loadingScreen" class="fixed inset-0 z-[80] flex flex-col items-center justify-center bg-[#08090b] px-6 transition-opacity duration-500">
  <div class="w-16 h-16 rounded-3xl glass2 flex items-center justify-center text-3xl">🦆</div>
  <h2 class="text-white font-black text-sm mt-5 tracking-widest">DUCK STORE</h2>
  <p class="text-[11px] mt-1.5" style="color:var(--faint)">در حال بارگذاری فروشگاه...</p>
  <div class="w-44 h-1 rounded-full overflow-hidden mt-5" style="background:rgba(255,255,255,.08)">
    <div id="loadingProgressBar" class="h-full bg-white transition-all duration-150" style="width:5%"></div>
  </div>
</div>

<!-- ۲. صفحه معرفی با دکمه "بزن بریم" -->
<div id="welcomeScreen" class="fixed inset-0 z-[75] hidden items-center justify-center sheet-backdrop p-5 opacity-0 transition-all duration-500">
  <div class="w-full max-w-sm glass2 rounded-[28px] p-6 flex flex-col items-center text-center space-y-5 fade-up">
    <div class="w-16 h-16 rounded-3xl bg-white/5 border border-white/10 flex items-center justify-center text-3xl">🦆</div>
    <div>
      <span class="text-[10px] font-black tracking-widest" style="color:var(--faint)">DUCK STORE</span>
      <h2 class="text-base font-black mt-1">به داک استور خوش اومدی</h2>
      <p class="text-xs mt-1.5" style="color:var(--dim)">مرجع اجاره گیفت، استارز و خدمات تلگرام</p>
    </div>
    <div class="w-full space-y-2 text-right text-xs">
      <div class="p-3 rounded-2xl glass glass-tight flex items-center gap-3">
        <span class="text-xl">🎁</span>
        <div><p class="font-bold">اجاره گیفت‌های نایاب</p><p class="text-[10px]" style="color:var(--faint)">تخفیف‌های بالای ۵۰٪ و شماره‌های رند</p></div>
      </div>
      <div class="p-3 rounded-2xl glass glass-tight flex items-center gap-3">
        <span class="text-xl">🚀</span>
        <div><p class="font-bold">بوست و خدمات ویژه</p><p class="text-[10px]" style="color:var(--faint)">سفارش با تعداد دلخواه و تحویل سریع</p></div>
      </div>
      <div class="p-3 rounded-2xl glass glass-tight flex items-center gap-3">
        <span class="text-xl">👑</span>
        <div><p class="font-bold">استارز و پرمیوم تلگرام</p><p class="text-[10px]" style="color:var(--faint)">فعال‌سازی بدون نیاز به پسورد اکانت</p></div>
      </div>
    </div>
    <button id="enterStoreBtn" class="w-full py-3.5 btn-inv text-xs flex items-center justify-center gap-2">
      <span>بزن بریم</span><i class="fa-solid fa-arrow-left text-xs"></i>
    </button>
  </div>
</div>

<!-- هدر -->
<header class="sticky top-0 z-30 px-4 py-3" style="background:rgba(8,9,11,.85); -webkit-backdrop-filter:blur(18px); backdrop-filter:blur(18px); border-bottom:1px solid var(--border)">
  <div class="max-w-xl mx-auto flex items-center justify-between">
    <div class="flex items-center gap-3">
      <div class="w-10 h-10 rounded-2xl glass2 flex items-center justify-center text-lg">🦆</div>
      <div>
        <h1 class="text-[10px] font-black uppercase tracking-widest" style="color:var(--faint)">DUCK STORE</h1>
        <p id="topGreeting" class="text-sm font-black">مرجع خدمات تلگرام</p>
      </div>
    </div>
    <a id="headerSupportLink" href="https://t.me/Zanjani_a" class="w-9 h-9 rounded-full btn-ghost flex items-center justify-center press">
      <i class="fa-brands fa-telegram text-sky-400 text-sm"></i>
    </a>
  </div>
</header>

<main class="max-w-xl mx-auto px-4 mt-4 space-y-4">

<!-- بخش ۱: خانه -->
<section id="view-home" class="space-y-4">
  <div id="promoBanner" class="hidden glass glass-tight p-3.5 flex items-center gap-2.5">
    <div class="w-8 h-8 rounded-xl flex items-center justify-center text-sm" style="background:rgba(217,201,161,.14)"><i class="fa-solid fa-bullhorn text-amber-300"></i></div>
    <span id="promoBannerText" class="text-xs font-bold flex-1"></span>
  </div>

  <div class="grid grid-cols-3 gap-2.5">
    <div class="glass glass-tight p-3 text-center">
      <p id="statGiftCount" class="text-lg font-black">__TOTAL_COUNT__</p>
      <p class="text-[10px] mt-0.5" style="color:var(--faint)">گیفت فعال</p>
    </div>
    <div class="glass glass-tight p-3 text-center">
      <p class="text-lg font-black" style="color:var(--good)">-50%</p>
      <p class="text-[10px] mt-0.5" style="color:var(--faint)">حداقل تخفیف</p>
    </div>
    <div class="glass glass-tight p-3 text-center">
      <p class="text-lg font-black">24/7</p>
      <p class="text-[10px] mt-0.5" style="color:var(--faint)">پشتیبانی</p>
    </div>
  </div>

  <div>
    <div class="flex items-center justify-between mb-2.5 px-1">
      <h3 class="text-sm font-black">دسترسی سریع</h3>
    </div>
    <div class="grid grid-cols-4 gap-2.5">
      <button onclick="goServices('stars')" class="glass glass-tight p-3 flex flex-col items-center gap-1.5 press">
        <span class="text-xl">⭐</span><span class="text-[10px] font-bold">استارز</span>
      </button>
      <button onclick="goServices('premium')" class="glass glass-tight p-3 flex flex-col items-center gap-1.5 press">
        <span class="text-xl">💎</span><span class="text-[10px] font-bold">پرمیوم</span>
      </button>
      <button onclick="switchView('market')" class="glass glass-tight p-3 flex flex-col items-center gap-1.5 press">
        <span class="text-xl">🎁</span><span class="text-[10px] font-bold">گیفت</span>
      </button>
      <button onclick="goServices('custom_0')" class="glass glass-tight p-3 flex flex-col items-center gap-1.5 press">
        <span class="text-xl">🚀</span><span class="text-[10px] font-bold">خدمات</span>
      </button>
    </div>
  </div>

  <div>
    <div class="flex items-center justify-between mb-2.5 px-1">
      <h3 class="text-sm font-black">تازه‌ترین گیفت‌ها</h3>
      <button onclick="switchView('market')" class="text-[10px] font-bold flex items-center gap-1" style="color:var(--dim)">مشاهده همه <i class="fa-solid fa-chevron-left text-[9px]"></i></button>
    </div>
    <div id="homeGiftScroll" class="flex gap-2.5 overflow-x-auto pb-1 -mx-4 px-4"></div>
  </div>
</section>

<!-- بخش ۲: بازار گیفت‌ها -->
<section id="view-market" class="hidden space-y-3">
  <div class="glass glass-tight p-3 flex items-center gap-2">
    <div class="relative flex-1">
      <i class="fa-solid fa-magnifying-glass absolute right-3 top-2.5 text-xs" style="color:var(--faint)"></i>
      <input type="text" id="searchInput" placeholder="جستجوی نام یا شماره گیفت..." class="w-full bg-transparent rounded-xl pr-8 pl-2 py-1.5 text-xs">
    </div>
    <button onclick="openModal()" class="px-3 py-1.5 rounded-xl btn-ghost text-xs font-bold flex items-center gap-1.5 whitespace-nowrap">
      <span id="selectedColText">کالکشن‌ها</span><i class="fa-solid fa-chevron-down text-[9px]"></i>
    </button>
  </div>

  <div class="flex items-center gap-2 overflow-x-auto pb-1">
    <button onclick="filterType('all', this)" class="type-btn chip active">همه (__TOTAL_COUNT__)</button>
    <button onclick="filterType('rare', this)" class="type-btn chip">💎 کمیاب‌ها (__RARE_COUNT__)</button>
    <button onclick="filterType('favs', this)" class="type-btn chip flex items-center gap-1.5"><i class="fa-solid fa-heart text-[10px] text-rose-500"></i> (<span id="favCount">0</span>)</button>
  </div>

  <div id="dealsGrid" class="grid grid-cols-2 gap-3"></div>
  <div id="marketEmpty" class="hidden text-center py-14">
    <div class="text-3xl mb-2 opacity-40"><i class="fa-solid fa-box-open"></i></div>
    <p class="text-xs font-bold" style="color:var(--dim)">گیفتی پیدا نشد</p>
  </div>
</section>

<!-- بخش ۳: خدمات داینامیک -->
<section id="view-services" class="hidden space-y-4">
  <div id="servicesTabsBar" class="flex items-center gap-1.5 overflow-x-auto pb-1">
    <button onclick="switchServiceSubTab('stars')" id="subtab-stars" class="service-subtab-btn chip active">استارز</button>
    <button onclick="switchServiceSubTab('premium')" id="subtab-premium" class="service-subtab-btn chip">پرمیوم</button>
  </div>

  <div id="subview-stars" class="space-y-3">
    <div class="glass glass-tight p-4 space-y-3">
      <h4 class="text-xs font-bold flex items-center gap-1.5">⭐ تعداد دلخواه استارز</h4>
      <div class="flex items-center gap-2">
        <input type="number" id="customStarsInput" min="50" placeholder="حداقل ۵۰ عدد..." class="flex-1 glass glass-tight px-3.5 py-2.5 text-xs font-bold">
        <button onclick="addCustomStarsToCart()" class="px-4 py-2.5 rounded-xl btn-inv text-xs whitespace-nowrap">خرید</button>
      </div>
      <div id="customStarsCalcBox" class="p-3 rounded-xl hidden items-center justify-between" style="background:var(--glass2)">
        <span class="text-xs font-medium" style="color:var(--dim)">مبلغ نهایی:</span>
        <span id="customStarsPrice" class="text-xs font-black">0 تومان</span>
      </div>
    </div>
    <div id="starsPackagesList" class="space-y-2"></div>
  </div>

  <div id="subview-premium" class="hidden space-y-2.5">
    <div id="premiumOptionsList" class="space-y-2.5"></div>
  </div>

  <div id="subview-custom" class="hidden space-y-3">
    <div id="customCategoryHeader" class="px-1">
      <h3 id="customCategoryTitle" class="text-sm font-black text-white"></h3>
    </div>
    <div id="customCategoryItemsList" class="space-y-3"></div>
  </div>
</section>

<!-- بخش ۴: سبد خرید -->
<section id="view-cart" class="hidden space-y-4">
  <div class="glass glass-tight p-4 space-y-3">
    <div class="flex items-center justify-between border-b pb-3" style="border-color:var(--border)">
      <h3 class="text-sm font-black">سبد خرید (<span id="cartCountHeader">0</span>)</h3>
      <button onclick="clearCart()" class="text-xs text-rose-400 hover:underline">خالی کردن</button>
    </div>

    <div id="cartItemsList" class="space-y-2.5 max-h-64 overflow-y-auto"></div>
    <div id="cartEmptyState" class="hidden text-center py-10">
      <p class="text-xs" style="color:var(--dim)">سبد خرید شما خالی است</p>
    </div>

    <div class="flex items-center gap-2 pt-2">
      <input type="text" id="couponInput" placeholder="کد تخفیف (مثلاً DUCK)" class="flex-1 glass glass-tight px-3 py-2 text-xs uppercase font-bold">
      <button onclick="applyCoupon()" class="px-4 py-2 rounded-xl btn-ghost text-xs font-bold whitespace-nowrap">اعمال</button>
    </div>

    <div class="hair pt-3 space-y-1.5 text-xs">
      <div class="flex items-center justify-between"><span style="color:var(--dim)">جمع کل</span><span id="cartSubtotal" class="font-bold">0 تومان</span></div>
      <div id="cartDiscountRow" class="hidden flex items-center justify-between"><span style="color:var(--good)">تخفیف</span><span id="cartDiscountAmount" class="font-bold" style="color:var(--good)">0 تومان</span></div>
      <div class="flex items-center justify-between pt-1.5 hair"><span class="font-black text-sm">مبلغ نهایی</span><span id="cartTotal" class="font-black text-sm text-cyan-400">0 تومان</span></div>
    </div>

    <button onclick="checkoutCart()" class="w-full py-3.5 rounded-2xl btn-inv text-xs flex items-center justify-center gap-2">
      <span>ثبت سفارش در تلگرام</span><i class="fa-solid fa-arrow-left text-xs"></i>
    </button>
  </div>
</section>

<!-- بخش ۵: پروفایل کاربر -->
<section id="view-profile" class="hidden space-y-4">
  <div class="glass p-6 flex flex-col items-center text-center space-y-4">
    <div class="w-18 h-18 rounded-full flex items-center justify-center text-3xl" style="background:var(--glass2); border:1px solid var(--border2)">
      👤
    </div>
    <div>
      <h2 id="profileName" class="text-base font-black">کاربر گرامی</h2>
      <p id="profileUsername" class="text-xs mt-0.5 dir-ltr" style="color:var(--faint)">@guest</p>
    </div>

    <div class="w-full hair pt-3 space-y-2 text-xs text-right">
      <div class="flex items-center justify-between"><span style="color:var(--dim)">شناسه کاربری (User ID)</span><span id="profileUserId" class="font-bold font-mono dir-ltr">—</span></div>
      <div class="flex items-center justify-between"><span style="color:var(--dim)">وضعیت</span><span class="font-bold" style="color:var(--good)">تاییدشده</span></div>
    </div>

    <div class="w-full space-y-2 pt-2">
      <a id="profileChannelBtn" href="https://t.me/duck_storee" class="w-full py-3 rounded-2xl btn-ghost text-xs font-bold flex items-center justify-center gap-2">
        <i class="fa-brands fa-telegram text-sky-400 text-sm"></i><span>عضویت در کانال تلگرام (@duck_storee)</span>
      </a>
      <a id="profileSupportBtn" href="https://t.me/Zanjani_a" class="w-full py-3 rounded-2xl btn-ghost text-xs font-bold flex items-center justify-center gap-2">
        <i class="fa-solid fa-headset text-xs"></i><span>ارتباط مستقیم با پشتیبانی</span>
      </a>
    </div>
  </div>
</section>

</main>

<!-- 🛍️ نوار پاپ‌آپ شناور سبد خرید (بالای نوار ناوبری) -->
<div id="floatingCartBar" class="fixed bottom-20 inset-x-4 max-w-lg mx-auto z-40 bg-[#0d1017]/95 backdrop-blur-xl border border-cyan-500/40 p-3.5 rounded-[22px] shadow-2xl transition-all duration-300 transform translate-y-40 opacity-0 flex items-center justify-between">
  <div class="flex items-center gap-3">
    <div class="w-10 h-10 rounded-2xl bg-cyan-400 text-black flex items-center justify-center font-black text-sm shadow-md">
      <span id="floatingCartCount">0</span>
    </div>
    <div>
      <p class="text-xs font-bold text-white">سبد خرید شما</p>
      <p id="floatingCartPrice" class="text-xs text-cyan-400 font-black">0 تومان</p>
    </div>
  </div>
  <div class="flex items-center gap-2">
    <button onclick="switchView('cart')" class="px-3.5 py-2 rounded-xl btn-ghost text-xs font-bold">نمایش سبد</button>
    <button onclick="checkoutCart()" class="px-4 py-2 rounded-xl btn-inv text-xs font-black flex items-center gap-1.5">
      <span>تسویه</span><i class="fa-solid fa-arrow-left text-[10px]"></i>
    </button>
  </div>
</div>

<!-- نوار ناوبری پایین صفحه -->
<nav class="fixed bottom-3 inset-x-4 max-w-xl mx-auto z-40 glass2 px-2 py-2 flex items-center justify-around" style="border-radius:30px;">
  <button onclick="switchView('home')" id="nav-home" class="nav-tab active px-3.5 py-2 rounded-2xl flex flex-col items-center gap-1 text-[10px] font-bold">
    <i class="fa-solid fa-house text-sm"></i><span>خانه</span><span class="dot"></span>
  </button>
  <button onclick="switchView('market')" id="nav-market" class="nav-tab px-3.5 py-2 rounded-2xl flex flex-col items-center gap-1 text-[10px] font-bold">
    <i class="fa-solid fa-gift text-sm"></i><span>گیفت‌ها</span><span class="dot"></span>
  </button>
  <button onclick="switchView('services')" id="nav-services" class="nav-tab px-3.5 py-2 rounded-2xl flex flex-col items-center gap-1 text-[10px] font-bold">
    <i class="fa-solid fa-bolt text-sm"></i><span>خدمات</span><span class="dot"></span>
  </button>
  <button onclick="switchView('cart')" id="nav-cart" class="nav-tab relative px-3.5 py-2 rounded-2xl flex flex-col items-center gap-1 text-[10px] font-bold">
    <i class="fa-solid fa-cart-shopping text-sm"></i><span>سبد</span><span class="dot"></span>
    <span id="navCartBadge" class="hidden absolute -top-0.5 left-1 min-w-[16px] h-4 px-1 rounded-full bg-white text-[9px] font-black text-black flex items-center justify-center">0</span>
  </button>
  <button onclick="switchView('profile')" id="nav-profile" class="nav-tab px-3.5 py-2 rounded-2xl flex flex-col items-center gap-1 text-[10px] font-bold">
    <i class="fa-solid fa-user text-sm"></i><span>حساب</span><span class="dot"></span>
  </button>
</nav>

<!-- 🎁 پاپ‌آپ جزئیات گیفت تصویر ۲ (بدون اسلایدر روز) -->
<div id="quickViewSheet" class="fixed inset-0 z-50 flex items-center justify-center p-4 sheet-backdrop hidden">
  <div class="glass2 w-full max-w-sm rounded-[28px] overflow-hidden flex flex-col shadow-2xl fade-up" style="background:#111317; border:1px solid var(--border2);">
    <div class="relative w-full h-56 flex items-center justify-center overflow-hidden" id="qvImageWrap">
      <button onclick="closeQuickView()" class="absolute top-3 left-3 w-8 h-8 rounded-full flex items-center justify-center z-10" style="background:rgba(0,0,0,.5); backdrop-filter:blur(6px); color:#fff;"><i class="fa-solid fa-xmark text-xs"></i></button>
      <button onclick="toggleFavoriteQV()" id="qvFavBtn" class="absolute top-3 right-3 w-8 h-8 rounded-full flex items-center justify-center z-10" style="background:rgba(0,0,0,.5); backdrop-filter:blur(6px);"><i class="fa-solid fa-heart text-xs"></i></button>
      <span id="qvDiscountBadge" class="absolute bottom-3 right-3 badge-disc"></span>
      <img id="qvImage" src="" alt="" class="w-36 h-36 object-contain drop-shadow-[0_12px_24px_rgba(0,0,0,.6)]">
    </div>
    <div class="p-5 space-y-4 text-right">
      <div>
        <h3 id="qvTitle" class="text-base font-black"></h3>
        <p id="qvNumber" class="text-xs mt-0.5" style="color:var(--faint)"></p>
      </div>
      <div class="p-3.5 rounded-2xl flex items-center justify-between" style="background:#181a20; border:1px solid var(--border);">
        <span class="text-xs font-bold" style="color:var(--dim)">مبلغ اجاره</span>
        <span id="qvPrice" class="text-sm font-black"></span>
      </div>
      <div class="flex items-center gap-2 pt-1">
        <button onclick="addQVToCart()" class="flex-1 py-3.5 btn-inv text-xs flex items-center justify-center gap-1.5"><i class="fa-solid fa-cart-shopping text-xs"></i><span id="qvAddCartText">افزودن به سبد</span></button>
        <a id="qvTgLink" href="#" target="_blank" class="flex-1 py-3.5 btn-ghost text-xs font-bold text-center">مشاهده در تلگرام</a>
      </div>
    </div>
  </div>
</div>

<!-- 📦 مودال انتخاب کالکشن با نمایش تصویر هر کالکشن -->
<div id="collectionModal" class="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 sheet-backdrop hidden">
  <div class="glass2 w-full sm:max-w-md rounded-t-[28px] sm:rounded-[28px] overflow-hidden flex flex-col max-h-[78vh]">
    <div class="px-5 py-4 flex items-center justify-between hair">
      <button onclick="closeModal()" class="w-7 h-7 rounded-full btn-ghost flex items-center justify-center"><i class="fa-solid fa-xmark text-xs"></i></button>
      <h3 class="text-xs font-black">کالکشن‌های گیفت</h3>
      <div class="w-7"></div>
    </div>
    <div class="p-3 border-b border-white/10 space-y-2">
      <input type="text" id="modalSearchInput" placeholder="جستجوی کالکشن..." class="w-full glass glass-tight px-3 py-1.5 text-xs">
      <div class="flex items-center justify-between text-xs px-1">
        <button onclick="selectAllCollections()" class="text-cyan-400 font-bold">انتخاب همه</button>
        <button onclick="clearCollectionSelection()" style="color:var(--faint)">پاک کردن</button>
      </div>
    </div>
    <div id="modalCollectionsList" class="p-3 space-y-1.5 overflow-y-auto flex-1"></div>
    <div class="p-3 hair">
      <button onclick="applyCollectionModal()" class="w-full py-2.5 btn-inv text-xs">اعمال فیلتر</button>
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
  if (window.Telegram?.WebApp?.initData) {
    try {
      const params = new URLSearchParams(window.Telegram.WebApp.initData);
      const userStr = params.get('user');
      if (userStr) {
        tgUser = JSON.parse(userStr);
        return tgUser;
      }
    } catch(e) {}
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

function triggerHaptic(type = 'light') {
  try {
    if (window.Telegram?.WebApp?.HapticFeedback) {
      if (type === 'selection') window.Telegram.WebApp.HapticFeedback.selectionChanged();
      else window.Telegram.WebApp.HapticFeedback.impactOccurred(type);
    }
  } catch(e) {}
}

// 🔗 هدایت قطعی، تضمینی و ضدبلاک به تلگرام
function openTgLink(url) {
  if (!url) return;
  const cleanUrl = url.replace('https://t.me/@', 'https://t.me/').trim();

  // کپی خودکار متن فاکتور در کلیپ‌بورد برای اطمینان ۱۰۰٪
  try {
    const urlObj = new URL(cleanUrl);
    const textParam = urlObj.searchParams.get('text');
    if (textParam && navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(textParam);
    }
  } catch(e) {}

  // ۱. برای محیط مینی‌اپ تلگرام
  if (window.Telegram?.WebApp) {
    if (cleanUrl.includes('t.me') || cleanUrl.startsWith('tg:')) {
      try {
        window.Telegram.WebApp.openTelegramLink(cleanUrl);
        return;
      } catch(e) {}
    }
    try {
      if (window.Telegram.WebApp.openLink) {
        window.Telegram.WebApp.openLink(cleanUrl);
        return;
      }
    } catch(e) {}
  }

  // ۲. برای مرورگر و وب‌ویو: ساخت لینک نامرئی و کلیک مستقیم
  try {
    const a = document.createElement('a');
    a.href = cleanUrl;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { if (a.parentNode) a.parentNode.removeChild(a); }, 150);
  } catch(e) {
    window.location.href = cleanUrl;
  }
}

function toast(msg, icon) {
  const wrap = document.getElementById('toastWrap');
  const el = document.createElement('div');
  el.className = 'toast';
  el.innerHTML = `<i class="fa-solid ${icon || 'fa-circle-check'} text-xs" style="color:var(--good)"></i><span>${msg}</span>`;
  wrap.appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; el.style.transform = 'translateY(-10px)'; el.style.transition = 'all .25s ease'; setTimeout(() => el.remove(), 250); }, 2200);
}

const WORKER_URL = "__WORKER_URL__";
const DEALS = Array.isArray(__DEALS_JSON__) ? __DEALS_JSON__ : [];
const COLLECTIONS = Array.isArray(__COLLECTIONS_JSON__) ? __COLLECTIONS_JSON__ : [];

const DEFAULT_SETTINGS = {
  ratePerStar: 1450, prem3: 620000, prem6: 950000, prem12: 1690000,
  giftMonthlyPrice: 160000, adminTg: 'Zanjani_a',
  announcementText: 'تخفیف ویژه جشنواره فعال شد', announcementActive: true,
  couponCode: 'DUCK', couponPercent: 10,
  customServices: [
    {
      id: "cat_boost",
      title: "بوست تلگرام",
      icon: "fa-rocket",
      items: [
        { id: "b1", name: "بوست تلگرام (1 روزه)", duration: "1 روز", price: 45000, minQty: 1 },
        { id: "b7", name: "بوست تلگرام (7 روزه)", duration: "7 روز", price: 180000, minQty: 1 },
        { id: "b30", name: "بوست تلگرام (30 روزه)", duration: "30 روز", price: 590000, minQty: 1 }
      ]
    }
  ]
};
let SETTINGS = { ...DEFAULT_SETTINGS };

let favorites = JSON.parse(localStorage.getItem('duck_favs_v3') || '[]');
let cart = JSON.parse(localStorage.getItem('duck_cart_v3') || '[]');
let selectedCollections = new Set();
let tempSelectedCollections = new Set();
let selectedType = 'all';
let activeQVDeal = null;
let appliedCouponPercent = 0;
let currentCustomCategoryIdx = 0;

function persist() {
  localStorage.setItem('duck_favs_v3', JSON.stringify(favorites));
  localStorage.setItem('duck_cart_v3', JSON.stringify(cart));
}

function fmtMoney(n) { return Math.round(Number(n)||0).toLocaleString('en-US'); }
function escAttr(s) { return String(s).replace(/'/g, "\\'"); }
function escapeHtml(s) { return String(s).replace(/</g, "&lt;").replace(/>/g, "&gt;"); }

/* ================= مشخصات خریدار تلگرام ================= */
function getBuyerDetailsText() {
  const u = getTgUser();
  if (!u) return "خریدار: کاربر وب";
  const name = `${u.first_name || ''} ${u.last_name || ''}`.trim() || 'کاربر تلگرام';
  const uname = u.username ? `@${u.username}` : 'بدون یوزرنیم';
  const uid = u.id || 'ثبت نشده';
  return `خریدار: ${name} (${uname} - آیدی: ${uid})`;
}

/* ================= ناوبری ================= */
function switchView(view) {
  triggerHaptic('selection');
  ['home','market','services','cart','profile'].forEach(v => {
    document.getElementById('view-' + v).classList.toggle('hidden', v !== view);
    document.getElementById('nav-' + v).classList.toggle('active', v === view);
  });
  if (view === 'cart') renderCart();
  window.scrollTo({top:0, behavior:'instant'});
}
function goServices(subtab) {
  switchView('services');
  switchServiceSubTab(subtab);
}

/* ================= خانه ================= */
function renderHome() {
  const scrollHtml = DEALS.slice(0, 10).map(d => `
    <div class="glass rounded-2xl overflow-hidden flex-shrink-0 w-32 press" onclick="openQuickView('${escAttr(d.name)}')">
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

/* ================= بازار گیفت‌ها ================= */
function dealCardHtml(d, idx) {
  const isFav = favorites.includes(d.name);
  const bg = d.bg_color || '#1e2433';
  const priceFormatted = fmtMoney(SETTINGS.giftMonthlyPrice || 160000);
  return `
  <div class="gift-card fade-up cursor-pointer" onclick="openQuickView('${escAttr(d.name)}')">
    <div class="relative w-full aspect-square flex items-center justify-center overflow-hidden" style="background-color:${bg};">
      <button onclick="event.stopPropagation(); toggleFavorite('${escAttr(d.name)}')" class="absolute top-2.5 left-2.5 w-7 h-7 rounded-full flex items-center justify-center z-10" style="background:rgba(0,0,0,.45); backdrop-filter:blur(4px)">
        <i class="fa-solid fa-heart text-[11px]" style="color:${isFav ? '#f4685f' : 'rgba(255,255,255,.6)'}"></i>
      </button>
      <span class="absolute bottom-2.5 right-2.5 badge-disc">${d.discount || '-50.0%'}</span>
      <img src="${d.image_url}" loading="lazy" alt="${escapeHtml(d.name)}" class="w-28 h-28 object-contain drop-shadow-[0_8px_16px_rgba(0,0,0,.5)] transition-transform duration-300 hover:scale-105" onerror="this.src='https://marketapp.org/favicon.ico'">
    </div>
    <div class="p-3 text-right">
      <p class="text-xs font-black truncate">${escapeHtml(d.gift_title)}</p>
      <p class="text-[10px] mt-0.5 dir-ltr text-right" style="color:var(--faint)">#${d.number} · ${d.days_range} روز</p>
      <p class="text-[10px] font-bold mt-2" style="color:var(--dim)">از <span class="font-black text-white text-xs">${priceFormatted}</span> <span style="color:var(--faint)">تومان/ماه</span></p>
    </div>
  </div>`;
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

function renderCards(list) {
  const grid = document.getElementById('dealsGrid');
  grid.innerHTML = list.map(dealCardHtml).join('');
  document.getElementById('marketEmpty').classList.toggle('hidden', list.length > 0);
  document.getElementById('favCount').innerText = favorites.length.toLocaleString('en-US');
}

function filterType(type, btn) {
  triggerHaptic('selection');
  selectedType = type;
  document.querySelectorAll('.type-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  renderCards(getFilteredDeals());
}

document.addEventListener('DOMContentLoaded', () => {
  const si = document.getElementById('searchInput');
  if (si) si.addEventListener('input', () => renderCards(getFilteredDeals()));
});

function toggleFavorite(name) {
  triggerHaptic('light');
  const idx = favorites.indexOf(name);
  if (idx >= 0) { favorites.splice(idx, 1); toast('از نشان‌شده‌ها حذف شد'); }
  else { favorites.push(name); toast('به نشان‌شده‌ها اضافه شد'); }
  persist();
  renderCards(getFilteredDeals());
}

/* ================= پاپ‌آپ جزئیات گیفت تصویر ۲ ================= */
function openQuickView(name) {
  const d = DEALS.find(x => x.name === name);
  if (!d) return;
  triggerHaptic('light');
  activeQVDeal = d;
  document.getElementById('qvImageWrap').style.backgroundColor = d.bg_color || '#1e2433';
  document.getElementById('qvImage').src = d.image_url;
  document.getElementById('qvTitle').innerText = d.gift_title;
  document.getElementById('qvNumber').innerText = `شماره #${d.number}`;
  document.getElementById('qvDiscountBadge').innerText = d.discount || '-50.0%';
  document.getElementById('qvTgLink').href = d.tg_link || 'https://t.me';
  
  const priceFormatted = fmtMoney(SETTINGS.giftMonthlyPrice || 160000);
  document.getElementById('qvPrice').innerText = priceFormatted + ' تومان / ماه';
  
  const inCart = cart.some(c => c.name === d.name);
  document.getElementById('qvAddCartText').innerText = inCart ? 'حذف از سبد' : 'افزودن به سبد';
  
  updateFavBtnQV();
  document.getElementById('quickViewSheet').classList.remove('hidden');
}
function closeQuickView() {
  document.getElementById('quickViewSheet').classList.add('hidden');
  activeQVDeal = null;
}
function updateFavBtnQV() {
  if (!activeQVDeal) return;
  const isFav = favorites.includes(activeQVDeal.name);
  document.getElementById('qvFavBtn').querySelector('i').style.color = isFav ? '#f4685f' : 'rgba(255,255,255,.7)';
}
function toggleFavoriteQV() {
  if (!activeQVDeal) return;
  toggleFavorite(activeQVDeal.name);
  updateFavBtnQV();
}
function addQVToCart() {
  if (!activeQVDeal) return;
  triggerHaptic('selection');
  const idx = cart.findIndex(c => c.name === activeQVDeal.name);
  if (idx > -1) {
    cart.splice(idx, 1);
    toast('از سبد خرید حذف شد');
  } else {
    cart.push({
      name: activeQVDeal.name,
      price: Number(SETTINGS.giftMonthlyPrice || 160000),
      tg_link: activeQVDeal.tg_link
    });
    toast('به سبد خرید اضافه شد', 'fa-cart-plus');
  }
  persist();
  updateGlobalCounters();
  closeQuickView();
  renderCards(getFilteredDeals());
}

/* ================= کالکشن‌ها (با نمایش عکس کامل هر کالکشن) ================= */
function openModal() {
  triggerHaptic('light');
  tempSelectedCollections = new Set(selectedCollections);
  const searchEl = document.getElementById('modalSearchInput');
  if (searchEl) searchEl.value = '';
  document.getElementById('collectionModal').classList.remove('hidden');
  renderModalCollections();
}
function closeModal() {
  triggerHaptic('light');
  document.getElementById('collectionModal').classList.add('hidden');
}

function renderModalCollections() {
  const q = (document.getElementById('modalSearchInput')?.value || '').trim().toLowerCase();
  const container = document.getElementById('modalCollectionsList');
  if (!container) return;

  const filtered = COLLECTIONS.filter(c => !q || (c.name && c.name.toLowerCase().includes(q)));

  if (filtered.length === 0) {
    container.innerHTML = '<p class="text-xs text-center py-6 text-slate-500">کالکشنی یافت نشد</p>';
    return;
  }

  container.innerHTML = filtered.map(col => {
    const isSelected = tempSelectedCollections.has(col.name);
    const imgSrc = col.image || 'https://marketapp.org/favicon.ico';
    return `
    <div onclick="toggleModalCollection('${escAttr(col.name)}')" class="p-2.5 rounded-xl border flex items-center justify-between cursor-pointer transition" style="border-color:${isSelected ? 'var(--border2)' : 'var(--border)'}; background:${isSelected ? 'var(--glass2)' : 'transparent'}">
      <div class="flex items-center gap-3">
        <div class="w-9 h-9 rounded-xl flex items-center justify-center p-1 bg-white/5 border border-white/10 overflow-hidden flex-shrink-0">
          <img src="${imgSrc}" class="w-full h-full object-contain" onerror="this.src='https://marketapp.org/favicon.ico'">
        </div>
        <span class="text-xs font-bold text-white">${escapeHtml(col.name)}</span>
      </div>
      <div class="flex items-center gap-2">
        <span class="text-[10px] font-bold px-2 py-0.5 rounded-md text-slate-400" style="background:var(--glass2)">${col.count}</span>
        <div class="w-4 h-4 rounded-full border flex items-center justify-center ${isSelected ? 'border-cyan-400 bg-cyan-400 text-black' : 'border-slate-600'}">
          ${isSelected ? '<i class="fa-solid fa-check text-[9px]"></i>' : ''}
        </div>
      </div>
    </div>`;
  }).join('');
}

document.addEventListener('DOMContentLoaded', () => {
  const msi = document.getElementById('modalSearchInput');
  if (msi) msi.addEventListener('input', renderModalCollections);
});

function toggleModalCollection(name) {
  triggerHaptic('selection');
  if (tempSelectedCollections.has(name)) tempSelectedCollections.delete(name);
  else tempSelectedCollections.add(name);
  renderModalCollections();
}
function selectAllCollections() { COLLECTIONS.forEach(c => tempSelectedCollections.add(c.name)); renderModalCollections(); }
function clearCollectionSelection() { tempSelectedCollections.clear(); renderModalCollections(); }
function applyCollectionModal() {
  selectedCollections = new Set(tempSelectedCollections);
  document.getElementById('selectedColText').innerText = selectedCollections.size === 0 ? 'کالکشن‌ها' : `${selectedCollections.size} کالکشن`;
  closeModal();
  renderCards(getFilteredDeals());
}

/* ================= خدمات اختصاصی با تعداد و فاکتور کامل تلگرام ================= */
function renderServicesNavigation() {
  const navBar = document.getElementById('servicesTabsBar');
  const customCats = Array.isArray(SETTINGS.customServices) ? SETTINGS.customServices : [];
  
  let html = `
    <button onclick="switchServiceSubTab('stars')" id="subtab-stars" class="service-subtab-btn chip">استارز</button>
    <button onclick="switchServiceSubTab('premium')" id="subtab-premium" class="service-subtab-btn chip">پرمیوم</button>
  `;

  customCats.forEach((cat, idx) => {
    html += `<button onclick="switchServiceSubTab('custom_${idx}')" id="subtab-custom_${idx}" class="service-subtab-btn chip">${escapeHtml(cat.title || 'سرویس')}</button>`;
  });

  navBar.innerHTML = html;
}

function switchServiceSubTab(tab) {
  triggerHaptic('selection');
  document.querySelectorAll('.service-subtab-btn').forEach(btn => btn.classList.remove('active'));
  const activeBtn = document.getElementById('subtab-' + tab);
  if (activeBtn) activeBtn.classList.add('active');

  const isCustom = String(tab).startsWith('custom_');
  document.getElementById('subview-stars').classList.toggle('hidden', tab !== 'stars');
  document.getElementById('subview-premium').classList.toggle('hidden', tab !== 'premium');
  document.getElementById('subview-custom').classList.toggle('hidden', !isCustom);

  if (isCustom) {
    const idx = parseInt(tab.replace('custom_', ''), 10) || 0;
    currentCustomCategoryIdx = idx;
    renderCustomCategoryView(idx);
  }
}

function renderCustomCategoryView(catIdx) {
  const cats = Array.isArray(SETTINGS.customServices) ? SETTINGS.customServices : [];
  const cat = cats[catIdx];
  if (!cat) return;

  document.getElementById('customCategoryTitle').innerText = cat.title || 'خدمات ویژه';
  const listContainer = document.getElementById('customCategoryItemsList');
  const items = Array.isArray(cat.items) ? cat.items : [];

  if (items.length === 0) {
    listContainer.innerHTML = '<p class="text-xs text-slate-500 py-6 text-center">موردی در این دسته ثبت نشده است.</p>';
    return;
  }

  listContainer.innerHTML = items.map((item, i) => {
    const minQ = Math.max(1, Number(item.minQty) || 1);
    const price = Number(item.price) || 0;
    const inputId = `cqty_${catIdx}_${i}`;
    const totalId = `ctotal_${catIdx}_${i}`;
    const initTotal = fmtMoney(price * minQ);

    return `
      <div class="glass glass-tight p-4 space-y-3">
        <div class="flex items-center justify-between">
          <div>
            <h4 class="text-xs font-black text-white">${escapeHtml(item.name)}</h4>
            <p class="text-[10px] mt-0.5" style="color:var(--faint)">${escapeHtml(item.duration || '')}</p>
          </div>
          <div class="text-left">
            <span class="text-xs font-black text-amber-300">${fmtMoney(price)} ت</span>
            <span class="text-[9px] block" style="color:var(--faint)">نرخ هر واحد</span>
          </div>
        </div>

        <div class="hair pt-3 flex items-center justify-between">
          <div class="flex items-center gap-1.5 glass glass-tight px-2 py-1">
            <button onclick="changeCustomQty('${inputId}', -1, ${minQ}, ${price}, '${totalId}')" class="w-6 h-6 rounded-md flex items-center justify-center font-bold text-xs" style="background:var(--glass2)">-</button>
            <input id="${inputId}" type="number" value="${minQ}" min="${minQ}" oninput="onCustomQtyInput('${inputId}', ${minQ}, ${price}, '${totalId}')" class="w-10 text-center bg-transparent text-xs font-black text-white">
            <button onclick="changeCustomQty('${inputId}', 1, ${minQ}, ${price}, '${totalId}')" class="w-6 h-6 rounded-md flex items-center justify-center font-bold text-xs" style="background:var(--glass2)">+</button>
            <span class="text-[9px] mr-1" style="color:var(--faint)">حداقل: ${minQ}</span>
          </div>

          <div class="flex items-center gap-2.5">
            <div class="text-left">
              <span id="${totalId}" class="text-xs font-black text-cyan-400">${initTotal} ت</span>
              <span class="text-[9px] block" style="color:var(--faint)">مبلغ کل</span>
            </div>
            <button onclick="orderCustomService('${escAttr(cat.title)}', '${escAttr(item.name)}', ${price}, '${inputId}', ${minQ})" class="px-4 py-2 rounded-xl btn-inv text-xs whitespace-nowrap">
              خرید
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function changeCustomQty(inputId, delta, minQ, unitPrice, totalId) {
  const el = document.getElementById(inputId);
  if (!el) return;
  let val = parseInt(el.value, 10) || minQ;
  val += delta;
  if (val < minQ) val = minQ;
  el.value = val;
  updateCustomPriceDisplay(val, unitPrice, totalId);
  triggerHaptic('selection');
}

function onCustomQtyInput(inputId, minQ, unitPrice, totalId) {
  const el = document.getElementById(inputId);
  if (!el) return;
  let val = parseInt(el.value, 10);
  if (isNaN(val) || val < minQ) val = minQ;
  el.value = val;
  updateCustomPriceDisplay(val, unitPrice, totalId);
}

function updateCustomPriceDisplay(qty, unitPrice, totalId) {
  const totalEl = document.getElementById(totalId);
  if (totalEl) totalEl.innerText = fmtMoney(qty * unitPrice) + ' ت';
}

function orderCustomService(catTitle, itemName, unitPrice, inputId, minQ) {
  triggerHaptic('heavy');
  const input = document.getElementById(inputId);
  let qty = parseInt(input ? input.value : minQ, 10) || minQ;
  if (qty < minQ) qty = minQ;

  const total = qty * unitPrice;
  const adminUser = (SETTINGS.adminTg || 'Zanjani_a').replace('@', '').trim();
  const nl = String.fromCharCode(10);
  const buyerText = getBuyerDetailsText();

  const msg = encodeURIComponent(
    "سلام، درخواست خرید خدمات تلگرام دارم:" + nl + nl +
    buyerText + nl + nl +
    "دسته: " + catTitle + nl +
    "پلن: " + itemName + nl +
    "تعداد سفارش: " + qty.toLocaleString('en-US') + " عدد" + nl +
    "تعرفه هر واحد: " + fmtMoney(unitPrice) + " تومان" + nl +
    "مبلغ کل قابل پرداخت: " + fmtMoney(total) + " تومان"
  );
  openTgLink("https://t.me/" + adminUser + "?text=" + msg);
}

// استارز با اطلاعات کامل خریدار
function renderStarsPackages() {
  const rate = Number(SETTINGS.ratePerStar) || 1450;
  const packs = [50, 100, 250, 500, 1000, 2500, 5000];
  document.getElementById('starsPackagesList').innerHTML = packs.map(p => `
    <div class="glass glass-tight p-3.5 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl flex items-center justify-center text-lg" style="background:var(--glass2)">⭐</div>
        <div><p class="text-xs font-black">${p} استارز</p><p class="text-[10px] mt-0.5" style="color:var(--faint)">${fmtMoney(p*rate)} تومان</p></div>
      </div>
      <button onclick="orderDirectStars(${p})" class="px-4 py-2 rounded-xl btn-ghost text-[11px] font-bold">خرید مستقیم</button>
    </div>`).join('');
}
function orderDirectStars(qty) {
  triggerHaptic('heavy');
  const adminUser = (SETTINGS.adminTg || 'Zanjani_a').replace('@', '').trim();
  const total = fmtMoney(qty * (Number(SETTINGS.ratePerStar)||1450));
  const nl = String.fromCharCode(10);
  const buyerText = getBuyerDetailsText();

  const msg = encodeURIComponent(
    "سلام، متقاضی خرید استارز تلگرام هستم:" + nl + nl +
    buyerText + nl + nl +
    "تعداد استارز: " + qty.toLocaleString('en-US') + " Stars" + nl +
    "مبلغ قابل پرداخت: " + total + " تومان"
  );
  openTgLink("https://t.me/" + adminUser + "?text=" + msg);
}
document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('customStarsInput');
  if (input) input.addEventListener('input', () => {
    const qty = parseInt(input.value, 10) || 0;
    const box = document.getElementById('customStarsCalcBox');
    if (qty >= 50) {
      box.classList.remove('hidden'); box.classList.add('flex');
      document.getElementById('customStarsPrice').innerText = fmtMoney(qty * (Number(SETTINGS.ratePerStar)||1450)) + ' تومان';
    } else { box.classList.add('hidden'); box.classList.remove('flex'); }
  });
});
function addCustomStarsToCart() {
  const qty = parseInt(document.getElementById('customStarsInput').value, 10) || 0;
  if (qty < 50) { toast('حداقل ۵۰ استارز وارد کنید'); return; }
  orderDirectStars(qty);
}

// پرمیوم با اطلاعات کامل خریدار
function renderPremiumOptions() {
  const plans = [
    { key: 'prem3', label: '۳ ماهه', price: SETTINGS.prem3 },
    { key: 'prem6', label: '۶ ماهه', price: SETTINGS.prem6 },
    { key: 'prem12', label: '۱۲ ماهه (۱ ساله)', price: SETTINGS.prem12 }
  ];
  document.getElementById('premiumOptionsList').innerHTML = plans.map(p => `
    <div class="glass glass-tight p-3.5 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl flex items-center justify-center text-lg" style="background:var(--glass2)">💎</div>
        <div><p class="text-xs font-black">پرمیوم ${p.label}</p><p class="text-[10px] mt-0.5" style="color:var(--faint)">${fmtMoney(p.price)} تومان</p></div>
      </div>
      <button onclick="orderDirectPremium('${p.label}', ${Number(p.price)||0})" class="px-4 py-2 rounded-xl btn-ghost text-[11px] font-bold">خرید مستقیم</button>
    </div>`).join('');
}
function orderDirectPremium(label, price) {
  triggerHaptic('heavy');
  const adminUser = (SETTINGS.adminTg || 'Zanjani_a').replace('@', '').trim();
  const nl = String.fromCharCode(10);
  const buyerText = getBuyerDetailsText();

  const msg = encodeURIComponent(
    "سلام، متقاضی خرید تلگرام پرمیوم هستم:" + nl + nl +
    buyerText + nl + nl +
    "نوع اشتراک: " + label + nl +
    "مبلغ قابل پرداخت: " + fmtMoney(price) + " تومان"
  );
  openTgLink("https://t.me/" + adminUser + "?text=" + msg);
}

/* ================= سبد خرید و پاپ‌آپ شناور ================= */
function renderCart() {
  const list = document.getElementById('cartItemsList');
  const empty = document.getElementById('cartEmptyState');
  document.getElementById('cartCountHeader').innerText = cart.length.toString();
  if (cart.length === 0) {
    list.innerHTML = ''; empty.classList.remove('hidden');
    updateCartTotals();
    return;
  }
  empty.classList.add('hidden');
  list.innerHTML = cart.map((c, i) => `
    <div class="glass glass-tight p-3 flex items-center justify-between">
      <div>
        <p class="text-xs font-bold">${escapeHtml(c.name)}</p>
        <p class="text-[10px] text-cyan-400 mt-0.5 font-bold">${fmtMoney(c.price)} تومان</p>
      </div>
      <button onclick="removeCartItem(${i})" class="w-7 h-7 rounded-full flex items-center justify-center text-rose-400 hover:bg-rose-500/10">
        <i class="fa-solid fa-xmark text-xs"></i>
      </button>
    </div>`).join('');
  updateCartTotals();
}

function updateFloatingCart() {
  const bar = document.getElementById('floatingCartBar');
  if (!bar) return;
  const count = cart.length;
  const sub = cart.reduce((s, c) => s + (Number(c.price) || 0), 0);
  const total = appliedCouponPercent > 0 ? Math.round(sub * (1 - appliedCouponPercent / 100)) : sub;

  document.getElementById('floatingCartCount').innerText = count.toString();
  document.getElementById('floatingCartPrice').innerText = fmtMoney(total) + ' ت';

  if (count > 0) {
    bar.classList.remove('translate-y-40', 'opacity-0');
    bar.classList.add('translate-y-0', 'opacity-100');
  } else {
    bar.classList.remove('translate-y-0', 'opacity-100');
    bar.classList.add('translate-y-40', 'opacity-0');
  }
}

function removeCartItem(i) {
  triggerHaptic('light');
  cart.splice(i, 1);
  persist(); renderCart(); updateGlobalCounters();
}
function clearCart() {
  triggerHaptic('warning');
  cart = []; appliedCouponPercent = 0;
  document.getElementById('couponInput').value = '';
  persist(); renderCart(); updateGlobalCounters();
  toast('سبد خرید خالی شد');
}
function applyCoupon() {
  const code = (document.getElementById('couponInput')?.value || '').trim().toUpperCase();
  if (!code) return;
  if (code === String(SETTINGS.couponCode || 'DUCK').toUpperCase()) {
    appliedCouponPercent = Number(SETTINGS.couponPercent) || 10;
    triggerHaptic('success');
    toast(`کد تخفیف ${appliedCouponPercent}٪ اعمال شد`);
  } else {
    appliedCouponPercent = 0;
    triggerHaptic('error');
    toast('کد تخفیف نامعتبر است');
  }
  updateCartTotals();
}
function updateCartTotals() {
  const sub = cart.reduce((s, c) => s + (Number(c.price) || 0), 0);
  document.getElementById('cartSubtotal').innerText = fmtMoney(sub) + ' تومان';
  const discRow = document.getElementById('cartDiscountRow');
  let total = sub;
  if (appliedCouponPercent > 0) {
    const disc = Math.round(sub * appliedCouponPercent / 100);
    total = sub - disc;
    document.getElementById('cartDiscountAmount').innerText = fmtMoney(disc) + ' تومان';
    discRow.classList.remove('hidden'); discRow.classList.add('flex');
  } else {
    discRow.classList.add('hidden'); discRow.classList.remove('flex');
  }
  document.getElementById('cartTotal').innerText = fmtMoney(total) + ' تومان';
  updateFloatingCart();
}

function checkoutCart() {
  triggerHaptic('heavy');
  if (cart.length === 0) { toast('سبد خرید شما خالی است'); return; }
  const adminUser = (SETTINGS.adminTg || 'Zanjani_a').replace('@', '').trim();
  const sub = cart.reduce((s, c) => s + (Number(c.price) || 0), 0);
  const disc = appliedCouponPercent > 0 ? Math.round(sub * appliedCouponPercent / 100) : 0;
  const total = sub - disc;
  const nl = String.fromCharCode(10);
  const buyerText = getBuyerDetailsText();

  const itemsText = cart.map((c, i) => `${i + 1}. 🎁 ${c.name} (${c.tg_link || ''})`).join(nl);
  const couponText = appliedCouponPercent > 0 ? (nl + `تخفیف: ${fmtMoney(disc)} تومان (${appliedCouponPercent}%)`) : '';

  const msg = encodeURIComponent(
    "سلام، درخواست اجاره گیفت دارم:" + nl + nl +
    buyerText + nl + nl +
    "اقلام سفارش (" + cart.length + " عدد):" + nl +
    itemsText + nl + nl +
    "مبلغ نهایی: " + fmtMoney(total) + " تومان / ماه" +
    couponText
  );
  openTgLink("https://t.me/" + adminUser + "?text=" + msg);
}

function updateGlobalCounters() {
  const count = cart.length;
  const badge = document.getElementById('navCartBadge');
  badge.innerText = count.toString();
  badge.classList.toggle('hidden', count === 0);
  updateFloatingCart();
}

async function fetchCloudSettings() {
  try {
    const res = await fetch(`${WORKER_URL}/api/settings`);
    if (res.ok) {
      const data = await res.json();
      SETTINGS = { ...DEFAULT_SETTINGS, ...data };
    }
  } catch(e) {}
  updateUI();
}

function updateUI() {
  if (SETTINGS.announcementActive && SETTINGS.announcementText) {
    document.getElementById('promoBanner').classList.remove('hidden');
    document.getElementById('promoBannerText').innerText = SETTINGS.announcementText;
  }
  renderHome();
  renderCards(getFilteredDeals());
  renderServicesNavigation();
  renderStarsPackages();
  renderPremiumOptions();
  updateGlobalCounters();

  const u = getTgUser();
  if (u) {
    const name = u.first_name || u.username || "کاربر گرامی";
    document.getElementById('topGreeting').innerText = `سلام ${name} 👋`;
    document.getElementById('profileName').innerText = `${u.first_name || ''} ${u.last_name || ''}`.trim() || name;
    document.getElementById('profileUsername').innerText = u.username ? `@${u.username}` : 'بدون یوزرنیم';
    document.getElementById('profileUserId').innerText = u.id || '—';
  }
}

/* ================= اسپلش لودینگ و صفحه خوش‌آمد ================= */
let loadingProgress = 5;
function startLoading() {
  const bar = document.getElementById('loadingProgressBar');
  const interval = setInterval(() => {
    loadingProgress += Math.floor(Math.random() * 18) + 10;
    if (loadingProgress >= 100) {
      loadingProgress = 100;
      clearInterval(interval);
      bar.style.width = '100%';
      setTimeout(() => {
        const loader = document.getElementById('loadingScreen');
        const welcome = document.getElementById('welcomeScreen');
        loader.classList.add('opacity-0');
        setTimeout(() => { loader.style.display = 'none'; }, 400);
        
        welcome.style.display = 'flex';
        welcome.classList.remove('hidden');
        setTimeout(() => { welcome.classList.remove('opacity-0'); }, 50);
      }, 300);
    } else {
      bar.style.width = `${loadingProgress}%`;
    }
  }, 90);
}

document.getElementById('enterStoreBtn')?.addEventListener('click', () => {
  triggerHaptic('heavy');
  const welcome = document.getElementById('welcomeScreen');
  welcome.classList.add('opacity-0');
  setTimeout(() => { welcome.style.display = 'none'; }, 400);
});

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

    try:
        with open(CONFIG["EXPORT_HTML"], "w", encoding="utf-8") as f:
            f.write(html_content)
    except Exception as e:
        print(f"❌ خطا در نوشتن HTML: {e}")

    try:
        with open(CONFIG["EXPORT_JSON"], "w", encoding="utf-8") as f:
            json.dump(deals, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ خطا در نوشتن JSON: {e}")


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
        f"🦆 <b>گزارش فروشگاه Duck Store</b>\n"
        f"📅 <i>{timestamp}</i>\n\n"
        f"🌐 <b>ورود به فروشگاه:</b>\n👉 <a href='{pages_url}'>{pages_url}</a>\n"
        f"📢 <b>کانال رسمی:</b>\n👉 <a href='{CONFIG['TELEGRAM_CHANNEL_LINK']}'>{CONFIG['TELEGRAM_CHANNEL_LINK']}</a>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 تعداد کل گیفت‌ها: {len(deals)} مورد (کمیاب: {rare_count})\n"
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
            print(f"❌ خطا در ارسال تلگرام: {e}")


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
# ⚡ موتور اسکرپر
# ==========================================
async def main():
    deals_found: List[Dict[str, Any]] = []
    seen_links: Set[str] = set()
    browser = None

    print("\n" + "═" * 65)
    print("  🦆 DUCK STORE TURBO SCRAPER (STABLE ENGINE V5) 🦆")
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

            print("🌐 بارگذاری اولیه مارکت...")
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
                    return cards.map(c => {
                        const img = c.querySelector('img');
                        let bg = '';
                        if (img && img.parentElement) {
                            bg = window.getComputedStyle(img.parentElement).backgroundColor || '';
                        }
                        return {
                            href: c.getAttribute('href') || '',
                            text: c.innerText || '',
                            img: img ? img.src : '',
                            bg: bg
                        };
                    });
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
                                "bg_color": c.get("bg") or "#1e2230",
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
            print(f"❌ خطا در خروجی CSV: {e}")

        print("\n⚡ فروشگاه پایدار Duck Store با نمایش عکس کالکشن‌ها و ناوبری ضدبلاک ساخته شد!")
        send_telegram_package(sorted_deals)


if __name__ == "__main__":
    asyncio.run(main())
