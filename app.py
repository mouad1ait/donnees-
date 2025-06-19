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

# Fonctions d'analyse
def calculate_time_to_failure(df, installation_date_col, failure_date_col):
    df[installation_date_col] = pd.to_datetime(df[installation_date_col])
    df[failure_date_col] = pd.to_datetime(df[failure_date_col])
    df['Time to Failure (jours)'] = (df[failure_date_col] - df[installation_date_col]).dt.days
    return df

def calculate_age_from_installation(df, installation_date_col, reference_date=None):
    df[installation_date_col] = pd.to_datetime(df[installation_date_col])
    if reference_date is None:
        reference_date = datetime.now()
    else:
        reference_date = pd.to_datetime(reference_date)
    df['Age depuis installation (jours)'] = (reference_date - df[installation_date_col]).dt.days
    return df

def generate_statistics(df, sheet_name):
    stats = {}
    stats["Nom de la feuille"] = sheet_name
    stats["Nombre d'enregistrements"] = len(df)
    
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in df.columns:
        if col in numeric_cols:
            stats[f"{col} - Moyenne"] = df[col].mean()
            stats[f"{col} - Médiane"] = df[col].median()
            stats[f"{col} - Écart-type"] = df[col].std()
        else:
            stats[f"{col} - Valeurs uniques"] = df[col].nunique()
            stats[f"{col} - Top valeur"] = df[col].mode()[0] if not df[col].empty else None
    
    return stats

def create_pdf_report(dataframes, analyses, figures):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Ajouter une page de titre
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, "Rapport d'analyse des données machines", 0, 1, 'C')
    pdf.ln(10)
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, f"Généré le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, 'C')
    pdf.ln(20)
    
    # Ajouter le contenu pour chaque feuille
    for sheet_name in dataframes.keys():
        pdf.add_page()
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, f"Feuille: {sheet_name}", 0, 1)
        pdf.ln(5)
        
        # Statistiques
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, "Statistiques:", 0, 1)
        pdf.set_font('Arial', '', 10)
        
        stats = analyses[sheet_name]
        for key, value in stats.items():
            if pd.isna(value):
                value = "N/A"
            pdf.cell(0, 6, f"{key}: {value}", 0, 1)
        
        pdf.ln(10)
        
        # Graphiques
        if sheet_name in figures:
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, "Graphiques:", 0, 1)
            
            for fig in figures[sheet_name]:
                img_path = f"temp_{sheet_name}.png"
                fig.savefig(img_path, bbox_inches='tight')
                pdf.image(img_path, x=10, w=190)
                pdf.ln(5)
    
    # Sauvegarder le PDF
    pdf_output = "rapport_analyse_machines.pdf"
    pdf.output(pdf_output)
    return pdf_output

# Interface Streamlit
st.title("Analyse des données machines")

uploaded_file = st.file_uploader("Télécharger le fichier Excel", type=["xlsx", "xls"])

if uploaded_file is not None:
    data = load_data(uploaded_file)
    analyses = {}
    figures = {}
    
    # Sélection de la feuille à afficher
    sheet_names = list(data.keys())
    selected_sheet = st.sidebar.selectbox("Sélectionner une feuille", sheet_names)
    
    if selected_sheet:
        df = data[selected_sheet].copy()
        
        # Affichage des données
        st.header(f"Feuille: {selected_sheet}")
        st.dataframe(df.head())
        
        # Calculs spécifiques selon la feuille
        if selected_sheet == "RMA machines":
            df = calculate_time_to_failure(df, "date d'installation", "date rma")
            df = calculate_age_from_installation(df, "date d'installation")
            st.dataframe(df[['modèle', 'no de série', 'Time to Failure (jours)', 'Age depuis installation (jours)']].head())
        
        if selected_sheet == "incidents":
            df = calculate_time_to_failure(df, "date d'installation", "date incident")
            df = calculate_age_from_installation(df, "date d'installation")
            st.dataframe(df[['modèle', 'no de série', 'Time to Failure (jours)', 'Age depuis installation (jours)']].head())
        
        # Analyse statistique
        st.subheader("Statistiques descriptives")
        stats = generate_statistics(df, selected_sheet)
        analyses[selected_sheet] = stats
        
        # Affichage des statistiques
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Métriques de base:**")
            st.write(f"Nombre d'enregistrements: {stats['Nombre d'enregistrements']}")
            
            for col in df.columns:
                if f"{col} - Valeurs uniques" in stats:
                    st.write(f"{col}: {stats[f'{col} - Valeurs uniques']} valeurs uniques")
        
        with col2:
            st.write("**Valeurs numériques:**")
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                st.write(f"{col}:")
                st.write(f"- Moyenne: {stats.get(f'{col} - Moyenne', 'N/A')}")
                st.write(f"- Médiane: {stats.get(f'{col} - Médiane', 'N/A')}")
        
        # Visualisations
        st.subheader("Visualisations")
        figs = []
        
        # Graphique 1: Répartition par modèle
        fig, ax = plt.subplots()
        df['modèle'].value_counts().plot(kind='bar', ax=ax)
        ax.set_title(f"Répartition par modèle - {selected_sheet}")
        st.pyplot(fig)
        figs.append(fig)
        
        # Graphique 2: Répartition par filiale si disponible
        if 'filiale' in df.columns:
            fig2, ax2 = plt.subplots()
            df['filiale'].value_counts().plot(kind='bar', ax=ax2)
            ax2.set_title(f"Répartition par filiale - {selected_sheet}")
            st.pyplot(fig2)
            figs.append(fig2)
        
        # Graphique 3: Time to Failure si disponible
        if 'Time to Failure (jours)' in df.columns:
            fig3, ax3 = plt.subplots()
            df['Time to Failure (jours)'].plot(kind='hist', bins=20, ax=ax3)
            ax3.set_title(f"Distribution du Time to Failure - {selected_sheet}")
            st.pyplot(fig3)
            figs.append(fig3)
        
        figures[selected_sheet] = figs
    
    # Bouton pour générer le rapport PDF
    if st.button("Générer le rapport PDF"):
        with st.spinner("Création du rapport..."):
            pdf_path = create_pdf_report(data, analyses, figures)
            
            with open(pdf_path, "rb") as f:
                base64_pdf = base64.b64encode(f.read()).decode('utf-8')
            
            pdf_display = f'<a href="data:application/pdf;base64,{base64_pdf}" download="rapport_analyse_machines.pdf">Télécharger le rapport PDF</a>'
            st.markdown(pdf_display, unsafe_allow_html=True)
else:
    st.info("Veuillez télécharger un fichier Excel pour commencer l'analyse.")
