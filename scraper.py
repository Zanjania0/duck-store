import asyncio
import csv
from datetime import datetime
import json
import os
import re
from typing import Any, Dict, List, Set, Tuple
import urllib.parse
import urllib.request
import httpx

# ==========================================
# ⚙️ تنظیمات پایه و اندپوینت‌ها
# ==========================================
CONFIG = {
    "API_RENT_GIFTS": "https://api.marketapp.org/v1/rent/gifts",
    "SWAP_WALLET_API": "https://api.swapwallet.app/v1/rates/ton",
    "WORKER_URL": "https://duck-api.ali-zanjani2007.workers.dev",
    "TARGET_DEALS_COUNT": 200,
    "EXPORT_HTML": "index.html",
    "EXPORT_JSON": "discounts.json",
    "EXPORT_CSV": "discounts.csv",
    "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN", ""),
    "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID", ""),
}

# کاتالوگ پشتیبان کامل در صورت عدم دسترسی به API
REAL_TELEGRAM_FALLBACK_GIFTS = [
    {
        "name": "Plush Pepe #2825",
        "gift_title": "Plush Pepe",
        "number": "2825",
        "price_ton_day": "0.05",
        "price_toman": 180000,
        "rent_days": 30,
        "discount": "۳۰ روزه",
        "image_url": "https://i2.anton.market/3SHMDVNMcpuaDG5ZnWdghhw4eByUrQrzl4Lz-ysNwwA/rs:fill:300:300:1/g:ce/czM6Ly9tYXJrZXRhcHAvYy9FUUE0MDFRcXBYdEJud0lhRGJGandkNXlYZlAybVlpQ3VzYkozWmN3OWVYUjlDcUwvOTBkNDNiMDBiNTVmOTA0MWQ4Y2JlOWMwNDI2N2Y4ZDgud2VicA",
        "tg_link": "https://t.me/nft/PlushPepe-2825",
        "market_link": "https://marketapp.org/rent/plush-pepe-2825",
        "bg_color": "#182a1b",
        "rarity": "🎯 خاص (#2825)",
    },
    {
        "name": "Eternal Rose #7077",
        "gift_title": "Eternal Rose",
        "number": "7077",
        "price_ton_day": "0.02",
        "price_toman": 85000,
        "rent_days": 30,
        "discount": "۳۰ روزه",
        "image_url": "https://i2.anton.market/b32fmE813CAOkRPrFkxDLWvxupaeOwXbnF0yCjelE1I/rs:fill:300:300:1/g:ce/czM6Ly9tYXJrZXRhcHAvYy9FUUR1bXkzYm5aWXpWNGJTV01TU1prbVhxeDUwWHVINWQ5UmxYX3lFaTJGTmxpdmsvZWQ0YzBmY2ZmM2IwODM4ZGNhMzEyMDAyYjVlN2ZmM2Eud2VicA",
        "tg_link": "https://t.me/nft/EternalRose-7077",
        "market_link": "https://marketapp.org/rent/eternal-rose-7077",
        "bg_color": "#28161b",
        "rarity": "💎 زیر 10000",
    }
]

def detect_rarity(num_str: str) -> str:
    try:
        n = int(re.sub(r"\D", "", str(num_str)))
    except Exception:
        return ""
    s = str(n)
    if n < 100: return "👑 زیر 100"
    if n < 1000: return "💎 زیر 1000"
    if len(s) >= 3 and len(set(s)) == 1: return f"✨ رند (#{s})"
    if s in ["123", "1234", "777", "888", "999"]: return f"🎯 خاص (#{s})"
    return ""

def clean_collection_title(title: str) -> str:
    t = re.sub(r"[#\d]", "", title).strip()
    t = re.sub(r"\b(rent|gifts?|market|nft|floor)\b", "", t, flags=re.IGNORECASE)
    words = [w.capitalize() for w in t.split() if w]
    return " ".join(words) if words else "Telegram Gift"

def generate_tg_nft_link(name: str, number: str) -> str:
    clean_name = re.sub(r"[^a-zA-Z0-9\s]", "", name)
    words = clean_name.split()
    slug = "".join(w.capitalize() for w in words)
    clean_num = re.sub(r"\D", "", str(number))
    return f"https://t.me/nft/{slug}-{clean_num}" if slug and clean_num else "https://t.me"

async def get_remote_settings() -> Dict[str, Any]:
    default_settings = {
        "profitMargin": 25,
        "rentDays": 30,
        "tonRateMode": "auto",
        "manualTonPrice": 485000,
        "minPriceToman": 0,
        "maxPriceToman": 0,
        "swapApiKey": "",
        "ratePerStar": 1450,
        "prem3": 620000,
        "prem6": 950000,
        "prem12": 1690000,
        "giftMonthlyPrice": 160000
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(f"{CONFIG['WORKER_URL']}/api/settings")
            if res.status_code == 200:
                data = res.json()
                default_settings.update(data)
                print("✅ تنظیمات ادمین، سود و بازه قیمتی با موفقیت از ورکر دریافت شد.")
    except Exception as e:
        print(f"⚠️ دریافت تنظیمات از ورکر ناموفق بود (استفاده از مقادیر پیش‌فرض): {e}")
    return default_settings

async def get_ton_price_toman(settings: Dict[str, Any]) -> int:
    if settings.get("tonRateMode") == "manual":
        val = int(settings.get("manualTonPrice", 485000))
        print(f"ℹ️ حالت دستی فعال است. نرخ تون: {val:,} تومان")
        return val

    headers = {"Accept": "application/json"}
    if settings.get("swapApiKey"):
        headers["Authorization"] = f"Bearer {settings['swapApiKey']}"

    try:
        async with httpx.AsyncClient(timeout=12) as client:
            res = await client.get(CONFIG["SWAP_WALLET_API"], headers=headers)
            if res.status_code == 200:
                data = res.json()
                rate = data.get("price_toman") or data.get("rate") or data.get("price") or (data.get("price_irr", 0) / 10)
                if rate and float(rate) > 0:
                    val = int(float(rate))
                    print(f"✅ نرخ زنده تون از صرافی SwapWallet استخراج شد: {val:,} تومان")
                    return val
    except Exception as e:
        print(f"⚠️ خطای صرافی SwapWallet: {e}")

    fallback = int(settings.get("manualTonPrice", 485000))
    print(f"ℹ️ استفاده از نرخ تون پشتیبان: {fallback:,} تومان")
    return fallback

async def fetch_and_process_gifts() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    settings = await get_remote_settings()
    ton_toman_rate = await get_ton_price_toman(settings)

    profit_margin = float(settings.get("profitMargin", 25))
    rent_days = int(settings.get("rentDays", 30))
    min_price = int(settings.get("minPriceToman", 0))
    max_price = int(settings.get("maxPriceToman", 0))

    deals: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

    print(f"🚀 شروع دریافت ۲۰۰ گیفت از مارکت‌اپ (سود: {profit_margin}% | دوره: {rent_days} روزه)...")

    async with httpx.AsyncClient(timeout=25) as client:
        for offset in [0, 100]:
            try:
                params = {
                    "limit": 100,
                    "offset": offset,
                    "sort_by": "price_per_day_asc"
                }
                res = await client.get(CONFIG["API_RENT_GIFTS"], params=params, headers=headers)
                if res.status_code != 200:
                    print(f"⚠️ وضعیت پاسخ API مارکت‌اپ: {res.status_code}")
                    break

                raw_data = res.json()
                items = raw_data.get("items") or raw_data.get("gifts") or (raw_data if isinstance(raw_data, list) else [])
                if not items:
                    break

                for it in items:
                    raw_num = str(it.get("number") or it.get("token_id") or it.get("num") or "")
                    raw_title = it.get("name") or it.get("title") or it.get("collection_name") or ""

                    if not raw_num and "#" in raw_title:
                        m = re.search(r"#(\d+)", raw_title)
                        if m: raw_num = m.group(1)

                    gift_title = clean_collection_title(raw_title)
                    item_id = f"{gift_title} #{raw_num}"

                    if not raw_num or item_id in seen:
                        continue

                    price_ton_day = float(it.get("price_per_day") or it.get("min_price") or 0.04)

                    # فرمول تبدیل قیمت: قیمت روزانه * روزها * نرخ تون * (1 + سود)
                    base_toman = price_ton_day * rent_days * ton_toman_rate
                    final_toman = int(base_toman * (1.0 + (profit_margin / 100.0)))

                    # اعمال بازه قیمتی ادمین
                    if min_price > 0 and final_toman < min_price:
                        continue
                    if max_price > 0 and final_toman > max_price:
                        continue

                    slug = gift_title.lower().replace(" ", "-")
                    direct_market_link = f"https://marketapp.org/rent/{slug}-{raw_num}"

                    deal = {
                        "name": item_id,
                        "gift_title": gift_title,
                        "number": raw_num,
                        "price_ton_day": str(price_ton_day),
                        "price_toman": final_toman,
                        "rent_days": rent_days,
                        "discount": f"{rent_days} روزه",
                        "image_url": it.get("image_url") or it.get("image") or it.get("preview_url") or "https://marketapp.org/favicon.ico",
                        "market_link": direct_market_link,
                        "tg_link": generate_tg_nft_link(gift_title, raw_num),
                        "rarity": detect_rarity(raw_num),
                        "bg_color": "#161d2a"
                    }
                    seen.add(item_id)
                    deals.append(deal)

                    if len(deals) >= CONFIG["TARGET_DEALS_COUNT"]:
                        break
            except Exception as e:
                print(f"⚠️ خطای استخراج: {e}")
                break

    if len(deals) < 4:
        print("⚠️ استفاده از کاتالوگ پشتیبان به دلیل نرسیدن به حد نصاب گیفت‌ها.")
        deals = REAL_TELEGRAM_FALLBACK_GIFTS

    print(f"🎯 مجموع {len(deals)} گیفت آماده‌سازی گردید.")
    return deals, settings

def generate_duck_store_html(deals: List[Dict[str, Any]], settings: Dict[str, Any]):
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
.badge-disc{ background:rgba(61,220,151,.15); color:var(--good); font-weight:800; font-size:10px; border-radius:8px; padding:2px 7px; }
.sheet-backdrop{ background:rgba(0,0,0,.85); backdrop-filter:blur(10px); }
.toast-wrap{ position:fixed; top:14px; left:50%; transform:translateX(-50%); z-index:999; width:90%; max-width:400px; }
.toast{ background:#161922; border:1px solid rgba(255,255,255,.2); border-radius:14px; padding:10px 16px; font-size:12px; font-weight:700; text-align:center; }
input[type=number]::-webkit-inner-spin-button, input[type=number]::-webkit-outer-spin-button { -webkit-appearance:none; margin:0; }
</style>
</head>
<body class="min-h-screen pb-44 select-none">

<div class="toast-wrap" id="toastWrap"></div>

<!-- ۱. لودینگ اولیه -->
<div id="splashScreen" class="fixed inset-0 z-[100] bg-[#07080c] flex flex-col items-center justify-center space-y-4 transition-opacity duration-500">
    <div class="w-20 h-20 rounded-3xl bg-cyan-400 text-slate-950 flex items-center justify-center text-4xl shadow-2xl animate-bounce">🦆</div>
    <div class="text-center space-y-1">
        <h2 class="text-base font-black text-white">DUCK STORE</h2>
        <p class="text-xs text-slate-400 font-bold">در حال بارگذاری ویترین گیفت‌های تلگرام...</p>
    </div>
</div>

<!-- ۲. مودال خوش‌آمدگویی -->
<div id="onboardingModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 sheet-backdrop hidden">
    <div class="glass w-full max-w-sm p-6 text-center space-y-4 bg-[#0e1017]">
        <div class="w-16 h-16 rounded-2xl bg-cyan-400 text-slate-950 flex items-center justify-center text-3xl mx-auto shadow-lg">🚀</div>
        <div class="space-y-1.5">
            <h3 class="text-base font-black text-white">خوش آمدید به Duck Store!</h3>
            <p class="text-xs text-slate-300 leading-relaxed">
                ویترین خرید و اجاره گیفت‌های اصیل تلگرام، خرید استارز و پرمیوم با محاسبه لحظه‌ای نرخ روز و تحویل آنی.
            </p>
        </div>
        <button onclick="dismissOnboarding()" class="w-full py-3.5 bg-cyan-400 text-slate-950 font-black text-xs rounded-2xl shadow-xl">
            بزن بریم! 🚀
        </button>
    </div>
</div>

<!-- هدر بالا -->
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

<!-- ۱. تب خانه -->
<section id="view-home" class="space-y-4">
  <div class="grid grid-cols-3 gap-2 text-center">
    <div class="glass glass-tight p-3"><p class="text-base font-black">__TOTAL_COUNT__</p><p class="text-[10px] text-slate-400">گیفت فعال</p></div>
    <div class="glass glass-tight p-3"><p class="text-base font-black text-emerald-400">نرخ زنده</p><p class="text-[10px] text-slate-400">صرافی آنلاین</p></div>
    <div class="glass glass-tight p-3"><p class="text-base font-black text-cyan-400">کارت‌به‌کارت</p><p class="text-[10px] text-slate-400">فاکتور تلگرام</p></div>
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
    <h3 class="text-xs font-black mb-2 px-1 text-slate-300">تازه‌ترین گیفت‌های موجود</h3>
    <div id="homeGiftScroll" class="flex gap-2.5 overflow-x-auto pb-1 -mx-4 px-4"></div>
  </div>
</section>

<!-- ۲. بازار گیفت‌ها -->
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

<!-- ۳. تب خدمات با محاسبه زنده قیمت -->
<section id="view-services" class="hidden space-y-4">
  <div id="servicesTabsBar" class="flex items-center gap-1.5 overflow-x-auto pb-1">
    <button onclick="switchServiceSubTab('stars')" id="subtab-stars" class="service-subtab-btn chip active">استارز</button>
    <button onclick="switchServiceSubTab('premium')" id="subtab-premium" class="service-subtab-btn chip">پرمیوم</button>
  </div>

  <!-- استارز با محاسبه زنده قیمت -->
  <div id="subview-stars" class="space-y-3">
    <div class="glass glass-tight p-4 space-y-3">
      <div class="flex justify-between items-center">
        <h4 class="text-xs font-black text-amber-300">⭐ خرید استارز تلگرام (تعداد دلخواه)</h4>
        <span class="text-[10px] text-slate-400">نرخ هر استارز: <span id="starRateLabel">1,450</span> تومان</span>
      </div>
      <div class="space-y-2">
        <input type="text" id="starsTargetId" placeholder="آیدی اکانت تلگرام یا کانال مقصد (الزامی)..." class="w-full glass glass-tight px-3 py-2 text-xs font-bold text-cyan-300">
        <div class="flex items-center gap-2">
          <input type="number" id="customStarsInput" oninput="calcLiveStarsPrice()" min="1" placeholder="تعداد استارز (مثال: 65)..." class="flex-1 glass glass-tight px-3 py-2 text-xs font-bold">
          <button onclick="submitCustomStars()" class="px-4 py-2 btn-inv text-xs font-bold">ثبت سفارش</button>
        </div>
      </div>
      <div class="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-between text-xs">
        <span class="text-slate-300 font-bold">مبلغ محاسبه‌شده:</span>
        <span id="starsLivePriceText" class="font-black text-amber-400 text-sm">۰ تومان</span>
      </div>
    </div>
    <div id="starsPackagesList" class="space-y-2"></div>
  </div>

  <!-- پرمیوم -->
  <div id="subview-premium" class="hidden space-y-3">
    <div class="glass glass-tight p-3 space-y-1">
      <label class="block text-[10px] text-slate-400 font-bold">آیدی اکانت تلگرام جهت فعال‌سازی پرمیوم (الزامی):</label>
      <input type="text" id="premiumTargetId" placeholder="مثال: @username" class="w-full glass glass-tight px-3 py-2 text-xs font-bold text-purple-300">
    </div>
    <div id="premiumOptionsList" class="space-y-2.5"></div>
  </div>

  <!-- خدمات سفارشی ادمین با محاسبه زنده -->
  <div id="subview-custom" class="hidden space-y-3">
    <div id="customCategoryItemsList" class="space-y-3"></div>
  </div>
</section>

<!-- ۴. سبد خرید -->
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

<!-- ۵. حساب کاربری و پیگیری سفارشات -->
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

<!-- نوار شناور سبد -->
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

<!-- ناوبری پایین -->
<nav class="fixed bottom-3 inset-x-4 max-w-xl mx-auto z-40 glass px-2 py-2 flex items-center justify-around rounded-full bg-[#0d0f15]/95">
  <button onclick="switchView('home')" id="nav-home" class="nav-tab active px-3 py-1 flex flex-col items-center gap-1 text-[10px] font-bold"><i class="fa-solid fa-house"></i><span>خانه</span></button>
  <button onclick="switchView('market')" id="nav-market" class="nav-tab px-3 py-1 flex flex-col items-center gap-1 text-[10px] font-bold"><i class="fa-solid fa-gift"></i><span>گیفت‌ها</span></button>
  <button onclick="switchView('services')" id="nav-services" class="nav-tab px-3 py-1 flex flex-col items-center gap-1 text-[10px] font-bold"><i class="fa-solid fa-bolt"></i><span>خدمات</span></button>
  <button onclick="switchView('cart')" id="nav-cart" class="nav-tab px-3 py-1 flex flex-col items-center gap-1 text-[10px] font-bold"><i class="fa-solid fa-cart-shopping"></i><span>سبد</span></button>
  <button onclick="switchView('profile')" id="nav-profile" class="nav-tab px-3 py-1 flex flex-col items-center gap-1 text-[10px] font-bold"><i class="fa-solid fa-user"></i><span>حساب</span></button>
</nav>

<!-- گردونه شانس -->
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

<!-- مودال مشاهده جزئیات گیفت -->
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
      <span class="text-slate-400">مبلغ اجاره:</span>
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

<!-- مودال کالکشن‌ها -->
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

window.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        const splash = document.getElementById("splashScreen");
        if (splash) {
            splash.classList.add("opacity-0");
            setTimeout(() => splash.remove(), 500);
        }
        if (!localStorage.getItem("duck_welcomed_v7")) {
            document.getElementById("onboardingModal").classList.remove("hidden");
        }
    }, 1000);
});

function dismissOnboarding() {
    localStorage.setItem("duck_welcomed_v7", "true");
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

// محاسبه لحظه‌ای استارز
function calcLiveStarsPrice() {
  const qty = parseInt(document.getElementById('customStarsInput').value, 10) || 0;
  const rate = Number(SETTINGS.ratePerStar) || 1450;
  const total = qty * rate;
  document.getElementById('starsLivePriceText').innerText = fmtMoney(total) + " تومان";
}

// محاسبه لحظه‌ای خدمات اختصاصی ادمین
function calcLiveCustomPrice(catIdx, itemIdx) {
  const cat = (SETTINGS.customServices || [])[catIdx];
  if (!cat) return;
  const item = cat.items[itemIdx];
  const qtyInput = document.getElementById(`customQty_${catIdx}_${itemIdx}`);
  const display = document.getElementById(`customLivePrice_${catIdx}_${itemIdx}`);
  const qty = parseInt(qtyInput.value, 10) || 1;
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
    <div class="glass p-2.5 rounded-2xl flex-shrink-0 w-32 cursor-pointer text-right space-y-1" onclick="openHomeDeal(${i})">
      <div class="w-full h-24 rounded-xl flex items-center justify-center p-1" style="background:${d.bg_color || '#1b1d28'}">
        <img src="${d.image_url}" class="w-20 h-20 object-contain" onerror="this.src='https://marketapp.org/favicon.ico'">
      </div>
      <p class="text-[11px] font-black truncate mt-1">${d.gift_title}</p>
      <span class="badge-disc inline-block">${d.discount}</span>
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
        <img src="${d.image_url}" class="w-24 h-24 object-contain" onerror="this.src='https://marketapp.org/favicon.ico'">
      </div>
      <div>
        <p class="text-xs font-black truncate">${d.gift_title}</p>
        <p class="text-[10px] text-slate-400 dir-ltr text-right mt-0.5">#${d.number}</p>
        <div class="flex items-center justify-between mt-1.5">
          <span class="badge-disc">${d.discount}</span>
          <span class="text-[11px] font-black text-amber-400">${fmtMoney(d.price_toman)} تومان</span>
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
  document.getElementById('qvImage').src = d.image_url;
  document.getElementById('qvTitle').innerText = d.gift_title;
  document.getElementById('qvNumber').innerText = `شماره گیفت: #${d.number}`;
  document.getElementById('qvPrice').innerText = fmtMoney(d.price_toman) + ` تومان (${d.rent_days} روزه)`;
  document.getElementById('quickViewSheet').classList.remove('hidden');
}

function closeQuickView() { document.getElementById('quickViewSheet').classList.add('hidden'); }

function addQVToCart() {
  if (!activeQVDeal) return;
  // حفظ لینک مستقیم مارکت‌اپ برای ادمین در سبد خرید
  cart.push({ 
    name: activeQVDeal.name, 
    price: Number(activeQVDeal.price_toman),
    market_link: activeQVDeal.market_link || ""
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
        fb.innerText = "کد تخفیف وارد شده معتبر نیست!";
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
      alert("✅ فاکتور در چت ربات برای شما صادر شد!\\nپس از واریز، عکس فیش یا کد رهگیری را بفرستید.");
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
  if (!targetId) return alert("⚠️ لطفاً آیدی اکانت یا کانال مقصد را وارد کنید.");

  const qty = parseInt(document.getElementById('customStarsInput').value, 10) || 0;
  if (qty < 1) return alert("حداقل ۱ استارز وارد کنید");
  const total = qty * Number(SETTINGS.ratePerStar);
  submitOrderToBot([{ name: `${qty} استارز تلگرام`, price: total, qty: qty }], total, `⭐ بسته ${qty} عددی استارز\\n📌 مقصد: ${targetId}`, targetId);
}

function submitStarsPackage(qty) {
  const targetId = document.getElementById("starsTargetId").value.trim();
  if (!targetId) return alert("⚠️ لطفاً در فیلد بالا آیدی اکانت یا کانال مقصد را وارد کنید.");
  const total = qty * Number(SETTINGS.ratePerStar);
  submitOrderToBot([{ name: `${qty} استارز تلگرام`, price: total, qty: qty }], total, `⭐ بسته ${qty} عددی استارز\\n📌 مقصد: ${targetId}`, targetId);
}

function submitPremiumOrder(label, price) {
  const targetId = document.getElementById("premiumTargetId").value.trim();
  if (!targetId) return alert("⚠️ لطفاً در کادر بالا آیدی اکانت تلگرام مقصد را وارد کنید.");
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
          <span class="text-[10px] text-slate-400 font-bold">تعداد:</span>
          <input id="customQty_${idx}_${i}" type="number" min="${minQ}" value="${minQ}" oninput="calcLiveCustomPrice(${idx}, ${i})" class="w-20 bg-black/40 border border-white/10 rounded-xl p-1.5 text-center font-bold text-xs">
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
  const inputVal = document.getElementById(`prompt_${catIdx}_${itemIdx}`).value.trim();
  const qty = parseInt(document.getElementById(`customQty_${catIdx}_${itemIdx}`).value, 10) || 1;

  if (!inputVal) return alert(`⚠️ لطفاً "${item.inputPrompt || 'ورودی'}" را وارد کنید.`);
  if (qty < (item.minQty || 1)) return alert(`حداقل تعداد خرید برای این سرویس ${item.minQty || 1} است.`);

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
          <img src="${col.image}" class="w-8 h-8 rounded-lg object-contain bg-white/5 p-1" onerror="this.src='https://marketapp.org/favicon.ico'">
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
            fieldnames=["name", "gift_title", "number", "price_toman", "rent_days", "rarity", "tg_link", "market_link"]
        )
        writer.writeheader()
        for d in deals:
            writer.writerow({
                "name": d.get("name", ""),
                "gift_title": d.get("gift_title", ""),
                "number": d.get("number", ""),
                "price_toman": d.get("price_toman", 0),
                "rent_days": d.get("rent_days", 30),
                "rarity": d.get("rarity", ""),
                "tg_link": d.get("tg_link", ""),
                "market_link": d.get("market_link", ""),
            })

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
    except Exception as e:
        print(f"⚠️ خطای ارسال فایل به تلگرام: {e}")

def send_telegram_package(deals: List[Dict[str, Any]]):
    token = CONFIG.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = CONFIG.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id: return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pages_url = "https://zanjania0.github.io/duck-store/"
    rare_count = sum(1 for d in deals if d.get("rarity"))
    
    full_text = (
        f"🦆 <b>فروشگاه هوشمند Duck Store به‌روزرسانی شد</b>\n"
        f"📅 <i>{timestamp}</i>\n\n"
        f"🌐 <b>ورود به فروشگاه:</b>\n👉 <a href='{pages_url}'>{pages_url}</a>\n\n"
        f"🎯 موجودی گیفت‌های فعال: {len(deals)} عدد (کمیاب: {rare_count})\n"
    )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode({"chat_id": chat_id, "text": full_text, "parse_mode": "HTML"}).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload)
        with urllib.request.urlopen(req, timeout=15): pass
    except Exception: pass

    send_telegram_document(token, chat_id, CONFIG["EXPORT_CSV"], "📊 <b>فایل کامل اکسل موجودی گیفت‌ها</b>")

async def main():
    print("\n" + "═" * 60)
    print("  🦆 DUCK STORE TURBO ENGINE (SWAPWALLET + MARKETAPP API) 🦆")
    print("═" * 60 + "\n")

    deals, settings = await fetch_and_process_gifts()
    generate_duck_store_html(deals, settings)
    print(f"✅ خروجی‌های کامل با موفقیت ساخته شدند! موجودی: {len(deals)}")
    send_telegram_package(deals)

if __name__ == "__main__":
    asyncio.run(main())
