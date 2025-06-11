import streamlit as st
import pandas as pd
import plotly.express as px
from utils import get_geojson

ENEDIS_COLORS = ["#2C75FF", "#75C700", "#4A9BFF", "#A0D87C", "#0072F0", "#47B361", "#6EABFF", "#9EE08E"]

st.set_page_config(page_title="Statistiques comparatives", layout="wide")

if "data" not in st.session_state:
    st.warning("Merci de d'abord charger un fichier via la page principale.")
    st.stop()

df = st.session_state["data"]


years = sorted(df["Année"].unique())
months = list(range(1, 13))
days = list(range(1, 32))
techs = sorted(df["Agent"].dropna().unique()) if "Agent" in df.columns else []
agences = sorted(df["Agence"].dropna().unique()) if "Agence" in df.columns else []
prestations = sorted(df["Prestation"].dropna().unique()) if "Prestation" in df.columns else []
uos = sorted(df["Code et libelle Uo"].dropna().unique()) if "Code et libelle Uo" in df.columns else []
statuts = sorted(df["Statut de l'intervention"].dropna().unique()) if "Statut de l'intervention" in df.columns else []
etats = sorted(df["Etat de réalisation"].dropna().unique()) if "Etat de réalisation" in df.columns else []

# Liste par defaut des techniciens a comparer
default_agents = ["CICIO Florin","DJABELKHIR Mohammed","MAILLARD Yoann","RONCERAY Florian","PEINADO BENITO Augustin","DANSOKO Toumany","GRANDEMANGE Gary","PAYET Vincent","VAUSSOUE Jean-françois","MARC Radjoucoumar","KONE Gaoussou","TRINH Quang","ABRANTES FELIZARDO Artur","KESSI Farid","TRARI Nasr eddine","CASTELLI Stéfano","DIANIFABA Ibrahima","AHAMADA Nazir","BOUJATLA Samir","MUZAMA NDANGU Landry","BROUILLARD Geoffroy","DJABRI Gabrielle","EXILUS Marc","KONGA Chris","SANTAT Eric","LAPITRE Jean-philippe","LARNICOL Lucas","DJABELKHIR Mohamed","DAAOU Yassine","DALAOUI Jeber","LOUBAKI CYS Francel","VACQUER Andre"]
default_agents_in_data = [a for a in default_agents if a in techs] or techs

with st.sidebar.form("filtres_comp"):
    tech = st.selectbox("Technicien", techs)
    comp_list = st.multiselect("Technicien à comparer", techs, default=default_agents_in_data)
    y = st.multiselect("Années", years, years)
    m = st.multiselect("Mois", months, months, format_func=lambda x: f"{x:02d}")
    d = st.multiselect("Jours", days, days, format_func=lambda x: f"{x:02d}")
    agc_sel = st.multiselect("Agence", agences, agences)
    pr = st.multiselect("Prestation", prestations, prestations)
    uo_sel = st.multiselect("UO", uos, uos)
    st_sel = st.multiselect("Statut", statuts, statuts)
    et_sel = st.multiselect("État", etats, etats)
    ok = st.form_submit_button("Appliquer")

if not ok:
    st.stop()

flt = df[
    df["Année"].isin(y)
    & df["Mois"].isin(m)
    & df["Jour"].isin(d)
    & df["Agent"].eq(tech)
]
if prestations:
    flt = flt[flt["Prestation"].isin(pr)]
if uos:
    flt = flt[flt["Code et libelle Uo"].isin(uo_sel)]
if statuts:
    flt = flt[flt["Statut de l'intervention"].isin(st_sel)]
if etats:
    flt = flt[flt["Etat de réalisation"].isin(et_sel)]
if agences:
    flt = flt[flt["Agence"].isin(agc_sel)]

comp = df[
    df["Année"].isin(y)
    & df["Mois"].isin(m)
    & df["Jour"].isin(d)
    & df["Agent"].isin(comp_list)
]
if prestations:
    comp = comp[comp["Prestation"].isin(pr)]
if uos:
    comp = comp[comp["Code et libelle Uo"].isin(uo_sel)]
if statuts:
    comp = comp[comp["Statut de l'intervention"].isin(st_sel)]
if etats:
    comp = comp[comp["Etat de réalisation"].isin(et_sel)]
if agences:
    comp = comp[comp["Agence"].isin(agc_sel)]

if flt.empty or comp.empty:
    st.warning("Aucune donnée pour ce technicien ou la comparaison.")
    st.stop()

st.title(f"Statistiques comparatives – {tech}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Interventions technicien", len(flt))
n_comp_agents = comp["Agent"].nunique() or 1
c2.metric(
    "Interventions comparées (moyenne)",
    f"{len(comp) / n_comp_agents:.1f}"
)
if "Temps réalisé" in flt.columns:
    c3.metric("Durée moyenne tech", f"{flt['Temps réalisé'].mean():.1f}")
    c4.metric("Durée moyenne comp", f"{comp['Temps réalisé'].mean():.1f}")

# Fonctions utilitaires

def _comp_counts(d1: pd.DataFrame, d2: pd.DataFrame, col: str, n: int | None = None, sort: bool = False) -> pd.DataFrame:
    vc1 = d1[col].value_counts()
    n_agents = d2["Agent"].nunique() if "Agent" in d2.columns else 1
    vc2 = d2[col].value_counts() / n_agents
    tot = (vc1 + vc2)
    if sort:
        tot = tot.sort_index()
    else:
        tot = tot.sort_values(ascending=False)
    if n is not None:
        tot = tot.head(n)
    idx = tot.index
    return pd.DataFrame({
        col: idx,
        "Technicien": vc1.reindex(idx, fill_value=0).values,
        "Comparaison": vc2.reindex(idx, fill_value=0).values,
    })

# Volume annuel comparé
va = _comp_counts(flt, comp, "Année", sort=True)
fig = px.bar(va, x="Année", y=["Technicien", "Comparaison"], barmode="group", color_discrete_sequence=ENEDIS_COLORS[:2], title="Volume annuel comparé")
st.plotly_chart(fig, use_container_width=True)

# Volume mensuel comparé (reprend l'ancien graphique)
if {"Agent"}.issubset(df.columns):
    grp = comp.groupby(["Année", "Mois", "Mois_nom", "Agent"]).size().reset_index(name="Interventions")
    months_df = grp[["Année", "Mois", "Mois_nom"]].drop_duplicates()
    tech_df = grp[grp["Agent"] == tech][["Année", "Mois", "Mois_nom", "Interventions"]].rename(columns={"Interventions": "tech"})
    merged = months_df.merge(tech_df, on=["Année", "Mois", "Mois_nom"], how="left")
    idx = grp.groupby(["Année", "Mois", "Mois_nom"])["Interventions"].idxmax()
    max_df = grp.loc[idx, ["Année", "Mois", "Mois_nom", "Agent", "Interventions"]].rename(columns={"Interventions": "max", "Agent": "agent_max"})
    merged = merged.merge(max_df, on=["Année", "Mois", "Mois_nom"], how="left")
    nz = grp[grp["Interventions"] > 0]
    idx = nz.groupby(["Année", "Mois", "Mois_nom"])["Interventions"].idxmin()
    min_df = nz.loc[idx, ["Année", "Mois", "Mois_nom", "Agent", "Interventions"]].rename(columns={"Interventions": "min", "Agent": "agent_min"})
    merged = merged.merge(min_df, on=["Année", "Mois", "Mois_nom"], how="left")
    mean_df = grp.groupby(["Année", "Mois", "Mois_nom"])["Interventions"].mean().reset_index(name="moyenne")
    merged = merged.merge(mean_df, on=["Année", "Mois", "Mois_nom"], how="left")
    merged["Date"] = pd.to_datetime(dict(year=merged["Année"], month=merged["Mois"], day=1))
    for col in ["tech", "max", "min", "moyenne", "agent_max", "agent_min"]:
        if col not in merged.columns:
            merged[col] = pd.NA
    lines = []
    for metric in ["tech", "max", "min", "moyenne"]:
        tmp = merged[["Date", metric]].copy()
        tmp["Metric"] = metric
        if metric == "tech":
            tmp["Agent"] = tech
        elif metric == "max":
            tmp["Agent"] = merged["agent_max"]
        elif metric == "min":
            tmp["Agent"] = merged["agent_min"]
        else:
            tmp["Agent"] = ""
        tmp = tmp.rename(columns={metric: "Interventions"})
        lines.append(tmp)
    lines = pd.concat(lines, ignore_index=True)
    fig2 = px.line(lines, x="Date", y="Interventions", color="Metric", markers=True, color_discrete_sequence=ENEDIS_COLORS[:4], title="Volume mensuel comparé", hover_data={"Agent": True})
    fig2.update_traces(hovertemplate="%{x|%Y-%m}<br>%{customdata[0]}<br>%{y} interventions")
    st.plotly_chart(fig2, use_container_width=True)

# Graphiques comparatifs supplementaires
bar_cols = [
    ("Prestation", "Répartition prestations"),
    ("Statut de l'intervention", "Répartition des statuts"),
    ("Etat de réalisation", "Répartition des états"),
    ("Motif de non réalisation", "Top 10 motifs de non réalisation"),
    ("Libelle du BI", "Top 10 Libellé BI"),
    ("Code et libelle Uo", "Top 10 UO"),
    ("Origine", "Répartition par Origine"),
]

for col, title in bar_cols:
    if col in flt.columns:
        t = _comp_counts(flt, comp, col, n=10)
        fig = px.bar(t, x=col, y=["Technicien", "Comparaison"], barmode="group", color_discrete_sequence=ENEDIS_COLORS[:2], title=title)
        st.plotly_chart(fig, use_container_width=True)

if {"Temps théorique", "Temps réalisé", "Prestation"}.issubset(flt.columns):
    tech_temps = flt.groupby("Prestation")[["Temps théorique", "Temps réalisé"]].mean().reset_index()
    comp_temps = comp.groupby("Prestation")[["Temps théorique", "Temps réalisé"]].mean().reset_index()
    tmp = pd.merge(tech_temps, comp_temps, on="Prestation", how="outer", suffixes=("_tech", "_comp")).fillna(0)
    fig = px.bar(tmp, x="Prestation", y=["Temps théorique_tech", "Temps théorique_comp", "Temps réalisé_tech", "Temps réalisé_comp"], barmode="group", color_discrete_sequence=ENEDIS_COLORS[:4], title="Temps théorique vs réalisé (comparé)")
    st.plotly_chart(fig, use_container_width=True)

gj = get_geojson()
if "Arr" in flt.columns and gj:
    arr_t = flt["Arr"].value_counts().rename_axis("Arr").reset_index(name="tech")
    arr_c = comp["Arr"].value_counts().rename_axis("Arr").reset_index(name="comp")
    arr = pd.merge(arr_t, arr_c, on="Arr", how="outer").fillna(0)
    arr["pct_tech"] = arr["tech"] / arr["tech"].sum() * 100
    arr["pct_comp"] = arr["comp"] / arr["comp"].sum() * 100
    col_t, col_c = st.columns(2)
    fig = px.choropleth(
        arr,
        geojson=gj,
        locations="Arr",
        color="pct_tech",
        color_continuous_scale=[[0, "#E6F0FF"], [1, "#2C75FF"]],
        featureidkey="properties.c_ar",
        hover_data={"pct_tech": ":.1f", "pct_comp": ":.1f"},
        center={"lat": 48.8566, "lon": 2.3522},
        title="Interventions par arrondissement – technicien",
    )
    fig.update_geos(fitbounds="locations", visible=False)
    col_t.plotly_chart(fig, use_container_width=True)

    fig_c = px.choropleth(
        arr,
        geojson=gj,
        locations="Arr",
        color="pct_comp",
        color_continuous_scale=[[0, "#E6F0FF"], [1, "#75C700"]],
        featureidkey="properties.c_ar",
        hover_data={"pct_tech": ":.1f", "pct_comp": ":.1f"},
        center={"lat": 48.8566, "lon": 2.3522},
        title="Interventions par arrondissement – comparaison",
    )
    fig_c.update_geos(fitbounds="locations", visible=False)
    col_c.plotly_chart(fig_c, use_container_width=True)

st.dataframe(flt)
