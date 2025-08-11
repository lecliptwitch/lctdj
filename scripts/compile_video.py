import subprocess
import os
import json
import sys
from datetime import datetime, timedelta

# --- Chemins des fichiers ---
INPUT_PATHS_JSON = os.path.join("data", "downloaded_clip_paths.json")
OUTPUT_VIDEO_PATH = os.path.join("output", "compiled_video.mp4")
CLIPS_LIST_TXT = os.path.join("data", "clips_list.txt") # Utilisé pour concaténation initiale

# --- Chemins pour les frames des vignettes ---
THUMBNAIL_FRAMES_DIR = os.path.join("data", "thumbnail_frames") # Nouveau dossier pour stocker les frames

# --- PARAMÈTRES FFmpeg ---
# ... (votre code existant pour FONT_PATH_FFMPEG et get_ffmpeg_font_path())
# Obtenir le chemin de la police pour FFmpeg (comme défini précédemment)
def get_ffmpeg_font_path():
    """Tente de trouver un chemin de police fiable pour FFmpeg."""
    font_paths = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", # Common on Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Regular.ttf",        # Common on Linux
        "/System/Library/Fonts/Supplemental/Arial.ttf",                  # macOS
        "C:/Windows/Fonts/arial.ttf"                                     # Windows
    ]
    for path in font_paths:
        if os.path.exists(path):
            print(f"✅ Police trouvée et utilisée pour FFmpeg: {path}")
            return path
    print("⚠️ Aucune police TrueType spécifique trouvée. Utilisation d'une police générique 'sans-serif'.")
    return "sans-serif" # Fallback to generic font family name for FFmpeg

FONT_PATH_FFMPEG = get_ffmpeg_font_path()

# --- NOUVEAU PARAMÈTRE : Limite le nombre total de clips dans la compilation finale ---
MAX_TOTAL_CLIPS = 30

# Obtenir le répertoire racine du dépôt (où se trouve .github/)
REPO_ROOT = os.getcwd() 

def format_duration(seconds):
    """Formate une durée en secondes en HH:MM:SS."""
    if seconds < 0:
        seconds = 0
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def extract_first_frame(video_path, output_image_path):
    """Extrait la première frame d'une vidéo et la sauvegarde comme image."""
    output_dir = os.path.dirname(output_image_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Dossier pour les frames de vignette créé : {output_dir}")

    command = [
        "ffmpeg",
        "-i", video_path,
        "-vf", "select='eq(n,0)'", # Sélectionne la première frame
        "-vsync", "vfr",
        "-q:v", "2", # Qualité élevée pour l'image
        "-y",
        output_image_path
    ]
    print(f"Extraction de la première frame de {os.path.basename(video_path)}: {' '.join(command)}")
    try:
        # Utiliser capture_output=True pour voir les erreurs de FFmpeg
        subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"✅ Première frame extraite et sauvegardée : {output_image_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de l'extraction de la frame de {video_path}: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Erreur inattendue lors de l'extraction de la frame de {video_path}: {e}")
        return False

def compile_video():
    print("🎬 Démarrage de la compilation des clips vidéo avec timecodes...")

    output_dir = os.path.dirname(OUTPUT_VIDEO_PATH)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Dossier de sortie créé : {output_dir}")
        
    if not os.path.exists(INPUT_PATHS_JSON):
        print(f"❌ Fichier des chemins de clips téléchargés '{INPUT_PATHS_JSON}' introuvable.")
        sys.exit(1)

    # Lire les informations des clips téléchargés et prétraités (incluant la durée réelle)
    with open(INPUT_PATHS_JSON, "r") as f:
        downloaded_clip_info = json.load(f)

    if not downloaded_clip_info:
        print("⚠️ Aucune information de vidéo téléchargée à compiler. Fin de l'étape de compilation.")
        sys.exit(0)

    # Filtrer et limiter les clips à traiter
    final_clips_to_process = []
    # Créer une liste temporaire pour collecter les informations mises à jour
    updated_downloaded_clip_info = []

    for clip_data in downloaded_clip_info:
        if clip_data.get("path") and clip_data.get("duration", 0.0) > 0:
            final_clips_to_process.append(clip_data)
        if len(final_clips_to_process) >= MAX_TOTAL_CLIPS:
            break

    # NOUVELLE LOGIQUE : Extraire la première frame pour les vignettes
    print("\n🖼️ Extraction des premières frames des clips pour la miniature...")
    for clip_info in final_clips_to_process:
        clip_id = clip_info['id'] # Supposons que chaque clip a un ID
        clip_path = clip_info['path']
        frame_output_path = os.path.join(THUMBNAIL_FRAMES_DIR, f"{clip_id}_first_frame.jpg")
        
        if extract_first_frame(clip_path, frame_output_path):
            # Mettre à jour l'information du clip avec le chemin de la frame
            clip_info['first_frame_path'] = frame_output_path
        else:
            print(f"⚠️ Impossible d'extraire la frame pour le clip {clip_id}. La miniature pourrait être affectée.")
            # Optionnel: Supprimer le clip de final_clips_to_process si la frame est critique
            # Ou simplement ne pas ajouter 'first_frame_path' si l'extraction échoue

        # Ajouter l'info du clip (modifiée ou non) à la liste mise à jour
        updated_downloaded_clip_info.append(clip_info)
    
    # Écrire les informations de clips mises à jour (avec les chemins des frames)
    with open(INPUT_PATHS_JSON, "w", encoding="utf-8") as f:
        json.dump(updated_downloaded_clip_info, f, ensure_ascii=False, indent=2)
    print("✅ Chemins des frames ajoutés à downloaded_clip_paths.json.")


    if not final_clips_to_process:
        print("⚠️ Après application des filtres et limites, aucune vidéo à compiler. Fin de l'étape.")
        sys.exit(0)

    print(f"Compilation de {len(final_clips_to_process)} clips (max {MAX_TOTAL_CLIPS} clips).")

    # --- Étape 1: Concaténation initiale (rapide) sans réencodage ---
    # ... (Le reste de votre code existant pour la concaténation vidéo et audio)
    temp_concat_video_path = os.path.join(output_dir, "temp_concat_video_no_audio.mp4")
    temp_concat_audio_path = os.path.join(output_dir, "temp_concat_audio.aac")

    # Crée le fichier de liste pour la concaténation
    with open(CLIPS_LIST_TXT, "w") as f:
        for clip_info in final_clips_to_process:
            absolute_clip_path = os.path.abspath(clip_info['path'])
            f.write(f"file '{absolute_clip_path}'\n")

    concat_video_command = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", CLIPS_LIST_TXT,
        "-c:v", "copy",
        "-an",
        "-y",
        temp_concat_video_path
    ]
    print(f"Exécution de la commande FFmpeg (concaténation vidéo initiale sans audio): {' '.join(concat_video_command)}")
    try:
        subprocess.run(concat_video_command, check=True, capture_output=True, text=True)
        print("✅ Concaténation vidéo initiale terminée.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de la concaténation vidéo initiale : {e.stderr}")
        sys.exit(1)

    # --- Étape 2: Concaténation et Normalisation Audio ---
    audio_inputs_cmd = []
    for clip_info in final_clips_to_process:
        absolute_clip_path = os.path.abspath(clip_info['path'])
        audio_inputs_cmd.extend(["-i", absolute_clip_path])
        
    audio_filter_complex = ""
    if len(final_clips_to_process) > 1:
        audio_filter_complex = "".join([f"[{i}:a]" for i in range(len(final_clips_to_process))])
        audio_filter_complex += f"concat=n={len(final_clips_to_process)}:v=0:a=1[aout];[aout]loudnorm=I=-16:TP=-1.5:LRA=11"
    else:
        audio_filter_complex = "[0:a]loudnorm=I=-16:TP=-1.5:LRA=11"

    audio_command = [
        "ffmpeg",
        *audio_inputs_cmd,
        "-filter_complex", audio_filter_complex,
        "-c:a", "aac",
        "-b:a", "192k",
        "-ac", "2",
        "-ar", "44100",
        "-vn",
        "-y",
        temp_concat_audio_path
    ]

    print(f"\nExécution de la commande FFmpeg (extraction, concaténation et normalisation audio): {' '.join(audio_command)}")
    try:
        subprocess.run(audio_command, check=True, capture_output=True, text=True)
        print("✅ Audio combiné et normalisé avec succès.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors du traitement audio : {e.stderr}")
        sys.exit(1)

    # --- Étape 3: Application des timecodes sur la vidéo concaténée et fusion avec l'audio ---
    drawtext_filters = []
    current_offset = 0.0
    for clip_info in final_clips_to_process:
        start_time_str = format_duration(current_offset)
        clip_duration = clip_info.get('duration', 0.0) 
        
        text_content = f"{start_time_str} - {clip_info['title']} par {clip_info['broadcaster_name']}"
        escaped_text = text_content.replace("'", "'\\''") 
        
        drawtext_filters.append(
            f"drawtext="
            f"fontfile='{FONT_PATH_FFMPEG}':"
            f"text='{escaped_text}':"
            f"x=(w-text_w)/2:"
            f"y=h-th-20:"
            f"fontsize=36:"
            f"fontcolor=white:"
            f"box=1:"
            f"boxcolor=black@0.6:"
            f"enable='between(t,{current_offset},{current_offset + min(clip_duration, 5)})'"
        )
        current_offset += clip_duration

    video_filter_complex = ",".join(drawtext_filters)

    final_command = [
        "ffmpeg",
        "-i", temp_concat_video_path,
        "-i", temp_concat_audio_path,
        "-filter_complex", video_filter_complex,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-y",
        OUTPUT_VIDEO_PATH
    ]
    
    print(f"\nExécution de la commande FFmpeg (ajout timecodes et fusion finale): {' '.join(final_command)}")
    try:
        process = subprocess.run(final_command, check=True, capture_output=True, text=True)
        print(f"✅ Compilation vidéo finale terminée avec timecodes: {OUTPUT_VIDEO_PATH}")
        if process.stdout: print("FFmpeg STDOUT (final):\n", process.stdout)
        if process.stderr: print("FFmpeg STDERR (final):\n", process.stderr)

        # Nettoyage des fichiers temporaires et des frames de vignette
        os.remove(temp_concat_video_path)
        os.remove(temp_concat_audio_path)
        os.remove(CLIPS_LIST_TXT)
        
        # Supprimer les frames de vignette après usage (ou les garder si tu veux les inspecter)
        # for clip_info in updated_downloaded_clip_info:
        #     if 'first_frame_path' in clip_info and os.path.exists(clip_info['first_frame_path']):
        #         os.remove(clip_info['first_frame_path'])
        # if os.path.exists(THUMBNAIL_FRAMES_DIR) and not os.listdir(THUMBNAIL_FRAMES_DIR): # Supprime le dossier s'il est vide
        #     os.rmdir(THUMBNAIL_FRAMES_DIR)

        print("✅ Fichiers temporaires nettoyés.")

    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de la compilation vidéo finale : {e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur inattendue lors de la compilation vidéo : {e}")
        sys.exit(1)

if __name__ == "__main__":
    compile_video()