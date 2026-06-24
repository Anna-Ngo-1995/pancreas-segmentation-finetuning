"""
Diagnostic de lecture DICOM avec SimpleITK
============================================
À lancer pour comprendre pourquoi dicom_to_nifti() échoue.
"""

import SimpleITK as sitk
from pathlib import Path

# ─────────────────────────────────────────────
DICOM_FOLDER = r"C:\MRIData\Vida-XT\Répétabilité\Splitted_data\BC_9f7d-d97c-46\T2_Haste_Ax_RespiLibreTomoStack"   # adapter
# ─────────────────────────────────────────────

folder = Path(DICOM_FOLDER)

print(f"📁 Dossier testé : {folder}")
print(f"   Existe : {folder.exists()}")
print(f"   Est un dossier : {folder.is_dir()}\n")

# Lister tout ce qu'il y a dedans (sans filtrer)
all_files = list(folder.iterdir())
print(f"📄 Contenu du dossier ({len(all_files)} éléments) :")
for f in all_files[:15]:
    tag = "📁 DIR" if f.is_dir() else "📄 FILE"
    print(f"   {tag}  {f.name}")
if len(all_files) > 15:
    print(f"   ... et {len(all_files) - 15} de plus")

print()

# Essayer de lire le premier fichier comme DICOM brut (pydicom)
print("🔍 Test de lecture brute avec pydicom :")
try:
    import pydicom
    first_file = next((f for f in all_files if f.is_file()), None)
    if first_file:
        ds = pydicom.dcmread(str(first_file), force=True)
        print(f"   ✓ Fichier lu : {first_file.name}")
        print(f"   SeriesInstanceUID : {getattr(ds, 'SeriesInstanceUID', 'absent')}")
        print(f"   Modality          : {getattr(ds, 'Modality', 'absent')}")
    else:
        print("   ⚠️  Aucun fichier trouvé (que des sous-dossiers ?)")
except Exception as e:
    print(f"   ✗ Erreur pydicom : {e}")

print()

# Essayer GetGDCMSeriesFileNames (méthode utilisée dans le script principal)
print("🔍 Test SimpleITK GetGDCMSeriesFileNames :")
reader = sitk.ImageSeriesReader()
series_files = reader.GetGDCMSeriesFileNames(str(folder))
print(f"   Fichiers détectés comme série DICOM : {len(series_files)}")

if len(series_files) == 0:
    print("\n   ⚠️  PROBLÈME CONFIRMÉ : GDCM ne détecte aucune série dans ce dossier.")
    print("   Causes possibles :")
    print("   - Les fichiers sont dans un sous-dossier (pas directement ici)")
    print("   - Les fichiers ne sont pas reconnus comme DICOM valides")
    print("   - Plusieurs SeriesInstanceUID mélangés, GDCM en choisit un par défaut")

    # Lister toutes les séries détectées (avec leurs UID)
    print("\n🔍 Recherche de TOUTES les séries dans ce dossier (incluant sous-dossiers) :")
    all_series_uids = reader.GetGDCMSeriesIDs(str(folder))
    print(f"   {len(all_series_uids)} SeriesInstanceUID trouvés :")
    for uid in all_series_uids:
        files_for_uid = reader.GetGDCMSeriesFileNames(str(folder), uid)
        print(f"   - {uid} → {len(files_for_uid)} fichiers")
else:
    print(f"   ✓ OK, série détectée avec succès\n")
    print("   Premiers fichiers de la série :")
    for f in series_files[:5]:
        print(f"     {f}")

print("\n" + "=" * 60)
print("Si 0 fichiers détectés malgré des .dcm visibles dans le dossier,")
print("vérifie s'il y a un sous-dossier supplémentaire (ex: DICOM/, IMG/)")
print("et relance ce diagnostic en pointant directement dans ce sous-dossier.")
