import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io
import numpy as np

# Configuration de la page
st.set_page_config(
    page_title="Dashboard Produits",
    page_icon="📊",
    layout="wide"
)

# Titre principal
st.title("📊 Analyse des Produits Industriels")

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
    
    # Nettoyage des listes (incidents et RMA)
    for col in ['liste_incidents', 'liste_rma', 'dates_incidents', 'dates_rma']:
        if col in df.columns:
            df[col] = df[col].astype(str)
    
    return df

# Téléversement de fichier
uploaded_file = st.file_uploader(
    "📤 Téléversez votre fichier Excel (format attendu : .xlsx)",
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
        # Analyse interactive
        # ---------------------------------------------------------------------
        st.header("Analyse Interactive")
        
        # Sidebar - Filtres
        st.sidebar.header("Paramètres d'analyse")
        
        # Sélection temporelle
        if 'Date de fabrication' in df.columns:
            min_year = df['Date de fabrication'].dt.year.min()
            max_year = df['Date de fabrication'].dt.year.max()
            selected_years = st.sidebar.slider(
                'Période de fabrication',
                min_value=int(min_year),
                max_value=int(max_year),
                value=(int(min_year), int(max_year))
            )
        
        # Filtre par modèle
        selected_models = st.sidebar.multiselect(
            'Modèles à inclure',
            options=sorted(df['modèle'].unique()),
            default=sorted(df['modèle'].unique())
        )
        
        # Filtre par pays
        if 'filiale' in df.columns:
            selected_countries = st.sidebar.multiselect(
                'Filiales/Pays',
                options=sorted(df['filiale'].unique()),
                default=sorted(df['filiale'].unique())
            )
        
        # Application des filtres
        filtered_df = df[df['modèle'].isin(selected_models)]
        if 'filiale' in df.columns:
            filtered_df = filtered_df[filtered_df['filiale'].isin(selected_countries)]
        if 'Date de fabrication' in df.columns:
            filtered_df = filtered_df[
                (filtered_df['Date de fabrication'].dt.year >= selected_years[0]) & 
                (filtered_df['Date de fabrication'].dt.year <= selected_years[1])
            ]
        
        # Métriques clés
        st.subheader("Indicateurs Clés")
        cols = st.columns(4)
        cols[0].metric("Produits", len(filtered_df))
        cols[1].metric("Incidents totaux", int(filtered_df['nombre_incidents'].sum()))
        if 'nombre_retours' in filtered_df.columns:
            cols[2].metric("Retours SAV", int(filtered_df['nombre_retours'].sum()))
        if 'délai_premier_incident' in filtered_df.columns:
            cols[3].metric("Délai moyen avant incident", f"{filtered_df['délai_premier_incident'].mean():.1f} jours")
        
        # Visualisations
        tab1, tab2, tab3 = st.tabs(["📈 Par Produit", "🌍 Par Zone", "🔄 Historique"])
        
        with tab1:
            # Analyse par modèle
            fig1 = px.bar(
                filtered_df.groupby('modèle').agg({
                    'nombre_incidents': 'sum',
                    'nombre_retours': 'sum'
                }).reset_index(),
                x='modèle',
                y=['nombre_incidents', 'nombre_retours'],
                barmode='group',
                title='Incidents et Retours par Modèle'
            )
            st.plotly_chart(fig1, use_container_width=True)
            
            # Délai avant incident
            if 'délai_premier_incident' in filtered_df.columns:
                fig2 = px.box(
                    filtered_df,
                    x='modèle',
                    y='délai_premier_incident',
                    title='Délai avant premier incident (jours)'
                )
                st.plotly_chart(fig2, use_container_width=True)
        
        with tab2:
            # Analyse géographique
            if 'filiale' in filtered_df.columns:
                geo_data = filtered_df.groupby('filiale').agg({
                    'nombre_incidents': 'sum',
                    'no de série': 'count'
                }).rename(columns={'no de série': 'count'}).reset_index()
                
                fig3 = px.choropleth(
                    geo_data,
                    locations='filiale',
                    locationmode='country names',
                    color='nombre_incidents',
                    hover_name='filiale',
                    hover_data=['count'],
                    title='Incidents par Pays/Filiale'
                )
                st.plotly_chart(fig3, use_container_width=True)
                
                # Top 10 pays à problèmes
                st.write("Top 10 filiales avec le plus d'incidents")
                st.dataframe(
                    geo_data.sort_values('nombre_incidents', ascending=False).head(10),
                    hide_index=True
                )
        
        with tab3:
            # Analyse temporelle
            if 'Date de fabrication' in filtered_df.columns:
                time_data = filtered_df.set_index('Date de fabrication').resample('M').agg({
                    'no de série': 'count',
                    'nombre_incidents': 'sum'
                }).rename(columns={'no de série': 'produits_fabriques'})
                
                fig4 = px.line(
                    time_data,
                    y=['produits_fabriques', 'nombre_incidents'],
                    title='Production et Incidents par Mois'
                )
                st.plotly_chart(fig4, use_container_width=True)
        
        # Données détaillées
        st.subheader("Données Détailées")
        st.dataframe(
            filtered_df.sort_values('nombre_incidents', ascending=False),
            column_config={
                "Date de fabrication": st.column_config.DateColumn("Fabriqué le"),
                "date d\'installation": st.column_config.DateColumn("Installé le")
            },
            hide_index=True,
            use_container_width=True
        )
        
    except Exception as e:
        st.error(f"Erreur lors du traitement: {str(e)}")
        st.stop()
else:
    st.info("Veuillez téléverser un fichier Excel pour commencer")
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
with st.expander("🔍 Mode d'emploi"):
    st.markdown("""
    1. **Téléversez** votre fichier Excel via le bouton ci-dessus
    2. **Filtrez** les données par modèle/période dans la sidebar
    3. **Explorez** les onglets pour différentes analyses:
       - Par Produit: comparaison entre modèles
       - Par Zone: répartition géographique
       - Historique: évolution temporelle
    4. **Exportez** les résultats via les options de chaque visualisation
    """)
