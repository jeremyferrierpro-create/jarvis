from typing import List

def skill_optimiser_planning(taches: List[str]) -> str:
    """
    Optimise le planning pour une liste de tâches.
    """
    if not taches:
        return "Aucune tâche à optimiser."
    
    return f"Planning optimisé avec succès pour {len(taches)} tâches : {', '.join(taches)}."

def skill_ajouter_formation(formation: str, date: str) -> str:
    """
    Ajoute une formation au planning.
    """
    return f"Formation '{formation}' ajoutée au planning pour la date : {date}."
