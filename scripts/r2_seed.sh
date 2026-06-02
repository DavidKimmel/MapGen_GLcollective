#!/usr/bin/env bash
# Seed GeoLine deliverables (print PNGs + delivery PDFs) into the R2 bucket.
#
# Object key = path relative to etsy/renders/ (the same rule r2_storage.py
# uses), so URLs the code generates always resolve. Mockup JPGs are skipped
# on purpose (they live on Etsy as listing images, never fetched by URL).
#
# Resumable: rclone skips files already present with a matching size.
#
# Usage:  bash scripts/r2_seed.sh            # full seed / resume
#         bash scripts/r2_seed.sh --dry-run  # show what would transfer
set -euo pipefail

cd "$(dirname "$0")/.."

ACCT=$(grep '^R2_ACCOUNT_ID=' .env | cut -d= -f2- | tr -d '\r ')
AKEY=$(grep '^R2_ACCESS_KEY_ID=' .env | cut -d= -f2- | tr -d '\r ')
SKEY=$(grep '^R2_SECRET_ACCESS_KEY=' .env | cut -d= -f2- | tr -d '\r ')
BUCKET=$(grep '^R2_BUCKET=' .env | cut -d= -f2- | tr -d '\r ')

export RCLONE_CONFIG_R2_TYPE=s3
export RCLONE_CONFIG_R2_PROVIDER=Cloudflare
export RCLONE_CONFIG_R2_ACCESS_KEY_ID="$AKEY"
export RCLONE_CONFIG_R2_SECRET_ACCESS_KEY="$SKEY"
export RCLONE_CONFIG_R2_ENDPOINT="https://${ACCT}.r2.cloudflarestorage.com"
export RCLONE_CONFIG_R2_REGION=auto

RCLONE="/c/Users/kimme/AppData/Local/Microsoft/WinGet/Packages/Rclone.Rclone_Microsoft.Winget.Source_8wekyb3d8bbwe/rclone-v1.73.3-windows-amd64/rclone.exe"

"$RCLONE" copy etsy/renders "r2:${BUCKET}" \
  --include "**.png" --include "**.pdf" \
  --transfers 12 --checkers 24 \
  --s3-no-check-bucket \
  --log-file r2_seed.log --log-level INFO \
  --stats 30s --stats-one-line \
  "$@"
