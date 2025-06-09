import streamlit as st, pandas as pd, numpy as np, plotly.express as px
import json
from pathlib import Path

ENEDIS_COLORS = ["#2C75FF", "#75C700", "#4A9BFF", "#A0D87C", "#0072F0", "#47B361", "#6EABFF", "#9EE08E"]

st.set_page_config(page_title="Détail par technicien", layout="wide")

if "data" not in st.session_state:
    st.warning("Merci de d'abord charger un fichier via la page principale.")
    st.stop()

df = st.session_state["data"]

years = sorted(df["Année"].unique())
months = list(range(1, 13))
days = list(range(1, 32))
agences = sorted(df["Agence"].dropna().unique()) if "Agence" in df.columns else []
prestations = sorted(df["Prestation"].dropna().unique()) if "Prestation" in df.columns else []
uos = sorted(df["Code et libelle Uo"].dropna().unique()) if "Code et libelle Uo" in df.columns else []
statuts = sorted(df["Statut de l'intervention"].dropna().unique()) if "Statut de l'intervention" in df.columns else []
etats = sorted(df["Etat de réalisation"].dropna().unique()) if "Etat de réalisation" in df.columns else []
techs = sorted(df["Agent"].dropna().unique()) if "Agent" in df.columns else []

with st.sidebar.form("filtres_detail"):
    tech = st.selectbox("Technicien", techs)
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

if flt.empty:
    st.warning("Aucune donnée pour ce technicien.")
    st.stop()

st.title(f"Statistiques détaillées – {tech}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Interventions", len(flt))

if "Temps réalisé" in flt.columns:
    pos = flt["Temps réalisé"][flt["Temps réalisé"] > 0]
    c2.metric("Durée moy", f"{pos.mean():.1f}")
    c3.metric("Durée max", f"{pos.max():.1f}")
    c4.metric("Durée min", f"{pos.min():.1f}")

if "Année" in flt.columns:
    va = flt["Année"].value_counts().sort_index().reset_index()
    va.columns = ["Année", "Interventions"]
    fig = px.bar(
        va,
        x="Année",
        y="Interventions",
        color="Année",
        color_discrete_sequence=ENEDIS_COLORS,
        title="Volume annuel",
    )
    fig.update_traces(text=va["Interventions"], textposition="outside",
                      hovertemplate="Année %{x}<br>%{y} interventions")
    st.plotly_chart(fig, use_container_width=True)

if {"Année", "Mois_nom"}.issubset(flt.columns):
    vm = flt.groupby(["Année", "Mois_nom"]).size().reset_index(name="Interventions")
    fig = px.bar(
        vm,
        x="Mois_nom",
        y="Interventions",
        color="Année",
        color_discrete_sequence=ENEDIS_COLORS,
        barmode="group",
        title="Volume mensuel",
    )
    st.plotly_chart(fig, use_container_width=True)

if "Prestation" in flt.columns:
    t = flt["Prestation"].value_counts().rename_axis("Prestation").reset_index(name="Interventions")
    t["%"] = (t["Interventions"] / t["Interventions"].sum() * 100).round(1)
    fig = px.pie(
        t,
        names="Prestation",
        values="Interventions",
        hover_data=["%"],
        title="Répartition prestations",
        color_discrete_sequence=ENEDIS_COLORS
    )
    fig.update_traces(textinfo="percent+label", hovertemplate="%{label}<br>Interventions : %{value}<br>% : %{customdata[0]}")
    st.plotly_chart(fig, use_container_width=True)

if "Statut de l'intervention" in flt.columns:
    statut_counts = flt["Statut de l'intervention"].value_counts().rename_axis("Statut").reset_index(name="Interventions")
    total = statut_counts["Interventions"].sum()
    statut_counts["%"] = (statut_counts["Interventions"] / total * 100).round(1)

    fig = px.bar(
        statut_counts,
        x="Statut",
        y="Interventions",
        title="Répartition des statuts d'intervention",
        color_discrete_sequence=ENEDIS_COLORS,
        hover_data={"%": True, "Interventions": True}
    )
    fig.update_traces(hovertemplate="%{x}<br>Interventions : %{y}<br>% : %{customdata[0]}%")
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

if "Etat de réalisation" in flt.columns:
    et_counts = flt["Etat de réalisation"].value_counts().rename_axis("Etat").reset_index(name="Interventions")
    et_counts["%"] = (et_counts["Interventions"] / et_counts["Interventions"].sum() * 100).round(1)
    fig = px.bar(
        et_counts,
        x="Etat",
        y="Interventions",
        title="Répartition des états de réalisation",
        color_discrete_sequence=ENEDIS_COLORS,
        hover_data={"%": True, "Interventions": True},
    )
    fig.update_traces(hovertemplate="%{x}<br>Interventions : %{y}<br>% : %{customdata[0]}%")
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)


if "Motif de non réalisation" in flt.columns:
    top_motifs = (
        flt["Motif de non réalisation"]
        .value_counts()
        .nlargest(10)
        .rename_axis("Motif")
        .reset_index(name="Interventions")
    )
    total = top_motifs["Interventions"].sum()
    top_motifs["%"] = (top_motifs["Interventions"] / total * 100).round(1)

    fig = px.bar(
        top_motifs,
        x="Motif",
        y="Interventions",
        title="Top 10 motifs de non réalisation",
        color_discrete_sequence=ENEDIS_COLORS,
        hover_data={"%": True, "Interventions": True}
    )
    fig.update_traces(hovertemplate="%{x}<br>Interventions : %{y}<br>% : %{customdata[0]}%")
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

if "Libelle du BI" in flt.columns:
    t = flt["Libelle du BI"].value_counts().nlargest(10).reset_index()
    t.columns = ["Libellé", "Interventions"]
    t["%"] = (t["Interventions"] / t["Interventions"].sum() * 100).round(1)
    fig = px.bar(
        t,
        x="Libellé",
        y="Interventions",
        text="%",
        color="Libellé",
        color_discrete_sequence=ENEDIS_COLORS,
        title="Top 10 Libellé BI",
    )
    fig.update_traces(hovertemplate="%{x}<br>%{text}%")
    st.plotly_chart(fig, use_container_width=True)

if "PRM" in flt.columns:
    flt["PRM_clean"] = flt["PRM"].dropna().apply(lambda x: str(x).split('.')[0])
    top_prm = flt["PRM_clean"].value_counts().nlargest(10).reset_index()
    top_prm.columns = ["PRM", "Interventions"]
    top_prm["Rang"] = [f"{i+1}ᵉ" for i in range(len(top_prm))]
    fig = px.bar(
        top_prm,
        x="Rang",
        y="Interventions",
        color="PRM",
        color_discrete_sequence=ENEDIS_COLORS,
        text="Interventions",
        title="Top 10 PRM (classés)",
    )
    fig.update_traces(textposition="outside",
                      hovertemplate="Rang %{x}<br>%{y} interventions<br>PRM %{customdata}")
    fig.update_layout(xaxis_title="Rang", yaxis_title="Nombre d’interventions")
    st.plotly_chart(fig, use_container_width=True)

if "Origine" in flt.columns:
    t = flt["Origine"].value_counts().reset_index()
    t.columns = ["Origine", "Interventions"]
    t["%"] = (t["Interventions"] / t["Interventions"].sum() * 100).round(1)
    fig = px.bar(
        t,
        x="Origine",
        y="Interventions",
        text="%",
        color="Origine",
        color_discrete_sequence=ENEDIS_COLORS,
        title="Répartition par Origine",
    )
    fig.update_traces(hovertemplate="%{x}<br>%{text}%")
    st.plotly_chart(fig, use_container_width=True)

if "Date de programmation" in flt.columns:
    try:
        flt["Date de programmation"] = pd.to_datetime(flt["Date de programmation"], errors='coerce')
        t = flt["Date de programmation"].dt.date.value_counts().sort_index().reset_index()
        t.columns = ["Date", "Interventions"]
        fig = px.bar(
            t,
            x="Date",
            y="Interventions",
            color_discrete_sequence=ENEDIS_COLORS,
            title="Volume des programmations par jour",
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        pass

if {"Temps théorique", "Temps réalisé", "Prestation"}.issubset(flt.columns):
    t = flt.groupby("Prestation")[["Temps théorique", "Temps réalisé"]].mean().reset_index()
    fig = px.bar(
        t,
        x="Prestation",
        y=["Temps théorique", "Temps réalisé"],
        color_discrete_sequence=ENEDIS_COLORS[:2],
        barmode="group",
        title="Temps théorique vs réalisé par prestation",
    )
    st.plotly_chart(fig, use_container_width=True)

if "CDT" in flt.columns:
    cdt_counts = flt["CDT"].value_counts().rename_axis("Agent CDT").reset_index(name="Interventions")
    fig = px.bar(
        cdt_counts,
        x="Agent CDT",
        y="Interventions",
        title="Interventions par agent CDT",
        color_discrete_sequence=ENEDIS_COLORS,
    )
    st.plotly_chart(fig, use_container_width=True)




geo = Path("arrondissements.geojson")

if "Arr" in flt.columns and geo.exists():
    arr = flt["Arr"].value_counts().rename_axis("Arr").reset_index(name="n")
    arr["Arr"] = arr["Arr"].astype(int) 
    arr["pct"] = arr["n"] / arr["n"].sum() * 100

    gj = json.loads(geo.read_text(encoding="utf-8"))

    fig = px.choropleth(
        arr,
        geojson=gj,
        locations="Arr",
        color="pct",
        color_continuous_scale=[[0, "#E6F0FF"], [1, "#2C75FF"]],
        featureidkey="properties.c_ar",  
        hover_data={"pct": ":.1f"},
        center={"lat": 48.8566, "lon": 2.3522},
        title="Interventions par arrondissement (%)"
    )

    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_traces(hovertemplate="Arr %{location}<br>%{customdata[0]}%")
    st.plotly_chart(fig, use_container_width=True)


if "Code et libelle Uo" in flt.columns:
    fig = px.bar(
        flt["Code et libelle Uo"].value_counts().nlargest(10).rename_axis("UO").reset_index(name="Interventions"),
        x="UO",
        y="Interventions",
        title="Top 10 UO",
        color_discrete_sequence=ENEDIS_COLORS
    )
    st.plotly_chart(fig, use_container_width=True)

st.dataframe(flt)
