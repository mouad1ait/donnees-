import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io

# Configuration de la page
st.set_page_config(
    page_title="Dashboard Analyse Produits",
    page_icon="📊",
    layout="wide"
)

# Titre principal
st.title("📊 Dashboard d'Analyse des Produits")

# Fonction pour traiter les données
def process_data(df):
    # Conversion des dates
    date_cols = ['date d\'installation', 'date de premier incident', 'date_fabrication']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Calcul du délai de panne
    if all(col in df.columns for col in ['date de premier incident', 'date d\'installation']):
        df['délai_panne'] = (df['date de premier incident'] - df['date d\'installation']).dt.days
    
    return df

# Téléversement de fichier
uploaded_file = st.file_uploader(
    "📤 Téléversez votre fichier Excel",
    type=['xlsx', 'xls'],
    help="Format attendu: colonnes modèle, numéro de série, incidents, etc."
)

if uploaded_file is not None:
    try:
        # Lire le fichier
        df = pd.read_excel(uploaded_file)
        df = process_data(df)
        
        # Afficher un message de succès
        st.success("Fichier chargé avec succès!")
        
        # Afficher un aperçu
        with st.expander("Aperçu des données brutes"):
            st.dataframe(df.head())
        
        # ---------------------------------------------------------------------
        # Analyse interactive
        # ---------------------------------------------------------------------
        st.header("Analyse Interactive")
        
        # Sidebar - Filtres
        st.sidebar.header("Filtres")
        
        # Filtre par modèle
        selected_models = st.sidebar.multiselect(
            'Modèles',
            options=sorted(df['modèle'].unique()),
            default=sorted(df['modèle'].unique())[:2]
        )
        
        # Filtre par pays
        selected_countries = st.sidebar.multiselect(
            'Pays (Filiale)',
            options=sorted(df['filiale'].unique()),
            default=sorted(df['filiale'].unique())[:2]
        )
        
        # Application des filtres
        filtered_df = df[
            (df['modèle'].isin(selected_models)) &
            (df['filiale'].isin(selected_countries))
        ]
        
        # Métriques clés
        st.subheader("Indicateurs Clés")
        cols = st.columns(3)
        cols[0].metric("Produits", len(filtered_df))
        cols[1].metric("Incidents moyens", round(filtered_df['nombre d\'incidents'].mean(), 1))
        if 'délai_panne' in filtered_df.columns:
            cols[2].metric("Délai moyen avant incident", f"{round(filtered_df['délai_panne'].mean(), 1)} jours")
        
        # Visualisations
        tab1, tab2 = st.tabs(["Analyse Produit", "Analyse Temporelle"])
        
        with tab1:
            # Graphique des incidents par modèle
            fig1 = px.bar(
                filtered_df.groupby('modèle')['nombre d\'incidents'].sum().reset_index(),
                x='modèle',
                y='nombre d\'incidents',
                title='Incidents par Modèle'
            )
            st.plotly_chart(fig1, use_container_width=True)
            
            # Heatmap des incidents
            if 'filiale' in filtered_df.columns:
                pivot = filtered_df.pivot_table(
                    index='filiale',
                    columns='modèle', 
                    values='nombre d\'incidents',
                    aggfunc='sum'
                )
                st.write("Incidents par pays et modèle")
                st.dataframe(pivot.style.background_gradient(cmap='YlOrRd'))
        
        with tab2:
            # Analyse temporelle
            if 'date d\'installation' in filtered_df.columns:
                monthly_data = filtered_df.set_index('date d\'installation').resample('M').size()
                fig2 = px.line(
                    monthly_data,
                    title='Installations par Mois'
                )
                st.plotly_chart(fig2, use_container_width=True)
        
        # Données filtrées
        st.subheader("Données Filtrees")
        st.dataframe(filtered_df)
        
    except Exception as e:
        st.error(f"Erreur lors du traitement du fichier: {str(e)}")
else:
    st.info("Veuillez téléverser un fichier Excel pour commencer l'analyse")
    st.markdown("""
    **Format attendu:**
    - Colonne 'modèle' (V01, V01KB, etc.)
    - Colonne 'numéro de série'
    - Colonne 'nombre d\'incidents'
    - Colonnes de dates (installation, premier incident)
    """)

# Instructions
with st.expander("ℹ️ Instructions"):
    st.markdown("""
    1. Cliquez sur "Browse files" pour téléverser votre fichier Excel
    2. Utilisez les filtres dans la sidebar pour affiner l'analyse
    3. Consultez les différents onglets pour les visualisations
    """)
