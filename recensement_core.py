"""GuildByMorricette (GBM) Manager - recensement : coeur de l'application (lecture, comparaison, mise en forme).

Ecrit pour GuildByMorricette. Idee proposee par Mekinox et la guilde Mortem In Anima.
Lit l'export de l'addon (variable GuildeForeverRecensement du fichier SavedVariables), le compare a la liste
des membres du serveur Discord et prepare le rapport. Aucun module exterieur : seulement Python standard.
"""
import glob
import json
import os
import re
import time
import unicodedata

FORMAT_SUPPORTE = 1
VARIABLE = "GuildeForeverRecensement"


# --- Lecture du fichier de sauvegarde -------------------------------------------------------------------------
def chemins_possibles():
    """Fichiers GuildeForever.lua probables sous Windows, du plus recent au plus ancien."""
    racines = [
        r"C:\Program Files (x86)\World of Warcraft\_forever_",
        r"C:\Program Files\World of Warcraft\_forever_",
        r"D:\World of Warcraft\_forever_",
        r"D:\Program Files (x86)\World of Warcraft\_forever_",
    ]
    trouves = []
    for r in racines:
        trouves += glob.glob(os.path.join(r, "WTF", "Account", "*", "SavedVariables", "GuildeForever.lua"))
    trouves.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return trouves


_ESC = {ord("n"): b"\n", ord("t"): b"\t", ord("r"): b"\r", ord("a"): b"\a", ord("b"): b"\b", ord("f"): b"\f",
        ord("v"): b"\v", ord("\\"): b"\\", ord('"'): b'"', ord("'"): b"'", ord("\n"): b"\n"}


def dechiffrer_chaine_lua(octets):
    """Decode le contenu (en octets) d'une chaine Lua entre guillemets : echappements \\n, \\", \\ddd..."""
    out = bytearray()
    i, n = 0, len(octets)
    while i < n:
        c = octets[i]
        if c != 0x5C:              # pas une barre oblique inverse : octet copie tel quel (UTF-8 compris)
            out.append(c)
            i += 1
            continue
        i += 1
        if i >= n:
            break
        c = octets[i]
        if 0x30 <= c <= 0x39:      # \ddd : jusqu'a trois chiffres decimaux
            j = i
            while j < n and j < i + 3 and 0x30 <= octets[j] <= 0x39:
                j += 1
            out.append(int(octets[i:j]) & 0xFF)
            i = j
        elif c == 0x0D:            # barre oblique en fin de ligne (Windows)
            out += b"\n"
            i += 2 if (i + 1 < n and octets[i + 1] == 0x0A) else 1
        else:
            out += _ESC.get(c, bytes([c]))
            i += 1
    return bytes(out)


def lire_export(chemin):
    """Rend le document JSON de l'export, ou leve ValueError avec un message clair."""
    with open(chemin, "rb") as f:
        texte = f.read()
    m = re.search(rb'^' + VARIABLE.encode() + rb'\s*=\s*"((?:[^"\\]|\\.)*)"', texte, re.M | re.S)
    if not m and re.search(rb'^' + VARIABLE.encode() + rb'\s*=\s*\{', texte, re.M):
        raise ValueError("L'export du fichier de sauvegarde est abime (bug de l'addon 1.16.0 de test) : installez la "
                         "derniere version de l'addon, puis tapez /reload.")
    if not m:
        raise ValueError("Pas de recensement dans ce fichier. En jeu, ouvrez l'onglet Recensement de la fenetre Guilde "
                         "(rang autorise par le chef de guilde), puis deconnectez-vous ou tapez /reload.")
    doc = json.loads(dechiffrer_chaine_lua(m.group(1)).decode("utf-8"))
    if doc.get("format", 0) > FORMAT_SUPPORTE:
        raise ValueError("Export au format %s : mettez l'application a jour." % doc.get("format"))
    return doc


# --- Comparaison ------------------------------------------------------------------------------------------------
def normaliser(nom):
    """Pour comparer les pseudos : minuscules, sans accents, sans espaces ni ponctuation de decoration."""
    if not nom:
        return ""
    nom = unicodedata.normalize("NFKD", str(nom)).encode("ascii", "ignore").decode("ascii")
    nom = nom.lower().strip()
    nom = re.sub(r"^@", "", nom)
    nom = re.sub(r"#\d{4}$", "", nom)          # ancien format pseudo#1234
    return re.sub(r"[\s._\-]+", "", nom)


def index_discord(membres_discord, ignorer_roles=()):
    """membres_discord : liste d'objets de l'API Discord. Rend { cle normalisee : membre simplifie }."""
    idx, liste = {}, []
    ignorer = set(str(r) for r in ignorer_roles or ())
    for m in membres_discord:
        u = m.get("user") or {}
        if u.get("bot"):
            continue
        if ignorer and ignorer.intersection(str(r) for r in m.get("roles", [])):
            continue
        simple = {
            "id": u.get("id"),
            "username": u.get("username") or "",
            "affiche": m.get("nick") or u.get("global_name") or u.get("username") or "",
            "arrive": m.get("joined_at"),
        }
        liste.append(simple)
        for cle in (u.get("username"), u.get("global_name"), m.get("nick")):
            k = normaliser(cle)
            if k and k not in idx:
                idx[k] = simple
    return idx, liste


def comparer(guilde, membres_discord, ignorer_roles=()):
    """Rend un dictionnaire de resultats pour une guilde de l'export."""
    idx, liste_discord = index_discord(membres_discord, ignorer_roles)
    joueurs = {}            # personnage principal -> infos du joueur
    for m in guilde.get("members", []):
        main = m.get("main") or m["name"]
        j = joueurs.setdefault(main, {"main": main, "persos": [], "discord": None, "niveau": 0, "classe": None,
                                      "derniere": 0})
        j["persos"].append(m["name"])
        if m.get("discord") and not j["discord"]:
            j["discord"] = m["discord"]
        if m["name"] == main or not j["classe"]:
            j["classe"] = m.get("class")
        j["niveau"] = max(j["niveau"], m.get("level") or 0)
        j["derniere"] = max(j["derniere"], m.get("lastOnline") or 0)
    des_deux, sans_pseudo, introuvables = [], [], []
    vus_discord = set()
    for j in sorted(joueurs.values(), key=lambda x: x["main"].lower()):
        if not j["discord"]:
            sans_pseudo.append(j)
            continue
        d = idx.get(normaliser(j["discord"]))
        if d:
            j["membre_discord"] = d
            des_deux.append(j)
            vus_discord.add(d["id"])
        else:
            introuvables.append(j)
    discord_seul = sorted((d for d in liste_discord if d["id"] not in vus_discord), key=lambda d: d["affiche"].lower())
    maintenant = time.time()
    evts = guilde.get("events", [])
    arrivees7 = [e for e in evts if e.get("type") == "join" and maintenant - e.get("time", 0) <= 7 * 86400]
    departs7 = [e for e in evts if e.get("type") == "leave" and maintenant - e.get("time", 0) <= 7 * 86400]
    return {
        "guilde": guilde.get("guild"), "photo": guilde.get("snapshot"), "par": guilde.get("snapshotBy"),
        "stats": guilde.get("stats", {}), "joueurs": len(joueurs), "persos": len(guilde.get("members", [])),
        "discord_total": len(liste_discord),
        "des_deux": des_deux, "sans_pseudo": sans_pseudo, "introuvables": introuvables, "discord_seul": discord_seul,
        "arrivees7": arrivees7, "departs7": departs7,
    }


# --- Mise en forme ---------------------------------------------------------------------------------------------------
COULEUR = 0x2BB5A8   # turquoise du theme "Guilde" de l'addon


def _liste(noms, limite=900):
    """Liste de noms qui tient dans un champ Discord (1024 caracteres)."""
    if not noms:
        return "—"
    out, taille = [], 0
    for i, n in enumerate(noms):
        if taille + len(n) + 2 > limite - 20:
            out.append("… et %d autres" % (len(noms) - i))
            break
        out.append(n)
        taille += len(n) + 2
    return ", ".join(out)


def _date(t):
    return time.strftime("%d/%m/%Y %H:%M", time.localtime(t)) if t else "-"


def embed(res):
    """Message Discord (embed) du recensement."""
    st = res["stats"]
    champs = [
        {"name": "Effectifs", "inline": False, "value": (
            "**%d** joueurs (rerolls regroupés) · **%d** personnages\n"
            "**%d** avec l'addon · **%d** membres sur le Discord"
            % (res["joueurs"], res["persos"], st.get("withAddon", 0), res["discord_total"]))},
        {"name": "✅ En jeu et sur Discord (%d)" % len(res["des_deux"]), "inline": False,
         "value": _liste(["%s (%s)" % (j["main"], j["membre_discord"]["affiche"]) for j in res["des_deux"]])},
        {"name": "🎮 En jeu, sans pseudo Discord (%d)" % len(res["sans_pseudo"]), "inline": False,
         "value": _liste([j["main"] for j in res["sans_pseudo"]])},
        {"name": "❓ Pseudo donné mais introuvable sur le serveur (%d)" % len(res["introuvables"]), "inline": False,
         "value": _liste(["%s (« %s »)" % (j["main"], j["discord"]) for j in res["introuvables"]])},
        {"name": "💬 Sur Discord, pas dans la guilde (%d)" % len(res["discord_seul"]), "inline": False,
         "value": _liste([d["affiche"] for d in res["discord_seul"]])},
        {"name": "Arrivées et départs (7 jours)", "inline": False, "value": (
            "Arrivées : %s\nDéparts : %s" % (
                _liste([e["name"] for e in res["arrivees7"]], 480), _liste([e["name"] for e in res["departs7"]], 480)))},
    ]
    return {
        "title": "Recensement · %s" % res["guilde"],
        "color": COULEUR,
        "fields": champs,
        "footer": {"text": "GuildByMorricette · photo du roster : %s par %s · sur 30 jours : %d arrivées, %d départs"
                   % (_date(res["photo"]), res["par"] or "?", st.get("joined30", 0), st.get("left30", 0))},
    }


def csv_texte(res):
    """Liste complete (separateur ;), pour Excel."""
    lignes = ["Categorie;Joueur;Personnages;Classe;Niveau;Pseudo Discord;Membre Discord;Derniere connexion"]
    def ligne(cat, j, d=None):
        lignes.append(";".join([cat, j["main"], " / ".join(j["persos"]), j.get("classe") or "", str(j.get("niveau") or ""),
                                j.get("discord") or "", (d or {}).get("affiche", ""), _date(j.get("derniere"))]))
    for j in res["des_deux"]:
        ligne("En jeu et sur Discord", j, j["membre_discord"])
    for j in res["sans_pseudo"]:
        ligne("En jeu, sans pseudo Discord", j)
    for j in res["introuvables"]:
        ligne("Pseudo introuvable sur Discord", j)
    for d in res["discord_seul"]:
        lignes.append(";".join(["Sur Discord, pas dans la guilde", "", "", "", "", "", d["affiche"], ""]))
    return "\n".join(lignes) + "\n"
