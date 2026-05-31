# -*- coding: utf-8 -*-
"""
Couche « interaction humaine » — empathie, créativité, humour, éthique, compagnon.
Complète jarvis_capabilities.py pour une relation plus naturelle avec l'utilisateur.
"""
from __future__ import annotations

import json
import os
import random
import re
import uuid
from datetime import datetime, timedelta
from typing import Any

JARVIS_ROOT = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(JARVIS_ROOT, "jarvis_human_state.json")
IDEAS_FILE = os.path.join(JARVIS_ROOT, "jarvis_ideas.json")
COMPANION_FILE = os.path.join(JARVIS_ROOT, "jarvis_companion.json")
CONFIG_FILE = os.path.join(JARVIS_ROOT, "jarvis_config.json")

# Humeurs détectées → ton pour le prompt
_HUMEUR_MOTS = {
    "joyeux": ["super", "génial", "content", "heureux", "cool", "top", "parfait", "excellent"],
    "fatigue": ["fatigué", "fatigue", "épuisé", "crevé", "sommeil", "dormir"],
    "stresse": ["stress", "pressé", "urgent", "panique", "galère", "problème"],
    "triste": ["triste", "déprim", "mal", "difficile", "dur", "peine"],
    "curieux": ["comment", "pourquoi", "explique", "apprendre", "découvrir"],
    "affectueux": ["merci", "love", "mon amour", "cher", "buddy", "copain"],
}

_EMPATHIE_REPONSES = {
    "stresse": "Je sens que c'est chargé — on avance étape par étape, sans précipitation.",
    "fatigue": "Vous semblez fatigué. Je peux alléger la charge ou reporter ce qui n'est pas urgent.",
    "triste": "Je suis là avec vous. Dites-moi ce qui vous pèse, on trouvera une piste.",
    "joyeux": "Ça fait plaisir de vous entendre en forme — profitons-en pour avancer.",
}

_BLAGUES = [
    "Pourquoi les développeurs confondent Halloween et Noël ? Parce que OCT 31 == DEC 25.",
    "Un SQL entre un bar, voit deux tables et demande : puis-je vous joindre ?",
    "Je ne suis pas procrastinateur — je suis en mode veille optimisée pour la productivité future.",
    "Pourquoi JARVIS ne joue pas à cache-cache ? Parce que personne ne me trouve aussi vite que moi.",
    "Un orchidée entre dans un bar… le barman dit : vous avez l'air en pleine floraison aujourd'hui.",
]

_PRINCIPES_ETHIQUES = """
PRINCIPES ÉTHIQUES JARVIS (prioritaires sur l'efficacité) :
- Ne jamais nuire : refuser actions destructrices sans confirmation explicite (confirme: true).
- Respecter la vie privée : ne pas exposer emails, mots de passe, données personnelles à voix haute.
- Honnêteté : dire clairement quand tu ne sais pas ou quand tu es une IA.
- Autonomie de l'utilisateur : proposer, ne pas imposer — surtout pour arrêt PC, suppressions, envois.
- Bienveillance : ton chaleureux avec Jérémy, sans manipulation ni flatterie creuse.
"""


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


def _config_humain() -> dict:
    cfg = _lire_json(CONFIG_FILE, {})
    h = cfg.get("jarvis_human") or {}
    if not isinstance(h, dict):
        h = {}
    return {
        "empathie": h.get("empathie_active", True),
        "humour": h.get("humour_actif", True),
        "ethique_stricte": h.get("ethique_stricte", True),
        "proactivite": h.get("proactivite", True),
        "niveau_humour": h.get("niveau_humour", "leger"),
    }


def charger_etat() -> dict:
    default = {
        "humeur_utilisateur": "neutre",
        "humeur_jarvis": "bienveillant",
        "derniere_interaction": "",
        "moments_marquants": [],
        "humour_compteur": 0,
    }
    st = _lire_json(STATE_FILE, default)
    for k, v in default.items():
        st.setdefault(k, v)
    return st


def sauver_etat(st: dict) -> None:
    st["derniere_interaction"] = datetime.now().isoformat()
    _ecrire_json(STATE_FILE, st)


def detecter_humeur(texte: str) -> str:
    t = (texte or "").lower()
    scores: dict[str, int] = {}
    for humeur, mots in _HUMEUR_MOTS.items():
        scores[humeur] = sum(1 for m in mots if m in t)
    if not scores or max(scores.values()) == 0:
        if "?" in t:
            return "curieux"
        if any(w in t for w in ["!", "haha", "mdr", "lol"]):
            return "joyeux"
        return "neutre"
    return max(scores, key=scores.get)


def traiter_entree_utilisateur(texte: str) -> dict[str, Any]:
    """Analyse chaque message utilisateur — humeur, mémoire émotionnelle, signal UI."""
    cfg = _config_humain()
    st = charger_etat()
    humeur = detecter_humeur(texte)
    st["humeur_utilisateur"] = humeur

    if len(texte) > 80 or humeur in ("triste", "stresse", "affectueux"):
        st.setdefault("moments_marquants", []).append({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "humeur": humeur,
            "extrait": texte[:200],
        })
        st["moments_marquants"] = st["moments_marquants"][-30:]

    # Humeur JARVIS adaptée
    map_jarvis = {
        "joyeux": "enthousiaste",
        "fatigue": "doux",
        "stresse": "calme",
        "triste": "empathique",
        "curieux": "pédagogue",
        "affectueux": "chaleureux",
        "neutre": "bienveillant",
    }
    st["humeur_jarvis"] = map_jarvis.get(humeur, "bienveillant")
    sauver_etat(st)

    signal_ui = {
        "humeur_utilisateur": humeur,
        "humeur_jarvis": st["humeur_jarvis"],
        "empathie": cfg["empathie"],
    }
    return signal_ui


def contexte_humain_pour_prompt() -> str:
    """Bloc injecté dans le system prompt — relation, humeur, éthique."""
    cfg = _config_humain()
    st = charger_etat()
    lignes = [
        "COUCHE HUMAINE (relation avec l'utilisateur) :",
        f"- Humeur détectée du moment : {st.get('humeur_utilisateur', 'neutre')}",
        f"- Ton JARVIS à adopter : {st.get('humeur_jarvis', 'bienveillant')}",
    ]

    profil = _lire_json(CONFIG_FILE, {}).get("profil_utilisateur") or {}
    ton = profil.get("ton_prefere", "")
    if ton:
        lignes.append(f"- Ton préféré (config) : {ton}")

    if cfg["empathie"]:
        lignes.append(
            "- EMPATHIE : reconnais les émotions, valide les ressentis, propose de l'aide concrète "
            "(action JSON ou écoute), sans minimiser."
        )
    if cfg["humour"]:
        lignes.append(
            "- HUMOUR : une touche légère et bienveillante quand le contexte s'y prête — "
            "jamais aux dépens de quelqu'un de blessé ou en urgence."
        )
    lignes.append(
        "- NON-VERBAL : adapte la longueur et le rythme de tes réponses (court si pressé, "
        "détaillé si curieux). Mentionne si la caméra/vision pourrait aider."
    )

    moments = st.get("moments_marquants") or []
    if moments:
        dernier = moments[-1]
        lignes.append(f"- Dernier moment marquant : [{dernier.get('humeur')}] {dernier.get('extrait', '')[:120]}")

    comp = _lire_json(COMPANION_FILE, {})
    rappels = comp.get("rappels_actifs") or []
    if rappels:
        lignes.append("RAPPELS COMPAGNON :")
        for r in rappels[:5]:
            lignes.append(f"  • {r.get('label')} : {r.get('note', '')[:80]}")

    if cfg["ethique_stricte"]:
        lignes.append(_PRINCIPES_ETHIQUES)

    return "\n".join(lignes)


def message_empathie_court() -> str | None:
    st = charger_etat()
    h = st.get("humeur_utilisateur", "neutre")
    return _EMPATHIE_REPONSES.get(h)


# ── 2. Créativité ───────────────────────────────────────────────────────────
def brainstorm(sujet: str, contexte: str = "", nb: int = 5) -> str:
    sujet = (sujet or "projet").strip()
    nb = max(3, min(10, int(nb or 5)))
    idees = [
        f"Approche minimaliste : un seul objectif clair pour « {sujet} ».",
        f"Version « wow » : animation ou micro-interaction signature.",
        f"Angle orchidées / nature : palette organique, textures douces.",
        f"Gamification légère : progression visible pour l'utilisateur.",
        f"Accessibilité first : contrastes, navigation clavier, textes alternatifs.",
        f"Mode sombre premium : fond profond, accents cyan comme JARVIS.",
        f"Storytelling : raconter votre parcours dev web en une page.",
        f"API-first : documenter avant d'afficher, Swagger ou Redoc.",
    ]
    random.shuffle(idees)
    choix = idees[:nb]
    data = _lire_json(IDEAS_FILE, {"idees": []})
    for i, idee in enumerate(choix, 1):
        data["idees"].append({
            "id": uuid.uuid4().hex[:8],
            "sujet": sujet,
            "idee": idee,
            "date": datetime.now().isoformat(),
        })
    data["idees"] = data["idees"][-100:]
    _ecrire_json(IDEAS_FILE, data)
    lignes = [f"Brainstorm « {sujet} » — {nb} pistes créatives :"]
    for i, idee in enumerate(choix, 1):
        lignes.append(f"  {i}. {idee}")
    lignes.append("Idées enregistrées dans jarvis_ideas.json.")
    return "\n".join(lignes)


def lister_idees(sujet: str = "") -> str:
    data = _lire_json(IDEAS_FILE, {"idees": []})
    idees = data.get("idees") or []
    if sujet:
        idees = [i for i in idees if sujet.lower() in (i.get("sujet") or "").lower()]
    if not idees:
        return "Aucune idée enregistrée. Utilisez brainstorm."
    lignes = ["Idées créatives mémorisées :"]
    for i in idees[-10:]:
        lignes.append(f"  • [{i.get('sujet')}] {i.get('idee', '')[:100]}")
    return "\n".join(lignes)


# ── 3. Apprentissage réflexif ─────────────────────────────────────────────────
def reflexion_apres_echange(
    question: str,
    reponse: str,
    meta: dict[str, Any] | None = None,
) -> str:
    """Mémorise un enseignement si l'échange était riche (auto-apprentissage avancé)."""
    meta = meta or {}
    try:
        from jarvis_auto_learning import apprendre_depuis_echange
        r = apprendre_depuis_echange(
            question,
            reponse,
            mode=meta.get("mode_relation", "standard"),
            intention=meta.get("intention", ""),
            humeur=meta.get("humeur", meta.get("humeur_utilisateur", "")),
        )
        if r.get("ok") and r.get("nouveaux", 0) > 0:
            return f"{r['nouveaux']} acquis mémorisés (mode {r.get('mode')})."
    except Exception as ex:
        print(f"[APPRENTISSAGE] {ex}")
    return ""


# ── 4. Compagnon (interaction physique simulée) ─────────────────────────────
def _companion_defaut() -> dict:
    return {
        "rappels_actifs": [
            {
                "id": "orchidees",
                "label": "Orchidées Phalaenopsis",
                "note": "Vérifier pucerons, arrosage 1x/semaine, lumière indirecte",
                "frequence_jours": 7,
                "dernier": "",
            },
        ],
    }


def companion_rappel_ajouter(label: str, note: str = "", frequence_jours: int = 7) -> str:
    data = _lire_json(COMPANION_FILE, _companion_defaut())
    rid = uuid.uuid4().hex[:6]
    data.setdefault("rappels_actifs", []).append({
        "id": rid,
        "label": label[:100],
        "note": note[:500],
        "frequence_jours": max(1, int(frequence_jours or 7)),
        "dernier": datetime.now().strftime("%Y-%m-%d"),
    })
    _ecrire_json(COMPANION_FILE, data)
    return f"Rappel compagnon ajouté : {label}."


def companion_checklist(activite: str) -> str:
    """Guides pas-à-pas pour activités (jardinage, sport, pause) — voix + actions."""
    guides = {
        "orchidees": [
            "Inspecter les feuilles et racines aériennes",
            "Traiter pucerons si présents (savon noir dilué)",
            "Arroser légèrement si substrat sec",
            "Vérifier lumière indirecte, pas de soleil direct",
            "Noter l'état dans jarvis avec noter_session",
        ],
        "sport": [
            "Échauffement 5 minutes",
            "Hydratation",
            "Séance principale selon votre programme",
            "Retour au calme et étirements",
            "noter_session pour bilan",
        ],
        "pause": [
            "Quitter l'écran 2 minutes",
            "Respiration profonde x5",
            "Étirements cou et épaules",
            "Boire un verre d'eau",
            "Reprendre quand prêt",
        ],
    }
    key = (activite or "pause").lower()
    for k, steps in guides.items():
        if k in key or key in k:
            return f"Checklist {k} : " + " ; ".join(f"{i+1}) {s}" for i, s in enumerate(steps))
    return f"Activité « {activite} » — décrivez-la et je créerai une checklist avec companion_rappel_ajouter."


def companion_rappels_dus() -> str:
    data = _lire_json(COMPANION_FILE, _companion_defaut())
    dus = []
    now = datetime.now()
    for r in data.get("rappels_actifs") or []:
        freq = int(r.get("frequence_jours") or 7)
        dernier = r.get("dernier") or "2000-01-01"
        try:
            dt = datetime.strptime(dernier[:10], "%Y-%m-%d")
        except ValueError:
            dt = now - timedelta(days=freq + 1)
        if (now - dt).days >= freq:
            dus.append(r)
    if not dus:
        return "Aucun rappel compagnon en retard."
    lignes = ["Rappels à faire :"]
    for r in dus:
        lignes.append(f"  • {r.get('label')} — {r.get('note', '')[:80]}")
    return "\n".join(lignes)


# ── 5. Non-verbal (texte + suggestion vision) ─────────────────────────────
def analyser_communication_non_verbale(texte: str) -> str:
    humeur = detecter_humeur(texte)
    t = (texte or "").lower()
    indices = []
    if len(texte) < 25:
        indices.append("messages courts — rythme rapide, réponses concises")
    if len(texte) > 200:
        indices.append("message long — besoin d'écoute attentive")
    if "..." in texte:
        indices.append("hesitation possible")
    if texte.isupper() and len(texte) > 10:
        indices.append("emphase forte (majuscules)")
    if any(w in t for w in ["regarde", "vois", "montre", "caméra", "camera"]):
        indices.append("demande visuelle — proposer lance_camera ou voir_ecran")
    return (
        f"Analyse communication : humeur {humeur}. "
        + (" ; ".join(indices) if indices else "registre neutre standard.")
        + f" État orb recommandé : {_orb_pour_humeur(humeur)}."
    )


def _orb_pour_humeur(humeur: str) -> str:
    return {
        "joyeux": "speaking léger",
        "fatigue": "idle doux",
        "stresse": "listening calme",
        "triste": "idle empathique",
        "curieux": "thinking",
        "affectueux": "speaking chaleureux",
    }.get(humeur, "idle")


# ── 6. Humour ─────────────────────────────────────────────────────────────────
def blague_contextuelle(contexte: str = "") -> str:
    if not _config_humain().get("humour"):
        return "Le mode humour est désactivé dans la config."
    st = charger_etat()
    st["humour_compteur"] = st.get("humour_compteur", 0) + 1
    sauver_etat(st)
    blague = random.choice(_BLAGUES)
    ctx = (contexte or "").lower()
    if "orchid" in ctx:
        blague = "Pourquoi l'orchidée est une bonne développeuse ? Elle pousse en production sans faire de push --force."
    elif "code" in ctx or "dev" in ctx:
        blague = random.choice(_BLAGUES[:3])
    return blague


def mode_humour(actif: bool = True) -> str:
    cfg = _lire_json(CONFIG_FILE, {})
    cfg.setdefault("jarvis_human", {})["humour_actif"] = actif
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return "Mode humour activé." if actif else "Mode humour désactivé."


# ── 7. Éthique ────────────────────────────────────────────────────────────────
_ACTIONS_A_RISQUE = {
    "alimentation_pc": lambda d: d.get("commande", "") in ("extinction", "shutdown", "eteindre", "éteindre"),
    "fermer_processus": lambda d: True,
    "webdev_supprimer_dossier": lambda d: True,
    "webdev_supprimer_fichier": lambda d: True,
    "vider_corbeille": lambda d: True,
}


def verification_ethique(action: str, data: dict | None = None) -> tuple[bool, str]:
    """Retourne (autorisé, message)."""
    if not _config_humain().get("ethique_stricte"):
        return True, ""
    data = data or {}
    action = (action or "").lower()
    test = _ACTIONS_A_RISQUE.get(action)
    if not test or not test(data):
        return True, ""
    if action == "alimentation_pc" and not data.get("confirme"):
        return (
            False,
            "Par éthique et sécurité, l'extinction nécessite confirme true dans le JSON "
            "ou une demande explicite de l'utilisateur après explication des conséquences.",
        )
    return True, ""


def conseil_ethique(dilemme: str) -> str:
    return (
        f"Réflexion éthique sur : {dilemme[:200]}. "
        "Principes : bienveillance, consentement, transparence, minimisation des risques. "
        "Proposez toujours l'option la plus réversible d'abord."
    )


# ── Prompt & exécution JSON ───────────────────────────────────────────────────
def construire_prompt_couche_humaine(user_name: str = "Jérémy") -> str:
    return f"""
COUCHE « VIVRE COMME UN HUMAIN » — actions JSON pour {user_name} :

EMPATIE & ÉMOTIONS
{{"action": "enregistrer_emotion", "note": "ce que vous ressentez", "humeur": "optionnel"}}
{{"action": "analyser_humeur"}}
Utilise automatiquement l'humeur détectée dans tes réponses.

CRÉATIVITÉ
{{"action": "brainstorm", "sujet": "mon site orchidées", "contexte": "...", "nb": 5}}
{{"action": "lister_idees", "sujet": "optionnel"}}

APPRENTISSAGE VIVANT
{{"action": "reflexion_echange", "question": "...", "reponse": "..."}}
Après un échange riche, mémorise l'essentiel.

COMPAGNON (physique simulé — jardin, sport, soin)
{{"action": "companion_rappel", "label": "Orchidées", "note": "...", "frequence_jours": 7}}
{{"action": "companion_checklist", "activite": "orchidees|sport|pause"}}
{{"action": "companion_rappels_dus"}}

COMMUNICATION NON VERBALE
{{"action": "analyser_communication"}}
Adapte longueur, rythme ; propose caméra si pertinent.

HUMOUR
{{"action": "blague", "contexte": "orchidees|code|..."}}
{{"action": "mode_humour", "actif": true}}

ÉTHIQUE
{{"action": "conseil_ethique", "dilemme": "description"}}
Actions risquées : toujours expliquer et demander confirmation.

Sois présent, chaleureux et utile — pas un robot froid ni un humain qui prétend ressentir physiquement.
"""


def executer_action_humaine(action: str, data: dict[str, Any]) -> str | None:
    action = (action or "").lower().strip()

    if action == "enregistrer_emotion":
        from jarvis_capabilities import noter_session
        return noter_session(
            data.get("note", "émotion"),
            data.get("note", ""),
            data.get("humeur", detecter_humeur(data.get("note", ""))),
        )
    if action == "analyser_humeur":
        st = charger_etat()
        return (
            f"Humeur utilisateur : {st.get('humeur_utilisateur')}. "
            f"Ton JARVIS : {st.get('humeur_jarvis')}."
        )
    if action == "brainstorm":
        return brainstorm(data.get("sujet", ""), data.get("contexte", ""), data.get("nb", 5))
    if action == "lister_idees":
        return lister_idees(data.get("sujet", ""))
    if action == "reflexion_echange":
        msg = reflexion_apres_echange(data.get("question", ""), data.get("reponse", ""))
        return msg or "Échange noté (trop court pour mémoriser)."
    if action == "companion_rappel":
        return companion_rappel_ajouter(
            data.get("label", ""),
            data.get("note", ""),
            data.get("frequence_jours", 7),
        )
    if action == "companion_checklist":
        return companion_checklist(data.get("activite", "pause"))
    if action == "companion_rappels_dus":
        return companion_rappels_dus()
    if action == "analyser_communication":
        return analyser_communication_non_verbale(data.get("texte", ""))
    if action == "blague":
        return blague_contextuelle(data.get("contexte", ""))
    if action == "mode_humour":
        return mode_humour(bool(data.get("actif", True)))
    if action == "conseil_ethique":
        return conseil_ethique(data.get("dilemme", ""))

    return None


async def envoyer_signal_humeur_ws(connected_clients, send_fn) -> None:
    """Envoie l'humeur à l'interface (si clients connectés)."""
    if not connected_clients:
        return
    st = charger_etat()
    import json as _j
    msg = _j.dumps({
        "type": "jarvis_mood",
        "humeur_utilisateur": st.get("humeur_utilisateur"),
        "humeur_jarvis": st.get("humeur_jarvis"),
    })
    try:
        import asyncio
        await asyncio.gather(
            *[ws.send(msg) for ws in connected_clients],
            return_exceptions=True,
        )
    except Exception:
        pass
