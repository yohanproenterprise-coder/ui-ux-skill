# Rédiger un CV et une lettre de motivation professionnels

## 1. Recueillir les informations (pose les questions, une série à la fois)
- Poste visé et entreprise (si l'utilisateur colle l'annonce ou un lien, lis-la avec fetch_url).
- Identité : nom, ville, téléphone, e-mail, (LinkedIn, permis, mobilité).
- Expériences : poste, entreprise, dates, 2 ou 3 réalisations concrètes chacune (avec des chiffres si possible).
- Formation, compétences techniques, langues (avec niveau), centres d'intérêt pertinents.
Enregistre les informations durables avec remember (pour ne pas les redemander la prochaine fois).
Si un ancien CV existe (Word ou PDF), lis-le avec read_document.

## 2. CV (1 page)
- Titre = le poste visé. Accroche de 2 lignes adaptée à l'annonce.
- Expériences de la plus récente à la plus ancienne ; verbes d'action ; résultats chiffrés.
- Reprends les mots-clés de l'annonce (les recruteurs et leurs logiciels les cherchent).
- Pas de photo sauf demande ; pas de faute : relis tout.
- Mise en page sobre en deux colonnes (colonne gauche colorée : contact, compétences, langues).

## 3. Lettre de motivation (moins d'une page)
Structure « vous / moi / nous » : ce que je sais de l'entreprise et du poste → ce que j'apporte (2 exemples
concrets) → ce que nous ferons ensemble + demande d'entretien. Ton sincère, pas de phrases toutes faites.

## 4. Fichiers
Produis les deux documents en PDF avec la méthode de la compétence document-pdf (use_skill("document-pdf")),
dans documents/CV-NOM.pdf et documents/Lettre-ENTREPRISE.pdf, puis ouvre-les.
Propose aussi une version courte de la lettre pour un e-mail de candidature.
