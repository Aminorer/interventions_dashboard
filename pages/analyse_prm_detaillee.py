import pandas as pd
import plotly.express as px
import streamlit as st

from app_utils import build_interventions, get_geojson

ENEDIS_COLORS = ["#2C75FF", "#75C700", "#4A9BFF", "#A0D87C", "#0072F0", "#47B361", "#6EABFF", "#9EE08E"]

st.set_page_config(page_title="Analyse détaillée PRM", layout="wide")

if "data" not in st.session_state:
    st.warning("Merci de d'abord charger un fichier via la page principale.")
    st.stop()


def _params(*args):
    """Return arguments as a tuple for caching."""

    return tuple(args)


@st.cache_data(show_spinner=False)
def _available_prm(interventions: pd.DataFrame) -> list[str]:
    """Return sorted unique PRM identifiers."""

    return sorted(interventions["PRM_clean"].dropna().unique())


@st.cache_data(show_spinner=False)
def _filter_prm(
    interventions: pd.DataFrame, prm: str, date_start, date_end, params: tuple
) -> pd.DataFrame:
    """Filter interventions for a PRM and date range."""

    flt = interventions[interventions["PRM_clean"].eq(prm)].copy()
    if "Date_intervention" in flt.columns:
        flt["Date_intervention"] = pd.to_datetime(flt["Date_intervention"])
        flt = flt[
            (flt["Date_intervention"] >= pd.to_datetime(date_start))
            & (flt["Date_intervention"] <= pd.to_datetime(date_end))
        ]
    return flt


@st.cache_data(show_spinner=False)
def _daily_volume(flt: pd.DataFrame, params: tuple) -> pd.DataFrame:
    """Return number of interventions per day."""

    vol = (
        flt.groupby(flt["Date_intervention"].dt.date)
        .size()
        .rename_axis("Date")
        .reset_index(name="Interventions")
    )
    vol["Date"] = pd.to_datetime(vol["Date"])
    return vol


@st.cache_data(show_spinner=False)
def _duration_stats(flt: pd.DataFrame, params: tuple) -> pd.DataFrame:
    """Return per-intervention durations for visualization."""

    cols = []
    if "Temps réalisé" in flt.columns:
        cols.append("Temps réalisé")
    if "Temps théorique" in flt.columns:
        cols.append("Temps théorique")
    if not cols:
        return pd.DataFrame()

    dur = flt[["Date_intervention", "Equipe", *cols]].copy()
    dur = dur.melt(
        id_vars=["Date_intervention", "Equipe"],
        value_vars=cols,
        var_name="Type",
        value_name="Durée (min)",
    )
    dur = dur.dropna(subset=["Durée (min)"])
    dur["Date_intervention"] = pd.to_datetime(dur["Date_intervention"])
    return dur


@st.cache_data(show_spinner=False)
def _arr_stats(flt: pd.DataFrame, params: tuple) -> pd.DataFrame:
    """Return interventions count by arrondissement with percentages."""

    if "Arr" not in flt.columns:
        return pd.DataFrame()

    arr = flt["Arr"].dropna().astype(int).value_counts().rename_axis("Arr").reset_index(name="n")
    arr["pct"] = arr["n"] / arr["n"].sum() * 100
    return arr


df = st.session_state["data"]
interventions = build_interventions(df)

if "PRM_clean" not in interventions.columns:
    st.warning("La colonne PRM est manquante ou invalide dans les données chargées.")
    st.stop()

prm_options = _available_prm(interventions)
if not prm_options:
    st.warning("Aucun PRM disponible dans les données filtrées.")
    st.stop()

min_date = pd.to_datetime(interventions["Date_intervention"].min())
max_date = pd.to_datetime(interventions["Date_intervention"].max())

with st.sidebar.form("prm_filters"):
    prm = st.selectbox("PRM", prm_options)
    date_range = st.date_input(
        "Période d'analyse",
        value=(min_date, max_date),
        min_value=min_date.to_pydatetime().date(),
        max_value=max_date.to_pydatetime().date(),
    )
    ok = st.form_submit_button("Analyser")

if not ok:
    st.stop()

if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_date, end_date = date_range
else:  # fallback when a single date is returned
    start_date = end_date = date_range

flt = _filter_prm(
    interventions,
    prm,
    start_date,
    end_date,
    _params(prm, start_date, end_date),
)

if flt.empty:
    st.warning("Aucune intervention pour ce PRM sur la période sélectionnée.")
    st.stop()

st.title(f"Analyse détaillée du PRM {prm}")

agents = flt["Agent"].dropna().unique() if "Agent" in flt.columns else []
cdts = flt["CDT"].dropna().unique() if "CDT" in flt.columns else []

c1, c2, c3, c4 = st.columns(4)
c1.metric("Interventions (dédupliquées)", f"{len(flt):,}".replace(",", " "))
c2.metric("Équipes mobilisées", flt["Equipe"].nunique())
c3.metric("Techniciens uniques", len(agents))
if "Temps réalisé" in flt.columns:
    c4.metric("Durée moyenne réalisée", f"{flt['Temps réalisé'].mean():.1f} min")
else:
    c4.metric("Durée moyenne réalisée", "N/A")

with st.expander("Intervenants"):
    st.write(
        "**Techniciens :** "
        + (", ".join(sorted(agents)) if len(agents) else "Non renseigné")
    )
    st.write(
        "**CDT :** " + (", ".join(sorted(cdts)) if len(cdts) else "Non renseigné")
    )

# Graphique 1 : chronologie des interventions
volume_jour = _daily_volume(
    flt,
    _params(prm, start_date, end_date),
)
fig_volume = px.bar(
    volume_jour,
    x="Date",
    y="Interventions",
    title="Chronologie des interventions",
    color_discrete_sequence=ENEDIS_COLORS,
)
fig_volume.update_traces(hovertemplate="%{x|%d/%m/%Y}<br>%{y} interventions")
st.plotly_chart(fig_volume, use_container_width=True)

# Graphique 2 : répartition par équipe
team_counts = (
    flt["Equipe"].value_counts().rename_axis("Equipe").reset_index(name="Interventions")
)
fig_team = px.bar(
    team_counts,
    x="Interventions",
    y="Equipe",
    orientation="h",
    color="Equipe",
    title="Poids des équipes mobilisées",
    color_discrete_sequence=ENEDIS_COLORS,
)
fig_team.update_layout(yaxis_categoryorder="total ascending")
st.plotly_chart(fig_team, use_container_width=True)

# Graphique 3 : temps réalisé vs théorique
if {"Temps réalisé", "Temps théorique"}.issubset(flt.columns):
    temps_cmp = flt[["Temps réalisé", "Temps théorique"]].describe()[1:]
    temps_cmp = temps_cmp.reset_index().rename(columns={"index": "Statistique"})
    temps_cmp = temps_cmp.melt("Statistique", var_name="Type", value_name="Minutes")
    fig_temps = px.bar(
        temps_cmp,
        x="Statistique",
        y="Minutes",
        color="Type",
        barmode="group",
        title="Durées réalisées vs théoriques (statistiques descriptives)",
        color_discrete_sequence=ENEDIS_COLORS[:2],
    )
    st.plotly_chart(fig_temps, use_container_width=True)
else:
    st.info("Durées théoriques/réalisées indisponibles pour ce PRM.")

# Graphique 4 : cartographie ou répartition géographique
arr = _arr_stats(
    flt,
    _params(prm, start_date, end_date),
)
geojson = get_geojson()
if not arr.empty and geojson:
    fig_map = px.choropleth(
        arr,
        geojson=geojson,
        locations="Arr",
        color="pct",
        featureidkey="properties.c_ar",
        color_continuous_scale=[[0, "#E6F0FF"], [1, "#2C75FF"]],
        hover_data={"n": True, "pct": ":.1f"},
        center={"lat": 48.8566, "lon": 2.3522},
        title="Répartition géographique des interventions",
    )
    fig_map.update_geos(fitbounds="locations", visible=False)
    fig_map.update_traces(hovertemplate="Arr %{location}<br>%{customdata[0]} interventions<br>%{customdata[1]:.1f}%")
    st.plotly_chart(fig_map, use_container_width=True)
else:
    st.info("Aucun arrondissement disponible pour cartographier ce PRM.")

# Graphique 5 : trajectoire des durées par intervention
per_intervention = _duration_stats(
    flt,
    _params(prm, start_date, end_date),
)
if not per_intervention.empty:
    fig_durations = px.scatter(
        per_intervention,
        x="Date_intervention",
        y="Durée (min)",
        color="Type",
        symbol="Equipe",
        custom_data=["Equipe"],
        title="Évolution des durées par intervention",
        color_discrete_sequence=ENEDIS_COLORS[:2],
    )
    fig_durations.update_traces(
        hovertemplate="%{x|%d/%m/%Y}<br>%{y:.1f} min<br>%{customdata[0]}"
    )
    st.plotly_chart(fig_durations, use_container_width=True)
else:
    st.info("Durées d'intervention non disponibles pour ce PRM.")

st.subheader("Données filtrées")
st.dataframe(flt)
