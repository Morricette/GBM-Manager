"""GuildByMorricette (GBM) Manager - texte de l'onglet Aide (guide pas a pas)."""

LIENS = [
    ("Nouvelles versions (GitHub)", "https://github.com/Morricette/GBM-Manager/releases/latest"),
    ("Portail développeurs Discord", "https://discord.com/developers/applications"),
    ("Inviter Raid-Helper", "https://raid-helper.xyz"),
    ("Discord de l'addon", "https://discord.gg/5fbmYu8cY"),
    ("Addon sur CurseForge", "https://www.curseforge.com/wow/addons/guildbymorricette"),
]

TEXTE = """GUILDBYMORRICETTE (GBM) MANAGER — GUIDE

GBM Manager relie l'addon GuildByMorricette au serveur Discord de la guilde. Il sert au chef de guilde et aux officiers, sur le PC où ils jouent. Trois outils :
  • Recensement : roster de la guilde comparé aux membres du Discord, message tenu à jour dans un salon des officiers (+ fichier CSV).
  • Commandes : les commandes aux artisans apparaissent dans un salon Discord en quelques secondes, avec mention de l'artisan visé, ou du rôle du métier (@Forgeron…) pour une commande à tous ; les commandes terminées sont effacées après un délai.
  • Raid-Helper : chaque événement publié dans l'addon devient un événement Raid-Helper, joueurs déjà inscrits ; les places libres restent ouvertes aux inscriptions sur Discord, et le bot appelle les rôles qui manquent (@Tank, @Soigneur, @Dégâts).

Nouvelles versions : page GitHub de GBM Manager (bouton plus bas), fichier GBM_Manager.exe.

Pourquoi une application ? Un addon n'a pas accès à Internet. Sur le PC du relais, l'addon affiche une fine bande de couleurs en haut à gauche de l'écran du jeu : GBM Manager la lit à l'écran et parle à Discord. Le fichier de sauvegarde, écrit à chaque /reload ou déconnexion, sert au recensement et au rattrapage.


ÉTAPE 1 — LE BOT DISCORD (un administrateur du serveur, une seule fois)
  1. Portail des développeurs Discord (bouton plus bas) : « New Application », nom « GBM Manager ».
  2. Onglet Bot : activer « Server Members Intent », enregistrer. Décocher « Bot public ».
     « Réinitialiser le token », « Copier » : c'est la CLÉ DU BOT. Elle est secrète : collez-la seulement ici.
  3. Onglet OAuth2, générateur d'URL : cocher « bot », puis les droits :
     Voir les salons, Envoyer des messages, Intégrer des liens, Joindre des fichiers, Gérer les messages,
     Lire l'historique des messages (depuis 1.2.0 : pour éviter les doublons entre officiers).
     Ouvrir l'adresse, choisir le serveur, « Autoriser ».
  4. Créer les salons : un salon privé des officiers (recensement), un salon des commandes (visible de ceux
     qui doivent les voir), un salon des événements (Raid-Helper). Le bot doit pouvoir y écrire.
  5. Discord, Paramètres > Avancés : activer « Mode développeur ». Clic droit sur le serveur ou un salon :
     « Copier l'identifiant ».

ÉTAPE 2 — RAID-HELPER (facultatif)
  1. Site officiel raid-helper.xyz : « Invite Bot », choisir le serveur.
     ATTENTION aux faux bots au nom proche (« RaidHelper » sans tiret...) : le vrai s'appelle Raid-Helper
     et n'a pas de commandes de points ni d'avertissements. Salon des événements privé : lui donner le droit d'y écrire.
  2. Un administrateur tape /apikey dans Discord et choisit la commande dans la liste : la CLÉ API du serveur
     s'affiche. Elle est secrète.
  3. Modèle (facultatif) : vide = le modèle « WoW: Forever » de Raid-Helper (n° 47), qui affiche la classe et la
     spécialisation de chaque joueur (Tank, Melee, Ranged, Healer). Un autre numéro : un autre modèle.
  4. Pour que Raid-Helper crée aussi l'événement Discord du serveur : lui donner le droit « Créer des événements »
     (sinon il le signale dans un message, sans gêner le reste).

ÉTAPE 3 — DANS LE JEU (chef de guilde ou officier)
  1. Addon GuildByMorricette 1.16.0 ou plus.
  2. /mg recensement : onglet Recensement de la fenêtre Guilde. Cocher « Relais Discord sur ce PC ».
     Jouer en mode fenêtré ou plein écran fenêtré (pas en plein écran exclusif), sans fenêtre sur le coin haut gauche du jeu.
  3. Taper /reload une fois : le jeu écrit le fichier de sauvegarde lu par GBM Manager.
  4. Tous les membres : donner leur pseudo Discord (onglet Recensement, ou /mg discord Pseudo).

ÉTAPE 4 — DANS GBM MANAGER (onglet Réglages)
  1. Fichier de sauvegarde : trouvé tout seul (sinon « Parcourir… »).
     <jeu>\\_forever_\\WTF\\Account\\<COMPTE>\\SavedVariables\\GuildeForever.lua
  2. Coller la clé du bot et l'identifiant du serveur.
  3. Coller l'identifiant de chaque salon voulu (laisser vide un outil qu'on n'utilise pas).
  4. Commandes : délai avant d'effacer une commande reçue ou annulée, mention de l'artisan visé, mention du rôle
     du métier pour une commande à tous (rôles Alchimiste, Forgeron, Enchanteur, Ingénieur, Travailleur du cuir,
     Tailleur, Mineur, Cuisinier, Secouriste sur le serveur ; addon 1.16.2 ou plus).
  5. Raid-Helper : clé API, identifiant du salon des événements, modèle et organisateur (facultatifs ; sans
     organisateur reconnu, le propriétaire du serveur est noté organisateur). Case « Appeler les rôles qui
     manquent » : rôles Tank, Soigneur, Dégâts du serveur ; le bot doit pouvoir écrire dans le salon des événements.
     Repères : 1 tank et 1 soigneur en donjon ; sinon 1 tank pour 10 joueurs et 1 soigneur pour 4.
  6. « Enregistrer », puis « Tester ». Laisser GBM Manager ouvert pendant que vous jouez.
     Case « Lancer GBM Manager au démarrage de Windows » : l'application s'ouvre toute seule, cachée près de
     l'horloge (flèche ^ en bas à droite de l'écran), et attend que le jeu soit lancé. Plus besoin d'y penser.
     La croix de la fenêtre la cache sans l'arrêter : clic droit sur son icône, « Ouvrir » ou « Quitter ».
  En jeu, /mg relais test affiche un message d'essai dans la bande de couleurs : il doit apparaître dans l'onglet Journal.

PLUSIEURS OFFICIERS EN MÊME TEMPS (1.2.0, addon 1.16.2)
  Chaque officier peut installer GBM Manager et cocher « Relais Discord sur ce PC » : pas de doublons.
  • Dans le jeu, un seul relais principal affiche la bande de couleurs (rang le plus haut, puis ordre
    alphabétique) ; les autres restent en réserve et prennent la main s'il se déconnecte. /mg relais etat.
  • Avant de publier, GBM Manager regarde si un autre officier a déjà publié la même commande, le même
    événement ou le même recensement (étiquette « réf. » discrète sur chaque message), et reprend ce message.
  • Tous les officiers utilisent le même bot : chacun colle la même clé du bot (et la même clé Raid-Helper).
    Le chef de guilde décide à qui il les donne ; si une clé fuit, il la régénère et redonne la nouvelle.

CE QUI SE PASSE ENSUITE
  • Commandes et événements : publiés quelques secondes après chaque changement en jeu (bande de couleurs).
  • Recensement : mis à jour à chaque /reload ou déconnexion (le même message est modifié).
  • À chaque /reload ou déconnexion, GBM Manager rattrape aussi tout ce qui aurait été manqué.

DÉPANNAGE
  • « Clé refusée » : recopier la clé du bot (Discord) ou la clé API (/apikey, Raid-Helper).
  • « Accès refusé » : donner au bot les droits dans le salon, activer « Server Members Intent ».
  • Les commandes n'arrivent qu'au /reload : vérifier « Relais Discord sur ce PC » en jeu, puis /mg relais test.
  • Un joueur pas reconnu sur Discord : il doit donner son pseudo (/mg discord Pseudo), identique à son nom
    d'utilisateur ou à son nom sur le serveur (majuscules, accents, espaces, points et tirets ignorés).
  • Windows avertit au lancement (programme non signé) : « Informations complémentaires », « Exécuter quand même ».

SÉCURITÉ
  Les clés sont enregistrées chiffrées pour votre session Windows (dossier %APPDATA%\\GBM-Manager). Ne les
  donnez à personne. Si une clé a fuité : la régénérer (portail Discord, ou /apikey sur Raid-Helper).

Idée de Mekinox et de la guilde Mortem In Anima. Écrit pour GuildByMorricette (Morricette), licence GPL.
"""
