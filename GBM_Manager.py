"""GuildByMorricette (GBM) Manager - application Windows de gestion de guilde.

Ecrit pour GuildByMorricette (licence GPL-2.0-or-later). Idee proposee par Mekinox et la guilde Mortem In Anima.
Trois outils : recensement (roster de la guilde compare aux membres du serveur Discord, message tenu a jour dans
un salon des officiers), commandes aux artisans publiees sur Discord en quelques secondes, evenements publies dans
l'addon envoyes a Raid-Helper avec les joueurs inscrits. Lit le fichier de sauvegarde et la bande de pixels de l'addon.

Lancement :  GBM_Manager.exe            fenetre
             GBM_Manager.exe --demo     essai sans Discord (fausse liste de membres), affiche le message
"""
import json
import os
import sys
import threading
import time

import aide
import recensement_core as core
import relais
from raidhelper import ErreurRaidHelper
from recensement_discord import Discord, ErreurDiscord

VERSION = "1.0.3"
NOM = "GuildByMorricette (GBM) Manager"
DOSSIER = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "GBM-Manager")
CONFIG = os.path.join(DOSSIER, "config.json")
ETAT = os.path.join(DOSSIER, "etat.json")


# --- Cle du bot : chiffree pour l'utilisateur Windows (DPAPI) ------------------------------------------------------
def _dpapi(donnees, chiffrer):
    import ctypes
    from ctypes import wintypes

    class BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    entree = BLOB(len(donnees), ctypes.cast(ctypes.create_string_buffer(donnees, len(donnees)), ctypes.POINTER(ctypes.c_char)))
    sortie = BLOB()
    f = ctypes.windll.crypt32.CryptProtectData if chiffrer else ctypes.windll.crypt32.CryptUnprotectData
    if not f(ctypes.byref(entree), None, None, None, None, 0, ctypes.byref(sortie)):
        raise OSError("DPAPI")
    res = ctypes.string_at(sortie.pbData, sortie.cbData)
    ctypes.windll.kernel32.LocalFree(sortie.pbData)
    return res


def cacher(cle):
    if not cle:
        return ""
    if os.name == "nt":
        try:
            return "dpapi:" + _dpapi(cle.encode("utf-8"), True).hex()
        except Exception:
            pass
    return "clair:" + cle


def montrer(valeur):
    if not valeur:
        return ""
    if valeur.startswith("dpapi:"):
        try:
            return _dpapi(bytes.fromhex(valeur[6:]), False).decode("utf-8")
        except Exception:
            return ""
    return valeur[6:] if valeur.startswith("clair:") else valeur


def charger_config():
    try:
        with open(CONFIG, "r", encoding="utf-8") as f:
            c = json.load(f)
    except (OSError, ValueError):
        c = {}
    c.setdefault("fichier", "")
    c.setdefault("cle", "")
    c.setdefault("serveur", "")
    c.setdefault("salon", "")
    c.setdefault("guilde", "")
    c.setdefault("ignorer_roles", [])
    c.setdefault("messages", {})        # { "serveur:salon:guilde" : id du message a modifier }
    c.setdefault("surveiller", True)
    c.setdefault("journal", "")             # (plus utilise depuis 1.0.3 : le relais passe par la bande de pixels)
    c.setdefault("organisateur", "")        # ID Discord de l'organisateur Raid-Helper par defaut (facultatif)
    c.setdefault("salon_commandes", "")
    c.setdefault("delai_heures", 24)
    c.setdefault("mentionner", True)
    c.setdefault("cle_rh", "")
    c.setdefault("salon_rh", "")
    c.setdefault("modele_rh", "")
    return c


def sauver_config(c):
    os.makedirs(DOSSIER, exist_ok=True)
    tmp = CONFIG + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(c, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CONFIG)


# --- Une mise a jour complete ---------------------------------------------------------------------------------------
def choisir_guilde(doc, nom):
    guildes = doc.get("guilds", [])
    if not guildes:
        raise ValueError("L'export ne contient aucune guilde recensee.")
    if nom:
        for g in guildes:
            if g.get("guild") == nom:
                return g
        raise ValueError("Guilde « %s » absente de l'export (guildes : %s)." % (nom, ", ".join(g.get("guild", "?") for g in guildes)))
    return max(guildes, key=lambda g: g.get("snapshot") or 0)


def mettre_a_jour(cfg, journal, membres_factices=None):
    """Lit l'export, compare, publie. Rend le resultat de la comparaison."""
    doc = core.lire_export(cfg["fichier"])
    g = choisir_guilde(doc, cfg.get("guilde"))
    if membres_factices is not None:
        membres = membres_factices
    else:
        d = Discord(montrer(cfg["cle"]))
        journal("Lecture des membres du serveur Discord…")
        membres = d.membres(cfg["serveur"])
    res = core.comparer(g, membres, cfg.get("ignorer_roles"))
    emb = core.embed(res)
    csv = core.csv_texte(res).encode("utf-8-sig")
    if membres_factices is not None:
        return res, emb, csv
    cle_msg = "%s:%s:%s" % (cfg["serveur"], cfg["salon"], res["guilde"])
    id_msg = cfg["messages"].get(cle_msg)
    nom_csv = "recensement.csv"
    if id_msg:
        try:
            d.modifier(cfg["salon"], id_msg, emb, (nom_csv, csv))
            journal("Message du salon mis à jour.")
            return res, emb, csv
        except ErreurDiscord as e:
            if "404" not in str(e):
                raise
            journal("Ancien message introuvable : nouveau message.")
    cfg["messages"][cle_msg] = d.envoyer(cfg["salon"], emb, (nom_csv, csv))
    sauver_config(cfg)
    journal("Message publié dans le salon.")
    return res, emb, csv


def resume(res):
    return ("%s : %d joueurs (%d personnages) · %d en jeu et sur Discord · %d sans pseudo · %d introuvables · "
            "%d sur Discord seulement" % (res["guilde"], res["joueurs"], res["persos"], len(res["des_deux"]),
                                           len(res["sans_pseudo"]), len(res["introuvables"]), len(res["discord_seul"])))


# --- Travail en arriere-plan (un seul fil : tout ce qui parle a Discord et a Raid-Helper) ----------------------------
class Moteur:
    """Lit la bande de pixels de l'addon (relais en direct) et le fichier de sauvegarde (recensement et rattrapage)."""

    def __init__(self, cfg, journal_ui):
        self.cfg = cfg
        self.log = journal_ui
        self.etat = relais.Etat(ETAT)
        self.relais = relais.Relais(cfg, self.etat, journal_ui, montrer)
        self.verrou = threading.Lock()
        self.pixels = None
        self.etat_pixels = ""
        self.mtime = 0
        self.dernier_menage = 0
        self.demande = False      # "Mettre a jour maintenant"
        self.actif = True
        self.fil = threading.Thread(target=self.boucle, daemon=True)
        self.fil_pixels = threading.Thread(target=self.boucle_pixels, daemon=True)

    def demarrer(self):
        self.fil.start()
        self.fil_pixels.start()

    def boucle_pixels(self):
        """Relais en direct : lit la bande de couleurs de l'addon une dizaine de fois par seconde."""
        try:
            import pixel
            self.pixels = pixel.Lecteur()
            self.pixels.capture = pixel.Capture()
        except Exception as e:      # hors Windows : pas de capture d'ecran
            self.etat_pixels = "indisponible (%s)" % e
            return
        while self.actif:
            if self.cfg.get("salon_commandes") or self.cfg.get("cle_rh"):
                try:
                    messages = self.pixels.tour()
                except Exception as e:
                    messages = []
                    self.pixels.etat = "erreur de capture (%s)" % e
                if self.pixels.etat != self.etat_pixels:
                    if self.pixels.etat == "bande lue":
                        self.log("Relais : bande de couleurs du jeu trouvée, lecture en direct.")
                    self.etat_pixels = self.pixels.etat
                for genre, donnees in messages:
                    with self.verrou:
                        self.relais.traiter(genre, donnees)
            time.sleep(0.1)

    def boucle(self):
        while self.actif:
            try:
                with self.verrou:
                    self.tour()
            except (ValueError, OSError, ErreurDiscord, ErreurRaidHelper) as e:
                self.log("⚠ " + str(e))
            except Exception as e:  # erreur inattendue : affichee, l'application continue
                self.log("⚠ Erreur inattendue : %r" % (e,))
            time.sleep(2)

    def tour(self):
        cfg = self.cfg
        # 2) fichier de sauvegarde ecrit par le jeu (deconnexion ou /reload) : recensement et rattrapage
        fichier = cfg.get("fichier")
        if fichier and os.path.exists(fichier):
            m = os.path.getmtime(fichier)
            nouveau = self.demande or (cfg.get("surveiller", True) and self.mtime and m != self.mtime)
            self.mtime = m        # 1.0.2 : retenu avant la lecture, sinon une erreur la faisait refaire toutes les 2 s
            if nouveau:
                self.demande = False
                self.log("Le jeu a enregistré le fichier de sauvegarde : mise à jour.")
                self.depuis_sauvegarde()
        # 3) menage des commandes terminees (toutes les minutes)
        if time.time() - self.dernier_menage > 60:
            self.dernier_menage = time.time()
            self.relais.nettoyer()

    def depuis_sauvegarde(self):
        cfg = self.cfg
        doc = core.lire_export(cfg["fichier"])
        g = choisir_guilde(doc, cfg.get("guilde"))
        self.relais.apprendre_export(g)
        if cfg.get("salon") and g.get("members"):
            res, _, _ = mettre_a_jour(cfg, self.log)
            self.log(resume(res))
        self.relais.rattraper(g)


# --- Fenetre ----------------------------------------------------------------------------------------------------------
def fenetre():
    import tkinter as tk
    import webbrowser
    from tkinter import filedialog, ttk

    premier = not os.path.exists(CONFIG)
    cfg = charger_config()
    if not cfg["fichier"]:
        trouves = core.chemins_possibles()
        if trouves:
            cfg["fichier"] = trouves[0]

    root = tk.Tk()
    root.title("%s %s" % (NOM, VERSION))
    root.geometry("900x720")
    root.minsize(760, 600)
    try:   # icone (logo de l'addon), aussi dans le .exe
        base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        root.iconbitmap(os.path.join(base, "icone.ico"))
    except Exception:
        pass

    onglets = ttk.Notebook(root)
    onglets.pack(fill="both", expand=True, padx=6, pady=6)
    t_reg = ttk.Frame(onglets, padding=8)
    t_log = ttk.Frame(onglets, padding=8)
    t_aide = ttk.Frame(onglets, padding=8)
    onglets.add(t_reg, text="Réglages")
    onglets.add(t_log, text="Journal")
    onglets.add(t_aide, text="Aide")

    # Journal ------------------------------------------------------------------------------------------------------
    texte = tk.Text(t_log, wrap="word", state="disabled")
    barre = ttk.Scrollbar(t_log, command=texte.yview)
    texte.configure(yscrollcommand=barre.set)
    texte.pack(side="left", fill="both", expand=True)
    barre.pack(side="right", fill="y")

    def journal(msg):
        def ecrire():
            texte.configure(state="normal")
            texte.insert("end", time.strftime("%H:%M:%S  ") + msg + "\n")
            texte.see("end")
            texte.configure(state="disabled")
            etat_bas.set(msg[:140])
        root.after(0, ecrire)

    # Aide ---------------------------------------------------------------------------------------------------------
    liens = ttk.Frame(t_aide)
    liens.pack(fill="x")
    for nom, url in aide.LIENS:
        ttk.Button(liens, text=nom, command=lambda u=url: webbrowser.open(u)).pack(side="left", padx=3, pady=3)
    t_aide_txt = tk.Text(t_aide, wrap="word")
    b2 = ttk.Scrollbar(t_aide, command=t_aide_txt.yview)
    t_aide_txt.configure(yscrollcommand=b2.set)
    t_aide_txt.insert("1.0", aide.TEXTE)
    t_aide_txt.configure(state="disabled")
    t_aide_txt.pack(side="left", fill="both", expand=True, pady=(6, 0))
    b2.pack(side="right", fill="y", pady=(6, 0))

    # Reglages -----------------------------------------------------------------------------------------------------
    v = {k: tk.StringVar(value=str(cfg.get(k) or "")) for k in
         ("fichier", "serveur", "salon", "guilde", "salon_commandes", "delai_heures", "salon_rh", "modele_rh", "organisateur")}
    v["cle"] = tk.StringVar(value=montrer(cfg["cle"]))
    v["cle_rh"] = tk.StringVar(value=montrer(cfg["cle_rh"]))
    v_mention = tk.BooleanVar(value=bool(cfg.get("mentionner", True)))
    v_surv = tk.BooleanVar(value=bool(cfg.get("surveiller", True)))
    t_reg.columnconfigure(0, weight=1)

    def section(titre, ligne):
        f = ttk.LabelFrame(t_reg, text=titre, padding=6)
        f.grid(row=ligne, column=0, sticky="ew", pady=4)
        f.columnconfigure(1, weight=1)
        return f

    def champ(f, r, etiquette, cle, cache=False, parcourir=None, aide_txt=None):
        ttk.Label(f, text=etiquette).grid(row=r, column=0, sticky="w", padx=4, pady=2)
        ttk.Entry(f, textvariable=v[cle], show="•" if cache else "").grid(row=r, column=1, sticky="ew", padx=4, pady=2)
        if parcourir:
            ttk.Button(f, text="Parcourir…", command=parcourir).grid(row=r, column=2, padx=4)
        elif aide_txt:
            ttk.Label(f, text=aide_txt, foreground="#777").grid(row=r, column=2, sticky="w", padx=4)

    def choisir(cle, titre, motif):
        p = filedialog.askopenfilename(title=titre, filetypes=[(motif, motif), ("Tous", "*.*")])
        if p:
            v[cle].set(p)

    s1 = section("Jeu", 0)
    champ(s1, 0, "Fichier de sauvegarde :", "fichier", parcourir=lambda: choisir("fichier", "GuildeForever.lua (dossier WTF)", "GuildeForever.lua"))
    ttk.Label(s1, text="Relais en direct : GBM Manager lit la bande de couleurs en haut à gauche du jeu.\n"
                       "Jeu en fenêtré ou plein écran fenêtré, coin non couvert par une autre fenêtre.",
              foreground="#777").grid(row=1, column=1, sticky="w", padx=4)
    s2 = section("Discord (bot GBM Manager)", 1)
    champ(s2, 0, "Clé du bot :", "cle", cache=True)
    champ(s2, 1, "ID du serveur :", "serveur")
    s3 = section("Recensement", 2)
    champ(s3, 0, "ID du salon des officiers :", "salon", aide_txt="vide = pas de recensement")
    champ(s3, 1, "Guilde :", "guilde", aide_txt="vide = la plus récente")
    ttk.Checkbutton(s3, text="Mettre à jour à chaque enregistrement du jeu (déconnexion ou /reload)", variable=v_surv).grid(row=2, column=0, columnspan=3, sticky="w", padx=4)
    s4 = section("Commandes aux artisans", 3)
    champ(s4, 0, "ID du salon des commandes :", "salon_commandes", aide_txt="vide = pas de commandes")
    champ(s4, 1, "Effacer après (heures) :", "delai_heures", aide_txt="commandes reçues ou annulées")
    ttk.Checkbutton(s4, text="Mentionner l'artisan visé (s'il a donné son pseudo Discord)", variable=v_mention).grid(row=2, column=0, columnspan=3, sticky="w", padx=4)
    s5 = section("Raid-Helper", 4)
    champ(s5, 0, "Clé API (/apikey) :", "cle_rh", cache=True)
    champ(s5, 1, "ID du salon des événements :", "salon_rh", aide_txt="vide = pas de Raid-Helper")
    champ(s5, 2, "Modèle (facultatif) :", "modele_rh", aide_txt="numéro du modèle Raid-Helper")
    champ(s5, 3, "Organisateur (facultatif) :", "organisateur", aide_txt="ID Discord ; vide = propriétaire du serveur")

    boutons = ttk.Frame(t_reg)
    boutons.grid(row=5, column=0, sticky="w", pady=8)
    etat_bas = tk.StringVar(value="")
    ttk.Label(root, textvariable=etat_bas, foreground="#555").pack(side="bottom", fill="x", padx=10, pady=(0, 6))

    def lire_champs():
        for k in ("fichier", "serveur", "salon", "guilde", "salon_commandes", "salon_rh", "modele_rh", "organisateur"):
            cfg[k] = v[k].get().strip()
        try:
            cfg["delai_heures"] = max(0.0, float(v["delai_heures"].get().replace(",", ".") or 24))
        except ValueError:
            cfg["delai_heures"] = 24
        cfg["cle"] = cacher(v["cle"].get().strip())
        cfg["cle_rh"] = cacher(v["cle_rh"].get().strip())
        cfg["mentionner"] = bool(v_mention.get())
        cfg["surveiller"] = bool(v_surv.get())
        sauver_config(cfg)
        moteur.relais.membres = None   # liste des membres relue avec les nouveaux reglages

    def en_fond(travail):
        def tache():
            try:
                travail()
            except (ValueError, OSError, ErreurDiscord, ErreurRaidHelper) as e:
                journal("⚠ " + str(e))
            except Exception as e:
                journal("⚠ Erreur inattendue : %r" % (e,))
        threading.Thread(target=tache, daemon=True).start()

    def tester():
        lire_champs()
        onglets.select(t_log)

        def t():
            doc = core.lire_export(cfg["fichier"])
            g = choisir_guilde(doc, cfg["guilde"])
            journal("Fichier de sauvegarde lu : guilde « %s », %d personnages, %d commandes, %d événements."
                    % (g.get("guild"), len(g.get("members", [])), len(g.get("orders", []) or []), len(g.get("raids", []) or [])))
            ep = moteur.etat_pixels or "en attente"
            journal("Relais en direct (bande de couleurs) : %s. En jeu, /mg relais test l'affiche 30 secondes." % ep)
            d = Discord(montrer(cfg["cle"]))
            journal("Bot Discord connecté : %s." % d.moi().get("username"))
            journal("Serveur : %s, %d membres lisibles." % (d.serveur(cfg["serveur"]).get("name"), len(d.membres(cfg["serveur"]))))
            if cfg.get("cle_rh"):
                from raidhelper import RaidHelper
                RaidHelper(montrer(cfg["cle_rh"]))._appel("GET", "/servers/%s/events" % cfg["serveur"])
                journal("Raid-Helper : clé API acceptée.")
            journal("Tout est prêt. Laissez GBM Manager ouvert pendant que vous jouez.")
        en_fond(t)

    def maintenant():
        lire_champs()
        moteur.demande = True
        journal("Mise à jour demandée.")

    def enregistrer_csv():
        lire_champs()
        cible = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="recensement.csv", filetypes=[("CSV (Excel)", "*.csv")])
        if not cible:
            return

        def t():
            g = choisir_guilde(core.lire_export(cfg["fichier"]), cfg["guilde"])
            res = core.comparer(g, Discord(montrer(cfg["cle"])).membres(cfg["serveur"]), cfg.get("ignorer_roles"))
            with open(cible, "wb") as f:
                f.write(core.csv_texte(res).encode("utf-8-sig"))
            journal("CSV enregistré : %s" % cible)
        en_fond(t)

    ttk.Button(boutons, text="Enregistrer", command=lambda: (lire_champs(), journal("Réglages enregistrés."))).pack(side="left", padx=4)
    ttk.Button(boutons, text="Tester", command=tester).pack(side="left", padx=4)
    ttk.Button(boutons, text="Mettre à jour maintenant", command=maintenant).pack(side="left", padx=4)
    ttk.Button(boutons, text="Recensement en CSV…", command=enregistrer_csv).pack(side="left", padx=4)

    moteur = Moteur(cfg, journal)
    moteur.demarrer()
    journal("%s %s démarré." % (NOM, VERSION))
    if premier:
        onglets.select(t_aide)
        journal("Premier lancement : suivez l'onglet Aide (étapes 1 à 4), puis remplissez l'onglet Réglages et cliquez sur « Tester ».")
    if not cfg["fichier"]:
        journal("Fichier de sauvegarde non trouvé : utilisez « Parcourir… » (dossier _forever_\\WTF\\Account\\<compte>\\SavedVariables).")

    def fermer():
        lire_champs()
        moteur.actif = False
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", fermer)
    root.mainloop()


# --- Essai sans Discord -------------------------------------------------------------------------------------------------
def demo(fichier, membres_json):
    cfg = {"fichier": fichier, "guilde": "", "ignorer_roles": []}
    with open(membres_json, "r", encoding="utf-8") as f:
        membres = json.load(f)
    res, emb, csv = mettre_a_jour(cfg, print, membres_factices=membres)
    print(resume(res))
    print(json.dumps(emb, ensure_ascii=False, indent=2))
    print(csv.decode("utf-8-sig"))
    return res, emb


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "--demo":
        demo(sys.argv[2], sys.argv[3])
    else:
        fenetre()
