"""GuildByMorricette (GBM) Manager - nouvelles versions (1.2.1).

Avis : au demarrage puis toutes les 6 heures, l'application demande a GitHub la derniere version publiee.
Mise a jour : le nouveau GBM_Manager.exe est telecharge a cote de l'ancien, puis un petit script attend la fermeture
de l'application, remplace le fichier et la relance. Seulement pour le .exe (pas en lancant le script Python).
"""
import json
import os
import subprocess
import sys
import tempfile
import urllib.request

from lang import T

DEPOT = "Morricette/GBM-Manager"
API = "https://api.github.com/repos/%s/releases/latest" % DEPOT
PAGE = "https://github.com/%s/releases/latest" % DEPOT
AGENT = "GBM-Manager (GuildByMorricette)"


def numero(v):
    """"v1.2.10" -> (1, 2, 10)"""
    out = []
    for p in str(v or "").lstrip("vV").split("."):
        try:
            out.append(int("".join(c for c in p if c.isdigit()) or 0))
        except ValueError:
            out.append(0)
    return tuple(out + [0] * (3 - len(out)))


def derniere():
    """(version, adresse du .exe) de la derniere version publiee, ou (None, None)."""
    req = urllib.request.Request(API, headers={"User-Agent": AGENT, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.loads(r.read())
    exe = next((a.get("browser_download_url") for a in d.get("assets") or [] if a.get("name") == "GBM_Manager.exe"), None)
    return (d.get("tag_name") or "").lstrip("vV") or None, exe


def plus_recente(distante, locale):
    return distante is not None and numero(distante) > numero(locale)


def peut_installer():
    """Mise a jour automatique possible : seulement pour GBM_Manager.exe sous Windows."""
    return os.name == "nt" and getattr(sys, "frozen", False)


def installer(adresse, journal):
    """Telecharge le nouveau .exe et prepare son remplacement. Rend True si l'application doit maintenant se fermer."""
    actuel = sys.executable
    neuf = actuel + ".nouveau"
    req = urllib.request.Request(adresse, headers={"User-Agent": AGENT})
    with urllib.request.urlopen(req, timeout=120) as r, open(neuf, "wb") as f:
        while True:
            bloc = r.read(1 << 16)
            if not bloc:
                break
            f.write(bloc)
    if os.path.getsize(neuf) < 1_000_000:          # fichier trop petit : telechargement rate
        os.remove(neuf)
        raise OSError(T("fichier téléchargé incomplet"))
    script = os.path.join(tempfile.gettempdir(), "gbm_manager_maj.bat")
    with open(script, "w", encoding="mbcs" if os.name == "nt" else "utf-8") as f:
        f.write("@echo off\r\n")
        f.write(":attendre\r\n")
        f.write('tasklist /fi "PID eq %d" | find "%d" >nul && (timeout /t 1 /nobreak >nul & goto attendre)\r\n'
                % (os.getpid(), os.getpid()))
        f.write('move /y "%s" "%s" >nul\r\n' % (neuf, actuel))
        f.write('start "" "%s" --fond\r\n' % actuel)
        f.write('del "%~f0"\r\n')
    subprocess.Popen(["cmd", "/c", script], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), close_fds=True)
    journal(T("Mise à jour téléchargée : GBM Manager redémarre."))
    return True
