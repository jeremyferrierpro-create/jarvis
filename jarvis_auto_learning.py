# -*- coding: utf-8 -*-
"""
Auto-apprentissage avancé JARVIS — extraction, consolidation, mémoire par mode.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime
from typing import Any

try:
    from database.db_engine import inserer_apprentissage
except ImportError:
    inserer_apprentissage = None


JARVIS_ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(JARVIS_ROOT, "jarvis_config.json")
BY_MODE_FILE = os.path.join(JARVIS_ROOT, "jarvis_learning_by_mode.json")
META_FILE = os.path.join(JARVIS_ROOT, "jarvis_learning_meta.json")

_MODE_CATEGORIE = {
    "professionnel": "code",
    "psychologique": "emotion",
    "amoureux": "relation",
    "personnel": "preference",
    "ami": "relation",
    "standard": "process",
}

_PATTERNS_PREFERENCE = [
    re.compile(r"(?:j['']aime|je préfère|je prefere|j'adore)\s+(.{5,120})", re.I),
    re.compile(r"(?:ma|mon)\s+(?:boisson|musique|plat)\s+(?:préférée?|preferee?|favori)\s*(?:est|:)?\s*(.{3,80})", re.I),
]
_PATTERNS_FAIT = [
    re.compile(r"(?:je travaille sur|mon projet|j'ai un problème sur)\s+(.{8,150})", re.I),
    re.compile(r"(?:souviens[- ]toi|n'oublie pas|mémorise)\s*(?:que)?\s*(.{10,200})", re.I),
]
_PATTERNS_TECHNIQUE = [
    re.compile(r"```[\w]*\n([\s\S]{20,2000})```"),
    re.compile(r"(?:solution|fix|correctif)\s*:\s*(.{20,500})", re.I),
]


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


def _config_apprentissage() -> dict:
    cfg = _lire_json(CONFIG_FILE, {})
    al = cfg.get("jarvis_auto_learning") or {}
    if not isinstance(al, dict):
        al = {}
    return {
        "actif": al.get("actif", True),
        "apprendre_echanges": al.get("apprendre_echanges", True),
        "min_chars_reponse": int(al.get("min_chars_reponse", 80)),
        "min_chars_question": int(al.get("min_chars_question", 12)),
        "consolider_apres": int(al.get("consolider_apres", 25)),
        "injecter_dans_prompt": al.get("injecter_dans_prompt", True),
        "max_insights_par_mode": int(al.get("max_insights_par_mode", 80)),
    }


def _charger_by_mode() -> dict:
    return _lire_json(BY_MODE_FILE, {"_schema": "v1", "modes": {}, "meta": {}})


def _sauver_by_mode(data: dict) -> None:
    data.setdefault("meta", {})["derniere_maj"] = datetime.now().isoformat()
    _ecrire_json(BY_MODE_FILE, data)


def _charger_meta() -> dict:
    return _lire_json(META_FILE, {
        "total_echanges": 0,
        "total_insights": 0,
        "derniere_consolidation": "",
        "echanges_depuis_consolidation": 0,
    })


def _sauver_meta(meta: dict) -> None:
    _ecrire_json(META_FILE, meta)


def _extraire_insights(question: str, reponse: str) -> list[dict[str, str]]:
    insights: list[dict[str, str]] = []
    q, r = question or "", reponse or ""

    for pat in _PATTERNS_PREFERENCE:
        for m in pat.finditer(q):
            insights.append({"type": "preference", "texte": m.group(1).strip()[:200]})
    for pat in _PATTERNS_FAIT:
        for m in pat.finditer(q):
            insights.append({"type": "fait", "texte": m.group(1).strip()[:200]})
    for pat in _PATTERNS_TECHNIQUE:
        for m in pat.finditer(r):
            code = m.group(1).strip()
            if len(code) >= 20:
                insights.append({"type": "technique", "texte": code[:1500]})

    if len(r) > 200 and any(k in q.lower() for k in ("comment", "pourquoi", "explique")):
        resume = re.sub(r"\s+", " ", r)[:400]
        insights.append({"type": "enseignement", "texte": f"Q: {q[:100]} → {resume}"})

    if any(k in q.lower() for k in ("triste", "stress", "anxiété", "mal", "difficile")):
        insights.append({"type": "emotion", "texte": q[:250]})

    if any(k in q.lower() for k in ("orchid", "phalaenopsis", "puceron")):
        insights.append({"type": "personnel", "texte": q[:200]})

    seen = set()
    uniques = []
    for ins in insights:
        key = (ins["type"], ins["texte"][:80].lower())
        if key not in seen and len(ins["texte"]) >= 8:
            seen.add(key)
            uniques.append(ins)
    return uniques[:8]


def _ajouter_insight_mode(mode: str, insight: dict[str, str], source: str = "echange") -> bool:
    cfg = _config_apprentissage()
    data = _charger_by_mode()
    modes = data.setdefault("modes", {})
    bucket = modes.setdefault(mode, {"insights": [], "stats": {"count": 0}})

    texte = insight.get("texte", "").strip()
    if not texte:
        return False

    for existing in bucket.get("insights", []):
        if existing.get("texte", "")[:80].lower() == texte[:80].lower():
            existing["utilisations"] = existing.get("utilisations", 0) + 1
            existing["derniere_vue"] = datetime.now().isoformat()
            _sauver_by_mode(data)
            return False

    entry = {
        "id": uuid.uuid4().hex[:10],
        "type": insight.get("type", "general"),
        "texte": texte[:2000],
        "source": source,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "utilisations": 0,
    }
    bucket.setdefault("insights", []).append(entry)
    max_n = cfg["max_insights_par_mode"]
    bucket["insights"] = bucket["insights"][-max_n:]
    bucket.setdefault("stats", {})["count"] = len(bucket["insights"])
    _sauver_by_mode(data)
    
    # --- AGI Transition : Sauvegarde dans Supabase ---
    if inserer_apprentissage:
        try:
            inserer_apprentissage({
                "mode": mode,
                "insight_type": entry["type"],
                "texte": entry["texte"],
                "source": entry["source"]
            })
        except Exception as e:
            print(f"[DB] Erreur insertion apprentissage: {e}")
    # ------------------------------------------------

    return True


def _memoriser_dans_knowledge(
    mode: str,
    insight: dict[str, str],
    question: str,
) -> bool:
    try:
        import knowledge_engine as ke
        ke.init(JARVIS_ROOT)
    except Exception:
        return False

    itype = insight.get("type", "general")
    texte = insight.get("texte", "")
    cat = _MODE_CATEGORIE.get(mode, "process")
    if itype == "technique":
        cat = "code"
    elif itype in ("emotion",):
        cat = "emotion"
    elif itype in ("preference", "personnel"):
        cat = "preference"
    elif itype in ("fait", "relation"):
        cat = "relation"

    sujet = f"[{mode}] {question[:60].strip() or itype}"
    if itype == "technique" and len(texte) > 30:
        r = ke.apprendre_code(sujet, texte, f"Appris en mode {mode}", source=f"auto:{mode}")
    else:
        r = ke.memoriser(sujet, texte, "", categorie=cat, source=f"auto:{mode}")
    return bool(r.get("ok"))


def _sync_preference_profil(insight: dict[str, str]) -> None:
    if insight.get("type") != "preference":
        return
    try:
        from memory_manager import ajouter_memoire
        cle = f"pref_{datetime.now():%Y%m%d}"
        ajouter_memoire(cle, insight.get("texte", "")[:500])
    except Exception:
        pass


def _sync_fait_config(insight: dict[str, str]) -> None:
    if insight.get("type") != "fait":
        return
    try:
        cfg = _lire_json(CONFIG_FILE, {})
        faits = cfg.setdefault("faits_memorises", [])
        texte = insight.get("texte", "")
        if any(texte[:40] in (f.get("fait") or "") for f in faits if isinstance(f, dict)):
            return
        faits.append({"date": datetime.now().strftime("%Y-%m-%d"), "fait": texte[:500]})
        cfg["faits_memorises"] = faits[-50:]
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=4)
    except Exception:
        pass


def apprendre_depuis_echange(
    question: str,
    reponse: str,
    mode: str = "standard",
    intention: str = "",
    humeur: str = "",
) -> dict[str, Any]:
    """Pipeline complet après chaque échange riche."""
    cfg = _config_apprentissage()
    if not cfg["actif"] or not cfg["apprendre_echanges"]:
        return {"ok": False, "raison": "désactivé"}

    q, r = (question or "").strip(), (reponse or "").strip()
    if len(q) < cfg["min_chars_question"] or len(r) < cfg["min_chars_reponse"]:
        return {"ok": False, "raison": "échange trop court"}

    mode = (mode or "standard").lower()
    if mode == "auto":
        mode = "standard"

    insights = _extraire_insights(q, r)
    meta = _charger_meta()
    meta["total_echanges"] = meta.get("total_echanges", 0) + 1
    meta["echanges_depuis_consolidation"] = meta.get("echanges_depuis_consolidation", 0) + 1

    nouveaux = 0
    for ins in insights:
        if _ajouter_insight_mode(mode, ins):
            nouveaux += 1
        _memoriser_dans_knowledge(mode, ins, q)
        _sync_preference_profil(ins)
        _sync_fait_config(ins)

    if intention or humeur:
        _ajouter_insight_mode(
            mode,
            {"type": "contexte", "texte": f"intention={intention}, humeur={humeur}"},
            source="meta",
        )

    meta["total_insights"] = meta.get("total_insights", 0) + nouveaux
    _sauver_meta(meta)

    if meta["echanges_depuis_consolidation"] >= cfg["consolider_apres"]:
        consolider_apprentissages()

    msg = ""
    if nouveaux:
        msg = f"[APPRENTISSAGE] +{nouveaux} insight(s) mode {mode}"
        print(msg)

    return {"ok": True, "nouveaux": nouveaux, "insights": len(insights), "mode": mode}


def consolider_apprentissages() -> str:
    """Fusionne insights proches et pousse vers knowledge_engine."""
    data = _charger_by_mode()
    fusionnes = 0
    try:
        import knowledge_engine as ke
        ke.init(JARVIS_ROOT)
    except Exception:
        ke = None

    for mode, bucket in data.get("modes", {}).items():
        insights = bucket.get("insights") or []
        by_prefix: dict[str, dict] = {}
        for ins in insights:
            key = ins.get("texte", "")[:50].lower()
            if key in by_prefix:
                by_prefix[key]["utilisations"] = by_prefix[key].get("utilisations", 0) + 1
                fusionnes += 1
            else:
                by_prefix[key] = ins
        bucket["insights"] = list(by_prefix.values())[-80:]
        if ke:
            for ins in bucket["insights"]:
                if ins.get("utilisations", 0) >= 2:
                    ke.memoriser(
                        f"[{mode}] {ins.get('type', 'insight')}",
                        ins.get("texte", "")[:2000],
                        categorie=_MODE_CATEGORIE.get(mode, "process"),
                        source=f"consolidation:{mode}",
                    )

    data.setdefault("meta", {})["derniere_consolidation"] = datetime.now().isoformat()
    _sauver_by_mode(data)
    meta = _charger_meta()
    meta["derniere_consolidation"] = datetime.now().isoformat()
    meta["echanges_depuis_consolidation"] = 0
    _sauver_meta(meta)
    return f"Consolidation terminée — {fusionnes} doublons fusionnés."


def injecter_apprentissage_mode(mode: str, requete: str = "", max_chars: int = 2500) -> str:
    """Insights récents du mode pour enrichir le prompt."""
    cfg = _config_apprentissage()
    if not cfg["injecter_dans_prompt"]:
        return ""

    mode = (mode or "standard").lower()
    if mode == "auto":
        mode = "standard"

    data = _charger_by_mode()
    insights = (data.get("modes", {}).get(mode) or {}).get("insights") or []
    if not insights:
        return ""

    mots = set(re.findall(r"[a-zàâäéèêëïîôùûüç0-9]{3,}", (requete or "").lower()))
    scored: list[tuple[int, dict]] = []
    for ins in insights:
        blob = ins.get("texte", "").lower()
        score = sum(1 for m in mots if m in blob) if mots else 1
        score += ins.get("utilisations", 0)
        scored.append((score, ins))
    scored.sort(key=lambda x: -x[0])

    lignes = [f"\n=== APPRENTISSAGES MODE {mode.upper()} (auto) ==="]
    total = 0
    for _, ins in scored[:10]:
        bloc = f"• [{ins.get('type')}] {ins.get('texte', '')[:220]}\n"
        if total + len(bloc) > max_chars:
            break
        lignes.append(bloc)
        total += len(bloc)
    lignes.append("Réutilise ces acquis ; ne les répète pas mot pour mot.\n")
    return "".join(lignes)[:max_chars]


def lister_apprentissages_mode(mode: str = "", limit: int = 15) -> str:
    data = _charger_by_mode()
    if mode:
        modes = {mode: data.get("modes", {}).get(mode, {})}
    else:
        modes = data.get("modes", {})

    if not modes:
        return "Aucun apprentissage par mode enregistré."
    lignes = ["Apprentissages par mode :"]
    for nom, bucket in modes.items():
        ins = (bucket or {}).get("insights") or []
        if not ins:
            continue
        lignes.append(f"\n— {nom.upper()} ({len(ins)}) —")
        for i in ins[-limit:]:
            lignes.append(f"  • [{i.get('type')}] {i.get('texte', '')[:100]}")
    return "\n".join(lignes)


def stats_apprentissage() -> str:
    meta = _charger_meta()
    data = _charger_by_mode()
    total_ins = sum(
        len((b or {}).get("insights") or [])
        for b in data.get("modes", {}).values()
    )
    try:
        import knowledge_engine as ke
        ke.init(JARVIS_ROOT)
        n_kb = ke.compter()
    except Exception:
        n_kb = "?"
    return (
        f"Échanges analysés : {meta.get('total_echanges', 0)} | "
        f"Insights par mode : {total_ins} | Base knowledge : {n_kb} entrées | "
        f"Dernière consolidation : {meta.get('derniere_consolidation') or 'jamais'}"
    )


def executer_action_apprentissage(action: str, data: dict[str, Any]) -> str | None:
    action = (action or "").lower().strip()
    data = data or {}
    if action == "consolider_apprentissage":
        return consolider_apprentissages()
    if action == "lister_apprentissage_mode":
        return lister_apprentissages_mode(data.get("mode", ""))
    if action == "stats_apprentissage":
        return stats_apprentissage()
    if action == "auto_apprendre_echange":
        r = apprendre_depuis_echange(
            data.get("question", ""),
            data.get("reponse", ""),
            data.get("mode", "standard"),
            data.get("intention", ""),
            data.get("humeur", ""),
        )
        return f"Apprentissage : {r.get('nouveaux', 0)} nouveau(x)." if r.get("ok") else r.get("raison", "échec")
    return None
