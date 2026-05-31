# -*- coding: utf-8 -*-
"""
Capacités avancées JARVIS — UI, workflows, sécurité, projets, domotique, apprentissage.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime
from typing import Any

JARVIS_ROOT = os.path.dirname(os.path.abspath(__file__))
WORKFLOWS_FILE = os.path.join(JARVIS_ROOT, "jarvis_workflows.json")
PROJECTS_FILE = os.path.join(JARVIS_ROOT, "jarvis_projects.json")
SESSION_FILE = os.path.join(JARVIS_ROOT, "jarvis_session_notes.json")

_SKIP_DIRS = frozenset({"node_modules", ".git", "__pycache__", "venv", ".venv", "dist", "build"})

_SEC_PATTERNS = [
    (r"(?i)(api[_-]?key|secret|password|passwd|token)\s*=\s*['\"][^'\"]{6,}", "Secret en clair possible"),
    (r"(?i)BEGIN\s+(RSA|OPENSSH)\s+PRIVATE", "Clé privée dans le fichier"),
    (r"\beval\s*\(", "eval() détecté"),
    (r"document\.write\s*\(", "document.write (XSS risque)"),
    (r"innerHTML\s*=", "innerHTML (XSS risque)"),
    (r"http://(?!localhost|127\.0\.0\.1)", "URL HTTP non sécurisée"),
    (r"(?i)SELECT\s+.+\s+FROM\s+.+\s+WHERE\s+.*\+", "Concat SQL possible"),
]

_UI_CHECKS = [
    (r"<img(?![^>]*\balt=)", "Image sans attribut alt"),
    (r"<html(?![^>]*\blang=)", "Balise html sans lang"),
    (r"<a[^>]+href\s*=\s*['\"]#['\"]", "Lien vide href=#"),
]


def _resoudre_chemin_projet(chemin: str) -> str:
    chemin = (chemin or ".").strip().strip('"')
    if os.path.isabs(chemin):
        return os.path.normpath(chemin)
    return os.path.normpath(os.path.join(JARVIS_ROOT, chemin))


def _lire_json(path: str, default: Any) -> Any:
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _ecrire_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _parcourir_sources(chemin_abs: str, extensions: tuple[str, ...]) -> list[str]:
    fichiers = []
    if not os.path.isdir(chemin_abs):
        return fichiers
    for root, dirs, files in os.walk(chemin_abs):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fname in files:
            if os.path.splitext(fname)[1].lower() in extensions:
                fichiers.append(os.path.join(root, fname))
    return fichiers


# ── 1. Optimisation interface (audit UI/UX) ─────────────────────────────────
def auditer_ui(chemin_dossier: str) -> str:
    from web_dev_engine import auditer_projet, formater_rapport_audit, detecter_stack

    path = _resoudre_chemin_projet(chemin_dossier)
    stack = detecter_stack(chemin_dossier)
    audit = auditer_projet(path, stack)
    ux: list[str] = []
    for fpath in _parcourir_sources(path, (".html", ".htm", ".php", ".jsx", ".tsx", ".vue")):
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError:
            continue
        rel = os.path.relpath(fpath, path)
        for pattern, msg in _UI_CHECKS:
            if re.search(pattern, content, re.I):
                ux.append(f"{rel}: {msg}")
        if re.search(r"<h1", content, re.I) is None and "index" in rel.lower():
            ux.append(f"{rel}: Pas de balise h1 détectée")
        if content.count("!important") > 15:
            ux.append(f"{rel}: Beaucoup de !important en CSS inline/styles ({content.count('!important')})")

    lines = ["=== AUDIT INTERFACE / UX ===", formater_rapport_audit(audit)]
    if ux:
        lines.append("\nRecommandations UX :")
        for u in ux[:25]:
            lines.append(f"  • {u}")
    else:
        lines.append("\nAucun problème UX majeur détecté.")
    lines.append("\nPour corriger : utilisez webdev_ecrire_fichier ou webdev_patch_fichier.")
    return "\n".join(lines)


# ── 2. Automatisation (workflows) ───────────────────────────────────────────
def _workflows_defaut() -> dict:
    return {
        "matin_dev": {
            "label": "Routine matin développeur",
            "steps": [
                {"action": "mode_boulot"},
                {"action": "info_systeme"},
            ],
        },
        "audit_projet": {
            "label": "Audit UI + sécurité d'un dossier",
            "steps": [
                {"action": "auditer_ui", "chemin_dossier": "projects/sites"},
                {"action": "auditer_securite", "chemin_dossier": "projects/sites"},
            ],
        },
        "pause": {
            "label": "Pause — baisse luminosité et volume",
            "steps": [
                {"action": "luminosite", "direction": "baisser"},
                {"action": "volume_systeme", "direction": "baisser", "paliers": 3},
            ],
        },
    }


def charger_workflows() -> dict:
    data = _lire_json(WORKFLOWS_FILE, {})
    wfs = data.get("workflows") if isinstance(data, dict) else {}
    if not isinstance(wfs, dict):
        wfs = {}
    defaults = _workflows_defaut()
    for k, v in defaults.items():
        wfs.setdefault(k, v)
    return wfs


def lister_workflows() -> str:
    wfs = charger_workflows()
    if not wfs:
        return "Aucun workflow enregistré."
    lignes = ["Workflows disponibles :"]
    for nom, info in wfs.items():
        nb = len(info.get("steps", []))
        lignes.append(f"  • {nom} — {info.get('label', nom)} ({nb} étapes)")
    return "\n".join(lignes)


def get_etapes_workflow(nom: str) -> list[dict]:
    wfs = charger_workflows()
    info = wfs.get((nom or "").strip().lower())
    if not info:
        for k, v in wfs.items():
            if k.lower() == (nom or "").lower() or (nom or "").lower() in (v.get("label") or "").lower():
                info = v
                break
    if not info:
        return []
    return list(info.get("steps") or [])


def enregistrer_workflow(nom: str, label: str, steps: list) -> str:
    nom = (nom or "").strip().lower().replace(" ", "_")
    if not nom or not steps:
        return "Nom et étapes requis pour enregistrer un workflow."
    data = _lire_json(WORKFLOWS_FILE, {"workflows": {}})
    data.setdefault("workflows", {})[nom] = {
        "label": label or nom,
        "steps": steps,
        "cree_le": datetime.now().isoformat(),
    }
    _ecrire_json(WORKFLOWS_FILE, data)
    return f"Workflow « {nom} » enregistré avec {len(steps)} étapes."


# ── 3. Apprentissage continu ──────────────────────────────────────────────────
def apprendre_techno(sujet: str, description: str = "", code: str = "", categorie: str = "web") -> str:
    try:
        import knowledge_engine as ke
        ke.init(JARVIS_ROOT)
        if code and len(code.strip()) > 10:
            return ke.apprendre_code(sujet, code, description, source="jarvis").get("message", "OK")
        return ke.memoriser(sujet, description, code, categorie=categorie, source="jarvis").get("message", "OK")
    except Exception as e:
        return f"Apprentissage impossible : {e}"


def synthese_connaissances(sujet: str = "") -> str:
    try:
        import knowledge_engine as ke
        ke.init(JARVIS_ROOT)
        entries = ke.rechercher(sujet, limite=8) if sujet else []
        if not entries and sujet:
            return f"Aucune connaissance trouvée pour « {sujet} »."
        if not entries:
            raw = ke._charger_raw()
            entries = list(raw.get("entries", {}).values())[-8:]
        lignes = ["Connaissances mémorisées :"]
        for ent in entries:
            lignes.append(f"  • [{ent.get('categorie')}] {ent.get('sujet')}: {str(ent.get('description', ''))[:120]}")
        return "\n".join(lignes)
    except Exception as e:
        return f"Erreur base de connaissances : {e}"


# ── 4. Sécurité ───────────────────────────────────────────────────────────────
def auditer_securite(chemin_dossier: str) -> str:
    path = _resoudre_chemin_projet(chemin_dossier)
    if not os.path.isdir(path):
        return f"Dossier introuvable : {chemin_dossier}"

    findings: list[str] = []
    for suspect in (".env", "credentials.json", "token.pickle", "id_rsa"):
        fp = os.path.join(path, suspect)
        if os.path.isfile(fp):
            findings.append(f"[CRITIQUE] Fichier sensible à la racine : {suspect}")

    for fpath in _parcourir_sources(path, (".py", ".js", ".jsx", ".ts", ".tsx", ".php", ".html", ".env", ".json")):
        rel = os.path.relpath(fpath, path)
        if any(p in rel for p in _SKIP_DIRS):
            continue
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError:
            continue
        for pattern, msg in _SEC_PATTERNS:
            if re.search(pattern, content):
                findings.append(f"{rel}: {msg}")

    lines = ["=== AUDIT SÉCURITÉ ==="]
    if not findings:
        lines.append("Aucune alerte majeure. Vérifiez quand même les dépendances (npm audit).")
    else:
        lines.append(f"{len(findings)} alerte(s) :")
        for f in findings[:30]:
            lines.append(f"  • {f}")
    return "\n".join(lines)


# ── 5. Développement créatif (scaffold) ─────────────────────────────────────
def creer_projet_creatif(
    nom: str,
    chemin_dossier: str,
    theme: str = "",
    type_projet: str = "site_vitrine",
    pages: str = "accueil, services, contact",
) -> str:
    from web_dev_engine import scaffold_projet, detecter_stack

    nom = (nom or "MonProjet").strip()
    stack_map = {
        "site_vitrine": "static",
        "portfolio": "static",
        "landing": "static",
        "api": "fastapi",
        "backend": "fastapi",
        "react": "react_vite",
        "fullstack": "fullstack_static_fastapi",
    }
    stack = stack_map.get((type_projet or "").lower(), detecter_stack(type_projet + " " + theme))
    rel = (chemin_dossier or f"projects/sites/{re.sub(r'[^a-z0-9]+', '-', nom.lower())}").strip()
    path = _resoudre_chemin_projet(rel)
    briefing = {
        "nom_site": nom,
        "theme": theme or f"Projet {nom} — design moderne et accessible",
        "pages": pages,
        "couleurs": "bleu profond, cyan accent, fond sombre élégant",
    }
    try:
        os.makedirs(path, exist_ok=True)
        created = scaffold_projet(path, stack, briefing)
        return (
            f"Projet créatif « {nom} » généré ({stack}) dans {rel}. "
            f"{len(created)} fichiers : {', '.join(os.path.basename(c) for c in created[:6])}."
        )
    except Exception as e:
        return f"Échec création projet : {e}"


# ── 6. Domotique — découverte HA ────────────────────────────────────────────
def decouvrir_home_assistant() -> str:
    try:
        from ha_config import HA_URL, HA_TOKEN, HA_HEADERS
        import requests
    except ImportError:
        return "Module ha_config indisponible."

    if not HA_URL or not HA_TOKEN:
        return "Configurez HA_URL et HA_TOKEN dans le fichier .env."

    try:
        r = requests.get(f"{HA_URL}/api/states", headers=HA_HEADERS, timeout=8)
        r.raise_for_status()
        states = r.json()
    except Exception as e:
        return f"Impossible de joindre Home Assistant : {e}"

    lights, switches, sensors, climate = [], [], [], []
    for s in states:
        eid = s.get("entity_id", "")
        if eid.startswith("light."):
            lights.append(eid)
        elif eid.startswith("switch.") or eid.startswith("input_boolean."):
            switches.append(eid)
        elif eid.startswith("sensor."):
            sensors.append(eid)
        elif eid.startswith("climate.") or eid.startswith("water_heater."):
            climate.append(eid)

    lignes = [
        f"Home Assistant — {len(states)} entités.",
        f"Lumières ({len(lights)}) : {', '.join(lights[:8])}{'…' if len(lights) > 8 else ''}",
        f"Interrupteurs ({len(switches)}) : {', '.join(switches[:6])}{'…' if len(switches) > 6 else ''}",
        f"Capteurs ({len(sensors)}) : {', '.join(sensors[:6])}{'…' if len(sensors) > 6 else ''}",
    ]
    if climate:
        lignes.append(f"Climat ({len(climate)}) : {', '.join(climate[:4])}")
    lignes.append("Ajoutez les entités utiles dans Paramètres → Appareils Home Assistant.")
    return " ".join(lignes)


# ── 7. Interaction humaine (notes de session) ───────────────────────────────
def noter_session(sujet: str, note: str = "", humeur: str = "") -> str:
    data = _lire_json(SESSION_FILE, {"notes": [], "derniere": {}})
    entry = {
        "id": uuid.uuid4().hex[:8],
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "sujet": (sujet or "session")[:200],
        "note": (note or "")[:2000],
        "humeur": (humeur or "")[:80],
    }
    data.setdefault("notes", []).append(entry)
    data["notes"] = data["notes"][-100:]
    data["derniere"] = entry
    _ecrire_json(SESSION_FILE, data)
    return f"Noté : {entry['sujet']}."


def contexte_session_pour_prompt() -> str:
    data = _lire_json(SESSION_FILE, {})
    notes = data.get("notes") or []
    derniere = data.get("derniere") or {}
    lignes = []
    if derniere.get("sujet"):
        lignes.append(f"Dernière session : {derniere.get('sujet')} ({derniere.get('date', '')})")
        if derniere.get("note"):
            lignes.append(f"  Note : {derniere['note'][:300]}")
        if derniere.get("humeur"):
            lignes.append(f"  Humeur : {derniere['humeur']}")
    recents = notes[-5:]
    if len(recents) > 1:
        lignes.append("Sessions récentes :")
        for n in recents:
            lignes.append(f"  • [{n.get('date')}] {n.get('sujet')}")
    proj_ctx = contexte_projets_pour_prompt()
    if proj_ctx:
        lignes.append(proj_ctx)
    return "\n".join(lignes) if lignes else ""


# ── 8. Gestion de projets ───────────────────────────────────────────────────
def _charger_projets() -> dict:
    return _lire_json(PROJECTS_FILE, {"projects": {}})


def projet_creer(nom: str, description: str = "", objectifs: list | None = None) -> str:
    nom_k = re.sub(r"[^a-z0-9_]+", "_", (nom or "projet").lower().strip())[:60]
    data = _charger_projets()
    projects = data.setdefault("projects", {})
    if nom_k in projects:
        return f"Le projet « {nom} » existe déjà."
    projects[nom_k] = {
        "nom": nom,
        "description": (description or "")[:2000],
        "objectifs": objectifs or [],
        "statut": "en_cours",
        "cree_le": datetime.now().strftime("%Y-%m-%d"),
        "taches": [],
    }
    _ecrire_json(PROJECTS_FILE, data)
    return f"Projet « {nom} » créé. Utilisez projet_tache_ajouter pour planifier."


def projet_tache_ajouter(nom_projet: str, tache: str, priorite: str = "normale") -> str:
    nom_k = _trouver_projet_key(nom_projet)
    if not nom_k:
        return f"Projet « {nom_projet} » introuvable."
    data = _charger_projets()
    p = data["projects"][nom_k]
    tid = uuid.uuid4().hex[:6]
    p.setdefault("taches", []).append({
        "id": tid,
        "titre": tache[:500],
        "priorite": priorite,
        "fait": False,
        "cree_le": datetime.now().strftime("%Y-%m-%d"),
    })
    _ecrire_json(PROJECTS_FILE, data)
    return f"Tâche ajoutée au projet « {p.get('nom')} » : {tache[:80]}."


def _trouver_projet_key(nom: str) -> str | None:
    data = _charger_projets()
    projects = data.get("projects", {})
    nom_l = (nom or "").lower()
    for k, v in projects.items():
        if k == nom_l or (v.get("nom") or "").lower() == nom_l:
            return k
        if nom_l in (v.get("nom") or "").lower():
            return k
    return None


def projet_statut(nom_projet: str) -> str:
    nom_k = _trouver_projet_key(nom_projet)
    if not nom_k:
        return f"Projet « {nom_projet} » introuvable."
    p = _charger_projets()["projects"][nom_k]
    taches = p.get("taches", [])
    faites = sum(1 for t in taches if t.get("fait"))
    lignes = [
        f"Projet « {p.get('nom')} » — statut {p.get('statut', '?')}.",
        p.get("description", "")[:200],
        f"Tâches : {faites}/{len(taches)} terminées.",
    ]
    for t in taches[:12]:
        mark = "✓" if t.get("fait") else "○"
        lignes.append(f"  {mark} [{t.get('priorite', '?')}] {t.get('titre')}")
    return "\n".join(lignes)


def projet_lister() -> str:
    projects = _charger_projets().get("projects", {})
    if not projects:
        return "Aucun projet enregistré. Créez-en un avec projet_creer."
    lignes = ["Projets en cours :"]
    for k, p in projects.items():
        nb = len(p.get("taches", []))
        faites = sum(1 for t in p.get("taches", []) if t.get("fait"))
        lignes.append(f"  • {p.get('nom')} ({faites}/{nb} tâches) — {p.get('statut')}")
    return "\n".join(lignes)


def projet_tache_terminee(nom_projet: str, tache_id: str = "", titre_partiel: str = "") -> str:
    nom_k = _trouver_projet_key(nom_projet)
    if not nom_k:
        return "Projet introuvable."
    data = _charger_projets()
    p = data["projects"][nom_k]
    for t in p.get("taches", []):
        if tache_id and t.get("id") == tache_id:
            t["fait"] = True
            _ecrire_json(PROJECTS_FILE, data)
            return f"Tâche terminée : {t.get('titre')}."
        if titre_partiel and titre_partiel.lower() in (t.get("titre") or "").lower():
            t["fait"] = True
            _ecrire_json(PROJECTS_FILE, data)
            return f"Tâche terminée : {t.get('titre')}."
    return "Tâche non trouvée."


def contexte_projets_pour_prompt() -> str:
    projects = _charger_projets().get("projects", {})
    actifs = [p for p in projects.values() if p.get("statut") == "en_cours"]
    if not actifs:
        return ""
    lignes = ["PROJETS ACTIFS :"]
    for p in actifs[:5]:
        pending = [t["titre"] for t in p.get("taches", []) if not t.get("fait")][:3]
        lignes.append(f"  • {p.get('nom')}: {', '.join(pending) or 'aucune tâche en attente'}")
    return "\n".join(lignes)


def construire_prompt_capacites_avancees(user_name: str = "Jérémy") -> str:
    wfs = ", ".join(charger_workflows().keys())
    return f"""
CAPACITÉS AVANCÉES JARVIS (carte blanche — utilise ces actions JSON) :

1. OPTIMISATION INTERFACE / UX
{{"action": "auditer_ui", "chemin_dossier": "projects/sites/mon-site"}}
Analyse HTML/CSS, accessibilité, structure. Corrige ensuite avec webdev_*.

2. AUTOMATISATION — WORKFLOWS
{{"action": "executer_workflow", "nom": "matin_dev"}}
{{"action": "lister_workflows"}}
{{"action": "enregistrer_workflow", "nom": "mon_flow", "label": "Description", "etapes": [{{"action": "ouvrir_app", "nom": "vscode"}}]}}
Workflows intégrés : {wfs}

3. APPRENTISSAGE CONTINU
{{"action": "apprendre_techno", "sujet": "React hooks", "description": "...", "code": "optionnel", "categorie": "web"}}
{{"action": "synthese_connaissances", "sujet": "optionnel"}}
Complète webdev_auto_apprendre et webdev_apprendre_web.

4. SÉCURITÉ APPLICATIONS
{{"action": "auditer_securite", "chemin_dossier": "chemin/projet"}}
Détecte secrets, eval, XSS, HTTP non sécurisé.

5. DÉVELOPPEMENT CRÉATIF
{{"action": "projet_creatif", "nom": "Mon Site", "chemin_dossier": "projects/sites/mon-site", "theme": "...", "type_projet": "site_vitrine|api|react", "pages": "accueil, contact"}}

6. DOMOTIQUE ÉTENDUE
{{"action": "ha_decouvrir"}}
Liste les entités Home Assistant pour les ajouter aux paramètres.

7. INTERACTION & CONTEXTE
{{"action": "noter_session", "sujet": "refonte API", "note": "...", "humeur": "concentré"}}
Mémorise le fil de la journée pour des réponses plus personnelles.

8. GESTION DE PROJETS
{{"action": "projet_creer", "nom": "Refonte API", "description": "...", "objectifs": ["FastAPI", "tests"]}}
{{"action": "projet_tache_ajouter", "nom_projet": "Refonte API", "tache": "Écrire les tests", "priorite": "haute"}}
{{"action": "projet_statut", "nom_projet": "Refonte API"}}
{{"action": "projet_lister"}}
{{"action": "projet_tache_terminee", "nom_projet": "...", "titre_partiel": "tests"}}

Ces capacités servent à rendre la vie de {user_name} plus simple — exécute-les quand c'est pertinent, pas seulement quand on te le demande explicitement.
"""


def executer_action_capacite(action: str, data: dict[str, Any]) -> str | None:
    action = (action or "").lower().strip()

    if action == "auditer_ui":
        return auditer_ui(data.get("chemin_dossier", "."))
    if action == "auditer_securite":
        return auditer_securite(data.get("chemin_dossier", "."))
    if action == "lister_workflows":
        return lister_workflows()
    if action == "enregistrer_workflow":
        return enregistrer_workflow(
            data.get("nom", ""),
            data.get("label", ""),
            data.get("etapes") or data.get("steps") or [],
        )
    if action == "apprendre_techno":
        return apprendre_techno(
            data.get("sujet", ""),
            data.get("description", ""),
            data.get("code", ""),
            data.get("categorie", "web"),
        )
    if action == "synthese_connaissances":
        return synthese_connaissances(data.get("sujet", ""))
    if action == "projet_creatif":
        return creer_projet_creatif(
            data.get("nom", "Projet"),
            data.get("chemin_dossier", ""),
            data.get("theme", ""),
            data.get("type_projet", "site_vitrine"),
            data.get("pages", "accueil, services, contact"),
        )
    if action == "ha_decouvrir":
        return decouvrir_home_assistant()
    if action == "noter_session":
        return noter_session(data.get("sujet", ""), data.get("note", ""), data.get("humeur", ""))
    if action == "projet_creer":
        return projet_creer(data.get("nom", ""), data.get("description", ""), data.get("objectifs"))
    if action == "projet_tache_ajouter":
        return projet_tache_ajouter(data.get("nom_projet", ""), data.get("tache", ""), data.get("priorite", "normale"))
    if action == "projet_statut":
        return projet_statut(data.get("nom_projet", ""))
    if action == "projet_lister":
        return projet_lister()
    if action == "projet_tache_terminee":
        return projet_tache_terminee(
            data.get("nom_projet", ""),
            data.get("tache_id", ""),
            data.get("titre_partiel", ""),
        )
    return None

# executer_workflow handled async in main2
