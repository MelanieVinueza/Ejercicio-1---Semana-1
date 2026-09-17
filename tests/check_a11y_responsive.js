// Accesibilidad (WCAG 2.1 AA) y adaptabilidad responsive del sitio estático.
//
// Levanta un pequeño servidor local, carga la página en viewports de
// móvil/tablet/escritorio y ejecuta:
//  1. axe-core con las reglas WCAG 2.1 A/AA (mismo estándar que pa11y).
//  2. Comprobaciones responsive: meta viewport, navegación visible y
//     ausencia de desbordamiento horizontal.
//
// Uso:
//   node tests/check_a11y_responsive.js
//
// Requiere las dependencias declaradas en package.json:
//   playwright-core (usa el Chrome/Edge instalado en el sistema, canal "chrome")
//   axe-core

"use strict";

const http = require("http");
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright-core");
const axeSource = require("axe-core").source;

const ROOT = path.resolve(__dirname, "..");
const HOST = "127.0.0.1";
const PORT = 8123;

const VIEWPORTS = [
  { name: "mobile", width: 375, height: 667 },
  { name: "tablet", width: 768, height: 800 },
  { name: "desktop", width: 1280, height: 800 },
];

// Reglas de axe-core equivalentes a la norma WCAG 2.1 nivel A/AA.
const WCAG_AA_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

const MIME_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".webp": "image/webp",
  ".ico": "image/x-icon",
  ".json": "application/json",
  ".txt": "text/plain; charset=utf-8",
};

// http.server mínimo para servir el sitio localmente sin dependencias extra.
function startServer() {
  return new Promise((resolve, reject) => {
    const server = http.createServer((req, res) => {
      try {
        const urlPath = decodeURIComponent(
          new URL(req.url, `http://${HOST}:${PORT}`).pathname
        );
        let filePath = path.resolve(ROOT, urlPath === "/" ? "index.html" : urlPath);
        if (!filePath.startsWith(ROOT)) {
          res.writeHead(403);
          res.end("Forbidden");
          return;
        }
        const stat = fs.statSync(filePath);
        if (stat.isDirectory()) filePath = path.join(filePath, "index.html");
        const ext = path.extname(filePath).toLowerCase();
        res.writeHead(200, {
          "Content-Type": MIME_TYPES[ext] || "application/octet-stream",
        });
        fs.createReadStream(filePath).pipe(res);
      } catch {
        res.writeHead(404);
        res.end("Not found");
      }
    });
    server.once("error", reject);
    server.listen(PORT, HOST, () => resolve(server));
  });
}

function launchBrowser() {
  // Usa el Chrome o Edge del sistema; en los runners de GitHub Actions
  // siempre hay Chrome disponible. Como alternativa admite CHROME_PATH.
  const channels = ["chrome", "msedge"];
  const candidates = [
    process.env.CHROME_PATH,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  ].filter(Boolean);

  return (async () => {
    for (const channel of channels) {
      try {
        return await chromium.launch({ channel });
      } catch {
        // Intenta el siguiente canal.
      }
    }
    for (const executablePath of candidates) {
      if (fs.existsSync(executablePath)) {
        try {
          return await chromium.launch({ executablePath });
        } catch {
          // Intenta el siguiente candidato.
        }
      }
    }
    throw new Error(
      "No se pudo iniciar Chromium/Chrome. Configura CHROME_PATH con la ruta al navegador."
    );
  })();
}

async function checkViewport(browser, viewport) {
  const pageVP = await browser.newPage();
  const failures = [];

  try {
    await pageVP.setViewportSize({ width: viewport.width, height: viewport.height });
    await pageVP.goto(`http://${HOST}:${PORT}/`, { waitUntil: "networkidle" });

    // ---- Responsive / adaptabilidad ----
    const layout = await pageVP.evaluate(() => {
      const doc = document.documentElement;
      return {
        innerWidth: window.innerWidth,
        scrollWidth: doc.scrollWidth,
        hasViewportMeta: Boolean(document.querySelector('meta[name="viewport"]')),
        navLinkCount: document.querySelectorAll("nav a").length,
        fontSize: getComputedStyle(document.body).fontSize,
      };
    });

    if (!layout.hasViewportMeta) {
      failures.push(`${viewport.name}: falta la meta viewport para diseño responsive`);
    }
    if (layout.navLinkCount === 0) {
      failures.push(`${viewport.name}: no hay enlaces de navegación`);
    }
    if (layout.scrollWidth - layout.innerWidth > 1) {
      failures.push(
        `${viewport.name}: desbordamiento horizontal de ` +
          `${layout.scrollWidth - layout.innerWidth}px ` +
          `(scrollWidth=${layout.scrollWidth}, innerWidth=${layout.innerWidth})`
      );
    }

    // ---- Accesibilidad WCAG 2.1 AA (axe-core) ----
    await pageVP.addScriptTag({ content: axeSource });
    const axeResults = await pageVP.evaluate(async (tags) => {
      return await axe.run(document, {
        runOnly: { type: "tag", values: tags },
      });
    }, WCAG_AA_TAGS);

    for (const violation of axeResults.violations) {
      const nodes = violation.nodes
        .map((node) => node.target.join(" "))
        .join(", ");
      failures.push(
        `${viewport.name} [${violation.impact}] ${violation.id}: ` +
          `${violation.help} -> ${nodes}`
      );
    }
  } finally {
    await pageVP.close();
  }

  return { viewport: viewport.name, failures };
}

(async () => {
  const server = await startServer();
  let browser;
  try {
    browser = await launchBrowser();
    const totalFailures = [];

    for (const viewport of VIEWPORTS) {
      const { viewport: name, failures } = await checkViewport(browser, viewport);
      if (failures.length > 0) {
        console.error(`\n[${name}] ${failures.length} problema(s):`);
        failures.forEach((failure) => console.error(`  - ${failure}`));
        totalFailures.push(...failures);
      } else {
        console.log(`[${name}] OK: WCAG 2.1 AA y responsive correctos (${viewport.width}x${viewport.height})`);
      }
    }

    if (totalFailures.length > 0) {
      console.error(`\nTotal de problemas encontrados: ${totalFailures.length}`);
      process.exitCode = 1;
    } else {
      console.log("\nOK: accesibilidad WCAG 2.1 AA y responsive en mobile, tablet y desktop.");
    }
  } catch (err) {
    console.error(err);
    process.exitCode = 1;
  } finally {
    if (browser) await browser.close();
    server.close();
  }
})();