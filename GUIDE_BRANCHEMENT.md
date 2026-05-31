"""
GUIDE D'INTÉGRATION — Branchement des modules débranché du JARVIS.

Modules détachés identifiés:
1. document_cognition.py — Analyse/cognition de documents
2. document_ingest.py — Ingestion de documents
3. jarvis_auto_learning.py — Apprentissage automatique
4. jarvis_capabilities.py — Audit UI, workflows, projets
5. jarvis_diagnostic.py — Diagnostic système
6. jarvis_human.py — Gestion de la relation humaine (émotions, compréhension)
7. jarvis_mode_detector.py — Détection automatique des modes (ami, amoureux, pro, etc.)
8. jarvis_relations.py — Gestion des relations (amitié, amour, professionnel)
9. knowledge_engine.py — Moteur de connaissance / RAG
10. pc_actions.py — Actions PC (écran, système, volume, etc.)
11. site_dev_agent.py — Agent développement web autonome
12. web_dev_engine.py — Moteur de développement web

PRIORITÉ DE BRANCHEMENT
═══════════════════════════════════════════════════════════════════════════════

TIER 1 — CRITIQUE (branche obligatoire)
───────────────────────────────────────
✓ jarvis_human.py — Gestion émotionnelle du compagnon
✓ jarvis_mode_detector.py — Détecte le mode de conversation
✓ jarvis_relations.py — Gère la relation avec l'utilisateur
✓ pc_actions.py — Actions système (volume, écran, etc.)

TIER 2 — FONCTIONNALITÉS PRINCIPALES
─────────────────────────────────────
• jarvis_auto_learning.py — Apprentissage sur les échanges
• knowledge_engine.py — Base de connaissances / RAG
• jarvis_capabilities.py — Audit/workflow/projets
• document_cognition.py + document_ingest.py — Traitement documents

TIER 3 — AVANCÉ (branchement optionnel)
────────────────────────────────────────
○ site_dev_agent.py + web_dev_engine.py — Dev web autonome
○ jarvis_diagnostic.py — Diagnostic système détaillé

═══════════════════════════════════════════════════════════════════════════════
ÉTAPES DE BRANCHEMENT
═══════════════════════════════════════════════════════════════════════════════

1. BRANCHER jarvis_human.py (Gestion émotionnelle)
───────────────────────────────────────────────────
Fichier: main2.py, ligne ~150 (après imports de modules)

Ajouter:
```python
# ─────────────────────────────────────────────────────────────────────────────
# GESTION ÉMOTIONNELLE & RELATION
# ─────────────────────────────────────────────────────────────────────────────
try:
    from jarvis_human import (
        charger_etat_humain, sauvegarder_etat_humain,
        detecter_humeur, evaluer_empathie,
        generer_reponse_empathique
    )
    _HUMAN_MODULE_OK = True
except ImportError:
    _HUMAN_MODULE_OK = False
    print("[AVERTISSEMENT] jarvis_human.py non chargé")

# Charger l'état humain au démarrage
if _HUMAN_MODULE_OK:
    ETAT_HUMAIN = charger_etat_humain()
```

Intégration dans les prompts JARVIS:
- Avant chaque réponse: analyser humeur et contexte émotionnel
- Utiliser `generer_reponse_empathique()` pour adapter le ton
- Sauvegarder l'état avec `sauvegarder_etat_humain()`

─────────────────────────────────────────────────────────────────────────────

2. BRANCHER jarvis_mode_detector.py (Détection de modes)
──────────────────────────────────────────────────────────
Fichier: main2.py, ligne ~170 (après jarvis_human)

Ajouter:
```python
# ─────────────────────────────────────────────────────────────────────────────
# DÉTECTION AUTOMATIQUE DES MODES
# ─────────────────────────────────────────────────────────────────────────────
try:
    from jarvis_mode_detector import (
        detecter_mode_contexte,
        evaluer_confiance_mode,
        MODES_PRIORITES
    )
    _MODE_DETECTOR_OK = True
except ImportError:
    _MODE_DETECTOR_OK = False
    print("[AVERTISSEMENT] jarvis_mode_detector.py non chargé")

DETECTED_MODE = "standard"  # Variable globale pour mode actuel
```

Intégration:
- Avant traitement utilisateur: `DETECTED_MODE = detecter_mode_contexte(texte_utilisateur)`
- Adapter le prompt principal selon le mode détecté

─────────────────────────────────────────────────────────────────────────────

3. BRANCHER jarvis_relations.py (Gestion des relations)
────────────────────────────────────────────────────────
Fichier: main2.py, ligne ~190 (après mode_detector)

Ajouter:
```python
try:
    from jarvis_relations import (
        charger_relations_db,
        evaluer_relation_contexte,
        enregistrer_interaction,
        obtenir_contexte_relation
    )
    _RELATIONS_OK = True
except ImportError:
    _RELATIONS_OK = False
    print("[AVERTISSEMENT] jarvis_relations.py non chargé")

if _RELATIONS_OK:
    RELATIONS_DB = charger_relations_db()
```

─────────────────────────────────────────────────────────────────────────────

4. BRANCHER pc_actions.py (Actions système)
─────────────────────────────────────────────
Fichier: main2.py, ligne ~210 (après relations)

Ajouter:
```python
try:
    from pc_actions import (
        get_volume_systeme, set_volume_systeme,
        get_luminosite, set_luminosite,
        get_info_systeme, obtenir_processus_actifs,
        terminer_application, info_memoire
    )
    _PC_ACTIONS_OK = True
except ImportError:
    _PC_ACTIONS_OK = False
    print("[AVERTISSEMENT] pc_actions.py non chargé")

builtins.get_volume_systeme = get_volume_systeme if _PC_ACTIONS_OK else None
```

─────────────────────────────────────────────────────────────────────────────

5. BRANCHER jarvis_auto_learning.py (Apprentissage)
───────────────────────────────────────────────────
Fichier: main2.py, ligne ~230 (après pc_actions)

Ajouter:
```python
try:
    from jarvis_auto_learning import (
        apprendre_echange, consolider_apprentissage,
        obtenir_insights_mode, injecter_context_appris
    )
    _AUTO_LEARNING_OK = True
except ImportError:
    _AUTO_LEARNING_OK = False
    print("[AVERTISSEMENT] jarvis_auto_learning.py non chargé")
```

Intégration:
- Après chaque échange utilisateur-JARVIS: `await apprendre_echange(question, reponse, mode)`
- Avant génération de réponse: `contexte_appris = obtenir_insights_mode(mode)`

─────────────────────────────────────────────────────────────────────────────

6. BRANCHER knowledge_engine.py (Base de connaissances)
────────────────────────────────────────────────────────
Fichier: main2.py, ligne ~250 (après auto_learning)

Ajouter:
```python
try:
    from knowledge_engine import (
        initialiser_rag, rechercher_connaissance,
        indexer_document, obtenir_contexte_rag
    )
    _KNOWLEDGE_ENGINE_OK = True
    RAG_ENGINE = initialiser_rag()
except ImportError:
    _KNOWLEDGE_ENGINE_OK = False
    RAG_ENGINE = None
    print("[AVERTISSEMENT] knowledge_engine.py non chargé")
```

─────────────────────────────────────────────────────────────────────────────

7. BRANCHER jarvis_capabilities.py (Audit/Workflows)
────────────────────────────────────────────────────
Fichier: main2.py, ligne ~270 (après knowledge_engine)

Ajouter:
```python
try:
    from jarvis_capabilities import (
        auditer_ui, auditer_securite,
        charger_workflows, lister_workflows,
        executer_workflow
    )
    _CAPABILITIES_OK = True
except ImportError:
    _CAPABILITIES_OK = False
    print("[AVERTISSEMENT] jarvis_capabilities.py non chargé")
```

─────────────────────────────────────────────────────────────────────────────

8. BRANCHER document_cognition.py + document_ingest.py
──────────────────────────────────────────────────────
Fichier: main2.py, ligne ~290 (après capabilities)

Ajouter:
```python
try:
    from document_ingest import charger_document, list_documents
    from document_cognition import analyser_document, extraire_donnees
    _DOC_MODULES_OK = True
except ImportError:
    _DOC_MODULES_OK = False
    print("[AVERTISSEMENT] Modules documents non chargés")
```

─────────────────────────────────────────────────────────────────────────────

9. BRANCHER site_dev_agent.py + web_dev_engine.py (Dev web autonome)
──────────────────────────────────────────────────────────────────────
Fichier: main2.py, ligne ~310 (après modules documents)

Ajouter:
```python
try:
    from site_dev_agent import agent_dev_autonome
    from web_dev_engine import generer_code, auditer_projet
    _WEB_DEV_OK = True
except ImportError:
    _WEB_DEV_OK = False
    print("[AVERTISSEMENT] Modules dev web non chargés")
```

─────────────────────────────────────────────────────────────────────────────

10. BRANCHER jarvis_diagnostic.py (Diagnostic système)
───────────────────────────────────────────────────────
Fichier: main2.py, ligne ~330 (après web_dev)

Ajouter:
```python
try:
    from jarvis_diagnostic import diagnostiquer_systeme, rapport_sante
    _DIAGNOSTIC_OK = True
except ImportError:
    _DIAGNOSTIC_OK = False
    print("[AVERTISSEMENT] jarvis_diagnostic.py non chargé")
```

═══════════════════════════════════════════════════════════════════════════════
CONFIGURATION DES VOIX
═══════════════════════════════════════════════════════════════════════════════

Nouveau système centralisé: voice_config.py

USAGE:
```python
from voice_config import charger_config, set_voice_id, lister_voix_edge
import asyncio

# Charger la config actuelle
config = charger_config()
print(f"Engine: {config['engine']}, Voice: {config['voice_id']}")

# Changer de voix
set_voice_id("fr-FR-DeniseNeural", engine="edge")

# Lister les voix disponibles
async def demo():
    voix = await lister_voix_edge("fr")
    for v in voix:
        print(f"  {v['label']} ({v['id']})")

asyncio.run(demo())
```

COMMANDES JARVIS POUR CONFIGURER LES VOIX:
─────────────────────────────────────────

1. "Affiche la configuration des voix"
   → Retourne la config actuelle

2. "Change ma voix en [voice_name]"
   → Cherche et change la voix
   → Crée une démo audio

3. "Liste les voix disponibles"
   → Affiche toutes les voix Edge TTS (langue: FR)

4. "Utilise le moteur [edge|pyttsx3|xtts|fish_speech]"
   → Change le moteur TTS

5. "Crée une démo avec ta voix"
   → Génère un fichier audio de démonstration

═══════════════════════════════════════════════════════════════════════════════
CHECKLIST D'INTÉGRATION
═══════════════════════════════════════════════════════════════════════════════

□ Brancher jarvis_human.py dans main2.py
□ Brancher jarvis_mode_detector.py dans main2.py
□ Brancher jarvis_relations.py dans main2.py
□ Brancher pc_actions.py dans main2.py
□ Brancher jarvis_auto_learning.py dans main2.py
□ Brancher knowledge_engine.py dans main2.py
□ Brancher jarvis_capabilities.py dans main2.py
□ Brancher document_*.py dans main2.py
□ Brancher site_dev_agent.py + web_dev_engine.py dans main2.py
□ Brancher jarvis_diagnostic.py dans main2.py
□ Tester les imports et la fonctionnalité
□ Intégrer voice_config.py dans main2.py ✓
□ Tester les commandes de configuration des voix
□ Documenter les commandes disponibles
□ Exécuter un nouvel audit pour vérifier que tous les modules sont connectés

═══════════════════════════════════════════════════════════════════════════════
"""

if __name__ == "__main__":
    print(__doc__)
