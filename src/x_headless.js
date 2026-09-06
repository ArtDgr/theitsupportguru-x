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
  const browser = await firefox.launchPersistentContext(profileDir, {headless: true, viewport:{width:1280,height:800}});
  const page = await browser.newPage();
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
