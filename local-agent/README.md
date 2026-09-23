# Jarvis : ton agent IA personnel

Jarvis est un assistant autonome installé **sur ton PC**. Tu lui dis ce que tu veux, il **agit** : il crée des fichiers et des sites, lance des programmes, cherche sur internet, lit tes documents, regarde ton écran, te parle et t'écoute.

## Installation (Windows, 15 à 30 minutes)

1. **Télécharge Jarvis** : https://github.com/yohanproenterprise-coder/ui-ux-skill/archive/refs/heads/claude/quirky-euler-dtsd45.zip
2. Fais un clic droit sur le ZIP → **Extraire tout**, puis ouvre le dossier `local-agent`.
3. Double-clique sur **`INSTALLER.bat`**. S'il s'affiche, clique sur « Informations complémentaires » → « Exécuter quand même » dans l'avertissement Windows.
   L'installateur s'occupe de tout : Python, Ollama, les modèles d'IA (environ 6 Go), la lecture des PDF et les raccourcis sur le Bureau.
4. Quand il te le propose, **colle une clé Gemini gratuite** (vivement conseillé, voir ci-dessous).
5. Lance Jarvis avec l'icône **Jarvis** du Bureau. L'interface s'ouvre dans ton navigateur.

## Tes deux cerveaux (important pour ton PC)

Ton ordinateur (i5 de portable, 8 Go de RAM, pas de carte graphique dédiée) peut faire tourner une IA locale, mais **seulement une petite, et lentement** (quelques mots par seconde, et 1 à 2 minutes pour la toute première réponse). Jarvis a donc deux cerveaux :

| | Cerveau **local** (`qwen3:4b`) | Cerveau **cloud gratuit** (Gemini Flash) |
|---|---|---|
| Coût | 0 € | 0 € (quota gratuit quotidien) |
| Limite | aucune | nombre de requêtes par jour et par minute |
| Vitesse sur ton PC | lent | très rapide |
| Intelligence | correcte pour les tâches simples | bien meilleure (code, raisonnement, gros documents) |
| Confidentialité | tout reste sur ton PC | les messages passent par Google |
| Internet | pas nécessaire (sauf pour la recherche web) | nécessaire |

**Réglage conseillé :** Gemini comme cerveau principal et le local en secours. Si le quota gratuit est épuisé ou si internet est coupé, Jarvis **bascule tout seul sur le local**. Tu as ainsi le meilleur des deux, sans jamais être bloqué.

Clé Gemini gratuite : https://aistudio.google.com/apikey (connexion avec un compte Google, bouton « Create API key »).
Autres cerveaux gratuits possibles : Groq (https://console.groq.com/keys, extrêmement rapide) et OpenRouter (https://openrouter.ai/settings/keys).
Ajoute une clé avec le bouton **Clés** de l'interface, puis choisis le cerveau dans le menu en haut.

## Ce que Jarvis sait faire

| Capacité | Exemple de demande |
|---|---|
| Commandes Windows (PowerShell) | « Quelle place reste-t-il sur mon disque ? Trouve les 20 plus gros fichiers » |
| Programmer et exécuter du Python | « Fais-moi un script qui renomme mes photos par date » |
| Créer et modifier des fichiers | « Crée un site vitrine pour une boulangerie dans le dossier boulangerie » |
| Lire des documents PDF, Word, Excel, PowerPoint | « Résume le PDF facture.pdf » |
| Chercher sur le web et lire des pages | « Quelles sont les nouveautés de Windows cette année ? » |
| Voir des images (📎 ou copier-coller) | « Qu'est-ce qui ne va pas sur cette capture ? » |
| Regarder ton écran | « Regarde mon écran et dis-moi ce que signifie ce message d'erreur » |
| Ouvrir des applications, sites, dossiers | « Ouvre Excel » / « Ouvre YouTube » |
| Presse-papiers | « Traduis en anglais ce que j'ai copié et remets-le dans le presse-papiers » |
| Voix : parler et écouter | bouton 🎤 et bouton « Voix » |
| **Piloter souris et clavier** | « Ouvre le Bloc-notes, écris une liste de courses et enregistre-la sur le Bureau » |
| **Rappels et notifications** | « Rappelle-moi dans 20 minutes de sortir le linge » |
| **Tâches automatiques** | « Chaque matin à 8h, résume-moi l'actualité et enregistre-la dans un fichier » |
| **Base de connaissances** | « Indexe mon dossier Documents » puis « Quel est mon numéro de contrat d'assurance ? » |
| **Création d'images** | « Crée une image d'un chat astronaute style aquarelle » |
| **Compétences apprises** | « Apprends cette méthode pour faire mes factures : … » (il la réutilisera ensuite) |
| Mémoire entre les sessions | « Retiens que je m'appelle … et que je travaille sur … » |
| Plans pour les grosses tâches | il affiche et coche les étapes au fur et à mesure |
| Sous-agents | il confie les longues recherches à un assistant secondaire |
| Conversations sans fin | il résume automatiquement les vieux échanges |

Jarvis travaille par défaut dans le dossier `C:\Users\<toi>\Jarvis`. Il peut aussi accéder à tout autre dossier si tu lui donnes le chemin.

Bon à savoir :
- Les rappels et tâches programmées ne se déclenchent que **quand Jarvis est ouvert**. Pour les tâches automatiques, utilise l'interface web.
- Le pilotage souris/clavier marche mieux avec un cerveau cloud (Gemini) : le petit modèle local ne l'utilise pas.
- La création d'images passe par le service gratuit Pollinations (internet requis).

## Mettre à jour Jarvis

Clique sur **Mise à jour** en haut de l'interface (ou tape `/maj` dans le terminal), puis ferme et relance Jarvis. Tes réglages, tes clés, ta mémoire et tes compétences sont conservés.

## Sécurité

Avant chaque commande, modification de fichier ou téléchargement, Jarvis **te demande l'autorisation** : *Autoriser*, *Refuser* ou *Toujours autoriser* (pour la session en cours).
Le bouton **Auto** supprime toutes les confirmations. Ne l'active que si tu sais ce que tu fais, car une IA peut se tromper.
L'interface web n'est accessible que depuis ton PC, pas depuis le réseau.

## Mode terminal

Raccourci **« Jarvis (terminal) »**. Commandes : `/aide`, `/voix`, `/parole`, `/auto`, `/cerveau gemini`, `/cerveau local`, `/modele NOM`, `/cle gemini TA_CLE`, `/memoire`, `/reprendre`, `/nouveau`, `/quitter`.

Tu peux aussi l'utiliser en ligne de commande :
```
python agent.py "range les fichiers de mon dossier Téléchargements par type"
python agent.py --web                 # interface web
python agent.py -c local -m qwen3:1.7b  # modèle local plus petit et plus rapide
```

## Réglages avancés

Tous les réglages sont dans `C:\Users\<toi>\.jarvis\config.json` :
- `provider` : cerveau principal ; `fallback` : cerveau de secours.
- `providers.local.model` : le modèle local. Sur ton PC : `qwen3:4b` (conseillé), `qwen3:1.7b` (plus rapide, moins intelligent). Installe un modèle avec `ollama pull NOM`.
- `providers.local.ctx` : mémoire de travail du modèle local en tokens (8192 ; ne dépasse pas 12288 avec 8 Go de RAM).
- `providers.gemini.model` : `gemini-3.6-flash` (tu peux le changer avec le bouton « Modèle »).
- `workdir` : dossier de travail ; `max_steps` : nombre maximal d'actions par demande.

La mémoire à long terme est dans `.jarvis\memoire.md` (modifiable à la main) et les conversations dans `.jarvis\sessions\`.

## Si ça ne marche pas

- **« Ollama ne répond pas »** : lance « Ollama » depuis le menu Démarrer (une icône de lama apparaît près de l'horloge).
- **« Modèle absent »** : ouvre PowerShell et tape `ollama pull qwen3:4b`.
- **Le local est très lent** : c'est normal sur ce PC. Ferme Chrome et les autres gros programmes (le modèle a besoin d'environ 4 Go de RAM libre), passe à `qwen3:1.7b` ou utilise Gemini.
- **Le micro ne marche pas** : dans l'interface web, utilise Microsoft Edge ou Chrome et autorise le micro. En mode terminal, il faut la reconnaissance vocale Windows en français (Paramètres → Heure et langue → Voix).
- **Nom de modèle cloud refusé** : les fournisseurs renomment parfois leurs modèles. Vérifie le nom sur leur site et change-le avec `/modele NOM`.
