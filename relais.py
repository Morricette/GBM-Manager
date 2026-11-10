"""GuildByMorricette (GBM) Manager - relais des commandes et des evenements vers Discord et Raid-Helper.

Deux sources, traitees de la meme facon (chaque traitement compare a ce qui est deja publie) :
  - la bande de pixels affichee par l'addon (case "Relais Discord sur ce PC"), lue a l'ecran par pixel.py :
    publication en quelques secondes (le lecteur du journal du chat plus bas n'est plus utilise depuis 1.0.3) ;
  - l'export du fichier de sauvegarde (listes "orders" et "raids") : rattrapage a chaque /reload ou deconnexion.
"""
import json
import os
import re
import time

import lang
from lang import T

import recensement_core as core
from raidhelper import (RaidHelper, ErreurRaidHelper, MODELE_FOREVER, besoins, choisir_classe, classe_forever,
                        modele_forever, role_de, trouver_inscription)
from recensement_discord import Discord, ErreurDiscord

# Metier (nom du jeu, francais ou anglais) -> role Discord des artisans (version 1.1.0). Le role est cherche par son
# nom sur le serveur : s'il n'existe pas, pas de mention.
ROLES_METIERS = {
    "alchimie": "Alchimiste", "alchemy": "Alchimiste",
    "forge": "Forgeron", "blacksmithing": "Forgeron",
    "enchantement": "Enchanteur", "enchanting": "Enchanteur",
    "ingenierie": "Ingénieur", "engineering": "Ingénieur",
    "travail du cuir": "Travailleur du cuir", "leatherworking": "Travailleur du cuir",
    "couture": "Tailleur", "tailoring": "Tailleur",
    "minage": "Mineur", "mining": "Mineur",
    "cuisine": "Cuisinier", "cooking": "Cuisinier",
    "secourisme": "Secouriste", "first aid": "Secouriste",
}
ROLES_METIERS = {core.normaliser(k): v for k, v in ROLES_METIERS.items()}   # memes regles que les noms recus
# Role T / H / D -> role Discord appele quand il en manque dans la composition d'un evenement
ROLES_COMBAT = {"T": "Tank", "H": "Soigneur", "D": "Dégâts"}
# 1.3.0 : serveurs en anglais (role cherche sous son nom anglais si le nom francais n'existe pas)
ROLES_COMBAT_EN = {"T": "Tank", "H": "Healer", "D": "DPS"}
ROLES_METIERS_EN = {"Alchimiste": "Alchemist", "Forgeron": "Blacksmith", "Enchanteur": "Enchanter", "Ingénieur": "Engineer",
                    "Travailleur du cuir": "Leatherworker", "Tailleur": "Tailor", "Mineur": "Miner", "Cuisinier": "Cook",
                    "Secouriste": "First Aid"}

MOTIF = re.compile(r"GBM1~(\w)~(\w+)~(\d+)/(\d+)~(.*)$")
ETATS = {
    "open": ("🛠️", "Demandée", 0xE0A030),
    "taken": ("🔨", "Prise par %s", 0x3A8EE6),
    "done": ("✅", "Reçue", 0x2EA44F),
    "cancel": ("❌", "Annulée", 0x8B8B8B),
}
FERMEES = ("done", "cancel")

# 1.2.0 : plusieurs officiers peuvent faire tourner GBM Manager en meme temps (meme bot). Chaque publication porte une
# etiquette discrete ("ref. O12" pour une commande, "ref. E7" pour un evenement) ; avant de publier, l'application
# cherche cette etiquette dans le salon (ou dans les evenements Raid-Helper) et reprend le message qui existe deja.
# Si deux officiers publient au meme instant, le plus ancien message est garde et l'autre est efface.
def etiquette(genre, ident):
    return "réf. %s%s" % (genre, ident)


def _num(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return 0


def _porte(texte, etiq):
    """L'etiquette est-elle dans le texte (sans confondre "ref. O1" et "ref. O12") ?"""
    return re.search(re.escape(etiq) + r"(?![\w-])", texte or "") is not None


def chemin_journal(chemin_sauvegarde):
    """<jeu>\\_forever_\\WTF\\Account\\X\\SavedVariables\\GuildeForever.lua -> <jeu>\\_forever_\\Logs\\WoWChatLog.txt"""
    if not chemin_sauvegarde:
        return ""
    racine = os.path.dirname(chemin_sauvegarde)
    for _ in range(4):
        racine = os.path.dirname(racine)
    return os.path.join(racine, "Logs", "WoWChatLog.txt")


# --- Lecture du journal du chat --------------------------------------------------------------------------------------
class Journal:
    """Lit les nouvelles lignes du journal du chat et recolle les messages coupes en morceaux."""

    def __init__(self, chemin):
        self.chemin = chemin
        self.position = None     # None : on commence a la fin du fichier (pas de rejeu de l'ancien journal)
        self.morceaux = {}
        self.vus = set()

    def lire(self):
        """Rend la liste des messages complets [(type, donnees)]."""
        if not self.chemin or not os.path.exists(self.chemin):
            return []
        taille = os.path.getsize(self.chemin)
        if self.position is None or taille < self.position:   # premier passage, ou journal recommence
            self.position = taille if self.position is None else 0
            if self.position == taille:
                return []
        with open(self.chemin, "rb") as f:
            f.seek(self.position)
            brut = f.read()
        fin = brut.rfind(b"\n")
        if fin < 0:
            return []            # ligne pas encore terminee
        self.position += fin + 1
        sortie = []
        for ligne in brut[:fin].decode("utf-8", "replace").splitlines():
            m = MOTIF.search(ligne)
            if not m:
                continue
            genre, num, k, n, texte = m.group(1), m.group(2), int(m.group(3)), int(m.group(4)), m.group(5)
            cle = (genre, num)
            if cle in self.vus:
                continue         # le meme chuchotement apparait deux fois ("A" et "De")
            parts = self.morceaux.setdefault(cle, {})
            parts[k] = texte
            if len(parts) == n:
                del self.morceaux[cle]
                self.vus.add(cle)
                try:
                    sortie.append((genre, json.loads("".join(parts[i] for i in range(1, n + 1)))))
                except ValueError:
                    pass
        if len(self.vus) > 5000:
            self.vus = set(list(self.vus)[-2000:])
        return sortie


# --- Etat publie (fichier etat.json, a cote de la configuration) -----------------------------------------------------
class Etat:
    def __init__(self, chemin):
        self.chemin = chemin
        try:
            with open(chemin, "r", encoding="utf-8") as f:
                self.d = json.load(f)
        except (OSError, ValueError):
            self.d = {}
        self.d.setdefault("commandes", {})
        self.d.setdefault("raids", {})

    def sauver(self):
        os.makedirs(os.path.dirname(self.chemin), exist_ok=True)
        tmp = self.chemin + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.d, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.chemin)


# --- Le relais ---------------------------------------------------------------------------------------------------------
class Relais:
    def __init__(self, cfg, etat, journal_ui, montrer):
        self.cfg = cfg
        self.etat = etat
        self.log = journal_ui
        self.montrer = montrer           # dechiffre une cle enregistree
        self.membres = None
        self.membres_t = 0
        self.pseudos = {}                # personnage -> pseudo Discord (dernier export lu)
        self.persos = {}                 # personnage -> personnage principal

    # Discord ---------------------------------------------------------------------------------------------------
    def discord(self):
        return Discord(self.montrer(self.cfg.get("cle")))

    def _membres(self):
        if self.membres is None or time.time() - self.membres_t > 600:
            self.membres = self.discord().membres(self.cfg["serveur"])
            self.membres_t = time.time()
        return self.membres

    def id_discord(self, perso):
        """Identifiant Discord d'un personnage, d'apres le pseudo donne dans l'addon (ou None)."""
        pseudo = self.pseudos.get(perso) or self.pseudos.get(self.persos.get(perso, ""))
        return self.id_pseudo(pseudo)

    def id_pseudo(self, pseudo):
        if not pseudo or not self.cfg.get("serveur"):
            return None
        idx, _ = core.index_discord(self._membres())
        d = idx.get(core.normaliser(pseudo))
        return d["id"] if d else None

    def id_role(self, nom):
        """Identifiant d'un role du serveur d'apres son nom (sans majuscules ni accents), ou None."""
        if not nom or not self.cfg.get("serveur"):
            return None
        if getattr(self, "_roles", None) is None or time.time() - self._roles_t > 600:
            self._roles = {core.normaliser(r.get("name", "")): str(r["id"]) for r in self.discord().roles(self.cfg["serveur"])}
            self._roles_t = time.time()
        return self._roles.get(core.normaliser(nom))

    def roles_metiers(self, o):
        """Roles Discord des metiers qui fabriquent l'objet commande (champ "profs" envoye par l'addon)."""
        out = []
        for p in o.get("profs") or []:
            nom = ROLES_METIERS.get(core.normaliser(str(p)))
            rid = self.id_role(nom) or self.id_role(ROLES_METIERS_EN.get(nom))
            if rid and rid not in out:
                out.append(rid)
        return out

    def apprendre_export(self, guilde):
        """Pseudos et personnages principaux du dernier export (pour les mentions et Raid-Helper)."""
        for m in guilde.get("members", []):
            self.persos[m["name"]] = m.get("main") or m["name"]
            if m.get("discord"):
                self.pseudos[m["name"]] = m["discord"]
        for e in guilde.get("discordNames", []):
            self.pseudos.setdefault(e["name"], e.get("discord"))

    # Doublons (1.2.0) -------------------------------------------------------------------------------------------
    def _moi(self):
        if not getattr(self, "_bot", None):
            self._bot = str(self.discord().moi().get("id") or "")
        return self._bot

    @staticmethod
    def _texte(m):
        parts = [m.get("content") or ""]
        for e in m.get("embeds") or []:
            parts += [e.get("title") or "", e.get("description") or "", (e.get("footer") or {}).get("text") or ""]
        return "\n".join(parts)

    def chercher(self, salon, etiq, frais=False):
        """Messages du bot dans le salon qui portent l'etiquette, du plus ancien au plus recent."""
        cache = self.__dict__.setdefault("_vus", {})
        c = cache.get(salon)
        if frais or not c or time.time() - c[0] > 5:
            try:
                msgs = self.discord().messages(salon, 100)
            except ErreurDiscord as e:
                if not getattr(self, "_avert_hist", False):
                    self._avert_hist = True
                    self.log(T("⚠ Anti-doublons impossible : donnez au bot le droit « Lire l'historique des messages » "
                               "dans les salons où il écrit (%s).") % e)
                msgs = []
            c = (time.time(), msgs)
            cache[salon] = c
        moi = self._moi()
        out = [m for m in c[1] if str((m.get("author") or {}).get("id")) == moi and _porte(self._texte(m), etiq)]
        return sorted(out, key=lambda m: _num(m.get("id")))

    def garder_un(self, salon, etiq, mien):
        """Juste apres une publication : si un autre officier a publie la meme chose au meme instant, on garde le plus
        ancien message et on efface les autres. Rend l'identifiant du message garde."""
        time.sleep(1.5)
        tous = self.chercher(salon, etiq, frais=True)
        if len(tous) <= 1:
            return mien
        garde = str(tous[0]["id"])
        for m in tous[1:]:
            try:
                self.discord().effacer(salon, m["id"])
            except ErreurDiscord:
                pass
        if garde != str(mien):
            self.log(T("Doublon évité (%s) : un autre officier avait publié au même moment.") % etiq)
        return garde

    # Commandes ------------------------------------------------------------------------------------------------
    def _embed_commande(self, o):
        icone, texte, couleur = ETATS.get(o.get("state"), ETATS["open"])
        texte = T(texte)
        if o.get("state") == "taken":
            texte = texte % (o.get("taker") or "?")
        lignes = [T("Demandée par **%s**") % o.get("who", "?"),
                  T("Pour : **%s**") % (o["to"] if o.get("to") else T("tous les artisans"))]
        if o.get("note"):
            lignes.append(T("Note : %s") % o["note"])
        lignes.append(T("État : %s %s") % (icone, texte))
        return {"title": "%s %d × %s" % (icone, o.get("qty", 1), o.get("itemName", "?")), "description": "\n".join(lignes),
                "color": couleur, "footer": {"text": T("GuildByMorricette · commande aux artisans · %s") % etiquette("O", o.get("id"))}}

    def commande(self, o):
        salon = self.cfg.get("salon_commandes")
        if not salon or not o.get("id"):
            return
        c = self.etat.d["commandes"].get(o["id"])
        etat = o.get("state")
        if c is None:
            # 1.2.0 : deja publiee par un autre officier ? on reprend son message (et on le met a jour si besoin)
            deja = self.chercher(salon, etiquette("O", o["id"]))
            if deja:
                c = {"msg": str(deja[0]["id"]), "etat": None, "taker": None, "maj": 0,
                     "cree": o["created"] if (o.get("created") or 0) > 1e9 else time.time()}
                self.etat.d["commandes"][o["id"]] = c
                self.log(T("Commande déjà publiée par un autre officier : %s (message repris).") % o.get("itemName", "?"))
        if c is None:
            if etat in FERMEES:          # deja terminee quand on la decouvre : rien a publier
                self.etat.d["commandes"][o["id"]] = {"msg": None, "etat": etat, "ferme": time.time(), "maj": o.get("updated", 0)}
                return
            contenu, mentions, roles = "", [], []
            if self.cfg.get("mentionner", True) and o.get("to"):
                uid = self.id_discord(o["to"]) or self.id_pseudo(o.get("toDiscord"))
                if uid:
                    contenu, mentions = "<@%s>" % uid, [uid]
            elif self.cfg.get("mentionner_metiers", True) and not o.get("to"):
                roles = self.roles_metiers(o)          # commande pour tous les artisans : on appelle le metier
                contenu = " ".join("<@&%s>" % r for r in roles)
            msg = self.discord().message(salon, contenu, self._embed_commande(o), mentions, roles)
            msg = self.garder_un(salon, etiquette("O", o["id"]), msg)
            self.etat.d["commandes"][o["id"]] = {"msg": msg, "etat": etat, "taker": o.get("taker"), "maj": o.get("updated", 0),
                                                 "cree": o["created"] if (o.get("created") or 0) > 1e9 else time.time()}
            self.log(T("Commande publiée : %d × %s (%s).") % (o.get("qty", 1), o.get("itemName", "?"), o.get("who", "?")))
        else:
            if (o.get("updated") or 0) < (c.get("maj") or 0) or (etat == c.get("etat") and o.get("taker") == c.get("taker")):
                return
            if c.get("msg"):
                self.discord().changer(salon, c["msg"], self._embed_commande(o))
            c.update({"etat": etat, "taker": o.get("taker"), "maj": o.get("updated", 0)})
            if etat in FERMEES:
                c["ferme"] = time.time()
            self.log(T("Commande mise à jour (%s) : %s.") % (ETATS.get(etat, ("", etat))[1].replace("%s", o.get("taker") or ""), o.get("itemName", "?")))
        self.etat.sauver()

    def nettoyer(self):
        """Efface les messages des commandes terminees apres le delai, et ceux des commandes expirees (8 jours)."""
        salon = self.cfg.get("salon_commandes")
        if not salon:
            return
        delai = float(self.cfg.get("delai_heures", 24)) * 3600
        change = False
        for cid, c in list(self.etat.d["commandes"].items()):
            if not c.get("msg"):
                if c.get("ferme") and time.time() - c["ferme"] > 30 * 86400:
                    del self.etat.d["commandes"][cid]
                    change = True
                continue
            trop_vieille = time.time() - (c.get("cree") or time.time()) > 8 * 86400
            if (c.get("ferme") and time.time() - c["ferme"] >= delai) or trop_vieille:
                self.discord().effacer(salon, c["msg"])
                c["msg"] = None
                c.setdefault("ferme", time.time())
                change = True
        if change:
            self.etat.sauver()

    # Evenements (Raid-Helper) -----------------------------------------------------------------------------------
    def rh(self):
        return RaidHelper(self.montrer(self.cfg.get("cle_rh")))

    def organisateur(self, e):
        """ID Discord de l'organisateur : son pseudo, sinon celui des Reglages, sinon le proprietaire du serveur."""
        chef = self.id_pseudo(e.get("leaderDiscord")) if e.get("leaderDiscord") else None
        if not chef and e.get("by"):
            chef = self.id_discord(e["by"])
        if not chef and str(self.cfg.get("organisateur") or "").strip().isdigit():
            chef = str(self.cfg["organisateur"]).strip()
        if not chef:
            if not getattr(self, "_proprietaire", None):
                self._proprietaire = str(self.discord().serveur(self.cfg["serveur"]).get("owner_id") or "")
            chef = self._proprietaire
            if chef and e.get("by"):
                self.log(T("Raid-Helper : %s n'est pas reconnu sur Discord, le propriétaire du serveur est noté organisateur.") % e["by"])
        return chef

    def evenement(self, e):
        if not (self.cfg.get("cle_rh") and self.cfg.get("salon_rh") and self.cfg.get("serveur")) or not e.get("id"):
            return
        r = self.etat.d["raids"].get(e["id"])
        if not (r and r.get("rh")) and self.cfg.get("cle_rh"):
            r = self._reprendre(e) or r     # 1.2.0 : deja publie par un autre officier ?
        if not e.get("published", True) or e.get("removed"):
            appels = {r["appel"]} if r and r.get("appel") else set()
            appels |= {str(m["id"]) for m in self.chercher(self.cfg["salon_rh"], etiquette("E", e["id"]))}   # 1.2.0
            for a in appels:
                try:
                    self.discord().effacer(self.cfg["salon_rh"], a)
                except ErreurDiscord:
                    pass
            if r and r.get("rh"):
                self.rh().supprimer(r["rh"])
                self.log(T("Événement Raid-Helper supprimé (n° %s).") % r["rh"])
            else:
                self.log(T("Événement retiré dans l'addon : aucun événement Raid-Helper connu pour lui."))
            self.etat.d["raids"].pop(e["id"], None)
            self.etat.sauver()
            return
        titre = e.get("title") or T("Événement")
        if e.get("place"):
            titre = "%s — %s" % (e["place"], titre)
        if not e.get("when"):
            self.log(T("Événement « %s » sans date ou heure valide (JJ/MM et HH:MM) : pas publié sur Raid-Helper.") % titre)
            return
        if e["when"] < time.time() and not (r and r.get("rh")):
            self.log(T("Événement « %s » : la date et l'heure sont déjà passées, pas publié sur Raid-Helper "
                       "(il serait clôturé). Corrigez-les dans l'addon, puis Enregistrer.") % titre)
            return
        sig = json.dumps([titre, e.get("desc"), e.get("when"), e.get("size"), e.get("kind")], ensure_ascii=False)
        desc = (e.get("desc") or "").strip()
        type_txt = T({"raid": "Raid", "donjon": "Donjon", "jcj": "JcJ"}.get(e.get("kind"), "Raid"))
        corps = {"title": titre, "date": str(int(e["when"])), "time": str(int(e["when"])),
                 "description": (desc + "\n\n" if desc else "") + T("%s · %d joueurs · préparé avec GuildByMorricette · %s")
                 % (type_txt, e.get("size", 40), etiquette("E", e["id"]))}
        corps["templateId"] = str(self.cfg.get("modele_rh") or MODELE_FOREVER)   # par defaut : WoW: Forever
        corps["leaderId"] = self.organisateur(e)    # obligatoire pour Raid-Helper
        rh = self.rh()
        if not r or not r.get("rh"):
            try:
                ev = rh.creer(self.cfg["serveur"], self.cfg["salon_rh"], dict(corps, advancedSettings={"limit": int(e.get("size", 40))}))
            except ErreurRaidHelper:
                ev = rh.creer(self.cfg["serveur"], self.cfg["salon_rh"], corps)   # sans la limite de places
            if not ev.get("id"):
                self.log(T("⚠ Raid-Helper a répondu sans numéro d'événement : %s") % json.dumps(ev, ensure_ascii=False)[:300])
                return
            r = {"rh": str(ev.get("id")), "sig": sig, "inscrits": {}}
            self.etat.d["raids"][e["id"]] = r
            self.etat.sauver()
            self.log(T("Événement Raid-Helper créé : %s (n° %s).") % (corps["title"], r["rh"]))
            self._un_seul_evenement(e, titre, r)
        elif r.get("sig") != sig:
            ev = rh.modifier(r["rh"], corps)
            r["sig"] = sig
            self.log(T("Événement Raid-Helper modifié : %s.") % corps["title"])
        if r.get("when") != e["when"]:          # 1.3.0 : date changee -> le rappel sera refait
            r.pop("rappel", None)
        r["when"], r["titre"] = e["when"], titre
        self._inscriptions(e, r)
        try:
            self._appel_roles(e, r, titre)
        except ErreurDiscord as err:                     # le bot ne peut pas ecrire dans le salon : on le signale
            self.log(T("⚠ Appel des rôles manquants impossible : %s") % err)
        self.etat.sauver()

    def _memes_evenements(self, e, titre, frais=False):
        """Evenements Raid-Helper deja publies pour cet evenement de l'addon (etiquette, ou meme titre, date et salon)."""
        c = getattr(self, "_rh_liste", None)
        if frais or not c or time.time() - c[0] > 10:
            try:
                c = self._rh_liste = (time.time(), self.rh().evenements(self.cfg["serveur"]))
            except ErreurRaidHelper as err:
                self.log(T("⚠ Raid-Helper : liste des événements illisible, doublons non vérifiés (%s).") % err)
                return []
        liste = c[1]
        etiq, out = etiquette("E", e["id"]), []
        for ev in liste:
            if not isinstance(ev, dict) or not ev.get("id"):
                continue
            meme = _porte(ev.get("description"), etiq) or (
                titre and ev.get("title") == titre and e.get("when") and _num(ev.get("startTime")) == int(e["when"])
                and str(ev.get("channelId") or self.cfg["salon_rh"]) == str(self.cfg["salon_rh"]))
            if meme:
                out.append(ev)
        return sorted(out, key=lambda x: _num(x.get("id")))

    def _titre(self, e):
        titre = e.get("title") or T("Événement")
        return "%s — %s" % (e["place"], titre) if e.get("place") else titre

    def _reprendre(self, e):
        """Evenement deja publie par un autre officier : on le reprend (sans le recreer)."""
        if not e.get("id"):
            return None
        memes = self._memes_evenements(e, self._titre(e))
        if not memes:
            return None
        r = {"rh": str(memes[0]["id"]), "sig": None, "inscrits": {}}
        self.etat.d["raids"][e["id"]] = r
        self.log(T("Événement déjà publié sur Raid-Helper par un autre officier : %s (n° %s, repris).") % (self._titre(e), r["rh"]))
        return r

    def _un_seul_evenement(self, e, titre, r):
        """Juste apres la creation : si un autre officier a cree le meme evenement au meme instant, on garde le plus
        ancien et on supprime les autres."""
        time.sleep(2)
        memes = self._memes_evenements(e, titre, frais=True)
        if len(memes) <= 1:
            return
        garde = str(memes[0]["id"])
        for ev in memes[1:]:
            self.rh().supprimer(ev["id"])
        if garde != r["rh"]:
            self.log(T("Doublon évité : « %s » avait été créé au même moment par un autre officier (n° %s gardé).") % (titre, garde))
            r["rh"], r["inscrits"] = garde, {}

    def rappels(self):
        """1.3.0 : avant le depart (60 min par defaut), le bot mentionne les inscrits sous l'evenement Raid-Helper.
        Le message est efface 3 heures apres le depart. Un seul rappel, meme avec plusieurs officiers (etiquette)."""
        if not (self.cfg.get("rappel_inscrits", True) and self.cfg.get("cle_rh") and self.cfg.get("salon_rh")):
            return
        salon, change = self.cfg["salon_rh"], False
        try:
            avance = 60 * max(5, int(self.cfg.get("rappel_minutes") or 60))
        except (TypeError, ValueError):
            avance = 3600
        for eid, r in list(self.etat.d["raids"].items()):
            quand = r.get("when")
            if not quand or not r.get("rh"):
                continue
            reste = quand - time.time()
            etiq = etiquette("R", eid)
            if r.get("rappel") and r["rappel"] != "fini" and reste < -3 * 3600:
                try:
                    self.discord().effacer(salon, r["rappel"])
                except ErreurDiscord:
                    pass
                r["rappel"] = "fini"
                change = True
                continue
            if r.get("rappel") or reste <= 0 or reste > avance:
                continue
            deja = self.chercher(salon, etiq)
            if deja:                                  # un autre officier l'a deja fait
                r["rappel"] = str(deja[0]["id"])
                change = True
                continue
            try:
                ev = self.rh().evenement(r["rh"])
            except ErreurRaidHelper as err:
                self.log(T("⚠ Rappel impossible, Raid-Helper : %s") % err)
                continue
            ids, noms = [], []
            for s in (ev.get("signUps") or ev.get("signups") or []):
                if str(s.get("className") or "").lower() in ("absence", "absent"):
                    continue
                uid = str(s.get("userId") or "")
                if uid.isdigit() and uid not in ids:
                    ids.append(uid)
                elif s.get("name"):
                    noms.append(str(s["name"]))
            minutes = max(1, int(round(reste / 60)))
            texte = T("⏰ **%s** commence dans %d min !") % (r.get("titre") or T("Événement"), minutes)
            if ids:
                texte += " " + " ".join("<@%s>" % u for u in ids[:60])
            if noms:
                texte += T("\nAussi inscrits : ") + ", ".join(noms[:30])
            texte += "\n-# %s" % etiq
            r["rappel"] = self.garder_un(salon, etiq, self.discord().message(salon, texte, mentions=ids[:60]))
            change = True
            self.log(T("Rappel envoyé pour « %s » (%d inscrits mentionnés).") % (r.get("titre") or "?", len(ids[:60])))
        if change:
            self.etat.sauver()

    def manques(self, e):
        """{T: n, H: n, D: n} : places de tank, soigneur et degats encore libres dans la composition de l'evenement."""
        taille = int(e.get("size") or 40)
        compte = {"T": 0, "H": 0, "D": 0}
        for s in e.get("slots") or []:
            if isinstance(s, dict) and s.get("name"):
                compte[role_de(s.get("class"), s.get("role"), s.get("tree"))] += 1
        tanks, soins = besoins(taille)
        out = {"T": max(0, tanks - compte["T"]), "H": max(0, soins - compte["H"])}
        out["D"] = max(0, taille - max(tanks, compte["T"]) - max(soins, compte["H"]) - compte["D"])
        return {k: n for k, n in out.items() if n > 0}

    def _appel_roles(self, e, r, titre):
        """Message du bot sous l'evenement : "Il manque 1 @Tank, 2 @Soigneur". Les roles ne sont mentionnes (notifies)
        qu'a la premiere publication ; ensuite le message est seulement corrige, puis efface quand tout est complet."""
        if not self.cfg.get("mentionner_roles", True):
            return
        m = self.manques(e)
        salon, ancien = self.cfg["salon_rh"], r.get("appel")
        etiq = etiquette("E", e["id"])
        if not ancien:                               # 1.2.0 : appel deja ecrit par un autre officier ?
            deja = self.chercher(salon, etiq)
            if deja:
                ancien = r["appel"] = str(deja[0]["id"])
                r["appel_txt"] = None
        if not m:
            if ancien:
                for x in [ancien] + [str(d["id"]) for d in self.chercher(salon, etiq) if str(d["id"]) != ancien]:
                    self.discord().effacer(salon, x)
                r.pop("appel", None)
                r.pop("appel_txt", None)
                self.log(T("« %s » : composition complète, appel des rôles retiré.") % titre)
            return
        ids = {k: self.id_role(ROLES_COMBAT[k]) or self.id_role(ROLES_COMBAT_EN[k]) for k in m}
        noms = ROLES_COMBAT_EN if lang.LANGUE == "en" else ROLES_COMBAT     # langue de l'application
        morceaux = ["%d %s" % (n, ("<@&%s>" % ids[k]) if ids[k] else noms[k]) for k, n in m.items()]
        texte = T("🔔 **%s** : il manque encore %s. Inscrivez-vous ci-dessus !\n-# %s") % (titre, ", ".join(morceaux), etiq)
        if ancien:
            if r.get("appel_txt") != texte:
                self.discord().changer(salon, ancien, contenu=texte)
                r["appel_txt"] = texte
            return
        roles = [i for i in ids.values() if i]
        r["appel"] = self.garder_un(salon, etiq, self.discord().message(salon, texte, roles=roles))
        r["appel_txt"] = texte
        self.log(T("« %s » : appel des rôles manquants (%s).") % (titre, ", ".join("%d %s" % (n, noms[k]) for k, n in m.items())))

    def _inscriptions(self, e, r):
        rh = self.rh()
        voulus = {s["name"]: s for s in (e.get("slots") or []) if isinstance(s, dict) and s.get("name")}
        inscrits = r.setdefault("inscrits", {})
        for nom in [n for n in inscrits if n not in voulus]:            # retires de la composition
            rh.desinscrire(r["rh"], inscrits.pop(nom))
            self.log(T("Raid-Helper : %s retiré.") % nom)
        nouveaux = [s for n, s in voulus.items() if n not in inscrits]
        if not nouveaux:
            return
        actuel = rh.evenement(r["rh"])
        classes = (actuel.get("classes") or [])
        for s in sorted(nouveaux, key=lambda x: x.get("slot", 0)):
            uid = self.id_pseudo(s.get("discord")) if s.get("discord") else self.id_discord(s["name"])
            deja = trouver_inscription(actuel, s["name"], uid)   # 1.2.0 : inscrit par un autre officier
            if deja:
                inscrits[s["name"]] = deja
                continue
            if modele_forever(classes):
                cl, sp = classe_forever(s.get("class"), s.get("role"), s.get("tree"))
            else:
                cl, sp = choisir_classe(classes, s.get("class"), s.get("role"), s.get("spec"))
            corps = {"name": s["name"], "notify": False}
            if uid:
                corps["userId"] = uid
            else:
                corps["isFake"] = True
            if cl:
                corps["className"] = cl
            if sp:
                corps["specName"] = sp
            try:
                ev = rh.inscrire(r["rh"], corps)
            except ErreurRaidHelper:
                corps.pop("specName", None)                              # modele sans specialisations
                try:
                    ev = rh.inscrire(r["rh"], corps)
                except ErreurRaidHelper as err:                          # un joueur refuse n'empeche pas les autres
                    self.log(T("⚠ Raid-Helper : %s pas inscrit (%s).") % (s["name"], err))
                    continue
            inscrits[s["name"]] = trouver_inscription(ev, s["name"], uid) or "?"
            self.log(T("Raid-Helper : %s inscrit%s.") % (s["name"], "" if uid else T(" (sans compte Discord)")))

    # Traitement commun ----------------------------------------------------------------------------------------
    def traiter(self, genre, donnees):
        try:
            if genre == "O":
                self.commande(donnees)
            elif genre == "E":
                self.evenement(donnees)
            elif genre == "T":
                self.log(T("Relais : ligne de test reçue du jeu (%s). Le relais en direct fonctionne.") % donnees.get("by", "?"))
        except (ErreurDiscord, ErreurRaidHelper) as e:
            self.log("⚠ " + str(e))

    def rattraper(self, guilde):
        """Depuis l'export du fichier de sauvegarde : commandes et evenements (et retrait des evenements disparus)."""
        self.apprendre_export(guilde)
        for o in guilde.get("orders", []) or []:
            self.traiter("O", o)
        if "raids" in guilde:
            presents = set()
            for e in guilde.get("raids") or []:
                presents.add(e.get("id"))
                self.traiter("E", e)
            for rid in list(self.etat.d["raids"]):
                if rid not in presents:
                    self.traiter("E", {"id": rid, "published": False, "removed": True})
