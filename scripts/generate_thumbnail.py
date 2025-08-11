import os
import json
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError # requests et BytesIO ne sont plus nécessaires
from datetime import datetime

# Chemins des fichiers
# INPUT_CLIPS_JSON n'est plus la source directe, on utilise downloaded_clip_paths.json
DOWNLOADED_CLIPS_INFO_JSON = os.path.join("data", "downloaded_clip_paths.json")
OUTPUT_THUMBNAIL_PATH = os.path.join("data", "thumbnail.jpg") # Miniature finale
LOGO_PATH = os.path.join("assets", "your_logo.png") # Chemin vers votre logo PNG

# Dimensions de la miniature YouTube standard
THUMBNAIL_WIDTH = 1280
THUMBNAIL_HEIGHT = 720

def get_font(size):
    """Tente de charger une police TrueType ou utilise la police par défaut."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", # Linux (souvent sur GitHub Actions)
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",    # macOS
        "C:/Windows/Fonts/arialbd.ttf"                          # Windows
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except IOError:
                continue
            
    print("⚠️ Aucune police TrueType trouvée pour la miniature. Utilisation de la police par défaut de Pillow.")
    return ImageFont.load_default()

# La fonction download_image n'est plus nécessaire ici !
# def download_image(url):
#     # ... (supprimer cette fonction)

def generate_thumbnail():
    print("🏞️ Démarrage de la génération de la miniature personnalisée...")

    data_dir = os.path.dirname(OUTPUT_THUMBNAIL_PATH)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"Dossier de données créé : {data_dir}")

    # Utiliser DOWNLOADED_CLIPS_INFO_JSON comme source
    if not os.path.exists(DOWNLOADED_CLIPS_INFO_JSON):
        print(f"❌ Erreur: Le fichier '{DOWNLOADED_CLIPS_INFO_JSON}' est introuvable. Assurez-vous que la compilation a réussi et a sauvegardé les chemins des frames.")
        generate_default_thumbnail("Fichier de clips introuvable pour la miniature.")
        return 

    with open(DOWNLOADED_CLIPS_INFO_JSON, "r", encoding="utf-8") as f:
        clips_data = json.load(f)

    today_date = datetime.now()
    date_str = today_date.strftime("%d/%m/%Y")

    if not clips_data:
        print("⚠️ Aucune donnée de clip à traiter. Le fichier downloaded_clip_paths.json est vide. Génération d'une miniature par défaut.")
        generate_default_thumbnail(f"Aucun clip trouvé pour aujourd'hui ({date_str}).")
        return 

    # Sélectionner les chemins des 4 premières frames disponibles
    selected_frame_paths = []
    for clip in clips_data:
        frame_path = clip.get("first_frame_path")
        if frame_path and os.path.exists(frame_path): # Vérifier que le chemin existe bien sur le disque
            selected_frame_paths.append(frame_path)
        if len(selected_frame_paths) >= 4:
            break

    if not selected_frame_paths:
        print("⚠️ Aucune frame de vignette disponible ou les chemins sont invalides. Impossible de créer la miniature basée sur les clips. Génération d'une miniature par défaut.")
        generate_default_thumbnail(f"Aucune frame disponible pour la miniature ({date_str}).")
        return 

    # Créer l'image finale vide
    final_image = Image.new('RGB', (THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), color=(0, 0, 0))

    quadrant_width = THUMBNAIL_WIDTH // 2
    quadrant_height = THUMBNAIL_HEIGHT // 2

    positions = [
        (0, 0),
        (quadrant_width, 0),
        (0, quadrant_height),
        (quadrant_width, quadrant_height)
    ]

    loaded_images = []
    for path in selected_frame_paths: # Itérer sur les chemins locaux des frames
        try:
            img = Image.open(path).convert("RGB")
            loaded_images.append(img)
        except (IOError, UnidentifiedImageError) as e:
            print(f"  ❌ Échec de chargement de l'image locale {path}: {e}. Remplacement par une image noire.")
            loaded_images.append(Image.new('RGB', (quadrant_width, quadrant_height), color='black'))

    # S'assurer qu'il y a exactement 4 images (remplir avec du noir si moins de 4 ont été chargées)
    while len(loaded_images) < 4:
        loaded_images.append(Image.new('RGB', (quadrant_width, quadrant_height), color='black'))

    # Coller les images dans les quadrants
    for i, img in enumerate(loaded_images):
        if i < len(positions):
            img = img.resize((quadrant_width, quadrant_height), Image.Resampling.LANCZOS)
            final_image.paste(img, positions[i])

    # --- Superposer le logo au centre ---
    if os.path.exists(LOGO_PATH):
        try:
            logo = Image.open(LOGO_PATH).convert("RGBA")
            
            # Calculer la position centrale du logo avec sa taille d'origine
            logo_x = (THUMBNAIL_WIDTH - logo.width) // 2
            logo_y = (THUMBNAIL_HEIGHT - logo.height) // 2
            
            final_image.paste(logo, (logo_x, logo_y), logo)
            print("✅ Logo superposé.")
        except Exception as e:
            print(f"❌ Erreur lors de la superposition du logo : {e}")
    else:
        print(f"⚠️ Fichier logo introuvable à {LOGO_PATH}. La miniature sera générée sans logo.")

    # Sauvegarder la miniature finale
    try:
        final_image.save(OUTPUT_THUMBNAIL_PATH)
        print(f"✅ Miniature générée et sauvegardée avec succès dans {OUTPUT_THUMBNAIL_PATH}")
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde de la miniature finale : {e}")

def generate_default_thumbnail(message):
    """Génère une miniature par défaut avec un message."""
    print(f"Génération d'une miniature par défaut : {message}")
    default_thumbnail = Image.new('RGB', (THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), color = 'black')
    draw = ImageDraw.Draw(default_thumbnail)
    
    font = get_font(40)
    bbox = draw.textbbox((0, 0), message, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    draw.text(((THUMBNAIL_WIDTH - text_width) / 2, (THUMBNAIL_HEIGHT - text_height) / 2), message, font=font, fill=(255, 255, 255))
    
    try:
        default_thumbnail.save(OUTPUT_THUMBNAIL_PATH)
        print(f"✅ Miniature par défaut générée et sauvegardée dans {OUTPUT_THUMBNAIL_PATH}.")
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde de la miniature par défaut : {e}")

if __name__ == "__main__":
    generate_thumbnail()