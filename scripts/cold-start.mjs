#!/usr/bin/env node
// Cold-start orchestrator for StockRAG.
//
// One command for a fresh clone:
//   1. Verifies prerequisites (Python 3, Node, npm).
//   2. Creates a Python venv at stockrag/backend/.venv and installs requirements.
//   3. Runs `npm install` for the frontend.
//   4. Ensures stockrag/.env exists; prompts for missing API keys interactively.
//   5. Warns if the Chroma vector store is empty (no ingested data).
//   6. Starts the FastAPI backend and the Vite frontend, prints the URL when ready,
//      and tears both down cleanly on Ctrl-C.

import { spawn, spawnSync } from "node:child_process";
import {
  createWriteStream,
  existsSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  unlinkSync,
  writeFileSync,
} from "node:fs";
import { createInterface } from "node:readline/promises";
import { stdin as input, stdout as output, platform } from "node:process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { pipeline } from "node:stream/promises";
import { createHash } from "node:crypto";
import http from "node:http";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const STOCKRAG = join(ROOT, "stockrag");
const BACKEND = join(STOCKRAG, "backend");
const FRONTEND = join(STOCKRAG, "frontend");
const VENV = join(BACKEND, ".venv");
const ENV_FILE = join(STOCKRAG, ".env");
const CHROMA_DIR = join(STOCKRAG, "chroma_db");

const IS_WIN = platform === "win32";
const VENV_BIN = IS_WIN ? join(VENV, "Scripts") : join(VENV, "bin");
const VENV_PYTHON = join(VENV_BIN, IS_WIN ? "python.exe" : "python");
const VENV_PIP = join(VENV_BIN, IS_WIN ? "pip.exe" : "pip");

const BACKEND_PORT = Number(process.env.API_PORT ?? 8000);
const FRONTEND_PORT = Number(process.env.VITE_PORT ?? 5173);

// Public Hugging Face dataset hosting the prebuilt Chroma snapshot. Override
// at runtime with CHROMA_DB_URL=… in the shell or stockrag/.env (set to empty
// string to skip the download and just warn). Resolved inside bootstrapChroma()
// so values from stockrag/.env (loaded by ensureEnvFile) are honored.
const DEFAULT_CHROMA_DB_URL =
  "https://huggingface.co/datasets/KrishPatel0111/stockrag-chroma-db/resolve/main/chroma_db.tar.gz";

const CYAN = "\x1b[36m";
const GREEN = "\x1b[32m";
const YELLOW = "\x1b[33m";
const RED = "\x1b[31m";
const DIM = "\x1b[2m";
const RESET = "\x1b[0m";

const log = (msg) => console.log(`${CYAN}[cold-start]${RESET} ${msg}`);
const warn = (msg) => console.log(`${YELLOW}[cold-start]${RESET} ${msg}`);
const ok = (msg) => console.log(`${GREEN}[cold-start]${RESET} ${msg}`);
const fail = (msg) => console.log(`${RED}[cold-start]${RESET} ${msg}`);

function run(cmd, args, opts = {}) {
  const result = spawnSync(cmd, args, { stdio: "inherit", shell: false, ...opts });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    throw new Error(`${cmd} ${args.join(" ")} exited with code ${result.status}`);
  }
}

function which(cmd) {
  const probe = spawnSync(IS_WIN ? "where" : "which", [cmd], { encoding: "utf8" });
  if (probe.status !== 0) return null;
  return probe.stdout.split(/\r?\n/)[0].trim() || null;
}

function findPython() {
  for (const candidate of ["python3", "python"]) {
    const path = which(candidate);
    if (!path) continue;
    const probe = spawnSync(candidate, ["-c", "import sys; print(sys.version_info[0])"], {
      encoding: "utf8",
    });
    if (probe.status === 0 && probe.stdout.trim() === "3") return candidate;
  }
  return null;
}

function checkPrerequisites() {
  log("Checking prerequisites…");
  const python = findPython();
  if (!python) {
    fail("Python 3 is required but was not found on PATH.");
    process.exit(1);
  }
  if (!which("node")) {
    fail("Node.js is required but was not found on PATH.");
    process.exit(1);
  }
  if (!which("npm")) {
    fail("npm is required but was not found on PATH.");
    process.exit(1);
  }
  ok(`Found ${python}, node, npm.`);
  return python;
}

function setupVenv(python) {
  if (existsSync(VENV_PYTHON)) {
    log("Python venv already exists — reusing.");
  } else {
    log(`Creating Python venv at ${VENV}…`);
    run(python, ["-m", "venv", VENV]);
  }
  log("Upgrading pip and installing backend requirements (this can take a few minutes)…");
  run(VENV_PYTHON, ["-m", "pip", "install", "--upgrade", "pip"]);
  // On Linux, the default PyPI torch wheel pulls ~4 GB of bundled CUDA libs that
  // we don't need — sentence-transformers runs CPU-only here. Pre-install the
  // CPU wheel so requirements.txt resolution is satisfied without GPU torch.
  // Default torch on macOS (CPU/MPS) and Windows (CPU) is already fine.
  if (platform === "linux") {
    log("Installing CPU-only torch (avoids ~4 GB of CUDA libs)…");
    run(VENV_PIP, [
      "install",
      "--upgrade",
      "torch",
      "--index-url",
      "https://download.pytorch.org/whl/cpu",
    ]);
  }
  run(VENV_PIP, ["install", "-r", join(BACKEND, "requirements.txt")]);
  ok("Backend dependencies installed.");
}

function setupFrontend() {
  if (existsSync(join(FRONTEND, "node_modules"))) {
    log("Frontend node_modules present — running `npm install` to verify it's up to date…");
  } else {
    log("Installing frontend dependencies…");
  }
  run(IS_WIN ? "npm.cmd" : "npm", ["install"], { cwd: FRONTEND });
  ok("Frontend dependencies installed.");
}

function parseEnv(text) {
  const out = {};
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    const idx = line.indexOf("=");
    if (idx === -1) continue;
    out[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
  }
  return out;
}

async function ensureEnvFile() {
  let existing = {};
  if (existsSync(ENV_FILE)) {
    existing = parseEnv(readFileSync(ENV_FILE, "utf8"));
    log(`Found existing ${ENV_FILE}.`);
  } else {
    log(`No .env at ${ENV_FILE} — creating a new one.`);
  }

  const required = [
    {
      key: "GEMINI_API_KEY",
      prompt: "Gemini API key (https://aistudio.google.com/apikey)",
      required: true,
    },
    {
      key: "FINNHUB_API_KEY",
      prompt: "Finnhub API key (https://finnhub.io/register) — used for live prices",
      required: false,
    },
  ];

  const missing = required.filter(({ key }) => !(key in existing));
  const interactive = Boolean(input.isTTY);
  if (missing.length && !interactive) {
    fail(
      `stockrag/.env is missing required keys (${missing
        .map((m) => m.key)
        .join(", ")}) and no TTY is attached for prompts.`,
    );
    fail(`Copy stockrag/.env.example to stockrag/.env, fill in the keys, and re-run.`);
    process.exit(1);
  }
  if (missing.length) {
    const rl = createInterface({ input, output });
    try {
      for (const { key, prompt, required: req } of missing) {
        const suffix = req ? "" : " (optional, press Enter to skip)";
        const answer = (await rl.question(`${CYAN}?${RESET} ${prompt}${suffix}: `)).trim();
        if (answer) existing[key] = answer;
        else if (req) {
          fail(`${key} is required.`);
          process.exit(1);
        } else {
          existing[key] = "";
        }
      }
    } finally {
      rl.close();
    }
  }

  const lines = [
    "# Generated by `npm run cold-start`. Edit freely.",
    `GEMINI_API_KEY=${existing.GEMINI_API_KEY ?? ""}`,
    `FINNHUB_API_KEY=${existing.FINNHUB_API_KEY ?? ""}`,
    `API_PORT=${existing.API_PORT ?? BACKEND_PORT}`,
  ];
  // Preserve any other keys the user may have already set.
  for (const [k, v] of Object.entries(existing)) {
    if (["GEMINI_API_KEY", "FINNHUB_API_KEY", "API_PORT"].includes(k)) continue;
    lines.push(`${k}=${v}`);
  }
  writeFileSync(ENV_FILE, lines.join("\n") + "\n");
  ok(`Wrote ${ENV_FILE}.`);

  // Surface .env values to the rest of cold-start so things like CHROMA_DB_URL
  // set in stockrag/.env are honored (shell env still wins — we only fill blanks).
  for (const [k, v] of Object.entries(existing)) {
    if (process.env[k] === undefined && v !== "") process.env[k] = v;
  }
}

function checkChromaData() {
  if (!existsSync(CHROMA_DIR)) {
    mkdirSync(CHROMA_DIR, { recursive: true });
  }
  const entries = readdirSync(CHROMA_DIR).filter((f) => f !== ".gitkeep");
  if (entries.length === 0) {
    warn("Chroma vector store is empty — the API will run but RAG queries will return no results.");
    warn("To bootstrap it, see stockrag/docs/CHROMA_DB_BOOTSTRAP.md.");
  } else {
    ok("Chroma vector store has data.");
  }
}

async function bootstrapChroma() {
  const url =
    process.env.CHROMA_DB_URL !== undefined ? process.env.CHROMA_DB_URL : DEFAULT_CHROMA_DB_URL;
  const shaUrl = process.env.CHROMA_DB_SHA256_URL ?? (url ? `${url}.sha256` : "");

  // Empty CHROMA_DB_URL = explicit opt-out; just warn like the old behavior.
  if (!url) return checkChromaData();

  if (!existsSync(CHROMA_DIR)) mkdirSync(CHROMA_DIR, { recursive: true });
  const existing = readdirSync(CHROMA_DIR).filter((f) => f !== ".gitkeep");
  if (existing.length > 0) {
    ok("Chroma vector store has data.");
    return;
  }

  log(`Downloading Chroma snapshot from ${url}…`);
  const tarPath = join(STOCKRAG, "chroma_db.tar.gz");

  const shaRes = await fetch(shaUrl, { redirect: "follow" });
  if (!shaRes.ok) throw new Error(`fetch ${shaUrl} -> ${shaRes.status}`);
  const expected = (await shaRes.text()).trim().split(/\s+/)[0];

  const tarRes = await fetch(url, { redirect: "follow" });
  if (!tarRes.ok) throw new Error(`fetch ${url} -> ${tarRes.status}`);
  const totalBytes = Number(tarRes.headers.get("content-length") ?? 0);
  if (totalBytes) log(`  ↳ size: ${(totalBytes / 1024 / 1024).toFixed(1)} MB`);

  const hash = createHash("sha256");
  try {
    await pipeline(
      tarRes.body,
      async function* (src) {
        for await (const chunk of src) {
          hash.update(chunk);
          yield chunk;
        }
      },
      createWriteStream(tarPath),
    );
  } catch (err) {
    try { unlinkSync(tarPath); } catch {}
    throw err;
  }

  const actual = hash.digest("hex");
  if (actual !== expected) {
    try { unlinkSync(tarPath); } catch {}
    throw new Error(`SHA256 mismatch — expected ${expected}, got ${actual}`);
  }
  ok("Verified SHA256 OK.");

  run("tar", ["-xzf", tarPath, "-C", STOCKRAG]);
  unlinkSync(tarPath);
  const sizeMb = totalBytes ? `~${(totalBytes / 1024 / 1024).toFixed(0)} MB` : "ready";
  ok(`Chroma vector store ready (${sizeMb}).`);
}

function waitForHttp(port, path = "/", timeoutMs = 60_000) {
  const start = Date.now();
  return new Promise((resolveReady, rejectReady) => {
    const tick = () => {
      const req = http.get({ host: "localhost", port, path, timeout: 1500, family: 4 }, (res) => {
        res.resume();
        if (res.statusCode && res.statusCode < 500) resolveReady();
        else retry();
      });
      req.on("error", retry);
      req.on("timeout", () => {
        req.destroy();
        retry();
      });
    };
    const retry = () => {
      if (Date.now() - start > timeoutMs) {
        rejectReady(new Error(`timed out waiting for http://127.0.0.1:${port}${path}`));
        return;
      }
      setTimeout(tick, 500);
    };
    tick();
  });
}

function startServices() {
  log("Starting backend (uvicorn) and frontend (vite)…");

  // No --reload here: cold-start is a one-shot launcher. With reload on, uvicorn
  // watches the backend cwd which contains .venv/, triggering nonstop restarts
  // as site-packages mtimes settle. For dev iteration, run `python main.py` directly.
  const backend = spawn(
    VENV_PYTHON,
    ["-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", String(BACKEND_PORT)],
    { cwd: BACKEND, stdio: ["ignore", "pipe", "pipe"] },
  );
  backend.stdout.on("data", (b) => process.stdout.write(`${DIM}[backend]${RESET} ${b}`));
  backend.stderr.on("data", (b) => process.stdout.write(`${DIM}[backend]${RESET} ${b}`));

  const frontend = spawn(
    IS_WIN ? "npm.cmd" : "npm",
    ["run", "dev", "--", "--host", "127.0.0.1", "--port", String(FRONTEND_PORT), "--strictPort"],
    { cwd: FRONTEND, stdio: ["ignore", "pipe", "pipe"] },
  );
  frontend.stdout.on("data", (b) => process.stdout.write(`${DIM}[frontend]${RESET} ${b}`));
  frontend.stderr.on("data", (b) => process.stdout.write(`${DIM}[frontend]${RESET} ${b}`));

  let shuttingDown = false;
  const shutdown = (code = 0) => {
    if (shuttingDown) return;
    shuttingDown = true;
    log("Shutting down…");
    for (const proc of [backend, frontend]) {
      if (proc.exitCode === null) proc.kill("SIGINT");
    }
    setTimeout(() => process.exit(code), 1500).unref();
  };

  backend.on("exit", (code) => {
    if (!shuttingDown) fail(`Backend exited unexpectedly (code ${code}).`);
    shutdown(code ?? 1);
  });
  frontend.on("exit", (code) => {
    if (!shuttingDown) fail(`Frontend exited unexpectedly (code ${code}).`);
    shutdown(code ?? 1);
  });
  process.on("SIGINT", () => shutdown(0));
  process.on("SIGTERM", () => shutdown(0));

  return Promise.all([
    waitForHttp(BACKEND_PORT, "/").then(() => ok(`Backend ready on http://localhost:${BACKEND_PORT}`)),
    waitForHttp(FRONTEND_PORT, "/").then(() => ok(`Frontend ready on http://localhost:${FRONTEND_PORT}`)),
  ]);
}

async function main() {
  console.log(`${GREEN}── StockRAG cold start ──${RESET}`);
  const python = checkPrerequisites();
  setupVenv(python);
  setupFrontend();
  await ensureEnvFile();
  await bootstrapChroma();
  await startServices();

  console.log("");
  console.log(`${GREEN}✓ All set — open the app at:${RESET} ${CYAN}http://localhost:${FRONTEND_PORT}${RESET}`);
  console.log(`${DIM}  API:  http://localhost:${BACKEND_PORT}${RESET}`);
  console.log(`${DIM}  Press Ctrl-C to stop both services.${RESET}`);
}

main().catch((err) => {
  fail(err.message ?? String(err));
  process.exit(1);
});
