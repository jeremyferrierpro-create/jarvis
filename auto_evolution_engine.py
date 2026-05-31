# -*- coding: utf-8 -*-
"""
Auto-Evolution Engine
Ce moteur permet à JARVIS de générer et modifier son propre code de manière isolée
dans le dossier jarvis_skills/ via des appels LLM ou des tâches d'auto-apprentissage.
"""
import os
import ast
import traceback
from core_plugin_loader import creer_skill_depuis_code

def valider_syntaxe_python(code: str) -> tuple[bool, str]:
    """Vérifie que le code Python généré est valide au niveau syntaxique."""
    try:
        ast.parse(code)
        return True, "Code valide."
    except SyntaxError as e:
        return False, f"Erreur de syntaxe : {e}\nLigne: {e.lineno}\nTexte: {e.text}"
    except Exception as e:
        return False, f"Erreur d'analyse : {str(e)}"

def generer_et_installer_skill(nom_skill: str, code_source: str) -> str:
    """
    Valide et installe une nouvelle compétence dynamique pour JARVIS.
    Le fichier sera sauvegardé dans jarvis_skills/{nom_skill}.py.
    """
    est_valide, msg_erreur = valider_syntaxe_python(code_source)
    if not est_valide:
        return f"[EVOLUTION] Échec de la création de la compétence '{nom_skill}' : {msg_erreur}"
    
    try:
        resultat = creer_skill_depuis_code(nom_skill, code_source)
        return f"[EVOLUTION] Succès : {resultat}"
    except Exception as e:
        return f"[EVOLUTION] Erreur critique lors de l'installation du skill '{nom_skill}' : {traceback.format_exc()}"

def auto_reparer_skill(nom_skill: str, erreur_detectee: str, fonction_llm) -> str:
    """
    Tente de réparer un fichier de skill existant qui aurait généré une erreur,
    en utilisant l'intelligence artificielle.
    """
    chemin = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_skills", f"{nom_skill}.py")
    if not os.path.exists(chemin):
        return f"Impossible de réparer : {chemin} n'existe pas."
    
    with open(chemin, "r", encoding="utf-8") as f:
        code_actuel = f.read()
    
    prompt = f"""Tu dois réparer un script Python. 
Script actuel :
```python
{code_actuel}
```
Erreur détectée :
{erreur_detectee}

Réponds UNIQUEMENT avec le NOUVEAU code complet corrigé (sans commentaires superflus en dehors du bloc de code). N'utilise pas le format markdown ```python si cela casse le parsing, ou fournis uniquement le code texte."""

    # Utilisation de la fonction LLM fournie en callback
    # Ce callback doit être une fonction asynchrone dans le cas général.
    # Ici, nous le laisserons pour être géré par l'appelant.
    pass
