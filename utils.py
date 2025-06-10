import json
from pathlib import Path
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
