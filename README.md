# Duck Store — MarketApp + SwapWallet Rent Engine

این نسخه موتور «رنت گیفت» را به پروژه اضافه می‌کند:

`MarketApp → قیمت خام TON → SwapWallet exchange-rate API → تومان → درصد سود/سود ثابت → رُند → فیلتر بازه → ویترین`

## معماری

- Frontend: GitHub Pages / Telegram Mini App
- Rent API: Cloudflare Worker
- Database: Cloudflare D1
- Scheduler: Cloudflare Cron Trigger هر ۱۰ دقیقه
- Market source: `GET /v1/rent/gifts/` از MarketApp
- Exchange source: endpoint قابل تنظیم SwapWallet
- Secretها فقط در Cloudflare Worker Secrets هستند و داخل GitHub/frontend قرار نمی‌گیرند.

## نکته مهم درباره SwapWallet

مستندات عمومی SwapPay در زمان ساخت این نسخه endpoint نرخ ارز را به‌صورت قابل استخراج از صفحه وب در اختیار این پروژه نگذاشت؛ بنابراین آدرس endpoint و JSON path نرخ در پنل رنت قابل تنظیم است. این باعث می‌شود با تغییر نسخه API مجبور به تغییر frontend نشوید.

## راه‌اندازی رایگان

### 1) ساخت D1

در Cloudflare:
Workers & Pages → D1 → Create database

نام پیشنهادی:
`duck-store-rent`

شناسه database را در `worker/wrangler.toml` جایگزین کنید.

سپس:

```bash
cd worker
npx wrangler d1 execute duck-store-rent --remote --file=schema.sql
```

یا SQL داخل `schema.sql` را در D1 Console اجرا کنید.

### 2) نصب و Deploy Worker

```bash
cd worker
npx wrangler deploy
```

URL شبیه این دریافت می‌کنید:

`https://duck-store-rent-api.<SUBDOMAIN>.workers.dev`

همین URL را در ابتدای `index.html` جایگزین کنید:

```js
const RENT_API_URL = "https://duck-store-rent-api.<SUBDOMAIN>.workers.dev";
```

و در `admin.html` هم مقدار پیش‌فرض را اصلاح کنید.

### 3) Secretهای Cloudflare

در Cloudflare Worker → Settings → Variables and Secrets:

```text
MARKETAPP_API_TOKEN=توکن MarketApp
SWAP_API_KEY=کلید SwapWallet (اگر لازم است)
ADMIN_PASSWORD=یک رمز قوی برای بخش رنت
```

یا با Wrangler:

```bash
npx wrangler secret put MARKETAPP_API_TOKEN
npx wrangler secret put SWAP_API_KEY
npx wrangler secret put ADMIN_PASSWORD
```

### 4) اتصال MarketApp

API طبق مستندات MarketApp با header زیر احراز هویت می‌شود:

```http
Authorization: YOUR_MARKETAPP_TOKEN
```

endpoint پیش‌فرض:

```text
/v1/rent/gifts/
```

در پنل رنت، اگر نسخه API تغییر کرد، Endpoint و JSON Path را قابل تنظیم نگه دارید.

### 5) اتصال SwapWallet

در پنل:

- Swap Rate URL
- Swap Rate JSON Path
- ارز مبدا
- ارز مقصد
- ضریب IRR به تومان

را تنظیم کنید.

مثلاً اگر پاسخ API این باشد:

```json
{
  "data": {
    "rate": 1234567
  }
}
```

بنویسید:

```text
Swap Rate JSON Path = data.rate
```

اگر نرخ برگشتی ریال باشد، مقدار:

```text
IRR → Toman = 0.1
```

است.

اگر endpoint نرخ شما مستقیماً تومان برمی‌گرداند، ضریب را `1` قرار دهید.

### 6) فرمول قیمت

فرمول فعلی:

```text
قیمت خام TON × نرخ تومان
+
درصد سود
+
سود ثابت
→ رُند
```

مثلاً:

```text
1 TON = 200,000 تومان
گیفت = 0.5 TON
سود = 20%

500,000 × 1.20 = 600,000 تومان
```

اگر رُند روی 1000 باشد:

```text
600,000 تومان
```

### 7) فیلتر بازه

از پنل می‌توانید:

- حداقل TON
- حداکثر TON
- حداقل قیمت فروش
- حداکثر قیمت فروش
- کالکشن‌های مجاز
- کالکشن‌های ممنوع
- شماره گیفت‌های مخفی
- تعداد آیتم ویترین
- ترتیب نمایش

را تعیین کنید.

### 8) شخصی‌سازی کامل رنت

از پنل رنت می‌توانید:

- فعال/غیرفعال کردن رنت
- درصد سود
- سود ثابت
- مبلغ رُند
- تعداد روز اجاره
- نمایش قیمت روزانه یا کل
- عنوان ویترین
- کش قیمت
- fallback نرخ
- sort
- collection whitelist/blacklist
- hidden gift numbers

را تنظیم کنید.

### 9) GitHub Actions

Workflow جدید:

`.github/workflows/deploy-rent-worker.yml`

برای deploy خودکار است.

در GitHub:

Settings → Secrets and variables → Actions

این دو Secret را اضافه کنید:

```text
CLOUDFLARE_API_TOKEN
CLOUDFLARE_ACCOUNT_ID
```

توکن Cloudflare باید اجازه deploy Worker داشته باشد.

### 10) Cron

Worker هر ۱۰ دقیقه sync می‌کند:

```text
*/10 * * * *
```

Cronهای Cloudflare بر اساس UTC اجرا می‌شوند.

### 11) تست

بعد از deploy این endpointها را تست کنید:

```text
GET /api/rent/catalog
GET /api/rent/settings
```

پنل:

```text
POST /api/admin/login
POST /api/admin/rent-test-market
POST /api/admin/rent-test-rate
POST /api/rent/sync
```

## امنیت

- API tokenهای MarketApp و SwapWallet داخل frontend قرار نمی‌گیرند.
- فقط Worker به APIهای خارجی دسترسی دارد.
- D1 برای تنظیمات و cache استفاده می‌شود.
- پنل رنت با `ADMIN_PASSWORD` محافظت شده است.
- قیمت نهایی سمت Worker محاسبه می‌شود؛ بنابراین کاربر نمی‌تواند درصد سود را از frontend تغییر دهد.

## محدودیت رایگان Cloudflare

این معماری برای استفاده سبک/فروشگاه کوچک مناسب است. Workers Free فعلاً 100,000 request/day دارد و D1 Free شامل 5 میلیون row read و 100,000 row write در روز است. از آنجا که cache رنت در یک رکورد JSON نگهداری می‌شود، مصرف D1 این بخش پایین می‌ماند.

اگر فروشگاه رشد زیادی کند، باید قبل از رسیدن به سقف‌های رایگان usage را بررسی کنید.
