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
     Lire l'historique des messages (pour éviter les doublons entre officiers).
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

NOUVEAU EN 1.2.1
  • Rappel des inscrits : avant le départ d'un événement (60 minutes par défaut, réglable), le bot mentionne les
    joueurs inscrits sur Raid-Helper sous l'événement ; le message s'efface 3 heures après le départ.
  • Nouvelles versions : GBM Manager regarde sur GitHub au démarrage puis toutes les 6 heures, et s'installe tout seul
    si la case est cochée (il se ferme, se met à jour et se relance). Bouton « Nouvelle version ? » pour vérifier.
  • Langue : français ou anglais (réglage « Langue / Language », au prochain lancement). Les messages publiés sur
    Discord suivent la même langue. Rôles anglais reconnus aussi : Tank, Healer, DPS, Alchemist, Blacksmith…

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


LIENS_EN = [
    ("New versions (GitHub)", "https://github.com/Morricette/GBM-Manager/releases/latest"),
    ("Discord developer portal", "https://discord.com/developers/applications"),
    ("Invite Raid-Helper", "https://raid-helper.xyz"),
    ("Addon Discord", "https://discord.gg/5fbmYu8cY"),
    ("Addon on CurseForge", "https://www.curseforge.com/wow/addons/guildbymorricette"),
]

TEXTE_EN = """GUILDBYMORRICETTE (GBM) MANAGER — GUIDE

GBM Manager links the GuildByMorricette addon with your guild's Discord server. It is for the guild master and the officers, on the PC they play on. Three tools:
  • Census: the guild roster compared with the Discord members, a message kept up to date in an officers' channel (+ CSV file).
  • Orders: crafting orders show in a Discord channel within seconds, mentioning the targeted crafter, or the profession role (@Blacksmith…) for an order to everyone; finished orders are deleted after a delay.
  • Raid-Helper: every event published in the addon becomes a Raid-Helper event with the players already signed up; free spots stay open for sign-ups on Discord, and the bot calls the missing roles (@Tank, @Healer, @DPS).

New versions: GBM Manager's GitHub page (button above), file GBM_Manager.exe.

Why an app? An addon has no Internet access. On the relay PC, the addon shows a thin band of colours at the top left of the game screen: GBM Manager reads it on screen and talks to Discord. The saved variables file, written on every /reload or logout, is used for the census and to catch up.


STEP 1 — THE DISCORD BOT (a server administrator, once)
  1. Discord developer portal (button above): "New Application", name "GBM Manager".
  2. Bot tab: turn on "Server Members Intent", save. Untick "Public Bot".
     "Reset Token", "Copy": this is the BOT TOKEN. It is secret: paste it only here.
  3. OAuth2 tab, URL generator: tick "bot", then the permissions:
     View Channels, Send Messages, Embed Links, Attach Files, Manage Messages,
     Read Message History (to avoid duplicates between officers).
     Open the link, pick the server, "Authorize".
  4. Create the channels: a private officers' channel (census), an orders channel (visible to those who
     need it), an events channel (Raid-Helper). The bot must be able to write in them.
  5. Discord, Settings > Advanced: turn on "Developer Mode". Right-click the server or a channel:
     "Copy ID".

STEP 2 — RAID-HELPER (optional)
  1. Official site raid-helper.xyz: "Invite Bot", pick the server.
     BEWARE of fake bots with a similar name ("RaidHelper" without a hyphen...): the real one is called Raid-Helper.
     Private events channel: give it permission to write there.
  2. An administrator types /apikey in Discord and picks the command from the list: the server's API KEY
     shows. It is secret.
  3. Template (optional): empty = Raid-Helper's "WoW: Forever" template (no. 47), which shows each player's class
     and spec (Tank, Melee, Ranged, Healer). Another number: another template.
  4. For Raid-Helper to also create the server's Discord event: give it the "Create Events" permission
     (otherwise it says so in a message, without blocking anything else).

STEP 3 — IN GAME (guild master or officer)
  1. GuildByMorricette addon 1.16.2 or later.
  2. /mg census: Census tab of the Guild window. Tick "Discord relay on this PC".
     Play in windowed or windowed fullscreen mode (not exclusive fullscreen), with nothing over the game's top left corner.
  3. Type /reload once: the game writes the saved variables file that GBM Manager reads.
  4. All members: give their Discord name (Census tab, or /mg discord Name).

STEP 4 — IN GBM MANAGER (Settings tab)
  1. Saved variables file: found automatically (otherwise "Browse…").
     <game>\\_forever_\\WTF\\Account\\<ACCOUNT>\\SavedVariables\\GuildeForever.lua
  2. Paste the bot token and the server ID.
  3. Paste the ID of each channel you want (leave a tool you don't use empty).
  4. Orders: delay before deleting a received or cancelled order, mention of the targeted crafter, mention of the
     profession role for an order to everyone (Alchemist, Blacksmith, Enchanter, Engineer, Leatherworker, Tailor,
     Miner, Cook, First Aid roles on the server; French role names work too).
  5. Raid-Helper: API key, events channel ID, template and organiser (optional; without a recognised organiser,
     the server owner is set as organiser). "Call the missing roles" box: Tank, Healer, DPS roles on the server.
     Guideline: 1 tank and 1 healer in a dungeon; otherwise 1 tank per 10 players and 1 healer per 4.
     "Remind signed-up players" box: the bot mentions them before the start (60 minutes by default).
  6. "Save", then "Test". Keep GBM Manager running while you play.
     "Start GBM Manager with Windows" box: the app opens on its own, hidden next to the clock (^ arrow at the
     bottom right of the screen), and waits for the game to start.
     The window's X hides it without stopping it: right-click its icon, "Open" or "Quit".
  In game, /mg relay test shows a test message in the colour band: it must appear in the Log tab.

SEVERAL OFFICERS AT THE SAME TIME
  Every officer can install GBM Manager and tick "Discord relay on this PC": no duplicates.
  • In game, only one main relay shows the colour band (highest rank, then alphabetical order); the others stay
    on standby and take over if it logs out. /mg relay status.
  • Before posting, GBM Manager checks whether another officer already posted the same order, event or census
    (a discreet "réf." label on each message), and reuses that message.
  • All officers use the same bot: each pastes the same bot token (and the same Raid-Helper key).
    The guild master decides who gets them; if a key leaks, regenerate it and hand out the new one.

UPDATES AND LANGUAGE
  • GBM Manager checks GitHub at start-up and every 6 hours, and installs new versions on its own if the box is ticked
    (it closes, updates and restarts). "New version?" button to check now.
  • Language: French or English ("Langue / Language" setting, next time the app starts). Messages posted on
    Discord follow the same language.

WHAT HAPPENS NEXT
  • Orders and events: posted a few seconds after each change in game (colour band).
  • Census: updated on every /reload or logout (the same message is edited).
  • On every /reload or logout, GBM Manager also catches up on anything it missed.

TROUBLESHOOTING
  • "Token refused": copy the bot token (Discord) or the API key (/apikey, Raid-Helper) again.
  • "Access denied": give the bot its permissions in the channel, turn on "Server Members Intent".
  • Orders only arrive on /reload: check "Discord relay on this PC" in game, then /mg relay test.
  • A player is not recognised on Discord: they must give their name (/mg discord Name), the same as their user
    name or their server nickname (case, accents, spaces, dots and hyphens are ignored).
  • Windows warns at start-up (unsigned program): "More info", "Run anyway".

SECURITY
  Keys are saved encrypted for your Windows session (folder %APPDATA%\\GBM-Manager). Never share them
  publicly. If a key leaked: regenerate it (Discord portal, or /apikey on Raid-Helper).

An idea from Mekinox and the Mortem In Anima guild. Written for GuildByMorricette (Morricette), GPL license.
"""


def texte():
    import lang
    return TEXTE_EN if lang.LANGUE == "en" else TEXTE


def liens():
    import lang
    return LIENS_EN if lang.LANGUE == "en" else LIENS
