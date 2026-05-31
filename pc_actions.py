"""
Actions PC exécutables par JARVIS (JSON → Windows).
"""
from __future__ import annotations

import os
import subprocess
import shutil
import webbrowser
from datetime import datetime
from typing import Any

try:
    import psutil
except ImportError:
    psutil = None

try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    import pyperclip
except ImportError:
    pyperclip = None

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    from ctypes import cast, POINTER
    _PYCAW_OK = True
except ImportError:
    _PYCAW_OK = False

try:
    import screen_brightness_control as sbc
    _SBC_OK = True
except ImportError:
    sbc = None
    _SBC_OK = False

from app_launcher import _APPS_CATALOGUE, _boulot_lancer, _fermer_app
from file_manager import resoudre_chemin

JARVIS_ROOT = os.path.dirname(os.path.abspath(__file__))

_APPS_WINDOWS = {
    "calculatrice": "calc",
    "calc": "calc",
    "notepad": "notepad",
    "bloc-notes": "notepad",
    "bloc notes": "notepad",
    "paint": "mspaint",
    "gestionnaire de taches": "taskmgr",
    "gestionnaire de tâches": "taskmgr",
    "task manager": "taskmgr",
    "parametres": "ms-settings:",
    "paramètres": "ms-settings:",
    "reglages": "ms-settings:",
    "réglages": "ms-settings:",
    "explorateur": "explorer",
    "explorateur de fichiers": "explorer",
    "cmd": "cmd",
    "invite de commande": "cmd",
    "powershell": "powershell",
    "terminal": "wt",
    "snipping tool": "SnippingTool",
    "capture": "SnippingTool",
    "enregistreur vocal": "SoundRecorder",
    "nettoyage de disque": "cleanmgr",
    "informations systeme": "msinfo32",
    "informations système": "msinfo32",
    "panneau de configuration": "control",
}


def _volume_iface():
    if not _PYCAW_OK:
        return None
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))
    except Exception:
        return None


def _volume_fallback_keys(direction: str, steps: int = 5) -> str:
    if not pyautogui:
        return "PyAutoGUI absent — impossible de régler le volume."
    key = {"monter": "volumeup", "baisser": "volumedown", "couper": "volumemute"}.get(direction)
    if not key:
        return "Direction volume inconnue."
    for _ in range(max(1, steps)):
        pyautogui.press(key)
    labels = {"monter": "augmenté", "baisser": "baissé", "couper": "coupé (mute)"}
    return f"Volume {labels[direction]}."


def action_volume(direction: str = "monter", pourcentage: int | None = None, paliers: int = 1) -> str:
    vol = _volume_iface()
    direction = (direction or "monter").lower().strip()

    if direction in ("couper", "mute", "silence"):
        if vol:
            vol.SetMute(1, None)
            return "Son coupé."
        return _volume_fallback_keys("couper")

    if direction in ("reactiver", "unmute", "activer"):
        if vol:
            vol.SetMute(0, None)
            return "Son réactivé."
        return "Son réactivé."

    if pourcentage is not None:
        pct = max(0, min(100, int(pourcentage)))
        if vol:
            vol.SetMasterVolumeLevelScalar(pct / 100.0, None)
            vol.SetMute(0, None)
            return f"Volume réglé à {pct}%."
        return _volume_fallback_keys("monter" if pct > 50 else "baisser", max(1, abs(pct - 50) // 10))

    step = 0.05 * max(1, int(paliers))
    if vol:
        cur = vol.GetMasterVolumeLevelScalar()
        if direction in ("monter", "augmenter", "hausse", "plus"):
            new_v = min(1.0, cur + step)
        elif direction in ("baisser", "diminuer", "reduire", "réduire", "moins"):
            new_v = max(0.0, cur - step)
        else:
            return f"Direction volume inconnue : {direction}"
        vol.SetMasterVolumeLevelScalar(new_v, None)
        vol.SetMute(0, None)
        return f"Volume à {int(new_v * 100)}%."
    fb = "monter" if direction in ("monter", "augmenter", "hausse", "plus") else "baisser"
    return _volume_fallback_keys(fb, max(1, int(paliers)))


def action_luminosite(direction: str = "monter", pourcentage: int | None = None) -> str:
    if not _SBC_OK or not sbc:
        return "Module luminosité absent — pip install screen-brightness-control"
    try:
        if pourcentage is not None:
            pct = max(0, min(100, int(pourcentage)))
            sbc.set_brightness(pct)
            return f"Luminosité réglée à {pct}%."
        cur = sbc.get_brightness(display=0)
        if isinstance(cur, list):
            cur = cur[0]
        direction = (direction or "monter").lower()
        if direction in ("monter", "augmenter", "plus", "max"):
            new_b = 100 if direction == "max" else min(100, cur + 15)
        elif direction in ("baisser", "diminuer", "moins", "min"):
            new_b = 0 if direction == "min" else max(0, cur - 15)
        else:
            return f"Direction luminosité inconnue : {direction}"
        sbc.set_brightness(new_b)
        return f"Luminosité à {new_b}%."
    except Exception as e:
        return f"Impossible de régler la luminosité : {e}"


def _trouver_app(nom: str):
    key = (nom or "").lower().strip()
    if not key:
        return None, None
    if key in _APPS_CATALOGUE:
        return key, _APPS_CATALOGUE[key]
    for cle, info in _APPS_CATALOGUE.items():
        if info.get("is_custom"):
            continue
        label = (info.get("label") or cle).lower()
        if key == label or key in label or label in key:
            return cle, info
    return None, None


def action_ouvrir_app(nom: str) -> str:
    key = (nom or "").lower().strip()
    if not key:
        return "Quelle application souhaitez-vous ouvrir ?"

    if key in _APPS_WINDOWS:
        try:
            subprocess.Popen(_APPS_WINDOWS[key], shell=True)
            return f"{nom} ouvert."
        except Exception as e:
            return f"Impossible d'ouvrir {nom} : {e}"

    _, info = _trouver_app(nom)
    if info:
        ok = _boulot_lancer(info.get("label", nom), info.get("noms", []), info.get("hints"))
        return f"{info.get('label', nom)} ouvert." if ok else f"{nom} introuvable sur ce PC."

    return f"Application « {nom} » inconnue. Dites « liste les applications » pour voir le catalogue."


def action_fermer_app(nom: str) -> str:
    _, info = _trouver_app(nom)
    if not info:
        return f"Je ne sais pas fermer « {nom} »."
    ok = _fermer_app(info.get("noms", []))
    return f"{info.get('label', nom)} fermé." if ok else f"Aucune fenêtre {nom} active."


def action_ouvrir_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return "Quelle URL ouvrir ?"
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    return f"J'ouvre {url}."


def action_ouvrir_fichier(chemin: str) -> str:
    path = resoudre_chemin(chemin) if chemin else None
    if not path:
        path = os.path.expanduser(chemin or "")
    if not path or not os.path.exists(path):
        return f"Fichier introuvable : {chemin}"
    os.startfile(path)
    return f"Fichier ouvert : {os.path.basename(path)}."


def action_capture_ecran(chemin: str | None = None) -> str:
    if not pyautogui:
        return "Capture impossible — pyautogui absent."
    dest = chemin or os.path.join(os.environ.get("USERPROFILE", ""), "Desktop", f"jarvis_capture_{datetime.now():%Y%m%d_%H%M%S}.png")
    dest = os.path.expanduser(dest)
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    pyautogui.screenshot(dest)
    return f"Capture enregistrée sur le bureau : {os.path.basename(dest)}."


def action_info_systeme() -> str:
    parts = []
    now = datetime.now()
    parts.append(f"Nous sommes le {now:%d/%m/%Y}, il est {now:%H:%M}.")
    if psutil:
        cpu = psutil.cpu_percent(interval=0.3)
        ram = psutil.virtual_memory()
        parts.append(f"Processeur à {cpu:.0f}%, mémoire à {ram.percent:.0f}%.")
        try:
            disk = psutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\")
            parts.append(f"Disque système : {disk.percent:.0f}% utilisé, {disk.free // (1024**3)} Go libres.")
        except Exception:
            pass
        try:
            bat = psutil.sensors_battery()
            if bat:
                plugged = "branché" if bat.power_plugged else "sur batterie"
                parts.append(f"Batterie : {bat.percent:.0f}%, {plugged}.")
        except Exception:
            pass
    else:
        parts.append("Installez psutil pour CPU/RAM détaillés.")
    return " ".join(parts)


def action_alimentation(commande: str, delai_secondes: int = 0, confirme: bool = False) -> str:
    cmd = (commande or "").lower().strip()
    delai = max(0, int(delai_secondes or 0))

    if cmd == "annuler":
        subprocess.Popen("shutdown /a", shell=True)
        return "Arrêt ou redémarrage annulé."

    if cmd in ("verrouiller", "lock"):
        subprocess.Popen("rundll32.exe user32.dll,LockWorkStation", shell=True)
        return "Session verrouillée."

    if cmd in ("veille", "sleep", "suspendre"):
        if delai > 0:
            subprocess.Popen(f"shutdown /h /t {delai}", shell=True)
            return f"Mise en veille dans {delai // 60 or 1} minute(s)."
        subprocess.Popen("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
        return "Mise en veille."

    if cmd in ("extinction", "shutdown", "eteindre", "éteindre"):
        if delai <= 0 and not confirme:
            return "Extinction immédiate : renvoyez l'action avec confirme true ou un delai_secondes."
        t = delai if delai > 0 else 10
        subprocess.Popen(f"shutdown /s /t {t}", shell=True)
        return f"Extinction dans {t} secondes."

    if cmd in ("redemarrage", "redémarrage", "reboot", "restart"):
        t = delai if delai > 0 else 30
        subprocess.Popen(f"shutdown /r /t {t}", shell=True)
        return f"Redémarrage dans {t} secondes."

    return f"Commande alimentation inconnue : {commande}"


def action_presse_papier(mode: str = "lire", texte: str | None = None) -> str:
    if not pyperclip:
        return "pyperclip absent — pip install pyperclip"
    mode = (mode or "lire").lower()
    if mode in ("copier", "ecrire", "écrire", "coller"):
        if not texte:
            return "Aucun texte à copier."
        pyperclip.copy(texte)
        return "Texte copié dans le presse-papier."
    contenu = pyperclip.paste()
    if not contenu:
        return "Le presse-papier est vide."
    return f"Presse-papier : {contenu[:500]}"


def action_raccourci(touches: list | str) -> str:
    if not pyautogui:
        return "PyAutoGUI absent."
    if isinstance(touches, str):
        touches = [t.strip() for t in touches.replace("+", ",").split(",") if t.strip()]
    if not touches:
        return "Aucun raccourci spécifié."
    try:
        if len(touches) == 1:
            pyautogui.press(touches[0].lower())
        else:
            pyautogui.hotkey(*[t.lower() for t in touches])
        return f"Raccourci {'+'.join(touches)} exécuté."
    except Exception as e:
        return f"Raccourci impossible : {e}"


def action_vider_corbeille() -> str:
    try:
        import winshell
        winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=False)
        return "Corbeille vidée."
    except ImportError:
        subprocess.run(
            'PowerShell -Command "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"',
            shell=True,
            capture_output=True,
        )
        return "Corbeille vidée."
    except Exception as e:
        return f"Impossible de vider la corbeille : {e}"


def action_minimiser_fenetres() -> str:
    if not pyautogui:
        return "PyAutoGUI absent."
    pyautogui.hotkey("win", "d")
    return "Toutes les fenêtres minimisées — bureau affiché."


def action_ouvrir_youtube(recherche: str | None = None, url: str | None = None) -> str:
    if url:
        return action_ouvrir_url(url)
    if recherche:
        q = recherche.replace(" ", "+")
        return action_ouvrir_url(f"https://www.youtube.com/results?search_query={q}")
    return action_ouvrir_url("https://www.youtube.com")


def action_lister_processus(limite: int = 8) -> str:
    if not psutil:
        return "psutil absent."
    procs = []
    for p in psutil.process_iter(["name", "memory_info"]):
        try:
            mem = p.info["memory_info"].rss if p.info.get("memory_info") else 0
            procs.append((mem, p.info.get("name", "?")))
        except Exception:
            pass
    procs.sort(reverse=True)
    top = procs[: max(3, min(20, limite))]
    lines = [f"{name} ({mem // (1024**2)} Mo)" for mem, name in top]
    return "Processus les plus gourmands : " + ", ".join(lines) + "."


def action_fermer_processus(nom: str) -> str:
    if not psutil or not nom:
        return "Nom de processus requis."
    nom_low = nom.lower().replace(".exe", "")
    tues = 0
    for p in psutil.process_iter(["name"]):
        try:
            pname = (p.info.get("name") or "").lower()
            if nom_low in pname:
                p.terminate()
                tues += 1
        except Exception:
            pass
    return f"{tues} processus « {nom} » terminé(s)." if tues else f"Aucun processus « {nom} » trouvé."


def liste_apps_pour_prompt(max_items: int = 40) -> str:
    seen = set()
    labels = []
    for cle, info in sorted(_APPS_CATALOGUE.items()):
        if info.get("is_custom"):
            label = info.get("label", cle)
            if label.lower() not in seen:
                seen.add(label.lower())
                labels.append(label)
            continue
        if " " in cle and cle in _APPS_CATALOGUE and _APPS_CATALOGUE.get(cle) is info:
            continue
        label = info.get("label", cle)
        if label.lower() in seen:
            continue
        seen.add(label.lower())
        labels.append(label)
        if len(labels) >= max_items:
            break
    extra = ", calculatrice, bloc-notes, paint, terminal, paramètres, explorateur"
    return ", ".join(labels[:max_items]) + extra


def construire_prompt_actions_pc(user_name: str = "Jérémy") -> str:
    apps = liste_apps_pour_prompt()
    return f"""
CONTRÔLE PC WINDOWS (actions JSON — utilise-les pour piloter l'ordinateur de {user_name}) :
{{"action": "ouvrir_app", "nom": "NOM_APP"}}
{{"action": "fermer_app", "nom": "NOM_APP"}}
Apps disponibles (exemples) : {apps}

{{"action": "volume_systeme", "direction": "monter|baisser|couper|reactiver", "pourcentage": null, "paliers": 4}}
{{"action": "luminosite", "direction": "monter|baisser|max|min", "pourcentage": null}}

{{"action": "ouvrir_url", "url": "https://..."}}
{{"action": "ouvrir_fichier", "chemin": "bureau/rapport.pdf ou chemin complet"}}
{{"action": "ouvrir_youtube", "recherche": "requête", "url": "optionnel"}}

{{"action": "capture_ecran", "chemin": "optionnel"}}
{{"action": "dictee", "texte": "texte à taper au curseur"}}

{{"action": "info_systeme"}}
{{"action": "lister_processus", "limite": 8}}
{{"action": "fermer_processus", "nom": "chrome"}}

{{"action": "alimentation_pc", "commande": "veille|extinction|redemarrage|annuler|verrouiller", "delai_secondes": 0, "confirme": false}}
Note : extinction immédiate requiert confirme true.

{{"action": "presse_papier", "mode": "lire|copier", "texte": "si copier"}}
{{"action": "raccourci_clavier", "touches": ["ctrl", "c"]}}
{{"action": "vider_corbeille"}}
{{"action": "minimiser_fenetres"}}
{{"action": "mode_boulot"}}

{{"action": "ouvrir_dossier", "chemin": "bureau/documents/downloads"}}
{{"action": "lister_dossier"}} | trier_par_type | trier_par_date | chercher_fichier

Exemples vocaux → JSON :
- « Ouvre Chrome » → ouvrir_app
- « Ferme Discord » → fermer_app
- « Monte le volume à 50% » → volume_systeme pourcentage 50
- « Capture d'écran » → capture_ecran
- « Verrouille le PC » → alimentation_pc verrouiller
- « Mode boulot » → mode_boulot
"""


def executer_action_pc(action: str, data: dict[str, Any]) -> str | None:
    """Exécute une action PC JSON. Retourne un message vocal ou None si action inconnue."""
    action = (action or "").lower().strip()

    if action == "ouvrir_app":
        return action_ouvrir_app(data.get("nom", ""))
    if action == "fermer_app":
        return action_fermer_app(data.get("nom", ""))
    if action == "volume_systeme":
        return action_volume(
            data.get("direction", "monter"),
            data.get("pourcentage"),
            data.get("paliers", 1),
        )
    if action == "luminosite":
        return action_luminosite(data.get("direction", "monter"), data.get("pourcentage"))
    if action == "ouvrir_url":
        return action_ouvrir_url(data.get("url", ""))
    if action == "ouvrir_fichier":
        return action_ouvrir_fichier(data.get("chemin", ""))
    if action == "ouvrir_youtube":
        return action_ouvrir_youtube(data.get("recherche"), data.get("url"))
    if action == "capture_ecran":
        return action_capture_ecran(data.get("chemin"))
    if action == "info_systeme":
        return action_info_systeme()
    if action == "alimentation_pc":
        return action_alimentation(
            data.get("commande", ""),
            data.get("delai_secondes", 0),
            bool(data.get("confirme", False)),
        )
    if action == "presse_papier":
        return action_presse_papier(data.get("mode", "lire"), data.get("texte"))
    if action == "raccourci_clavier":
        return action_raccourci(data.get("touches", []))
    if action == "vider_corbeille":
        return action_vider_corbeille()
    if action == "minimiser_fenetres":
        return action_minimiser_fenetres()
    if action == "lister_processus":
        return action_lister_processus(data.get("limite", 8))
    if action == "fermer_processus":
        return action_fermer_processus(data.get("nom", ""))

    return None
