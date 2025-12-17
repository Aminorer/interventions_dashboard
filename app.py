import streamlit as st, pandas as pd, numpy as np, plotly.express as px, unicodedata, re
from app_utils import get_logo_bytes, get_geojson, build_interventions

st.set_page_config(page_title="Interventions Enedis", layout="wide", initial_sidebar_state="expanded")

enedis_cols = ["#2C75FF", "#75C700", "#4A9BFF", "#A0D87C", "#0072F0", "#47B361", "#6EABFF", "#9EE08E"]

logo_bytes = get_logo_bytes()
if logo_bytes:
    st.image(logo_bytes, width=220)
else:
    st.warning("Logo manquant")

def _n(x):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(x)) if not unicodedata.combining(c)).lower().replace(' ', '').replace('_', '')

if hasattr(st, "cache_data"):
    cache_decorator = st.cache_data
else:  # pragma: no cover - fallback for older streamlit versions
    cache_decorator = st.cache


@cache_decorator
def _load(upload):
    def _p(df):
        df.columns = df.columns.str.strip()
        m = {_n(c): c for c in df.columns}
        d = m.get('datederealisation')
        c = m.get('commune')
        if d is None or c is None:
            return None

        ap = m.get('agentprogramme')
        ag = m.get('agent')
        if ap and 'Agent' not in df.columns:
            df.rename(columns={ap: 'Agent'}, inplace=True)
        elif ag and 'Agent' not in df.columns:
            df.rename(columns={ag: 'Agent'}, inplace=True)

        rt = m.get('tempsrealise')
        tt = m.get('tempstheorique')
        if rt:
            df.rename(columns={rt: 'Temps réalisé'}, inplace=True)
            df['Temps réalisé'] = pd.to_numeric(df['Temps réalisé'], errors='coerce')
        if tt:
            df.rename(columns={tt: 'Temps théorique'}, inplace=True)
            df['Temps théorique'] = pd.to_numeric(df['Temps théorique'], errors='coerce')

        pg = m.get('perimetregeographique')
        if pg :
            df['Agence'] = (
                df[pg]
                .astype(str)
                .str.extract(r'AISMA\s+\d+_(.+)', expand=False)
                .str.replace('_', ' ', regex=False)
                .str.title()
            )

        df[d] = pd.to_datetime(df[d], errors='coerce')
        df = df.dropna(subset=[d])
        df['Année'] = df[d].dt.year
        df['Mois'] = df[d].dt.month
        df['Jour'] = df[d].dt.day
        df['Mois_nom'] = df[d].dt.strftime('%b')
        df['Arr'] = df[c].astype(str).str.extract(r'PARIS\s*(\d{1,2})')[0].astype(float).astype('Int64')
        return df

    for s in (2, 1, 0):
        try:
            upload.seek(0)
            raw = pd.read_excel(upload, skiprows=s, engine='openpyxl').dropna(how='all')
        except:
            continue
        o = _p(raw)
        if o is not None:
            return o
    return None


upl = st.sidebar.file_uploader("Fichier Excel", type=["xlsx"])
if upl is None:
    st.stop()

if "data" in st.session_state and st.session_state.get("upload_name") == getattr(upl, "name", None):
    df = st.session_state["data"]
else:
    df = _load(upl)
    if df is None or df.empty:
        st.error("Fichier non conforme")
        st.stop()
    st.session_state["data"] = df
    st.session_state["upload_name"] = getattr(upl, "name", None)

years = sorted(df["Année"].unique())
months = list(range(1, 13))
days = list(range(1, 32))
agents = sorted(df["Agent"].dropna().unique()) if "Agent" in df.columns else []
agences = sorted(df["Agence"].dropna().unique()) if "Agence" in df.columns else []
default_agents = ["CICIO Florin","DJABELKHIR Mohammed","MAILLARD Yoann","RONCERAY Florian","PEINADO BENITO Augustin","DANSOKO Toumany","GRANDEMANGE Gary","PAYET Vincent","VAUSSOUE Jean-françois","MARC Radjoucoumar","KONE Gaoussou","TRINH Quang","ABRANTES FELIZARDO Artur","KESSI Farid","TRARI Nasr eddine","CASTELLI Stéfano","DIANIFABA Ibrahima","AHAMADA Nazir","BOUJATLA Samir","MUZAMA NDANGU Landry","BROUILLARD Geoffroy","DJABRI Gabrielle","EXILUS Marc","KONGA Chris","SANTAT Eric","LAPITRE Jean-philippe","LARNICOL Lucas","DJABELKHIR Mohamed","DAAOU Yassine","DALAOUI Jeber","LOUBAKI CYS Francel","VACQUER Andre"]
default_agents_in_data = [a for a in default_agents if a in agents] or agents
prestations = sorted(df["Prestation"].dropna().unique()) if "Prestation" in df.columns else []
uos = sorted(df["Code et libelle Uo"].dropna().unique()) if "Code et libelle Uo" in df.columns else []
statuts = sorted(df["Statut de l'intervention"].dropna().unique()) if "Statut de l'intervention" in df.columns else []
etats = sorted(df["Etat de réalisation"].dropna().unique()) if "Etat de réalisation" in df.columns else []

with st.sidebar.form("filtres"):
    y = st.multiselect("Années", years, years)
    m = st.multiselect("Mois", months, months, format_func=lambda x: f"{x:02d}")
    d = st.multiselect("Jours", days, days, format_func=lambda x: f"{x:02d}")
    ag_sel = st.multiselect("Techniciens", options=agents, default=default_agents_in_data)
    agc_sel = st.multiselect("Agence", agences, agences)
    pr = st.multiselect("Prestation", prestations, prestations)
    uo_sel = st.multiselect("UO", uos, uos)
    st_sel = st.multiselect("Statut", statuts, statuts)
    et_sel = st.multiselect("État", etats, etats)
    ok = st.form_submit_button("Appliquer")


if not ok:
    st.stop()

msk = df["Année"].isin(y) & df["Mois"].isin(m) & df["Jour"].isin(d)
if set(ag_sel) != set(agents):
    msk &= df["Agent"].isin(ag_sel)
if set(agc_sel) != set(agences):
    msk &= df["Agence"].isin(agc_sel)
if prestations:
    msk &= df["Prestation"].isin(pr)
if uos:
    msk &= df["Code et libelle Uo"].isin(uo_sel)
if statuts:
    msk &= df["Statut de l'intervention"].isin(st_sel)
if etats:
    msk &= df["Etat de réalisation"].isin(et_sel)

flt = df[msk]
if flt.empty:
    st.warning("Aucune donnée")
    st.stop()

interventions = build_interventions(flt)
if interventions.empty:
    st.warning("Aucune intervention selon les critères définis.")
    st.stop()

def pct(s):
    return (s / s.sum() * 100).round(1)

c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric("Nombre d’interventions", len(interventions))

if {"Temps réalisé", "Temps théorique"}.issubset(interventions.columns):
    réalisé_moy = interventions["Temps réalisé"].mean()
    théorique_moy = interventions["Temps théorique"].mean()
    réalisé_max = interventions["Temps réalisé"].max()
    réalisé_min = interventions["Temps réalisé"].min()
    ecart_moyen = (interventions["Temps réalisé"] - interventions["Temps théorique"]).mean()
    taux_depassement = (interventions["Temps réalisé"] > interventions["Temps théorique"]).mean() * 100

    c2.metric("Réalisé moyen (min)", f"{réalisé_moy:.1f}")
    c3.metric("Théorique moyen (min)", f"{théorique_moy:.1f}")
    c4.metric("Durée max (réalisé)", f"{réalisé_max:.1f}")
    c5.metric("Durée min (réalisé)", f"{réalisé_min:.1f}")
    c6.metric("Écart moyen (réal - théor)", f"{ecart_moyen:+.1f} min")

    st.caption(f"💡 {taux_depassement:.1f}% des interventions ont dépassé la durée théorique.")
else:
    réalisé_moy = interventions["Temps réalisé"].mean()
    réalisé_max = interventions["Temps réalisé"].max()
    réalisé_min = interventions["Temps réalisé"].min()

    c2.metric("Durée moyenne", f"{réalisé_moy:.1f} min")
    c3.metric("Durée max", f"{réalisé_max:.1f} min")
    c4.metric("Durée min", f"{réalisé_min:.1f} min")

va = interventions["Année"].value_counts().sort_index().reset_index()
va.columns = ["Année", "n"]
f = px.bar(
    va,
    x="Année",
    y="n",
    color="Année",
    color_discrete_sequence=enedis_cols,
    title="Volume annuel",
)
f.update_traces(text=va["n"], textposition="outside", hovertemplate="Année %{x}<br>%{y} interventions")
st.plotly_chart(f, use_container_width=True)


vm = interventions.groupby(["Année", "Mois_nom"]).size().reset_index(name="n")
st.plotly_chart(px.bar(vm, x="Mois_nom", y="n", color="Année", color_discrete_sequence=enedis_cols, barmode="group", title="Volume mensuel"), use_container_width=True)

if "Prestation" in interventions.columns:
    st.plotly_chart(px.pie(interventions, names="Prestation", color_discrete_sequence=enedis_cols, title="Répartition prestations"), use_container_width=True)

if {"Statut de l'intervention", "Etat de réalisation"}.issubset(interventions.columns):
    a, b = st.columns(2)
    a.plotly_chart(px.pie(interventions, names="Statut de l'intervention", color_discrete_sequence=enedis_cols, title="Statut"), use_container_width=True)
    b.plotly_chart(px.pie(interventions, names="Etat de réalisation", color_discrete_sequence=enedis_cols, title="État de réalisation"), use_container_width=True)

if "Libelle du BI" in interventions.columns:
    t = interventions["Libelle du BI"].value_counts().nlargest(10).reset_index()
    t.columns = ["lbl", "n"]
    t["pct"] = pct(t["n"])
    f = px.bar(t, x="lbl", y="n", text="pct", color="lbl", color_discrete_sequence=enedis_cols, title="Top 10 Libellé BI")
    f.update_traces(hovertemplate="%{x}<br>%{text}%")
    st.plotly_chart(f, use_container_width=True)

if "Code et libelle Uo" in interventions.columns:
    u = interventions["Code et libelle Uo"].value_counts().nlargest(10).reset_index()
    u.columns = ["uo", "n"]
    u["pct"] = pct(u["n"])
    f = px.bar(u, x="uo", y="n", text="pct", color="uo", color_discrete_sequence=enedis_cols, title="Top 10 UO")
    f.update_traces(hovertemplate="%{x}<br>%{text}%")
    st.plotly_chart(f, use_container_width=True)



if "PRM" in interventions.columns:
    interventions = interventions.copy()
    interventions["PRM_clean"] = interventions["PRM"].dropna().apply(lambda x: str(x).split('.')[0])
    top_prm = interventions["PRM_clean"].value_counts().nlargest(10).reset_index()
    top_prm.columns = ["PRM", "n"]
    top_prm["Rang"] = [f"{i+1}ᵉ" for i in range(len(top_prm))]

    f = px.bar(
        top_prm,
        x="Rang",
        y="n",
        color="PRM",
        color_discrete_sequence=enedis_cols,
        text="n",
        title="Top 10 PRM (classés)"
    )
    f.update_traces(textposition="outside", hovertemplate="Rang %{x}<br>%{y} interventions<br>PRM %{customdata}")
    f.update_layout(xaxis_title="Rang", yaxis_title="Nombre d’interventions")
    st.plotly_chart(f, use_container_width=True)


cols_order = [
    "PRM", "Prestation", "Perimètre géographique", "Libelle du BI", "Commune",
    "Code et libelle Uo", "Origine", "Date de programmation", "Date de réalisation",
    "Statut de l'intervention", "Etat de réalisation", "Motif de non réalisation",
    "Temps théorique", "Temps réalisé", "Agent", "CDT", "Commentaire du technicien"
]

# Affichage du tableau des lignes concernées
if "PRM_clean" in interventions.columns:
    top_10_prm = top_prm["PRM"].tolist()
    top_prm_df = interventions[interventions["PRM_clean"].isin(top_10_prm)]

    st.subheader("📋 Détails des interventions des 10 PRM les plus sollicités")
    st.dataframe(top_prm_df[[c for c in cols_order if c in top_prm_df.columns]])



if "Origine" in interventions.columns:
    t = interventions["Origine"].value_counts().reset_index()
    t.columns = ["Origine", "n"]
    t["pct"] = pct(t["n"])
    f = px.bar(t, x="Origine", y="n", text="pct", color="Origine", color_discrete_sequence=enedis_cols, title="Répartition par Origine")
    f.update_traces(hovertemplate="%{x}<br>%{text}%")
    st.plotly_chart(f, use_container_width=True)

if "Date de programmation" in interventions.columns:
    try:
        interventions = interventions.copy()
        interventions["Date de programmation"] = pd.to_datetime(interventions["Date de programmation"], errors='coerce')
        t = interventions["Date de programmation"].dt.date.value_counts().sort_index().reset_index()
        t.columns = ["Date", "n"]
        f = px.bar(t, x="Date", y="n", color_discrete_sequence=enedis_cols, title="Volume des programmations par jour")
        st.plotly_chart(f, use_container_width=True)
    except:
        pass

if "Motif de non réalisation" in interventions.columns:
    t = interventions["Motif de non réalisation"].dropna().value_counts().nlargest(10).reset_index()
    t.columns = ["Motif", "n"]
    t["pct"] = pct(t["n"])
    f = px.bar(t, x="Motif", y="n", text="pct", color="Motif", color_discrete_sequence=enedis_cols, title="Top 10 Motifs de non réalisation")
    f.update_traces(hovertemplate="%{x}<br>%{text}%")
    st.plotly_chart(f, use_container_width=True)




if {"Temps théorique", "Temps réalisé", "Prestation"}.issubset(interventions.columns):
    t = interventions.groupby("Prestation")[["Temps théorique", "Temps réalisé"]].mean().reset_index()
    f = px.bar(t, x="Prestation", y=["Temps théorique", "Temps réalisé"], color_discrete_sequence=enedis_cols[:2], barmode="group", title="Temps théorique vs réalisé par prestation")
    st.plotly_chart(f, use_container_width=True)

gj = get_geojson()
if "Arr" in interventions.columns and gj:
    arr = interventions["Arr"].value_counts().rename_axis("Arr").reset_index(name="n")
    arr["Arr"] = arr["Arr"].astype(int)
    arr["pct"] = pct(arr["n"])
    f = px.choropleth(
    arr,
    geojson=gj,
    locations="Arr",
    color="pct",
    color_continuous_scale=[[0, "#E6F0FF"], [1, "#2C75FF"]],
    featureidkey="properties.c_ar",  # ← gardé une seule fois
    hover_data={"pct":":.1f"},
    center={"lat": 48.8566, "lon": 2.3522},
    title="Interventions par arrondissement")
    f.update_geos(fitbounds="locations", visible=False)
    f.update_traces(hovertemplate="Arr %{location}<br>%{customdata[0]}%")
    st.plotly_chart(f, use_container_width=True)

cols_order = ["PRM", "Prestation", "Perimètre géographique", "Libelle du BI", "Commune", "Code et libelle Uo", "Origine", "Date de programmation", "Date de réalisation", "Statut de l'intervention", "Etat de réalisation", "Motif de non réalisation", "Temps théorique", "Temps réalisé", "Agent", "CDT", "Commentaire du technicien"]
st.dataframe(interventions[[c for c in cols_order if c in interventions.columns]])

