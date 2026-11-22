"""GuildByMorricette (GBM) Manager - connexions HTTPS (1.2.4).

Le .exe fabrique par PyInstaller lit les certificats racine du magasin de Windows tels qu'ils sont sur le disque.
Windows ne telecharge certaines racines qu'a la premiere demande : celle de GitHub pouvait manquer
(« CERTIFICATE_VERIFY_FAILED ... unable to get issuer certificate »). On verifie donc les certificats comme
Windows lui-meme (truststore), sinon avec la liste de certifi, sinon avec le reglage par defaut de Python.
"""
import ssl
import urllib.request


def _contexte():
    try:
        import truststore
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except (ImportError, OSError, ssl.SSLError):
        pass   # pas de truststore (autre systeme, ou .exe fabrique sans lui) : on essaie certifi
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except (ImportError, OSError, ssl.SSLError):
        return ssl.create_default_context()


CONTEXTE = _contexte()


def ouvrir(req, timeout=30):
    """Comme urllib.request.urlopen, avec la verification des certificats ci-dessus."""
    return urllib.request.urlopen(req, timeout=timeout, context=CONTEXTE)
