# 🚀 Inbox Copilot

**Tu parles, je gère tes mails.**

---

## 🎨 Branding

### Logo
- **Design** : Oiseau copilote + enveloppe stylisée
- **Couleurs** : Dégradé #0A84FF → #5E00FF
- **Animation** : Ailes qui se lèvent légèrement (Framer Motion)
- **Formats** : Responsive (sm, md, lg, xl)

### Palette de Couleurs
- **Primaire (Bleu)** : `rgb(10, 132, 255)` - Pour l'utilisateur
- **Accent (Violet)** : `rgb(94, 0, 255)` - Pour l'assistant IA
- **Dégradé Logo** : `linear-gradient(135deg, #0A84FF 0%, #5E00FF 100%)`
- **Background** : `#F5F5F7` (light mode)

---

## 💬 Messages Motivants

Les messages d'accueil alternent toutes les 10 secondes :

1. **"Tu parles, je gère tes mails. Recherche, réponses, relances — je m'occupe de tout."**
2. **"Ton temps est précieux. Laisse-moi dompter ta boîte mail."**
3. **"Moins d'emails, plus de business. 🚀"**

Ces messages renforcent la **mission produit** : faire gagner du temps à l'utilisateur.

---

## 🎯 Mission Produit

**Inbox Copilot gère 100% des actions liées aux emails :**

### ✅ Fonctionnalités Implémentées

1. **Rédaction / Réponse / Envoi**
   - Génération de brouillons via GPT-4
   - Modification dans le chat
   - Validation avant envoi (toujours)

2. **Recherche Avancée**
   - Recherche multi-comptes (Gmail + Outlook)
   - Filtres par expéditeur, date, pièces jointes
   - Résultats avec liens directs

3. **Scan Auto des Nouveaux Emails**
   - Système de "Fichiers Attendus"
   - Scan périodique configurable
   - Alertes intelligentes

4. **Relances Automatiques**
   - Suivi des fichiers attendus
   - Suggestions de relance
   - **Validation utilisateur requise**

5. **Suivi des Documents Attendus**
   - Page dédiée
   - Statuts : En attente, Reçu, Relancé
   - Historique et emails associés

6. **Résumé Intelligent** (à venir)
   - Résumé quotidien de la boîte
   - Emails importants à traiter
   - Priorisation automatique

7. **Suggestions d'Actions** (à venir)
   - Emails à traiter
   - Réponses suggérées
   - Actions recommandées

### 🔒 Règle d'Or
**Aucune action n'est exécutée sans validation explicite de l'utilisateur.**

---

## 📱 UI/UX - Mobile-First

### Design Vibrant & Motivant

**Bulles de Chat Type iMessage**
- **Utilisateur** : Bleu `#0A84FF` (dégradé) + arrondi en bas à droite
- **Assistant** : Violet `#5E00FF` (dégradé) + arrondi en bas à gauche
- Animations énergiques (spring, bounce-in)

**Navigation Mobile**
- Bottom bar fixe avec 3 onglets
- 💬 Assistant / 📄 Fichiers / ⚙️ Paramètres
- Touch-friendly (min 44px)

**Chat Plein Écran**
- Priorité à la conversation
- Champ message + micro bien visibles
- Bottom sheet pour brouillons/résultats

**Dictée Vocale**
- Bouton micro intégré
- API SpeechRecognition
- Animation "recording" pendant l'écoute
- Gros bouton accessible au pouce

### Animations Énergiques

- **Messages** : Scale + spring animation
- **Empty State** : Fade in avec badges interactifs
- **Loading** : Sparkles qui tournent
- **Logo** : Ailes qui battent doucement

---

## 🏗️ Architecture (Backend Inchangé)

### Backend FastAPI
- ✅ OAuth2 Gmail/Microsoft
- ✅ CRUD comptes & signatures
- ✅ Envoi/Recherche emails
- ✅ Fichiers attendus + scan
- ✅ MongoDB

### Frontend Next.js
- ✅ Pages : Assistant, Fichiers, Paramètres
- ✅ Composants : Logo, MotivationalMessage, MobileNav, DesktopSidebar
- ✅ Responsive : Desktop + Mobile optimisé
- ✅ Thème : Light/Dark toggle

---

## 🎨 Nouveaux Composants

### `Logo.jsx`
- Logo animé avec dégradé
- Sizes : sm, md, lg, xl
- Animation des ailes
- Glow effect

### `MotivationalMessage.jsx`
- Messages alternés toutes les 10s
- Fade in/out smooth
- 3 messages motivants

### Styles CSS Ajoutés
```css
.user-bubble { /* Bleu dégradé */ }
.ai-bubble { /* Violet dégradé */ }
.gradient-text { /* Texte dégradé logo */ }
.bounce-in { /* Animation énergique */ }
.recording { /* Animation micro */ }
```

---

## 🚀 Expérience Utilisateur

### Objectif
**Un outil qu'on a envie d'ouvrir tous les jours comme WhatsApp.**

### Pourquoi ?
1. **Design vibrant** : Couleurs énergiques, animations fluides
2. **Messages motivants** : Rappellent la valeur ajoutée
3. **Mobile-first** : Parfait pour iPhone
4. **Gain de temps réel** : Actions email en quelques secondes
5. **Validation toujours requise** : Contrôle total

### Cas d'Usage Typiques
- **Matin** : "Résume mes emails importants"
- **En déplacement** : Dictée vocale pour rédiger un email
- **Suivi** : "Ai-je reçu la facture Distram ?"
- **Relance** : "Relance Marie pour le contrat"

---

## 📦 Installation & Configuration

### Prérequis
- Node.js 18+
- Python 3.11+
- MongoDB
- Credentials OAuth (Google + Microsoft)

### Démarrage
```bash
# Frontend
cd /app
yarn install
sudo supervisorctl restart nextjs

# Backend
cd /app/backend
pip install -r requirements.txt
sudo supervisorctl restart fastapi

# Accès
http://localhost:3000
```

### Configuration OAuth
Voir `/app/README_ASSISTANT.md` pour les instructions complètes.

---

## 🎯 Roadmap

### Prochaines Fonctionnalités
- [ ] Résumé quotidien intelligent de la boîte
- [ ] Suggestions d'emails à traiter
- [ ] Relances automatiques avec validation
- [ ] Intégration calendrier (Google/Outlook)
- [ ] Réponses rapides pré-configurées
- [ ] Templates d'emails personnalisés
- [ ] Statistiques & analytics

---

## 🔥 Points Forts

1. **Branding fort** : Logo unique, couleurs vibrantes
2. **Messages motivants** : Engagement utilisateur
3. **Mobile-first** : Parfait pour iPhone
4. **Dictée vocale** : Gain de temps énorme
5. **Animations** : Expérience premium
6. **iMessage-like** : Familier et intuitif
7. **Validation requise** : Sécurité et contrôle

---

**Inbox Copilot - Moins d'emails, plus de business. 🚀**
