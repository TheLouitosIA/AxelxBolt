import psycopg2
from psycopg2 import sql

def get_connection():
    try:
        connection = psycopg2.connect(
            dbname="chauffeurs_db",
            user="app_user",  # Utilise l'utilisateur que tu as créé
            password="AXL_userapp",
            host="localhost",
            port="5432"
        )
        print("Connexion à la base de données réussie.")
        return connection
    except Exception as e:
        print(f"Erreur de connexion à la base de données : {e}")
        return None
    
if __name__ == "__main__":
    conn = get_connection()
    if conn:
        conn.close()
        print("Connexion fermée.")

