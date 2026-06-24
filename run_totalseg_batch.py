"""
Segmentation TotalSegmentator en masse — pancréas uniquement
===============================================================
Parcourt le dossier imagesTr (format nnU-Net) et lance TotalSegmentator
sur chaque image narrow FOV (suffixe _0000), en extrayant uniquement
le masque du pancréas.

Sert de BASELINE de comparaison avant le fine-tuning, et avant d'avoir
les vraies segmentations du radiologue.

Dépendances :
    pip install TotalSegmentator
"""

from pathlib import Path
from totalsegmentator.python_api import totalsegmentator
import shutil
import time

# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────

IMAGES_DIR   = Path(r"C:\nnunet_project\nnunet_raw\Dataset001_Pancreas\imagesTr")
OUTPUT_DIR   = Path(r"C:\Users\phuon\Desktop\Code\Charite_output\totalseg_baseline") # où stocker les résultats
CHANNEL_SUFFIX = "_0000"   # narrow FOV = canal 0 (celui qui a les labels)
TASK         = "total_mr"
ROBUST_CROP  = True        # nécessaire pour ton FOV restreint (cf. discussion précédente)

# ─────────────────────────────────────────────


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # On ne garde que les fichiers narrow FOV (canal 0), pas les wide (_0001)
    narrow_files = sorted(IMAGES_DIR.glob(f"*{CHANNEL_SUFFIX}.nii*"))

    if not narrow_files:
        print(f"❌ Aucun fichier trouvé dans {IMAGES_DIR} avec le suffixe {CHANNEL_SUFFIX}")
        return

    print(f"{len(narrow_files)} fichiers narrow FOV trouvés\n")

    n_success = 0
    n_failed = 0
    start_total = time.time()

    for idx, img_path in enumerate(narrow_files, start=1):
        # Nom du sujet : on retire le suffixe _0000 et l'extension
        case_id = img_path.name.replace(CHANNEL_SUFFIX, "").split(".nii")[0]

        print(f"[{idx}/{len(narrow_files)}] {case_id}")

        case_output_dir = OUTPUT_DIR / case_id
        case_output_dir.mkdir(parents=True, exist_ok=True)
        input=str(img_path)
        output=str(case_output_dir)
        # Si déjà traité, on skip (utile pour relancer après une interruption)
        final_pancreas_path = OUTPUT_DIR / f"{case_id}_pancreas.nii.gz"
        if final_pancreas_path.exists():
            print(f"   Déjà traité, skip")
            n_success += 1
            continue

        try:
            t0 = time.time()

            totalsegmentator(input, output, task="total_mr", fast=False)

            # totalsegmentator(
            #     input=str(img_path),
            #     output=str(case_output_dir),
            #     task=TASK,
            #     roi_subset=["pancreas"],
            #     robust_crop=ROBUST_CROP,
            # )
            elapsed = time.time() - t0

            # Le résultat avec roi_subset=["pancreas"] génère un fichier pancreas.nii.gz
            pancreas_file = case_output_dir / "pancreas.nii.gz"
            if pancreas_file.exists():
                # Déplacer (pas copier) avec un nom plus explicite dans le dossier racine
                shutil.move(str(pancreas_file), str(final_pancreas_path))
                print(f"   ✓ Terminé en {elapsed:.1f}s → {final_pancreas_path.name}")
                n_success += 1
            else:
                print(f"Pas de fichier pancreas.nii.gz généré dans {case_output_dir}")
                n_failed += 1

            # Nettoyer le dossier intermédiaire (on ne garde que le fichier final à la racine)
            if case_output_dir.exists():
                shutil.rmtree(case_output_dir)

        except Exception as e:
            print(f"   ✗ Erreur : {e}")
            n_failed += 1

        print()

    total_elapsed = time.time() - start_total
    print("=" * 55)
    print(f"Terminé : {n_success} succès, {n_failed} échecs")
    print(f"Temps total : {total_elapsed/60:.1f} minutes")
    print(f"Résultats : {OUTPUT_DIR}")
    print()


if __name__ == "__main__":
    main()
