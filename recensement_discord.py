"""GuildByMorricette (GBM) Manager - acces a Discord (API REST du bot), avec seulement Python standard.

Le bot a besoin de :
  - l'option "Server Members Intent" activee sur le portail des developpeurs Discord (liste des membres) ;
  - les droits "Voir le salon", "Envoyer des messages", "Integrer des liens" et "Joindre des fichiers"
    dans le salon des officiers ;
  - depuis 1.2.0, "Lire l'historique des messages" dans chaque salon ou il ecrit : avant de publier, l'application
    regarde si un autre officier n'a pas deja publie la meme chose (plusieurs officiers peuvent jouer en meme temps).
"""
import json
import time
import urllib.error
import urllib.request
import uuid

API = "https://discord.com/api/v10"
AGENT = "DiscordBot (https://www.curseforge.com/wow/addons/guildbymorricette, 1.0) GBM-Manager"


class ErreurDiscord(Exception):
    pass


class Discord:
    def __init__(self, cle):
        self.cle = (cle or "").strip()

    def _appel(self, methode, chemin, corps=None, multipart=None, essais=4):
        url = API + chemin
        entetes = {"Authorization": "Bot " + self.cle, "User-Agent": AGENT}
        donnees = None
        if multipart is not None:
            donnees, type_contenu = multipart
            entetes["Content-Type"] = type_contenu
        elif corps is not None:
            donnees = json.dumps(corps).encode("utf-8")
            entetes["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=donnees, headers=entetes, method=methode)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                brut = r.read()
                return json.loads(brut) if brut else None
        except urllib.error.HTTPError as e:
            texte = e.read().decode("utf-8", "replace")
            if e.code == 429 and essais > 0:          # trop de demandes : on attend ce que Discord demande
                try:
                    attente = float(json.loads(texte).get("retry_after", 2))
                except ValueError:
                    attente = 2
                time.sleep(min(attente, 30) + 0.2)
                return self._appel(methode, chemin, corps, multipart, essais - 1)
            raise ErreurDiscord(self._expliquer(e.code, texte))
        except urllib.error.URLError as e:
            raise ErreurDiscord("Discord injoignable (%s). Verifiez la connexion Internet." % e.reason)

    @staticmethod
    def _expliquer(code, texte):
        if code == 401:
            return "Cle du bot refusee (401) : recopiez la cle depuis le portail des developpeurs Discord."
        if code == 403:
            return ("Acces refuse (403) : le bot n'a pas les droits dans ce salon (voir, envoyer des messages, "
                    "integrer des liens, joindre des fichiers, lire l'historique des messages), ou l'option "
                    "Server Members Intent est desactivee.")
        if code == 404:
            return "Introuvable (404) : verifiez l'identifiant du serveur et celui du salon."
        return "Erreur Discord %s : %s" % (code, texte[:300])

    # --- lecture -----------------------------------------------------------------------------------------
    def moi(self):
        return self._appel("GET", "/users/@me")

    def serveur(self, id_serveur):
        return self._appel("GET", "/guilds/%s" % id_serveur)

    def roles(self, id_serveur):
        """Roles du serveur : liste de {id, name, mentionable, ...}."""
        return self._appel("GET", "/guilds/%s/roles" % id_serveur) or []

    def messages(self, id_salon, limite=100):
        """Derniers messages du salon, du plus recent au plus ancien (1.2.0, pour eviter les doublons)."""
        return self._appel("GET", "/channels/%s/messages?limit=%d" % (id_salon, max(1, min(100, limite)))) or []

    def membres(self, id_serveur):
        """Tous les membres du serveur (par pages de 1000)."""
        tous, apres = [], "0"
        while True:
            page = self._appel("GET", "/guilds/%s/members?limit=1000&after=%s" % (id_serveur, apres)) or []
            tous += page
            if len(page) < 1000:
                return tous
            apres = page[-1]["user"]["id"]

    # --- ecriture ----------------------------------------------------------------------------------------
    def message(self, id_salon, contenu="", embed=None, mentions=None, roles=None):
        """Message simple (texte et/ou embed), avec mentions autorisees (membres, roles) ; rend son identifiant."""
        corps = {"content": contenu or "", "allowed_mentions": {"parse": [], "users": list(mentions or []),
                                                               "roles": list(roles or [])}}
        if embed:
            corps["embeds"] = [embed]
        return self._appel("POST", "/channels/%s/messages" % id_salon, corps)["id"]

    def changer(self, id_salon, id_message, embed=None, contenu=None):
        corps = {"allowed_mentions": {"parse": []}}
        if embed is not None:
            corps["embeds"] = [embed]
        if contenu is not None:
            corps["content"] = contenu
        self._appel("PATCH", "/channels/%s/messages/%s" % (id_salon, id_message), corps)

    def effacer(self, id_salon, id_message):
        try:
            self._appel("DELETE", "/channels/%s/messages/%s" % (id_salon, id_message))
        except ErreurDiscord as e:
            if "404" not in str(e):   # deja efface : rien a faire
                raise

    def envoyer(self, id_salon, embed, fichier=None):
        """Nouveau message ; rend son identifiant."""
        if fichier:
            nom, contenu = fichier
            r = self._appel("POST", "/channels/%s/messages" % id_salon, multipart=_multipart({"embeds": [embed]}, nom, contenu))
        else:
            r = self._appel("POST", "/channels/%s/messages" % id_salon, {"embeds": [embed]})
        return r["id"]

    def modifier(self, id_salon, id_message, embed, fichier=None):
        """Remplace le contenu du message (et son fichier joint)."""
        if fichier:
            nom, contenu = fichier
            charge = {"embeds": [embed], "attachments": []}
            self._appel("PATCH", "/channels/%s/messages/%s" % (id_salon, id_message), multipart=_multipart(charge, nom, contenu))
        else:
            self._appel("PATCH", "/channels/%s/messages/%s" % (id_salon, id_message), {"embeds": [embed]})


def _multipart(charge, nom_fichier, contenu):
    """Corps multipart/form-data : le message (payload_json) et un fichier joint."""
    charge = dict(charge, attachments=[{"id": 0, "filename": nom_fichier}])
    limite = "----GBM" + uuid.uuid4().hex
    morceaux = [
        ("--%s\r\nContent-Disposition: form-data; name=\"payload_json\"\r\nContent-Type: application/json\r\n\r\n" % limite).encode(),
        json.dumps(charge).encode("utf-8"), b"\r\n",
        ("--%s\r\nContent-Disposition: form-data; name=\"files[0]\"; filename=\"%s\"\r\n"
         "Content-Type: text/csv; charset=utf-8\r\n\r\n" % (limite, nom_fichier)).encode(),
        contenu, b"\r\n",
        ("--%s--\r\n" % limite).encode(),
    ]
    return b"".join(morceaux), "multipart/form-data; boundary=" + limite
