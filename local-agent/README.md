# Jarvis — ton agent IA 100 % local

Un agent autonome qui tourne **sur ton ordinateur**, sans abonnement, sans quota de tokens et sans envoyer tes données sur internet (sauf quand il fait une recherche web).

Il peut :

| Capacité | Outil |
|---|---|
| Lancer n'importe quelle commande (installer, compiler, tester, git…) | `run_command` |
| Lire, créer, modifier des fichiers | `read_file`, `write_file`, `edit_file` |
| Explorer et chercher dans un projet | `list_dir`, `search_files` |
| Chercher sur le web et lire des pages | `web_search`, `fetch_url` |
| Se souvenir de toi entre les sessions | `remember` (fichier `~/.jarvis/memoire.md`) |
| Planifier les tâches longues | `update_plan` |
| Conversations illimitées | résumé automatique quand le contexte se remplit |

## Soyons honnêtes

- **« Sans limite de tokens »** : oui, tu ne paies rien et il n'y a pas de quota. Mais chaque modèle a une *fenêtre de contexte* (sa mémoire de travail, ici 32 000 tokens par défaut). Jarvis la gère en résumant les vieux échanges, ce qui lui permet de travailler aussi longtemps que tu veux.
- **« Les mêmes capacités que Claude »** : les outils, oui. L'intelligence dépend du modèle que tu fais tourner, et donc de ta machine. Un bon modèle local est très capable pour le code et les tâches courantes, mais il reste en dessous des meilleurs modèles cloud sur les tâches les plus difficiles. Plus ta carte graphique est puissante, plus tu peux faire tourner un gros modèle.

## Installation (10 minutes)

### 1. Installer Python 3.9 ou plus
- Windows : https://www.python.org/downloads/. **Coche « Add Python to PATH »** pendant l'installation.
- Mac : `brew install python`, ou le site ci-dessus.
- Linux : c'est généralement déjà installé.

### 2. Installer Ollama (le moteur qui fait tourner le modèle)
Télécharge-le sur https://ollama.com/download, installe-le et lance-le.

### 3. Télécharger un modèle adapté à ta machine
Ouvre un terminal (PowerShell sur Windows) et tape **une** de ces commandes :

| Ta machine | Commande | Remarque |
|---|---|---|
| 8 Go de RAM, pas de GPU | `ollama pull qwen3:4b` | petit mais utilisable |
| 16 Go de RAM ou GPU 8 Go | `ollama pull qwen3:8b` | bon compromis |
| GPU 12-16 Go (RTX 4070/4080…) | `ollama pull qwen3:14b` | **recommandé (par défaut)** |
| GPU 16-24 Go | `ollama pull gpt-oss:20b` ou `ollama pull qwen3-coder:30b` | très bon pour le code |
| GPU 24 Go+ / Mac 64 Go+ | `ollama pull qwen3:32b` ou `ollama pull gpt-oss:120b` | le plus proche des modèles cloud |

> Le modèle doit gérer les **tools** (appels d'outils). C'est le cas de tous ceux listés ici. Liste complète : https://ollama.com/search?c=tools

### 4. Lancer Jarvis
- **Windows** : double-clique sur `jarvis.bat`.
- **Mac/Linux** : `./jarvis.sh`

Ou directement :
```bash
python agent.py                          # mode conversation
python agent.py -m qwen3:8b              # choisir le modèle
python agent.py -d C:\MesProjets\site     # travailler dans un dossier précis
python agent.py "résume les fichiers PDF du dossier"   # tâche directe
```

## Utilisation

Parle-lui normalement :
- « Crée-moi un site vitrine pour un restaurant dans le dossier resto »
- « Trouve pourquoi mon script plante et corrige-le »
- « Cherche les dernières nouveautés de Python et fais-moi un résumé »
- « Range mes fichiers du dossier Téléchargements par type »

Avant chaque commande ou modification de fichier, Jarvis **te demande l'autorisation** :
`o` = oui, `n` = non, `t` = toujours (pour le reste de la session).

Commandes spéciales : `/aide`, `/auto`, `/modele NOM`, `/memoire`, `/resume`, `/nouveau`, `/quitter`.

## Réglages

| Option | Variable d'environnement | Défaut |
|---|---|---|
| `-m` modèle | `JARVIS_MODEL` | `qwen3:14b` |
| `--ctx` taille de contexte | `JARVIS_CTX` | `32768` (augmente-la si tu as beaucoup de VRAM) |
| `--host` adresse d'Ollama | `OLLAMA_HOST` | `http://localhost:11434` |
| `--auto` | – | désactivé : **ne l'active que si tu sais ce que tu fais** |
| `--max-steps` | – | 50 actions par demande |

Les conversations sont enregistrées dans `~/.jarvis/sessions/` et la mémoire dans `~/.jarvis/memoire.md`, que tu peux modifier à la main.

## Sécurité

Jarvis peut exécuter de vraies commandes sur ton ordinateur. Garde le mode confirmation, lis ce qu'il propose avant d'accepter et lance-le dans le dossier de ton projet plutôt qu'à la racine du disque.
