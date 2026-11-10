"""GuildByMorricette (GBM) Manager - langue de l'application et des messages Discord (1.2.1).

Le texte francais sert de cle : T("texte") rend la traduction anglaise quand la langue est l'anglais.
Langue : reglage "langue" (auto = celle de Windows, fr, en). Le changement s'applique au prochain lancement.
"""
import os

LANGUE = "fr"


def langue_windows():
    """'fr' si Windows est en francais, sinon 'en'."""
    if os.name == "nt":
        try:
            import ctypes
            lid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            return "fr" if (lid & 0x3FF) == 0x0C else "en"
        except Exception:
            pass
    import locale
    loc = (locale.getdefaultlocale()[0] or "") if hasattr(locale, "getdefaultlocale") else ""
    return "fr" if loc.lower().startswith("fr") else "en"


def regler(code):
    global LANGUE
    LANGUE = langue_windows() if code in (None, "", "auto") else ("en" if code == "en" else "fr")
    return LANGUE


def T(s):
    if LANGUE == "en":
        return EN.get(s, s)
    return s


EN = {
    # --- fenetre ---
    "Réglages": "Settings",
    "Journal": "Log",
    "Aide": "Help",
    "Parcourir…": "Browse…",
    "Jeu": "Game",
    "Fichier de sauvegarde :": "Saved variables file:",
    "GuildeForever.lua (dossier WTF)": "GuildeForever.lua (WTF folder)",
    "Relais en direct : GBM Manager lit la bande de couleurs en haut à gauche du jeu.\n"
    "Jeu en fenêtré ou plein écran fenêtré, coin non couvert par une autre fenêtre.":
        "Live relay: GBM Manager reads the colour band at the top left of the game.\n"
        "Game in windowed or windowed fullscreen mode, corner not covered by another window.",
    "Lancer GBM Manager au démarrage de Windows (caché près de l'horloge ; il attend que le jeu soit lancé)":
        "Start GBM Manager with Windows (hidden next to the clock; it waits for the game to start)",
    "Installer les nouvelles versions de GBM Manager automatiquement": "Install new GBM Manager versions automatically",
    "Langue / Language :": "Langue / Language:",
    "au prochain lancement": "next time the app starts",
    "Discord (bot GBM Manager)": "Discord (GBM Manager bot)",
    "Clé du bot :": "Bot token:",
    "ID du serveur :": "Server ID:",
    "Recensement": "Census",
    "ID du salon des officiers :": "Officers' channel ID:",
    "vide = pas de recensement": "empty = no census",
    "Guilde :": "Guild:",
    "vide = la plus récente": "empty = the most recent",
    "Mettre à jour à chaque enregistrement du jeu (déconnexion ou /reload)": "Update every time the game saves (logout or /reload)",
    "Commandes aux artisans": "Crafting orders",
    "ID du salon des commandes :": "Orders channel ID:",
    "vide = pas de commandes": "empty = no orders",
    "Effacer après (heures) :": "Delete after (hours):",
    "commandes reçues ou annulées": "received or cancelled orders",
    "Mentionner l'artisan visé (s'il a donné son pseudo Discord)": "Mention the targeted crafter (if they gave their Discord name)",
    "Commande pour tous : mentionner le rôle du métier (@Forgeron, @Alchimiste…)":
        "Order for everyone: mention the profession role (@Blacksmith, @Alchemist…)",
    "Clé API (/apikey) :": "API key (/apikey):",
    "ID du salon des événements :": "Events channel ID:",
    "vide = pas de Raid-Helper": "empty = no Raid-Helper",
    "Modèle (facultatif) :": "Template (optional):",
    "vide = WoW: Forever (47)": "empty = WoW: Forever (47)",
    "Organisateur (facultatif) :": "Organiser (optional):",
    "ID Discord ; vide = propriétaire du serveur": "Discord ID; empty = server owner",
    "Appeler les rôles qui manquent (@Tank, @Soigneur, @Dégâts) sous l'événement":
        "Call the missing roles (@Tank, @Healer, @DPS) under the event",
    "Rappeler les inscrits avant le départ (mention sur Discord)": "Remind signed-up players before the start (Discord mention)",
    "Rappel (minutes avant) :": "Reminder (minutes before):",
    "60 par défaut": "60 by default",
    "Enregistrer": "Save",
    "Tester": "Test",
    "Mettre à jour maintenant": "Update now",
    "Recensement en CSV…": "Census as CSV…",
    "Nouvelle version ?": "New version?",
    "Ouvrir GBM Manager": "Open GBM Manager",
    "Quitter GBM Manager": "Quit GBM Manager",
    # --- journal ---
    "L'export ne contient aucune guilde recensee.": "The export contains no guild census.",
    "Guilde « %s » absente de l'export (guildes : %s).": "Guild \"%s\" not in the export (guilds: %s).",
    "Lecture des membres du serveur Discord…": "Reading the Discord server members…",
    "Message du salon mis à jour.": "Channel message updated.",
    "Ancien message introuvable : nouveau message.": "Old message not found: new message.",
    "Recensement déjà publié par un autre officier : son message est mis à jour.":
        "Census already posted by another officer: their message is updated.",
    "Message publié dans le salon.": "Message posted in the channel.",
    "%s : %d joueurs (%d personnages) · %d en jeu et sur Discord · %d sans pseudo · %d introuvables · %d sur Discord seulement":
        "%s: %d players (%d characters) · %d in game and on Discord · %d without name · %d not found · %d on Discord only",
    "Jeu détecté : lecture de la bande de couleurs.": "Game detected: reading the colour band.",
    "Jeu fermé : GBM Manager attend son lancement.": "Game closed: GBM Manager waits for it to start.",
    "Relais : bande de couleurs du jeu trouvée, lecture en direct.": "Relay: game colour band found, reading live.",
    "⚠ Erreur inattendue : %r": "⚠ Unexpected error: %r",
    "Le jeu a enregistré le fichier de sauvegarde : mise à jour.": "The game saved its file: updating.",
    "GBM Manager est déjà ouvert sur ce PC : son icône est près de l'horloge (flèche ^ en bas à droite de l'écran).":
        "GBM Manager is already open on this PC: its icon is next to the clock (^ arrow at the bottom right of the screen).",
    "Lancement au démarrage de Windows : %s.": "Start with Windows: %s.",
    "activé": "on",
    "désactivé": "off",
    "⚠ Lancement au démarrage de Windows impossible à régler : %s": "⚠ Could not set start with Windows: %s",
    "Fichier de sauvegarde lu : guilde « %s », %d personnages, %d commandes, %d événements.":
        "Saved file read: guild \"%s\", %d characters, %d orders, %d events.",
    "en attente": "waiting",
    "Relais en direct (bande de couleurs) : %s. En jeu, /mg relais test l'affiche 30 secondes.":
        "Live relay (colour band): %s. In game, /mg relay test shows it for 30 seconds.",
    "Bot Discord connecté : %s.": "Discord bot connected: %s.",
    "Serveur : %s, %d membres lisibles.": "Server: %s, %d readable members.",
    "Raid-Helper : clé API acceptée.": "Raid-Helper: API key accepted.",
    "Tout est prêt. Laissez GBM Manager ouvert pendant que vous jouez.": "All set. Keep GBM Manager running while you play.",
    "Mise à jour demandée.": "Update requested.",
    "CSV enregistré : %s": "CSV saved: %s",
    "Réglages enregistrés.": "Settings saved.",
    "%s %s démarré.": "%s %s started.",
    "Premier lancement : suivez l'onglet Aide (étapes 1 à 4), puis remplissez l'onglet Réglages et cliquez sur « Tester ».":
        "First start: follow the Help tab (steps 1 to 4), then fill in the Settings tab and click \"Test\".",
    "Fichier de sauvegarde non trouvé : utilisez « Parcourir… » (dossier _forever_\\WTF\\Account\\<compte>\\SavedVariables).":
        "Saved file not found: use \"Browse…\" (folder _forever_\\WTF\\Account\\<account>\\SavedVariables).",
    "GBM Manager continue de tourner, caché près de l'horloge. Clic droit sur son icône pour l'ouvrir ou le quitter.":
        "GBM Manager keeps running, hidden next to the clock. Right-click its icon to open or quit it.",
    "GBM Manager est près de l'horloge : la croix de la fenêtre le cache sans l'arrêter (clic droit sur l'icône pour l'ouvrir ou le quitter).":
        "GBM Manager is next to the clock: the window's X hides it without stopping it (right-click the icon to open or quit it).",
    "⚠ Nouvelle version : GitHub injoignable (%s).": "⚠ New version: GitHub unreachable (%s).",
    "GBM Manager est à jour (%s).": "GBM Manager is up to date (%s).",
    "Nouvelle version de GBM Manager disponible : %s (vous avez %s).": "New GBM Manager version available: %s (you have %s).",
    "⚠ Mise à jour automatique impossible (%s). Téléchargez-la : %s": "⚠ Automatic update failed (%s). Download it: %s",
    "Téléchargement : %s": "Download: %s",
    "GBM Manager %s est disponible.": "GBM Manager %s is available.",
    "Mise à jour téléchargée : GBM Manager redémarre.": "Update downloaded: GBM Manager restarts.",
    "fichier téléchargé incomplet": "incomplete download",
    # --- relais ---
    "Demandée": "Requested",
    "Prise par %s": "Taken by %s",
    "Reçue": "Received",
    "Annulée": "Cancelled",
    "Demandée par **%s**": "Requested by **%s**",
    "Pour : **%s**": "For: **%s**",
    "tous les artisans": "all crafters",
    "Note : %s": "Note: %s",
    "État : %s %s": "Status: %s %s",
    "GuildByMorricette · commande aux artisans · %s": "GuildByMorricette · crafting order · %s",
    "⚠ Anti-doublons impossible : donnez au bot le droit « Lire l'historique des messages » dans les salons où il écrit (%s).":
        "⚠ Duplicate check impossible: give the bot the \"Read Message History\" permission in the channels it writes to (%s).",
    "Doublon évité (%s) : un autre officier avait publié au même moment.": "Duplicate avoided (%s): another officer posted at the same time.",
    "Commande déjà publiée par un autre officier : %s (message repris).": "Order already posted by another officer: %s (message reused).",
    "Commande publiée : %d × %s (%s).": "Order posted: %d × %s (%s).",
    "Commande mise à jour (%s) : %s.": "Order updated (%s): %s.",
    "Raid-Helper : %s n'est pas reconnu sur Discord, le propriétaire du serveur est noté organisateur.":
        "Raid-Helper: %s is not recognised on Discord, the server owner is set as organiser.",
    "Événement Raid-Helper supprimé (n° %s).": "Raid-Helper event deleted (no. %s).",
    "Événement retiré dans l'addon : aucun événement Raid-Helper connu pour lui.": "Event removed in the addon: no known Raid-Helper event for it.",
    "Événement": "Event",
    "Événement « %s » sans date ou heure valide (JJ/MM et HH:MM) : pas publié sur Raid-Helper.":
        "Event \"%s\" has no valid date or time (DD/MM and HH:MM): not posted on Raid-Helper.",
    "Événement « %s » : la date et l'heure sont déjà passées, pas publié sur Raid-Helper (il serait clôturé). Corrigez-les dans l'addon, puis Enregistrer.":
        "Event \"%s\": the date and time have already passed, not posted on Raid-Helper (it would be closed). Fix them in the addon, then Save.",
    "Raid": "Raid",
    "Donjon": "Dungeon",
    "JcJ": "PvP",
    "%s · %d joueurs · préparé avec GuildByMorricette · %s": "%s · %d players · planned with GuildByMorricette · %s",
    "⚠ Raid-Helper a répondu sans numéro d'événement : %s": "⚠ Raid-Helper replied without an event number: %s",
    "Événement Raid-Helper créé : %s (n° %s).": "Raid-Helper event created: %s (no. %s).",
    "Événement Raid-Helper modifié : %s.": "Raid-Helper event updated: %s.",
    "⚠ Appel des rôles manquants impossible : %s": "⚠ Could not call the missing roles: %s",
    "⚠ Raid-Helper : liste des événements illisible, doublons non vérifiés (%s).": "⚠ Raid-Helper: event list unreadable, duplicates not checked (%s).",
    "Événement déjà publié sur Raid-Helper par un autre officier : %s (n° %s, repris).":
        "Event already posted on Raid-Helper by another officer: %s (no. %s, reused).",
    "Doublon évité : « %s » avait été créé au même moment par un autre officier (n° %s gardé).":
        "Duplicate avoided: \"%s\" was created at the same time by another officer (no. %s kept).",
    "⚠ Rappel impossible, Raid-Helper : %s": "⚠ Reminder failed, Raid-Helper: %s",
    "⏰ **%s** commence dans %d min !": "⏰ **%s** starts in %d min!",
    "\nAussi inscrits : ": "\nAlso signed up: ",
    "Rappel envoyé pour « %s » (%d inscrits mentionnés).": "Reminder sent for \"%s\" (%d players mentioned).",
    "« %s » : composition complète, appel des rôles retiré.": "\"%s\": group complete, role call removed.",
    "🔔 **%s** : il manque encore %s. Inscrivez-vous ci-dessus !\n-# %s": "🔔 **%s**: still missing %s. Sign up above!\n-# %s",
    "« %s » : appel des rôles manquants (%s).": "\"%s\": calling the missing roles (%s).",
    "⚠ Raid-Helper : %s pas inscrit (%s).": "⚠ Raid-Helper: %s not signed up (%s).",
    "Raid-Helper : %s inscrit%s.": "Raid-Helper: %s signed up%s.",
    " (sans compte Discord)": " (without a Discord account)",
    "Raid-Helper : %s retiré.": "Raid-Helper: %s removed.",
    "Relais : ligne de test reçue du jeu (%s). Le relais en direct fonctionne.": "Relay: test line received from the game (%s). The live relay works.",
    # --- recensement ---
    "L'export du fichier de sauvegarde est abime (bug de l'addon 1.16.0 de test) : installez la derniere version de l'addon, puis tapez /reload.":
        "The saved file export is damaged (bug of the 1.16.0 test addon): install the latest addon version, then type /reload.",
    "Export au format %s : mettez l'application a jour.": "Export in format %s: update the app.",
    "**%d** joueurs (rerolls regroupés) · **%d** personnages\n**%d** avec l'addon · **%d** membres sur le Discord":
        "**%d** players (alts grouped) · **%d** characters\n**%d** with the addon · **%d** Discord members",
    "✅ En jeu et sur Discord (%d)": "✅ In game and on Discord (%d)",
    "🎮 En jeu, sans pseudo Discord (%d)": "🎮 In game, no Discord name (%d)",
    "❓ Pseudo donné mais introuvable sur le serveur (%d)": "❓ Name given but not found on the server (%d)",
    "💬 Sur Discord, pas dans la guilde (%d)": "💬 On Discord, not in the guild (%d)",
    "Arrivées et départs (7 jours)": "Arrivals and departures (7 days)",
    "GuildByMorricette · photo du roster : %s par %s · sur 30 jours : %d arrivées, %d départs":
        "GuildByMorricette · roster snapshot: %s by %s · over 30 days: %d arrivals, %d departures",
    "Recensement · %s": "Census · %s",
    "Categorie;Joueur;Personnages;Classe;Niveau;Pseudo Discord;Membre Discord;Derniere connexion":
        "Category;Player;Characters;Class;Level;Discord name;Discord member;Last login",
    "En jeu et sur Discord": "In game and on Discord",
    "En jeu, sans pseudo Discord": "In game, no Discord name",
    "Pseudo introuvable sur Discord": "Name not found on Discord",
    "Sur Discord, pas dans la guilde": "On Discord, not in the guild",
    # --- Discord et Raid-Helper ---
    "Discord injoignable (%s). Verifiez la connexion Internet.": "Discord unreachable (%s). Check the Internet connection.",
    "Acces refuse (403) : le bot n'a pas les droits dans ce salon (voir, envoyer des messages, integrer des liens, joindre des fichiers, lire l'historique des messages), ou l'option Server Members Intent est desactivee.":
        "Access denied (403): the bot lacks permissions in this channel (view, send messages, embed links, attach files, read message history), or the Server Members Intent option is off.",
    "Pas de recensement dans ce fichier. En jeu, ouvrez l'onglet Recensement de la fenetre Guilde (rang autorise par le chef de guilde), puis deconnectez-vous ou tapez /reload.":
        "No census in this file. In game, open the Census tab of the Guild window (rank allowed by the guild master), then log out or type /reload.",
    "Cle du bot refusee (401) : recopiez la cle depuis le portail des developpeurs Discord.":
        "Bot token refused (401): copy the token again from the Discord developer portal.",
    "Introuvable (404) : verifiez l'identifiant du serveur et celui du salon.": "Not found (404): check the server and channel IDs.",
    "Erreur Discord %s : %s": "Discord error %s: %s",
    "Raid-Helper refuse la cle API (%s) : recopiez-la avec /apikey sur Discord.": "Raid-Helper refuses the API key (%s): copy it again with /apikey on Discord.",
    "Raid-Helper : introuvable (404). Verifiez l'identifiant du serveur et du salon.": "Raid-Helper: not found (404). Check the server and channel IDs.",
    "Raid-Helper injoignable (%s).": "Raid-Helper unreachable (%s).",
    "Raid-Helper, erreur %s : %s": "Raid-Helper, error %s: %s",
}
