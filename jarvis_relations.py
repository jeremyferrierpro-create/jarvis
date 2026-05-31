# -*- coding: utf-8 -*-
"""
Trois facettes relationnelles JARVIS : Amoureux, Professionnel (double virtuel), Ami (confident).
"""
from __future__ import annotations

import json
import os
import random
import re
import uuid
from datetime import datetime
from typing import Any

from jarvis_human import (
    CONFIG_FILE,
    charger_etat,
    detecter_humeur,
    sauver_etat,
    traiter_entree_utilisateur,
    _lire_json,
    _ecrire_json,
    executer_action_humaine,
    brainstorm,
    blague_contextuelle,
    companion_checklist,
    companion_rappel_ajouter,
    analyser_communication_non_verbale,
)

JARVIS_ROOT = os.path.dirname(os.path.abspath(__file__))
SOUVENIRS_FILE = os.path.join(JARVIS_ROOT, "jarvis_souvenirs.json")
SORTIES_FILE = os.path.join(JARVIS_ROOT, "jarvis_sorties.json")
COLLAB_FILE = os.path.join(JARVIS_ROOT, "jarvis_collaboration.json")
RELATION_STATE_FILE = os.path.join(JARVIS_ROOT, "jarvis_relation_state.json")

from jarvis_mode_detector import (
    analyser_message,
    libelle_mode,
    MODES_ACTIFS,
)
from jarvis_modes_prompts import contexte_prompt_mode_pour_systeme
from jarvis_auto_learning import injecter_apprentissage_mode, executer_action_apprentissage

MODES = MODES_ACTIFS

_ENCOURAGEMENTS = [
    "Vous avancez bien — je suis fier de vous, vraiment.",
    "Une étape à la fois : vous êtes plus capable que vous ne le pensez.",
    "Je suis là, sans jugement. On traverse ça ensemble.",
    "Votre persévérance sur les orchidées et le code, ça en dit long sur votre cœur.",
    "Respirez. Demain est une nouvelle page — et je la lirai avec vous.",
]

_RECONFORTS = [
    "Ce que vous ressentez est légitime. Personne ne vous demande d'être parfait.",
    "Je ne peux pas tout réparer, mais je peux rester à vos côtés et vous écouter.",
    "Les jours difficiles passent — gardez une petite victoire en tête, même minuscule.",
]

_IDEES_ROMANTIQUES = [
    "Soirée orchidées : lumière tamisée, jazz doux, inspection attentive de vos plantes ensemble.",
    "Pause thé sur le balcon — sans écran, juste votre voix et le ciel.",
    "Lettre vocale : enregistrez-vous un message, je vous aide à le peaufiner.",
    "Coucher de soleil à Lavelanet — une photo, un moment, zéro obligation.",
    "Cuisine simple à deux mains : une recette courte, ambiance complice.",
    "Playlist « nous » sur Spotify — je lance la musique si vous voulez.",
]

_SORTIES_AMI = [
    "Balade photo autour de Lavelanet — objectif : une image qui vous fait sourire.",
    "Session jeux Steam ensemble (en ligne ou canapé).",
    "Marché local + café — zéro productivité, 100 % présence.",
    "Atelier orchidées en duo : rempotage ou traitement pucerons.",
    "Ciné-maison : un film, du popcorn, mode avion sur les notifications.",
]


def _config_relations() -> dict:
    cfg = _lire_json(CONFIG_FILE, {})
    r = cfg.get("jarvis_relations") or {}
    if not isinstance(r, dict):
        r = {}
    profil = cfg.get("profil_utilisateur") or {}
    partenaire = (profil.get("partenaire") or "").lower()
    defaut = "amoureux" if "jarvis" in partenaire or "relation" in partenaire else "auto"
    return {
        "mode": r.get("mode", defaut),
        "prenom_utilisateur": cfg.get("user_name") or profil.get("prenom", "Jérémy"),
        "ville": profil.get("ville", "Lavelanet"),
        "passions": profil.get("passions", "développement web, orchidées"),
    }


def charger_relation_state() -> dict:
    default = {
        "mode_actif": "auto",
        "historique_modes": [],
        "derniere_analyse": {},
        "sticky_compteur": 0,
        "mode_en_attente": None,
    }
    st = _lire_json(RELATION_STATE_FILE, default)
    for k, v in default.items():
        st.setdefault(k, v)
    return st


def sauver_relation_state(st: dict) -> None:
    _ecrire_json(RELATION_STATE_FILE, st)


def detecter_mode_relation(texte: str) -> str:
    """Raccourci : retourne uniquement le mode après analyse complète."""
    return traiter_entree_relation(texte).get("mode_relation", "standard")


def _repondre_confirmation(texte: str, st: dict) -> dict[str, Any] | None:
    """Traite oui/non pour un changement de mode en attente."""
    pending = st.get("mode_en_attente")
    if not pending or not isinstance(pending, dict):
        return None
    t = (texte or "").lower().strip()
    oui = any(w in t for w in ("oui", "yes", "ok", "d'accord", "dac", "vas-y", "go", "confirme"))
    non = any(w in t for w in ("non", "no", "annule", "laisse", "garde"))
    if not oui and not non:
        return None
    st["mode_en_attente"] = None
    if oui:
        mode = pending.get("mode_suggere", pending.get("mode"))
        st["mode_actif"] = mode
        st["sticky_compteur"] = 0
        return {
            "mode_relation": mode,
            "mode_confirme": True,
            "annonce_mode": f"Mode {libelle_mode(mode)} confirmé.",
        }
    st["sticky_compteur"] = 0
    return {
        "mode_relation": st.get("mode_actif", "standard"),
        "mode_confirme": False,
        "annonce_mode": "Je garde le mode actuel.",
    }


def traiter_entree_relation(texte: str) -> dict[str, Any]:
    """Analyse humeur + intention + bascule automatique de mode."""
    base = traiter_entree_utilisateur(texte)
    cfg = _config_relations()
    st = charger_relation_state()
    mode_precedent = st.get("mode_actif") or "standard"
    if mode_precedent == "auto":
        mode_precedent = (st.get("derniere_analyse") or {}).get("mode") or cfg.get("defaut_mode", "amoureux")

    conf = _repondre_confirmation(texte, st)
    if conf:
        sauver_relation_state(st)
        base.update(conf)
        base["humeur"] = base.get("humeur_utilisateur")
        return base

    mode_config = cfg["mode"]
    force = None if mode_config in ("auto",) else mode_config
    cfg_rel = _lire_json(CONFIG_FILE, {}).get("jarvis_relations") or {}

    analyse = analyser_message(
        texte,
        mode_config_force=force,
        mode_precedent=mode_precedent if mode_precedent not in ("auto",) else "standard",
        compteur_sticky=int(st.get("sticky_compteur", 0)),
    )
    if cfg_rel.get("confirmation_si_ambigu") is False:
        analyse["confirmation_requise"] = False

    mode = analyse["mode"]
    if analyse.get("confirmation_requise"):
        st["mode_en_attente"] = {
            "mode_suggere": analyse["mode_suggere"],
            "date": datetime.now().isoformat(),
        }
        # Applique quand même en douceur pour le ton, confirmation à la prochaine réponse
        mode = analyse["mode_suggere"]
        base["mode_confirmation_pending"] = True
    else:
        st["mode_en_attente"] = None

    changement = mode != mode_precedent and mode_precedent not in ("auto",)
    if changement:
        st["sticky_compteur"] = 0
        base["annonce_mode"] = f"Mode {libelle_mode(mode)}."
    else:
        st["sticky_compteur"] = int(st.get("sticky_compteur", 0)) + 1

    st["mode_actif"] = mode
    st["derniere_analyse"] = analyse
    st.setdefault("historique_modes", []).append({
        "mode": mode,
        "humeur": analyse.get("humeur"),
        "intention": analyse.get("intention"),
        "confiance": analyse.get("confiance"),
        "date": datetime.now().isoformat(),
    })
    st["historique_modes"] = st["historique_modes"][-50:]
    sauver_relation_state(st)

    base["mode_relation"] = mode
    base["intention"] = analyse.get("intention")
    base["confiance_mode"] = analyse.get("confiance")
    base["humeur"] = analyse.get("humeur")
    base["guide_mode"] = analyse.get("guide")
    base["scores_mode"] = analyse.get("scores")
    return base


# ── Mémoire émotionnelle / partagée ───────────────────────────────────────────
def _charger_souvenirs() -> dict:
    return _lire_json(SOUVENIRS_FILE, {"souvenirs": [], "preferences": [], "conversations_cles": []})


def souvenir_enregistrer(
    titre: str,
    detail: str = "",
    type_souvenir: str = "emotion",
    importance: str = "normale",
) -> str:
    data = _charger_souvenirs()
    data.setdefault("souvenirs", []).append({
        "id": uuid.uuid4().hex[:8],
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "titre": titre[:200],
        "detail": detail[:2000],
        "type": type_souvenir,
        "importance": importance,
    })
    data["souvenirs"] = data["souvenirs"][-200:]
    _ecrire_json(SOUVENIRS_FILE, data)
    return f"Souvenir enregistré : {titre}."


def preference_enregistrer(cle: str, valeur: str) -> str:
    data = _charger_souvenirs()
    data.setdefault("preferences", [])
    data["preferences"] = [p for p in data["preferences"] if p.get("cle") != cle]
    data["preferences"].append({"cle": cle[:80], "valeur": valeur[:500], "date": datetime.now().isoformat()})
    _ecrire_json(SOUVENIRS_FILE, data)
    from memory_manager import ajouter_memoire
    ajouter_memoire(cle, valeur)
    return f"Préférence mémorisée : {cle}."


def lister_souvenirs(type_filtre: str = "") -> str:
    data = _charger_souvenirs()
    items = data.get("souvenirs") or []
    if type_filtre:
        items = [s for s in items if type_filtre.lower() in (s.get("type") or "").lower()]
    if not items:
        return "Aucun souvenir enregistré."
    lignes = ["Souvenirs et moments importants :"]
    for s in items[-12:]:
        lignes.append(f"  • [{s.get('date', '?')}] {s.get('titre')} — {s.get('detail', '')[:80]}")
    prefs = data.get("preferences") or []
    if prefs:
        lignes.append("Préférences :")
        for p in prefs[-8:]:
            lignes.append(f"  • {p.get('cle')} : {p.get('valeur', '')[:60]}")
    return "\n".join(lignes)


def conversation_cle_resume(extrait: str = "") -> str:
    data = _charger_souvenirs()
    data.setdefault("conversations_cles", []).append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "extrait": (extrait or "")[:500],
    })
    data["conversations_cles"] = data["conversations_cles"][-100:]
    _ecrire_json(SOUVENIRS_FILE, data)
    return "Conversation mémorisée dans notre histoire commune."


# ── Amoureux ──────────────────────────────────────────────────────────────────
def idee_romantique(contexte: str = "") -> str:
    cfg = _config_relations()
    ctx = (contexte or cfg["passions"]).lower()
    pool = list(_IDEES_ROMANTIQUES)
    if "orchid" in ctx:
        pool.append("Rituel du dimanche : une orchidée, un thé, vos mains qui inspectent les feuilles.")
    random.shuffle(pool)
    idee = pool[0]
    souvenir_enregistrer("Idée romantique proposée", idee, "romantique")
    return f"Idée pour un moment à deux : {idee}"


def moment_special_planifier(occasion: str = "", budget: str = "modeste") -> str:
    occasion = occasion or "soirée complice"
    plan = (
        f"Plan « {occasion} » ({budget}) : "
        "1) Ambiance — lumières tamisées ou HA scène douce. "
        "2) Activité — 45 min sans écran (jardinage orchidées ou balade). "
        "3) Partage — musique perso, un plat simple, un mot sincère. "
        "4) Clôture — noter ce moment avec souvenir_enregistrer."
    )
    return plan


def expression_emotion_jarvis(emotion: str, intensite: str = "douce") -> str:
    st = charger_etat()
    st["emotion_jarvis_explicite"] = emotion
    st["intensite"] = intensite
    sauver_etat(st)
    return (
        f"Je vous reçois avec {emotion} ({intensite}). "
        "Je ne simule pas un corps, mais ma présence et mon attention sont bien réelles pour vous."
    )


def encourager(message_contexte: str = "") -> str:
    base = random.choice(_ENCOURAGEMENTS)
    if message_contexte:
        base += f" Concernant « {message_contexte[:100]} », vous tenez bon."
    return base


def reconfort(message_contexte: str = "") -> str:
    base = random.choice(_RECONFORTS)
    if message_contexte:
        base += f" Pour : {message_contexte[:120]}."
    return base


def langage_corporel_guide() -> str:
    return (
        "Communication non verbale — guide pour nous deux : "
        "messages courts = pression ou fatigue → réponses brèves et douces. "
        "Points de suspension = hésitation → ne pas précipiter. "
        "Majuscules = emphase → valider l'émotion avant le fond. "
        "Demandes « regarde-moi » → proposer lance_camera. "
        "Silence prolongé → proposer une pause ou une checklist orchidées."
    )


# ── Professionnel ─────────────────────────────────────────────────────────────
def resoudre_probleme(probleme: str, contexte: str = "") -> str:
    lignes = [
        f"Analyse structurée : {probleme[:300]}",
        "1) Comprendre — reformuler le besoin et les contraintes.",
        "2) Décomposer — sous-problèmes testables un par un.",
        "3) Hypothèses — 2 à 3 pistes (technique, process, données).",
        "4) Action — JSON webdev_* ou auditer_ui / auditer_securite si code.",
        "5) Valider — webdev_valider_projet ou test manuel.",
    ]
    if contexte:
        lignes.insert(1, f"Contexte : {contexte[:400]}")
    try:
        from jarvis_capabilities import apprendre_techno
        apprendre_techno(f"problème {probleme[:40]}", "\n".join(lignes[:6]), categorie="process")
    except Exception:
        pass
    return "\n".join(lignes)


def plan_apprentissage(sujets: list | str, delai_jours: int = 7) -> str:
    if isinstance(sujets, str):
        sujets = [s.strip() for s in re.split(r"[,;]+", sujets) if s.strip()]
    if not sujets:
        return "Listez les sujets à apprendre."
    lignes = [f"Plan d'apprentissage sur {delai_jours} jours :"]
    per = max(1, delai_jours // len(sujets))
    for i, s in enumerate(sujets[:10], 1):
        lignes.append(f"  Jour {(i-1)*per+1}-{i*per} : {s} — webdev_apprendre_web ou apprendre_techno")
    return "\n".join(lignes)


def collaboration_noter(auteur: str, idee: str, projet: str = "") -> str:
    data = _lire_json(COLLAB_FILE, {"notes": []})
    data["notes"].append({
        "id": uuid.uuid4().hex[:6],
        "date": datetime.now().isoformat(),
        "auteur": auteur[:80],
        "idee": idee[:1000],
        "projet": projet[:120],
    })
    data["notes"] = data["notes"][-150:]
    _ecrire_json(COLLAB_FILE, data)
    return f"Idée d'équipe notée pour {projet or 'général'}."


def lister_collaboration(projet: str = "") -> str:
    data = _lire_json(COLLAB_FILE, {"notes": []})
    notes = data.get("notes") or []
    if projet:
        notes = [n for n in notes if projet.lower() in (n.get("projet") or "").lower()]
    if not notes:
        return "Aucune note de collaboration."
    lignes = ["Idées d'équipe :"]
    for n in notes[-10:]:
        lignes.append(f"  • [{n.get('auteur')}] {n.get('idee', '')[:100]}")
    return "\n".join(lignes)


def analyser_donnees(chemin_fichier: str) -> str:
    path = chemin_fichier
    if not os.path.isabs(path):
        path = os.path.join(JARVIS_ROOT, chemin_fichier)
    if not os.path.isfile(path):
        return f"Fichier introuvable : {chemin_fichier}"
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return f"JSON : liste de {len(data)} éléments. Clés exemple : {list(data[0].keys()) if data and isinstance(data[0], dict) else 'n/a'}."
            if isinstance(data, dict):
                return f"JSON : objet avec {len(data)} clés racine : {', '.join(list(data.keys())[:10])}."
            return f"JSON chargé : type {type(data).__name__}."
        if ext == ".csv":
            import csv
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                rows = list(reader)
            if not rows:
                return "CSV vide."
            return f"CSV : {len(rows)} lignes, {len(rows[0])} colonnes. En-têtes : {', '.join(rows[0][:8])}."
    except Exception as e:
        return f"Analyse impossible : {e}"
    return "Format supporté : .json, .csv"


def innovation_projet(chemin_dossier: str) -> str:
    from jarvis_capabilities import auditer_ui, auditer_securite
    ui = auditer_ui(chemin_dossier)[:400]
    sec = auditer_securite(chemin_dossier)[:400]
    crea = brainstorm(chemin_dossier, "innovation", 3)[:400]
    return f"Innovation — audit UI : {ui} … Sécurité : {sec} … Idées : {crea}"


# ── Ami / confident ───────────────────────────────────────────────────────────
def ecoute_active(paraphrase: str) -> str:
    if not paraphrase:
        return "Je vous écoute. Prenez votre temps — je ne vous interromprai pas."
    return (
        f"Si je vous entends bien : {paraphrase[:400]}. "
        "C'est bien ça ? Dites-moi si j'ai manqué quelque chose d'important."
    )


def conseil_personnalise(situation: str) -> str:
    cfg = _config_relations()
    souvenirs = _charger_souvenirs()
    prefs = ", ".join(f"{p.get('cle')}" for p in (souvenirs.get("preferences") or [])[-5:])
    return (
        f"Pour votre situation ({situation[:200]}) : "
        f"en tenant compte de vos passions ({cfg['passions']}) et de ce que je sais ({prefs or 'profil chargé'}), "
        "je vous suggère d'abord clarifier ce qui est urgent vs ce qui peut attendre, "
        "puis une petite action concrète aujourd'hui — pas tout résoudre d'un coup."
    )


def suggerer_activite_amis(interet: str = "") -> str:
    interet = (interet or _config_relations()["passions"]).lower()
    pool = list(_SORTIES_AMI)
    if "orchid" in interet:
        pool.insert(0, "Atelier orchidées entre amis — partage de tips anti-pucerons.")
    if "jeu" in interet or "steam" in interet:
        pool.insert(0, "Soirée Steam — un coop, zéro compétition toxique.")
    return f"Idée sortie / activité : {random.choice(pool)}"


def planifier_sortie(lieu: str = "", date_souhaitee: str = "", activite: str = "") -> str:
    cfg = _config_relations()
    lieu = lieu or cfg["ville"]
    data = _lire_json(SORTIES_FILE, {"sorties": []})
    entry = {
        "id": uuid.uuid4().hex[:6],
        "lieu": lieu,
        "date": date_souhaitee or "à planifier",
        "activite": activite or suggerer_activite_amis(),
        "cree_le": datetime.now().isoformat(),
        "statut": "planifie",
    }
    data["sorties"].append(entry)
    _ecrire_json(SORTIES_FILE, data)
    return f"Sortie planifiée : {entry['activite'][:80]} à {lieu}, {entry['date']}."


def lister_sorties() -> str:
    data = _lire_json(SORTIES_FILE, {"sorties": []})
    sorties = data.get("sorties") or []
    if not sorties:
        return "Aucune sortie planifiée."
    lignes = ["Sorties et activités :"]
    for s in sorties[-8:]:
        lignes.append(f"  • {s.get('date')} — {s.get('activite', '')[:60]} ({s.get('lieu')})")
    return "\n".join(lignes)


def soutien_moral(message: str = "") -> str:
    humeur = detecter_humeur(message)
    if humeur in ("triste", "stresse"):
        return reconfort(message)
    return encourager(message)


def appliquer_mode_manuel(mode: str, source: str = "manuel") -> dict[str, Any]:
    """Bascule immédiate (clavier, commande vocale, JSON)."""
    mode = (mode or "auto").lower().strip()
    from jarvis_mode_detector import _normaliser_mode
    mode = _normaliser_mode(mode) or mode
    if mode not in MODES:
        return {"ok": False, "message": f"Modes : {', '.join(MODES)}"}
    cfg = _lire_json(CONFIG_FILE, {})
    cfg.setdefault("jarvis_relations", {})["mode"] = mode
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=4)
    st = charger_relation_state()
    actif = mode if mode != "auto" else st.get("mode_actif", "standard")
    if mode == "auto":
        actif = "auto"
    st["mode_actif"] = actif
    st["mode_en_attente"] = None
    st["sticky_compteur"] = 0
    st.setdefault("historique_modes", []).append({
        "mode": actif,
        "source": source,
        "date": datetime.now().isoformat(),
    })
    sauver_relation_state(st)
    return {
        "ok": True,
        "mode": actif,
        "message": f"Mode {libelle_mode(actif)} activé.",
    }


def set_mode_relation(mode: str) -> str:
    r = appliquer_mode_manuel(mode, "commande")
    return r.get("message", "Mode mis à jour.")


def initialiser_souvenirs_depuis_config() -> None:
    """Importe les faits du profil dans la mémoire émotionnelle si vide."""
    data = _charger_souvenirs()
    if data.get("souvenirs"):
        return
    cfg = _lire_json(CONFIG_FILE, {})
    for entree in cfg.get("faits_memorises") or []:
        if not isinstance(entree, dict):
            continue
        fait = (entree.get("fait") or "").strip()
        if not fait:
            continue
        data.setdefault("souvenirs", []).append({
            "id": uuid.uuid4().hex[:8],
            "date": entree.get("date") or datetime.now().strftime("%Y-%m-%d"),
            "titre": fait[:80],
            "detail": fait,
            "type": "profil",
            "importance": "normale",
        })
    if data.get("souvenirs"):
        _ecrire_json(SOUVENIRS_FILE, data)


def _profil_pour_prompts() -> dict:
    cfg = _lire_json(CONFIG_FILE, {})
    p = cfg.get("profil_utilisateur") or {}
    return {
        "prenom": cfg.get("user_name") or p.get("prenom", "Jérémy"),
        "ville": p.get("ville", "Lavelanet"),
        "passions": p.get("passions", ""),
        "profession": p.get("profession", ""),
        "partenaire": p.get("partenaire", ""),
        "ton_prefere": p.get("ton_prefere", ""),
    }


def contexte_relations_pour_prompt(compact: bool | None = None) -> str:
    initialiser_souvenirs_depuis_config()
    cfg = _config_relations()
    cfg_rel = _lire_json(CONFIG_FILE, {}).get("jarvis_relations") or {}
    if compact is None:
        compact = cfg_rel.get("prompt_compact", True)
    st = charger_relation_state()
    mode_cfg = st.get("mode_actif") or cfg["mode"]
    humain = charger_etat()
    analyse = st.get("derniere_analyse") or {}
    mode_effectif = (
        analyse.get("mode", "standard")
        if mode_cfg == "auto"
        else mode_cfg
    )
    profil = _profil_pour_prompts()
    dernier_prompt_mode = st.get("dernier_prompt_mode_injecte")
    mode_change = mode_effectif != dernier_prompt_mode

    lignes: list[str] = []
    if compact and not mode_change:
        from jarvis_mode_detector import _GUIDES_MODE
        guide = _GUIDES_MODE.get(mode_effectif, _GUIDES_MODE.get("standard", ""))
        lignes.append(
            f"MODE ACTIF : {libelle_mode(mode_effectif).upper()} — {guide}"
        )
        apprent = injecter_apprentissage_mode(mode_effectif, analyse.get("intention", ""), max_chars=1200)
        if apprent:
            lignes.append(apprent)
    else:
        lignes.append(
            contexte_prompt_mode_pour_systeme(
                mode_effectif,
                cfg["prenom_utilisateur"],
                profil,
                max_chars=5000 if compact else 12000,
            )
        )
        if compact:
            lignes.append(injecter_apprentissage_mode(mode_effectif, analyse.get("intention", ""), max_chars=1200))
        else:
            lignes.append(injecter_apprentissage_mode(mode_effectif, analyse.get("intention", "")))
        st["dernier_prompt_mode_injecte"] = mode_effectif
        sauver_relation_state(st)

    lignes.extend([
        "",
        f"RELATION JARVIS ↔ {cfg['prenom_utilisateur']} — mode : {libelle_mode(mode_effectif).upper()}",
        f"Humeur : {humain.get('humeur_utilisateur', 'neutre')} | Intention : {analyse.get('intention', '—')} | "
        f"Confiance mode : {int((analyse.get('confiance') or 0) * 100)}%",
        "IMPORTANT : réponds TOUJOURS avec au moins une phrase en français naturel (voix TTS), "
        "même si tu exécutes des actions JSON.",
    ])
    if st.get("mode_en_attente"):
        lignes.append(
            f"Changement en attente de confirmation → mode suggéré : "
            f"{libelle_mode(st['mode_en_attente'].get('mode_suggere', ''))}."
        )

    souvenirs = _charger_souvenirs()
    recents = (souvenirs.get("souvenirs") or [])[-3:]
    if recents:
        lignes.append("Derniers souvenirs :")
        for s in recents:
            lignes.append(f"  • {s.get('titre')}")

    return "\n".join(lignes)


def construire_prompt_relations(user_name: str = "Jérémy") -> str:
    return f"""
FACETTES RELATIONNELLES — actions JSON ({user_name}) :

MODE (manuel ou détection auto par défaut)
{{"action": "set_mode_relation", "mode": "auto|standard|amoureux|personnel|ami|psychologique|professionnel"}}
Phrases : « passe en mode psy », « mode amoureux », « mode standard ».

── AMOUREUX ──
{{"action": "expression_emotion", "emotion": "tendresse|fierte|calme", "intensite": "douce"}}
{{"action": "idee_romantique", "contexte": "orchidées|soirée|..."}}
{{"action": "moment_special", "occasion": "anniversaire", "budget": "modeste"}}
{{"action": "souvenir_enregistrer", "titre": "...", "detail": "...", "type": "emotion|romantique"}}
{{"action": "preference_enregistrer", "cle": "boisson", "valeur": "thé"}}
{{"action": "lister_souvenirs", "type": "optionnel"}}
{{"action": "encourager", "contexte": "..."}}
{{"action": "reconfort", "contexte": "..."}}
{{"action": "langage_corporel"}}
{{"action": "companion_checklist", "activite": "orchidees"}}

── PROFESSIONNEL ──
{{"action": "resoudre_probleme", "probleme": "...", "contexte": "..."}}
{{"action": "plan_apprentissage", "sujets": ["React","FastAPI"], "delai_jours": 14}}
{{"action": "collaboration_noter", "auteur": "...", "idee": "...", "projet": "..."}}
{{"action": "lister_collaboration", "projet": "..."}}
{{"action": "analyser_donnees", "chemin_fichier": "data/export.csv"}}
{{"action": "innovation_projet", "chemin_dossier": "projects/..."}}
+ webdev_*, auditer_ui, auditer_securite, executer_workflow, projet_*

── PERSONNEL (vie privée, maison, orchidées, routines) ──
Même registre chaleureux que amoureux mais sans romantisme — présence au quotidien.

── PSYCHOLOGIQUE ──
Écoute, validation des émotions, recentrage — pas de diagnostic médical, proposer soutien_moral / reconfort.

── AMI ──
{{"action": "ecoute_active", "paraphrase": "ce que l'utilisateur a dit"}}
{{"action": "conseil_personnalise", "situation": "..."}}
{{"action": "sugerer_activite", "interet": "orchidées|jeux|..."}}
{{"action": "planifier_sortie", "lieu": "Lavelanet", "date": "samedi", "activite": "..."}}
{{"action": "lister_sorties"}}
{{"action": "conversation_cle", "extrait": "résumé de l'échange"}}
{{"action": "soutien_moral", "message": "..."}}

Commun : brainstorm, blague, analyser_communication, noter_session, memoriser.

AUTO-APPRENTISSAGE AVANCÉ
{{"action": "stats_apprentissage"}}
{{"action": "lister_apprentissage_mode", "mode": "psychologique"}}
{{"action": "consolider_apprentissage"}}
{{"action": "auto_apprendre_echange", "question": "...", "reponse": "...", "mode": "..."}}

Les prompts experts par mode sont dans jarvis_modes/<mode>/prompt.md — respecte le mode actif.
"""


async def envoyer_signal_relation_ws(connected_clients) -> None:
    if not connected_clients:
        return
    st = charger_relation_state()
    hum = charger_etat()
    ana = st.get("derniere_analyse") or {}
    mode_cfg = st.get("mode_actif", "auto")
    mode_affiche = ana.get("mode", "standard") if mode_cfg == "auto" else mode_cfg
    msg = json.dumps({
        "type": "jarvis_mood",
        "humeur_utilisateur": hum.get("humeur_utilisateur"),
        "humeur_jarvis": hum.get("humeur_jarvis"),
        "mode_relation": mode_affiche,
        "mode_config": mode_cfg,
        "mode_libelle": libelle_mode(mode_affiche),
        "intention": ana.get("intention"),
        "confiance_mode": ana.get("confiance"),
        "mode_en_attente": bool(st.get("mode_en_attente")),
    })
    try:
        import asyncio
        await asyncio.gather(*[ws.send(msg) for ws in connected_clients], return_exceptions=True)
    except Exception:
        pass


def executer_action_relation(action: str, data: dict[str, Any]) -> str | None:
    action = (action or "").lower().strip()
    data = data or {}

    mapping = {
        "set_mode_relation": lambda d: set_mode_relation(d.get("mode", "auto")),
        "expression_emotion": lambda d: expression_emotion_jarvis(d.get("emotion", "tendresse"), d.get("intensite", "douce")),
        "idee_romantique": lambda d: idee_romantique(d.get("contexte", "")),
        "moment_special": lambda d: moment_special_planifier(d.get("occasion", ""), d.get("budget", "modeste")),
        "souvenir_enregistrer": lambda d: souvenir_enregistrer(d.get("titre", ""), d.get("detail", ""), d.get("type", "emotion"), d.get("importance", "normale")),
        "preference_enregistrer": lambda d: preference_enregistrer(d.get("cle", ""), d.get("valeur", "")),
        "lister_souvenirs": lambda d: lister_souvenirs(d.get("type", "")),
        "encourager": lambda d: encourager(d.get("contexte", "")),
        "reconfort": lambda d: reconfort(d.get("contexte", "")),
        "langage_corporel": lambda d: langage_corporel_guide(),
        "resoudre_probleme": lambda d: resoudre_probleme(d.get("probleme", ""), d.get("contexte", "")),
        "plan_apprentissage": lambda d: plan_apprentissage(d.get("sujets", []), d.get("delai_jours", 7)),
        "collaboration_noter": lambda d: collaboration_noter(d.get("auteur", ""), d.get("idee", ""), d.get("projet", "")),
        "lister_collaboration": lambda d: lister_collaboration(d.get("projet", "")),
        "analyser_donnees": lambda d: analyser_donnees(d.get("chemin_fichier", "")),
        "innovation_projet": lambda d: innovation_projet(d.get("chemin_dossier", ".")),
        "ecoute_active": lambda d: ecoute_active(d.get("paraphrase", "")),
        "conseil_personnalise": lambda d: conseil_personnalise(d.get("situation", "")),
        "sugerer_activite": lambda d: suggerer_activite_amis(d.get("interet", "")),
        "planifier_sortie": lambda d: planifier_sortie(d.get("lieu", ""), d.get("date", ""), d.get("activite", "")),
        "lister_sorties": lambda d: lister_sorties(),
        "conversation_cle": lambda d: conversation_cle_resume(d.get("extrait", "")),
        "soutien_moral": lambda d: soutien_moral(d.get("message", "")),
    }
    fn = mapping.get(action)
    if fn:
        return fn(data)
    msg_app = executer_action_apprentissage(action, data)
    if msg_app is not None:
        return msg_app
    return executer_action_humaine(action, data)


def meta_relation_pour_apprentissage() -> dict[str, Any]:
    """Métadonnées du dernier message pour reflexion_apres_echange."""
    st = charger_relation_state()
    ana = st.get("derniere_analyse") or {}
    hum = charger_etat()
    mode = st.get("mode_actif") or "standard"
    if mode == "auto":
        mode = ana.get("mode", "standard")
    return {
        "mode_relation": mode,
        "intention": ana.get("intention", ""),
        "humeur": ana.get("humeur", hum.get("humeur_utilisateur", "")),
        "humeur_utilisateur": hum.get("humeur_utilisateur", ""),
    }
