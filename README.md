# Tableau de bord des interventions

Cette application Streamlit permet d'explorer les interventions à partir d'un fichier Excel. Elle comporte trois pages principales :

- **Page principale (`app.py`)**
- **Page de statistiques détaillées (`pages/statistiques_detaillees.py`)**
- **Page de statistiques comparatives (`pages/statistiques_comparatives.py`)**

Ci-dessous la liste des graphiques disponibles sur chaque page.

## Page principale

- **Volume annuel** : histogramme du nombre d'interventions par année.
- **Volume mensuel** : histogramme groupé par mois et par année.
- **Répartition prestations** : diagramme circulaire montrant la part de chaque prestation.
- **Statut** / **État de réalisation** : deux graphiques circulaires indiquant la répartition des statuts et des états des interventions.
- **Top 10 Libellé BI** : bar chart des dix libellés de BI les plus fréquents.
- **Top 10 UO** : bar chart des dix UO les plus représentées.
- **Top 10 PRM (classés)** : bar chart classé des dix PRM les plus sollicités.
- **Répartition par Origine** : bar chart de la provenance des demandes.
- **Volume des programmations par jour** : histogramme du nombre de programmations par date.
- **Top 10 Motifs de non réalisation** : bar chart des motifs de non réalisation les plus fréquents.
- **Temps théorique vs réalisé par prestation** : comparaison des temps moyens par prestation.
- **Interventions par arrondissement** : carte choroplèthe localisant les interventions sur Paris.
- Un tableau récapitulatif liste les lignes filtrées.

## Page de statistiques détaillées

Cette page se concentre sur un technicien sélectionné et reprend la plupart des graphiques de la page principale appliqués au filtre courant :

- **Volume annuel** et **Volume mensuel** pour le technicien.
- **Répartition prestations**.
- **Répartition des statuts d'intervention** et **des états de réalisation**.
- **Top 10 motifs de non réalisation**.
- **Top 10 Libellé BI** et **Top 10 PRM** pour le technicien.
- **Répartition par Origine** et **volume des programmations par jour**.
- **Temps théorique vs réalisé par prestation**.
- **Interventions par arrondissement** (carte).
- **Top 10 UO**.
- Un tableau détaille les lignes correspondant au filtre appliqué.

## Page de statistiques comparatives

Cette page permet de comparer un technicien sélectionné avec un ou plusieurs autres agents.
Elle propose les graphiques suivants :

- **Volume annuel comparé** : histogramme comparant le volume du technicien à la moyenne de la sélection.
- **Volume mensuel comparé** : courbe montrant l'évolution du technicien avec les valeurs maximale, minimale et moyenne du groupe.
- **Répartition prestations**, **statuts** et **états** : bar charts comparant la distribution pour le technicien et pour la comparaison.
- **Top 10 motifs de non réalisation**, **Top 10 Libellé BI**, **Top 10 UO** : classements comparatifs.
- **Répartition par Origine** : comparaison de la provenance des demandes.
- **Temps théorique vs réalisé (comparé)** : comparaison des durées moyennes par prestation.
- **Interventions par arrondissement – technicien** et **comparaison** : deux cartes choroplèthes.
- Un tableau récapitule les lignes correspondant au technicien filtré.

Pour utiliser l'application, chargez un fichier Excel via la page principale puis naviguez dans les différentes pages pour explorer les données.
