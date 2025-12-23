#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
TARGET="$ROOT/backend/.env"

read -r -p "GOOGLE_CLIENT_ID: " CID
read -r -p "GOOGLE_CLIENT_SECRET: " CSEC

python3 - <<INNER
from pathlib import Path
env_path = Path("$TARGET")
lines = {}
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if '=' in line and not line.strip().startswith('#'):
            if '=' in line:
                k,v = line.split('=',1)
                lines[k]=v
lines["GOOGLE_CLIENT_ID"] = "$CID"
lines["GOOGLE_CLIENT_SECRET"] = "$CSEC"
lines["GOOGLE_REDIRECT_URI"] = "http://127.0.0.1:8000/api/auth/gmail/callback"
lines["FRONTEND_BASE_URL"] = "http://localhost:3000"
env_path.write_text('\\n'.join(f"{k}={v}" for k,v in lines.items()) + '\\n')
print(f"Wrote {env_path}")
INNER

echo "OK. Now run: ./run-local.sh"
