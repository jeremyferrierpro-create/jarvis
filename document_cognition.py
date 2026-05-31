# -*- coding: utf-8 -*-
"""
Analyse cognitive des documents — extraction structurée et mémoire long terme.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Awaitable, Callable

_jarvis_root = ""
_knowledge_file = ""

SPEC_KEYS = (
    "nom_site", "theme", "objectif", "pages", "stack", "couleurs",
    "fonctionnalites", "public_cible", "contraintes", "references_visuelles",
    "contenu_cles", "seo", "accessibilite",
)

CATEGORIE_TO_MODE = {
    "prive": "personnel",
    "travail": "professionnel",
    "apprentissage": "apprentissage",
    "amitie": "ami",
    "dev": "dev",
    "briefing": "dev",
    "general": "general",
}


def init(jarvis_root: str) -> None:
    global _jarvis_root, _knowledge_file
    _jarvis_root = jarvis_root
    _knowledge_file = os.path.join(jarvis_root, "jarvis_project_knowledge.json")
    os.makedirs(os.path.dirname(_knowledge_file), exist_ok=True)


def _charger() -> dict[str, Any]:
    if not os.path.isfile(_knowledge_file):
        return {"documents": {}, "projets": {}, "projet_actif": None}
    try:
        with open(_knowledge_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("documents", {})
        data.setdefault("projets", {})
        return data
    except Exception:
        return {"documents": {}, "projets": {}, "projet_actif": None}


def _sauver(data: dict[str, Any]) -> None:
    try:
        with open(_knowledge_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[COGNITION] Erreur sauvegarde : {e}")


def _parse_json_reponse(texte: str) -> dict[str, Any]:
    if not texte:
        return {}
    texte = texte.strip()
    start = texte.find("{")
    end = texte.rfind("}")
    if start == -1 or end <= start:
        return {}
    try:
        return json.loads(texte[start : end + 1])
    except json.JSONDecodeError:
        return {}


def memoriser_document(doc_id: str, filename: str, spec: dict[str, Any], resume: str, texte_ref: str = "") -> None:
    data = _charger()
    data["documents"][doc_id] = {
        "filename": filename,
        "date_analyse": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "spec": spec,
        "resume_cognitif": resume[:4000],
        "texte_extrait_ref": texte_ref[:500],
    }
    slug = _slug_from_spec(spec)
    if slug:
        proj = data["projets"].setdefault(slug, {"spec_fusionnee": {}, "document_ids": []})
        if doc_id not in proj["document_ids"]:
            proj["document_ids"].append(doc_id)
        proj["spec_fusionnee"] = fusionner_specs(proj["spec_fusionnee"], spec)
        proj["derniere_maj"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data["projet_actif"] = slug
    _sauver(data)
    print(f"[COGNITION] Mémorisé : {filename} → projet {slug or '?'}")


def fusionner_specs(base: dict[str, Any], nouveau: dict[str, Any]) -> dict[str, Any]:
    out = dict(base or {})
    for k, v in (nouveau or {}).items():
        if v and str(v).strip():
            out[k] = str(v).strip()[:2000]
    return out


def _slug_from_spec(spec: dict[str, Any]) -> str:
    nom = spec.get("nom_site") or spec.get("theme") or ""
    if not nom:
        return ""
    s = re.sub(r"[^a-z0-9]+", "-", nom.lower()).strip("-")
    return s[:48] or "projet"


def get_spec_projet_actif() -> dict[str, Any]:
    data = _charger()
    slug = data.get("projet_actif")
    if slug and slug in data.get("projets", {}):
        return data["projets"][slug].get("spec_fusionnee", {})
    return {}


def contexte_memoire_projet(max_chars: int = 12000) -> str:
    data = _charger()
    parts = ["\n=== MÉMOIRE LONG TERME PROJET WEB (jarvis_project_knowledge.json) ===\n"]
    total = len(parts[0])

    spec = get_spec_projet_actif()
    if spec:
        bloc = "SPÉCIFICATION FUSIONNÉE DU PROJET ACTIF :\n"
        for k in SPEC_KEYS:
            if spec.get(k):
                bloc += f"- {k}: {spec[k]}\n"
        parts.append(bloc)
        total += len(bloc)

    for doc_id, doc in list(data.get("documents", {}).items())[-6:]:
        bloc = (
            f"\n--- Doc mémorisé : {doc.get('filename')} ({doc.get('date_analyse')}) ---\n"
            f"{doc.get('resume_cognitif', '')}\n"
        )
        if doc.get("spec"):
            for k, v in doc["spec"].items():
                if v:
                    bloc += f"  [{k}] {str(v)[:300]}\n"
        if total + len(bloc) > max_chars:
            break
        parts.append(bloc)
        total += len(bloc)

    if len(parts) == 1:
        return ""
    parts.append("\nCes données sont la source de vérité — respecte-les pour le développement.\n")
    return "".join(parts)[:max_chars]


def spec_vers_briefing(spec: dict[str, Any]) -> dict[str, str]:
    """Mappe une spec cognitive vers les champs briefing site_dev."""
    mapping = {}
    for k in SPEC_KEYS:
        if k in ("public_cible", "contraintes", "references_visuelles", "contenu_cles", "seo", "accessibilite"):
            continue
        if spec.get(k):
            mapping[k if k in ("nom_site", "theme", "objectif", "pages", "stack", "couleurs", "fonctionnalites") else k] = str(spec[k])
    extras = []
    for k in ("public_cible", "contraintes", "contenu_cles", "references_visuelles"):
        if spec.get(k):
            extras.append(f"{k}: {spec[k]}")
    if extras:
        mapping["fonctionnalites"] = (mapping.get("fonctionnalites", "") + " | " + " | ".join(extras)).strip(" |")
    return mapping


PROMPT_ANALYSE = """Tu es un développeur web fullstack senior. Analyse ce document pour en extraire
TOUTES les informations utiles à la création d'un site web.

Réponds UNIQUEMENT avec un objet JSON valide (pas de markdown) :
{
  "nom_site": "",
  "theme": "",
  "objectif": "",
  "pages": "liste des pages séparées par des virgules",
  "stack": "HTML/CSS/JS, PHP, React, etc.",
  "couleurs": "charte graphique, couleurs hex si présentes",
  "fonctionnalites": "menu, formulaire, galerie, API, etc.",
  "public_cible": "",
  "contraintes": "",
  "references_visuelles": "maquettes, inspirations",
  "contenu_cles": "textes, sections importantes à reprendre",
  "seo": "",
  "accessibilite": "",
  "resume_executif": "synthèse en 5 phrases pour un dev",
  "elements_ui": "description layout, header, footer, sidebar",
  "donnees_manquantes": "ce qu'il faudrait encore demander au client"
}

Document : {filename}
---
{texte}
"""

PROMPT_CLASSIFICATION = """Analyse ce document et classifie-le dans UNE seule catégorie.

Catégories possibles :
- "prive" : document personnel (factures, santé, administratif, identité, famille)
- "travail" : document professionnel (contrats, clients, facturation, gestion, RH)
- "apprentissage" : cours, tutoriels, documentation technique, notes d'étude, formations
- "amitie" : messages personnels, photos souvenirs, événements sociaux, loisirs
- "dev" : code source, logs, configuration, fichiers techniques, debug
- "briefing" : brief client, maquettes, cahier des charges, spécifications de projet web

Réponds UNIQUEMENT avec un objet JSON valide (pas de markdown) :
{{
  "categorie": "...",
  "confiance": 0.85,
  "raison": "explication courte de pourquoi cette catégorie"
}}

Fichier : {filename}
Extrait :
{texte}
"""

PROMPT_ANALYSE_GENERAL = """Tu es un assistant intelligent. Analyse ce document et extrais les informations clés.

Réponds UNIQUEMENT avec un objet JSON valide (pas de markdown) :
{{
  "sujet": "",
  "resume_executif": "synthèse en 5 phrases",
  "points_cles": ["..."],
  "dates_importantes": ["..."],
  "personnes_mentionnees": ["..."],
  "actions_requises": ["..."],
  "donnees_sensibles": false
}}

Document : {filename}
---
{texte}
"""


async def classifier_document(
    doc: dict[str, Any],
    llm_fn: Callable[[str], Awaitable[str | None]],
) -> dict[str, Any]:
    """Classifie un document via LLM — retourne {categorie, confiance, raison}."""
    texte = doc.get("texte") or doc.get("resume") or ""
    if len(texte.strip()) < 15:
        return {"categorie": "general", "confiance": 0.5, "raison": "texte trop court"}

    prompt = PROMPT_CLASSIFICATION.format(
        filename=doc.get("filename", "document"),
        texte=texte[:3000],
    )
    try:
        rep = await llm_fn(prompt)
        if not rep:
            return {"categorie": "general", "confiance": 0.3, "raison": "pas de réponse LLM"}
        result = _parse_json_reponse(rep)
        if not result or "categorie" not in result:
            return {"categorie": "general", "confiance": 0.3, "raison": "réponse non parsable"}
        # Valider la catégorie
        cats_valides = ("prive", "travail", "apprentissage", "amitie", "dev", "briefing")
        cat = result.get("categorie", "general").lower().strip()
        if cat not in cats_valides:
            cat = "general"
        conf = min(1.0, max(0.0, float(result.get("confiance", 0.5))))
        return {
            "categorie": cat,
            "confiance": round(conf, 2),
            "raison": str(result.get("raison", ""))[:200],
        }
    except Exception as e:
        print(f"[COGNITION] Erreur classification : {e}")
        return {"categorie": "general", "confiance": 0.3, "raison": str(e)[:100]}


async def analyser_document_cognitif(
    doc: dict[str, Any],
    llm_fn: Callable[[str], Awaitable[str | None]],
    categorie: str = "general",
) -> dict[str, Any]:
    """Appelle le LLM pour extraire une spec structurée."""
    texte = doc.get("texte") or doc.get("resume") or ""
    if len(texte.strip()) < 20:
        return {}

    prompt_to_use = PROMPT_ANALYSE if categorie in ("dev", "briefing") else PROMPT_ANALYSE_GENERAL
    prompt = prompt_to_use.format(
        filename=doc.get("filename", "document"),
        texte=texte[:18000],
    )
    try:
        rep = await llm_fn(prompt)
        if not rep:
            return {}
        spec = _parse_json_reponse(rep)
        if not spec:
            return {"resume_executif": rep[:2000]}
        return spec
    except Exception as e:
        print(f"[COGNITION] Erreur LLM : {e}")
        return {}


async def analyser_et_memoriser(
    doc: dict[str, Any],
    llm_fn: Callable[[str], Awaitable[str | None]],
    sauver_learning_fn: Callable[[str, str, str], str] | None = None,
    categorie: str = "general",
) -> dict[str, Any]:
    """Pipeline complet : analyse LLM + mémoire long terme + base apprentissage."""
    spec = await analyser_document_cognitif(doc, llm_fn, categorie)
    if not spec:
        return {}

    resume = spec.get("resume_executif") or spec.get("resume") or json.dumps(spec, ensure_ascii=False)[:1500]
    doc_id = doc.get("id") or doc.get("filename", "doc")
    memoriser_document(doc_id, doc.get("filename", ""), spec, resume, texte_ref=doc.get("texte", "")[:200])

    if sauver_learning_fn:
        sujet = f"projet web — {spec.get('nom_site') or spec.get('theme') or doc.get('filename')}"
        desc = resume + "\n\nSpec:\n" + json.dumps(
            {k: spec[k] for k in SPEC_KEYS if spec.get(k)}, ensure_ascii=False, indent=2
        )[:2500]
        try:
            sauver_learning_fn(sujet[:120], desc, "")
        except Exception:
            pass

    return spec


def lister_fichiers_dossier_uploads() -> list[str]:
    try:
        import document_ingest as di
        d = di.get_uploads_dir()
    except Exception:
        d = os.path.join(_jarvis_root, "jarvis_uploads")
    if not os.path.isdir(d):
        return []
    fichiers = []
    for name in os.listdir(d):
        if name.startswith("_") or name.endswith(".json"):
            continue
        path = os.path.join(d, name)
        if os.path.isfile(path):
            fichiers.append(path)
    return sorted(fichiers, key=os.path.getmtime, reverse=True)


def synchroniser_dossier_uploads(context: str = "briefing") -> tuple[int, list[dict[str, Any]]]:
    """
    Indexe les fichiers présents dans jarvis_uploads/ non encore dans l'index.
    Retourne (nb_nouveaux, liste_docs).
    """
    try:
        import document_ingest as di
    except ImportError:
        return 0, []

    paths = lister_fichiers_dossier_uploads()
    index_paths = {d.get("stored_path") for d in di.lister_documents()}
    nouveaux = []
    for path in paths:
        if path in index_paths:
            continue
        try:
            with open(path, "rb") as f:
                raw = f.read()
            name = re.sub(r"^\d{8}_\d{6}_[a-f0-9]{8}_", "", os.path.basename(path))
            r = di.enregistrer_document(name, raw, context, note="scan_dossier")
            if r.get("ok"):
                nouveaux.append(r["document"])
        except Exception as e:
            print(f"[COGNITION] Scan échec {path}: {e}")
    return len(nouveaux), nouveaux
