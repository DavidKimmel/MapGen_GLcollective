"""DEPRECATED — superseded by scripts/r2_seed.sh (Cloudflare R2 migration, 2026-06).

Blueprint print files are no longer uploaded to Dropbox. All deliverables (print
PNGs + delivery PDFs under etsy/renders/) are seeded to the R2 bucket by:

    bash scripts/r2_seed.sh          # full seed / resume (idempotent)

The object key is each file's path relative to etsy/renders/ — the same rule
etsy/r2_storage.py uses — so URLs from the CSV/PDF/manifest generators resolve.
This stub remains only so old commands fail loudly with guidance instead of
hitting a retired Dropbox token.
"""
import sys

_MSG = (
    "DEPRECATED: this script no longer uploads to Dropbox.\n"
    "Seed deliverables to Cloudflare R2 with:\n"
    "    bash scripts/r2_seed.sh\n"
    "(re-runnable; only changed files transfer). See etsy/r2_storage.py."
)

if __name__ == "__main__":
    print(_MSG)
    sys.exit(1)
