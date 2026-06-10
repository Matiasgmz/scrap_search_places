import pandas as pd
from pathlib import Path


def load_and_concat_xlsx(path_template: str, start: int = 1, end: int = 60) -> pd.DataFrame:
    """Charge et concatène plusieurs fichiers Excel numérotés de start à end.

    Le modèle de chemin doit contenir '{i}' pour le numéro.
    Exemple: 'fichier_{i}.xlsx'.
    """
    frames = []
    for i in range(start, end + 1):
        path = Path(path_template.format(i=i))
        if path.exists():
            frames.append(pd.read_excel(path))
        else:
            print(f"Fichier introuvable: {path}")

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


if __name__ == "__main__":
    merged = load_and_concat_xlsx("agence_immo_{i:02d}_search_google.xlsx")
    merged.to_excel("fichier_merge.xlsx", index=False)
