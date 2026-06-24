"""
Correction en masse : suppression de la dimension fantôme (squeeze) dans des NIfTI
=====================================================================================
Certains NIfTI convertis depuis DICOM ont une 4e dimension fantôme de taille 1
(ex: shape (576, 496, 19, 1) au lieu de (576, 496, 19)).
Ce script corrige tous les fichiers .nii.gz d'un dossier en une fois.
"""

import nibabel as nib
import numpy as np
from pathlib import Path

# ─────────────────────────────────────────────
INPUT_DIR  = r"C:\nnunet_project\nnunet_raw\Dataset001_Pancreas\imagesTr"   # dossier à corriger
# Si tu veux écrire ailleurs plutôt que d'écraser, mets un autre chemin ici.
# Si None, les fichiers sont corrigés EN PLACE (écrasés après vérification).
OUTPUT_DIR = None
# ─────────────────────────────────────────────


def fix_file(path: Path, output_path: Path):
    img = nib.load(str(path))
    shape_before = img.shape

    if len(shape_before) <= 3:
        return False, shape_before, shape_before  # rien à faire

    data = np.squeeze(img.get_fdata())
    new_img = nib.Nifti1Image(data, img.affine)
    nib.save(new_img, str(output_path))
    return True, shape_before, data.shape


def main():
    input_dir = Path(INPUT_DIR)
    output_dir = Path(OUTPUT_DIR) if OUTPUT_DIR else input_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    nifti_files = sorted(input_dir.glob("*.nii"))
    print(f"{len(nifti_files)} fichiers NIfTI trouvés dans {input_dir}\n")

    n_fixed = 0
    n_already_ok = 0

    for f in nifti_files:
        out_path = output_dir / f.name
        fixed, before, after = fix_file(f, out_path)
        if fixed:
            print(f"  ✓ {f.name} : {before} → {after}")
            n_fixed += 1
        else:
            print(f"  - {f.name} : déjà OK {before}")
            n_already_ok += 1

    print(f"\n Terminé : {n_fixed} fichiers corrigés, {n_already_ok} déjà corrects")


if __name__ == "__main__":
    main()
