"""Call protected admin endpoints with X-Admin-API-Key.

Examples:
  python scripts/admin_api.py get /api/parsed-documents
  python scripts/admin_api.py post-json /api/parsed-documents payload.json
  python scripts/admin_api.py post-json /api/parsed-documents/15/embed payload.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("method", choices=["get", "post-json", "patch-json"])
    parser.add_argument("path", help="API path, e.g. /api/parsed-documents")
    parser.add_argument("payload", nargs="?", help="JSON payload file for post-json/patch-json")
    parser.add_argument("--base-url", default=os.getenv("ADMIN_API_BASE_URL", "https://medical-rag-api-snes.onrender.com"))
    args = parser.parse_args()

    api_key = os.getenv("ADMIN_API_KEY")
    if not api_key:
        print("ADMIN_API_KEY is required in the environment.", file=sys.stderr)
        return 2

    url = f"{args.base_url.rstrip('/')}/{args.path.lstrip('/')}"
    headers = {"X-Admin-API-Key": api_key}
    if args.method == "get":
        response = requests.get(url, headers=headers, timeout=120)
    else:
        if not args.payload:
            print("A JSON payload file is required.", file=sys.stderr)
            return 2
        payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
        request = requests.post if args.method == "post-json" else requests.patch
        response = request(url, headers=headers, json=payload, timeout=180)

    print(response.text)
    return 0 if response.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
