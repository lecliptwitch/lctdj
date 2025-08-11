# scripts/upload_youtube.py
import os
import json
import io
import httplib2
import sys
import re # Importation ajoutée pour les expressions régulières
from datetime import datetime # Importation ajoutée pour la date dans le titre

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Scopes requis pour l'upload de vidéo
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# --- MODIFICATION ICI : Mise à jour du chemin de la vidéo compilée ---
COMPILED_VIDEO_PATH = os.path.join("output", "compiled_video.mp4") # Anciennement data/
# --- FIN DE LA MODIFICATION ---

THUMBNAIL_PATH = os.path.join("data", "thumbnail.jpg")
METADATA_JSON_PATH = os.path.join("data", "video_metadata.json") # CORRIGÉ

def upload_video():
    print("📤 Démarrage de l'upload YouTube...")

    # 1. Charger les métadonnées
    if not os.path.exists(METADATA_JSON_PATH):
        print(f"❌ Fichier de métadonnées '{METADATA_JSON_PATH}' introuvable.")
        sys.exit(1)
    with open(METADATA_JSON_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    # --- DÉBUT DES MODIFICATIONS POUR LE TITRE (SIMPLIFIÉ) ---
    # Le titre complet est déjà généré par generate_metadata.py et devrait être "Titre réel | Le Clip Twitch du Jour FR - Jour Mois Année"
    title_from_metadata = metadata["title"]
    description = metadata["description"]
    tags = metadata["tags"]
    
    # Nettoyage et troncation du titre complet reçu de generate_metadata.py
    cleaned_final_title = title_from_metadata
    
    # Supprimer les caractères spéciaux problématiques, mais conserver ceux utiles (tirets, virgules, points d'interrogation, etc.)
    # Cette regex conserve les caractères alphanumériques, espaces, et certains ponctuations communes.
    # Elle supprime les émojis et autres symboles complexes.
    cleaned_final_title = re.sub(r'[^\w\s\-\.,\'"!?|]', '', cleaned_final_title)
    
    # Supprimer les mentions de !commands ou autres spam potentiels (ex: !discord)
    cleaned_final_title = re.sub(r'!\w+', '', cleaned_final_title)
    
    # Remplacer les multiples espaces par un seul et supprimer les espaces en début/fin
    cleaned_final_title = re.sub(r'\s+', ' ', cleaned_final_title).strip() 

    max_title_length = 100 # Limite de caractères pour les titres YouTube

    # Si le titre nettoyé est trop long, le tronquer intelligemment
    if len(cleaned_final_title) > max_title_length:
        # Tronquer et ajouter "..."
        truncated_title = cleaned_final_title[:max_title_length - 3].strip()
        # S'assurer qu'on ne coupe pas un mot en plein milieu
        last_space = truncated_title.rfind(' ')
        if last_space != -1: # Si un espace est trouvé, couper au dernier mot complet
            truncated_title = truncated_title[:last_space]
        cleaned_final_title = truncated_title + "..."
    
    # Si le titre nettoyé est vide après le traitement (très rare, mais pour la robustesse)
    if not cleaned_final_title:
        cleaned_final_title = "Le meilleur des clips Twitch du Jour" # Titre par défaut

    title = cleaned_final_title # C'est le titre final pour YouTube
    # --- FIN DES MODIFICATIONS POUR LE TITRE ---


    # Récupérer la catégorie et le statut de confidentialité depuis les métadonnées
    category_id = metadata.get("category_id", "20") # Par défaut "Gaming"
    privacy_status = metadata.get("privacyStatus", "public")

    # 2. Authentification YouTube (via Refresh Token)
    creds = None
    refresh_token = os.getenv('YOUTUBE_REFRESH_TOKEN')
    client_id = os.getenv('YOUTUBE_CLIENT_ID')
    client_secret = os.getenv('YOUTUBE_CLIENT_SECRET')
    
    if not all([refresh_token, client_id, client_secret]):
        print("❌ ERREUR: YOUTUBE_REFRESH_TOKEN, YOUTUBE_CLIENT_ID ou YOUTUBE_CLIENT_SECRET manquants.")
        print("Veuillez vous assurer que tous les secrets GitHub sont configurés.")
        sys.exit(1)
        
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES
    )
    print("✅ Tentative d'authentification YouTube via Refresh Token...")

    try:
        creds.refresh(Request())
        print("✅ Refresh Token utilisé avec succès pour obtenir un nouveau jeton d'accès.")
    except Exception as e:
        print(f"❌ Échec du rafraîchissement du jeton d'accès : {e}")
        print("Vérifiez YOUTUBE_REFRESH_TOKEN, YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET et la validité du token.")
        sys.exit(1)
        

    # Construire le service YouTube
    youtube = build("youtube", "v3", credentials=creds)

    # 3. Préparer la vidéo et la miniature
    if not os.path.exists(COMPILED_VIDEO_PATH):
        print(f"❌ Fichier vidéo compilée '{COMPILED_VIDEO_PATH}' introuvable.")
        sys.exit(1)

    thumbnail_present = False
    if os.path.exists(THUMBNAIL_PATH):
        thumbnail_present = True
    else:
        print(f"⚠️ Fichier miniature '{THUMBNAIL_PATH}' introuvable. La vidéo sera uploadée sans miniature personnalisée.")


    body = {
        "snippet": {
            "title": title, # Utilise le titre nettoyé et tronqué
            "description": description,
            "tags": tags,
            "categoryId": category_id # Utilise la catégorie des métadonnées
        },
        "status": {
            "privacyStatus": privacy_status, # Utilise le statut de confidentialité des métadonnées
            "selfDeclaredMadeForKids": False # Important: doit être False si pas pour enfants
        }
    }

    # Uploader la vidéo
    media_body = MediaFileUpload(COMPILED_VIDEO_PATH, resumable=True)

    print(f"Uploading video: '{title}'...")
    insert_request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media_body
    )

    try:
        response = insert_request.execute()
        print(f"✅ Vidéo uploadée ! URL: https://www.youtube.com/watch?v={response['id']}") # URL de YouTube corrigée
        
        # Uploader la miniature
        if thumbnail_present:
            print(f"Uploading thumbnail: '{THUMBNAIL_PATH}'...")
            try:
                youtube.thumbnails().set(
                    videoId=response['id'],
                    media_body=MediaFileUpload(THUMBNAIL_PATH)
                ).execute()
                print("✅ Miniature uploadée avec succès !")
            except Exception as thumbnail_e:
                print(f"❌ ERREUR lors de l'upload de la miniature : {thumbnail_e}")
                print("Cela peut être dû à des permissions manquantes sur votre chaîne YouTube pour les miniatures personnalisées.")
        else:
            print("⚠️ Pas de miniature trouvée, upload ignoré.")
        
        return True
    except Exception as e:
        print(f"❌ ERREUR lors de l'upload sur YouTube : {e}")
        print("La vidéo compilée a été conservée dans le dossier 'output/' si cette étape a été atteinte.")
        return False

if __name__ == "__main__":
    upload_video()