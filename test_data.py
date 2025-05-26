import streamlit as st
import pandas as pd
import plotly.express as px
import pgeocode
import unicodedata
import re
from pathlib import Path
import numpy as np



st.set_page_config(page_title="Interventions Enedis", layout="wide", initial_sidebar_state="expanded")



def _n(x):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(x)) if not unicodedata.combining(c)).lower().replace(' ', '').replace('_', '')



@st.cache_resource(show_spinner=False)
def _geo_engine():
    return pgeocode.Nominatim('fr')



@st.cache_data(show_spinner=False)
def _geo(names):
    g = _geo_engine()
    rows = []
    for raw in pd.Series(names).dropna().unique():
        clean = re.sub(r'\d+', '', str(raw)).strip().title()
        d = g.query_location(clean)
        if isinstance(d, pd.DataFrame) and not d.empty and pd.notna(d.iloc[0].latitude) and pd.notna(d.iloc[0].longitude):
            rows.append({'geo_key': raw, 'lat': d.iloc[0].latitude, 'lon': d.iloc[0].longitude})
    return pd.DataFrame(rows, columns=['geo_key', 'lat', 'lon'])



@st.cache_data(show_spinner=False)
def _load(file):
    ext = Path(file.name).suffix.lower()
    skip, engine = (2, 'openpyxl') if ext == '.xlsx' else (1, 'xlrd')
    df = pd.read_excel(file, skiprows=skip, engine=engine).dropna(how='all')
    df.columns = df.columns.str.strip()
    nmap = {_n(c): c for c in df.columns}
    dcol = nmap.get('datederealisation')
    if dcol is None:
        return None
    df[dcol] = pd.to_datetime(df[dcol], errors='coerce')
    df = df.dropna(subset=[dcol])
    perim = next((c for c in df.columns if _n(c).startswith('perimetregeo')), None)
    if perim is not None:
        df['Agence'] = df[perim].astype(str).str.extract(r'AISMA\s+\d+_(.*)', expand=False).str.title()
    rename = {}
    for pat, new in [('agentprogrammé$', 'Agent Programmé'),
                     ('agent$', 'Agent'),
                     ('cdt', 'CDT'),
                     ('durée', 'Durée'),
                     ('tempstheorique', 'Temps théorique'),
                     ('tempsreal', 'Temps realisé'),
                     ('prestation|type$', 'Type'),
                     ('cat', 'Catégories OPEX/CAPEX'),
                     ('uoe|libelleu[o0]', 'uoe libelle')]:
        col = next((x for x in df.columns if re.search(pat, _n(x))), None)
        if col is not None:
            rename[col] = new
    df = df.rename(columns=rename)
    com = nmap.get('commune')
    if com is None:
        return None
    df['geo_key'] = df[com].astype(str).str.strip()
    geo = _geo(df['geo_key'].unique())
    df = df.merge(geo, on='geo_key', how='left').dropna(subset=['lat', 'lon'])
    if df.empty:
        return None
    df['Année'] = df[dcol].dt.year
    df['Mois'] = df[dcol].dt.month
    df['Mois_nom'] = df[dcol].dt.strftime('%b')
    for c in ['Durée', 'Temps théorique', 'Temps realisé']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    df.attrs['date_col'] = dcol
    return df



file = st.sidebar.file_uploader('Téléverser le fichier Excel', type=['xls', 'xlsx'])
if file is None:
    st.stop()



df = _load(file)
if df is None:
    st.error('Fichier non conforme')
    st.stop()



date_col = df.attrs['date_col']



agent_col = 'Agent Programmé' if 'Agent Programmé' in df.columns else 'Agent'



pages = ['Accueil', 'Statistiques détaillées']
page = st.sidebar.radio('Page', pages)



with st.sidebar.form('Filtres'):
    techs = sorted(df[agent_col].dropna().unique())
    years = sorted(df['Année'].unique())
    months = sorted(df['Mois'].unique())
    agences = sorted(df['Agence'].dropna().unique()) if 'Agence' in df.columns else []
    types = sorted(df['Type'].dropna().unique()) if 'Type' in df.columns else []
    sel_techs = st.multiselect('Technicien', techs, techs if page == 'Accueil' else techs) if page == 'Accueil' else techs
    sel_years = st.multiselect('Année', years, years)
    sel_months = st.multiselect('Mois', months, months, format_func=lambda x: f'{x:02d}')
    sel_agence = st.multiselect('Agence', agences, agences)
    sel_types = st.multiselect('Type', types, types)
    btn = st.form_submit_button('Appliquer')



if not btn:
    st.stop()



mask = (df[agent_col].isin(sel_techs)) & \
       df['Année'].isin(sel_years) & \
       df['Mois'].isin(sel_months) & \
       (df['Agence'].isin(sel_agence) if 'Agence' in df.columns else True) & \
       (df['Type'].isin(sel_types) if 'Type' in df.columns else True)



flt = df[mask]
if flt.empty:
    st.warning('Aucune donnée')
    st.stop()



def pct(s):
    s = s.astype(float)
    return s.div(s.sum()).mul(100)



def mapbox(d, col, title):
    fig = px.scatter_mapbox(d, lat='lat', lon='lon', size='Interventions', color=col,
                            zoom=5, size_max=18, height=520, title=title,
                            color_discrete_sequence=px.colors.qualitative.Vivid if col != 'Interventions' else None,
                            color_continuous_scale='Reds' if col == 'Interventions' else None)
    fig.update_layout(mapbox_style='carto-positron', margin=dict(l=0, r=0, t=50, b=0))
    st.plotly_chart(fig, use_container_width=True)



base_cols = ['lat', 'lon']



if page == 'Accueil':
    dur_series = flt['Durée'] if 'Durée' in flt.columns and flt['Durée'].any() else flt['Temps realisé'] if 'Temps realisé' in flt.columns else pd.Series(dtype=float)
    positive = dur_series[dur_series > 0]
    total = len(flt)
    avg_r = positive.mean() if not positive.empty else 0
    min_r = positive.min() if not positive.empty else 0
    max_r = dur_series.max() if not dur_series.empty else 0
    avg_t = flt['Temps théorique'][flt['Temps théorique'] > 0].mean() if 'Temps théorique' in flt.columns else 0
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric('Interventions', total)
    c2.metric('Réal moy (min)', f'{avg_r:.1f}')
    c3.metric('Réal min (min)', f'{min_r}')
    c4.metric('Réal max (min)', f'{max_r}')
    c5.metric('Théor moy (min)', f'{avg_t:.1f}')
    mapbox(flt.groupby(base_cols).size().reset_index(name='Interventions'), 'Interventions', 'Carte des interventions')
    if 'Type' in flt.columns:
        st.plotly_chart(px.pie(flt, names='Type', hole=.4, title='Répartition par type').update_traces(textinfo='percent+label'), use_container_width=True)
    if agent_col in flt.columns:
        tc = flt[agent_col].value_counts().rename_axis('Technicien').reset_index(name='Interventions')
        tc['%'] = pct(tc['Interventions'])
        st.plotly_chart(px.bar(tc, y='Technicien', x='Interventions', orientation='h', text='%', title='Interventions par technicien'), use_container_width=True)
    mc = flt.groupby(['Année', 'Mois_nom']).size().reset_index(name='Interventions')
    st.plotly_chart(px.bar(mc, x='Mois_nom', y='Interventions', color='Année', barmode='group', title='Interventions mensuelles'), use_container_width=True)
    if 'Etat de réalisation' in flt.columns:
        et = flt['Etat de réalisation'].value_counts().rename_axis('Etat').reset_index(name='Interventions')
        et['%'] = pct(et['Interventions'])
        st.plotly_chart(px.bar(et, x='Etat', y='Interventions', text='%', title='État de réalisation'), use_container_width=True)
    if 'Catégories OPEX/CAPEX' in flt.columns:
        cat = flt['Catégories OPEX/CAPEX'].value_counts().rename_axis('Catégorie').reset_index(name='Interventions')
        cat['%'] = pct(cat['Interventions'])
        st.plotly_chart(px.bar(cat, x='Catégorie', y='Interventions', text='%', title='Catégorie OPEX/CAPEX'), use_container_width=True)
    if 'uoe libelle' in flt.columns:
        top10 = flt['uoe libelle'].value_counts().nlargest(10).rename_axis('UO').reset_index(name='Interventions')
        top10['%'] = pct(top10['Interventions'])
        st.plotly_chart(px.bar(top10, y='UO', x='Interventions', orientation='h', text='%', title='Top 10 UO'), use_container_width=True)
    if {'Temps théorique', 'Temps realisé', agent_col}.issubset(flt.columns):
        tm = flt.groupby(agent_col)[['Temps théorique', 'Temps realisé']].mean().reset_index()
        st.plotly_chart(px.bar(tm, y=agent_col, x=['Temps théorique', 'Temps realisé'], orientation='h', barmode='group', title='Temps théorique vs réalisé moyen'), use_container_width=True)
    if not dur_series.empty:
        st.plotly_chart(px.histogram(flt, x=dur_series, nbins=30, title='Distribution temps réalisé'), use_container_width=True)
        st.plotly_chart(px.box(flt, y=dur_series, title='Boîte temps réalisé'), use_container_width=True)
    st.dataframe(flt)



if page == 'Statistiques détaillées':
    if agent_col not in df.columns:
        st.warning('Pas de colonne Agent')
        st.stop()
    tech_option = st.selectbox('Choisis un technicien', sorted(flt[agent_col].dropna().unique()))
    tf = flt[flt[agent_col] == tech_option]
    if tf.empty:
        st.warning('Aucune donnée')
        st.stop()
    dur_t = tf['Durée'] if 'Durée' in tf.columns and tf['Durée'].any() else tf['Temps realisé'] if 'Temps realisé' in tf.columns else pd.Series(dtype=float)
    pos_t = dur_t[dur_t > 0]
    avg_rt = pos_t.mean() if not pos_t.empty else 0
    min_rt = pos_t.min() if not pos_t.empty else 0
    max_rt = dur_t.max() if not dur_t.empty else 0
    avg_tt = tf['Temps théorique'][tf['Temps théorique'] > 0].mean() if 'Temps théorique' in tf.columns else 0
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric('Interventions', len(tf))
    c2.metric('Réal moy (min)', f'{avg_rt:.1f}')
    c3.metric('Réal min (min)', f'{min_rt}')
    c4.metric('Réal max (min)', f'{max_rt}')
    c5.metric('Théor moy (min)', f'{avg_tt:.1f}')
    gcols = base_cols + (['Type'] if 'Type' in tf.columns else [])
    mapbox(tf.groupby(gcols).size().reset_index(name='Interventions'), 'Type' if 'Type' in tf.columns else 'Interventions', f'Carte – {tech_option}')
    ts = tf.resample('ME', on=date_col).size().reset_index(name='Interventions')
    st.plotly_chart(px.line(ts, x=date_col, y='Interventions', markers=True, title='Interventions par mois'), use_container_width=True)
    if 'Type' in tf.columns:
        tp = tf['Type'].value_counts(normalize=True).mul(100).round(2).reset_index()
        tp.columns = ['Type', 'Pourcentage']
        st.plotly_chart(px.pie(tp, names='Type', values='Pourcentage', hole=.4, title='Répartition des interventions par type').update_traces(textinfo='percent+label'), use_container_width=True)
    if 'Etat de réalisation' in tf.columns:
        es = tf['Etat de réalisation'].value_counts(normalize=True).mul(100).round(2).reset_index()
        es.columns = ['Etat', 'Pourcentage']
        st.plotly_chart(px.bar(es, x='Etat', y='Pourcentage', text='Pourcentage', title='État de réalisation'), use_container_width=True)
    if {'Année', 'Mois_nom', 'Type'}.issubset(tf.columns):
        mt = tf.groupby(['Année', 'Mois_nom', 'Type']).size().reset_index(name='Interventions')
        st.plotly_chart(px.bar(mt, x='Mois_nom', y='Interventions', color='Type', facet_col='Année', facet_col_wrap=2, title='Interventions mensuelles par type'), use_container_width=True)
    if 'CDT' in tf.columns:
        comp = tf.assign(Comparaison=lambda d: d.apply(lambda r: 'Identiques' if r['CDT'] == r[agent_col] else ('CDT manquant' if pd.isna(r['CDT']) and pd.notna(r[agent_col]) else 'Différents'), axis=1))
        cc = comp['Comparaison'].value_counts().rename_axis('Comparaison').reset_index(name='Interventions')
        st.plotly_chart(px.bar(cc, x='Comparaison', y='Interventions', text='Interventions', title='Comparaison Agent / CDT'), use_container_width=True)
    if not dur_t.empty:
        st.plotly_chart(px.histogram(tf, x=dur_t, nbins=25, title='Distribution temps réalisé'), use_container_width=True)
    st.dataframe(tf)
