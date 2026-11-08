"""GuildByMorricette (GBM) Manager - lecture de la bande de pixels affichee par l'addon (relais en direct).

L'addon (case "Relais Discord sur ce PC") affiche en haut a gauche de l'ecran du jeu une bande de 2 x 128 carres
de couleur. Chaque carre vaut 0 a 63 (rouge, vert, bleu sur 4 niveaux). Voir FORMAT-RECENSEMENT.txt de l'addon.
Ce module capture ce coin de l'ecran (Windows), retrouve la bande, decode les images et recolle les messages.
"""
import json
import time

COLS, ROWS = 128, 2
CELLS = COLS * ROWS
HEAD = 17
DATA_CELLS = CELLS - HEAD
GENRES = {1: "O", 2: "E", 3: "T"}
ZONE = (640, 32)          # largeur, hauteur capturees en haut a gauche du jeu (pixels de l'ecran)


# --- Decodage (pur Python, testable sans Windows) ----------------------------------------------------------------
def _magenta(p):
    r, g, b = p
    return r > 150 and b > 150 and g < 100


def _vert(p):
    r, g, b = p
    return g > 150 and r < 100 and b < 100


def trouver_bande(pix, larg, haut):
    """pix(x, y) -> (r, g, b). Rend (x0, y0, taille du carre) ou None."""
    for y in range(min(haut, 12)):
        for x in range(min(larg, 24)):
            if not _magenta(pix(x, y)):
                continue
            n = 1
            while x + n < larg and _magenta(pix(x + n, y)):
                n += 1
            if n < 1 or n > 12:
                continue
            # le carre suivant est vert, de la meme taille, puis magenta, puis vert
            if all(_vert(pix(x + n + k, y)) for k in range(n)) and _magenta(pix(x + 2 * n + n // 2, y)) \
                    and _vert(pix(x + 3 * n + n // 2, y)):
                y0 = y
                while y0 > 0 and _magenta(pix(x, y0 - 1)):
                    y0 -= 1
                return x, y0, n
    return None


def lire_image(pix, x0, y0, s):
    """Rend la liste des 256 valeurs (0 a 63) ou None si l'etalonnage est incoherent."""
    def centre(i):
        c, r = i % COLS, i // COLS
        return pix(x0 + c * s + s // 2, y0 + r * s + s // 2)
    gris = [sum(centre(4 + k)) / 3.0 for k in range(4)]
    if not (gris[0] < gris[1] < gris[2] < gris[3]) or gris[3] - gris[0] < 120:
        return None
    seuils = [(gris[k] + gris[k + 1]) / 2 for k in range(3)]

    def niveau(v):
        return sum(1 for t in seuils if v > t)
    vals = []
    for i in range(CELLS):
        r, g, b = centre(i)
        vals.append(niveau(r) * 16 + niveau(g) * 4 + niveau(b))
    if vals[0:4] != [51, 12, 51, 12]:
        return None
    return vals


def octets(cellules, n):
    out, acc, nb = bytearray(), 0, 0
    for c in cellules:
        acc = (acc << 6) | c
        nb += 6
        if nb >= 8:
            nb -= 8
            out.append((acc >> nb) & 0xFF)
            acc &= (1 << nb) - 1
            if len(out) == n:
                break
    return bytes(out)


def controle(data, ident, part, total, genre):
    s = ident + part * 3 + total * 5 + len(data) * 7 + genre * 11
    for i, b in enumerate(data):
        s += b * (i % 7 + 1)
    return s % 4096


def decoder(vals):
    """Rend (ident, morceau, total, genre, octets) ou None (image coupee pendant un changement, etc.)."""
    ident = vals[8] * 64 + vals[9]
    part, total = vals[10], vals[11]
    n = vals[12] * 64 + vals[13]
    genre = vals[14]
    c = vals[15] * 64 + vals[16]
    if not (1 <= part <= total <= 63) or genre not in GENRES or n > DATA_CELLS * 6 // 8:
        return None
    data = octets(vals[HEAD:], n)
    if len(data) != n or controle(data, ident, part, total, genre) != c:
        return None
    return ident, part, total, GENRES[genre], data


class Assembleur:
    """Recolle les morceaux ; chaque message complet n'est rendu qu'une fois (la bande le repete en boucle)."""

    def __init__(self):
        self.morceaux = {}     # (ident, genre, total) -> {part: octets}
        self.vus = {}          # (ident, empreinte) -> date

    def ajouter(self, ident, part, total, genre, data):
        cle = (ident, genre, total)
        m = self.morceaux.setdefault(cle, {})
        m[part] = data
        if len(m) < total:
            return None
        texte = b"".join(m[k] for k in range(1, total + 1))
        del self.morceaux[cle]
        maintenant = time.time()
        for k in [k for k, t in self.vus.items() if maintenant - t > 900]:
            del self.vus[k]
        empreinte = (ident, hash(texte))
        if empreinte in self.vus:
            return None
        self.vus[empreinte] = maintenant
        try:
            return genre, json.loads(texte.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            return None


# --- Capture de l'ecran (Windows) --------------------------------------------------------------------------------
class Capture:
    """Capture le coin haut gauche de la fenetre du jeu (GDI). Rend une fonction pix(x, y) ou None."""

    def __init__(self):
        import ctypes
        from ctypes import wintypes
        self.ct, self.wt = ctypes, wintypes
        self.u32, self.g32 = ctypes.windll.user32, ctypes.windll.gdi32
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)     # coordonnees en vrais pixels de l'ecran
        except Exception:
            try:
                self.u32.SetProcessDPIAware()
            except Exception:
                pass
        self.hwnd = None
        self.dernier = 0

    def fenetre_jeu(self):
        ct, wt, u32 = self.ct, self.wt, self.u32
        if self.hwnd and u32.IsWindow(self.hwnd) and time.time() - self.dernier < 10:
            return self.hwnd
        trouve = []
        PROTO = ct.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

        def chaque(h, _):
            if not u32.IsWindowVisible(h):
                return True
            cls = ct.create_unicode_buffer(128)
            u32.GetClassNameW(h, cls, 128)
            titre = ct.create_unicode_buffer(256)
            u32.GetWindowTextW(h, titre, 256)
            if cls.value == "waApplication Window" or titre.value.startswith("World of Warcraft"):
                trouve.append(h)
                return False
            return True
        u32.EnumWindows(PROTO(chaque), 0)
        self.hwnd = trouve[0] if trouve else None
        self.dernier = time.time()
        return self.hwnd

    def lire(self):
        ct, wt, u32, g32 = self.ct, self.wt, self.u32, self.g32
        h = self.fenetre_jeu()
        if not h or u32.IsIconic(h):
            return None, "jeu introuvable ou réduit"
        pt = wt.POINT(0, 0)
        u32.ClientToScreen(h, ct.byref(pt))
        larg, haut = ZONE
        ecran = u32.GetDC(0)
        mem = g32.CreateCompatibleDC(ecran)
        bmp = g32.CreateCompatibleBitmap(ecran, larg, haut)
        g32.SelectObject(mem, bmp)
        g32.BitBlt(mem, 0, 0, larg, haut, ecran, pt.x, pt.y, 0x00CC0020)   # SRCCOPY

        class BIH(ct.Structure):
            _fields_ = [("biSize", wt.DWORD), ("biWidth", wt.LONG), ("biHeight", wt.LONG), ("biPlanes", wt.WORD),
                        ("biBitCount", wt.WORD), ("biCompression", wt.DWORD), ("biSizeImage", wt.DWORD),
                        ("biXPelsPerMeter", wt.LONG), ("biYPelsPerMeter", wt.LONG), ("biClrUsed", wt.DWORD),
                        ("biClrImportant", wt.DWORD)]
        bih = BIH(ct.sizeof(BIH), larg, -haut, 1, 32, 0, 0, 0, 0, 0, 0)
        buf = ct.create_string_buffer(larg * haut * 4)
        g32.GetDIBits(mem, bmp, 0, haut, buf, ct.byref(bih), 0)
        g32.DeleteObject(bmp)
        g32.DeleteDC(mem)
        u32.ReleaseDC(0, ecran)
        raw = buf.raw

        def pix(x, y):
            if x < 0 or y < 0 or x >= larg or y >= haut:
                return (0, 0, 0)
            i = (y * larg + x) * 4
            return raw[i + 2], raw[i + 1], raw[i]          # BGRA -> RGB
        return pix, None


class Lecteur:
    """Boucle de lecture : rend les messages complets (genre, donnees) au fil des images."""

    def __init__(self, capture=None):
        self.capture = capture
        self.asm = Assembleur()
        self.bande = None          # (x0, y0, taille)
        self.etat = ""

    def tour(self):
        if self.capture is None:
            self.capture = Capture()
        pix, err = self.capture.lire()
        if pix is None:
            self.etat = err or ""
            return []
        return self.analyser(pix, *ZONE)

    def analyser(self, pix, larg, haut):
        vals = None
        if self.bande:
            vals = lire_image(pix, *self.bande)
        if vals is None:
            b = trouver_bande(pix, larg, haut)
            if not b:
                self.etat = "pas de bande"
                return []
            self.bande = b
            vals = lire_image(pix, *b)
            if vals is None:
                self.etat = "bande illisible"
                return []
        self.etat = "bande lue"
        d = decoder(vals)
        if not d:
            return []
        m = self.asm.ajouter(*d)
        return [m] if m else []
