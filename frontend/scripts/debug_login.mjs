import { chromium } from "playwright";
import { mkdirSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, resolve } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(__dirname, "../../docs/assets/debug");
mkdirSync(OUT, { recursive: true });

const BASE = process.env.BASE_URL || "http://localhost:5173";

const ACCOUNTS = [
  { role: "admin", email: "admin@city.gov", password: "admin123" },
  { role: "lead", email: "lead@city.gov", password: "lead123" },
  { role: "officer", email: "officer@city.gov", password: "officer123" },
  { role: "citizen", email: "citizen@example.com", password: "citizen123" },
];

async function run(account) {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const consoleErrors = [];
  const consoleWarnings = [];
  const pageErrors = [];
  const failedRequests = [];

  page.on("console", (msg) => {
    const type = msg.type();
    if (type === "error") consoleErrors.push(msg.text());
    else if (type === "warning") consoleWarnings.push(msg.text());
  });
  page.on("pageerror", (err) => pageErrors.push(err.stack || err.message));
  page.on("requestfailed", (req) =>
    failedRequests.push(`${req.method()} ${req.url()} :: ${req.failure()?.errorText}`)
  );
  page.on("response", (res) => {
    if (res.status() >= 400)
      failedRequests.push(`HTTP ${res.status()} ${res.request().method()} ${res.url()}`);
  });

  await page.goto(BASE, { waitUntil: "networkidle" });

  // Login flow
  await page.fill('input[type="email"]', account.email);
  await page.fill('input[type="password"]', account.password);
  await Promise.all([
    page.click('button[type="submit"]'),
  ]);

  // Wait for the login view to go away / app shell to mount
  try {
    await page.waitForSelector('header', { timeout: 8000 });
  } catch { /* maybe crashed */ }
  await page.waitForTimeout(3500); // let dashboards fetch + render
  try { await page.waitForLoadState("networkidle", { timeout: 8000 }); } catch {}

  const root = await page.$("#root");
  const innerLen = root ? (await root.innerHTML()).length : 0;
  const visibleText = (await page.evaluate(() => document.body.innerText || "")).trim();

  await page.screenshot({ path: resolve(OUT, `${account.role}.png`), fullPage: true });

  await browser.close();

  return {
    role: account.role,
    rootInnerHTMLLength: innerLen,
    visibleTextLength: visibleText.length,
    visibleTextSample: visibleText.slice(0, 120).replace(/\s+/g, " "),
    consoleErrors,
    consoleWarnings: consoleWarnings.slice(0, 5),
    pageErrors,
    failedRequests,
  };
}

const results = [];
for (const acc of ACCOUNTS) {
  try {
    results.push(await run(acc));
  } catch (e) {
    results.push({ role: acc.role, fatal: e.stack || e.message });
  }
}

console.log(JSON.stringify(results, null, 2));
