# Duck Store — رنت گیفت با Marketapp + SwapWallet + Cloudflare

این نسخه Backend را به Cloudflare Workers + D1 منتقل می‌کند و قیمت رنت را به شکل زیر محاسبه می‌کند:

`Marketapp (TON rent price) → SwapWallet (TON/تومان) → درصد سود → حداقل/حداکثر قیمت → فروشگاه`

## امکانات اضافه‌شده

- دریافت موجودی رنت گیفت از `GET /v1/rent/gifts/` مارکت‌اپ.
- نگهداری API tokenها در Cloudflare Worker Secrets، نه در HTML.
- تبدیل TON به تومان از طریق API قابل تنظیم SwapWallet.
- نرخ جایگزین ثابت در صورت قطع API نرخ.
- درصد سود قابل تنظیم.
- حداقل و حداکثر قیمت فروش.
- انتخاب قیمت روزانه یا ماهانه.
- لینک آموزش تصویری قابل تنظیم از پنل.
- متن راهنما قابل ویرایش از پنل.
- بعد از تأیید پرداخت رنت، راهنما برای کاربر ارسال می‌شود.
- کاربر از داخل پروفایل لینک `fragment.com` را برای سفارش می‌فرستد.
- لینک برای ادمین ارسال می‌شود.
- ادمین دکمه «تأیید اتصال موفق» دارد.
- بعد از تأیید، پیام موفقیت برای کاربر ارسال می‌شود.
- GitHub Actions برای Deploy Worker.

## 1) ساخت D1

در Cloudflare:

1. Workers & Pages → D1 → Create database
2. نام را `duck-store` بگذارید.
3. ID دیتابیس را بردارید.
4. در `worker/wrangler.toml` مقدار `database_id` را جایگزین کنید.

سپس:

```bash
npx wrangler@latest d1 execute duck-store --remote --file=worker/schema.sql
```

## 2) نصب Wrangler

```bash
npm install -g wrangler
wrangler login
```

یا بدون نصب دائمی:

```bash
npx wrangler@latest login
```

## 3) Secretهای Cloudflare

این‌ها را هرگز داخل GitHub یا HTML قرار ندهید:

```bash
npx wrangler secret put ADMIN_PASSWORD
npx wrangler secret put MARKETAPP_TOKEN
npx wrangler secret put SWAP_API_TOKEN
npx wrangler secret put TELEGRAM_BOT_TOKEN
npx wrangler secret put ADMIN_CHAT_ID
```

`ADMIN_PASSWORD` همان رمز ورود پنل است.

## 4) Deploy

```bash
npx wrangler@latest deploy worker/index.js --config worker/wrangler.toml
```

بعد از Deploy، URL Worker را بردارید.

در `index.html` و `admin.html` مقدار:

```js
const WORKER_URL = "https://YOUR-WORKER.workers.dev";
```

را تنظیم کنید.

## 5) تنظیم Marketapp

در پنل مدیریت:

- Base URL: `https://api.marketapp.org`
- Rent Path: `/v1/rent/gifts/`
- نوع قیمت: ماهانه یا روزانه

Marketapp اعلام کرده endpointهای API نیاز به API token دارند و token با Header `Authorization` بدون پیشوند Bearer ارسال می‌شود.

## 6) تنظیم SwapWallet

به علت اینکه ساختار دقیق endpoint نرخ در حساب شما ممکن است بر اساس نسخه/API plan متفاوت باشد، پنل این موارد را قابل تنظیم کرده است:

- Base URL
- Price Path
- Method
- Query
- JSON Path

مثلاً اگر پاسخ API شما این باشد:

```json
{
  "data": {
    "ton_toman": 123456
  }
}
```

در JSON Path بنویسید:

```text
data.ton_toman
```

توکن SwapWallet فقط از Secret خوانده می‌شود.

اگر API نرخ موقتاً در دسترس نباشد، مقدار `نرخ ثابت جایگزین` استفاده می‌شود.

## 7) فرمول قیمت

قیمت پایه:

```text
TON rent × نرخ TON/تومان
```

بعد:

```text
قیمت فروش = قیمت پایه × (1 + درصد سود / 100)
```

و سپس:

```text
اگر قیمت < حداقل → نمایش داده نمی‌شود
اگر قیمت > حداکثر → نمایش داده نمی‌شود
```

مثال:

```text
Rent = 0.5 TON
TON/IRT = 100,000
سود = 20%

قیمت پایه = 50,000
قیمت فروش = 60,000 تومان
```

## 8) گردش خرید رنت گیفت

1. کاربر گیفت را انتخاب می‌کند.
2. قیمت زنده از Backend دریافت می‌شود.
3. کاربر سفارش را ثبت می‌کند.
4. Worker سفارش را در D1 ثبت می‌کند.
5. ربات تلگرام شماره سفارش و مبلغ را می‌فرستد.
6. ادمین پرداخت را تأیید می‌کند.
7. Worker متن راهنما + لینک آموزش تصویری را برای کاربر می‌فرستد.
8. کاربر از Fragment لینک را کپی می‌کند.
9. در پروفایل فروشگاه، سفارش را انتخاب و لینک را ارسال می‌کند.
10. لینک در D1 ذخیره و برای ادمین ارسال می‌شود.
11. ادمین اتصال را بررسی می‌کند.
12. با «تأیید اتصال موفق»، سفارش completed می‌شود.
13. پیام موفقیت برای کاربر ارسال می‌شود.

## 9) متن پیش‌فرض راهنما

```text
راهنما:

1. وارد Fragment.com شوید
2. با اکانت تلگرام Login کنید
3. روی Connect کلیک کنید
4. دکمه بالا سمت چپ را بزنید و لینک را کپی کنید
5. لینک را در فیلد زیر وارد کنید
6. پس از اتصال موفق به Fragment برگردید
7. از بخش Assets وارد Gifts شوید
8. روی سه نقطه کنار NFT زده و Display on Telegram را بزنید
9. NFT روی اکانت تلگرام شما ظاهر می‌شود

نکته: هر روز ۳ ولت و ۳ NFT می‌توانید وصل کنید.

آموزش تصویری
```

متن و URL آموزش از پنل قابل تغییر است.

## 10) GitHub Actions

دو workflow دارید:

- Scraper قبلی
- `deploy-worker.yml`

در GitHub → Settings → Secrets and variables → Actions این دو Secret را اضافه کنید:

```text
CLOUDFLARE_API_TOKEN
CLOUDFLARE_ACCOUNT_ID
```

برای API Token، دسترسی Worker/D1 موردنیاز حساب خود را بدهید.

## نکته مهم امنیتی

API tokenهای Marketapp و SwapWallet را داخل `index.html`، `admin.html` یا Git commit نگذارید.

Frontend فقط endpoint Worker را صدا می‌زند:

```text
/api/rent/gifts
```

بنابراین کلیدها در مرورگر کاربر دیده نمی‌شوند.

## محدودیت فعلی

این نسخه «محاسبه قیمت + ثبت سفارش + workflow لینک Fragment + تأیید ادمین» را کامل می‌کند.

اگر هدف شما این است که بعد از تأیید پرداخت، خود Worker به‌صورت خودکار `POST /v1/rent/{nft_address}/pay/` مارکت‌اپ را نیز اجرا کند، باید body دقیق `RentNFTBody` و شرایط پرداخت/Transaction API حساب Marketapp مشخص باشد؛ آن مرحله را نباید با حدس درباره payload پیاده کرد.



## نسخه اصلاح‌شده Rent

- لیست ثابت قبلی از فرانت‌اند حذف شده و صفحه Rent فقط از `/api/rent/gifts` تغذیه می‌شود.
- قیمت هر Gift از `price_toman` همان Gift نمایش داده می‌شود و دیگر مقدار ثابت `giftMonthlyPrice` روی همه کارت‌ها نشان داده نمی‌شود.
- خطای اتصال MarketApp یا نرخ TON به کاربر در صفحه نمایش داده می‌شود و بی‌صدا نادیده گرفته نمی‌شود.
- Worker برای ساختارهای متداول پاسخ MarketApp انعطاف‌پذیرتر شده است.
- برای نرخ TON، اگر API نرخ یا Fallback تنظیم نشده باشد، سیستم به‌جای نمایش قیمت جعلی با ضریب 1، خطای واضح می‌دهد.

MarketApp مستند کرده که endpoint رنت Gift برابر `GET /v1/rent/gifts/` است و احراز هویت با هدر `Authorization` بدون پیشوند Bearer انجام می‌شود.
