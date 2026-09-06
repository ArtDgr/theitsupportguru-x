import { firefox } from "playwright";
import fs from "node:fs";
const profileDir = process.env.X_PROFILE_DIR || "profiles/x-playwright";
fs.mkdirSync(profileDir, {recursive:true});
const ctx = await firefox.launchPersistentContext(profileDir, {headless:false});
const page = await ctx.newPage();
await page.goto("https://x.com/login", {waitUntil:"domcontentloaded"});
console.log("Firefox opened. Log into @theitsupportguru there. Press Enter in this terminal when done, or wait 5 min for auto-save...");
await new Promise(r=>{
  let done=false;
  process.stdin.once("data",()=>{ if(!done){ done=true; r(); }});
  setTimeout(()=>{ if(!done){ done=true; r(); }}, 300000);
});
const cookies = await ctx.cookies();
fs.writeFileSync("out/x-cookies.json", JSON.stringify(cookies, null, 2));
console.log(`Saved ${cookies.length} cookies to out/x-cookies.json`);
const b64 = Buffer.from(JSON.stringify(cookies)).toString("base64");
console.log(`\n=== X_COOKIES_B64 (paste this) ===\n${b64}\n=== end ===\nRun:\ngh secret set X_COOKIES_B64 --repo ArtDgr/theitsupportguru-x --body "${b64.slice(0,30)}..."\nOr: echo "${b64}" | gh secret set X_COOKIES_B64 --repo ArtDgr/theitsupportguru-x`);
await ctx.close();
