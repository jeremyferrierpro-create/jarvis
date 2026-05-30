# J.A.R.V.I.S

Assistant vocal personnel Windows (v5.5) — domotique, multimédia, vision et **mode développeur web autonome**.

Site du créateur original : [TechEnClair](https://www.techenclair.fr)

## Fonctionnalités

- Reconnaissance vocale et synthèse (Edge TTS)
- Interface Three.js (orbe, globe, hologramme) + compagnon mobile
- Home Assistant, Google (Gmail, Drive, Calendar), Spotify, Deezer
- **Super IA Dev** : analyse de projet, lecture/écriture de fichiers, terminal, recherche web, auto-apprentissage
- Modes dev : `assistant`, `autonomous`, `learn`

## Prérequis

- Windows 10/11
- Python 3.10+
- [Node.js](https://nodejs.org/) 18+ (pour reconstruire le frontend)
- Microphone

## Installation

```powershell
cd JARVIS
copy .env.example .env
# Éditez .env avec vos clés API

copy jarvis_config.example.json jarvis_config.json
# Personnalisez votre prénom, micro, etc.

# Environnement Python
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt

# Frontend (optionnel si dist/ déjà présent)
cd frontend
npm install
npm run build
cd ..
```

Lancement :

```powershell
.\DEMARRER_JARVIS.bat
```

Ou : `.\venv\Scripts\python.exe main2.py`

## Configuration

| Fichier | Rôle |
|---------|------|
| `.env` | Clés API (ignoré par Git) |
| `jarvis_config.json` | Profil utilisateur (ignoré par Git) |
| `ha_config.py` | Entités Home Assistant — à adapter à votre maison |
| `credentials.json` | OAuth Google — voir `credentials_LISEZ_MOI.txt` |

## Mode développeur web

1. Dites : **« Jarvis, mode dev autonome »**
2. Exemple : **« Crée le dossier frontend/demo et un fichier index.html Hello World »**

Commandes vocales utiles :

- `mode assistant dev` — une action à la fois
- `mode apprentissage` — recherche web + mémorisation
- `désactive le mode dev`

## Ports réseau

| Port | Service |
|------|---------|
| 8765 | WebSocket (UI ↔ backend) |
| 5173 | Frontend Vite (dev) |
| 8080 | Interface mobile |

> Sur un réseau partagé, limitez l’accès (pare-feu) : les ports sont exposés sans authentification par défaut.

## Structure du projet

```
JARVIS/
├── main2.py              # Orchestrateur principal
├── ha_config.py          # Domotique
├── memory_manager.py     # Mémoire persistante
├── vision_module.py      # Vision écran / webcam
├── frontend/             # Interface web (Vite + Three.js)
├── mobile/               # UI mobile
└── _setup/               # Scripts d’installation
```

## Sécurité

- Ne poussez **jamais** `.env`, `credentials.json` ni `token.pickle` sur GitHub.
- Si des clés ont été exposées, **révoquez-les** immédiatement sur les consoles fournisseurs.

## Licence

Usage personnel. Voir le dépôt pour les conditions applicables.
