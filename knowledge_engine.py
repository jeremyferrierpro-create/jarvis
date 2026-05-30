# -*- coding: utf-8 -*-
"""
Moteur de connaissances JARVIS — processus formalisés, apprentissage structuré, réutilisation.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime
from typing import Any

_jarvis_root = ""
_knowledge_file = ""
_process_file = ""

CATEGORIES = ("code", "web", "pattern", "projet", "erreur", "process", "document")

PROCESSUS_CREATION_SITE = [
    {"id": "collecte_documents", "label": "Collecter cahier des charges, maquettes, assets", "obligatoire": True},
    {"id": "analyse_cognitive", "label": "Analyser documents (OCR, LLM, jarvis_uploads)", "obligatoire": True},
    {"id": "briefing", "label": "Compléter le briefing (questions manquantes)", "obligatoire": True},
    {"id": "scaffold", "label": "Générer scaffold senior (structure fichiers)", "obligatoire": True},
    {"id": "developpement", "label": "Personnaliser code (webdev_*)", "obligatoire": True},
    {"id": "validation", "label": "Valider projet (webdev_valider_projet)", "obligatoire": True},
    {"id": "apprentissage_retour", "label": "Mémoriser patterns réussis dans la base", "obligatoire": False},
]

_SUJETS_INTERDITS = frozenset({
    "continue", "ok", "oui", "non", "merci", "lance le developpement", "lance le développement",
    "c'est bon", "cest bon", "scanne les documents", "jarvis",
})

_BRUIT_PATTERNS = (
    r"réponds uniquement",
    r"important:\s*réponds",
    r"\[tache dev web",
    r"voici ce que j'ai trouvé sur le web pour (continue|lance|ok)\b",
)


def init(jarvis_root: str) -> None:
    global _jarvis_root, _knowledge_file, _process_file
    _jarvis_root = jarvis_root
    _knowledge_file = os.path.join(jarvis_root, "jarvis_learning_base.json")
    _process_file = os.path.join(jarvis_root, "jarvis_process_state.json")
    _migrer_ancien_format()


def _migrer_ancien_format() -> None:
    if not os.path.isfile(_knowledge_file):
        return
    try:
        with open(_knowledge_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return
    if data.get("_schema") == "v2":
        return
    if isinstance(data.get("entries"), dict):
        return
    nouveau: dict[str, Any] = {"_schema": "v2", "entries": {}, "meta": {}}
    for sujet, info in data.items():
        if not isinstance(info, dict):
            continue
        eid = _nouvel_id()
        nouveau["entries"][eid] = {
            "id": eid,
            "sujet": str(sujet)[:120],
            "categorie": _deviner_categorie(str(sujet), info.get("description", ""), info.get("code", "")),
            "tags": _extraire_tags(str(sujet), info.get("description", "")),
            "description": info.get("description", "")[:4000],
            "code": info.get("code", "")[:8000],
            "source": "legacy",
            "date": info.get("date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            "utilisations": 0,
        }
    _sauver_raw(nouveau)


def _nouvel_id() -> str:
    return datetime.now().strftime("%Y%m%d") + "_" + uuid.uuid4().hex[:10]


def _charger_raw() -> dict[str, Any]:
    if not os.path.isfile(_knowledge_file):
        return {"_schema": "v2", "entries": {}, "meta": {}}
    try:
        with open(_knowledge_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("_schema") != "v2":
            init(_jarvis_root or os.path.dirname(_knowledge_file))
            with open(_knowledge_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return data
    except Exception:
        return {"_schema": "v2", "entries": {}, "meta": {}}


def _sauver_raw(data: dict[str, Any]) -> None:
    data["_schema"] = "v2"
    data.setdefault("meta", {})["derniere_maj"] = datetime.now().isoformat()
    with open(_knowledge_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _deviner_categorie(sujet: str, desc: str, code: str) -> str:
    t = (sujet + " " + desc).lower()
    if code and len(code.strip()) > 30:
        return "code"
    if any(x in t for x in ("erreur", "bug", "fix")):
        return "erreur"
    if any(x in t for x in ("projet", "site web", "cahier")):
        return "projet"
    return "web"


def _extraire_tags(sujet: str, desc: str) -> list[str]:
    texte = (sujet + " " + desc).lower()
    tags = set()
    for mot in re.findall(r"[a-zàâäéèêëïîôùûüç0-9#.+]{3,}", texte):
        if mot in ("les", "des", "pour", "avec", "dans", "une"):
            continue
        tags.add(mot[:30])
    return sorted(tags)[:12]


def _est_entree_valide(sujet: str, description: str) -> tuple[bool, str]:
    sujet_n = (sujet or "").strip().lower()
    if len(sujet_n) < 4:
        return False, "Sujet trop court"
    if sujet_n in _SUJETS_INTERDITS:
        return False, "Commande vocale"
    if len(sujet) > 150:
        return False, "Sujet bruité"
    desc = description or ""
    for pat in _BRUIT_PATTERNS:
        if re.search(pat, sujet + " " + desc, re.I):
            return False, "Bruit contexte/recherche"
    if len(desc.strip()) < 10 and not desc.strip():
        return False, "Description vide"
    return True, ""


def memoriser(
    sujet: str,
    description: str,
    code: str = "",
    categorie: str = "web",
    tags: list[str] | None = None,
    source: str = "auto",
) -> dict[str, Any]:
    ok, raison = _est_entree_valide(sujet, description or code)
    if not ok:
        print(f"[KNOWLEDGE] Rejeté ({raison}) : {(sujet or '')[:60]}")
        return {"ok": False, "message": f"Non mémorisé : {raison}", "id": None}

    if categorie not in CATEGORIES:
        categorie = _deviner_categorie(sujet, description, code)

    data = _charger_raw()
    entries = data.setdefault("entries", {})
    sujet_key = sujet.strip()[:120].lower()

    for eid, ent in entries.items():
        if ent.get("sujet", "").lower() == sujet_key:
            ent["description"] = (description or ent.get("description", ""))[:4000]
            if code:
                ent["code"] = code[:8000]
            ent["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ent["source"] = source
            _sauver_raw(data)
            return {"ok": True, "message": f"Connaissance mise à jour : {sujet}", "id": eid}

    eid = _nouvel_id()
    entries[eid] = {
        "id": eid,
        "sujet": sujet.strip()[:120],
        "categorie": categorie,
        "tags": tags or _extraire_tags(sujet, description),
        "description": (description or "")[:4000],
        "code": (code or "")[:8000],
        "source": source,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "utilisations": 0,
    }
    _sauver_raw(data)
    print(f"[KNOWLEDGE] + [{categorie}] {sujet[:60]}")
    return {"ok": True, "message": f"Mémorisé [{categorie}] : {sujet}", "id": eid}


def apprendre_code(sujet: str, code: str, description: str = "", source: str = "utilisateur") -> dict[str, Any]:
    if not code or len(code.strip()) < 10:
        return {"ok": False, "message": "Code trop court.", "id": None}
    lang = _detecter_langage(code)
    if not sujet:
        sujet = f"pattern {lang} {datetime.now().strftime('%Y%m%d')}"
    return memoriser(
        sujet,
        description or f"Snippet {lang} — {len(code)} car.",
        code,
        categorie="code",
        tags=[lang] if lang else [],
        source=source,
    )


def _detecter_langage(code: str) -> str:
    c = code.strip()
    if "<html" in c[:300].lower():
        return "html"
    if "function " in c or "=>" in c:
        return "javascript"
    if "def " in c:
        return "python"
    if "<?php" in c:
        return "php"
    if "{" in c and ":" in c:
        return "css"
    return "code"


def apprendre_depuis_web(sujet: str, contenu_brut: str, url: str = "") -> dict[str, Any]:
    if not contenu_brut or len(contenu_brut.strip()) < 40:
        return {"ok": False, "message": "Contenu web insuffisant.", "id": None}
    lines = []
    for line in contenu_brut.split("\n"):
        line = line.strip()
        if not line or "Voici ce que j'ai trouvé" in line:
            continue
        lines.append(re.sub(r"^-\s+[^:]+:\s*", "", line))
    return memoriser(
        sujet,
        "\n".join(lines)[:2500],
        "",
        categorie="web",
        tags=_extraire_tags(sujet, contenu_brut),
        source=f"web:{url[:60]}" if url else "web",
    )


def rechercher(query: str, categorie: str | None = None, limit: int = 12) -> list[dict[str, Any]]:
    mots = set(re.findall(r"[a-zàâäéèêëïîôùûüç0-9]{3,}", (query or "").lower()))
    if not mots:
        return []
    scores: list[tuple[int, dict]] = []
    for ent in _charger_raw().get("entries", {}).values():
        if categorie and ent.get("categorie") != categorie:
            continue
        blob = (ent.get("sujet", "") + " " + " ".join(ent.get("tags", [])) + " " + ent.get("description", "")[:400]).lower()
        score = sum(2 if m in ent.get("sujet", "").lower() else 1 for m in mots if m in blob)
        if score > 0:
            scores.append((score, ent))
    scores.sort(key=lambda x: (-x[0], x[1].get("date", "")))
    return [e for _, e in scores[:limit]]


def injecter_pour_tache(tache: str, max_chars: int = 10000) -> str:
    parties = [contexte_processus("creation_site")]
    hits = rechercher(tache, limit=12) or list(_charger_raw().get("entries", {}).values())[-8:]
    if hits:
        parties.append("\n=== CONNAISSANCES PERTINENTES (réutilise) ===\n")
        total = 0
        for ent in hits:
            bloc = f"\n[{ent.get('categorie')}] {ent.get('sujet')}\n{ent.get('description', '')[:600]}\n"
            if ent.get("code"):
                bloc += f"```\n{ent['code'][:1200]}\n```\n"
            if total + len(bloc) > max_chars:
                break
            parties.append(bloc)
            total += len(bloc)
    return "".join(parties)[:max_chars]


def injecter_format_legacy() -> str:
    entries = list(_charger_raw().get("entries", {}).values())
    if not entries:
        return ""
    ctx = f"\n\n=== BASE DE CONNAISSANCES ({len(entries)} entrées) ===\n"
    for ent in entries[-35:]:
        ctx += f"- [{ent.get('categorie')}] {ent.get('sujet')} ({ent.get('date')})\n"
        ctx += f"  {ent.get('description', '')[:350]}\n"
        if ent.get("code"):
            ctx += f"  Code: {ent['code'][:400]}\n"
    return ctx


def compter() -> int:
    return len(_charger_raw().get("entries", {}))


def _charger_process() -> dict[str, Any]:
    if not os.path.isfile(_process_file):
        return {"processus_actif": None, "etapes": {}}
    try:
        with open(_process_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"processus_actif": None, "etapes": {}}


def _sauver_process(data: dict[str, Any]) -> None:
    with open(_process_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def demarrer_processus(nom: str = "creation_site") -> None:
    data: dict[str, Any] = {"processus_actif": nom, "demarre": datetime.now().isoformat(), "etapes": {}}
    for e in PROCESSUS_CREATION_SITE:
        data["etapes"][e["id"]] = {"statut": "pending", "label": e["label"]}
    _sauver_process(data)


def marquer_etape(etape_id: str, statut: str = "done") -> None:
    data = _charger_process()
    if not data.get("processus_actif"):
        demarrer_processus("creation_site")
        data = _charger_process()
    if etape_id in data.get("etapes", {}):
        data["etapes"][etape_id]["statut"] = statut
        data["etapes"][etape_id]["horodatage"] = datetime.now().isoformat()
        _sauver_process(data)


def prochaine_etape_requise() -> dict[str, Any] | None:
    data = _charger_process()
    if data.get("processus_actif") != "creation_site":
        return None
    for step in PROCESSUS_CREATION_SITE:
        st = data.get("etapes", {}).get(step["id"], {}).get("statut", "pending")
        if step["obligatoire"] and st not in ("done", "skipped"):
            return step
    return None


def contexte_processus(nom: str = "creation_site") -> str:
    data = _charger_process()
    if data.get("processus_actif") != nom:
        seq = " → ".join(s["id"] for s in PROCESSUS_CREATION_SITE)
        return f"\n=== PROCESSUS CRÉATION SITE (ordre obligatoire) ===\n{seq}\n"
    lines = [f"\n=== PROCESSUS {nom} — ÉTAT ==="]
    for step in PROCESSUS_CREATION_SITE:
        st = data.get("etapes", {}).get(step["id"], {}).get("statut", "pending")
        mark = {"done": "✓", "in_progress": "→", "failed": "✗"}.get(st, "○")
        lines.append(f"  {mark} {step['id']}: {step['label']}")
    nxt = prochaine_etape_requise()
    if nxt:
        lines.append(f"\nÉTAPE OBLIGATOIRE MAINTENANT : {nxt['id']}\n")
    return "\n".join(lines)
