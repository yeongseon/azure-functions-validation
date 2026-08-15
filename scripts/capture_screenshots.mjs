// Live endpoint screenshot capture for the Azure Release Certification workflow.
//
// Runs against a freshly deployed e2e_app on real Azure and renders each
// endpoint's HTTP response into a styled page, then screenshots it. The three
// captures demonstrate the package end to end: a healthy GET, a validated
// create (200), and the standardized 422 validation-error envelope.
//
// Resilient by design: a failure to reach one endpoint is recorded in
// metadata.json and never aborts the run, so screenshot capture can never gate
// a release certification.
import { chromium } from "playwright";
import { mkdir, writeFile } from "node:fs/promises";
import { join } from "node:path";

const BASE_URL = (process.env.E2E_APP_URL || "").replace(/\/+$/, "");
const OUT_DIR = process.env.OUT_DIR || "screenshots";
const VERSION = process.env.CAPTURE_VERSION || "";
const SHA = process.env.CAPTURE_SHA || "";

const targets = [
  { id: "e2e_app_health", method: "GET", path: "/api/health" },
  {
    id: "e2e_app_items_created",
    method: "POST",
    path: "/api/items",
    body: { name: "widget", quantity: 3 },
  },
  {
    id: "e2e_app_items_validation_error",
    method: "POST",
    path: "/api/items",
    body: { name: "", quantity: 0 },
  },
];

function escapeHtml(value) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function renderPage(target, status, bodyText) {
  const curlBody = target.body ? ` -d '${JSON.stringify(target.body)}'` : "";
  const request = `${target.method} ${target.path}`;
  let pretty = bodyText;
  try {
    pretty = JSON.stringify(JSON.parse(bodyText), null, 2);
  } catch {
    /* leave raw body as-is */
  }
  return `<!doctype html><html><head><meta charset="utf-8"><style>
    body { margin: 0; background: #0d1117; color: #e6edf3;
      font-family: "SFMono-Regular", ui-monospace, Menlo, Consolas, monospace; }
    .wrap { padding: 28px 32px; }
    .req { color: #7ee787; font-size: 18px; margin-bottom: 6px; }
    .curl { color: #8b949e; font-size: 13px; margin-bottom: 18px; }
    .status { font-size: 15px; margin-bottom: 14px; }
    .ok { color: #7ee787; } .err { color: #ff7b72; }
    pre { background: #161b22; border: 1px solid #30363d; border-radius: 8px;
      padding: 18px 20px; font-size: 15px; line-height: 1.5; margin: 0; }
  </style></head><body><div class="wrap">
    <div class="req">${escapeHtml(request)}</div>
    <div class="curl">curl -X ${target.method} ${escapeHtml(BASE_URL + target.path)}${escapeHtml(curlBody)}</div>
    <div class="status">HTTP <span class="${status >= 200 && status < 400 ? "ok" : "err"}">${status}</span></div>
    <pre>${escapeHtml(pretty)}</pre>
  </div></body></html>`;
}

async function main() {
  await mkdir(OUT_DIR, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1000, height: 640 } });
  const records = [];

  for (const target of targets) {
    const record = {
      id: target.id,
      image: `${target.id}.png`,
      request: `${target.method} ${target.path}`,
      method: "playwright",
    };
    try {
      const init = { method: target.method, headers: {} };
      if (target.body) {
        init.headers["Content-Type"] = "application/json";
        init.body = JSON.stringify(target.body);
      }
      const res = await fetch(BASE_URL + target.path, init);
      const text = await res.text();
      record.http_status = res.status;
      await page.setContent(renderPage(target, res.status, text), {
        waitUntil: "load",
      });
      await page.screenshot({ path: join(OUT_DIR, `${target.id}.png`) });
      record.captured = true;
    } catch (err) {
      record.captured = false;
      record.error = String(err);
    }
    records.push(record);
  }

  await browser.close();
  await writeFile(
    join(OUT_DIR, "metadata.json"),
    JSON.stringify(
      {
        package_version: VERSION,
        git_sha: SHA,
        base_url: BASE_URL,
        captured_at: new Date().toISOString(),
        method: "playwright",
        screenshots: records,
      },
      null,
      2,
    ),
  );
  console.log(`Captured ${records.filter((r) => r.captured).length}/${records.length} screenshot(s).`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
