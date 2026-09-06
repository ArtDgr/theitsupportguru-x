import fs from "node:fs";
// Chrome extension export: user is already logged in at https://x.com/TheITSupprtGuru
// Guide: Install "Cookie-Editor" extension, export cookies as JSON, save to out/x-cookies.json, then run this to convert to B64
const p = "out/x-cookies.json";
if(!fs.existsSync(p)){
  console.log(`Missing ${p}. Do this:`);
  console.log(`1. Chrome -> https://x.com/TheITSupprtGuru (logged in)`);
  console.log(`2. Install "Cookie-Editor" extension (https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)`);
  console.log(`3. Click Cookie-Editor icon -> Export -> Export as JSON -> Copy`);
  console.log(`4. Paste into out/x-cookies.json (create file, paste JSON array)`);
  console.log(`5. Then run: node src/export_x_cookies_chrome.js`);
  process.exit(1);
}
let cookies = JSON.parse(fs.readFileSync(p,"utf8"));
// Cookie-Editor exports as array of {name, value, domain, ...} but may need mapping to Playwright format
cookies = cookies.map(c=>({
  name: c.name,
  value: c.value,
  domain: c.domain || ".x.com",
  path: c.path || "/",
  expires: c.expirationDate || c.expires || -1,
  httpOnly: !!c.httpOnly,
  secure: !!c.secure,
  sameSite: c.sameSite || "None"
}));
const hasAuth = cookies.some(c=>c.name==="auth_token");
console.log(`Loaded ${cookies.length} cookies from ${p}, has auth_token: ${hasAuth}`);
if(!hasAuth) console.log("WARNING: No auth_token found — you are not logged in as @theitsupprtguru in that Chrome export. Log in at https://x.com/login first, then export again.");
const b64 = Buffer.from(JSON.stringify(cookies)).toString("base64");
fs.writeFileSync("out/x-cookies.b64.txt", b64);
console.log(`\n=== X_COOKIES_B64 ===\n${b64}\n=== end ===`);
console.log(`\nRun: echo "${b64.slice(0,40)}..." | gh secret set X_COOKIES_B64 --repo ArtDgr/theitsupportguru-x`);
if(hasAuth) console.log("SUCCESS: auth_token found — this will work for headless posting.");
