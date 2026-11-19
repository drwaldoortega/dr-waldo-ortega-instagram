#!/usr/bin/env python3
"""Arma las láminas de un carrusel de Instagram (1080x1350 PNG) a partir de la plantilla.

Uso:
    python3 plantilla/armar_carrusel.py carruseles/<carpeta>/carrusel.json [--previa /tmp/previa.png]

carrusel.json:
{
  "tematica": "Salud masculina" | "Estilo de vida" | "Liderazgo",
  "laminas": [
    {
      "archivo": "01-portada.png",              # nombre del PNG de salida (en la carpeta del json)
      "plantilla": "Main.dc.html",              # archivo de plantilla/laminas/
      "props": {"fondo": "Gris plata"},         # tweaks de la lámina (opcional; la temática se agrega sola)
      "valores": {"sub": "..."},                # reemplaza valores que entrega renderVals (opcional)
      "reemplazos": [["texto de ejemplo", "texto nuevo"]],  # reemplazos literales en el HTML (opcional)
      "foto": "/ruta/absoluta/foto.jpg",        # solo láminas Foto-*: reemplaza el espacio de foto (opcional)
      "foto_posicion": "center 30%"             # encuadre de la foto (opcional, por defecto center)
    }
  ]
}

- La numeración "NN / NN" se ajusta sola según la posición y el total de láminas.
- Si un texto no cabe en la lámina, el programa avisa con DESBORDE y termina con error:
  hay que acortar el texto, nunca achicar la letra.
- Cada reemplazo debe encontrar su texto en la lámina; si no, el programa avisa y termina con error.
"""
import argparse, html, json, os, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

AQUI = Path(__file__).resolve().parent
LAMINAS, FUENTES = AQUI / "laminas", AQUI / "fuentes"
W, H = 1080, 1350

FACE = "".join(
    f"@font-face{{font-family:'{fam}';font-weight:{w};src:url('{(FUENTES / f).as_uri()}') format('woff2')}}"
    for fam, w, f in [("Barlow", 400, "barlow-latin-400-normal.woff2"),
                      ("Barlow", 600, "barlow-latin-600-normal.woff2"),
                      ("Barlow Condensed", 700, "barlow-condensed-latin-700-normal.woff2")]
) + "body{margin:0}"

JS = """([src, props]) => { class DCLogic { constructor(p) { this.props = p; this.state = {}; } }
  const C = new Function('DCLogic', src + '; return Component;')(DCLogic); return new C(props).renderVals(); }"""

MARCA_FOTO = re.compile(
    r'<svg width="72" height="72".*?</svg>\s*<span[^>]*>FOTO</span>\s*<span[^>]*>.*?</span>', re.S)


def partes(nombre):
    src = (LAMINAS / nombre).read_text(encoding="utf-8")
    cuerpo = re.search(r"<x-dc>(.*)</x-dc>", src, re.S).group(1)
    cuerpo = re.sub(r"<helmet>.*?</helmet>", "", cuerpo, flags=re.S)
    script = re.search(r'<script type="text/x-dc"[^>]*>(.*?)</script>', src, re.S).group(1)
    return cuerpo, script


def rellenar(cuerpo, v):
    cuerpo = re.sub(r'<sc-if value="\{\{(\w+)\}\}"[^>]*>(.*?)</sc-if>',
                    lambda m: m.group(2) if v.get(m.group(1)) else "", cuerpo, flags=re.S)
    return re.sub(r"\{\{\s*(\w+)\s*\}\}", lambda m: str(v[m.group(1)]), cuerpo)


def lanzar(p):
    try:
        return p.chromium.launch()
    except Exception:
        for ruta in ("/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"):
            if os.path.exists(ruta):
                return p.chromium.launch(executable_path=ruta)
        raise


def previa(pngs, salida):
    from PIL import Image
    esc, sep = 0.3, 24
    w, h = int(W * esc), int(H * esc)
    cols = min(3, len(pngs))
    filas = (len(pngs) + cols - 1) // cols
    hoja = Image.new("RGB", (cols * w + (cols + 1) * sep, filas * h + (filas + 1) * sep), (250, 250, 250))
    for i, ruta in enumerate(pngs):
        f, c = divmod(i, cols)
        hoja.paste(Image.open(ruta).convert("RGB").resize((w, h), Image.LANCZOS),
                   (sep + c * (w + sep), sep + f * (h + sep)))
    hoja.save(salida)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--previa")
    a = ap.parse_args()
    spec_path = Path(a.spec).resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    carpeta, laminas = spec_path.parent, spec["laminas"]
    total, errores, salidas = len(laminas), [], []

    with sync_playwright() as p:
        nav = lanzar(p)
        pg = nav.new_page(viewport={"width": W, "height": H})
        for i, lam in enumerate(laminas, 1):
            cuerpo, script = partes(lam["plantilla"])
            props = {"tematica": spec["tematica"], **lam.get("props", {})}
            pg.set_content("<html><body></body></html>")
            v = pg.evaluate(JS, [script, props])
            v.update(lam.get("valores", {}))
            v = {k: (html.escape(x, quote=False) if isinstance(x, str) and k != "photoBg" else x) for k, x in v.items()}
            if lam.get("foto"):
                uri = Path(lam["foto"]).resolve().as_uri()
                v["photoBg"] = f"url('{uri}') {lam.get('foto_posicion', 'center')} / cover no-repeat"
            doc = rellenar(cuerpo, v)
            if lam.get("foto"):
                doc = MARCA_FOTO.sub("", doc)
            for viejo, nuevo in lam.get("reemplazos", []):
                if viejo not in doc:
                    errores.append(f"{lam['archivo']}: no encontré el texto «{viejo}» en {lam['plantilla']}")
                doc = doc.replace(viejo, nuevo)
            doc = re.sub(r"\b\d{2} / \d{2}\b", f"{i:02d} / {total:02d}", doc)
            tmp = carpeta / f".tmp-{i:02d}.html"
            tmp.write_text(f"<!doctype html><html lang='es'><head><meta charset='utf-8'><style>{FACE}</style>"
                           f"</head><body>{doc}</body></html>", encoding="utf-8")
            pg.goto(tmp.as_uri())
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(300)
            if not pg.evaluate("document.fonts.check('700 96px \"Barlow Condensed\"') && document.fonts.check('400 40px Barlow')"):
                errores.append(f"{lam['archivo']}: no cargó la fuente Barlow")
            alto, ancho = pg.evaluate("[document.body.firstElementChild.scrollHeight, document.body.firstElementChild.scrollWidth]")
            if alto > H or ancho > W:
                errores.append(f"{lam['archivo']}: DESBORDE ({ancho}x{alto} px, máximo {W}x{H}): acorta el texto")
            salida = carpeta / lam["archivo"]
            pg.screenshot(path=str(salida), clip={"x": 0, "y": 0, "width": W, "height": H})
            tmp.unlink()
            salidas.append(salida)
            print(f"ok  {salida.name}")
        nav.close()

    if a.previa:
        previa(salidas, a.previa)
        print(f"previa: {a.previa}")
    if errores:
        print("\n".join(errores), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
