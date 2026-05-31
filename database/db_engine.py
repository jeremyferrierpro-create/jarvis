import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Construct the path to the .env file in the root directory (JARVIS)
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
env_path = os.path.join(root_dir, '.env')

# Load the environment variables
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase_client: Client = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Erreur lors de l'initialisation du client Supabase : {e}")

def init_db():
    """
    Vérifie l'accès à la base de données Supabase.
    Le DDL n'étant pas possible via l'API REST standard de Supabase,
    nous assumons que la table 'apprentissages' existe déjà, avec les colonnes :
    - id (PK)
    - sujet (text)
    - categorie (text)
    - resume (text)
    - dates (jsonb ou text array)
    - actions (jsonb ou text array)
    - importance (text)
    """
    if not supabase_client:
        print("Erreur: Client Supabase non initialisé (vérifiez .env).")
        return False
        
    try:
        # Essai de lecture pour valider que la connexion fonctionne et que la table est accessible
        response = supabase_client.table("apprentissages").select("*").limit(1).execute()
        print("Connexion à Supabase et accès à la table 'apprentissages' validés.")
        return True
    except Exception as e:
        print(f"Erreur lors de la vérification de la DB Supabase : {e}")
        return False

def inserer_apprentissage(donnees: dict):
    """
    Insère un apprentissage dans la table 'apprentissages'.
    :param donnees: un dictionnaire contenant les champs (ex: sujet, categorie, resume, dates, actions, importance)
    """
    if not supabase_client:
        print("Erreur: Client Supabase non initialisé.")
        return None
        
    try:
        response = supabase_client.table("apprentissages").insert(donnees).execute()
        return response.data
    except Exception as e:
        print(f"Erreur lors de l'insertion de l'apprentissage : {e}")
        return None

def rechercher_apprentissage(query: str) -> list:
    """
    Recherche des apprentissages dont le sujet ou le résumé contient la query.
    :param query: le texte à rechercher
    :return: une liste de dictionnaires représentant les apprentissages trouvés
    """
    if not supabase_client:
        print("Erreur: Client Supabase non initialisé.")
        return []
        
    try:
        # Utilisation de l'opérateur 'or' pour chercher sur plusieurs colonnes
        # .ilike permet une recherche insensible à la casse (%query%)
        search_term = f"%{query}%"
        response = supabase_client.table("apprentissages") \
            .select("*") \
            .or_(f"sujet.ilike.{search_term},resume.ilike.{search_term}") \
            .execute()
        return response.data
    except Exception as e:
        print(f"Erreur lors de la recherche des apprentissages : {e}")
        return []
