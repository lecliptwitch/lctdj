import requests
import os
import sys
import json # Import pour afficher la réponse si besoin

# Récupérer les identifiants Twitch depuis les variables d'environnement
CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    print("❌ ERREUR: Les variables d'environnement TWITCH_CLIENT_ID ou TWITCH_CLIENT_SECRET ne sont pas définies.")
    print("Veuillez les définir avant d'exécuter ce script (par exemple, 'export TWITCH_CLIENT_ID=votre_id').")
    sys.exit(1)

TWITCH_AUTH_URL = "https://id.twitch.tv/oauth2/token"
TWITCH_USERS_API_URL = "https://api.twitch.tv/helix/users"

def get_twitch_access_token():
    """Récupère un jeton d'accès d'application pour l'API Twitch."""
    print("🔑 Tentative de récupération du jeton d'accès Twitch...")
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    try:
        response = requests.post(TWITCH_AUTH_URL, data=payload)
        response.raise_for_status() # Lève une exception pour les codes d'état HTTP d'erreur (4xx ou 5xx)
        token_data = response.json()
        print("✅ Jeton d'accès Twitch récupéré.")
        return token_data["access_token"]
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur lors de la récupération du jeton d'accès Twitch : {e}")
        sys.exit(1)

def get_broadcaster_id(access_token, streamer_login):
    """Récupère l'ID d'un streamer Twitch à partir de son nom d'utilisateur (login)."""
    headers = {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {access_token}"
    }
    params = {
        "login": streamer_login
    }

    print(f"🔍 Recherche de l'ID pour le streamer : '{streamer_login}'...")
    try:
        response = requests.get(TWITCH_USERS_API_URL, headers=headers, params=params)
        response.raise_for_status()
        user_data = response.json()

        if user_data and user_data.get("data"):
            # L'API retourne une liste, même pour un seul login. On prend le premier élément.
            broadcaster = user_data["data"][0]
            print(f"✅ ID trouvé pour '{streamer_login}' : {broadcaster['id']}")
            return broadcaster['id']
        else:
            print(f"⚠️ Aucun streamer trouvé avec le login '{streamer_login}'. Vérifiez l'orthographe.")
            # print(f"Réponse API complète : {json.dumps(user_data, indent=2)}") # Décommenter pour plus de détails
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur lors de la requête API Twitch pour '{streamer_login}' : {e}")
        if response.content:
            print(f"    Contenu de la réponse API: {response.content.decode()}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Erreur de décodage JSON pour '{streamer_login}': {e}")
        if response.content:
            print(f"    Contenu brut de la réponse: {response.content.decode()}")
        return None

if __name__ == "__main__":
    token = get_twitch_access_token()
    if token:
        # Demande à l'utilisateur d'entrer le nom du streamer
        streamer_name = input("Entrez le nom d'utilisateur (login) du streamer Twitch : ").strip()
        
        if streamer_name:
            broadcaster_id = get_broadcaster_id(token, streamer_name)
            if broadcaster_id:
                print(f"\nVous pouvez ajouter cet ID à votre liste BROADCASTER_IDS dans get_top_clips.py : '{broadcaster_id}'")
            else:
                print("\nImpossible de récupérer l'ID du streamer. Assurez-vous que le nom est correct.")
        else:
            print("Aucun nom de streamer n'a été entré.")