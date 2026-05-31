import os
import importlib
import importlib.util
import inspect
from typing import Dict, Callable, Any
import logging

logger = logging.getLogger(__name__)

def charger_plugins(directory: str = "jarvis_skills") -> Dict[str, Callable[..., Any]]:
    """
    Scans a directory for Python files and loads functions starting with 'skill_'.
    Returns a dictionary mapping function names to callable functions.
    """
    plugins: Dict[str, Callable[..., Any]] = {}
    
    if not os.path.exists(directory):
        try:
            os.makedirs(directory, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create directory {directory}: {e}")
            return plugins

    for filename in os.listdir(directory):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = filename[:-3]
            module_path = os.path.join(directory, filename)
            
            try:
                # Dynamically load the module
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Extract functions starting with 'skill_'
                    for name, obj in inspect.getmembers(module, inspect.isfunction):
                        if name.startswith("skill_"):
                            plugins[name] = obj
                            
            except Exception as e:
                logger.error(f"Failed to load plugin {filename}: {e}")

    return plugins

def creer_skill_depuis_code(nom_skill: str, code_python: str, directory: str = "jarvis_skills") -> None:
    """
    Auto-evolution engine placeholder: creates a new skill file from python code.
    The newly created skill can be loaded by calling `charger_plugins` again.
    """
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        
    if not nom_skill.endswith('.py'):
        nom_skill += '.py'
        
    filepath = os.path.join(directory, nom_skill)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code_python)
        logger.info(f"Skill {nom_skill} created successfully at {filepath}.")
        
        # Optionally, one could trigger importlib.invalidate_caches() here 
        # and re-run charger_plugins if a global registry is used.
        importlib.invalidate_caches()
    except Exception as e:
        logger.error(f"Failed to create skill {nom_skill}: {e}")
