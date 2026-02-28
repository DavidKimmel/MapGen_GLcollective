"""GeoLine Collective — Etsy OAuth2 PKCE Authentication.

Implements the Etsy Open API v3 OAuth2 PKCE flow:
  1. Generate code_verifier + code_challenge
  2. Open browser for user consent
  3. Catch callback with authorization code
  4. Exchange for access + refresh tokens
  5. Store tokens in .credentials.json

Usage:
    python -m etsy.auth                     # Run OAuth flow
    python -m etsy.auth --check             # Check if authenticated
    python -m etsy.auth --refresh           # Force token refresh
"""

from __future__ import annotations

import base64
import hashlib
import http.server
import json
import os
import secrets
import sys
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), ".credentials.json")

ETSY_AUTH_URL = "https://www.etsy.com/oauth/connect"
ETSY_TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"
ETSY_API_BASE = "https://openapi.etsy.com/v3"

REDIRECT_HOST = "localhost"
REDIRECT_PORT = 3000
REDIRECT_URI = f"http://{REDIRECT_HOST}:{REDIRECT_PORT}/callback"

# Scopes we need for listing management
SCOPES = [
    "listings_r",
    "listings_w",
    "shops_r",
    "shops_w",
]


# ---------------------------------------------------------------------------
# PKCE helpers
# ---------------------------------------------------------------------------

def _generate_code_verifier() -> str:
    """Generate a random 43-128 character code verifier."""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode("ascii")


def _generate_code_challenge(verifier: str) -> str:
    """SHA256 hash the verifier and base64url-encode it."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


# ---------------------------------------------------------------------------
# Credential storage
# ---------------------------------------------------------------------------

def _load_credentials() -> dict | None:
    """Load stored credentials from disk."""
    if not os.path.exists(CREDENTIALS_FILE):
        return None
    try:
        with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _save_credentials(creds: dict) -> None:
    """Save credentials to disk."""
    with open(CREDENTIALS_FILE, "w", encoding="utf-8") as f:
        json.dump(creds, f, indent=2)
    print(f"Credentials saved to {CREDENTIALS_FILE}")


def get_client_id() -> str:
    """Get the API key (client_id) from credentials or environment."""
    creds = _load_credentials()
    if creds and creds.get("client_id"):
        return creds["client_id"]
    env_key = os.environ.get("ETSY_API_KEY")
    if env_key:
        return env_key
    raise ValueError(
        "No Etsy API key found. Run 'python -m etsy.auth' to authenticate, "
        "or set ETSY_API_KEY environment variable."
    )


def get_access_token() -> str:
    """Get a valid access token, refreshing if needed."""
    creds = _load_credentials()
    if not creds:
        raise ValueError("Not authenticated. Run 'python -m etsy.auth' first.")

    # Check if token has expired
    expires_at = creds.get("expires_at", 0)
    if time.time() < expires_at - 60:  # 60s buffer
        return creds["access_token"]

    # Try to refresh
    if creds.get("refresh_token"):
        print("Access token expired, refreshing...")
        return refresh_token(creds)

    raise ValueError("Token expired and no refresh token. Run 'python -m etsy.auth' again.")


def refresh_token(creds: dict | None = None) -> str:
    """Refresh the access token using the refresh token."""
    if creds is None:
        creds = _load_credentials()
    if not creds or not creds.get("refresh_token"):
        raise ValueError("No refresh token available.")

    resp = requests.post(ETSY_TOKEN_URL, json={
        "grant_type": "refresh_token",
        "client_id": creds["client_id"],
        "refresh_token": creds["refresh_token"],
    })

    if resp.status_code != 200:
        raise ValueError(f"Token refresh failed ({resp.status_code}): {resp.text}")

    data = resp.json()
    creds["access_token"] = data["access_token"]
    creds["refresh_token"] = data["refresh_token"]
    creds["expires_at"] = time.time() + data.get("expires_in", 3600)
    _save_credentials(creds)
    print("Token refreshed successfully.")
    return creds["access_token"]


# ---------------------------------------------------------------------------
# OAuth2 PKCE flow
# ---------------------------------------------------------------------------

def authenticate(client_id: str, client_secret: str) -> dict:
    """Run the full OAuth2 PKCE flow.

    Opens a browser for user consent, catches the callback,
    exchanges the code for tokens, and saves credentials.
    """
    code_verifier = _generate_code_verifier()
    code_challenge = _generate_code_challenge(code_verifier)
    state = secrets.token_urlsafe(16)

    # Build authorization URL
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": " ".join(SCOPES),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    auth_url = f"{ETSY_AUTH_URL}?{urllib.parse.urlencode(params)}"

    # Start local server to catch callback
    auth_code = None
    received_state = None
    server_ready = threading.Event()

    class CallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal auth_code, received_state
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/callback":
                qs = urllib.parse.parse_qs(parsed.query)
                auth_code = qs.get("code", [None])[0]
                received_state = qs.get("state", [None])[0]

                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(
                    b"<html><body><h2>Authentication successful!</h2>"
                    b"<p>You can close this tab and return to the terminal.</p>"
                    b"</body></html>"
                )
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format, *args):
            pass  # Suppress server logging

    server = http.server.HTTPServer((REDIRECT_HOST, REDIRECT_PORT), CallbackHandler)
    server.timeout = 120  # 2 minute timeout

    def run_server():
        server_ready.set()
        server.handle_request()  # Handle exactly one request

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    server_ready.wait()

    # Open browser
    print(f"\nOpening browser for Etsy authentication...")
    print(f"If the browser doesn't open, visit this URL manually:\n")
    print(f"  {auth_url}\n")
    webbrowser.open(auth_url)

    # Wait for callback
    print("Waiting for authentication callback...")
    thread.join(timeout=120)
    server.server_close()

    if not auth_code:
        raise ValueError("Authentication failed — no authorization code received.")

    if received_state != state:
        raise ValueError("Authentication failed — state mismatch (possible CSRF).")

    print("Authorization code received. Exchanging for tokens...")

    # Exchange code for tokens
    resp = requests.post(ETSY_TOKEN_URL, json={
        "grant_type": "authorization_code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "code": auth_code,
        "code_verifier": code_verifier,
    })

    if resp.status_code != 200:
        raise ValueError(f"Token exchange failed ({resp.status_code}): {resp.text}")

    data = resp.json()

    creds = {
        "client_id": client_id,
        "client_secret": client_secret,
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "expires_at": time.time() + data.get("expires_in", 3600),
        "scope": " ".join(SCOPES),
    }
    _save_credentials(creds)

    print("\nAuthentication successful!")
    print(f"  Access token expires in: {data.get('expires_in', 3600)}s")
    print(f"  Credentials saved to: {CREDENTIALS_FILE}")

    return creds


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Etsy OAuth2 authentication")
    parser.add_argument("--check", action="store_true", help="Check authentication status")
    parser.add_argument("--refresh", action="store_true", help="Force token refresh")
    parser.add_argument("--client-id", default=None, help="Etsy API key (keystring)")
    parser.add_argument("--client-secret", default=None, help="Etsy shared secret")
    args = parser.parse_args()

    if args.check:
        creds = _load_credentials()
        if not creds:
            print("Not authenticated. Run 'python -m etsy.auth' to authenticate.")
            sys.exit(1)
        expires_in = creds.get("expires_at", 0) - time.time()
        print(f"Authenticated as: {creds.get('client_id', 'unknown')}")
        print(f"Token expires in: {max(0, int(expires_in))}s")
        print(f"Scopes: {creds.get('scope', 'unknown')}")
        sys.exit(0)

    if args.refresh:
        try:
            refresh_token()
            print("Token refreshed.")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
        sys.exit(0)

    # Full authentication flow
    client_id = args.client_id or os.environ.get("ETSY_API_KEY")
    client_secret = args.client_secret or os.environ.get("ETSY_API_SECRET")

    if not client_id:
        client_id = input("Enter your Etsy API Key (keystring): ").strip()
    if not client_secret:
        client_secret = input("Enter your Etsy Shared Secret: ").strip()

    if not client_id or not client_secret:
        print("Error: Both API key and shared secret are required.")
        sys.exit(1)

    try:
        authenticate(client_id, client_secret)
    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
