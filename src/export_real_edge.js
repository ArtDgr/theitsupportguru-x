import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
// Uses your REAL Edge profile where you're already logged in at https://x.com/TheITSupprtGuru
// No login, no Confirm, no bot flag — just reads existing cookies
const edgeUserData = path.join(os.homedir(), "AppData", "Local", "Microsoft", "Edge", "User Data");
console.log(`Using Edge profile: ${edgeUserData}`);
if(!fs.existsSync(edgeUserData)) {
  console.log("Edge profile not found. Try: C:\\Users\\Admin\\AppData\\Local\\Microsoft\\Edge\\User Data");
  process.exit(1);
}
// Close Edge first if open, or it will lock
console.log("Close Edge completely (all windows) before this runs, then press Enter...");
await new Promise(r=>{ process.stdin.once("data",()=>r()); });
const ctx = await chromium.launchPersistentContext(edgeUserData, {
  channel: "msedge",
  headless: false,
  args: ["--disable-blink-features=AutomationControlled"]
});
const cookies = await ctx.cookies("https://x.com");
console.log(`Found ${cookies.length} cookies for x.com`);
const hasAuth = cookies.some(c=>c.name==="auth_token");
console.log(`has auth_token: ${hasAuth} ${hasAuth? "(good)" : "(not logged in as @theitsupprtguru in this Edge profile — log in at https://x.com/TheITSupprtGuru in Edge first)"}`);
fs.mkdirSync("out",{recursive:true});
fs.writeFileSync("out/x-cookies.json", JSON.stringify(cookies, null, 2));
const b64 = Buffer.from(JSON.stringify(cookies)).toString("base64");
fs.writeFileSync("out/x-cookies.b64.txt", b64);
console.log(`\n=== X_COOKIES_B64 ===\n${b64}\n=== end ===`);
await ctx.close();
