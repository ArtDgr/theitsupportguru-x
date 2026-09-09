import fs from "node:fs";
import path from "node:path";
import { firefox } from "playwright";
const AEST = 10*3600*1000;
function todayAEST(){ return new Date(Date.now()+AEST).toISOString().slice(0,10); }
function loadTweets(){
  const p = path.join("out","tweets.json");
  if(!fs.existsSync(p)) throw new Error("no out/tweets.json — run synthesize.py first");
  return JSON.parse(fs.readFileSync(p,"utf8"));
}
function pickForSlot(tweets){
  const now = new Date(Date.now()+AEST);
  const hm = now.toTimeString().slice(0,5);
  const times = ["06:00","12:00","17:00","20:00"];
  let idx = 0;
  for(let i=0;i<times.length;i++){
    if(hm >= times[i]) idx = i;
  }
  // Deterministic per slot today
  return tweets[idx % tweets.length] || tweets[0];
}
async function run({dry=false}={}){
  const tweets = loadTweets();
  const tweet = pickForSlot(tweets);
  const text = tweet.text || "";
  console.log(`[x-headless] ${dry?"DRY ":""}slot ${tweet.slot} (${text.length} chars) -> ${text.slice(0,80)}...`);
  if(dry){ console.log("[x-headless] dry-run, not posting"); return; }
  const profileDir = process.env.X_PROFILE_DIR || "profiles/x-playwright";
  fs.mkdirSync(profileDir,{recursive:true});
  let storageStatePath = null;
  let cookiesToInject = null;
  if(process.env.X_STORAGE_B64){
    try{
      const state = JSON.parse(Buffer.from(process.env.X_STORAGE_B64, "base64").toString("utf8"));
      storageStatePath = "/tmp/x-storage.json";
      fs.writeFileSync(storageStatePath, JSON.stringify(state));
      console.log(`[x-headless] storageState ready (${state.cookies.length} cookies, ${state.origins?.length||0} origins)`);
    }catch(e){ console.log("X_STORAGE_B64 parse fail: "+e.message); }
  } else if(process.env.X_COOKIES_B64){
    try{
      const j = JSON.parse(Buffer.from(process.env.X_COOKIES_B64, "base64").toString("utf8"));
      cookiesToInject = j;
      console.log(`[x-headless] loaded ${j.length} cookies from X_COOKIES_B64`);
    }catch(e){ console.log("X_COOKIES_B64 parse fail: "+e.message); }
  } else if(fs.existsSync("/tmp/x-cookies.json")){
    try{
      cookiesToInject = JSON.parse(fs.readFileSync("/tmp/x-cookies.json","utf8"));
      console.log(`[x-headless] loaded cookies from /tmp/x-cookies.json`);
    }catch{}
  }
  const launchOpts = { headless: true, viewport:{width:1280,height:800} };
  if(storageStatePath) launchOpts.storageState = storageStatePath;
  const browser = await firefox.launchPersistentContext(profileDir, launchOpts);
  const page = browser.pages()[0] || await browser.newPage();
  if(!storageStatePath && cookiesToInject){
    try{
      const normalized = cookiesToInject.map(c=>{
        let exp = c.expires;
        if(exp && exp > 1e12) exp = Math.floor(exp/1000);
        if(exp && exp < 0) exp = -1;
        // Fix Firefox host .x.com -> playwright expects domain .x.com is ok, but url is more reliable for HttpOnly
        return {
          name: c.name,
          value: c.value,
          domain: c.domain || ".x.com",
          path: c.path || "/",
          expires: exp ?? -1,
          httpOnly: !!c.httpOnly,
          secure: !!c.secure,
          sameSite: (c.sameSite==="None" && c.secure) ? "None" : "Lax",
          url: "https://x.com"
        };
      }).filter(c=>c.value);
      // Playwright addCookies wants either url or domain/path, but url takes precedence and handles HttpOnly
      const forAdd = normalized.map(({url, ...rest}) => ({...rest, url}));
      await browser.addCookies(forAdd);
      console.log(`[x-headless] cookies injected via url (${forAdd.length})`);
    }catch(e){ console.log("cookie inject fail: "+e.message); }
  } else if(storageStatePath){
    console.log(`[x-headless] using storageState, no addCookies needed`);
  }
  try{
    await page.goto("https://x.com/home", {waitUntil:"domcontentloaded", timeout:40000});
    await page.waitForTimeout(2500);
    const composer = page.locator('div[data-testid="tweetTextarea_0"], div[role="textbox"]').first();
    if(!(await composer.isVisible().catch(()=>false))){
      console.log("[x-headless] Not logged in — go to https://x.com/login in this profile once, or set X_COOKIES_B64 secret");
      throw new Error("Not logged in on X");
    }
    await composer.click();
    await page.keyboard.type(text, {delay: 40 + Math.random()*60});
    await page.waitForTimeout(1200);
    const postBtn = page.locator('div[data-testid="tweetButtonInline"]').first();
    await postBtn.click();
    console.log("[x-headless] posted");
    await page.waitForTimeout(3000);
  } finally {
    await browser.close().catch(()=>{});
  }
}
const dry = process.argv.includes("--dry");
run({dry}).catch(e=>{ console.error(e.message); process.exit(1); });
