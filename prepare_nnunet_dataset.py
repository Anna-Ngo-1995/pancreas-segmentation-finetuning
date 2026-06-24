"""
Préparation du dataset nnU-Net pour la segmentation du pancréas en IRM T2
=========================================================================
Structure attendue en entrée :
    data_root/
    ├── subject_01/
    │   ├── narrow/      ← dossier DICOM T2 narrow FOV
    │   └── wide/        ← dossier DICOM T2 wide FOV
    ├── subject_02/
    │   ├── narrow/
    │   └── wide/
    └── ...

Structure générée en sortie (nnU-Net) :
    nnunet_raw/
    └── Dataset001_Pancreas/
        ├── imagesTr/
        │   ├── pancreas_001_0000.nii.gz   ← T2 narrow (canal 0)
        │   ├── pancreas_001_0001.nii.gz   ← T2 wide   (canal 1)
        │   ├── pancreas_002_0000.nii.gz
        │   └── ...
        ├── labelsTr/                       ← à remplir après segmentation radiologue
        │   └── (vide pour l'instant)
        └── dataset.json

Dépendances :
    pip install pydicom SimpleITK nibabel numpy
"""

import os
import json
import shutil
import numpy as np
from pathlib import Path

# ─────────────────────────────────────────────
#  CONFIGURATION — adapter à ta situation
# ─────────────────────────────────────────────

DATA_ROOT    = r"C:\MRIData\Vida-XT\Repeatability\Splitted_data"  
OUTPUT_ROOT  = r"C:\MRIData\Vida-XT\Repeatability\Splitted_data\Nifti"    # où sera créé Dataset001_Pancreas
NARROW_DIR   = "T2_Haste_Ax_RespiLibreTomoStack"   # nom du sous-dossier narrow FOV dans chaque sujet
WIDE_DIR     = "T2_Haste_Ax_RespiLibre"     # nom du sous-dossier wide FOV dans chaque sujet
DATASET_ID   = 1          # identifiant numérique du dataset nnU-Net

# ─────────────────────────────────────────────


def dicom_to_nifti(dicom_dir: Path, output_path: Path) -> bool:
    """
    Convertit un dossier DICOM en fichier NIfTI.
    Retourne True si succès.
    """
    try:
        import SimpleITK as sitk
        reader = sitk.ImageSeriesReader()
        dicom_files = reader.GetGDCMSeriesFileNames(str(dicom_dir))
        if not dicom_files:
            print(f"  ⚠️  Aucun fichier DICOM trouvé dans {dicom_dir}")
            return False
        reader.SetFileNames(dicom_files)
        image = reader.Execute()
        sitk.WriteImage(image, str(output_path))
        print(f"  ✓  {dicom_dir.name} → {output_path.name}")
        return True
    except Exception as e:
        print(f"  ✗  Erreur conversion {dicom_dir}: {e}")
        return False


def resample_to_reference(moving_path: Path, reference_path: Path, output_path: Path):
    """
    Resampler l'image wide FOV dans l'espace du narrow FOV.
    Utile si les deux images n'ont pas exactement la même grille.
    """
    import SimpleITK as sitk
    reference = sitk.ReadImage(str(reference_path))
    moving    = sitk.ReadImage(str(moving_path))

    resampler = sitk.ResampleImageFilter()
    resampler.SetReferenceImage(reference)
    resampler.SetInterpolator(sitk.sitkLinear)
    resampler.SetDefaultPixelValue(0)
    resampler.SetTransform(sitk.Transform())  # identité (pas de recalage)

    resampled = resampler.Execute(moving)
    sitk.WriteImage(resampled, str(output_path))
    print(f"  ✓  Wide FOV resamplé sur la grille narrow")


def check_image_info(nifti_path: Path):
    """Affiche les infos de l'image pour vérification."""
    import SimpleITK as sitk
    img = sitk.ReadImage(str(nifti_path))
    size    = img.GetSize()
    spacing = img.GetSpacing()
    print(f"     Taille  : {size[0]} x {size[1]} x {size[2]} voxels")
    print(f"     Spacing : {spacing[0]:.2f} x {spacing[1]:.2f} x {spacing[2]:.2f} mm")
    return size, spacing


def create_dataset_json(output_dir: Path, n_subjects: int):
    """Génère le dataset.json requis par nnU-Net."""
    dataset = {
        "channel_names": {
            "0": "T2_narrow_FOV",
            "1": "T2_wide_FOV"
        },
        "labels": {
            "background": 0,
            "pancreas":   1
        },
        "numTraining": n_subjects,
        "file_ending": ".nii.gz",
        "name": "Pancreas_T2_MRI",
        "description": "Fine-tuning TotalSegmentator - segmentation pancréas IRM T2",
        "reference": "Segmentation manuelle par radiologue",
        "licence": "Internal research use only",
        "release": "1.0"
    }
    json_path = output_dir / "dataset.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    print(f"\n✓ dataset.json créé : {json_path}")


def prepare_dataset():
    data_root   = Path(DATA_ROOT)
    output_root = Path(OUTPUT_ROOT)
    dataset_dir = output_root / f"Dataset{DATASET_ID:03d}_Pancreas"
    images_dir  = dataset_dir / "imagesTr"
    labels_dir  = dataset_dir / "labelsTr"
    tmp_dir     = dataset_dir / "_tmp_nifti"  # conversion intermédiaire

    # Créer les dossiers
    for d in [images_dir, labels_dir, tmp_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Lister les sujets
    subjects = sorted([
        d for d in data_root.iterdir()
        if d.is_dir() and (d / NARROW_DIR).exists()
    ])

    if not subjects:
        print(f"❌ Aucun sujet trouvé dans {data_root}")
        print(f"   Vérifier que les sous-dossiers '{NARROW_DIR}' et '{WIDE_DIR}' existent.")
        return

    print(f"📁 {len(subjects)} sujets trouvés\n")
    success_count = 0

    for idx, subject_dir in enumerate(subjects, start=1):
        case_id  = f"pancreas_{idx:03d}"
        path_narrow_dicom = subject_dir / NARROW_DIR
        narrow_dicom =  path_narrow_dicom #next(f for f in path_narrow_dicom.iterdir() if f.is_file())
        path_wide_dicom   = subject_dir / WIDE_DIR
        wide_dicom = path_wide_dicom # next(f for f in path_wide_dicom.iterdir() if f.is_file())

        print(f"[{idx}/{len(subjects)}] Sujet : {subject_dir.name}")

        # Chemins de sortie finaux
        out_narrow = images_dir / f"{case_id}_0000.nii.gz"
        out_wide   = images_dir / f"{case_id}_0001.nii.gz"

        # Conversion narrow DICOM → NIfTI
        tmp_narrow = tmp_dir / f"{case_id}_narrow_raw.nii.gz"
        ok_narrow  = dicom_to_nifti(narrow_dicom, tmp_narrow)
        if not ok_narrow:
            print(f"  ⚠️  Sujet {subject_dir.name} ignoré (narrow manquant)\n")
            continue

        # Conversion wide DICOM → NIfTI
        tmp_wide = tmp_dir / f"{case_id}_wide_raw.nii.gz"
        ok_wide  = dicom_to_nifti(wide_dicom, tmp_wide)

        # Infos narrow
        print(f"  → Narrow FOV :")
        check_image_info(tmp_narrow)

        # Copier narrow vers imagesTr
        shutil.copy2(tmp_narrow, out_narrow)

        if ok_wide:
            print(f"  → Wide FOV (avant resampling) :")
            check_image_info(tmp_wide)
            # Resampler wide sur la grille du narrow
            resample_to_reference(tmp_wide, tmp_narrow, out_wide)
            print(f"  → Wide FOV (après resampling) :")
            check_image_info(out_wide)
        else:
            print(f"  ⚠️  Wide FOV manquant pour {subject_dir.name}, "
                  f"copie du narrow comme canal 1 (fallback)")
            shutil.copy2(out_narrow, out_wide)

        # Placeholder label (à remplacer après segmentation radiologue)
        # On crée un masque vide de même dimension que narrow
        import SimpleITK as sitk
        ref_img    = sitk.ReadImage(str(out_narrow))
        empty_mask = sitk.Image(ref_img.GetSize(), sitk.sitkUInt8)
        empty_mask.CopyInformation(ref_img)
        label_path = labels_dir / f"{case_id}.nii.gz"
        sitk.WriteImage(empty_mask, str(label_path))
        print(f"  ✓  Label placeholder créé (à remplacer le 23)\n")

        success_count += 1

    # dataset.json
    create_dataset_json(dataset_dir, success_count)

    # Nettoyer tmp
    shutil.rmtree(tmp_dir)

    # Résumé
    print("\n" + "="*55)
    print(f"Dataset prêt : {success_count}/{len(subjects)} sujets convertis")
    print(f"Dossier de sortie : {dataset_dir}")
    print()
    print("Prochaines étapes :")
    print()
    print("1. Copier les segmentations du radiologue dans :")
    print(f"   {labels_dir}")
    print("   → Les fichiers doivent s'appeler pancreas_001.nii.gz, etc.")
    print("   → Labels : 0 = fond, 1 = pancréas")
    print()
    print("2. Définir la variable d'environnement nnU-Net :")
    print(f'   set nnUNet_raw="{output_root}"')
    print(f'   set nnUNet_preprocessed="{output_root}\\preprocessed"')
    print(f'   set nnUNet_results="{output_root}\\results"')
    print()
    print("3. Vérifier le dataset :")
    print(f"   nnUNetv2_plan_and_preprocess -d {DATASET_ID} --verify_dataset_integrity")
    print()
    print("4. Fine-tuning depuis les poids TotalSegmentator :")
    print(f"   nnUNetv2_train {DATASET_ID} 3d_fullres 0 \\")
    print("     --pretrained_weights <chemin_poids_totalsegmentator>\\checkpoint_final.pth")


if __name__ == "__main__":
    prepare_dataset()
