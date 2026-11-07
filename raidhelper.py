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
