import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
from datetime import datetime

# Charger les données
@st.cache_data
def load_data():
    df = pd.read_excel("votre_fichier.xlsx")  # Remplacez par votre chemin
    
    # Convertir les colonnes de date si nécessaire (ex: "date_fabrication" en datetime)
    df["date_fabrication"] = pd.to_datetime(df["date_fabrication"], errors="coerce")
    df["date d'installation"] = pd.to_datetime(df["date d'installation"], errors="coerce")
    
    # Calculer le délai avant premier incident (si les colonnes existent)
    if "date de premier incident" in df.columns:
        df["délai_panne"] = (df["date de premier incident"] - df["date d'installation"]).dt.days
    
    return df

df = load_data()

# ---------------------------------------------------------------------
# Interface Streamlit
# ---------------------------------------------------------------------
st.title("📊 Dashboard Analyse Produits")
st.markdown("Explorez les données par modèle, pays et période.")

# Sidebar : Filtres
st.sidebar.header("**Filtres**")

# 1. Filtre par modèle
selected_models = st.sidebar.multiselect(
    "Modèles",
    options=sorted(df["modèle"].unique()),
    default=df["modèle"].unique()[0]  # Par défaut, premier modèle
)

# 2. Filtre par pays (filiale)
selected_countries = st.sidebar.multiselect(
    "Pays (Filiale)",
    options=sorted(df["filiale"].unique()),
    default=df["filiale"].unique()[0]
)

# 3. Filtre par année de fabrication
if "date_fabrication" in df.columns:
    min_year = df["date_fabrication"].dt.year.min()
    max_year = df["date_fabrication"].dt.year.max()
    year_range = st.sidebar.slider(
        "Année de fabrication",
        min_value=int(min_year),
        max_value=int(max_year),
        value=(int(min_year), int(max_year))
else:
    st.sidebar.warning("Colonne 'date_fabrication' non trouvée.")

# 4. Filtre par nombre d'incidents
incident_range = st.sidebar.slider(
    "Nombre d'incidents (min-max)",
    min_value=int(df["nombre d'incidents"].min()),
    max_value=int(df["nombre d'incidents"].max()),
    value=(0, int(df["nombre d'incidents"].max()))
)

# Appliquer les filtres
filtered_df = df[
    (df["modèle"].isin(selected_models)) &
    (df["filiale"].isin(selected_countries)) &
    (df["nombre d'incidents"].between(*incident_range))
]

if "date_fabrication" in df.columns:
    filtered_df = filtered_df[
        (filtered_df["date_fabrication"].dt.year >= year_range[0]) &
        (filtered_df["date_fabrication"].dt.year <= year_range[1])
    ]

# ---------------------------------------------------------------------
# Visualisations
# ---------------------------------------------------------------------
st.header("📈 Statistiques Clés")

# KPI rapides
col1, col2, col3 = st.columns(3)
col1.metric("Produits filtrés", len(filtered_df))
col2.metric("Incidents moyens", round(filtered_df["nombre d'incidents"].mean(), 1))
if "délai_panne" in filtered_df.columns:
    col3.metric("Délai moyen avant incident (jours)", round(filtered_df["délai_panne"].mean(), 1))

# 1. Histogramme des incidents par modèle
st.subheader("Incidents par modèle")
fig1 = px.bar(
    filtered_df.groupby("modèle")["nombre d'incidents"].sum().reset_index(),
    x="modèle",
    y="nombre d'incidents",
    color="modèle"
)
st.plotly_chart(fig1, use_container_width=True)

# 2. Carte des retours par pays (si colonne "pays" est exploitable)
if "filiale" in filtered_df.columns:
    st.subheader("Retours par pays")
    country_counts = filtered_df["filiale"].value_counts().reset_index()
    country_counts.columns = ["pays", "count"]
    
    fig2 = px.choropleth(
        country_counts,
        locations="pays",
        locationmode="country names",
        color="count",
        hover_name="pays",
        title="Nombre de retours par pays"
    )
    st.plotly_chart(fig2, use_container_width=True)

# 3. Graphique temporel des installations/incidents
if "date d'installation" in filtered_df.columns:
    st.subheader("Activité mensuelle")
    monthly_data = filtered_df.set_index("date d'installation").resample("M").agg({
        "numéro de série": "count",
        "nombre d'incidents": "sum"
    }).reset_index()
    
    fig3 = px.line(
        monthly_data,
        x="date d'installation",
        y=["numéro de série", "nombre d'incidents"],
        labels={"value": "Nombre", "variable": "Type"},
        title="Installations vs Incidents par mois"
    )
    st.plotly_chart(fig3, use_container_width=True)

# 4. Tableau interactif des données filtrées
st.subheader("Données Brutes (Filtrées)")
st.dataframe(filtered_df, height=300)
