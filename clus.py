import streamlit as st
import pandas as pd
import numpy as np
import re
import nltk
import spacy
import subprocess
import sys

# Vérifier si le modèle français est installé, sinon le télécharger
try:
    nlp = spacy.load("fr_core_news_sm")
except OSError:
    subprocess.run([sys.executable, "-m", "spacy", "download", "fr_core_news_sm"])
    nlp = spacy.load("fr_core_news_sm")


from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import hdbscan
import umap.umap_ as umap

from sentence_transformers import SentenceTransformer

import matplotlib.pyplot as plt

# Charger le modèle spacy FR pour lemmatisation
nlp = spacy.load("fr_core_news_sm")

# Charger Sentence-BERT
sbert_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

# Téléchargement stopwords
nltk.download('stopwords')
from nltk.corpus import stopwords
stop_words = set(stopwords.words("french"))

# -----------------------------
# Fonction de nettoyage
# -----------------------------
def preprocess_text(text):
    text = text.lower()
    text = re.sub(r"[^a-zA-Zàâçéèêëîïôûùüÿñæœ\s]", " ", text)
    doc = nlp(text)
    tokens = [token.lemma_ for token in doc if token.text not in stop_words and not token.is_punct]
    return " ".join(tokens)

# -----------------------------
# Fonction de vectorisation
# -----------------------------
def vectorize_texts(texts, method="TF-IDF"):
    if method == "TF-IDF":
        vectorizer = TfidfVectorizer()
        vectors = vectorizer.fit_transform(texts).toarray()
    else:  # Sentence-BERT
        vectors = sbert_model.encode(texts)
    return vectors

# -----------------------------
# Réduction dimension
# -----------------------------
def reduce_dimensions(vectors, method="UMAP"):
    if method == "PCA":
        reducer = PCA(n_components=2)
    else:
        reducer = umap.UMAP(n_neighbors=15, min_dist=0.1, n_components=2, random_state=42)
    reduced = reducer.fit_transform(vectors)
    return reduced

# -----------------------------
# Clustering
# -----------------------------
def cluster_texts(vectors, method="KMeans", n_clusters=5):
    if method == "KMeans":
        model = KMeans(n_clusters=n_clusters, random_state=42)
        labels = model.fit_predict(vectors)
    else:  # HDBSCAN
        model = hdbscan.HDBSCAN(min_cluster_size=5)
        labels = model.fit_predict(vectors)
    return labels

# -----------------------------
# Interface Streamlit
# -----------------------------
st.title("📊 Clustering de Textes (Non Supervisé)")

# Exemple de dataset
default_texts = [
    "L’intelligence artificielle transforme le secteur des assurances.",
    "Le football est un sport très populaire.",
    "Les voitures électriques représentent l’avenir de l’automobile.",
    "Le machine learning permet l’automatisation des processus.",
    "La Coupe du Monde attire des millions de spectateurs.",
    "Les énergies renouvelables sont essentielles pour l’avenir.",
]

user_input = st.text_area("Collez vos textes (un par ligne) :", "\n".join(default_texts))
texts = [preprocess_text(t.strip()) for t in user_input.split("\n") if t.strip()]

# Paramètres
vec_method = st.selectbox("Méthode de vectorisation :", ["TF-IDF", "Sentence-BERT"])
dim_method = st.selectbox("Méthode de réduction de dimension :", ["PCA", "UMAP"])
clust_method = st.selectbox("Algorithme de clustering :", ["KMeans", "HDBSCAN"])

if clust_method == "KMeans":
    n_clusters = st.slider("Nombre de clusters (KMeans uniquement)", 2, 10, 3)
else:
    n_clusters = None

if st.button("🚀 Lancer le clustering"):
    if len(texts) < 2:
        st.warning("Veuillez entrer au moins 2 textes.")
    else:
        # Vectorisation
        vectors = vectorize_texts(texts, method=vec_method)

        # Réduction
        reduced = reduce_dimensions(vectors, method=dim_method)

        # Clustering
        labels = cluster_texts(vectors, method=clust_method, n_clusters=n_clusters if n_clusters else 0)

        # Affichage des résultats
        df = pd.DataFrame({"Texte": texts, "Cluster": labels})
        st.write("### Résultats du clustering")
        st.dataframe(df)

        # Visualisation
        fig, ax = plt.subplots()
        scatter = ax.scatter(reduced[:,0], reduced[:,1], c=labels, cmap="tab10", s=80)
        legend1 = ax.legend(*scatter.legend_elements(), title="Clusters")
        ax.add_artist(legend1)
        st.pyplot(fig)
