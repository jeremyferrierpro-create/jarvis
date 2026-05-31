# -*- coding: utf-8 -*-
"""
Agent création de site web A→Z pour JARVIS.
- Briefing interactif (questions / réponses)
- Indexation des cours Desktop/FORMATION
- Prompt de développement autonome
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from datetime import datetime
from typing import Any

try:
    from web_dev_engine import (
        PROMPT_SENIOR_FULLSTACK,
        auditer_projet,
        detecter_stack,
        formater_rapport_audit,
        scaffold_projet,
    )
except ImportError:
    PROMPT_SENIOR_FULLSTACK = ""
    auditer_projet = None
    detecter_stack = lambda t: "static"
    formater_rapport_audit = lambda a: str(a)
    scaffold_projet = None

try:
    import jarvis_capabilities
except ImportError:
    jarvis_capabilities = None


FORMATION_DEFAULT = os.path.join(os.path.expanduser("~"), "Desktop", "FORMATION")
BRIEFING_FILENAME = "_jarvis_site_briefing.json"

# Extensions utiles pour s'inspirer des cours
_FORMATION_EXTS = {".html", ".css", ".js", ".php", ".md", ".txt", ".json"}
_FORMATION_SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv", "dist", ".next",
    ".vscode", "vendor",
}
_MAX_FORMATION_CHARS = 12000

QUESTIONS_BRIEFING = [
    {
        "id": "nom_site",
        "question": (
            "Quel est le nom du site ? "
            "Par exemple : Mes Orchidées, Agri-Connect…"
        ),
        "required": True,
    },
    {
        "id": "theme",
        "question": (
            "Quel est le thème ou le sujet principal ? "
            "Décrivez en une ou deux phrases."
        ),
        "required": True,
    },
    {
        "id": "objectif",
        "question": (
            "Quel est l'objectif du site ? "
            "Vitrine, blog, e-commerce, encyclopédie, portfolio…"
        ),
        "required": True,
    },
    {
        "id": "pages",
        "question": (
            "Quelles pages voulez-vous ? "
            "Par exemple : accueil, à propos, contact, galerie, encyclopédie…"
        ),
        "required": True,
    },
    {
        "id": "stack",
        "question": (
            "Quelle technologie préférez-vous ? "
            "HTML et CSS seuls, HTML CSS JavaScript, ou PHP comme dans votre fil rouge orchidées ?"
        ),
        "required": True,
    },
    {
        "id": "couleurs",
        "question": (
            "Quelles couleurs ou ambiance visuelle ? "
            "Par exemple : vert nature, élégant bordeaux et or, minimaliste…"
        ),
        "required": True,
    },
    {
        "id": "fonctionnalites",
        "question": (
            "Des fonctionnalités particulières ? "
            "Menu latéral, formulaire de contact, recherche, galerie photos…"
        ),
        "required": False,
    },
    {
        "id": "reference",
        "question": (
            "Un site ou projet de référence dans vos cours ? "
            "Dites fil rouge orchidées, mes_orchidees1, ou aucun."
        ),
        "required": False,
    },
]

_MOTS_DEMARRAGE_SITE = (
    "crée un site", "creer un site", "créer un site", "crée le site",
    "faire un site", "fait un site", "fabrique un site", "génère un site",
    "genere un site", "nouveau site web", "créer un site web",
    "creer un site web", "développe un site", "developpe un site",
)

_MOTS_LANCER_DEV = (
    "c'est bon", "cest bon", "lance le développement", "lance le developpement",
    "tu peux développer", "tu peux developper", "commence le site",
    "vas-y développe", "vas y developpe", "génère le site", "genere le site",
    "ok développe", "ok developpe", "lance la création",
)

_MOTS_SCAN_DOCS = (
    "scanne les documents", "scan les documents", "analyse les documents",
    "analyse les uploads", "scanne le dossier", "documents prêts", "documents prets",
    "j'ai ajouté", "j ai ajoute", "voici les documents", "fichiers ajoutés",
    "importe les documents", "relis les documents",
)

_MOTS_PASSER_COLLECTE = (
    "pas de document", "sans document", "continue sans", "passe aux questions",
    "pas de cahier", "on avance", "questions directement",
)

_MOTS_ANNULER = (
    "annule le site", "annule le projet", "stop le site", "abandonne le site",
)

DOCUMENTS_SENIOR_CHECKLIST = (
    "Cahier des charges ou specifications (PDF, Word, HTML)",
    "Maquettes ou captures d'ecran (PNG, JPG)",
    "Charte graphique ou liste de couleurs",
    "Liste des pages et du contenu",
    "Reference technique (HTML, PHP, React…)",
)

_briefing_state: dict[str, Any] | None = None
_jarvis_root: str = ""
_formation_path: str = FORMATION_DEFAULT


def _processus(etape_id: str, statut: str = "done") -> None:
    try:
        import knowledge_engine as ke
        ke.init(_jarvis_root)
        if etape_id == "collecte_documents" and statut == "in_progress":
            ke.demarrer_processus("creation_site")
        ke.marquer_etape(etape_id, statut)
    except Exception:
        pass


def init(jarvis_root: str, formation_path: str | None = None) -> None:
    global _jarvis_root, _formation_path
    _jarvis_root = jarvis_root
    if formation_path and os.path.isdir(formation_path):
        _formation_path = formation_path
    elif os.path.isdir(FORMATION_DEFAULT):
        _formation_path = FORMATION_DEFAULT
    else:
        _formation_path = formation_path or FORMATION_DEFAULT
    _charger_briefing_persiste()


def _briefing_path() -> str:
    d = os.path.join(_jarvis_root, "projects", "sites")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, BRIEFING_FILENAME)


def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return text[:48] or "mon-site"


def _charger_briefing_persiste() -> None:
    global _briefing_state
    path = _briefing_path()
    if not os.path.isfile(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("phase") == "briefing" or data.get("phase") == "collecte_documents":
            _briefing_state = data
    except Exception:
        pass


def _sauvegarder_briefing() -> None:
    if not _briefing_state:
        return
    try:
        with open(_briefing_path(), "w", encoding="utf-8") as f:
            json.dump(_briefing_state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _effacer_briefing_persiste() -> None:
    path = _briefing_path()
    if os.path.isfile(path):
        try:
            os.remove(path)
        except Exception:
            pass


def detecter_demande_site(texte: str) -> bool:
    t = (texte or "").lower()
    return any(m in t for m in _MOTS_DEMARRAGE_SITE) or (
        "site web" in t and any(v in t for v in ("crée", "creer", "créer", "faire", "nouveau", "développe"))
    )


def collecte_documents_active() -> bool:
    return bool(_briefing_state and _briefing_state.get("phase") == "collecte_documents")


def briefing_actif() -> bool:
    return bool(
        _briefing_state
        and _briefing_state.get("phase") in ("collecte_documents", "briefing")
    )


def en_developpement_site() -> bool:
    return bool(_briefing_state and _briefing_state.get("phase") == "building")


def get_session_timeout() -> float:
    if briefing_actif() or collecte_documents_active():
        return 300.0
    if en_developpement_site():
        return 180.0
    return 30.0


def get_max_react_depth() -> int:
    if en_developpement_site() or (_briefing_state and _briefing_state.get("phase") in ("building", "ready")):
        return 50
    return 5


def _appliquer_spec_aux_reponses(spec: dict[str, Any]) -> list[str]:
    """Fusionne une spec cognitive dans answers. Retourne clés remplies."""
    if not _briefing_state or not spec:
        return []
    try:
        from document_cognition import spec_vers_briefing
        mapped = spec_vers_briefing(spec)
    except ImportError:
        mapped = {k: str(v) for k, v in spec.items() if k in ("nom_site", "theme", "objectif", "pages", "stack", "couleurs", "fonctionnalites") and v}
    remplis = []
    for k, v in mapped.items():
        if v and not (_briefing_state.get("answers") or {}).get(k):
            _briefing_state.setdefault("answers", {})[k] = v[:500]
            remplis.append(k)
    if spec.get("resume_executif"):
        _briefing_state.setdefault("cognitive", {})["resume"] = spec["resume_executif"][:2000]
    if spec.get("donnees_manquantes"):
        _briefing_state.setdefault("cognitive", {})["manquant"] = spec["donnees_manquantes"][:1000]
    _sauvegarder_briefing()
    return remplis


def _questions_restantes() -> list[dict]:
    """Questions briefing non encore couvertes par answers ou documents."""
    if not _briefing_state:
        return list(QUESTIONS_BRIEFING)
    ans = _briefing_state.get("answers", {})
    return [q for q in QUESTIONS_BRIEFING if q["required"] and not (ans.get(q["id"]) or "").strip()]


def _message_collecte_documents(nb_docs: int, nb_importes: int = 0) -> str:
    checklist = " ".join(f"{i+1}. {item}." for i, item in enumerate(DOCUMENTS_SENIOR_CHECKLIST))
    msg = (
        "En tant que developpeur fullstack senior, j'ai besoin de documents avant de coder. "
        f"Placez vos fichiers dans jarvis_uploads ou utilisez le bouton DOCS. "
        f"Documents attendus : {checklist} "
    )
    if nb_importes:
        msg += f"J'ai importe {nb_importes} nouveau(x) fichier(s) du dossier. "
    if nb_docs:
        msg += f"J'ai {nb_docs} document(s) disponible(s). Dites scanne les documents pour analyse cognitive, "
        msg += "ou continue sans document pour repondre aux questions oralement."
    else:
        msg += "Aucun document pour l'instant. Ajoutez un cahier des charges puis dites scanne les documents."
    return msg


def synchroniser_et_analyser_documents_sync() -> tuple[int, int, list[dict[str, Any]]]:
    """Scan disque + retourne (total_docs, nb_importes, docs)."""
    importes = []
    try:
        import document_ingest as di
        importes = di.synchroniser_fichiers_disque("briefing")
        total = len(di.lister_documents())
    except ImportError:
        total = 0
    return total, len(importes), importes


def demarrer_briefing(texte_initial: str = "") -> str:
    global _briefing_state
    total, nb_imp, _ = synchroniser_et_analyser_documents_sync()
    _processus("collecte_documents", "in_progress")

    _briefing_state = {
        "phase": "collecte_documents",
        "question_index": 0,
        "answers": {},
        "documents": [],
        "started": datetime.now().isoformat(),
        "texte_initial": texte_initial[:500],
    }
    if texte_initial:
        for hint in ("sur les ", "sur la ", "sur le ", "à propos de ", "a propos de "):
            if hint in texte_initial.lower():
                part = texte_initial.lower().split(hint, 1)[-1].strip()
                if len(part) > 3:
                    _briefing_state["answers"]["theme"] = part[:200]
                break

    try:
        from document_cognition import get_spec_projet_actif, spec_vers_briefing
        spec = get_spec_projet_actif()
        if spec:
            _appliquer_spec_aux_reponses(spec)
    except ImportError:
        pass

    _sauvegarder_briefing()
    intro = (
        "Tres bien, je prends en charge votre site web de A a Z, comme un dev senior. "
        "Commencons par la collecte documentaire — c'est la base d'un projet reussi. "
    )
    if _briefing_state["answers"].get("theme"):
        intro += f"Theme note : {_briefing_state['answers']['theme']}. "
    return intro + _message_collecte_documents(total, nb_imp)


def passer_a_questions_briefing() -> str:
    """Passe de la collecte aux questions (seulement celles manquantes)."""
    global _briefing_state
    if not _briefing_state:
        return ""
    _processus("collecte_documents", "done")
    _processus("briefing", "in_progress")
    _briefing_state["phase"] = "briefing"
    restantes = _questions_restantes()
    if not restantes:
        _briefing_state["phase"] = "ready"
        _processus("briefing", "done")
        _sauvegarder_briefing()
        return (
            "Le briefing est complet grace aux documents et reponses. "
            "Dites lance le developpement pour que je code le site."
        )
    _briefing_state["question_index"] = QUESTIONS_BRIEFING.index(restantes[0])
    _sauvegarder_briefing()
    return (
        "Passons aux precisions restantes. "
        + restantes[0]["question"]
    )


def annuler_briefing() -> str:
    global _briefing_state
    _briefing_state = None
    _effacer_briefing_persiste()
    return "Projet de site web annulé. Dites-moi quand vous voulez recommencer."


def pret_a_developper() -> bool:
    return bool(_briefing_state and _briefing_state.get("phase") == "ready")


def _question_courante() -> dict | None:
    if not _briefing_state or _briefing_state.get("phase") != "briefing":
        return None
    idx = _briefing_state.get("question_index", 0)
    if idx >= len(QUESTIONS_BRIEFING):
        return None
    return QUESTIONS_BRIEFING[idx]


def _avancer_questions() -> str | None:
    """Passe à la question suivante. Retourne la prochaine question ou None si terminé."""
    assert _briefing_state is not None
    _briefing_state["question_index"] = _briefing_state.get("question_index", 0) + 1
    _sauvegarder_briefing()
    q = _question_courante()
    if q:
        return q["question"]
    _briefing_state["phase"] = "ready"
    _sauvegarder_briefing()
    return None


def _reponses_obligatoires_completes() -> bool:
    if not _briefing_state:
        return False
    ans = _briefing_state.get("answers", {})
    for q in QUESTIONS_BRIEFING:
        if q["required"] and not (ans.get(q["id"]) or "").strip():
            return False
    return True


def questions_restantes() -> list[dict]:
    return _questions_restantes()


def fusionner_spec_cognitive(spec: dict[str, Any], doc: dict[str, Any] | None = None) -> list[str]:
    """Applique spec LLM au briefing + intègre le doc."""
    remplis = _appliquer_spec_aux_reponses(spec)
    if doc:
        integrer_document_briefing(doc)
        if spec.get("resume_executif") and doc.get("id"):
            doc = dict(doc)
            doc["resume"] = spec["resume_executif"]
    return remplis


def traiter_reponse_briefing(texte: str) -> tuple[bool, str, bool]:
    """
    Retourne (handled, message_vocal, declencher_developpement).
    """
    global _briefing_state
    t = (texte or "").strip()
    tl = t.lower()

    if any(m in tl for m in _MOTS_ANNULER):
        return True, annuler_briefing(), False

    if not briefing_actif() and not pret_a_developper():
        return False, "", False

    # Phase collecte documents (senior dev)
    if collecte_documents_active():
        if any(m in tl for m in _MOTS_PASSER_COLLECTE):
            return True, passer_a_questions_briefing(), False
        if any(m in tl for m in _MOTS_SCAN_DOCS):
            total, nb_imp, _ = synchroniser_et_analyser_documents_sync()
            return (
                True,
                f"J'ai synchronise jarvis_uploads : {total} document(s) indexe(s). "
                "L'analyse cognitive est en cours ou deja faite. "
                + _message_collecte_documents(total, nb_imp),
                False,
            )
        return (
            True,
            "Phase collecte documentaire. Deposez vos fichiers dans jarvis_uploads ou DOCS, "
            "puis dites scanne les documents. Ou dites continue sans document.",
            False,
        )

    if any(m in tl for m in _MOTS_LANCER_DEV):
        manquantes = _questions_restantes()
        if manquantes:
            labels = [q["id"] for q in manquantes]
            return (
                True,
                "Il me manque encore : "
                + ", ".join(labels)
                + ". Repondez ou televersez un document dans jarvis_uploads.",
                False,
            )
        _briefing_state["phase"] = "ready"
        _sauvegarder_briefing()
        return (
            True,
            "Parfait, j'ai tout ce qu'il me faut. Je commence le développement du site maintenant.",
            True,
        )

    if pret_a_developper():
        return False, "", True

    q = _question_courante()
    if not q:
        _briefing_state["phase"] = "ready"
        _sauvegarder_briefing()
        return True, "Briefing terminé. Je lance le développement.", True

    # Enregistrer la réponse à la question courante
    if t:
        _briefing_state.setdefault("answers", {})[q["id"]] = t[:500]
        _sauvegarder_briefing()

    suivante = _avancer_questions()
    if suivante:
        accuse = f"Noté pour {q['id'].replace('_', ' ')}. "
        return True, accuse + suivante, False

    recap = (
        "Merci, le briefing est complet. "
        "Dites « lance le développement » pour que je crée l'arborescence et tous les fichiers, "
        "ou précisez un dernier détail."
    )
    return True, recap, False


def _lister_fichiers_formation() -> list[dict[str, str]]:
    fichiers = []
    if not os.path.isdir(_formation_path):
        return fichiers
    for root, dirs, files in os.walk(_formation_path):
        dirs[:] = [d for d in dirs if d not in _FORMATION_SKIP_DIRS]
        for name in files:
            ext = os.path.splitext(name)[1].lower()
            if ext not in _FORMATION_EXTS:
                continue
            full = os.path.join(root, name)
            try:
                if os.path.getsize(full) > 120_000:
                    continue
            except OSError:
                continue
            rel = os.path.relpath(full, _formation_path)
            fichiers.append({"path": rel, "full": full, "ext": ext})
    return fichiers


def _score_fichier(rel_path: str, mots_cles: list[str]) -> int:
    p = rel_path.lower()
    score = 0
    for m in mots_cles:
        if m and m in p:
            score += 3
    if "fil rouge" in p or "fil_rouge" in p:
        score += 2
    if "orchide" in p:
        score += 2
    if "html_css" in p or "modules" in p:
        score += 1
    return score


def extraire_contexte_formation(theme: str, stack: str = "", reference: str = "") -> str:
    """Extrait des extraits des cours FORMATION pertinents pour le prompt."""
    if not os.path.isdir(_formation_path):
        return f"(Dossier FORMATION introuvable : {_formation_path})"

    mots = re.findall(r"[a-zàâäéèêëïîôùûüç0-9]{3,}", (theme + " " + stack + " " + reference).lower())
    mots_cles = list(dict.fromkeys(mots))[:15]

    if reference:
        ref_l = reference.lower()
        if "orchid" in ref_l or "fil rouge" in ref_l:
            mots_cles.extend(["orchide", "mes_orchidees", "mon_orchidee", "fil rouge"])

    fichiers = _lister_fichiers_formation()
    fichiers.sort(key=lambda f: _score_fichier(f["path"], mots_cles), reverse=True)

    parties = [
        f"=== COURS FORMATION ({_formation_path}) ===\n",
        "Utilise ces conventions (structure HTML, assets/css, sidebar, accessibilité) pour le nouveau site.\n",
    ]
    total = 0
    for f in fichiers[:12]:
        if total >= _MAX_FORMATION_CHARS:
            break
        try:
            with open(f["full"], "r", encoding="utf-8", errors="replace") as fp:
                contenu = fp.read()
        except Exception:
            continue
        if f["ext"] == ".html":
            contenu = contenu[:3500]
        elif f["ext"] == ".css":
            contenu = contenu[:2000]
        else:
            contenu = contenu[:1500]
        bloc = f"\n--- Référence cours : {f['path']} ---\n{contenu}\n"
        if total + len(bloc) > _MAX_FORMATION_CHARS:
            bloc = bloc[: _MAX_FORMATION_CHARS - total]
        parties.append(bloc)
        total += len(bloc)

    modules = set()
    for f in fichiers:
        parts = f["path"].replace("\\", "/").split("/")
        if len(parts) > 1:
            modules.add(parts[0])
    if modules:
        parties.insert(1, "Modules indexés : " + ", ".join(sorted(modules)[:20]) + "\n")

    return "".join(parties) if len(parties) > 1 else "(Aucun extrait de cours chargé.)"


def chemin_projet_site() -> str:
    ans = (_briefing_state or {}).get("answers", {})
    nom = ans.get("nom_site") or ans.get("theme") or "mon-site"
    slug = _slugify(nom)
    return os.path.join("projects", "sites", slug)


def scaffolder_projet_garanti() -> tuple[str, list[str]]:
    """Crée le scaffold senior avant l'IA. Retourne (chemin_rel, fichiers_créés)."""
    if not _briefing_state or not scaffold_projet:
        return "", []
    ans = _briefing_state.get("answers", {})
    chemin_rel = chemin_projet_site()
    chemin_abs = os.path.join(_jarvis_root, chemin_rel.replace("/", os.sep))
    stack_text = " ".join(str(v) for v in ans.values())
    stack = detecter_stack(stack_text + " " + ans.get("stack", ""))
    _briefing_state["stack"] = stack
    fichiers = scaffold_projet(chemin_abs, stack, ans)
    audit = auditer_projet(chemin_abs, stack) if auditer_projet else {"ok": True}
    print(f"[SCAFFOLD] Stack {stack} — {len(fichiers)} fichiers — audit OK={audit.get('ok')}")
    return chemin_rel, fichiers


def construire_prompt_developpement() -> str:
    """Prompt envoyé au LLM pour enrichir le scaffold senior."""
    global _briefing_state
    if not _briefing_state:
        return ""

    ans = _briefing_state.get("answers", {})
    chemin_rel, fichiers_scaffold = scaffolder_projet_garanti()
    _processus("briefing", "done")
    _processus("scaffold", "done")
    _processus("developpement", "in_progress")
    _briefing_state["phase"] = "building"
    _briefing_state["chemin_projet"] = chemin_rel
    _sauvegarder_briefing()

    formation_ctx = extraire_contexte_formation(
        ans.get("theme", ""),
        ans.get("stack", ""),
        ans.get("reference", ""),
    )

    pages = ans.get("pages", "accueil, contact")
    stack = _briefing_state.get("stack", detecter_stack(ans.get("stack", "")))
    liste_f = "\n".join(f"- {f}" for f in fichiers_scaffold) if fichiers_scaffold else "(aucun)"

    connaissances = ""
    try:
        import knowledge_engine as ke
        ke.init(_jarvis_root)
        connaissances = ke.injecter_pour_tache(
            f"{ans.get('theme', '')} {stack} {pages}", max_chars=6000
        )
    except Exception:
        pass

    return (
        f"[CREATION SITE WEB A→Z — FULLSTACK SENIOR — MODE AUTONOME]\n"
        f"{PROMPT_SENIOR_FULLSTACK}\n\n"
        f"Un SCAFFOLD PROFESSIONNEL est déjà créé sans erreur dans {chemin_rel}/\n"
        f"Fichiers générés :\n{liste_f}\n\n"
        f"BRIEFING :\n"
        f"- Nom : {ans.get('nom_site', '')}\n"
        f"- Thème : {ans.get('theme', '')}\n"
        f"- Objectif : {ans.get('objectif', '')}\n"
        f"- Pages : {pages}\n"
        f"- Stack : {stack}\n"
        f"- Couleurs : {ans.get('couleurs', '')}\n"
        f"- Fonctionnalités : {ans.get('fonctionnalites', 'standard')}\n\n"
        f"SOURCE DE VERITE : jarvis_uploads/ + jarvis_project_knowledge.json — respecte le contenu extrait.\n\n"
        f"TA MISSION : PERSONNALISER et COMPLÉTER le scaffold (pas le recréer from scratch).\n"
        f"1. webdev_lire_fichier index.html et assets/css/style.css\n"
        f"2. webdev_ecrire_fichier avec contenu RICHE adapté au thème ({ans.get('theme', '')})\n"
        f"3. Enrichir CHAQUE page ({pages}) avec vrai contenu métier\n"
        f"4. CSS minimum 400 caractères, design cohérent avec {ans.get('couleurs', '')}\n"
        f"5. Si React/Node/FastAPI : webdev_executer_commande npm install ou pip install\n"
        f"6. webdev_valider_projet — corriger TOUTES les erreurs jusqu'à OK\n\n"
        f"{formation_ctx}\n\n"
        f"{extraire_contexte_documents_briefing()}\n\n"
        f"{connaissances}\n\n"
        f"EXÉCUTE webdev_* maintenant. Zéro placeholder. Zéro erreur de validation."
    )


def integrer_document_briefing(doc: dict[str, Any]) -> list[str]:
    """Fusionne un document dans le briefing actif. Retourne les champs pré-remplis."""
    if not _briefing_state:
        return []
    _briefing_state.setdefault("documents", []).append(
        {
            "id": doc.get("id"),
            "filename": doc.get("filename"),
            "resume": doc.get("resume", "")[:500],
            "texte": doc.get("texte", "")[:MAX_TEXT_PROMPT if False else 8000],
        }
    )
    remplis = []
    for key, val in (doc.get("champs_briefing") or {}).items():
        if val and not (_briefing_state.get("answers") or {}).get(key):
            _briefing_state.setdefault("answers", {})[key] = val
            remplis.append(key)
    _sauvegarder_briefing()
    return remplis


def extraire_contexte_documents_briefing() -> str:
    parts = []
    try:
        from document_cognition import contexte_memoire_projet
        mem = contexte_memoire_projet()
        if mem:
            parts.append(mem)
    except ImportError:
        pass
    try:
        import document_ingest as di
        ctx = di.contexte_pour_prompt("briefing") or di.contexte_pour_prompt(None)
        if ctx:
            parts.append(ctx)
    except ImportError:
        pass
    if _briefing_state:
        docs = _briefing_state.get("documents") or []
        cog = _briefing_state.get("cognitive") or {}
        if cog.get("resume"):
            parts.append(f"\n=== SYNTHESE COGNITIVE ===\n{cog['resume']}\n")
        if cog.get("manquant"):
            parts.append(f"\nDonnees encore manquantes : {cog['manquant']}\n")
        for d in docs:
            parts.append(f"\n--- Briefing doc : {d.get('filename')} ---\n{d.get('texte', d.get('resume', ''))[:5000]}\n")
    return "".join(parts)[:16000]


def get_stack_projet() -> str:
    if not _briefing_state:
        return "static"
    return _briefing_state.get("stack", "static")


def get_chemin_projet() -> str:
    if _briefing_state and _briefing_state.get("chemin_projet"):
        return _briefing_state["chemin_projet"]
    return chemin_projet_site()


def terminer_developpement() -> None:
    global _briefing_state
    if _briefing_state:
        _briefing_state["phase"] = "done"
        _briefing_state["finished"] = datetime.now().isoformat()
    _effacer_briefing_persiste()
    _briefing_state = None


def get_briefing_resume() -> str:
    if not _briefing_state:
        return ""
    ans = _briefing_state.get("answers", {})
    lignes = [f"Phase : {_briefing_state.get('phase')}"]
    for k, v in ans.items():
        lignes.append(f"  {k}: {v[:80]}")
    return "\n".join(lignes)
