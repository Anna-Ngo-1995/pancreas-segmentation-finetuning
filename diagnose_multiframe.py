"""
Diagnostic et conversion d'un DICOM multi-frame (1 seul fichier = plusieurs coupes/volumes)
=============================================================================================
Cas Siemens "enhanced DICOM" : toutes les coupes (et parfois plusieurs volumes)
sont stockées dans UN SEUL fichier .dcm, au lieu d'un fichier par coupe.
"""

import pydicom
import SimpleITK as sitk
import numpy as np
from pathlib import Path

# ─────────────────────────────────────────────
DICOM_FILE = r"C:\MRIData\Vida-XT\Repeatability\Splitted_data\BC_9f7d-d97c-46\T2_Haste_Ax_RespiLibreTomoStack\46946105"
OUTPUT_NIFTI = r"C:\MRIData\Vida-XT\Repeatability\Splitted_data\BC_9f7d-d97c-46\sortie_test.nii.gz"
# ─────────────────────────────────────────────

print(f"📄 Lecture du fichier : {DICOM_FILE}\n")

# 1. Inspection avec pydicom pour comprendre la structure
ds = pydicom.dcmread(DICOM_FILE, force=True)

print("🔍 Tags clés :")
print(f"   SOPClassUID         : {getattr(ds, 'SOPClassUID', '-')}")
print(f"   NumberOfFrames       : {getattr(ds, 'NumberOfFrames', '-')}")
print(f"   Rows x Columns       : {getattr(ds, 'Rows', '-')} x {getattr(ds, 'Columns', '-')}")
print(f"   Modality             : {getattr(ds, 'Modality', '-')}")

# Vérifier si c'est bien du multi-frame
n_frames = getattr(ds, 'NumberOfFrames', None)
if n_frames:
    print(f"\n✓ Confirmé : DICOM multi-frame avec {n_frames} frames (coupes)")
else:
    print("\n⚠️  Pas de tag NumberOfFrames trouvé — structure différente, à investiguer")

# Vérifier s'il y a plusieurs "stacks" (volumes) dans ce multi-frame
# Tag utile : PerFrameFunctionalGroupsSequence (DICOM enhanced)
if hasattr(ds, 'PerFrameFunctionalGroupsSequence'):
    print(f"\n🔍 Structure 'Enhanced MR' détectée (PerFrameFunctionalGroupsSequence)")
    n_pffg = len(ds.PerFrameFunctionalGroupsSequence)
    print(f"   {n_pffg} groupes fonctionnels par frame")

    # Inspecter quelques tags variables par frame (position, stack ID, écho...)
    print("\n   Aperçu des premières frames :")
    for i in range(min(5, n_pffg)):
        frame_group = ds.PerFrameFunctionalGroupsSequence[i]
        stack_id = "-"
        in_stack_pos = "-"
        try:
            stack_id = frame_group.FrameContentSequence[0].StackID
            in_stack_pos = frame_group.FrameContentSequence[0].InStackPositionNumber
        except Exception:
            pass
        print(f"     Frame {i}: StackID={stack_id}, InStackPosition={in_stack_pos}")

    # Compter le nombre de StackID uniques (= nombre de volumes distincts)
    stack_ids = []
    for frame_group in ds.PerFrameFunctionalGroupsSequence:
        try:
            stack_ids.append(frame_group.FrameContentSequence[0].StackID)
        except Exception:
            pass
    unique_stacks = set(stack_ids)
    print(f"\n   → {len(unique_stacks)} StackID unique(s) détecté(s) : {unique_stacks}")
    if len(unique_stacks) > 1:
        print("   ⚠️  PLUSIEURS VOLUMES dans ce fichier (probablement narrow + wide, ou multi-écho)")
    else:
        print("   ✓ Un seul volume — conversion directe possible")

# 2. Conversion directe avec SimpleITK (lecture simple, sans ImageSeriesReader)
print("\n🔄 Tentative de conversion directe avec SimpleITK...")
try:
    image = sitk.ReadImage(DICOM_FILE)
    size = image.GetSize()
    print(f"   ✓ Image lue : taille = {size}")
    sitk.WriteImage(image, OUTPUT_NIFTI)
    print(f"   ✓ NIfTI écrit : {OUTPUT_NIFTI}")
except Exception as e:
    print(f"   ✗ Erreur SimpleITK ReadImage : {e}")
    print("   → Si plusieurs StackID détectés ci-dessus, il faut séparer les frames")
    print("     manuellement par StackID avant conversion (voir étape suivante).")
