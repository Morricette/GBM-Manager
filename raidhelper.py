"""GuildByMorricette (GBM) Manager - acces a Raid-Helper (API v4), avec seulement Python standard.

Cle : la cle API du serveur, que montre la commande /apikey de Raid-Helper (administrateur du serveur Discord).
Documentation : https://raid-helper.xyz/documentation/api
"""
import json
import time
import urllib.error
import urllib.request

API = "https://raid-helper.xyz/api/v4"
AGENT = "GBM-Manager (GuildByMorricette)"


class ErreurRaidHelper(Exception):
    pass


class RaidHelper:
    def __init__(self, cle):
        self.cle = (cle or "").strip()

    def _appel(self, methode, chemin, corps=None, essais=3):
        entetes = {"Authorization": self.cle, "User-Agent": AGENT}
        donnees = None
        if corps is not None:
            donnees = json.dumps(corps).encode("utf-8")
            entetes["Content-Type"] = "application/json; charset=utf-8"
        req = urllib.request.Request(API + chemin, data=donnees, headers=entetes, method=methode)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                brut = r.read()
                return json.loads(brut) if brut else {}
        except urllib.error.HTTPError as e:
            texte = e.read().decode("utf-8", "replace")
            if e.code == 429 and essais > 0:
                time.sleep(3)
                return self._appel(methode, chemin, corps, essais - 1)
            if e.code in (401, 403):
                raise ErreurRaidHelper("Raid-Helper refuse la cle API (%s) : recopiez-la avec /apikey sur Discord." % e.code)
            if e.code == 404:
                raise ErreurRaidHelper("Raid-Helper : introuvable (404). Verifiez l'identifiant du serveur et du salon.")
            raise ErreurRaidHelper("Raid-Helper, erreur %s : %s" % (e.code, texte[:300]))
        except urllib.error.URLError as e:
            raise ErreurRaidHelper("Raid-Helper injoignable (%s)." % e.reason)

    def creer(self, serveur, salon, corps):
        r = self._appel("POST", "/servers/%s/channels/%s/event" % (serveur, salon), corps)
        ev = r.get("event") or r
        return ev

    def modifier(self, id_evt, corps):
        r = self._appel("PATCH", "/events/%s" % id_evt, corps)
        return r.get("event") or r

    def supprimer(self, id_evt):
        try:
            self._appel("DELETE", "/events/%s" % id_evt)
        except ErreurRaidHelper as e:
            if "404" not in str(e):
                raise

    def evenements(self, serveur):
        """Evenements a venir du serveur (1.2.0, pour eviter les doublons quand plusieurs officiers publient)."""
        r = self._appel("GET", "/servers/%s/events" % serveur)
        if isinstance(r, list):
            return r
        return r.get("postedEvents") or r.get("events") or []

    def evenement(self, id_evt):
        r = self._appel("GET", "/events/%s" % id_evt)
        return r.get("event") or r

    def inscrire(self, id_evt, corps):
        r = self._appel("POST", "/events/%s/signups" % id_evt, corps)
        return r.get("event") or r

    def desinscrire(self, id_evt, id_inscription):
        try:
            self._appel("DELETE", "/events/%s/signups/%s" % (id_evt, id_inscription))
        except ErreurRaidHelper as e:
            if "404" not in str(e):
                raise


# --- Modele "WoW: Forever" de Raid-Helper (numero 47) -------------------------------------------------------------
# Lu dans le tableau de bord de Raid-Helper (novembre 2026) : categories Tank, Melee, Ranged, Healer, et dans
# chacune des specialisations en anglais ("Protection1" : paladin, "Holy1" : paladin, "Restoration1" : chaman).
MODELE_FOREVER = "47"
_TANK = {"Warrior": "Protection", "Paladin": "Protection1", "Druid": "Guardian", "Shaman": "Enhancement"}
_SOINS = {"Priest": {1: "Discipline", None: "Holy"}, "Paladin": {None: "Holy1"}, "Druid": {None: "Restoration"},
          "Shaman": {None: "Restoration1"}}
_DPS = {
    "Warrior": {1: ("Melee", "Arms"), None: ("Melee", "Fury")},
    "Paladin": {None: ("Melee", "Retribution")},
    "Rogue": {1: ("Melee", "Assassination"), 3: ("Melee", "Subtlety"), None: ("Melee", "Combat")},
    "Hunter": {1: ("Ranged", "Beastmastery"), 3: ("Ranged", "Survival"), None: ("Ranged", "Marksmanship")},
    "Mage": {1: ("Ranged", "Arcane"), 2: ("Ranged", "Fire"), None: ("Ranged", "Frost")},
    "Warlock": {2: ("Ranged", "Demonology"), 3: ("Ranged", "Destruction"), None: ("Ranged", "Affliction")},
    "Priest": {1: ("Ranged", "Smite"), 2: ("Ranged", "Smite"), None: ("Ranged", "Shadow")},
    "Shaman": {2: ("Melee", "Enhancement"), None: ("Ranged", "Elemental")},
    "Druid": {2: ("Melee", "Feral"), None: ("Ranged", "Balance")},
}
# arbre de talents principal -> role, si le joueur n'a pas choisi le sien (ordre des arbres du jeu)
_ROLE_ARBRE = {("Warrior", 3): "T", ("Paladin", 2): "T", ("Paladin", 1): "H", ("Priest", 1): "H", ("Priest", 2): "H",
               ("Druid", 3): "H", ("Shaman", 3): "H"}


def role_de(classe, role, arbre):
    """Role T (tank), H (soins) ou D (degats) d'un joueur : son choix, sinon son arbre de talents principal."""
    if role in ("T", "H", "D"):
        return role
    return _ROLE_ARBRE.get((classe, arbre), "D")


def besoins(taille):
    """(tanks, soigneurs) attendus selon la taille : 1 et 1 en donjon, puis 1 tank pour 10 et 1 soigneur pour 4."""
    taille = int(taille or 0)
    if taille <= 5:
        return 1, 1
    return max(2, taille // 10), max(2, taille // 4)


def modele_forever(classes):
    noms = {_nom(c) for c in classes or []}
    return {"Tank", "Melee", "Ranged", "Healer"} <= noms


def classe_forever(classe, role, arbre):
    """(className, specName) du modele WoW: Forever, d'apres la classe (anglais), le role T/H/D et l'arbre 1-3."""
    if not classe:
        return {"T": ("Tank", None), "H": ("Healer", None)}.get(role, ("Melee", None))
    role = role or _ROLE_ARBRE.get((classe, arbre), "D")
    if role == "T" and classe in _TANK:
        return "Tank", _TANK[classe]
    if role == "H" and classe in _SOINS:
        t = _SOINS[classe]
        return "Healer", t.get(arbre, t[None])
    t = _DPS.get(classe)
    if not t:
        return "Melee", None
    return t.get(arbre, t[None])


# --- Choix de la classe et de la specialisation dans le modele de l'evenement ------------------------------------
SPECS_ROLE = {
    "T": ("protection", "guardian", "feral", "tank", "bear"),
    "H": ("holy", "restoration", "discipline", "heal", "resto"),
}


def _nom(x):
    return (x.get("name") or x.get("className") or "") if isinstance(x, dict) else str(x)


def choisir_classe(classes, classe, role, spec):
    """classes : liste du modele Raid-Helper ({name, specs: [{name}]}). Rend (className, specName ou None)."""
    if not classes:
        return classe, None
    cl = None
    for c in classes:
        if classe and _nom(c).lower() == classe.lower():
            cl = c
            break
    if cl is None and role == "T":
        cl = next((c for c in classes if _nom(c).lower() == "tank"), None)
    if cl is None:
        return None, None
    specs = [s for s in (cl.get("specs") or []) if isinstance(s, dict)] if isinstance(cl, dict) else []
    if not specs:
        return _nom(cl), None
    noms = [_nom(s) for s in specs]
    if spec:
        for n in noms:
            if spec.lower() in n.lower() or n.lower() in spec.lower():
                return _nom(cl), n
    for mot in SPECS_ROLE.get(role or "", ()):
        for n in noms:
            if mot in n.lower():
                return _nom(cl), n
    return _nom(cl), noms[0]


def trouver_inscription(ev, nom=None, user_id=None):
    for s in (ev.get("signUps") or ev.get("signups") or []):
        if user_id and str(s.get("userId")) == str(user_id):
            return s.get("id")
        if nom and (s.get("name") or "").lower() == nom.lower():
            return s.get("id")
    return None
