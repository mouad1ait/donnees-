import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
import base64
from datetime import datetime

# Configuration de la page
st.set_page_config(layout="wide", page_title="Analyse des données machines")

# Fonction pour charger les données
@st.cache_data
def load_data(uploaded_file):
    if uploaded_file is not None:
        xls = pd.ExcelFile(uploaded_file)
        sheets = {}
        for sheet_name in xls.sheet_names:
            sheets[sheet_name] = pd.read_excel(xls, sheet_name=sheet_name)
        return sheets
    return None

# Fonctions de calcul TTF et âge
def calculate_metrics(df, date_col, event_date_col):
    df[date_col] = pd.to_datetime(df[date_col])
    df[event_date_col] = pd.to_datetime(df[event_date_col])
    
    # Calcul du Time To Failure (en jours)
    df['TTF (jours)'] = (df[event_date_col] - df[date_col]).dt.days
    
    # Calcul de l'âge depuis installation (en jours)
    df['Age (jours)'] = (pd.to_datetime('today') - df[date_col]).dt.days
    
    # Calcul du taux de défaillance (1/TTF)
    df['Taux défaillance (1/jour)'] = 1 / df['TTF (jours)']
    
    return df

def generate_statistics(df):
    stats = {}
    
    # Statistiques de base
    stats["Nombre total"] = len(df)
    stats["Première date"] = df['date d\'installation'].min().strftime('%Y-%m-%d')
    stats["Dernière date"] = df['date d\'installation'].max().strftime('%Y-%m-%d')
    
    # Statistiques par modèle
    model_stats = df.groupby('modèle').agg({
        'no de série': 'count',
        'TTF (jours)': ['mean', 'median', 'std'],
        'Age (jours)': 'mean'
    })
    stats["Par modèle"] = model_stats
    
    return stats

# Interface Streamlit
st.title("📊 Analyse des données machines")
uploaded_file = st.file_uploader("Télécharger le fichier Excel", type=["xlsx", "xls"])

if uploaded_file is not None:
    data = load_data(uploaded_file)
    
    # Onglets pour chaque feuille
    tabs = st.tabs(list(data.keys()))
    
    for tab, (sheet_name, df) in zip(tabs, data.items()):
        with tab:
            st.header(f"Feuille: {sheet_name}")
            
            # Calculs spécifiques
            if sheet_name in ["RMA machines", "incidents"]:
                date_col = "date d'installation"
                event_col = "date rma" if sheet_name == "RMA machines" else "date incident"
                df = calculate_metrics(df, date_col, event_col)
            
            # Affichage des données
            with st.expander("Afficher les données brutes"):
                st.dataframe(df)
            
            # Statistiques descriptives
            st.subheader("📈 Statistiques descriptives")
            
            if sheet_name in ["RMA machines", "incidents"]:
                # Affichage des métriques TTF
                col1, col2, col3 = st.columns(3)
                with col1:
                    avg_ttf = df['TTF (jours)'].mean()
                    st.metric("MTTF (jours)", f"{avg_ttf:.1f}")
                
                with col2:
                    median_ttf = df['TTF (jours)'].median()
                    st.metric("Mediane TTF (jours)", f"{median_ttf:.1f}")
                
                with col3:
                    failure_rate = df['Taux défaillance (1/jour)'].mean()
                    st.metric("Taux de défaillance moyen", f"{failure_rate:.6f}")
            
            # Répartition par modèle
            st.subheader("📋 Répartition par modèle")
            
            model_dist = df['modèle'].value_counts().reset_index()
            model_dist.columns = ['Modèle', 'Nombre']
            
            col1, col2 = st.columns([2, 3])
            with col1:
                st.dataframe(model_dist)
            
            with col2:
                fig, ax = plt.subplots()
                model_dist.plot(kind='bar', x='Modèle', y='Nombre', ax=ax, legend=False)
                ax.set_title("Distribution par modèle")
                ax.set_ylabel("Nombre d'occurrences")
                st.pyplot(fig)
            
            # Répartition par filiale
            if 'filiale' in df.columns:
                st.subheader("🏢 Répartition par filiale")
                filiale_dist = df['filiale'].value_counts().reset_index()
                filiale_dist.columns = ['Filiale', 'Nombre']
                st.dataframe(filiale_dist)
            
            # Téléchargement des résultats
            st.download_button(
                label="Télécharger les résultats",
                data=df.to_csv(index=False).encode('utf-8'),
                file_name=f"resultats_{sheet_name}.csv",
                mime="text/csv"
            )

else:
    st.info("Veuillez télécharger un fichier Excel pour commencer l'analyse.")
