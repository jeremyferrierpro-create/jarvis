# -*- coding: utf-8 -*-
"""
Environnement Audio (Analyse du bruit ambiant)
Capacité pour JARVIS d'écouter en fond et de déterminer s'il y a de la musique,
du clavier (travail), ou du silence.

Nécessite: pip install sounddevice librosa numpy
"""
import os
import numpy as np

try:
    import sounddevice as sd
except ImportError:
    sd = None

try:
    import librosa
except ImportError:
    librosa = None

def ecouter_environnement(duree_sec=3.0, sample_rate=22050):
    """
    Enregistre un bref échantillon audio depuis le microphone par défaut.
    Retourne le tableau numpy audio.
    """
    if not sd:
        return None, "Module sounddevice non installé."
    
    try:
        audio = sd.rec(int(duree_sec * sample_rate), samplerate=sample_rate, channels=1, dtype='float32')
        sd.wait()
        return audio.flatten(), None
    except Exception as e:
        return None, str(e)

def analyser_contexte_sonore() -> dict:
    """
    Analyse l'audio courant et retourne un dictionnaire décrivant le contexte
    (volume général, type de bruit suspecté).
    """
    if not sd or not librosa:
        return {"erreur": "Bibliothèques audio manquantes (sounddevice, librosa)."}
    
    audio, err = ecouter_environnement()
    if err or audio is None:
        return {"erreur": f"Impossible d'écouter: {err}"}
    
    # Calcul du volume (RMS)
    rms = librosa.feature.rms(y=audio)
    volume_moyen = float(np.mean(rms))
    
    # Zero Crossing Rate (aide à distinguer voix/bruit percussif vs sons continus)
    zcr = librosa.feature.zero_crossing_rate(y=audio)
    zcr_moyen = float(np.mean(zcr))
    
    contexte = "silence"
    if volume_moyen > 0.01:
        if zcr_moyen > 0.1:
            contexte = "bruits_percussifs_ou_clavier"
        else:
            contexte = "voix_ou_musique_de_fond"
    elif volume_moyen > 0.005:
        contexte = "bruit_leger"

    return {
        "volume_rms": round(volume_moyen, 4),
        "zero_crossing_rate": round(zcr_moyen, 4),
        "contexte_estime": contexte
    }
