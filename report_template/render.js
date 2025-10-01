// render.js (ESM)
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import puppeteer from "puppeteer";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// 既定のHTML（ベースとなる report.html を固定）
const DEFAULT_HTML_PATH = path.resolve(__dirname, "report_template.html");

function ts() {
  const d = new Date();
  const z = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}${z(d.getMonth() + 1)}${z(d.getDate())}-${z(
    d.getHours()
  )}${z(d.getMinutes())}${z(d.getSeconds())}`;
}

function toBaseUrl(dirPath) {
  let href = pathToFileURL(path.resolve(dirPath)).href;
  if (!href.endsWith("/")) href += "/";
  return href; // e.g. file:///.../
}

function parseArgs(argv) {
  const flags = { html: null };
  const positional = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--html") {
      flags.html = argv[++i];
      continue;
    }
    positional.push(a);
  }
  return { flags, positional };
}

async function readTrichoData(tempDir) {
  const p = path.join(tempDir, "tricho_data.json");
  const raw = await fs.readFile(p, "utf8");
  const json = JSON.parse(raw);

  // 期待構造: { report_metadata: {...}, tricho_analysis: [...] }
  const meta = json.report_metadata || {};
  const arr = Array.isArray(json.tricho_analysis) ? json.tricho_analysis : [];

  return { meta, arr };
}

function safeMeta(meta, key, fallback) {
  const v = meta?.[key];
  if (v === undefined || v === null) return fallback;
  const s = String(v).trim();
  return s ? s : fallback;
}

async function main() {
  const [, , ...raw] = process.argv;
  const { flags, positional } = parseArgs(raw);

  if (positional.length < 1) {
    console.error(
      "Usage:\n" +
        "  node render.js <temp_dir> [out.pdf] [--html /path/to/report.html]\n\n" +
        "Assumptions:\n" +
        "  <temp_dir>/tricho_data.json\n" +
        "  <temp_dir>/filtered_images/*.png            # 本人（B）\n" +
        "Output:\n" +
        "  PDF => parent(<temp_dir>)/report-YYYYMMDD-HHMMSS.pdf  (or specified name)"
    );
    process.exit(1);
  }

  const tempDir = path.resolve(positional[0]);
  const outNameMaybe = positional[1];
  const htmlPath = flags.html ? path.resolve(flags.html) : DEFAULT_HTML_PATH;

  // 出力は temp 親ディレクトリ
  const parentDir = path.dirname(tempDir);
  const outPath = path.join(
    parentDir,
    outNameMaybe && path.extname(outNameMaybe).toLowerCase() === ".pdf"
      ? outNameMaybe
      : `report-${ts()}.pdf`
  );

  // 進行ログ
  console.log("=== Tricho Report Render ===");
  console.log("temp_dir        :", tempDir);
  console.log(
    "html            :",
    htmlPath,
    flags.html ? "(override)" : "(default)"
  );
  console.log("pdf_out         :", outPath);

  // 入力の存在チェック
  console.log("▶ Checking inputs...");
  const dataJsonPath = path.join(tempDir, "tricho_data.json");
  await fs.access(dataJsonPath).catch(() => {
    console.error("✗ Missing file:", dataJsonPath);
    process.exit(1);
  });
  await fs.access(htmlPath).catch(() => {
    console.error("✗ Missing HTML:", htmlPath);
    process.exit(1);
  });

  // データ読込
  console.log("▶ Reading tricho_data.json ...");
  const { meta, arr } = await readTrichoData(tempDir);
  const patientId = safeMeta(meta, "name", "-");
  const examDate = safeMeta(
    meta,
    "appointment_date",
    new Date().toLocaleString("ja-JP")
  );
  console.log("  patientId     :", patientId);
  console.log("  examDate      :", examDate);
  console.log("  regions(count):", arr.length);

  // 画像ディレクトリ
  const patientImagesDir = path.join(tempDir, "filtered_images");
  const normalImagesDir = path.join(__dirname, "normal_images");
  console.log("  images.A(normal):", normalImagesDir);
  console.log("  images.B(patient):", patientImagesDir);

  // Puppeteer
  console.log("▶ Launching browser...");
  const browser = await puppeteer.launch({
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
    headless: "new",
  });
  const page = await browser.newPage();

  // ページ側 console をターミナルに中継
  page.on("console", (msg) => {
    const type = msg.type();
    const text = msg.text();
    // 長い dataURL を抑制したい場合は適宜短縮
    console.log(`[page:${type}]`, text);
  });

  console.log("▶ Loading HTML ...");
  const url = pathToFileURL(htmlPath).href;
  await page.goto(url, { waitUntil: "domcontentloaded" });

  // 画像ベースURL
  const images = {
    normalBaseUrl: toBaseUrl(normalImagesDir),
    patientBaseUrl: toBaseUrl(patientImagesDir),
  };

  console.log("▶ Injecting data & rendering ...");
  console.time("render:evaluate");
  await page.evaluate(
    (payload) => {
      if (typeof window.renderReportFromJson !== "function") {
        throw new Error("renderReportFromJson() not found on page");
      }
      window.renderReportFromJson(payload.data, payload.opts);
    },
    {
      data: arr,
      opts: {
        patientId,
        examDate,
        thresholds: { thin60: 0.3, ratio_max: 1.8, ultra30: 0.15 },
        images,
      },
    }
  );
  console.timeEnd("render:evaluate");

  console.log("▶ Waiting for DOM to settle (logic table) ...");
  await page
    .waitForSelector("#mini tbody tr", { timeout: 8000 })
    .catch(() => {});
  const cardCount = await page
    .$$eval(".card", (els) => els.length)
    .catch(() => 0);
  console.log("  cards rendered:", cardCount);

  console.log("▶ Exporting PDF ...");
  console.time("pdf:write");
  await page.emulateMediaType("screen");
  await page.pdf({
    path: outPath,
    printBackground: true,
    preferCSSPageSize: true, // HTMLの@page（横向きA4）を尊重
  });
  console.timeEnd("pdf:write");

  await browser.close();
  console.log("✔ Done. Saved:", outPath);
}

main().catch((e) => {
  console.error("✗ Error:", e);
  process.exit(1);
});
