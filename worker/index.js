/**
 * Duck Store Cloudflare Worker
 * D1-backed backend for Marketapp rent + configurable FX provider + Telegram workflow.
 */
const DEFAULTS = {
  marketBaseUrl: "https://api.marketapp.org",
  marketRentPath: "/v1/rent/gifts/",
  marketEnabled: true,
  swapBaseUrl: "",
  swapPricePath: "",
  swapMethod: "GET",
  swapTokenHeader: "Authorization",
  swapTokenPrefix: "",
  swapQuery: "",
  swapJsonPath: "",
  tonToTomanMultiplier: 1,
  rentMarkupPercent: 0,
  rentMinToman: 0,
  rentMaxToman: 0,
  rentPriceMode: "monthly",
  tutorialUrl: "",
  guideText: `راهنما:\n\n1. وارد Fragment.com شوید\n2. با اکانت تلگرام Login کنید\n3. روی Connect کلیک کنید\n4. دکمه بالا سمت چپ را بزنید و لینک را کپی کنید\n5. لینک را در فیلد زیر وارد کنید\n6. پس از اتصال موفق به Fragment برگردید\n7. از بخش Assets وارد Gifts شوید\n8. روی سه نقطه کنار NFT زده و Display on Telegram را بزنید\n9. NFT روی اکانت تلگرام شما ظاهر می‌شود\n\nنکته: هر روز ۳ ولت و ۳ NFT می‌توانید وصل کنید.\n\nآموزش تصویری`
};

function json(data, status=200, extra={}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {"content-type":"application/json; charset=utf-8", "access-control-allow-origin":"*", "access-control-allow-headers":"Content-Type, Authorization", ...extra}
  });
}
function cors(r){ return r; }
function pathGet(obj, path, fallback=null) {
  if (!path) return fallback;
  try { return path.split(".").filter(Boolean).reduce((a,k)=>a==null?undefined:a[k],obj) ?? fallback; } catch { return fallback; }
}
function num(v){ const n=Number(v); return Number.isFinite(n)?n:null; }
function slug(s){ return String(s||"").toLowerCase().replace(/[^\p{L}\p{N}]+/gu,"-").replace(/^-|-$/g,""); }
function adminToken(env){ return env.ADMIN_PASSWORD ? env.ADMIN_PASSWORD : ""; }
async function authAdmin(req, env) {
  const h=req.headers.get("authorization")||"";
  return h.startsWith("Bearer ") && h.slice(7) === await adminToken(env);
}
async function settings(env) {
  const row=await env.DB.prepare("SELECT value FROM settings WHERE key='config'").first();
  let cfg={...DEFAULTS};
  if(row?.value) try { cfg={...cfg,...JSON.parse(row.value)} } catch {}
  return cfg;
}
async function saveSettings(env,cfg) {
  await env.DB.prepare("INSERT INTO settings(key,value,updated_at) VALUES('config',?,?,datetime('now')) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=datetime('now')")
    .bind("config",JSON.stringify({...DEFAULTS,...cfg})).run();
}
function telegramUrlForGift(d){
  if(d.tg_link) return d.tg_link;
  const n=d.number||d.nft_number||"";
  const title=d.gift_title||d.name||"gift";
  return n ? `https://t.me/nft/${slug(title)}-${n}` : "";
}
function normalizeGift(x,cfg){
  const priceTon=num(x.price_per_month ?? x.monthly_price ?? x.price_per_day ?? x.price ?? x.amount ?? x.rent_price);
  const daily=num(x.price_per_day);
  const monthly=num(x.price_per_month ?? x.monthly_price);
  const baseTon = cfg.rentPriceMode==="daily" ? (daily ?? priceTon) : (monthly ?? priceTon);
  const fx=num(cfg.tonToTomanMultiplier)||1;
  const rawToman=(baseTon||0)*fx;
  const marked=rawToman*(1+(num(cfg.rentMarkupPercent)||0)/100);
  const min=num(cfg.rentMinToman)||0, max=num(cfg.rentMaxToman)||0;
  if(min && marked<min) return null;
  if(max && marked>max) return null;
  return {
    id:x.id||x.nft_address||x.address||x.slug||crypto.randomUUID(),
    nft_address:x.nft_address||x.address||x.id||"",
    name:x.name||`${x.gift_title||x.title||"Gift"} #${x.number||""}`.trim(),
    gift_title:x.gift_title||x.title||x.collection_name||"Telegram Gift",
    number:String(x.number??x.nft_number??""),
    image_url:x.image_url||x.image||x.img||"",
    tg_link:telegramUrlForGift(x),
    market_link:x.market_link||x.url||"",
    bg_color:x.bg_color||"#161d2a",
    rarity:x.rarity||"",
    price_ton:baseTon||0,
    price_toman:Math.round(marked),
    discount:x.discount||""
  };
}
async function marketGifts(env,cfg){
  const token=env.MARKETAPP_TOKEN||"";
  if(!token) throw new Error("MARKETAPP_TOKEN is not configured");
  const u=new URL(cfg.marketRentPath,cfg.marketBaseUrl);
  const res=await fetch(u,{headers:{Authorization:token,Accept:"application/json"}});
  if(!res.ok) throw new Error(`Marketapp ${res.status}`);
  const data=await res.json();
  const arr=Array.isArray(data)?data:(data.items||data.results||data.gifts||data.data||[]);
  return arr.map(x=>normalizeGift(x,cfg)).filter(Boolean);
}
async function swapFx(env,cfg){
  if(!cfg.swapBaseUrl||!cfg.swapPricePath) return null;
  const u=new URL(cfg.swapPricePath,cfg.swapBaseUrl);
  if(cfg.swapQuery) for(const pair of String(cfg.swapQuery).split("&")) {
    const [k,v]=pair.split("="); if(k) u.searchParams.set(k,v??"");
  }
  const headers={Accept:"application/json"};
  if(env.SWAP_API_TOKEN){
    headers[cfg.swapTokenHeader||"Authorization"]=(cfg.swapTokenPrefix||"")+env.SWAP_API_TOKEN;
  }
  const init={method:(cfg.swapMethod||"GET").toUpperCase(),headers};
  const res=await fetch(u,init);
  if(!res.ok) throw new Error(`Swap API ${res.status}`);
  const data=await res.json();
  const rate=num(pathGet(data,cfg.swapJsonPath));
  if(!rate) throw new Error("Swap response path did not resolve to a number");
  return rate;
}
async function getFx(env,cfg){
  const live=await swapFx(env,cfg).catch(()=>null);
  if(live) return live;
  return num(cfg.tonToTomanMultiplier)||1;
}
async function sendTelegram(env,chatId,text){
  if(!env.TELEGRAM_BOT_TOKEN||!chatId) return;
  await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`,{
    method:"POST",headers:{"content-type":"application/json"},
    body:JSON.stringify({chat_id:String(chatId),text,disable_web_page_preview:true})
  }).catch(()=>{});
}
async function notifyAdmin(env,text){
  return sendTelegram(env,env.ADMIN_CHAT_ID,text);
}
async function createOrder(env,p){
  const id="RNT-"+Date.now().toString(36).toUpperCase()+"-"+Math.floor(Math.random()*9999);
  const inferred = p.orderType || (/استارز/i.test(p.itemsText||"") ? "stars" : /پرمیوم/i.test(p.itemsText||"") ? "premium" : "rent_gift");
  await env.DB.prepare(`INSERT INTO orders(id,user_id,user_name,order_type,items_json,items_text,total_price,status,created_at,updated_at)
    VALUES(?,?,?,?,?,?,?,?,datetime('now'),datetime('now'))`)
    .bind(id,String(p.userId),p.userName||"",inferred,JSON.stringify(p.items||[]),p.itemsText||"",Number(p.totalPrice)||0,"pending_receipt").run();
  return id;
}
const GUIDE=(cfg)=>{ const t=cfg.guideText||DEFAULTS.guideText; return cfg.tutorialUrl ? `${t}\n\n🎥 لینک آموزش تصویری:\n${cfg.tutorialUrl}` : t; };
async function handle(req,env){
  const u=new URL(req.url), p=u.pathname, method=req.method;
  if(method==="OPTIONS") return new Response("",{status:204,headers:{"access-control-allow-origin":"*","access-control-allow-headers":"Content-Type, Authorization","access-control-allow-methods":"GET,POST,OPTIONS"}});
  if(p==="/api/health") return json({ok:true});
  if(p==="/api/settings" && method==="GET"){
    const c=await settings(env); const safe={...c}; return json(safe);
  }
  if(p==="/api/rent/gifts" && method==="GET"){
    const c=await settings(env);
    try {
      const fx=await getFx(env,c); const gifts=await marketGifts(env,{...c,tonToTomanMultiplier:fx});
      return json({items:gifts,tonToToman:fx,updatedAt:new Date().toISOString()});
    } catch(e) { return json({error:e.message},502); }
  }
  if(p==="/api/admin/login" && method==="POST"){
    const b=await req.json().catch(()=>({}));
    if(!env.ADMIN_PASSWORD || b.password!==env.ADMIN_PASSWORD) return json({error:"invalid"},401);
    return json({token:env.ADMIN_PASSWORD});
  }
  if(p==="/api/admin/settings" && method==="POST"){
    if(!await authAdmin(req,env)) return json({error:"unauthorized"},401);
    const b=await req.json(); await saveSettings(env,b); return json({ok:true});
  }
  if(p==="/api/order/submit" && method==="POST"){
    const b=await req.json();
    const id=await createOrder(env,b);
    await sendTelegram(env,b.userId,`🧾 سفارش شما ثبت شد\nشماره سفارش: ${id}\nمبلغ: ${Number(b.totalPrice||0).toLocaleString()} تومان\n\nپس از پرداخت، رسید را در ربات ارسال کنید.`);
    return json({ok:true,orderId:id});
  }
  if(p==="/api/order/fragment-link" && method==="POST"){
    const b=await req.json();
    const order=await env.DB.prepare("SELECT * FROM orders WHERE id=? AND user_id=?").bind(String(b.orderId),String(b.userId)).first();
    if(!order) return json({error:"order_not_found"},404);
    const link=String(b.fragmentLink||"").trim();
    if(!/^https?:\/\/(www\.)?fragment\.com\//i.test(link)) return json({error:"invalid_fragment_link"},400);
    await env.DB.prepare("UPDATE orders SET fragment_link=?,status='awaiting_connection',updated_at=datetime('now') WHERE id=?").bind(link,order.id).run();
    await notifyAdmin(env,`🔗 لینک Fragment جدید\nسفارش: ${order.id}\nکاربر: ${order.user_name} (${order.user_id})\n${link}`);
    return json({ok:true});
  }
  if(p==="/api/user-data" && method==="GET"){
    const uid=u.searchParams.get("userId")||"";
    const rows=await env.DB.prepare("SELECT id,user_id,user_name,order_type,items_json,items_text,total_price,status,fragment_link,created_at,updated_at FROM orders WHERE user_id=? ORDER BY created_at DESC LIMIT 30").bind(uid).all();
    return json({orders:rows.results||[],guide:GUIDE(await settings(env))});
  }
  if(p==="/api/admin/orders" && method==="GET"){
    if(!await authAdmin(req,env)) return json({error:"unauthorized"},401);
    const rows=await env.DB.prepare("SELECT * FROM orders ORDER BY created_at DESC LIMIT 100").all();
    return json(rows.results||[]);
  }
  if(p==="/api/admin/order-action" && method==="POST"){
    if(!await authAdmin(req,env)) return json({error:"unauthorized"},401);
    const b=await req.json(); const o=await env.DB.prepare("SELECT * FROM orders WHERE id=?").bind(String(b.orderId)).first();
    if(!o) return json({error:"not_found"},404);
    const map={appr:"processing",rejc:"rejected",done:"completed",connected:"completed"};
    const status=map[b.action]||b.status; await env.DB.prepare("UPDATE orders SET status=?,updated_at=datetime('now') WHERE id=?").bind(status,o.id).run();
    const cfg=await settings(env);
    if(b.action==="appr" && o.order_type==="rent_gift") {
      await sendTelegram(env,o.user_id,`✅ پرداخت سفارش ${o.id} تأیید شد.\n\n${GUIDE(cfg)}\n\n🔗 لطفاً لینک Fragment را از داخل فروشگاه برای همین سفارش ارسال کنید.`);
    }
    if(b.action==="connected") await sendTelegram(env,o.user_id,`✅ اتصال سفارش ${o.id} با موفقیت توسط مدیریت تأیید شد.\nممنون از خرید شما.`);
    return json({ok:true,status});
  }
  if(p==="/api/admin/analytics" && method==="GET"){
    if(!await authAdmin(req,env)) return json({error:"unauthorized"},401);
    const revenue=await env.DB.prepare("SELECT COALESCE(SUM(total_price),0) v FROM orders WHERE status='completed'").first();
    const orders=await env.DB.prepare("SELECT COUNT(*) v FROM orders").first();
    const users=await env.DB.prepare("SELECT COUNT(DISTINCT user_id) v FROM orders").first();
    return json({totalRevenue:revenue?.v||0,totalOrders:orders?.v||0,totalUsers:users?.v||0});
  }
  return json({error:"not_found"},404);
}
export default {fetch:handle};
