import streamlit as st, pandas as pd, numpy as np, plotly.express as px
from utils import get_geojson


def _params(*args):
    """Return arguments as a tuple for caching."""
    return tuple(args)


@st.cache_data(show_spinner=False)
def _value_counts(flt: pd.DataFrame, column: str, params: tuple, n: int | None = None, sort: bool = False) -> pd.DataFrame:
    """Return value counts for *column* with optional top-n filtering."""
    vc = flt[column].value_counts()
    if sort:
        vc = vc.sort_index()
    if n is not None:
        vc = vc.nlargest(n)
    return vc.rename_axis(column).reset_index(name="Interventions")


@st.cache_data(show_spinner=False)
def _monthly_counts(flt: pd.DataFrame, params: tuple) -> pd.DataFrame:
    """Return counts by year and month."""
    return flt.groupby(["Année", "Mois_nom"]).size().reset_index(name="Interventions")


@st.cache_data(show_spinner=False)
def _date_prog_counts(flt: pd.DataFrame, params: tuple) -> pd.DataFrame:
    """Return volume of programmations per day."""
    dt = pd.to_datetime(flt["Date de programmation"], errors="coerce")
    t = dt.dt.date.value_counts().sort_index().reset_index()
    t.columns = ["Date", "Interventions"]
    return t


@st.cache_data(show_spinner=False)
def _temps_moyens(flt: pd.DataFrame, params: tuple) -> pd.DataFrame:
    """Return mean theoretical and realised times by prestation."""
    return flt.groupby("Prestation")[["Temps théorique", "Temps réalisé"]].mean().reset_index()


@st.cache_data(show_spinner=False)
def _arr_counts(flt: pd.DataFrame, params: tuple) -> pd.DataFrame:
    """Return interventions count by arrondissement with percentages."""
    arr = flt["Arr"].value_counts().rename_axis("Arr").reset_index(name="n")
    arr["Arr"] = arr["Arr"].astype(int)
    arr["pct"] = arr["n"] / arr["n"].sum() * 100
    return arr


@st.cache_data(show_spinner=False)
def _top_prm(flt: pd.DataFrame, params: tuple) -> pd.DataFrame:
    """Return top 10 PRM after cleaning the column."""
    prm = flt["PRM"].dropna().apply(lambda x: str(x).split(".")[0])
    top = prm.value_counts().nlargest(10).reset_index()
    top.columns = ["PRM", "Interventions"]
    top["Rang"] = [f"{i+1}ᵉ" for i in range(len(top))]
    return top


@st.cache_data(show_spinner=False)
def _uo_top(flt: pd.DataFrame, params: tuple) -> pd.DataFrame:
    """Return top 10 UO counts."""
    return (
        flt["Code et libelle Uo"]
        .value_counts()
        .nlargest(10)
        .rename_axis("UO")
        .reset_index(name="Interventions")
    )


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
    va = _value_counts(
        flt,
        "Année",
        _params(tech, y, m, d, agc_sel, pr, uo_sel, st_sel, et_sel),
        sort=True,
    )
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
    vm = _monthly_counts(
        flt,
        _params(tech, y, m, d, agc_sel, pr, uo_sel, st_sel, et_sel),
    )
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

    if {"Agent"}.issubset(df.columns):
        all_flt = df[
            df["Année"].isin(y)
            & df["Mois"].isin(m)
            & df["Jour"].isin(d)
        ]
        if prestations:
            all_flt = all_flt[all_flt["Prestation"].isin(pr)]
        if uos:
            all_flt = all_flt[all_flt["Code et libelle Uo"].isin(uo_sel)]
        if statuts:
            all_flt = all_flt[all_flt["Statut de l'intervention"].isin(st_sel)]
        if etats:
            all_flt = all_flt[all_flt["Etat de réalisation"].isin(et_sel)]
        if agences:
            all_flt = all_flt[all_flt["Agence"].isin(agc_sel)]

        grp = (
            all_flt.groupby(["Année", "Mois", "Mois_nom", "Agent"])
            .size()
            .reset_index(name="Interventions")
        )

        months_df = grp[["Année", "Mois", "Mois_nom"]].drop_duplicates()
        tech_df = (
            grp[grp["Agent"] == tech]
            [["Année", "Mois", "Mois_nom", "Interventions"]]
            .rename(columns={"Interventions": "tech"})
        )
        merged = months_df.merge(tech_df, on=["Année", "Mois", "Mois_nom"], how="left")

        idx = grp.groupby(["Année", "Mois", "Mois_nom"])["Interventions"].idxmax()
        max_df = grp.loc[idx, ["Année", "Mois", "Mois_nom", "Agent", "Interventions"]]
        max_df = max_df.rename(columns={"Interventions": "max", "Agent": "agent_max"})
        merged = merged.merge(max_df, on=["Année", "Mois", "Mois_nom"], how="left")

        nz = grp[grp["Interventions"] > 0]
        idx = nz.groupby(["Année", "Mois", "Mois_nom"])["Interventions"].idxmin()
        min_df = nz.loc[idx, ["Année", "Mois", "Mois_nom", "Agent", "Interventions"]]
        min_df = min_df.rename(columns={"Interventions": "min", "Agent": "agent_min"})
        merged = merged.merge(min_df, on=["Année", "Mois", "Mois_nom"], how="left")

        mean_df = grp.groupby(["Année", "Mois", "Mois_nom"])["Interventions"].mean().reset_index(name="mean")
        merged = merged.merge(mean_df, on=["Année", "Mois", "Mois_nom"], how="left")

        merged["Date"] = pd.to_datetime(dict(year=merged["Année"], month=merged["Mois"], day=1))

        # Ensure all metric columns exist to avoid KeyError when they are missing
        for col in ["tech", "max", "min", "mean", "agent_max", "agent_min"]:
            if col not in merged.columns:
                merged[col] = pd.NA

        lines = []
        for metric in ["tech", "max", "min", "mean"]:
            tmp = merged[["Date"]].copy()
            if metric in merged.columns:
                tmp[metric] = merged[metric]
            else:
                tmp[metric] = pd.NA
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

        fig2 = px.line(
            lines,
            x="Date",
            y="Interventions",
            color="Metric",
            markers=True,
            color_discrete_sequence=ENEDIS_COLORS[:4],
            title="Volume mensuel comparé",
            hover_data={"Agent": True},
        )
        fig2.update_traces(
            hovertemplate="%{x|%Y-%m}<br>%{customdata[0]}<br>%{y} interventions"
        )
        st.plotly_chart(fig2, use_container_width=True)

if "Prestation" in flt.columns:
    t = _value_counts(
        flt,
        "Prestation",
        _params(tech, y, m, d, agc_sel, pr, uo_sel, st_sel, et_sel),
    )
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
    statut_counts = _value_counts(
        flt,
        "Statut de l'intervention",
        _params(tech, y, m, d, agc_sel, pr, uo_sel, st_sel, et_sel),
    )
    total = statut_counts["Interventions"].sum()
    statut_counts["%"] = (statut_counts["Interventions"] / total * 100).round(1)

    fig = px.bar(
        statut_counts,
        x="Statut de l'intervention",
        y="Interventions",
        title="Répartition des statuts d'intervention",
        color_discrete_sequence=ENEDIS_COLORS,
        hover_data={"%": True, "Interventions": True}
    )
    fig.update_traces(hovertemplate="%{x}<br>Interventions : %{y}<br>% : %{customdata[0]}%")
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

if "Etat de réalisation" in flt.columns:
    et_counts = _value_counts(
        flt,
        "Etat de réalisation",
        _params(tech, y, m, d, agc_sel, pr, uo_sel, st_sel, et_sel),
    )
    et_counts["%"] = (et_counts["Interventions"] / et_counts["Interventions"].sum() * 100).round(1)
    fig = px.bar(
        et_counts,
        x="Etat de réalisation",
        y="Interventions",
        title="Répartition des états de réalisation",
        color_discrete_sequence=ENEDIS_COLORS,
        hover_data={"%": True, "Interventions": True},
    )
    fig.update_traces(hovertemplate="%{x}<br>Interventions : %{y}<br>% : %{customdata[0]}%")
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)


if "Motif de non réalisation" in flt.columns:
    top_motifs = _value_counts(
        flt,
        "Motif de non réalisation",
        _params(tech, y, m, d, agc_sel, pr, uo_sel, st_sel, et_sel),
        n=10,
    )
    total = top_motifs["Interventions"].sum()
    top_motifs["%"] = (top_motifs["Interventions"] / total * 100).round(1)

    fig = px.bar(
        top_motifs,
        x="Motif de non réalisation",
        y="Interventions",
        title="Top 10 motifs de non réalisation",
        color_discrete_sequence=ENEDIS_COLORS,
        hover_data={"%": True, "Interventions": True}
    )
    fig.update_traces(hovertemplate="%{x}<br>Interventions : %{y}<br>% : %{customdata[0]}%")
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

if "Libelle du BI" in flt.columns:
    t = _value_counts(
        flt,
        "Libelle du BI",
        _params(tech, y, m, d, agc_sel, pr, uo_sel, st_sel, et_sel),
        n=10,
    )
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
    top_prm = _top_prm(
        flt,
        _params(tech, y, m, d, agc_sel, pr, uo_sel, st_sel, et_sel),
    )
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
    t = _value_counts(
        flt,
        "Origine",
        _params(tech, y, m, d, agc_sel, pr, uo_sel, st_sel, et_sel),
    )
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
        t = _date_prog_counts(
            flt,
            _params(tech, y, m, d, agc_sel, pr, uo_sel, st_sel, et_sel),
        )
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
    t = _temps_moyens(
        flt,
        _params(tech, y, m, d, agc_sel, pr, uo_sel, st_sel, et_sel),
    )
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
    cdt_counts = _value_counts(
        flt,
        "CDT",
        _params(tech, y, m, d, agc_sel, pr, uo_sel, st_sel, et_sel),
    )
    fig = px.bar(
        cdt_counts,
        x="CDT",
        y="Interventions",
        title="Interventions par agent CDT",
        color_discrete_sequence=ENEDIS_COLORS,
    )
    st.plotly_chart(fig, use_container_width=True)



gj = get_geojson()

if "Arr" in flt.columns and gj:
    arr = _arr_counts(
        flt,
        _params(tech, y, m, d, agc_sel, pr, uo_sel, st_sel, et_sel),
    )

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
        _uo_top(
            flt,
            _params(tech, y, m, d, agc_sel, pr, uo_sel, st_sel, et_sel),
        ),
        x="UO",
        y="Interventions",
        title="Top 10 UO",
        color_discrete_sequence=ENEDIS_COLORS,
    )
    st.plotly_chart(fig, use_container_width=True)

st.dataframe(flt)
