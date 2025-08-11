import subprocess
import os
import json
import sys
import re # Importation pour les expressions régulières

INPUT_CLIPS_JSON = os.path.join("data", "top_clips.json")
RAW_CLIPS_DIR = os.path.join("data", "raw_clips") # Keep original downloads here
PROCESSED_CLIPS_DIR = os.path.join("data", "processed_clips") # New directory for consistent clips
CLIP_FRAMES_DIR = os.path.join("data", "clip_frames") # Nouveau dossier pour les frames extraites

def get_video_duration(filepath):
    """
    Obtient la durée d'une vidéo en secondes en utilisant ffprobe.
    Retourne 0.0 si la durée ne peut pas être déterminée.
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            filepath
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError) as e:
        print(f"  ⚠️ Impossible d'obtenir la durée de {filepath} avec ffprobe: {e}")
        return 0.0

def ffmpeg_escape_string(text):
    """
    Escapes characters in a string for FFmpeg drawtext filter to prevent syntax errors.
    Handles backslashes, single quotes, colons, and square brackets.
    """
    # Escape backslashes first, then single quotes, then colons
    text = text.replace('\\', '\\\\')
    text = text.replace("'", "\\'")
    text = text.replace(':', '\\:')
    text = text.replace('[', '\\[')
    text = text.replace(']', '\\]')
    # Commas can also be an issue if they're not intended as separators
    text = text.replace(',', '\\,')
    return text

def download_clips():
    print("📥 Démarrage du téléchargement et du prétraitement des clips Twitch individuels...")
    os.makedirs(RAW_CLIPS_DIR, exist_ok=True)
    os.makedirs(PROCESSED_CLIPS_DIR, exist_ok=True) # Create the new processed clips directory
    os.makedirs(CLIP_FRAMES_DIR, exist_ok=True) # Créer le nouveau dossier pour les frames

    if not os.path.exists(INPUT_CLIPS_JSON):
        print(f"❌ Fichier des clips '{INPUT_CLIPS_JSON}' introuvable.")
        # Écrire un fichier JSON vide pour downloaded_clip_paths.json
        with open(os.path.join("data", "downloaded_clip_paths.json"), "w") as f:
            json.dump([], f)
        sys.exit(1)

    with open(INPUT_CLIPS_JSON, "r", encoding="utf-8") as f:
        clips = json.load(f)

    # --- DÉBOGAGE : Aperçu des données lues depuis top_clips.json ---
    if clips:
        print("\n--- Aperçu des données lues depuis top_clips.json dans download_clips.py ---")
        for i, clip_data in enumerate(clips[:3]): # Affiche les 3 premiers clips pour vérification
            print(f"Clip {i+1}:")
            print(f"  ID: {clip_data.get('id', 'N/A')}")
            print(f"  Title: {clip_data.get('title', 'N/A')}")
            print(f"  Broadcaster Name: {clip_data.get('broadcaster_name', 'N/A')}")
            print(f"  URL: {clip_data.get('url', 'N/A')}")
        print("----------------------------------------------------------------------\n")
    # --- FIN DÉBOGAGE ---

    if not clips:
        print("⚠️ Aucun clip à télécharger. La liste des clips est vide.")
        with open(os.path.join("data", "downloaded_clip_paths.json"), "w") as f:
            json.dump([], f)
        return

    downloaded_and_processed_info = [] # Will store dicts with path, id, and actual duration
    for i, clip in enumerate(clips):
        clip_url = clip["url"]

        clip_id = clip.get("id", f"unknown_id_{i}")
        clip_title_raw = clip.get("title", "Titre inconnu")
        broadcaster_name_raw = clip.get("broadcaster_name", "Streamer inconnu")

        clip_title_escaped = ffmpeg_escape_string(clip_title_raw)
        broadcaster_name_escaped = ffmpeg_escape_string(broadcaster_name_raw)

        raw_output_filename = os.path.join(RAW_CLIPS_DIR, f"{clip_id}_raw.mp4")
        processed_output_filename = os.path.join(PROCESSED_CLIPS_DIR, f"{clip_id}_processed.mp4")
        first_frame_output_path = os.path.join(CLIP_FRAMES_DIR, f"{clip_id}_first_frame.jpg") # Chemin de la frame

        print(f"Téléchargement du clip {i+1}/{len(clips)}: {clip_title_raw} par {broadcaster_name_raw} (ID: {clip_id})...")
        try:
            # 1. Téléchargement avec yt-dlp
            yt_dlp_command = [
                "yt-dlp",
                "--output", raw_output_filename,
                "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                clip_url
            ]
            subprocess.run(yt_dlp_command, check=True)
            print(f"  ✅ Clip téléchargé: {raw_output_filename}")

            # 2. Prétraitement avec FFmpeg pour normaliser le format, les codecs et ajouter du texte
            print(f"  Prétraitement du clip {i+1}/{len(clips)}: {clip_title_raw} (ajout du texte)...")

            title_display = clip_title_escaped
            broadcaster_display = broadcaster_name_escaped

            font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
            if not os.path.exists(font_path):
                font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Regular.ttf"
                if not os.path.exists(font_path):
                    font_path = "sans-serif" # Generic font family name for FFmpeg
                    print(f"⚠️ Police spécifique non trouvée. Utilisation d'une police générique '{font_path}'.")

            font_size = 36
            text_color = "white"
            border_color = "black"
            border_width = 2

            title_filter = (
                f"drawtext=fontfile='{font_path}':"
                f"text='{title_display}':"
                f"x=(w-text_w)/2:y=H*0.04:"
                f"fontcolor={text_color}:fontsize={font_size}:"
                f"bordercolor={border_color}:borderw={border_width}"
            )

            broadcaster_filter = (
                f"drawtext=fontfile='{font_path}':"
                f"text='{broadcaster_display}':"
                f"x=(w-text_w)/2:y=H*0.04+text_h+5:"
                f"fontcolor={text_color}:fontsize={font_size}:"
                f"bordercolor={border_color}:borderw={border_width}"
            )

            video_filters = (
                "scale=1920:1080:force_original_aspect_ratio=decrease,"
                "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,"
                "setsar=1,fps=30,"
                f"{title_filter},"
                f"{broadcaster_filter}"
            )

            ffmpeg_preprocess_command = [
                "ffmpeg",
                "-i", raw_output_filename,
                "-vf", video_filters,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-ac", "2",
                "-ar", "44100",
                "-loglevel", "error",
                "-y",
                processed_output_filename
            ]
            subprocess.run(ffmpeg_preprocess_command, check=True, capture_output=True, text=True)
            print(f"  ✅ Clip prétraité avec texte: {processed_output_filename}")

            # --- NOUVEAU : Extraire la première frame du clip traité ---
            print(f"  Extraction de la première frame pour {clip_id}...")
            ffmpeg_extract_frame_command = [
                "ffmpeg",
                "-i", processed_output_filename,
                "-vframes", "1",
                "-q:v", "2", # Qualité de sortie (1-31, 1 est le meilleur)
                "-y",
                first_frame_output_path
            ]
            subprocess.run(ffmpeg_extract_frame_command, check=True, capture_output=True, text=True)
            print(f"  ✅ Première frame extraite: {first_frame_output_path}")
            # --- FIN NOUVEAU ---

            actual_duration = get_video_duration(processed_output_filename)
            print(f"  Durée réelle du clip traité: {actual_duration:.2f} secondes.")

            downloaded_and_processed_info.append({
                "id": clip_id,
                "path": processed_output_filename,
                "duration": actual_duration,
                "title": clip_title_raw,
                "broadcaster_name": broadcaster_name_raw,
                "first_frame_path": first_frame_output_path # Ajoute le chemin de la frame
            })

        except subprocess.CalledProcessError as e:
            print(f"  ❌ Erreur lors du traitement du clip {clip_url} (téléchargement ou prétraitement/extraction frame): {e}")
            if e.stdout: print(f"    STDOUT: {e.stdout}")
            if e.stderr: print(f"    STDERR: {e.stderr}")
        except Exception as e:
            print(f"  ❌ Erreur inattendue lors du traitement du clip {clip_url}: {e}")

    with open(os.path.join("data", "downloaded_clip_paths.json"), "w", encoding="utf-8") as f:
        json.dump(downloaded_and_processed_info, f, ensure_ascii=False, indent=2)

    print("✅ Téléchargement et prétraitement des clips terminé.")

if __name__ == "__main__":
    download_clips()