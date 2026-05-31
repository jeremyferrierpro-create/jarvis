"""
COMMANDES JARVIS — Configuration des voix et qualité audio.

Commandes vocales disponibles:
────────────────────────────────────────────────────────────────────────────
• "Liste les voix disponibles"
  → Affiche toutes les voix Edge TTS en français

• "Affiche la configuration des voix" / "Ma configuration vocal"
  → Affiche engine, voice_id, paramètres actuels

• "Change ma voix en [nom]"
  → Cherche et change la voix
  → Génère une démo audio

• "Utilise la voix [voice_id]"
  → Change la voix (ID format: ex: "fr-FR-DeniseNeural")

• "Utilise le moteur [edge|pyttsx3|xtts|fish_speech]"
  → Change le moteur TTS

• "Crée une démo de ta voix"
  → Génère un fichier audio de démonstration

• "Applique la vitesse +20%" / "-20%"
  → Change la vitesse du TTS

• "Augmente/Baisse le volume de ta voix"
  → Change le volume de la synthèse (Edge/pyttsx3)

────────────────────────────────────────────────────────────────────────────
"""

import asyncio
import os
import json
from typing import Optional

try:
    from tts_engine import (
        charger_config_tts,
        get_voice_id, get_engine, set_voice_id, set_engine,
        lister_voix, lister_voix_edge, lister_voix_reference, lister_voix_pyttsx3,
        creer_demo_voix, afficher_config,
        EDGE_VOICES_PRESETS, DEFAULT_TTS, ENGINES
    )
    _VOICE_CONFIG_OK = True
except ImportError as e:
    _VOICE_CONFIG_OK = False
    print(f"[ERREUR] Impossible charger tts_engine: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# COMMANDES JARVIS
# ─────────────────────────────────────────────────────────────────────────────

async def jarvis_voix_afficher_config() -> str:
    """Affiche la configuration actuelle des voix."""
    if not _VOICE_CONFIG_OK:
        return "❌ Module de configuration des voix non disponible"
    
    return afficher_config()


async def jarvis_voix_liste() -> str:
    """Liste les voix disponibles."""
    if not _VOICE_CONFIG_OK:
        return "❌ Module de configuration des voix non disponible"
    
    config = charger_config_tts()
    engine = config.get("engine", "edge")
    
    result = [
        "",
        "🎤 VOIX DISPONIBLES",
        "═" * 60,
        f"Moteur actuel : {engine}",
        "",
    ]
    
    try:
        voix = await lister_voix(engine)
        result.append(f"Voix disponibles pour le moteur '{engine}' ({len(voix)}):")
        for i, v in enumerate(voix[:15], 1):
            gender = f" [{v.get('gender', '?')}]" if v.get('gender') else ""
            result.append(f"  {i:2d}. {v['label']:<45} {gender}")
        if len(voix) > 15:
            result.append(f"  ... et {len(voix) - 15} autres")
    except Exception as e:
        result.append(f"⚠️  Erreur listage des voix: {e}")
    
    # Lister les voix de référence (XTTS, Fish Speech)
    try:
        refs = lister_voix_reference()
        if refs:
            result.append(f"\nVoix de référence (XTTS/Fish - {len(refs)} fichiers):")
            for r in refs:
                result.append(f"  • {r['label']}")
    except Exception as e:
        pass
    
    result.append("═" * 60)
    return "\n".join(result)


async def jarvis_voix_changer(voice_id_ou_nom: str) -> str:
    """Change la voix actuelle par ID ou nom."""
    if not _VOICE_CONFIG_OK:
        return "❌ Module de configuration des voix non disponible"
    
    voice_id_ou_nom = voice_id_ou_nom.strip().lower()
    
    # Récupérer la config actuelle
    config = charger_config_tts()
    
    # Chercher la voix par nom partiel dans le moteur actif
    voix_list = await lister_voix(config.get("engine", "edge"))
    voix_trouvees = []
    
    for v in voix_list:
        label_lower = v["label"].lower()
        id_lower = v["id"].lower()
        if voice_id_ou_nom in label_lower or voice_id_ou_nom in id_lower:
            voix_trouvees.append(v)
    
    if not voix_trouvees:
        # Essayer exact match
        for v in voix_list:
            if v["id"].lower() == voice_id_ou_nom:
                voix_trouvees = [v]
                break
    
    if not voix_trouvees:
        return f"❌ Voix '{voice_id_ou_nom}' non trouvée. Utilise 'Liste les voix disponibles' pour voir les options."
    
    voix = voix_trouvees[0]
    new_voice_id = voix["id"]
    
    # Sauvegarder
    if not set_voice_id(new_voice_id):
        return f"❌ Erreur sauvegarde de la voix"
    
    result = [
        f"✓ Voix changée en : {voix['label']}",
        f"  ID: {new_voice_id}",
    ]
    
    # Tenter de créer une démo
    try:
        demo_path = await creer_demo_voix()
        if demo_path and os.path.exists(demo_path):
            result.append(f"\n🎵 Démo générée : {demo_path}")
    except Exception as e:
        result.append(f"\n⚠️  Impossible créer la démo : {e}")
    
    return "\n".join(result)


async def jarvis_voix_moteur(engine_name: str) -> str:
    """Change le moteur TTS."""
    if not _VOICE_CONFIG_OK:
        return "❌ Module de configuration des voix non disponible"
    
    engine_name = engine_name.strip().lower()
    
    if engine_name not in ENGINES:
        engines_list = ", ".join(ENGINES)
        return f"❌ Moteur invalide: {engine_name}\nMoteurs disponibles: {engines_list}"
    
    if not set_engine(engine_name):
        return f"❌ Erreur changement moteur"
    
    return f"✓ Moteur TTS changé en : {engine_name}"


async def jarvis_voix_demo() -> str:
    """Crée une démo audio avec la voix actuelle."""
    if not _VOICE_CONFIG_OK:
        return "❌ Module de configuration des voix non disponible"
    
    config = charger_config_tts()
    voice_id = config.get("voice_id", "fr-FR-HenriNeural")
    engine = config.get("engine", "edge")
    
    result = [
        f"🎤 Création démo audio",
        f"   Engine: {engine}",
        f"   Voice: {voice_id}",
        "",
    ]
    
    try:
        demo_path = await creer_demo_voix()
        if demo_path and os.path.exists(demo_path):
            size_mb = os.path.getsize(demo_path) / (1024 * 1024)
            result.append(f"✓ Démo générée avec succès")
            result.append(f"   Fichier: {os.path.basename(demo_path)}")
            result.append(f"   Taille: {size_mb:.2f} MB")
            return "\n".join(result)
        else:
            return "❌ Erreur création démo (fichier non créé)"
    except Exception as e:
        return f"❌ Erreur création démo : {e}"


async def jarvis_voix_vitesse(direction: str, pourcentage: int = 20) -> str:
    """Change la vitesse du TTS."""
    if not _VOICE_CONFIG_OK:
        return "❌ Module de configuration des voix non disponible"
    
    config = charger_config_tts()
    engine = config.get("engine", "edge")
    
    direction = direction.strip().lower()
    if direction not in ["augmenter", "augmente", "plus", "baisse", "baisser", "moins"]:
        return f"❌ Direction invalide: {direction}"
    
    if engine == "edge":
        current = config.get("edge_tts_rate", "+0%")
        # Parser le courant
        try:
            current_val = int(current.replace("%", "").replace("+", ""))
        except:
            current_val = 0
        
        if direction in ["augmenter", "augmente", "plus"]:
            new_val = current_val + pourcentage
        else:
            new_val = current_val - pourcentage
        
        new_val = max(-100, min(100, new_val))  # Limiter entre -100% et +100%
        new_rate = f"{new_val:+d}%"
        
        from tts_engine import sauvegarder_config_tts
        sauvegarder_config_tts({"edge_tts_rate": new_rate})
        return f"✓ Vitesse Edge TTS changée : {new_rate}"
    
    elif engine == "pyttsx3":
        current_rate = config.get("pyttsx3_rate", 150)
        
        if direction in ["augmenter", "augmente", "plus"]:
            new_rate = current_rate + 10
        else:
            new_rate = current_rate - 10
        
        new_rate = max(50, min(300, new_rate))  # Limiter entre 50 et 300 WPM
        
        from tts_engine import sauvegarder_config_tts
        sauvegarder_config_tts({"pyttsx3_rate": new_rate})
        return f"✓ Vitesse pyttsx3 changée : {new_rate} WPM"
    
    else:
        return f"⚠️  Vitesse non configurable pour engine {engine}"


async def jarvis_voix_volume(direction: str, pourcentage: float = 10.0) -> str:
    """Change le volume du TTS."""
    if not _VOICE_CONFIG_OK:
        return "❌ Module de configuration des voix non disponible"
    
    config = charger_config_tts()
    engine = config.get("engine", "edge")
    
    direction = direction.strip().lower()
    if direction not in ["augmenter", "augmente", "plus", "baisse", "baisser", "moins"]:
        return f"❌ Direction invalide: {direction}"
    
    if engine == "edge":
        current = config.get("edge_tts_volume", "+0%")
        try:
            current_val = int(current.replace("%", "").replace("+", ""))
        except:
            current_val = 0
        
        if direction in ["augmenter", "augmente", "plus"]:
            new_val = current_val + int(pourcentage)
        else:
            new_val = current_val - int(pourcentage)
        
        new_val = max(-100, min(100, new_val))
        new_volume = f"{new_val:+d}%"
        
        from tts_engine import sauvegarder_config_tts
        sauvegarder_config_tts({"edge_tts_volume": new_volume})
        return f"✓ Volume Edge TTS changé : {new_volume}"
    
    elif engine == "pyttsx3":
        current_vol = config.get("pyttsx3_volume", 0.9)
        
        if direction in ["augmenter", "augmente", "plus"]:
            new_vol = current_vol + (pourcentage / 100)
        else:
            new_vol = current_vol - (pourcentage / 100)
        
        new_vol = max(0.0, min(1.0, new_vol))
        
        from tts_engine import sauvegarder_config_tts
        sauvegarder_config_tts({"pyttsx3_volume": new_vol})
        return f"✓ Volume pyttsx3 changé : {new_vol * 100:.0f}%"
    
    else:
        return f"⚠️  Volume non configurable pour engine {engine}"


# ─────────────────────────────────────────────────────────────────────────────
# ROUTING DES COMMANDES JARVIS
# ─────────────────────────────────────────────────────────────────────────────

async def traiter_commande_voix(commande: str, args: list = None) -> Optional[str]:
    """
    Traite les commandes JARVIS liées aux voix.
    
    Retourne la réponse ou None si la commande n'est pas reconnue.
    """
    if not _VOICE_CONFIG_OK:
        return None
    
    commande_lower = commande.lower().strip()
    args = args or []
    
    # Liste des voix
    if any(x in commande_lower for x in [
        "liste les voix", "liste voix", "quelles voix",
        "voix disponibles", "les voix disponibles"
    ]):
        return await jarvis_voix_liste()
    
    # Afficher config
    elif any(x in commande_lower for x in [
        "affiche la config", "configuration voix", "ma config vocal",
        "affiche ma voix", "quelle est ma voix"
    ]):
        return await jarvis_voix_afficher_config()
    
    # Changer voix
    elif any(x in commande_lower for x in [
        "change ma voix", "change ta voix", "utilise la voix",
        "mets la voix"
    ]):
        # Extraire le nom de la voix après la commande
        for keyword in ["change ma voix en", "change ta voix en", "utilise la voix", "mets la voix"]:
            if keyword in commande_lower:
                voice_part = commande_lower.split(keyword)[-1].strip()
                if voice_part:
                    return await jarvis_voix_changer(voice_part)
        
        if args:
            return await jarvis_voix_changer(args[0])
        return "⚠️  Précise le nom de la voix (ex: 'Change ma voix en Denise')"
    
    # Moteur TTS
    elif any(x in commande_lower for x in [
        "utilise le moteur", "utilise moteur", "active le moteur",
        "engine", "tts moteur"
    ]):
        for keyword in ["utilise le moteur", "utilise moteur", "active le moteur"]:
            if keyword in commande_lower:
                engine_part = commande_lower.split(keyword)[-1].strip()
                if engine_part:
                    return await jarvis_voix_moteur(engine_part)
        
        if args:
            return await jarvis_voix_moteur(args[0])
        return "⚠️  Spécifie le moteur (edge, pyttsx3, xtts, fish_speech)"
    
    # Démo voix
    elif any(x in commande_lower for x in [
        "crée une démo", "demo voix", "demo ta voix",
        "exemple ta voix", "écoute ta voix"
    ]):
        return await jarvis_voix_demo()

    # Vitesse
    elif any(x in commande_lower for x in [
        "vitesse", "plus vite", "moins vite", "augmente la vitesse",
        "baisse la vitesse"
    ]):
        direction = "augmenter" if any(x in commande_lower for x in [
            "plus vite", "augmente", "accélère"
        ]) else "baisser"
        return await jarvis_voix_vitesse(direction)
    
    # Volume
    elif any(x in commande_lower for x in [
        "volume de ta voix", "augmente ta voix", "baisse ta voix",
        "parle plus fort", "parle moins fort"
    ]):
        direction = "augmenter" if any(x in commande_lower for x in [
            "augmente", "plus fort", "plus loud"
        ]) else "baisser"
        return await jarvis_voix_volume(direction)

    # Pas reconnue
    return None


if __name__ == "__main__":
    print(__doc__)
    print("\n[Pour tester les commandes, intègre ce module dans main2.py]")
