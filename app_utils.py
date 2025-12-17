import json
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

ROOT = Path(__file__).parent
LOGO = ROOT / "enedis_logo.png"
GEO = ROOT / "arrondissements.geojson"


def _download(url: str, dest: Path, timeout: int = 15) -> None:
    """Download a file to dest, show a warning on failure."""
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
    except Exception as e:
        st.warning(f"Impossible de télécharger {url} : {e}")
        return
    dest.write_bytes(r.content)


@st.cache_resource(show_spinner=False)
def get_logo_bytes():
    """Return the logo bytes, downloading it if needed."""
    if not LOGO.exists():
        _download(
            "https://upload.wikimedia.org/wikipedia/fr/7/7d/Enedis_logo.svg",
            LOGO,
            timeout=15,
        )
    if LOGO.exists():
        return LOGO.read_bytes()
    return None


@st.cache_resource(show_spinner=False)
def get_geojson():
    """Return the GeoJSON data for Paris arrondissements."""
    if not GEO.exists():
        _download(
            "https://opendata.paris.fr/explore/dataset/arrondissements/download/?format=geojson",
            GEO,
            timeout=30,
        )
    if GEO.exists():
        try:
            return json.loads(GEO.read_text(encoding="utf-8"))
        except Exception as e:
            st.warning(f"Erreur de lecture {GEO}: {e}")
    return None


def build_interventions(df: pd.DataFrame) -> pd.DataFrame:
    """Return a deduplicated view of *df* using the (PRM, date, équipe) rule.

    - PRM is cleaned to remove decimal suffixes.
    - The date is taken from the "Date de réalisation" column and reduced to the
      calendar day.
    - L'équipe corresponds to the couple Agent + CDT.

    If one of the key columns is missing, the original frame is returned.
    """

    if df.empty:
        return df.copy()

    res = df.copy()

    if "PRM" in res.columns:
        res["PRM_clean"] = res["PRM"].apply(lambda x: str(x).split(".")[0] if pd.notna(x) else pd.NA)

    if "Date de réalisation" in res.columns:
        res["Date_intervention"] = pd.to_datetime(res["Date de réalisation"], errors="coerce").dt.date

    agent = res["Agent"].fillna("") if "Agent" in res.columns else pd.Series("", index=res.index)
    cdt = res["CDT"].fillna("") if "CDT" in res.columns else pd.Series("", index=res.index)
    res["Equipe"] = (agent.astype(str) + " / " + cdt.astype(str)).str.strip(" /")

    keys = ["PRM_clean", "Date_intervention", "Equipe"]
    if not set(keys).issubset(res.columns):
        return res

    res = res.dropna(subset=["Date_intervention"]).drop_duplicates(subset=keys)
    return res
