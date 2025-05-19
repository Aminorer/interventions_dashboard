import streamlit as st
import pandas as pd
import plotly.express as px
import pgeocode

st.set_page_config(page_title="Interventions Enedis", layout="wide", initial_sidebar_state="expanded")

@st.cache_resource(show_spinner=False)
def _nomi():
    return pgeocode.Nominatim("fr")

@st.cache_data(show_spinner=False)
def _geocode(codes):
    geo = _nomi().query_postal_code(codes)
    return geo[["postal_code", "latitude", "longitude"]].rename(columns={"postal_code": "cp_clean", "latitude": "lat", "longitude": "lon"})

@st.cache_data(show_spinner=False)
def _load_and_prepare(uploaded):
    df = pd.read_excel(uploaded, skiprows=2)
    df = df.dropna(how="all")
    mask = ~df.astype(str).apply(lambda s: s.str.contains("supprim|rgpd", case=False, na=False)).any(axis=1)
    df = df[mask]
    date_col = "date de réalisation"
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col])
    df["Année"] = df[date_col].dt.year
    df["Mois"] = df[date_col].dt.month
    df["Mois_nom"] = df[date_col].dt.strftime("%b")
    cp_candidates = [c for c in df.columns if c.lower().replace(" ", "").replace("_", "")
                     in ["cp", "codepostal", "codepostale", "code_postal", "postalcode", "postal_code"]]
    if not cp_candidates:
        return None
    df["cp_clean"] = df[cp_candidates[0]].astype(str).str.extract(r"(\d{5})", expand=False)
    df = df.dropna(subset=["cp_clean"])
    df = df.merge(_geocode(df["cp_clean"].unique()), on="cp_clean", how="left")
    df = df.dropna(subset=["lat", "lon"])
    return df

file = st.sidebar.file_uploader("Téléverser le fichier Excel", type=["xlsx"])
if file is None:
    st.info("Importe d’abord le fichier pour afficher les pages.")
    st.stop()

df = _load_and_prepare(file)
if df is None:
    st.error("Aucune colonne code postal trouvée.")
    st.stop()

page = st.sidebar.radio("Page", ["Accueil", "Statistiques détaillées"])

with st.sidebar.form("Filtres"):
    techs = sorted(df["Agent Programmé"].dropna().unique())
    years = sorted(df["Année"].unique())
    months = sorted(df["Mois"].unique())
    agences = sorted(df["Agence"].dropna().unique())
    types = sorted(df["Type"].dropna().unique())

    if page == "Accueil":
        selected_techs = st.multiselect("Technicien", techs, default=techs)
    else:
        selected_techs = techs

    selected_years = st.multiselect("Année", years, default=years)
    selected_months = st.multiselect("Mois", months, default=months, format_func=lambda x: f"{x:02d}")
    selected_agences = st.multiselect("Agence", agences, default=agences)
    selected_types = st.multiselect("Type", types, default=types)
    apply_filters = st.form_submit_button("Appliquer")

if not apply_filters:
    st.stop()

filtered = df[
    (df["Agent Programmé"].isin(selected_techs))
    & (df["Année"].isin(selected_years))
    & (df["Mois"].isin(selected_months))
    & (df["Agence"].isin(selected_agences))
    & (df["Type"].isin(selected_types))
]

if filtered.empty:
    st.warning("Aucune ligne ne correspond aux filtres.")
    st.stop()

pct = lambda s: s / s.sum() * 100

def carte(data, color_col, color_scale, title):
    fig = px.scatter_mapbox(
        data,
        lat="lat",
        lon="lon",
        size="Interventions",
        color=color_col,
        color_continuous_scale=color_scale if color_col == "Interventions" else None,
        color_discrete_sequence=px.colors.qualitative.Vivid if color_col == "Type" else None,
        zoom=5,
        size_max=18,
        height=520,
        title=title
    )
    fig.update_layout(mapbox_style="carto-positron", margin=dict(l=0, r=0, t=50, b=0))
    st.plotly_chart(fig, use_container_width=True)

if page == "Accueil":
    total, avg, minimum, maximum = len(filtered), filtered["Durée"].mean(), filtered["Durée"].min(), filtered["Durée"].max()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Interventions", total)
    c2.metric("Durée moyenne (min)", f"{avg:.1f}")
    c3.metric("Durée mini (min)", f"{minimum}")
    c4.metric("Durée maxi (min)", f"{maximum}")

    carte(filtered.groupby(["cp_clean", "lat", "lon"]).size().reset_index(name="Interventions"),
          "Interventions", "Reds", "Carte des interventions")

    st.plotly_chart(
        px.pie(filtered, names="Type", hole=.4, title="Répartition des interventions par type")
          .update_traces(textinfo="percent+label"),
        use_container_width=True
    )

    tech_counts = filtered["Agent Programmé"].value_counts().reset_index()
    tech_counts.columns = ["Technicien", "Interventions"]
    tech_counts["%"] = pct(tech_counts["Interventions"])
    st.plotly_chart(
        px.bar(tech_counts, y="Technicien", x="Interventions", orientation="h", text="%", title="Interventions par technicien"),
        use_container_width=True
    )

    month_counts = filtered.groupby(["Année", "Mois_nom"]).size().reset_index(name="Interventions")
    st.plotly_chart(
        px.bar(month_counts, x="Mois_nom", y="Interventions", color="Année", barmode="group",
               title="Interventions par mois et année"),
        use_container_width=True
    )

    state_counts = filtered["Etat de réalisation"].value_counts().reset_index()
    state_counts.columns = ["Etat", "Interventions"]
    state_counts["%"] = pct(state_counts["Interventions"])
    st.plotly_chart(
        px.bar(state_counts, x="Etat", y="Interventions", text="%", title="État de réalisation"),
        use_container_width=True
    )

    cat_counts = filtered["Catégories OPEX/CAPEX"].value_counts().reset_index()
    cat_counts.columns = ["Catégorie", "Interventions"]
    cat_counts["%"] = pct(cat_counts["Interventions"])
    st.plotly_chart(
        px.bar(cat_counts, x="Catégorie", y="Interventions", text="%", title="Catégorie OPEX/CAPEX"),
        use_container_width=True
    )

    top10 = filtered["uoe libelle"].value_counts().nlargest(10).reset_index()
    top10.columns = ["UO", "Interventions"]
    top10["%"] = pct(top10["Interventions"])
    st.plotly_chart(
        px.bar(top10, y="UO", x="Interventions", orientation="h", text="%", title="Top 10 UO"),
        use_container_width=True
    )

    st.dataframe(filtered)

else:
    tech_choice = st.selectbox("Choisis un technicien", sorted(df["Agent Programmé"].dropna().unique()))
    tech_df = filtered[filtered["Agent Programmé"] == tech_choice]
    if tech_df.empty:
        st.warning("Aucune ligne pour ce technicien.")
        st.stop()

    t_total, t_avg, t_min, t_max = len(tech_df), tech_df["Durée"].mean(), tech_df["Durée"].min(), tech_df["Durée"].max()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Interventions", t_total)
    c2.metric("Durée moyenne (min)", f"{t_avg:.1f}")
    c3.metric("Durée mini (min)", f"{t_min}")
    c4.metric("Durée maxi (min)", f"{t_max}")

    carte(tech_df.groupby(["cp_clean", "lat", "lon", "Type"]).size().reset_index(name="Interventions"),
          "Type", None, f"Carte – {tech_choice}")

    ts = tech_df.resample("ME", on="date de réalisation").size().reset_index(name="Interventions")
    st.plotly_chart(px.line(ts, x="date de réalisation", y="Interventions", markers=True,
                            title="Interventions par mois"), use_container_width=True)

    type_pct = tech_df["Type"].value_counts(normalize=True).mul(100).round(2).reset_index()
    type_pct.columns = ["Type", "Pourcentage"]
    st.plotly_chart(
        px.pie(type_pct, names="Type", values="Pourcentage", hole=.4,
               title="Répartition des interventions par type")
          .update_traces(textinfo="percent+label"),
        use_container_width=True
    )

    by_state = tech_df["Etat de réalisation"].value_counts(normalize=True).mul(100).reset_index()
    by_state.columns = ["Etat", "Pourcentage"]
    st.plotly_chart(px.bar(by_state, x="Etat", y="Pourcentage", text="Pourcentage",
                           title="État de réalisation"), use_container_width=True)

    monthly_type = tech_df.groupby(["Année", "Mois_nom", "Type"]).size().reset_index(name="Interventions")
    st.plotly_chart(
        px.bar(monthly_type, x="Mois_nom", y="Interventions", color="Type",
               facet_col="Année", facet_col_wrap=2,
               color_discrete_sequence=px.colors.qualitative.Vivid,
               title="Interventions mensuelles par type"),
        use_container_width=True
    )

    comparaison = tech_df.assign(Comparaison=lambda d: d.apply(
        lambda r: "Identiques" if r["Agent CDT"] == r["Agent Programmé"]
        else ("Agent CDT manquant" if pd.isna(r["Agent CDT"]) and pd.notna(r["Agent Programmé"]) else "Différents"), axis=1))
    comp_counts = comparaison["Comparaison"].value_counts().reset_index()
    comp_counts.columns = ["Comparaison", "Interventions"]
    st.plotly_chart(px.bar(comp_counts, x="Comparaison", y="Interventions", text="Interventions",
                           title="Comparaison Agent Programmé / Agent CDT"), use_container_width=True)

    st.dataframe(tech_df)
