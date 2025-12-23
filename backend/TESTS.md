# Tests Backend - Inbox Copilot

## Prérequis
```bash
# Démarrer MongoDB (si pas déjà)
mongod --dbpath /data/db

# Démarrer le backend
cd backend
uvicorn main:app --reload --port 8000
```

## Tests API (curl)

### 1. Health Check
```bash
curl http://localhost:8000/api/health
# Expected: {"status":"ok","mongo":true}
```

### 2. Memory - Aliases

#### Lister les aliases
```bash
curl "http://localhost:8000/api/memory/aliases?user_id=default_user"
# Expected: {"aliases":[],"total":0,"limit":50,"offset":0}
```

#### Créer un alias
```bash
curl -X POST "http://localhost:8000/api/memory/aliases?user_id=default_user" \
  -H "Content-Type: application/json" \
  -d '{"key":"comptable","value":"celine@cerfrance.fr","confidence":1.0}'
# Expected: {"id":"...","key":"comptable","value":"celine@cerfrance.fr","confidence":1.0,...}
```

#### Supprimer un alias par clé
```bash
curl -X DELETE "http://localhost:8000/api/memory/aliases/by-key/comptable?user_id=default_user"
# Expected: {"status":"deleted"}
```

### 3. Memory - Vendors

#### Lister les vendors
```bash
curl "http://localhost:8000/api/memory/vendors?user_id=default_user"
# Expected: {"vendors":[],"total":0,...}
```

#### Créer un vendor
```bash
curl -X POST "http://localhost:8000/api/memory/vendors?user_id=default_user" \
  -H "Content-Type: application/json" \
  -d '{"name":"distram","domain":"distram.fr","last_invoice_email":"facturation@distram.fr"}'
# Expected: {"id":"...","name":"distram","domains":["distram.fr"],...}
```

### 4. Memory - Contacts

#### Lister les contacts
```bash
curl "http://localhost:8000/api/memory/contacts?user_id=default_user"
# Expected: {"contacts":[],"total":0,...}
```

### 5. Memory - Stats
```bash
curl "http://localhost:8000/api/memory/stats?user_id=default_user"
# Expected: {"user_id":"default_user","stats":{"contacts":0,"aliases":0,"vendors":0}}
```

### 6. Copilot - Resolve

#### Résoudre un alias
```bash
# D'abord créer l'alias
curl -X POST "http://localhost:8000/api/memory/aliases?user_id=default_user" \
  -H "Content-Type: application/json" \
  -d '{"key":"comptable","value":"celine@cerfrance.fr"}'

# Puis résoudre
curl -X POST "http://localhost:8000/api/copilot/resolve" \
  -H "Content-Type: application/json" \
  -d '{"text":"comptable","user_id":"default_user"}'
# Expected: {"resolved":true,"email":"celine@cerfrance.fr","source":"alias",...}
```

### 7. Copilot - Search

```bash
# Nécessite un compte Gmail connecté
curl -X POST "http://localhost:8000/api/copilot/search" \
  -H "Content-Type: application/json" \
  -d '{"query_text":"facture distram du mois dernier","user_id":"default_user"}'
# Expected: {"account":{...},"query_text":"...","attempts":[...],"results":[...],...}
```

### 8. Chat (requiert LLM configuré)

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message":"trouve la dernière facture Distram","mode":"actions","user_id":"default_user"}'
# Expected: {"reply":"...","action":"show_email_results","context":{...}}
```

## Tests avec Python

```python
# tests/test_memory.py
import httpx
import asyncio

BASE = "http://localhost:8000"

async def test_memory_crud():
    async with httpx.AsyncClient() as client:
        # Create alias
        r = await client.post(
            f"{BASE}/api/memory/aliases",
            params={"user_id": "test_user"},
            json={"key": "test_alias", "value": "test@example.com"}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["key"] == "test_alias"
        alias_id = data["id"]

        # List aliases
        r = await client.get(f"{BASE}/api/memory/aliases", params={"user_id": "test_user"})
        assert r.status_code == 200
        assert len(r.json()["aliases"]) >= 1

        # Delete alias
        r = await client.delete(f"{BASE}/api/memory/aliases/{alias_id}", params={"user_id": "test_user"})
        assert r.status_code == 200

        print("✅ All memory tests passed")

if __name__ == "__main__":
    asyncio.run(test_memory_crud())
```

## Résultats attendus

| Endpoint | Status | Response |
|----------|--------|----------|
| GET /api/health | 200 | `{"status":"ok","mongo":true}` |
| GET /api/memory/aliases | 200 | `{"aliases":[...],"total":N}` |
| POST /api/memory/aliases | 200 | `{"id":"...","key":"..."}` |
| DELETE /api/memory/aliases/{id} | 200 | `{"status":"deleted"}` |
| POST /api/copilot/resolve | 200 | `{"resolved":true/false,...}` |
| POST /api/copilot/search | 200 | `{"results":[...],"attempts":[...]}` |
| POST /api/chat | 200 | `{"reply":"...","action":"..."}` |
