"""
Split et inspection de dossiers DICOM mixtes
=============================================
Étape 1 : audit()   → affiche ce qui est dans le dossier (patients, séries, séquences)
Étape 2 : split()   → réorganise les fichiers par patient/série
Structure générée :
    output_root/
    ├── PatientID_001/
    │   ├── Series_T2_narrow/
    │   │   ├── IM-0001.dcm
    │   │   └── ...
    │   └── Series_T2_wide/
    │       └── ...
    ├── PatientID_002/
    │   └── ...
    └── ...
Dépendances :
    pip install pydicom
"""
import os
import shutil
import pydicom
from pathlib import Path
from collections import defaultdict
ROOT_DIR   = Path(r"C:\MRIData\Vida-XT\Répétabilité") 
# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────
#DICOM_DIR   = r"C:\MRIData\Vida-XT\Répétabilité\2026-04-14_VacRecherche_AN_PG"   # dossier à splitter
OUTPUT_DIR  = Path(r"C:\MRIData\Vida-XT\Répétabilité\Splitted_data")       # où écrire le résultat
# ─────────────────────────────────────────────

def read_tag(ds, tag, default="UNKNOWN"):
    """Lire un tag DICOM en toute sécurité."""
    try:
        val = getattr(ds, tag, None)
        return str(val).strip() if val else default
    except Exception:
        return default

def collect_dicom_files(dicom_dir: Path) -> list:
    """Parcourir récursivement et collecter tous les fichiers DICOM."""
    dcm_files = []
    for f in dicom_dir.rglob("*"):
        if f.is_file():
            try:
                ds = pydicom.dcmread(str(f), stop_before_pixels=True)
                dcm_files.append((f, ds))
            except Exception:
                pass  # pas un DICOM valide
    return dcm_files


def audit(dicom_dir):
    """
    ÉTAPE 1 — Inspecter le dossier et afficher un résumé.
    Lancer ceci en premier pour comprendre l'organisation.
    """
    #dicom_dir = Path(DICOM_DIR)
    print(f"🔍 Lecture de {dicom_dir} ...\n")

    files = collect_dicom_files(dicom_dir)
    print(f"   {len(files)} fichiers DICOM trouvés\n")

    # Grouper par PatientID > StudyInstanceUID > SeriesInstanceUID
    tree = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    for f, ds in files:
        patient_id  = read_tag(ds, "PatientID")
        patient_name= read_tag(ds, "PatientName")
        study_uid   = read_tag(ds, "StudyInstanceUID")
        series_uid  = read_tag(ds, "SeriesInstanceUID")
        series_desc = read_tag(ds, "SeriesDescription", "NoDescription")
        sequence    = read_tag(ds, "SequenceName", "")
        n_slices    = read_tag(ds, "ImagesInAcquisition", "?")

        key = f"{patient_id} | {patient_name}"
        tree[key][study_uid][(series_uid, series_desc, sequence)].append(f)

    # Affichage
    print("=" * 65)
    for patient, studies in sorted(tree.items()):
        print(f"\n👤 Patient : {patient}")
        for study_uid, series_dict in studies.items():
            print(f"   📋 Study  : {study_uid[:30]}...")
            for (series_uid, desc, seq), flist in sorted(series_dict.items(),
                                                          key=lambda x: x[0][1]):
                print(f"      🗂  Série : {desc:<35} "
                      f"seq={seq:<15} "
                      f"→ {len(flist):>4} fichiers")
    print("\n" + "=" * 65)
    print("\n→ Si l'audit est correct, lancer split() pour réorganiser les fichiers.")

def split(dicom_dir: Path, output_dir: Path, source_name: str):
    """
    ÉTAPE 2 — Réorganiser les fichiers DICOM par patient et par série.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"🔍 Lecture de {dicom_dir} ...\n")
    files = collect_dicom_files(dicom_dir)
    print(f"   {len(files)} fichiers DICOM trouvés\n")

    # Grouper par PatientID > SeriesInstanceUID
    series_map = defaultdict(list)
    series_meta = {}

    for f, ds in files:
        study_uid   = read_tag(ds, "StudyID", "UnknownStudy")
        series_uid  = read_tag(ds, "SeriesInstanceUID", "UnknownSeries")
        series_desc = read_tag(ds, "SeriesDescription", "NoDesc")

        # Nettoyer les caractères spéciaux pour les noms de dossiers
        series_desc_clean = "".join(
            c if c.isalnum() or c in "-_ " else "_" for c in series_desc
        ).strip().replace(" ", "_")

        key = (study_uid, series_uid)
        series_map[key].append(f)
        series_meta[key] = series_desc_clean

    print(f"   {len(set(k[0] for k in series_map))} patients détectés")
    print(f"   {len(series_map)} séries au total\n")

    # Copier les fichiers
    for idx, ((study_uid, series_uid), file_list) in enumerate(series_map.items()):
        series_desc = series_meta[(study_uid, series_uid)]

        # Dossier destination : output/PatientID/SeriesDescription_uid_court/
        uid_short    = series_uid[-8:]  # 8 derniers caractères pour l'unicité
        series_name  = f"{series_desc}_{uid_short}"

        # prend les 12 derniers caractères du nom du dossier source
        source_last12 = source_name[-12:]

        # prend les 12 derniers caractères du StudyInstanceUID
        study_short = study_uid[-12:]

        # concaténation pour former le nom final du dossier
        source_short = f"{source_last12}_{study_short}"

        dest_dir = output_dir / f"Study_{source_short}" / series_name
        dest_dir.mkdir(parents=True, exist_ok=True)

        for src_file in file_list:
            shutil.copy2(src_file, dest_dir / src_file.name)

        print(f"  [{idx+1}/{len(series_map)}] "
              f"Study {study_short} | {series_desc}"
              f"→ {len(file_list)} fichiers copiés")

    print(f"\n✅ Split terminé → {output_dir}")
    print("\nProchaine étape : renommer les dossiers narrow/wide manuellement")
    print("selon la description de série, puis relancer prepare_nnunet_dataset.py")

# ─────────────────────────────────────────────
#  POINT D'ENTRÉE
# ─────────────────────────────────────────────

# if __name__ == "__main__":
#     print("Que veux-tu faire ?")
#     print("  1 → audit()  : inspecter le dossier (recommandé en premier)")
#     print("  2 → split()  : réorganiser les fichiers")
#     choice = input("\nChoix (1 ou 2) : ").strip()
#     if choice == "1":
#         audit()
#     elif choice == "2":
#         split()
#     else:
#         print("Choix invalide.")
# ─────────────────────────────────────────────
#  BOUCLE SUR TOUS LES SOUS-DOSSIERS
# ─────────────────────────────────────────────
for subfolder in ROOT_DIR.glob("2026*"):
    if subfolder.is_dir():
        split(subfolder, OUTPUT_DIR, subfolder.name)

#     print("Choix invalide.")
print("\n✅ Tous les dossiers ont été traités.")