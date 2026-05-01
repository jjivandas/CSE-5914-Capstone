# Bootstrapping `chroma_db/` for cold-start

`stockrag/chroma_db/` is gitignored (~511 MB raw, ~250 MB gzipped) and rebuilding
it from raw EDGAR data takes hours. To make a fresh clone usable, we host a
prebuilt snapshot on a public Hugging Face dataset and have `npm run cold-start`
pull it down on first run.

- Dataset: <https://huggingface.co/datasets/KrishPatel0111/stockrag-chroma-db>
- Tarball URL (no auth):
  `https://huggingface.co/datasets/KrishPatel0111/stockrag-chroma-db/resolve/main/chroma_db.tar.gz`
- Checksum URL: same path with `.sha256` appended.

## How cold-start uses it

`scripts/cold-start.mjs` runs `bootstrapChroma()`:

1. If `stockrag/chroma_db/` already has data, it's a no-op.
2. Otherwise it streams the tarball, verifies the SHA256 mid-stream against the
   `.sha256` file, runs `tar -xzf` into `stockrag/`, then deletes the tarball.

A failed checksum or download leaves no partial files behind.

## Re-publishing a fresh snapshot

Run on the machine that has a populated `stockrag/chroma_db/` (Krish's box,
typically). You need `huggingface_hub` installed and `hf auth login` done with a
write token.

```bash
# from repo root
tar -czf chroma_db.tar.gz -C stockrag chroma_db
shasum -a 256 chroma_db.tar.gz | tee chroma_db.tar.gz.sha256

hf upload KrishPatel0111/stockrag-chroma-db chroma_db.tar.gz       --repo-type dataset
hf upload KrishPatel0111/stockrag-chroma-db chroma_db.tar.gz.sha256 --repo-type dataset

rm chroma_db.tar.gz chroma_db.tar.gz.sha256
```

The dataset URL stays the same, so anyone running cold-start after this picks
up the new snapshot automatically. Re-run after every re-ingest.

Verify the upload from a clean shell (no auth):

```bash
URL=https://huggingface.co/datasets/KrishPatel0111/stockrag-chroma-db/resolve/main/chroma_db.tar.gz
curl -sL -o /tmp/check.tar.gz "$URL"
shasum -a 256 /tmp/check.tar.gz   # must match the uploaded .sha256
```

## Overrides

Set in the shell or `stockrag/.env`:

| Var                      | Effect                                                                       |
| ------------------------ | ---------------------------------------------------------------------------- |
| `CHROMA_DB_URL`          | Use a different tarball URL (e.g. a personal HF dataset for a custom index). |
| `CHROMA_DB_SHA256_URL`   | Override the checksum URL (defaults to `${CHROMA_DB_URL}.sha256`).           |
| `CHROMA_DB_URL=` (empty) | Skip the download entirely; just warn if the store is empty.                 |

## Watch out for

- Schema changes (different embedding model, collection names, sentence-transformers version) make the snapshot incompatible — re-publish with a fresh upload. The URL is unversioned, so the old snapshot is overwritten.
- Dataset visibility must stay **public** for unauthenticated cold-start to work.
- HF outages or rate limits will fail cold-start with a clear error; re-run, or set `CHROMA_DB_URL=` to skip and start the API empty.
- Tarball size is bounded by HF's per-file limits (effectively unbounded via LFS), but bigger snapshots = slower cold-start.
