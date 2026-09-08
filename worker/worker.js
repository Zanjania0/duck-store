/**
 * Duck Store Rent API
 * Cloudflare Worker + D1
 *
 * Secrets:
 *   MARKETAPP_API_TOKEN
 *   SWAP_API_KEY (optional if Swap endpoint does not need one)
 *   ADMIN_PASSWORD
 *
 * D1 binding: DB
 */
const DEFAULTS = {
  enabled: true,
  marketBaseUrl: "https://api.marketapp.org",
  marketEndpoint: "/v1/rent/gifts/",
  marketLimit: 200,
  marketSortBy: "price_per_day_asc",
  marketCurrency: "TON",
  marketPricePath: "price_per_day",
  marketNamePath: "gift_name",
  marketNumberPath: "gift_number",
  marketImagePath: "image_url",
  marketAddressPath: "nft_address",
  marketCollectionPath: "collection_name",
  marketDurationPath: "duration",
  marketLinkPath: "market_link",
  swapRateUrl: "",
  swapRateMethod: "GET",
  swapRatePath: "rate",
  swapFrom: "TON",
  swapTo: "IRR",
  irrToToman: 0.1,
  manualRate: 0,
  useManualRate: false,
  profitPercent: 20,
  fixedProfitToman: 0,
  roundingStep: 1000,
  minSourceTon: 0,
  maxSourceTon: 0,
  minFinalToman: 0,
  maxFinalToman: 0,
  defaultRentDays: 30,
  minRentDays: 1,
  maxRentDays: 365,
  pricePerDay: true,
  enabledCollections: [],
  excludedCollections: [],
  hiddenNumbers: [],
  displayLimit: 200,
  sort: "final_price_asc",
  cacheSeconds: 120,
  staleSeconds: 1800,
  fallbackEnabled: true,
  fallbackTonToToman: 0,
  fallbackPriceMode: "keep",
  title: "اجاره گیفت تلگرام",
  subtitle: "قیمت لحظه‌ای بر اساس MarketApp + نرخ صرافی",
};

function json(data, status=200, extra={}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {"content-type":"application/json; charset=utf-8", ...extra}
  });
}
function cors(h={}) {
  return {
    "access-control-allow-origin": "*",
    "access-control-allow-methods": "GET,POST,OPTIONS",
    "access-control-allow-headers": "Content-Type, Authorization",
    ...h
  };
}
function ok(data, status=200){ return json(data,status,cors()); }

async function dbGet(env, key, fallback=null) {
  const row = await env.DB.prepare("SELECT value FROM settings WHERE key=?1").bind(key).first();
  if (!row) return fallback;
  try { return JSON.parse(row.value); } catch { return row.value; }
}
async function dbSet(env, key, value) {
  await env.DB.prepare(
    "INSERT INTO settings(key,value,updated_at) VALUES(?1,?2,datetime('now')) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at"
  ).bind(key, JSON.stringify(value)).run();
}
async function getSettings(env) {
  const s = await dbGet(env, "rent_settings", {});
  return {...DEFAULTS, ...(s || {})};
}
function deepGet(obj, path, fallback=null) {
  if (!path) return fallback;
  const parts = String(path).replace(/\[(\d+)\]/g, ".$1").split(".").filter(Boolean);
  let cur=obj;
  for (const p of parts) {
    if (cur == null) return fallback;
    cur=cur[p];
  }
  return cur == null ? fallback : cur;
}
function num(v, fallback=0){
  if (typeof v === "number" && Number.isFinite(v)) return v;
  const n=parseFloat(String(v ?? "").replace(/,/g,""));
  return Number.isFinite(n) ? n : fallback;
}
function normalizeList(payload){
  if (Array.isArray(payload)) return payload;
  for (const k of ["items","results","data","gifts","rent_items","rentItems"]) {
    if (Array.isArray(payload?.[k])) return payload[k];
  }
  if (Array.isArray(payload?.data?.items)) return payload.data.items;
  return [];
}
function normalizeItem(x, s){
  const name = deepGet(x,s.marketNamePath, deepGet(x,"name",deepGet(x,"gift_title","Telegram Gift")));
  const number = deepGet(x,s.marketNumberPath, deepGet(x,"number",deepGet(x,"gift_number","")));
  const sourceTon = num(
    deepGet(x,s.marketPricePath, deepGet(x,"price_per_day",deepGet(x,"price",deepGet(x,"rent_price",0))))
  );
  const image = deepGet(x,s.marketImagePath, deepGet(x,"image_url",deepGet(x,"image","")));
  const collection = deepGet(x,s.marketCollectionPath, deepGet(x,"collection_name",deepGet(x,"gift_title",name)));
  const address = deepGet(x,s.marketAddressPath, deepGet(x,"nft_address",deepGet(x,"address","")));
  const duration = deepGet(x,s.marketDurationPath, deepGet(x,"duration",s.defaultRentDays));
  const marketLink = deepGet(x,s.marketLinkPath, deepGet(x,"market_link",""));
  const tgLink = deepGet(x,"tg_link", address ? `https://t.me/nft/${String(name).replace(/[^a-zA-Z0-9 ]/g,"").trim().split(/\s+/).map(w=>w[0]?.toUpperCase()+w.slice(1)).join("")}-${number}` : "https://t.me");
  return {raw:x,name:String(name),number:String(number),sourceTon,image:String(image||""),collection:String(collection||"Telegram Gift"),address:String(address||""),duration,tgLink,marketLink:String(marketLink||"")};
}
function roundMoney(v, step){
  const n=num(v);
  const st=Math.max(1,num(step,1));
  return Math.round(n/st)*st;
}
function calcFinal(item, s, rateToman){
  const sourceToman=item.sourceTon*rateToman;
  let final=sourceToman*(1+num(s.profitPercent)/100)+num(s.fixedProfitToman);
  final=roundMoney(final,s.roundingStep);
  const days=Math.max(s.minRentDays, Math.min(s.maxRentDays, num(s.defaultRentDays,30)));
  const total=s.pricePerDay ? final*days : final;
  return {sourceToman, priceToman:final, totalToman:roundMoney(total,s.roundingStep), rentDays:days};
}
function allowed(item, s, final){
  if (!s.enabled) return false;
  if (s.minSourceTon>0 && item.sourceTon<s.minSourceTon) return false;
  if (s.maxSourceTon>0 && item.sourceTon>s.maxSourceTon) return false;
  if (s.minFinalToman>0 && final.priceToman<s.minFinalToman) return false;
  if (s.maxFinalToman>0 && final.priceToman>s.maxFinalToman) return false;
  if (Array.isArray(s.enabledCollections) && s.enabledCollections.length && !s.enabledCollections.includes(item.collection)) return false;
  if (Array.isArray(s.excludedCollections) && s.excludedCollections.includes(item.collection)) return false;
  if (Array.isArray(s.hiddenNumbers) && s.hiddenNumbers.includes(item.number)) return false;
  return true;
}
async function fetchMarket(env,s){
  const u=new URL(s.marketEndpoint,s.marketBaseUrl);
  u.searchParams.set("limit",String(s.marketLimit));
  if (s.marketSortBy) u.searchParams.set("sort_by",s.marketSortBy);
  const headers={"accept":"application/json"};
  if(env.MARKETAPP_API_TOKEN) headers.authorization=env.MARKETAPP_API_TOKEN;
  const r=await fetch(u,{headers});
  const text=await r.text();
  if(!r.ok) throw new Error(`MarketApp ${r.status}: ${text.slice(0,300)}`);
  return JSON.parse(text);
}
async function fetchSwapRate(env,s){
  if(s.useManualRate && num(s.manualRate)>0) return num(s.manualRate);
  if(!s.swapRateUrl) throw new Error("Swap rate URL is not configured");
  const headers={"accept":"application/json"};
  if(env.SWAP_API_KEY) {
    headers.authorization=`Bearer ${env.SWAP_API_KEY}`;
    headers["x-api-key"]=env.SWAP_API_KEY;
  }
  const r=await fetch(s.swapRateUrl,{method:s.swapRateMethod||"GET",headers});
  const text=await r.text();
  if(!r.ok) throw new Error(`Swap rate ${r.status}: ${text.slice(0,300)}`);
  const body=JSON.parse(text);
  let rate=num(deepGet(body,s.swapRatePath,0));
  if(!rate) {
    for(const p of ["rate","price","result.rate","data.rate","data.price","result.price","quote.rate","data.result.rate"]){
      rate=num(deepGet(body,p,0)); if(rate) break;
    }
  }
  if(!rate) throw new Error("Could not extract exchange rate from Swap response");
  return rate*num(s.irrToToman,0.1);
}
async function sync(env){
  const s=await getSettings(env);
  const [market, rateBase] = await Promise.all([
    fetchMarket(env,s),
    fetchSwapRate(env,s).catch(async e=>{
      if(num(s.fallbackTonToToman)>0) return num(s.fallbackTonToToman);
      if(s.fallbackEnabled) {
        const old=await dbGet(env,"last_rate",0);
        if(num(old)>0) return num(old);
      }
      throw e;
    })
  ]);
  const raw=normalizeList(market).map(x=>normalizeItem(x,s));
  const gifts=[];
  for(const item of raw){
    const c=calcFinal(item,s,rateBase);
    if(!allowed(item,s,c)) continue;
    gifts.push({...item,...c,sourceCurrency:s.marketCurrency,rateToman:rateBase});
  }
  gifts.sort((a,b)=>{
    if(s.sort==="source_price_asc") return a.sourceTon-b.sourceTon;
    if(s.sort==="source_price_desc") return b.sourceTon-a.sourceTon;
    if(s.sort==="name_asc") return a.name.localeCompare(b.name);
    return a.priceToman-b.priceToman;
  });
  const out={updatedAt:new Date().toISOString(),rateToman:rateBase,rateBase,gifts:gifts.slice(0,Math.max(1,num(s.displayLimit,200)))};
  await dbSet(env,"rent_cache",out);
  await dbSet(env,"last_rate",rateBase);
  return out;
}
function tokenFor(secret){
  return btoa(unescape(encodeURIComponent(secret))).replace(/=+$/,"");
}
function adminOk(req,env){
  const h=req.headers.get("authorization")||"";
  return h===`Bearer ${tokenFor(env.ADMIN_PASSWORD||"")}`;
}
async function handle(req,env){
  const url=new URL(req.url);
  if(req.method==="OPTIONS") return new Response(null,{headers:cors()});
  if(url.pathname==="/api/rent/settings" && req.method==="GET") return ok(await getSettings(env));
  if(url.pathname==="/api/rent/catalog" && req.method==="GET"){
    const s=await getSettings(env);
    let cache=await dbGet(env,"rent_cache",null);
    const age=cache?.updatedAt ? (Date.now()-Date.parse(cache.updatedAt))/1000 : Infinity;
    if(!cache || age>s.cacheSeconds){
      try { cache=await sync(env); }
      catch(e){
        if(!cache) return ok({error:e.message,gifts:[],settings:s},502);
      }
    }
    return ok({settings:s,...cache,stale:age>s.staleSeconds});
  }
  if(url.pathname==="/api/rent/sync" && req.method==="POST"){
    if(!adminOk(req,env)) return ok({error:"Unauthorized"},401);
    try { return ok(await sync(env)); } catch(e){ return ok({error:e.message},502); }
  }
  if(url.pathname==="/api/admin/login" && req.method==="POST"){
    const body=await req.json().catch(()=>({}));
    if(!env.ADMIN_PASSWORD || body.password!==env.ADMIN_PASSWORD) return ok({error:"Invalid password"},401);
    return ok({token:tokenFor(env.ADMIN_PASSWORD)});
  }
  if(url.pathname==="/api/admin/rent-settings" && req.method==="GET"){
    if(!adminOk(req,env)) return ok({error:"Unauthorized"},401);
    return ok(await getSettings(env));
  }
  if(url.pathname==="/api/admin/rent-settings" && req.method==="POST"){
    if(!adminOk(req,env)) return ok({error:"Unauthorized"},401);
    const body=await req.json().catch(()=>null);
    if(!body || typeof body!=="object") return ok({error:"Invalid body"},400);
    const merged={...DEFAULTS,...body};
    await dbSet(env,"rent_settings",merged);
    return ok(merged);
  }
  if(url.pathname==="/api/admin/rent-test-market" && req.method==="POST"){
    if(!adminOk(req,env)) return ok({error:"Unauthorized"},401);
    try {
      const s=await getSettings(env); const data=await fetchMarket(env,s);
      return ok({ok:true,count:normalizeList(data).length,sample:normalizeList(data).slice(0,3)});
    } catch(e){ return ok({ok:false,error:e.message},502); }
  }
  if(url.pathname==="/api/admin/rent-test-rate" && req.method==="POST"){
    if(!adminOk(req,env)) return ok({error:"Unauthorized"},401);
    try { const s=await getSettings(env); const raw=await fetchSwapRate(env,s); return ok({ok:true,rateToman:raw}); }
    catch(e){ return ok({ok:false,error:e.message},502); }
  }
  return ok({service:"duck-store-rent-api",version:"1.0.0"},200);
}
export default {
  async fetch(req,env){ return handle(req,env); },
  async scheduled(event,env,ctx){
    ctx.waitUntil(sync(env).catch(()=>{}));
  }
};
