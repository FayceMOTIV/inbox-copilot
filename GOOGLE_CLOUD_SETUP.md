# Google OAuth Setup (Gmail)

Use these exact settings in Google Cloud Console → Credentials → Create OAuth client ID → Web application.

## Fields
- Name: Inbox Copilot (or any)
- Authorized redirect URI:
  - `http://127.0.0.1:8000/api/auth/gmail/callback`
  - (prod) `https://YOUR_DOMAIN/api/auth/gmail/callback`
- Authorized origins:
  - `http://localhost:3000`
  - (prod) `https://YOUR_DOMAIN`

## Where to find keys
- After creation, copy **Client ID** and **Client Secret** shown in the OAuth client details page.

## Paste into backend/.env (or run ./set-google-env.sh)
```
GOOGLE_CLIENT_ID=PASTE_CLIENT_ID_HERE
GOOGLE_CLIENT_SECRET=PASTE_CLIENT_SECRET_HERE
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/api/auth/gmail/callback
FRONTEND_BASE_URL=http://localhost:3000
```
