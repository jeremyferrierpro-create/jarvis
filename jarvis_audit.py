"""
AUDIT COMPLET DU PROJET JARVIS.
Analyse :
- Les dépendances des modules
- Les imports utilisés dans main2.py
- Les fichiers connectés vs débranché
- Les configurations manquantes
- La santé du projet
"""
import os
import json
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple

JARVIS_ROOT = os.path.dirname(os.path.abspath(__file__))

# Fichiers à ignorer
IGNORED_FILES = {
    "__pycache__", ".git", "venv", ".venv", "node_modules", ".pytest_cache",
    "dist", "build", "*.egg-info", "__pycache__", ".env", ".env.example",
    "credentials.json", "credentials_LISEZ_MOI.txt", "*.pyc", "*.pyo",
    "Untitled", "unins000.dat", "unins000.exe", "jarvis_tts_*.mp3"
}

# Fichiers centraux toujours utilisés
CORE_FILES = {
    "main2.py", "jarvis_config.json", "tts_engine.py", "memory_manager.py",
    "jarvis_agent.py", "jarvis_modes_prompts.py", "voice_config.py"
}

# Répertoires à scanner
SCAN_DIRS = {"jarvis_modes", "jarvis_human_features", "jarvis_skills"}

class AuditJarvis:
    def __init__(self, root: str = JARVIS_ROOT):
        self.root = root
        self.modules: Dict[str, Set[str]] = defaultdict(set)  # module -> imports
        self.used_modules: Set[str] = set()
        self.unused_modules: Set[str] = set()
        self.connected_modules: Set[str] = set()
        self.config_issues: List[str] = []
        self.import_errors: List[Tuple[str, str]] = []
        self.file_sizes: Dict[str, int] = {}
        
    def scanner_imports(self, filepath: str) -> Set[str]:
        """Extrait les imports d'un fichier Python."""
        imports = set()
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            
            # Patterns d'import
            patterns = [
                r"^from\s+([\w\.]+)\s+import",
                r"^import\s+([\w\.]+)",
                r"^from\s+\.?([\w]+)\s+import",
            ]
            
            for pattern in patterns:
                for match in re.finditer(pattern, content, re.MULTILINE):
                    module = match.group(1).split('.')[0]
                    imports.add(module)
        except Exception as e:
            self.import_errors.append((filepath, str(e)))
        
        return imports
    
    def lister_python_files(self) -> List[str]:
        """Liste tous les fichiers Python du projet."""
        files = []
        for root, dirs, filenames in os.walk(self.root):
            # Filtrer les répertoires ignorés
            dirs[:] = [d for d in dirs if d not in IGNORED_FILES]
            
            for filename in filenames:
                if filename.endswith('.py') and filename not in {'setup.py', 'install.py'}:
                    filepath = os.path.join(root, filename)
                    files.append(filepath)
        
        return sorted(files)
    
    def analyser_main2(self) -> Set[str]:
        """Analyse main2.py pour voir quels modules sont importés."""
        main_path = os.path.join(self.root, "main2.py")
        if not os.path.exists(main_path):
            return set()
        
        imports = self.scanner_imports(main_path)
        
        # Modules locaux Python (extraire les noms de fichiers)
        local_modules = set()
        for imp in imports:
            py_file = os.path.join(self.root, f"{imp}.py")
            if os.path.exists(py_file):
                local_modules.add(f"{imp}.py")
        
        return local_modules
    
    def analyser_dependances(self) -> None:
        """Construit le graphe de dépendances."""
        py_files = self.lister_python_files()
        
        for py_file in py_files:
            imports = self.scanner_imports(py_file)
            relname = os.path.relpath(py_file, self.root)
            self.modules[relname] = imports
            self.file_sizes[relname] = os.path.getsize(py_file) / 1024  # KB
    
    def identifier_modules_connectes(self) -> None:
        """Identifie quels modules sont utilisés par main2.py."""
        used = self.analyser_main2()
        
        # Ajouter récursivement tous les modules importés
        to_check = list(used)
        while to_check:
            mod = to_check.pop(0)
            if mod in self.connected_modules:
                continue
            
            self.connected_modules.add(mod)
            imports = self.modules.get(mod, set())
            
            for imp in imports:
                py_file = f"{imp}.py"
                if py_file not in self.connected_modules:
                    to_check.append(py_file)
    
    def identifier_modules_inutilises(self) -> None:
        """Identifie les modules Python non utilisés."""
        py_files = self.lister_python_files()
        
        for py_file in py_files:
            relname = os.path.relpath(py_file, self.root)
            
            # Les fichiers core ne sont jamais inutilisés
            if os.path.basename(relname) in CORE_FILES:
                continue
            
            # Les fichiers dans les dossiers spécialisés ne sont pas "inutilisés"
            if any(d in relname for d in SCAN_DIRS):
                continue
            
            if relname not in self.connected_modules:
                self.unused_modules.add(relname)
    
    def verifier_config(self) -> None:
        """Vérifie les fichiers de configuration."""
        config_file = os.path.join(self.root, "jarvis_config.json")
        config_example = os.path.join(self.root, "jarvis_config.example.json")
        
        if not os.path.exists(config_file):
            self.config_issues.append("❌ jarvis_config.json MANQUANT (copier depuis .example.json)")
        
        if not os.path.exists(config_example):
            self.config_issues.append("⚠️  jarvis_config.example.json MANQUANT")
        
        # Vérifier les clés TTS dans la config
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                if "tts" not in config:
                    self.config_issues.append("⚠️  Section 'tts' manquante dans jarvis_config.json")
                
                if "jarvis_relations" not in config:
                    self.config_issues.append("⚠️  Section 'jarvis_relations' manquante")
                
                if "jarvis_human" not in config:
                    self.config_issues.append("⚠️  Section 'jarvis_human' manquante")
            except Exception as e:
                self.config_issues.append(f"❌ Erreur lecture config : {e}")
        
        # Vérifier les dossiers spécialisés
        required_dirs = [
            "voices", "jarvis_modes", "jarvis_human_features", 
            "jarvis_skills", "jarvis_uploads", "frontend", "mobile"
        ]
        for dir_name in required_dirs:
            dir_path = os.path.join(self.root, dir_name)
            if not os.path.isdir(dir_path):
                self.config_issues.append(f"⚠️  Répertoire manquant : {dir_name}/")
    
    def generer_rapport(self) -> str:
        """Génère le rapport d'audit complet."""
        self.analyser_dependances()
        self.identifier_modules_connectes()
        self.identifier_modules_inutilises()
        self.verifier_config()
        
        lines = [
            "",
            "╔" + "═" * 78 + "╗",
            "║" + " " * 78 + "║",
            "║" + "AUDIT COMPLET JARVIS".center(78) + "║",
            "║" + " " * 78 + "║",
            "╚" + "═" * 78 + "╝",
        ]
        
        # Statistiques générales
        py_files = self.lister_python_files()
        total_size = sum(self.file_sizes.values())
        
        lines.extend([
            "",
            "📊 STATISTIQUES GÉNÉRALES",
            "─" * 80,
            f"  Fichiers Python        : {len(py_files)}",
            f"  Taille totale          : {total_size:.1f} KB",
            f"  Modules connectés      : {len(self.connected_modules)}",
            f"  Modules non utilisés   : {len(self.unused_modules)}",
            f"  Fichiers ignorés       : {len(IGNORED_FILES)}",
        ])
        
        # Modules connectés
        lines.extend([
            "",
            "✓ MODULES CONNECTÉS (utilisés par main2.py)",
            "─" * 80,
        ])
        if self.connected_modules:
            for mod in sorted(self.connected_modules):
                size = self.file_sizes.get(mod, 0)
                lines.append(f"  ✓ {mod:<40} ({size:>6.1f} KB)")
        else:
            lines.append("  (aucun détecté)")
        
        # Modules débranché
        lines.extend([
            "",
            "⚠️  MODULES NON CONNECTÉS (débranché)",
            "─" * 80,
        ])
        if self.unused_modules:
            categorized = defaultdict(list)
            for mod in sorted(self.unused_modules):
                # Catégoriser
                if "example" in mod or "test" in mod:
                    categorized["Test/Exemple"].append(mod)
                elif mod.startswith("_"):
                    categorized["Privé"].append(mod)
                elif "setup" in mod or "install" in mod:
                    categorized["Setup"].append(mod)
                else:
                    categorized["Modules détachés"].append(mod)
            
            for category, mods in sorted(categorized.items()):
                lines.append(f"\n  [{category}]")
                for mod in mods:
                    size = self.file_sizes.get(mod, 0)
                    lines.append(f"    • {mod:<35} ({size:>6.1f} KB)")
        else:
            lines.append("  ✓ Tous les modules sont connectés !")
        
        # Problèmes de configuration
        lines.extend([
            "",
            "⚙️  CONFIGURATION",
            "─" * 80,
        ])
        if self.config_issues:
            for issue in self.config_issues:
                lines.append(f"  {issue}")
        else:
            lines.append("  ✓ Configuration OK")
        
        # Erreurs d'import
        if self.import_errors:
            lines.extend([
                "",
                "❌ ERREURS D'IMPORT",
                "─" * 80,
            ])
            for filepath, error in self.import_errors[:10]:
                rel = os.path.relpath(filepath, self.root)
                lines.append(f"  ❌ {rel}: {error}")
        
        # Recommandations
        lines.extend([
            "",
            "💡 RECOMMANDATIONS",
            "─" * 80,
        ])
        
        recommendations = []
        
        if self.unused_modules:
            for mod in sorted(self.unused_modules):
                if "controller" in mod.lower():
                    recommendations.append(
                        f"  • {mod}: Intégrer ou documenter son utilisation"
                    )
        
        if self.config_issues:
            recommendations.append("  • Vérifier et corriger les problèmes de configuration")
        
        if len(self.connected_modules) < len(py_files) / 2:
            recommendations.append("  • Beaucoup de modules ne sont pas connectés")
            recommendations.append("    → À brancher, documenter ou supprimer")
        
        if recommendations:
            for rec in recommendations:
                lines.append(rec)
        else:
            lines.append("  ✓ Aucune recommandation majeure")
        
        lines.extend([
            "",
            "╔" + "═" * 78 + "╗",
            "║" + " FIN DE L'AUDIT ".center(78) + "║",
            "╚" + "═" * 78 + "╝",
            "",
        ])
        
        return "\n".join(lines)


def lancer_audit() -> None:
    """Fonction principale pour lancer l'audit."""
    audit = AuditJarvis()
    rapport = audit.generer_rapport()
    print(rapport)
    
    # Sauvegarder dans un fichier
    audit_file = os.path.join(JARVIS_ROOT, "AUDIT_RAPPORT.txt")
    with open(audit_file, "w", encoding="utf-8") as f:
        f.write(rapport)
    print(f"\n✓ Rapport sauvegardé dans : {audit_file}")


if __name__ == "__main__":
    lancer_audit()
