import os
import time
import json
import asyncio

try:
    import pyautogui
except ImportError:
    pyautogui = None
try:
    import requests
except ImportError:
    requests = None
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Rempli par main2.py via builtins (client, CHOSEN_MODEL) ou valeurs par défaut Gemini
VISION_MODEL = "gemini-2.5-flash"


def _vision_client():
    import builtins
    return getattr(builtins, "client", None)


def _vision_model():
    import builtins
    m = getattr(builtins, "CHOSEN_MODEL", VISION_MODEL)
    if m and "gpt" in str(m).lower():
        return VISION_MODEL
    return m or VISION_MODEL


def _open_image(path):
    from PIL import Image
    return Image.open(path)


async def jarvis_vision_cliquer(instruction):
    try:
        if not pyautogui:
            return "pyautogui n'est pas installé, Mickael."
        client = _vision_client()
        if not client:
            return "La vision nécessite une clé Gemini configurée, Mickael."
        time.sleep(0.5)
        path_ss = "jarvis_vision_temp.png"
        screenshot = pyautogui.screenshot()
        screenshot.save(path_ss)
        img_w, img_h = screenshot.size
        img = _open_image(path_ss)
        prompt_vision = (
            f"Tu es l'oeil de JARVIS. Voici une capture de l'écran ({img_w}x{img_h} pixels).\n"
            f"Instruction : {instruction}\n"
            "Trouve l'élément demandé sur l'écran.\n"
            "Réponds UNIQUEMENT en JSON :\n"
            '{"box": [ymin, xmin, ymax, xmax], "description": "description courte"}\n'
            "Coordonnées normalisées 0 à 1000."
        )
        response = client.models.generate_content(
            model=_vision_model(), contents=[prompt_vision, img]
        )
        rep_text = response.text.strip()
        print(f"[VISION] Gemini a renvoyé : {rep_text}")
        start = rep_text.find("{")
        end = rep_text.rfind("}")
        if start != -1 and end != -1:
            rep_text = rep_text[start : end + 1]
        data = json.loads(rep_text)

        box = data.get("box", [500, 500, 500, 500])
        ymin, xmin, ymax, xmax = box
        center_y = (ymin + ymax) / 2
        center_x = (xmin + xmax) / 2
        target_x = int((center_x / 1000) * img_w)
        target_y = int((center_y / 1000) * img_h)

        print(f"[VISION] Cible : {data.get('description', 'inconnu')} à ({target_x}, {target_y})")
        pyautogui.moveTo(target_x, target_y, duration=0.5)
        time.sleep(0.2)
        t_inst = instruction.lower()
        if any(k in t_inst for k in ["musique", "chanson", "piste", "numéro", "numero", "titre"]):
            pyautogui.doubleClick()
        else:
            pyautogui.click()

        if os.path.exists(path_ss):
            os.remove(path_ss)
        desc = data.get("description", instruction)
        return f"C'est fait, j'ai cliqué sur : {desc}."
    except Exception as e:
        print(f"[VISION ERROR] {e}")
        return "Je n'ai pas réussi à identifier l'élément sur l'écran."


async def jarvis_vision_ecrire(instruction, texte_a_taper):
    try:
        import pyperclip
        if not pyautogui:
            return "pyautogui n'est pas installé."
        client = _vision_client()
        if not client:
            return "La vision nécessite Gemini."
        path_ss = "jarvis_vision_temp.png"
        screenshot = pyautogui.screenshot()
        screenshot.save(path_ss)
        img_w, img_h = screenshot.size
        img = _open_image(path_ss)
        prompt_vision = (
            f"Trouve le champ de saisie : {instruction}. Résolution {img_w}x{img_h}.\n"
            'Réponds UNIQUEMENT en JSON : {"box": [ymin, xmin, ymax, xmax], "description": "..."}'
        )
        response = client.models.generate_content(model=_vision_model(), contents=[prompt_vision, img])
        rep_text = response.text.strip()
        start, end = rep_text.find("{"), rep_text.rfind("}")
        if start != -1 and end != -1:
            rep_text = rep_text[start : end + 1]
        data = json.loads(rep_text)
        box = data.get("box", [500, 500, 500, 500])
        ymin, xmin, ymax, xmax = box
        target_x = int(((xmin + xmax) / 2 / 1000) * img_w)
        target_y = int(((ymin + ymax) / 2 / 1000) * img_h)
        pyautogui.moveTo(target_x, target_y, duration=0.5)
        time.sleep(0.15)
        pyautogui.click()
        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.1)
        pyperclip.copy(texte_a_taper)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.1)
        pyautogui.press("enter")
        if os.path.exists(path_ss):
            os.remove(path_ss)
        return f"J'ai saisi le texte dans {instruction}."
    except Exception as e:
        print(f"[VISION ERROR] {e}")
        return "Impossible de taper dans le champ demandé."


async def jarvis_vision_rechercher_sur_site(texte_recherche):
    try:
        import pyperclip
        if not pyautogui:
            return "pyautogui n'est pas installé."
        client = _vision_client()
        if not client:
            return "La vision nécessite Gemini."
        path_ss = "jarvis_vision_temp.png"
        screenshot = pyautogui.screenshot()
        screenshot.save(path_ss)
        img_w, img_h = screenshot.size
        img = _open_image(path_ss)
        prompt_vision = (
            f"Localise la barre de recherche du site affiché ({img_w}x{img_h}).\n"
            'JSON uniquement : {"box": [ymin, xmin, ymax, xmax], "description": "..."}'
        )
        response = client.models.generate_content(model=_vision_model(), contents=[prompt_vision, img])
        rep_text = response.text.strip()
        start, end = rep_text.find("{"), rep_text.rfind("}")
        if start != -1 and end != -1:
            rep_text = rep_text[start : end + 1]
        data = json.loads(rep_text)
        box = data.get("box", [500, 500, 500, 500])
        ymin, xmin, ymax, xmax = box
        target_x = int(((xmin + xmax) / 2 / 1000) * img_w)
        target_y = int(((ymin + ymax) / 2 / 1000) * img_h)
        pyautogui.moveTo(target_x, target_y, duration=0.5)
        time.sleep(0.15)
        pyautogui.click()
        time.sleep(0.35)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.1)
        pyperclip.copy(texte_recherche)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.15)
        pyautogui.press("enter")
        if os.path.exists(path_ss):
            os.remove(path_ss)
        return f"Recherche '{texte_recherche}' lancée sur le site."
    except Exception as e:
        print(f"[VISION ERROR] {e}")
        return "Je n'ai pas trouvé la barre de recherche sur cette page."


async def jarvis_vision_camera(texte_utilisateur):
    """Capture une image webcam et l'analyse avec Gemini."""
    try:
        client = _vision_client()
        if not client:
            return "Configurez une clé Gemini pour utiliser la caméra."
        try:
            import cv2
        except ImportError:
            return "opencv-python est requis pour la caméra."
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return "Impossible d'ouvrir la webcam."
        await asyncio.sleep(0.5)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return "Échec de capture webcam."
        path_ss = "jarvis_vision_temp.png"
        cv2.imwrite(path_ss, frame)
        img = _open_image(path_ss)
        prompt = (
            f"Tu es la vision de JARVIS. Question de l'utilisateur : {texte_utilisateur}\n"
            "Décris ce que tu vois et réponds précisément à la question."
        )
        response = client.models.generate_content(model=_vision_model(), contents=[prompt, img])
        if os.path.exists(path_ss):
            os.remove(path_ss)
        return response.text.strip()
    except Exception as e:
        print(f"[VISION CAMERA] {e}")
        return "Erreur lors de l'analyse par la caméra."


async def jarvis_vision_navigateur(texte_utilisateur):
    """Demande une capture d'écran via le frontend puis analyse (délégué à main2)."""
    import builtins
    capture = getattr(builtins, "request_screen_capture", None)
    if not capture:
        return "La vision navigateur n'est pas disponible."
    img_b64 = await capture()
    if not img_b64:
        return "Activez la vision sur l'interface et autorisez le partage d'écran."
    demander = getattr(builtins, "demander_ia_vision", None)
    if demander:
        return await demander(texte_utilisateur, img_b64)
    return "Module de vision non initialisé."
