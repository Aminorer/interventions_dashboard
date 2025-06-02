import streamlit as st, pandas as pd, numpy as np, plotly.express as px, unicodedata, re, json, requests
from pathlib import Path

st.set_page_config(page_title="Interventions Enedis", layout="wide", initial_sidebar_state="expanded")

root = Path(__file__).parent
logo = root / "enedis_logo.png"
geo = root / "arrondissements.geojson"
if not logo.exists():
    logo.write_bytes(requests.get("https://upload.wikimedia.org/wikipedia/fr/7/7d/Enedis_logo.svg", timeout=15).content)
if not geo.exists():
    geo.write_bytes(requests.get("https://opendata.paris.fr/explore/dataset/arrondissements/download/?format=geojson", timeout=30).content)

enedis_cols = ["#2C75FF", "#75C700", "#4A9BFF", "#A0D87C", "#0072F0", "#47B361", "#6EABFF", "#9EE08E"]

st.image(str(logo), width=220)

def _n(x):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(x)) if not unicodedata.combining(c)).lower().replace(' ', '').replace('_', '')

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

df = _load(upl)
if df is None or df.empty:
    st.error("Fichier non conforme")
    st.stop()

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

def pct(s):
    return (s / s.sum() * 100).round(1)

c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric("Nombre d’interventions", len(flt))

if {"Temps réalisé", "Temps théorique"}.issubset(flt.columns):
    réalisé_moy = flt["Temps réalisé"].mean()
    théorique_moy = flt["Temps théorique"].mean()
    réalisé_max = flt["Temps réalisé"].max()
    réalisé_min = flt["Temps réalisé"].min()
    ecart_moyen = (flt["Temps réalisé"] - flt["Temps théorique"]).mean()
    taux_depassement = (flt["Temps réalisé"] > flt["Temps théorique"]).mean() * 100

    c2.metric("Réalisé moyen (min)", f"{réalisé_moy:.1f}")
    c3.metric("Théorique moyen (min)", f"{théorique_moy:.1f}")
    c4.metric("Durée max (réalisé)", f"{réalisé_max:.1f}")
    c5.metric("Durée min (réalisé)", f"{réalisé_min:.1f}")
    c6.metric("Écart moyen (réal - théor)", f"{ecart_moyen:+.1f} min")

    st.caption(f"💡 {taux_depassement:.1f}% des interventions ont dépassé la durée théorique.")
else:
    réalisé_moy = flt["Temps réalisé"].mean()
    réalisé_max = flt["Temps réalisé"].max()
    réalisé_min = flt["Temps réalisé"].min()

    c2.metric("Durée moyenne", f"{réalisé_moy:.1f} min")
    c3.metric("Durée max", f"{réalisé_max:.1f} min")
    c4.metric("Durée min", f"{réalisé_min:.1f} min")


vm = flt.groupby(["Année", "Mois_nom"]).size().reset_index(name="n")
st.plotly_chart(px.bar(vm, x="Mois_nom", y="n", color="Année", color_discrete_sequence=enedis_cols, barmode="group", title="Volume mensuel"), use_container_width=True)

if "Prestation" in flt.columns:
    st.plotly_chart(px.pie(flt, names="Prestation", color_discrete_sequence=enedis_cols, title="Répartition prestations"), use_container_width=True)

if {"Statut de l'intervention", "Etat de réalisation"}.issubset(flt.columns):
    a, b = st.columns(2)
    a.plotly_chart(px.pie(flt, names="Statut de l'intervention", color_discrete_sequence=enedis_cols, title="Statut"), use_container_width=True)
    b.plotly_chart(px.pie(flt, names="Etat de réalisation", color_discrete_sequence=enedis_cols, title="État de réalisation"), use_container_width=True)

if "Libelle du BI" in flt.columns:
    t = flt["Libelle du BI"].value_counts().nlargest(10).reset_index()
    t.columns = ["lbl", "n"]
    t["pct"] = pct(t["n"])
    f = px.bar(t, x="lbl", y="n", text="pct", color="lbl", color_discrete_sequence=enedis_cols, title="Top 10 Libellé BI")
    f.update_traces(hovertemplate="%{x}<br>%{text}%")
    st.plotly_chart(f, use_container_width=True)

if "Code et libelle Uo" in flt.columns:
    u = flt["Code et libelle Uo"].value_counts().nlargest(10).reset_index()
    u.columns = ["uo", "n"]
    u["pct"] = pct(u["n"])
    f = px.bar(u, x="uo", y="n", text="pct", color="uo", color_discrete_sequence=enedis_cols, title="Top 10 UO")
    f.update_traces(hovertemplate="%{x}<br>%{text}%")
    st.plotly_chart(f, use_container_width=True)

if {"Temps théorique", "Temps réalisé", "Prestation"}.issubset(flt.columns):
    t = flt.groupby("Prestation")[["Temps théorique", "Temps réalisé"]].mean().reset_index()
    f = px.bar(t, x="Prestation", y=["Temps théorique", "Temps réalisé"], color_discrete_sequence=enedis_cols[:2], barmode="group", title="Temps théorique vs réalisé par prestation")
    st.plotly_chart(f, use_container_width=True)

if "Arr" in flt.columns and geo.exists():
    arr = flt["Arr"].value_counts().rename_axis("Arr").reset_index(name="n")
    arr["Arr"] = arr["Arr"].astype(str).str.zfill(2)
    arr["pct"] = pct(arr["n"])
    gj = json.loads(geo.read_text())
    f = px.choropleth(arr, geojson=gj, locations="Arr", color="pct", color_continuous_scale=[[0, "#E6F0FF"], [1, "#2C75FF"]], featureidkey="properties.c_ar", hover_data={"pct":":.1f"}, center={"lat": 48.8566, "lon": 2.3522}, title="Interventions par arrondissement")
    f.update_geos(fitbounds="locations", visible=False)
    f.update_traces(hovertemplate="Arr %{location}<br>%{customdata[0]}%")
    st.plotly_chart(f, use_container_width=True)

cols_order = ["PRM", "Prestation", "Perimètre géographique", "Libelle du BI", "Commune", "Code et libelle Uo", "Origine", "Date de programmation", "Date de réalisation", "Statut de l'intervention", "Etat de réalisation", "Motif de non réalisation", "Temps théorique", "Temps réalisé", "Agent", "CDT", "Commentaire du technicien"]
st.dataframe(flt[[c for c in cols_order if c in flt.columns]])

st.session_state["data"] = df
