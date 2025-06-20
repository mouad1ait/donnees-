import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import numpy as np

# Configuration de la page
st.set_page_config(
    page_title="Dashboard Produits - Filtres Avancés",
    page_icon="🔍",
    layout="wide"
)

# Titre principal
st.title("🔍 Analyse des Produits avec Filtres Avancés")

# Fonction pour traiter les données
def process_data(df):
    # Conversion des dates
    date_cols = ['date d\'installation', 'dernière connexion', 'Première date incident', 'Date de fabrication']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Extraction année/mois de fabrication depuis numéro de série si nécessaire
    if 'Date de fabrication' not in df.columns and 'no de série' in df.columns:
        try:
            df['Date de fabrication'] = df['no de série'].apply(
                lambda x: datetime.strptime(f"20{x[2:4]}-{x[:2]}-01", "%Y-%m-%d") if pd.notna(x) and len(str(x)) >= 4 else pd.NaT
            )
        except:
            pass
    
    # Calcul du délai avant premier incident
    if all(col in df.columns for col in ['Première date incident', 'date d\'installation']):
        df['délai_premier_incident'] = (df['Première date incident'] - df['date d\'installation']).dt.days
    
    return df

# Téléversement de fichier
uploaded_file = st.file_uploader(
    "📤 Téléversez votre fichier Excel",
    type=['xlsx'],
    help="Colonnes attendues: modèle, no de série, nombre_incidents, etc."
)

if uploaded_file is not None:
    try:
        # Lire le fichier
        df = pd.read_excel(uploaded_file)
        df = process_data(df)
        
        # Afficher un message de succès
        st.success(f"Fichier chargé avec succès! ({len(df)} enregistrements)")
        
        # ---------------------------------------------------------------------
        # Filtres Avancés - Sidebar
        # ---------------------------------------------------------------------
        st.sidebar.header("🔧 Filtres Avancés")
        
        # 1. Filtre Texte (Recherche)
        st.sidebar.subheader("Recherche Textuelle")
        
        # Recherche par modèle
        model_search = st.sidebar.text_input("Recherche par modèle (ex: V01, VRS)")
        if model_search:
            df = df[df['modèle'].astype(str).str.contains(model_search, case=False, na=False)]
        
        # Recherche par numéro de série
        serial_search = st.sidebar.text_input("Recherche par numéro de série")
        if serial_search:
            df = df[df['no de série'].astype(str).str.contains(serial_search, case=False, na=False)]
        
        # 2. Filtres par Sélection
        st.sidebar.subheader("Filtres par Sélection")
        
        # Filtre multi-sélection pour modèle
        selected_models = st.sidebar.multiselect(
            "Filtrer par modèle",
            options=sorted(df['modèle'].unique()),
            default=None,
            help="Sélectionnez un ou plusieurs modèles"
        )
        if selected_models:
            df = df[df['modèle'].isin(selected_models)]
        
        # Filtre multi-sélection pour pays
        if 'filiale' in df.columns:
            selected_countries = st.sidebar.multiselect(
                "Filtrer par filiale/pays",
                options=sorted(df['filiale'].unique()),
                default=None
            )
            if selected_countries:
                df = df[df['filiale'].isin(selected_countries)]
        
        # 3. Filtres Numériques
        st.sidebar.subheader("Filtres Numériques")
        
        # Filtre par nombre d'incidents
        if 'nombre_incidents' in df.columns:
            min_incidents, max_incidents = st.sidebar.slider(
                "Nombre d'incidents",
                min_value=int(df['nombre_incidents'].min()),
                max_value=int(df['nombre_incidents'].max()),
                value=(0, int(df['nombre_incidents'].max()))
            )
            df = df[df['nombre_incidents'].between(min_incidents, max_incidents)]
        
        # Filtre par nombre de retours
        if 'nombre_retours' in df.columns:
            min_returns, max_returns = st.sidebar.slider(
                "Nombre de retours SAV",
                min_value=int(df['nombre_retours'].min()),
                max_value=int(df['nombre_retours'].max()),
                value=(0, int(df['nombre_retours'].max()))
            )
            df = df[df['nombre_retours'].between(min_returns, max_returns)]
        
        # 4. Filtres Temporels
        st.sidebar.subheader("Filtres Temporels")
        
        # Filtre par date de fabrication
        if 'Date de fabrication' in df.columns:
            min_date = df['Date de fabrication'].min().to_pydatetime()
            max_date = df['Date de fabrication'].max().to_pydatetime()
            date_range = st.sidebar.date_input(
                "Période de fabrication",
                [min_date, max_date],
                min_value=min_date,
                max_value=max_date
            )
            if len(date_range) == 2:
                df = df[
                    (df['Date de fabrication'] >= pd.to_datetime(date_range[0])) & 
                    (df['Date de fabrication'] <= pd.to_datetime(date_range[1]))
                ]
        
        # ---------------------------------------------------------------------
        # Affichage des Résultats
        # ---------------------------------------------------------------------
        st.header("📊 Résultats Filtres")
        
        # Métriques clés
        st.subheader("Indicateurs Clés")
        cols = st.columns(4)
        cols[0].metric("Produits filtrés", len(df))
        cols[1].metric("Incidents totaux", int(df['nombre_incidents'].sum()))
        if 'nombre_retours' in df.columns:
            cols[2].metric("Retours SAV", int(df['nombre_retours'].sum()))
        if 'délai_premier_incident' in df.columns:
            cols[3].metric("Délai moyen avant incident", f"{df['délai_premier_incident'].mean():.1f} jours")
        
        # Visualisation des données filtrées
        tab1, tab2 = st.tabs(["📋 Données Brutes", "📈 Visualisations"])
        
        with tab1:
            # Affichage du dataframe avec possibilité de tri
            st.dataframe(
                df.sort_values('nombre_incidents', ascending=False),
                column_config={
                    "Date de fabrication": st.column_config.DateColumn("Fabriqué le"),
                    "date d\'installation": st.column_config.DateColumn("Installé le")
                },
                hide_index=True,
                use_container_width=True,
                height=500
            )
            
            # Bouton d'export
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Exporter les données filtrées (CSV)",
                data=csv,
                file_name='donnees_filtrees.csv',
                mime='text/csv'
            )
        
        with tab2:
            # Graphique 1: Répartition des incidents par modèle
            fig1 = px.bar(
                df.groupby('modèle')['nombre_incidents'].sum().reset_index(),
                x='modèle',
                y='nombre_incidents',
                title='Incidents totaux par Modèle',
                color='modèle'
            )
            st.plotly_chart(fig1, use_container_width=True)
            
            # Graphique 2: Délai avant premier incident
            if 'délai_premier_incident' in df.columns:
                fig2 = px.box(
                    df,
                    x='modèle',
                    y='délai_premier_incident',
                    title='Délai avant Premier Incident (jours) par Modèle'
                )
                st.plotly_chart(fig2, use_container_width=True)
            
            # Graphique 3: Carte géographique (si données disponibles)
            if 'filiale' in df.columns:
                geo_data = df.groupby('filiale')['nombre_incidents'].sum().reset_index()
                fig3 = px.choropleth(
                    geo_data,
                    locations='filiale',
                    locationmode='country names',
                    color='nombre_incidents',
                    hover_name='filiale',
                    title='Incidents par Pays/Filiale'
                )
                st.plotly_chart(fig3, use_container_width=True)
    
    except Exception as e:
        st.error(f"Erreur lors du traitement: {str(e)}")
else:
    st.info("Veuillez téléverser un fichier Excel pour commencer l'analyse")
    st.markdown("""
    **Colonnes attendues:**
    - modèle (V01, V01KB...)
    - no de série
    - filiale (pays)
    - date d'installation
    - nombre_incidents
    - nombre_retours
    """)

# Instructions
with st.expander("ℹ️ Mode d'emploi des filtres"):
    st.markdown("""
    **1. Recherche Textuelle:**
    - Tapez un terme pour filtrer les modèles ou numéros de série
    
    **2. Filtres par Sélection:**
    - Choisissez un ou plusieurs modèles/pays
    
    **3. Filtres Numériques:**
    - Sélectionnez une plage d'incidents ou retours
    
    **4. Filtres Temporels:**
    - Définissez une période de fabrication
    
    **Astuce:** Combinez plusieurs filtres pour affiner votre analyse!
    """)
