# Assistant Email IA 📧🤖

## 🎯 Fonctionnalités

### ✅ Implémenté
- **Backend FastAPI séparé** : API REST moderne et modulaire sur le port 8000
- **Chat IA avec OpenAI GPT-4** (via clé Emergent universelle)
- **Deux modes de chat** :
  - 📨 **Mode Actions email** : L'IA peut déclencher des actions (brouillon, recherche, fichiers attendus)
  - 💬 **Mode Discussion** : Discussion pure avec l'IA sans actions
- **Frontend Next.js** moderne avec :
  - Interface dark mode élégante
  - Animations Framer Motion
  - Composants shadcn/ui
  - Pages : Assistant, Paramètres, Fichiers attendus
- **Architecture OAuth2 complète** :
  - Gmail (Google OAuth)
  - Microsoft Outlook (Azure OAuth)
- **Gestion des signatures** :
  - Créer, modifier, supprimer des signatures par compte
  - Signature par défaut par compte
  - Application automatique lors de l'envoi
- **Fichiers attendus** :
  - Créer des fichiers à surveiller (factures, contrats, devis)
  - Scanner les emails pour détecter leur réception
  - Statuts : En attente, Reçu, Relancé
- **Envoi d'emails** via Gmail API et Microsoft Graph
- **Recherche d'emails** via Gmail API et Microsoft Graph
- **Base de données MongoDB** pour :
  - Comptes connectés
  - Signatures
  - Fichiers attendus
  - Historique de chat

## 🔧 Configuration OAuth2

### ⚠️ IMPORTANT : Avant de tester l'application

Vous devez configurer les credentials OAuth pour Gmail et Microsoft dans le fichier `/app/.env`.

### 1. Google Cloud Console (Gmail)

1. Allez sur https://console.cloud.google.com/
2. Créez un nouveau projet (ex: "Assistant Email IA")
3. Activez "Gmail API" dans "APIs & Services"
4. Allez dans "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
5. Type d'application : "Web application"
6. Authorized redirect URIs : 
   - `http://localhost:3000/api/auth/gmail/callback`
   - (prod SaaS) `https://YOUR_DOMAIN/api/auth/gmail/callback`
7. Récupérez **Client ID** et **Client Secret**

### 2. Azure Portal (Microsoft / Outlook)

1. Allez sur https://portal.azure.com/
2. "App registrations" → "New registration"
3. Nom : "Assistant Email IA"
4. Redirect URI (Web) : 
   - `http://localhost:3000/api/auth/microsoft/callback`
5. Dans "Certificates & secrets" → créez un "Client secret"
6. Dans "API permissions" → ajoutez "Microsoft Graph" :
   - Mail.ReadWrite
   - Mail.Send
   - User.Read
7. Récupérez :
   - **Application (client) ID**
   - **Client Secret**
   - **Directory (tenant) ID**

### 3. Configurez le fichier .env

Éditez `/app/.env` et remplacez les placeholders :

```bash
# Google OAuth
GOOGLE_CLIENT_ID=votre_google_client_id_ici
GOOGLE_CLIENT_SECRET=votre_google_client_secret_ici

# Microsoft OAuth
MICROSOFT_CLIENT_ID=votre_microsoft_client_id_ici
MICROSOFT_CLIENT_SECRET=votre_microsoft_client_secret_ici
MICROSOFT_TENANT_ID=common  # ou votre tenant ID spécifique
```

### 4. Redémarrez le backend

```bash
sudo supervisorctl restart fastapi
```

Pour Google OAuth : copiez l'URL de `GOOGLE_REDIRECT_URI.txt` dans Google Cloud > Authorized redirect URIs.

## 🚀 Démarrage local rapide

```bash
# Backend (depuis la racine)
backend/.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000

# Frontend (depuis la racine)
corepack yarn dev --port 3000
```

Tests rapides :
- Vérifier la redirection OAuth Gmail : `curl -I http://127.0.0.1:8000/api/auth/gmail/start` (302 attendu si credentials valides, 500 JSON explicite sinon).
- Debug credentials : `curl http://127.0.0.1:8000/api/auth/gmail/debug`
- Comptes après connexion : `curl http://127.0.0.1:8000/api/accounts`

Google Cloud (Authorized redirect URIs) :
- `http://127.0.0.1:8000/api/auth/gmail/callback`
- (prod) `https://YOUR_DOMAIN/api/auth/gmail/callback`

## 🚀 Utilisation

### 1. Connecter un compte email

1. Ouvrez l'application : http://localhost:3000
2. Allez dans **Paramètres**
3. Cliquez sur "Connecter Gmail" ou "Connecter Outlook"
4. Authentifiez-vous avec votre compte
5. Autorisez l'application à accéder à vos emails

### 2. Créer des signatures

1. Dans **Paramètres** → Section "Signatures"
2. Cliquez sur "Ajouter"
3. Choisissez le compte, donnez un nom et le contenu
4. Cochez "Signature par défaut" si nécessaire

### 3. Utiliser l'assistant

#### Mode Actions email 📨
- "Écris un email à john@example.com pour lui dire bonjour"
- "Recherche tous les emails de Marie reçus cette semaine"
- "Note que j'attends la facture Distram de novembre 2025"

#### Mode Discussion 💬
- "Comment devrais-je formuler cette demande ?"
- "Aide-moi à reformuler cet email"
- "Donne-moi des idées pour répondre à ce client"

### 4. Fichiers attendus

1. Allez dans **Fichiers attendus**
2. Cliquez sur "Ajouter"
3. Renseignez :
   - Titre (ex: "Facture Distram novembre 2025")
   - Contact (ex: "Distram")
   - Type (facture, contrat, devis)
   - Date limite
4. Cliquez sur "Scanner mes emails" pour chercher automatiquement

## 🏗️ Architecture

```
/app/
├── backend/                    # Backend FastAPI (Python)
│   ├── main.py                # Endpoints API
│   ├── database.py            # MongoDB
│   ├── ai_service.py          # OpenAI GPT-4
│   ├── oauth_gmail.py         # OAuth Google
│   ├── oauth_microsoft.py     # OAuth Microsoft
│   └── email_service.py       # Envoi/recherche emails
├── app/                       # Frontend Next.js
│   ├── page.js               # Page principale (chat)
│   ├── parametres/page.js    # Page paramètres
│   └── fichiers-attendus/page.js  # Page fichiers attendus
└── .env                       # Variables d'environnement
```

## 📡 Endpoints API

### OAuth
- `GET /api/auth/gmail/start` - Démarre OAuth Gmail
- `GET /api/auth/gmail/callback` - Callback OAuth Gmail
- `GET /api/auth/microsoft/start` - Démarre OAuth Microsoft
- `GET /api/auth/microsoft/callback` - Callback OAuth Microsoft

### Chat / IA
- `POST /api/chat` - Envoie un message à l'IA
  ```json
  {
    "message": "Écris un email...",
    "mode": "actions" | "discussion"
  }
  ```

### Email
- `POST /api/email/send` - Envoie un email
- `POST /api/email/search` - Recherche des emails

### Comptes
- `GET /api/accounts` - Liste des comptes connectés
- `DELETE /api/accounts/{id}` - Supprime un compte

### Signatures
- `GET /api/signatures` - Liste des signatures
- `POST /api/signatures` - Crée une signature
- `PUT /api/signatures/{id}` - Modifie une signature
- `DELETE /api/signatures/{id}` - Supprime une signature

### Fichiers attendus
- `GET /api/expected-files` - Liste des fichiers attendus
- `POST /api/expected-files` - Crée un fichier attendu
- `POST /api/expected-files/scan` - Scanne les emails
- `DELETE /api/expected-files/{id}` - Supprime un fichier

## 🔑 Variables d'environnement

```bash
# MongoDB (déjà configuré)
MONGO_URL=mongodb://localhost:27017/assistant_email_ia

# Next.js (déjà configuré)
NEXT_PUBLIC_BASE_URL=http://localhost:3000

# OpenAI (déjà configuré avec clé Emergent)
EMERGENT_LLM_KEY=sk-emergent-...

# Google OAuth (À CONFIGURER)
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:3000/api/auth/gmail/callback

# Microsoft OAuth (À CONFIGURER)
MICROSOFT_CLIENT_ID=your_microsoft_client_id_here
MICROSOFT_CLIENT_SECRET=your_microsoft_client_secret_here
MICROSOFT_TENANT_ID=common
MICROSOFT_REDIRECT_URI=http://localhost:3000/api/auth/microsoft/callback

# Backend
BACKEND_URL=http://localhost:8000
```

## 🐛 Dépannage

### Le backend ne démarre pas
```bash
# Vérifier les logs
tail -f /var/log/supervisor/fastapi.out.log

# Redémarrer
sudo supervisorctl restart fastapi
```

### Erreur OAuth
- Vérifiez que les redirect URIs sont bien configurés dans Google Cloud Console et Azure Portal
- Vérifiez que les credentials dans `.env` sont corrects
- Redémarrez le backend après modification du `.env`

### Emails non envoyés
- Vérifiez que le compte est bien connecté dans Paramètres
- Vérifiez que les scopes OAuth sont corrects
- Consultez les logs du backend

## 📝 Notes techniques

- **Hot reload** : Le frontend Next.js se recharge automatiquement
- **Tokens OAuth** : Stockés en MongoDB, automatiquement rafraîchis
- **Sécurité** : Les tokens ne sont jamais exposés au frontend
- **IA** : Utilise GPT-4o via la clé universelle Emergent
- **Base de données** : MongoDB local sur le port 27017

## 🎉 Prochaines étapes suggérées

1. ✅ Configurer les credentials OAuth
2. ✅ Connecter vos comptes email
3. ✅ Créer des signatures
4. ✅ Tester l'envoi d'emails
5. ✅ Tester la recherche d'emails
6. ✅ Créer des fichiers attendus et scanner

---

**Bon usage de votre Assistant Email IA ! 🚀**
