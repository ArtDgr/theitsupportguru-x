import fs from "node:fs";
import { firefox, chromium } from "playwright";
const AEST = 10*3600*1000;
const profileDir = process.env.X_PROFILE_DIR || "profiles/x-playwright";
fs.mkdirSync(profileDir, {recursive:true});
// Try stealth chromium (msedge) first — X blocks Firefox automation more often. Fallback to firefox.
let ctx;
try{
  ctx = await chromium.launchPersistentContext(profileDir, {headless:false, channel:"msedge", viewport:{width:1280,height:800}});
  console.log("[export] Launched Edge (stealth) profile");
}catch{
  ctx = await firefox.launchPersistentContext(profileDir, {headless:false, viewport:{width:1280,height:800}});
  console.log("[export] Launched Firefox profile");
}
const page = await ctx.newPage();
await page.goto("https://x.com/login", {waitUntil:"domcontentloaded", timeout:60000});
console.log("Browser opened. Log into @theitsupprtguru there (complete 2FA/captcha if shown).");
console.log("Waiting for login to complete (auth_token)... Press Enter when you see your Home timeline, or wait for auto-detect (5 min)...");
let done=false;
const stdinPromise = new Promise(r=>{ process.stdin.once("data",()=>{ if(!done){ done=true; r("enter"); }})});
const pollPromise = (async()=>{
  for(let i=0;i<300;i++){
    await new Promise(r=>setTimeout(r,1000));
    if(done) break;
    try{
      const cookies = await ctx.cookies();
      const hasAuth = cookies.some(c=>c.name==="auth_token" && c.value.length>10);
      if(hasAuth){
        console.log(`[export] auth_token detected after ${i+1}s — saving...`);
        done=true;
        return "auto";
      }
      if(i%15===14) console.log(`[export] still waiting... ${i+1}s (cookies: ${cookies.length}, has auth: ${hasAuth}) — log in in the window`);
    }catch{}
  }
  return "timeout";
})();
const reason = await Promise.race([stdinPromise, pollPromise]);
console.log(`[export] saving due to: ${reason}`);
const cookies = await ctx.cookies();
fs.mkdirSync("out",{recursive:true});
fs.writeFileSync("out/x-cookies.json", JSON.stringify(cookies, null, 2));
const hasAuth = cookies.some(c=>c.name==="auth_token" && c.value.length>10);
console.log(`Saved ${cookies.length} cookies to out/x-cookies.json, has auth_token: ${hasAuth}`);
if(!hasAuth) console.log("WARNING: No auth_token — login did not complete. Try again, complete captcha/2FA in the window, then press Enter.");
const b64 = Buffer.from(JSON.stringify(cookies)).toString("base64");
console.log(`\n=== X_COOKIES_B64 (paste this) ===\n${b64}\n=== end ===\nRun:\ngh secret set X_COOKIES_B64 --repo ArtDgr/theitsupportguru-x --body "${b64.slice(0,30)}..."\nOr: echo "${b64}" | gh secret set X_COOKIES_B64 --repo ArtDgr/theitsupportguru-x`);
await ctx.close();

