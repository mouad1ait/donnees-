import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import os
from datetime import datetime

# Configuration de la page
st.set_page_config(
    page_title="Dashboard Analyse Produits",
    page_icon="📊",
    layout="wide"
)

# Fonction de chargement des données avec vérification
@st.cache_data
def load_data():
    try:
        # Essaye plusieurs noms de fichiers courants
        possible_files = [
            "donnees.xlsx",
            "data.xlsx",
            "produits.xlsx",
            "votre_fichier.xlsx"
        ]
        
        for file in possible_files:
            if os.path.exists(file):
                df = pd.read_excel(file)
                
                # Conversion des dates et nettoyage
                date_columns = ['date d\'installation', 'date de premier incident', 'date_fabrication']
                for col in date_columns:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                
                # Calcul du délai de panne si les colonnes existent
                if all(col in df.columns for col in ['date de premier incident', 'date d\'installation']):
                    df['délai_panne'] = (df['date de premier incident'] - df['date d\'installation']).dt.days
                
                return df
        
        st.error("Aucun fichier Excel valide trouvé. Veuillez placer votre fichier dans le même dossier que cette application.")
        return None
        
    except Exception as e:
        st.error(f"Erreur lors du chargement : {str(e)}")
        return None

# Chargement des données
df = load_data()

# Interface principale
st.title("📊 Dashboard d'Analyse des Produits")
st.markdown("""
    Visualisation interactive des données produits avec filtres dynamiques.
    """)

# Sidebar - Filtres
st.sidebar.header("Filtres")

if df is not None:
    # Filtre par modèle
    model_list = sorted(df['modèle'].unique())
    selected_models = st.sidebar.multiselect(
        'Sélectionnez les modèles',
        model_list,
        default=model_list[:2]
    )

    # Filtre par pays
    country_list = sorted(df['filiale'].unique())
    selected_countries = st.sidebar.multiselect(
        'Sélectionnez les pays',
        country_list,
        default=country_list[:2]
    )

    # Filtre par année de fabrication
    if 'date_fabrication' in df.columns:
        min_year = df['date_fabrication'].dt.year.min()
        max_year = df['date_fabrication'].dt.year.max()
        year_range = st.sidebar.slider(
            'Période de fabrication',
            min_year,
            max_year,
            (min_year, max_year)
        )

    # Filtre par nombre d'incidents
    incident_range = st.sidebar.slider(
        'Nombre d\'incidents',
        int(df['nombre d\'incidents'].min()),
        int(df['nombre d\'incidents'].max()),
        (0, int(df['nombre d\'incidents'].max()))
    )

    # Application des filtres
    filtered_df = df[
        (df['modèle'].isin(selected_models)) &
        (df['filiale'].isin(selected_countries)) &
        (df['nombre d\'incidents'].between(*incident_range))
    ]
    
    if 'date_fabrication' in df.columns:
        filtered_df = filtered_df[
            (filtered_df['date_fabrication'].dt.year >= year_range[0]) &
            (filtered_df['date_fabrication'].dt.year <= year_range[1])
        ]

    # Métriques clés
    st.header("Indicateurs Clés")
    col1, col2, col3 = st.columns(3)
    col1.metric("Produits filtrés", len(filtered_df))
    col2.metric("Incidents moyens", round(filtered_df['nombre d\'incidents'].mean(), 1))
    if 'délai_panne' in filtered_df.columns:
        col3.metric("Délai moyen avant incident", f"{round(filtered_df['délai_panne'].mean(), 1)} jours")

    # Onglets pour différentes analyses
    tab1, tab2, tab3 = st.tabs(["📈 Analyse Produit", "🌍 Analyse Géographique", "🔄 Historique"])

    with tab1:
        st.subheader("Performance par Modèle")
        
        # Graphique à barres des incidents par modèle
        fig1 = px.bar(
            filtered_df.groupby('modèle').agg({
                'nombre d\'incidents': 'sum',
                'nombre de retours': 'sum'
            }).reset_index(),
            x='modèle',
            y=['nombre d\'incidents', 'nombre de retours'],
            barmode='group',
            title='Incidents et Retours par Modèle'
        )
        st.plotly_chart(fig1, use_container_width=True)

        # Boxplot des délais de panne
        if 'délai_panne' in filtered_df.columns:
            fig2 = px.box(
                filtered_df,
                x='modèle',
                y='délai_panne',
                title='Distribution des Délais avant Premier Incident'
            )
            st.plotly_chart(fig2, use_container_width=True)

    with tab2:
        st.subheader("Analyse par Pays")
        
        # Carte géographique (si les noms de pays sont valides)
        try:
            country_stats = filtered_df.groupby('filiale').size().reset_index(name='count')
            fig3 = px.choropleth(
                country_stats,
                locations='filiale',
                locationmode='country names',
                color='count',
                hover_name='filiale',
                title='Répartition Géographique des Produits'
            )
            st.plotly_chart(fig3, use_container_width=True)
        except:
            st.warning("Impossible de générer la carte. Vérifiez les noms de pays.")

        # Heatmap des incidents par pays/modèle
        pivot_data = filtered_df.pivot_table(
            index='filiale',
            columns='modèle',
            values='nombre d\'incidents',
            aggfunc='sum'
        ).fillna(0)
        plt.figure(figsize=(10, 6))
        sns.heatmap(pivot_data, annot=True, cmap='YlOrRd')
        st.pyplot(plt)

    with tab3:
        st.subheader("Analyse Temporelle")
        
        # Evolution mensuelle des installations et incidents
        if 'date d\'installation' in filtered_df.columns:
            monthly_data = filtered_df.set_index('date d\'installation').resample('M').agg({
                'numéro de série': 'count',
                'nombre d\'incidents': 'sum'
            }).reset_index()
            
            fig4 = px.line(
                monthly_data,
                x='date d\'installation',
                y=['numéro de série', 'nombre d\'incidents'],
                title='Activité Mensuelle'
            )
            st.plotly_chart(fig4, use_container_width=True)

    # Données brutes
    st.subheader("Données Complètes")
    st.dataframe(filtered_df, height=300, use_container_width=True)

else:
    st.warning("""
        Le chargement des données a échoué. Veuillez :
        1. Vérifier qu'un fichier Excel est présent dans le dossier
        2. Que son nom correspond à l'un de ces formats :
           - donnees.xlsx
           - data.xlsx
           - produits.xlsx
        3. Que le fichier n'est pas corrompu
        """)
