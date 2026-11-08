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

import recensement_core as core
from raidhelper import RaidHelper, ErreurRaidHelper, choisir_classe, trouver_inscription
from recensement_discord import Discord, ErreurDiscord

MOTIF = re.compile(r"GBM1~(\w)~(\w+)~(\d+)/(\d+)~(.*)$")
ETATS = {
    "open": ("🛠️", "Demandée", 0xE0A030),
    "taken": ("🔨", "Prise par %s", 0x3A8EE6),
    "done": ("✅", "Reçue", 0x2EA44F),
    "cancel": ("❌", "Annulée", 0x8B8B8B),
}
FERMEES = ("done", "cancel")


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

    def apprendre_export(self, guilde):
        """Pseudos et personnages principaux du dernier export (pour les mentions et Raid-Helper)."""
        for m in guilde.get("members", []):
            self.persos[m["name"]] = m.get("main") or m["name"]
            if m.get("discord"):
                self.pseudos[m["name"]] = m["discord"]
        for e in guilde.get("discordNames", []):
            self.pseudos.setdefault(e["name"], e.get("discord"))

    # Commandes ------------------------------------------------------------------------------------------------
    def _embed_commande(self, o):
        icone, texte, couleur = ETATS.get(o.get("state"), ETATS["open"])
        if o.get("state") == "taken":
            texte = texte % (o.get("taker") or "?")
        lignes = ["Demandée par **%s**" % o.get("who", "?"),
                  "Pour : **%s**" % (o["to"] if o.get("to") else "tous les artisans")]
        if o.get("note"):
            lignes.append("Note : %s" % o["note"])
        lignes.append("État : %s %s" % (icone, texte))
        return {"title": "%s %d × %s" % (icone, o.get("qty", 1), o.get("itemName", "?")), "description": "\n".join(lignes),
                "color": couleur, "footer": {"text": "GuildByMorricette · commande aux artisans"}}

    def commande(self, o):
        salon = self.cfg.get("salon_commandes")
        if not salon or not o.get("id"):
            return
        c = self.etat.d["commandes"].get(o["id"])
        etat = o.get("state")
        if c is None:
            if etat in FERMEES:          # deja terminee quand on la decouvre : rien a publier
                self.etat.d["commandes"][o["id"]] = {"msg": None, "etat": etat, "ferme": time.time(), "maj": o.get("updated", 0)}
                return
            contenu, mentions = "", []
            if self.cfg.get("mentionner", True) and o.get("to"):
                uid = self.id_discord(o["to"]) or self.id_pseudo(o.get("toDiscord"))
                if uid:
                    contenu, mentions = "<@%s>" % uid, [uid]
            msg = self.discord().message(salon, contenu, self._embed_commande(o), mentions)
            self.etat.d["commandes"][o["id"]] = {"msg": msg, "etat": etat, "taker": o.get("taker"), "maj": o.get("updated", 0),
                                                 "cree": o["created"] if (o.get("created") or 0) > 1e9 else time.time()}
            self.log("Commande publiée : %d × %s (%s)." % (o.get("qty", 1), o.get("itemName", "?"), o.get("who", "?")))
        else:
            if (o.get("updated") or 0) < (c.get("maj") or 0) or (etat == c.get("etat") and o.get("taker") == c.get("taker")):
                return
            if c.get("msg"):
                self.discord().changer(salon, c["msg"], self._embed_commande(o))
            c.update({"etat": etat, "taker": o.get("taker"), "maj": o.get("updated", 0)})
            if etat in FERMEES:
                c["ferme"] = time.time()
            self.log("Commande mise à jour (%s) : %s." % (ETATS.get(etat, ("", etat))[1].replace("%s", o.get("taker") or ""), o.get("itemName", "?")))
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
                self.log("Raid-Helper : %s n'est pas reconnu sur Discord, le propriétaire du serveur est noté organisateur." % e["by"])
        return chef

    def evenement(self, e):
        if not (self.cfg.get("cle_rh") and self.cfg.get("salon_rh") and self.cfg.get("serveur")) or not e.get("id"):
            return
        r = self.etat.d["raids"].get(e["id"])
        if not e.get("published", True) or e.get("removed"):
            if r and r.get("rh"):
                self.rh().supprimer(r["rh"])
                self.log("Événement Raid-Helper supprimé (n° %s)." % r["rh"])
            else:
                self.log("Événement retiré dans l'addon : aucun événement Raid-Helper connu pour lui.")
            self.etat.d["raids"].pop(e["id"], None)
            self.etat.sauver()
            return
        titre = e.get("title") or "Événement"
        if e.get("place"):
            titre = "%s — %s" % (e["place"], titre)
        if not e.get("when"):
            self.log("Événement « %s » sans date ou heure valide (JJ/MM et HH:MM) : pas publié sur Raid-Helper." % titre)
            return
        if e["when"] < time.time() and not (r and r.get("rh")):
            self.log("Événement « %s » : la date et l'heure sont déjà passées, pas publié sur Raid-Helper "
                     "(il serait clôturé). Corrigez-les dans l'addon, puis Enregistrer." % titre)
            return
        sig = json.dumps([titre, e.get("desc"), e.get("when"), e.get("size"), e.get("kind")], ensure_ascii=False)
        desc = (e.get("desc") or "").strip()
        type_txt = {"raid": "Raid", "donjon": "Donjon", "jcj": "JcJ"}.get(e.get("kind"), "Raid")
        corps = {"title": titre, "date": str(int(e["when"])), "time": str(int(e["when"])),
                 "description": (desc + "\n\n" if desc else "") + "%s · %d joueurs · préparé avec GuildByMorricette" % (type_txt, e.get("size", 40))}
        if self.cfg.get("modele_rh"):
            corps["templateId"] = str(self.cfg["modele_rh"])
        corps["leaderId"] = self.organisateur(e)    # obligatoire pour Raid-Helper
        rh = self.rh()
        if not r or not r.get("rh"):
            try:
                ev = rh.creer(self.cfg["serveur"], self.cfg["salon_rh"], dict(corps, advancedSettings={"limit": int(e.get("size", 40))}))
            except ErreurRaidHelper:
                ev = rh.creer(self.cfg["serveur"], self.cfg["salon_rh"], corps)   # sans la limite de places
            if not ev.get("id"):
                self.log("⚠ Raid-Helper a répondu sans numéro d'événement : %s" % json.dumps(ev, ensure_ascii=False)[:300])
                return
            r = {"rh": str(ev.get("id")), "sig": sig, "inscrits": {}}
            self.etat.d["raids"][e["id"]] = r
            self.etat.sauver()
            self.log("Événement Raid-Helper créé : %s (n° %s)." % (corps["title"], r["rh"]))
        elif r.get("sig") != sig:
            ev = rh.modifier(r["rh"], corps)
            r["sig"] = sig
            self.log("Événement Raid-Helper modifié : %s." % corps["title"])
        self._inscriptions(e, r)
        self.etat.sauver()

    def _inscriptions(self, e, r):
        rh = self.rh()
        voulus = {s["name"]: s for s in (e.get("slots") or []) if isinstance(s, dict) and s.get("name")}
        inscrits = r.setdefault("inscrits", {})
        for nom in [n for n in inscrits if n not in voulus]:            # retires de la composition
            rh.desinscrire(r["rh"], inscrits.pop(nom))
            self.log("Raid-Helper : %s retiré." % nom)
        nouveaux = [s for n, s in voulus.items() if n not in inscrits]
        if not nouveaux:
            return
        classes = (rh.evenement(r["rh"]).get("classes") or [])
        for s in sorted(nouveaux, key=lambda x: x.get("slot", 0)):
            uid = self.id_pseudo(s.get("discord")) if s.get("discord") else self.id_discord(s["name"])
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
                    self.log("⚠ Raid-Helper : %s pas inscrit (%s)." % (s["name"], err))
                    continue
            inscrits[s["name"]] = trouver_inscription(ev, s["name"], uid) or "?"
            self.log("Raid-Helper : %s inscrit%s." % (s["name"], "" if uid else " (sans compte Discord)"))

    # Traitement commun ----------------------------------------------------------------------------------------
    def traiter(self, genre, donnees):
        try:
            if genre == "O":
                self.commande(donnees)
            elif genre == "E":
                self.evenement(donnees)
            elif genre == "T":
                self.log("Relais : ligne de test reçue du jeu (%s). Le relais en direct fonctionne." % donnees.get("by", "?"))
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
