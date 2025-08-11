import requests
import os
import json
import sys
from datetime import datetime, timedelta, timezone

# Twitch API credentials from GitHub Secrets
CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    print("❌ ERREUR: TWITCH_CLIENT_ID ou TWITCH_CLIENT_SECRET non définis.")
    sys.exit(1)

TWITCH_AUTH_URL = "https://id.twitch.tv/oauth2/token"
TWITCH_API_URL = "https://api.twitch.tv/helix/clips"

OUTPUT_CLIPS_JSON = os.path.join("data", "top_clips.json")

# --- PARAMÈTRES DE FILTRAGE ET DE SÉLECTION ---

# NOUVELLE OPTION DE CONFIGURATION :
# Si TRUE, le script privilégiera strictement les clips de BROADCASTER_IDS avant d'ajouter des clips de GAME_IDS.
# Si FALSE, tous les clips (broadcasters et jeux) seront collectés puis triés globalement par vues.
PRIORITIZE_BROADCASTERS_STRICTLY = False # <-- CHANGEZ CETTE VALEUR (True/False) POUR BASCULER LA LOGIQUE

# NOUVEAU PARAMÈTRE : Nombre maximal de clips par streamer dans la compilation finale.
MAX_CLIPS_PER_BROADCASTER_IN_FINAL_COMPILATION = 3 # Définis ta limite ici (ex: 5, 10, etc.)

# Liste des IDs de jeux pour lesquels vous voulez récupérer des clips.
GAME_IDS = [
    "509670",        # Just Chatting
    "21779",         # League of Legends
    "32982",         # Grand Theft Auto V
    "512965",        # VALORANT
    "518018",        # Minecraft
    "513143",        # Fortnite
    "32982",         # Grand Theft Auto V
    "32399",         # Counter-Strike
    "511224",        # Apex Legends
    "506520",        # Dota 2
    "490422",        # Dead by Daylight
    "514873",        # Call of Duty: Warzone
    "65768",         # Rocket League
    "518883",        # EA Sports FC 24
    "180025139",     # Mario Kart 8 Deluxe
    "280721",        # Teamfight Tactics
    "488427",        # World of Warcraft
    "1467408070",    # Rust
    "32213",         # Hearthstone
    "138585",        # Chess
    "493306",        # Overwatch 2
    "509660",        # Special Events
    "1063683693",    # Pokémon Scarlet and Violet
    "1678120671",    # Baldur's Gate 3
    "27471",         # osu!
    "507316",        # Phasmophobia
    "19326",         # The Elder Scrolls V: Skyrim
    "512710",        # Fall Guys
    "1285324545",    # Lethal Company
    # Ajoutez d'autres IDs si nécessaire
]

# Liste des IDs de streamers francophones populaires.
# Les clips seront prioritaires selon l'ordre de cette liste si PRIORITIZE_BROADCASTERS_STRICTLY est True.
BROADCASTER_IDS = [
    "737048563",     # Anyme023
    "52130765",      # Squeezie (chaîne principale)
    "22245231",      # SqueezieLive (sa chaîne secondaire pour le live)
    "80716629",      # Inoxtag
    "153066440",     # Michou
    "737048563",     # AmineMaTue
    "496105401",     # byilhann
    "57402636",      # RebeuDeter
    "887001013",     # Nico_la
    "60256640",      # Flamby
    "253195796",     # helydia
    "24147592",      # Gotaga
    "134966333",     # Kameto
    "175560856",     # Hctuan
    "57404419",      # Ponce
    "38038890",      # Antoine Daniel
    "48480373",      # MisterMV
    "19075728",      # Sardoche
    "54546583",      # Locklear
    "50290500",      # Domingo
    "47565457",      # Joyca
    "41719107",      # ZeratoR
    "41487980",      # Pauleta_Twitch (Pfut)
    "31429949",      # LeBouseuh
    "46296316",      # Maghla
    "49896798",      # Chowh1
    "49749557",      # Jiraya
    "53696803",      # Wankil Studio (Laink et Terracid - chaîne principale)
    "72366922",      # Laink (ID individuel, généralement couvert par Wankil Studio)
    "129845722",     # Terracid (ID individuel, généralement couvert par Wankil Studio)
    "51950294",      # Mynthos
    "53140510",      # Etoiles
    "134812328",     # LittleBigWhale
    "180237751",     # Mister V (l'artiste/youtubeur, différent de MisterMV)
    "55787682",      # Shaunz
    "142436402",     # Ultia
    "20875990",      # LCK_France (pour les clips de la ligue de LoL française)
    # Ajoutez d'autres IDs vérifiés ici
]

# --- NOUVEAU PARAMÈTRE : Langue du clip ---
CLIP_LANGUAGE = "fr" # Code ISO 639-1 pour le français

# PARAMÈTRE POUR LA DURÉE CUMULÉE MINIMALE DE LA VIDÉO FINALE
MIN_VIDEO_DURATION_SECONDS = 630 # 10 minutes et 30 secondes (10*60 + 30)

# --- FIN PARAMÈTRES ---

def get_twitch_access_token():
    """Gets an application access token for Twitch API."""
    print("🔑 Récupération du jeton d'accès Twitch...")
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    try:
        response = requests.post(TWITCH_AUTH_URL, data=payload)
        response.raise_for_status()
        token_data = response.json()
        print("✅ Jeton d'accès Twitch récupéré.")
        return token_data["access_token"]
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur lors de la récupération du jeton d'accès Twitch : {e}")
        sys.exit(1)

def fetch_clips(access_token, params, source_type, source_id):
    """Helper function to fetch clips and handle errors."""
    headers = {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {access_token}"
    }
    try:
        response = requests.get(TWITCH_API_URL, headers=headers, params=params)
        response.raise_for_status()
        clips_data = response.json()
        
        if not clips_data.get("data"):
            print(f"  ⚠️ Aucune donnée de clip trouvée pour {source_type} {source_id} dans la période spécifiée.")
            return []

        collected_clips = []
        for clip in clips_data.get("data", []):
            collected_clips.append({
                "id": clip.get("id"),
                "url": clip.get("url"),
                "embed_url": clip.get("embed_url"),
                "thumbnail_url": clip.get("thumbnail_url"),
                "title": clip.get("title"),
                "viewer_count": clip.get("view_count", 0),
                "broadcaster_id": clip.get("broadcaster_id"), # Assure-toi que l'ID du streamer est inclus
                "broadcaster_name": clip.get("broadcaster_name"),
                "game_name": clip.get("game_name"),
                "created_at": clip.get("created_at"),
                "duration": float(clip.get("duration", 0.0)),
                "language": clip.get("language")
            })
        return collected_clips
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur lors de la récupération des clips Twitch pour {source_type} {source_id} : {e}")
        if response.content:
            print(f"    Contenu de la réponse API Twitch: {response.content.decode()}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Erreur de décodage JSON pour {source_type} {source_id}: {e}")
        if response.content:
            print(f"    Contenu brut de la réponse: {response.content.decode()}")
        return []

def get_top_clips(access_token, num_clips_per_source=50, days_ago=3):    
    """Fetches and prioritizes clips based on configured parameters, with a limit per broadcaster."""
    print(f"📊 Récupération d'un maximum de {num_clips_per_source} clips Twitch par source (jeu/streamer) pour les dernières {days_ago} jours...")
            
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days_ago)
    
    seen_clip_ids = set() # Use a set to prevent duplicate clips across all collections

    # --- Phase de collecte ---
    # Collecte tous les clips des broadcasters prioritaires
    print("\n--- Collecte des clips des streamers prioritaires ---")
    all_broadcaster_clips = []
    for broadcaster_id in BROADCASTER_IDS:
        print(f"  - Recherche de clips pour le broadcaster_id: {broadcaster_id}")
        params = {
            "first": num_clips_per_source,
            "started_at": start_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "ended_at": end_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "sort": "views",
            "broadcaster_id": broadcaster_id,
            "language": CLIP_LANGUAGE
        }
        clips = fetch_clips(access_token, params, "broadcaster_id", broadcaster_id)
        for clip in clips:
            if clip["id"] not in seen_clip_ids:
                all_broadcaster_clips.append(clip)
                seen_clip_ids.add(clip["id"])
    print(f"✅ Collecté {len(all_broadcaster_clips)} clips uniques de streamers prioritaires.")

    # Collecte tous les clips des jeux (excluant ceux déjà vus des broadcasters)
    print("\n--- Collecte des clips des jeux spécifiés ---")
    all_game_clips = []
    for game_id in GAME_IDS:
        print(f"  - Recherche de clips pour le game_id: {game_id}")
        params = {
            "first": num_clips_per_source,
            "started_at": start_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "ended_at": end_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "sort": "views",
            "game_id": game_id,
            "language": CLIP_LANGUAGE
        }
        clips = fetch_clips(access_token, params, "game_id", game_id)
        for clip in clips:
            if clip["id"] not in seen_clip_ids: # Important: avoid duplicates from priority broadcasters
                all_game_clips.append(clip)
                seen_clip_ids.add(clip["id"])
    print(f"✅ Collecté {len(all_game_clips)} clips uniques des jeux spécifiés (hors clips déjà inclus).")

    # --- Logique de sélection finale basée sur l'option ---
    final_clips_for_compilation = []
    current_duration_sum = 0.0
    clips_added_per_broadcaster = {} # Nouveau dictionnaire pour suivre le nombre de clips ajoutés par streamer

    if PRIORITIZE_BROADCASTERS_STRICTLY:
        print(f"\nMode de sélection: PRIORITAIRE (streamers d'abord). Atteindre {MIN_VIDEO_DURATION_SECONDS}s.")
        # 1. Trier et ajouter les clips des streamers prioritaires
        sorted_priority_clips = sorted(all_broadcaster_clips, key=lambda x: x.get('viewer_count', 0), reverse=True)
        for clip in sorted_priority_clips:
            broadcaster_id = clip.get('broadcaster_id')
            
            # Vérifie si la limite pour ce streamer est atteinte
            if clips_added_per_broadcaster.get(broadcaster_id, 0) >= MAX_CLIPS_PER_BROADCASTER_IN_FINAL_COMPILATION:
                print(f"  [PRIO] Ignoré : Limite de clips ({MAX_CLIPS_PER_BROADCASTER_IN_FINAL_COMPILATION}) atteinte pour {clip.get('broadcaster_name', 'N/A')}")
                continue # Passe au clip suivant

            clip_duration = float(clip.get('duration', 0.0))
            if clip_duration > 0:
                final_clips_for_compilation.append(clip)
                current_duration_sum += clip_duration
                # Incrémente le compteur de clips pour ce streamer
                clips_added_per_broadcaster[broadcaster_id] = clips_added_per_broadcaster.get(broadcaster_id, 0) + 1 
                
                print(f"  [PRIO] Ajouté : '{clip.get('title', 'N/A')}' par {clip.get('broadcaster_name', 'N/A')} ({clip_duration:.1f}s, Vues: {clip.get('viewer_count', 0)}). Durée cumulée: {current_duration_sum:.1f}s. Clips de ce streamer: {clips_added_per_broadcaster[broadcaster_id]}/{MAX_CLIPS_PER_BROADCASTER_IN_FINAL_COMPILATION}")
                
                if current_duration_sum >= MIN_VIDEO_DURATION_SECONDS and len(final_clips_for_compilation) >= 3:
                    print(f"  ✅ Durée minimale ({MIN_VIDEO_DURATION_SECONDS}s) atteinte avec {len(final_clips_for_compilation)} clips prioritaires.")
                    break # Stop adding priority clips

        # 2. Si la durée n'est pas atteinte, compléter avec les clips de jeux
        if current_duration_sum < MIN_VIDEO_DURATION_SECONDS:
            print(f"  ⚠️ Durée minimale pas encore atteinte ({current_duration_sum:.1f}s). Ajout de clips des jeux pour compléter.")
            sorted_game_clips = sorted(all_game_clips, key=lambda x: x.get('viewer_count', 0), reverse=True)
            for clip in sorted_game_clips:
                # Double-check if already added (should be covered by seen_clip_ids, but safety)
                if clip["id"] in [c["id"] for c in final_clips_for_compilation]:
                    continue
                
                broadcaster_id = clip.get('broadcaster_id')

                # Applique aussi la limite aux clips de jeux pour éviter qu'un streamer dominent trop la fin
                if clips_added_per_broadcaster.get(broadcaster_id, 0) >= MAX_CLIPS_PER_BROADCASTER_IN_FINAL_COMPILATION:
                    print(f"  [JEUX] Ignoré : Limite de clips ({MAX_CLIPS_PER_BROADCASTER_IN_FINAL_COMPILATION}) atteinte pour {clip.get('broadcaster_name', 'N/A')}")
                    continue # Passe au clip suivant

                clip_duration = float(clip.get('duration', 0.0))
                if clip_duration > 0:
                    final_clips_for_compilation.append(clip)
                    current_duration_sum += clip_duration
                    clips_added_per_broadcaster[broadcaster_id] = clips_added_per_broadcaster.get(broadcaster_id, 0) + 1 
                    print(f"  [JEUX] Ajouté : '{clip.get('title', 'N/A')}' par {clip.get('broadcaster_name', 'N/A')} ({clip_duration:.1f}s, Vues: {clip.get('viewer_count', 0)}). Durée cumulée: {current_duration_sum:.1f}s. Clips de ce streamer: {clips_added_per_broadcaster[broadcaster_id]}/{MAX_CLIPS_PER_BROADCASTER_IN_FINAL_COMPILATION}")
                    
                    if current_duration_sum >= MIN_VIDEO_DURATION_SECONDS and len(final_clips_for_compilation) >= 3:
                        print(f"  ✅ Durée minimale ({MIN_VIDEO_DURATION_SECONDS}s) atteinte avec {len(final_clips_for_compilation)} clips (mix prioritaires/jeux).")
                        break # Stop adding game clips

    else: # Logique "comme avant": tout trier par vues
        print(f"\nMode de sélection: CLASSIQUE (tous les clips triés par vues). Atteindre {MIN_VIDEO_DURATION_SECONDS}s.")
        all_collected_clips = []
        all_collected_clips.extend(all_broadcaster_clips)
        all_collected_clips.extend(all_game_clips) # game_clips should not contain duplicates already in broadcaster_clips due to seen_clip_ids

        # Filtrer par langue une dernière fois (au cas où l'API renverrait des clips hors langue)
        filtered_clips_by_language = [clip for clip in all_collected_clips if clip.get('language') == CLIP_LANGUAGE]
        sorted_clips_by_views = sorted(filtered_clips_by_language, key=lambda x: x.get('viewer_count', 0), reverse=True)

        for clip in sorted_clips_by_views:
            broadcaster_id = clip.get('broadcaster_id')

            # Vérifie si la limite pour ce streamer est atteinte, même en mode classique
            if clips_added_per_broadcaster.get(broadcaster_id, 0) >= MAX_CLIPS_PER_BROADCASTER_IN_FINAL_COMPILATION:
                print(f"  [GLOBAL] Ignoré : Limite de clips ({MAX_CLIPS_PER_BROADCASTER_IN_FINAL_COMPILATION}) atteinte pour {clip.get('broadcaster_name', 'N/A')}")
                continue # Passe au clip suivant

            clip_duration = float(clip.get('duration', 0.0))
            if clip_duration > 0:
                final_clips_for_compilation.append(clip)
                current_duration_sum += clip_duration
                clips_added_per_broadcaster[broadcaster_id] = clips_added_per_broadcaster.get(broadcaster_id, 0) + 1 
                print(f"  [GLOBAL] Ajouté : '{clip.get('title', 'N/A')}' par {clip.get('broadcaster_name', 'N/A')} ({clip_duration:.1f}s, Vues: {clip.get('viewer_count', 0)}). Durée cumulée: {current_duration_sum:.1f}s. Clips de ce streamer: {clips_added_per_broadcaster[broadcaster_id]}/{MAX_CLIPS_PER_BROADCASTER_IN_FINAL_COMPILATION}")
                
                if current_duration_sum >= MIN_VIDEO_DURATION_SECONDS and len(final_clips_for_compilation) >= 3:
                    print(f"  ✅ Durée minimale ({MIN_VIDEO_DURATION_SECONDS}s) atteinte avec {len(final_clips_for_compilation)} clips.")
                    break


    # Final check and logging
    if current_duration_sum < MIN_VIDEO_DURATION_SECONDS and final_clips_for_compilation:
        print(f"⚠️ ATTENTION: Impossible d'atteindre la durée minimale de {MIN_VIDEO_DURATION_SECONDS} secondes ({MIN_VIDEO_DURATION_SECONDS / 60:.2f} minutes) avec les clips disponibles. Durée finale: {current_duration_sum:.1f}s")
            
    if not final_clips_for_compilation:
        print("⚠️ Aucun clip viable n'a été sélectionné pour la compilation (peut-être tous avec durée 0, ou aucun trouvé). Le fichier top_clips.json sera vide.")
        sys.exit(0)

    # The final list of clips to save
    final_clips = final_clips_for_compilation

    # --- DÉBUGGAGE : Affiche les clips finaux avant de les écrire dans le JSON ---
    print("\n--- CLIPS FINAUX SÉLECTIONNÉS POUR SAUVEGARDE ---")
    if final_clips:
        for i, clip in enumerate(final_clips):
            print(f"{i+1}. Title: {clip.get('title', 'N/A')}, Broadcaster: {clip.get('broadcaster_name', 'N/A')}, Views: {clip.get('viewer_count', 0)}, Duration: {clip.get('duration', 'N/A')}s, Language: {clip.get('language', 'N/A')}, URL: {clip.get('url', 'N/A')}")
    else:
        print("Aucun clip à sauvegarder.")
    print("--------------------------------------------------\n")
            
    with open(OUTPUT_CLIPS_JSON, "w", encoding="utf-8") as f:
        json.dump(final_clips, f, ensure_ascii=False, indent=2)
    
    print(f"✅ {len(final_clips)} clips récupérés et sauvegardés dans {OUTPUT_CLIPS_JSON} pour une durée totale de {current_duration_sum:.1f} secondes.")
    return final_clips

if __name__ == "__main__":
    token = get_twitch_access_token()
    if token:
        get_top_clips(token, num_clips_per_source=50)