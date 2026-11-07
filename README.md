# GuildByMorricette (GBM) Manager

Application Windows qui relie l'addon World of Warcraft **GuildByMorricette** (WoW Forever) au serveur Discord de la guilde.
Pour le chef de guilde et les officiers, sur le PC où ils jouent.

## ⬇️ Télécharger

**[Dernière version : GBM_Manager.exe](https://github.com/Morricette/GBM-Manager/releases/latest)**

Lancer `GBM_Manager.exe`. Au premier lancement, Windows peut afficher un avertissement
(programme non signé) : « Informations complémentaires », puis « Exécuter quand même ».
Le mode d'emploi complet est dans l'onglet **Aide** de l'application.

Il faut l'addon GuildByMorricette **1.16.0 ou plus** : [CurseForge](https://www.curseforge.com/wow/addons/guildbymorricette).

## Ce qu'elle fait

Trois outils, chacun facultatif :

- **Recensement** : le roster de la guilde (principaux, rerolls, arrivées, départs, pseudos Discord) comparé aux membres
  du serveur. Un message tenu à jour dans un salon privé des officiers, avec la liste complète en fichier CSV.
- **Commandes aux artisans** : chaque commande passée dans l'addon arrive dans un salon Discord en quelques secondes,
  avec la mention de l'artisan visé. L'icône change quand elle est prise 🔨, reçue ✅ ou annulée ❌, puis le message
  est effacé après un délai réglable.
- **Raid-Helper** : chaque composition publiée dans l'addon devient un événement [Raid-Helper](https://raid-helper.dev),
  avec les joueurs déjà placés inscrits d'avance. Les places libres restent ouvertes aux inscriptions sur Discord.

## Comment ça marche

Un addon n'a pas accès à Internet. L'addon écrit dans des fichiers du jeu : le journal du chat (relais en direct)
et le fichier de sauvegarde (à la déconnexion ou au `/reload`). GBM Manager les lit et parle à Discord avec un bot
que vous créez sur votre serveur ([GUIDE-BOT-DISCORD.txt](GUIDE-BOT-DISCORD.txt)).

Les clés (bot Discord, clé API Raid-Helper) restent sur votre PC, chiffrées pour votre session Windows
(`%APPDATA%\GBM-Manager`). Elles ne sont jamais dans ce dépôt.

## Fabriquer le .exe soi-même

Python 3 pour Windows, puis double-clic sur `FABRIQUER-EXE.bat` (le programme est créé dans `dist`).
Chaque version publiée ici est fabriquée automatiquement par GitHub (`.github/workflows/build.yml`).

## Crédits

Idée de **Mekinox** et de la guilde **Mortem In Anima**. Écrit pour GuildByMorricette (Morricette).
Raid-Helper est un bot indépendant, sans lien avec ce projet. Licence GPL-2.0-or-later.
