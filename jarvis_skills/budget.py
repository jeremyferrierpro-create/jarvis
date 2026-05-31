def skill_ajouter_depense(montant: float, categorie: str) -> str:
    """
    Ajoute une dépense au budget.
    """
    if montant < 0:
        return "Le montant d'une dépense ne peut pas être négatif."
    return f"Dépense de {montant}€ ajoutée dans la catégorie '{categorie}'."

def skill_bilan_budget() -> str:
    """
    Renvoie un bilan du budget.
    """
    return "Bilan budget : Les dépenses et les revenus sont équilibrés."
