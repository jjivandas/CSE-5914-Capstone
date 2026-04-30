# Bootstrapping `chroma_db/` for cold-start

## Why cold-start skips this
- Raw SEC data is ~27 GB, gitignored, no fetch script in repo.
- Parse + embed takes hours.
- `chroma_db/` is gitignored too, so a fresh clone has nothing to serve.
- Fix: ship a pre-built snapshot as a GitHub Release asset, have cold-start pull it.

## Publish a snapshot (run on the machine with data)

```bash
# 1. Package
tar -czf chroma_db.tar.gz -C stockrag chroma_db
shasum -a 256 chroma_db.tar.gz | tee chroma_db.tar.gz.sha256

# 2. Release (tag = date)
TAG=chroma-db-v$(date +%Y%m%d)
gh release create "$TAG" chroma_db.tar.gz chroma_db.tar.gz.sha256 \
  --title "Chroma DB snapshot $TAG" --notes "SEC fact index $(date -u +%F)"
```

- Tarball must stay under 2 GB (GitHub asset cap). Switch to `--zstd` if close.
- Re-run on every re-ingest; bump the date tag.

## Wire into cold-start

Replace `checkChromaData()` in `scripts/cold-start.mjs` with the snippet below; swap the call in `main()` to `await bootstrapChroma()`.

```js
import { unlinkSync, createWriteStream } from "node:fs";
import { pipeline } from "node:stream/promises";
import { createHash } from "node:crypto";

const RELEASE_REPO = "OWNER/REPO";  // fill in
const RELEASE_TAG = process.env.CHROMA_DB_RELEASE_TAG ?? "latest";

async function fetchAsset(name) {
  const base = `https://github.com/${RELEASE_REPO}/releases`;
  const url = RELEASE_TAG === "latest"
    ? `${base}/latest/download/${name}`
    : `${base}/download/${RELEASE_TAG}/${name}`;
  const res = await fetch(url, { redirect: "follow" });
  if (!res.ok) throw new Error(`fetch ${url} -> ${res.status}`);
  return res;
}

async function bootstrapChroma() {
  if (!existsSync(CHROMA_DIR)) mkdirSync(CHROMA_DIR, { recursive: true });
  if (readdirSync(CHROMA_DIR).filter((f) => f !== ".gitkeep").length > 0) {
    ok("Chroma vector store has data.");
    return;
  }
  log(`Downloading chroma snapshot (${RELEASE_TAG})…`);
  const tarPath = join(STOCKRAG, "chroma_db.tar.gz");
  const [tarRes, sumRes] = await Promise.all([
    fetchAsset("chroma_db.tar.gz"),
    fetchAsset("chroma_db.tar.gz.sha256"),
  ]);
  const expected = (await sumRes.text()).trim().split(/\s+/)[0];
  const hash = createHash("sha256");
  await pipeline(tarRes.body, async function* (src) {
    for await (const c of src) { hash.update(c); yield c; }
  }, createWriteStream(tarPath));
  if (hash.digest("hex") !== expected) throw new Error("checksum mismatch");
  run("tar", ["-xzf", tarPath, "-C", STOCKRAG]);
  unlinkSync(tarPath);
  ok("Chroma vector store ready.");
}
```

## Usage

- Default: `npm run cold-start` pulls `latest`.
- Pin a tag: `CHROMA_DB_RELEASE_TAG=chroma-db-v20260301 npm run cold-start`.
- Force re-fetch: `rm -rf stockrag/chroma_db && npm run cold-start`.

## Watch out for

- Public repo = public asset. Fine for SEC filings, not for anything private.
- Schema change (embedding model, collection names) → snapshot incompatible. Cut a new tag.
- >2 GB → split assets or move to S3/GCS.
