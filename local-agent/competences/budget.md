# Analyser les dépenses à partir des relevés bancaires et faire un budget

## 1. Récupérer les relevés
Demande à l'utilisateur d'exporter ses relevés depuis le site de sa banque, idéalement en CSV (ou Excel / PDF),
et de donner le chemin du fichier (souvent dans Téléchargements : list_dir("~/Downloads", "*.csv")).
Lis-les avec read_file (CSV) ou read_document (PDF, Excel). Ne partage jamais ces données ailleurs.

## 2. Classer les opérations (run_python)
Lis le CSV avec le module csv (séparateur souvent « ; », décimales avec virgule, encodage utf-8 ou latin-1).
Catégories : Logement, Courses, Transport, Restaurants & sorties, Abonnements, Santé, Shopping, Loisirs,
Épargne, Revenus, Autres. Classe par mots-clés du libellé (ex : CARREFOUR/LECLERC/LIDL → Courses ;
SNCF/TOTAL/ESSENCE → Transport ; NETFLIX/SPOTIFY/FREE/ORANGE/SFR → Abonnements), puis montre les opérations
« Autres » les plus grosses et demande à l'utilisateur de les classer.

## 3. Rapport
Crée budget/rapport-AAAA-MM.html (write_file puis open_item) avec :
- total des revenus, des dépenses, et le solde du mois ;
- un tableau par catégorie (montant, % des dépenses) et des barres horizontales en HTML/CSS
  (div de largeur proportionnelle) ;
- la liste des abonnements récurrents détectés (même libellé chaque mois) avec leur coût annuel ;
- les 5 plus grosses dépenses.

## 4. Conseils
3 pistes d'économies concrètes et chiffrées (abonnements en doublon, frais bancaires, dépenses en hausse).
Propose un budget mensuel cible par catégorie (méthode 50/30/20 : besoins / envies / épargne) et, si
l'utilisateur le veut, un rappel mensuel avec schedule pour refaire le point.
