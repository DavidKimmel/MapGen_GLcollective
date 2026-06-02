"""GeoLine Collective — Cloudflare R2 object storage.

S3-compatible storage that replaces Dropbox for:
  - hosting print files Gelato fetches at order time
  - hosting digital deliverables customers download

Public reads are served via the custom domain bound to the bucket
(R2_PUBLIC_BASE), so an object key maps to a stable, permanent URL:
    {R2_PUBLIC_BASE}/{key}

Unlike the Dropbox access token (which expired every ~4 hours), the S3
API credentials used here do not expire.

Config is read from the project .env:
    R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET
    R2_PUBLIC_BASE  (optional — defaults to the bound custom domain)
"""

from __future__ import annotations

import mimetypes
from functools import lru_cache
from pathlib import Path

import boto3
from botocore.config import Config

PROJECT_DIR = Path(__file__).parent.parent
RENDERS_DIR = PROJECT_DIR / "etsy" / "renders"
_DEFAULT_PUBLIC_BASE = "https://geoline.neodigitalventures.com"


def _load_env() -> dict[str, str]:
    """Parse the project .env into a dict, stripping whitespace/CRLF."""
    env_path = PROJECT_DIR / ".env"
    if not env_path.exists():
        raise FileNotFoundError(f".env not found at {env_path}")
    out: dict[str, str] = {}
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        out[key.strip()] = val.strip()
    return out


@lru_cache(maxsize=1)
def _config() -> dict[str, str]:
    env = _load_env()
    required = ["R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID",
                "R2_SECRET_ACCESS_KEY", "R2_BUCKET"]
    missing = [k for k in required if not env.get(k)]
    if missing:
        raise RuntimeError(f"Missing R2 config in .env: {', '.join(missing)}")
    return {
        "account_id": env["R2_ACCOUNT_ID"],
        "access_key_id": env["R2_ACCESS_KEY_ID"],
        "secret_access_key": env["R2_SECRET_ACCESS_KEY"],
        "bucket": env["R2_BUCKET"],
        "public_base": env.get("R2_PUBLIC_BASE", _DEFAULT_PUBLIC_BASE).rstrip("/"),
    }


@lru_cache(maxsize=1)
def _client():
    cfg = _config()
    endpoint = f"https://{cfg['account_id']}.r2.cloudflarestorage.com"
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=cfg["access_key_id"],
        aws_secret_access_key=cfg["secret_access_key"],
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def public_url(key: str) -> str:
    """Return the permanent public URL for an object key."""
    return f"{_config()['public_base']}/{key.lstrip('/')}"


def upload_file(local_path: str | Path, key: str) -> str:
    """Upload a local file to R2 under `key`; return its public URL."""
    src = Path(local_path)
    if not src.exists():
        raise FileNotFoundError(f"upload source not found: {src}")
    content_type = mimetypes.guess_type(src.name)[0] or "application/octet-stream"
    _client().upload_file(
        str(src),
        _config()["bucket"],
        key.lstrip("/"),
        ExtraArgs={"ContentType": content_type},
    )
    return public_url(key)


def delete_object(key: str) -> None:
    """Delete an object (free operation in R2)."""
    _client().delete_object(Bucket=_config()["bucket"], Key=key.lstrip("/"))


def key_for_render(local_path: str | Path) -> str:
    """Object key for a file under etsy/renders/ — its path relative to that
    directory, POSIX-style. This is the single rule shared by the seeder
    (scripts/r2_seed.sh) and all upload code, so generated URLs resolve."""
    rel = Path(local_path).resolve().relative_to(RENDERS_DIR.resolve())
    return rel.as_posix()


def upload_render(local_path: str | Path) -> str:
    """Upload a file that lives under etsy/renders/ and return its public URL.
    The key is derived from its path relative to etsy/renders/."""
    return upload_file(local_path, key_for_render(local_path))


def render_url(local_path: str | Path) -> str:
    """Public URL a render file maps to, without uploading."""
    return public_url(key_for_render(local_path))
