# -*- coding: utf-8 -*-
"""Diagnostic rapide JARVIS — lancer : python jarvis_diagnostic.py"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def _ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def _warn(msg: str) -> None:
    print(f"  [!!] {msg}")


def _fail(msg: str) -> None:
    print(f"  [XX] {msg}")


def main() -> int:
    print("=== Diagnostic JARVIS ===\n")
    erreurs = 0

    env_path = os.path.join(ROOT, ".env")
    if os.path.isfile(env_path):
        _ok(".env présent")
        with open(env_path, encoding="utf-8") as f:
            txt = f.read()
        for cle in ("OPENAI_API_KEY", "GEMINI", "GROQ", "ANTHROPIC"):
            if cle in txt.upper() and "votre" not in txt.lower():
                _ok(f"clé {cle} semble définie")
            else:
                _warn(f"clé {cle} absente ou placeholder — l'IA peut ne pas répondre")
    else:
        _fail(".env manquant — copiez .env.example")
        erreurs += 1

    cfg_path = os.path.join(ROOT, "jarvis_config.json")
    if os.path.isfile(cfg_path):
        _ok("jarvis_config.json")
    else:
        _fail("jarvis_config.json manquant")
        erreurs += 1

    try:
        from jarvis_relations import contexte_relations_pour_prompt
        ctx = contexte_relations_pour_prompt(compact=True)
        n = len(ctx)
        if n > 15000:
            _warn(f"prompt relations très long ({n} car.) — risque timeout")
        else:
            _ok(f"prompt relations compact ({n} car.)")
    except Exception as e:
        _fail(f"jarvis_relations : {e}")
        erreurs += 1

    try:
        import main2
        sp = main2.construire_system_prompt()
        n = len(sp)
        if n > 100000:
            _warn(f"system prompt énorme ({n} car.) — réduisez les connaissances injectées")
        elif n > 50000:
            _warn(f"system prompt long ({n} car.)")
        else:
            _ok(f"system prompt ({n} car.)")
    except Exception as e:
        _fail(f"main2.construire_system_prompt : {e}")
        erreurs += 1

    ws_token = os.getenv("WS_TOKEN", "").strip()
    if ws_token:
        _warn("WS_TOKEN actif — l'interface doit utiliser ?token=… sinon pas de connexion WebSocket")
    else:
        _ok("WebSocket sans token (mode local)")

    for nom in ("jarvis_learning_base.json", "jarvis_memoire.json"):
        p = os.path.join(ROOT, nom)
        if os.path.isfile(p):
            try:
                json.load(open(p, encoding="utf-8"))
                _ok(f"{nom} JSON valide")
            except Exception as e:
                _fail(f"{nom} corrompu : {e}")
                erreurs += 1

    print()
    if erreurs:
        print(f"Résultat : {erreurs} problème(s) critique(s). Corrigez avant de relancer JARVIS.")
        return 1
    print("Résultat : configuration plausible. Si JARVIS ne parle toujours pas :")
    print("  1. Redémarrez main2.py et regardez la console [CERVEAU] / [JARVIS]")
    print("  2. Dites « Jarvis » puis une phrase (micro) OU utilisez le clavier HUD")
    print("  3. Vérifiez que le micro n'est pas coupé (bouton micro)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
