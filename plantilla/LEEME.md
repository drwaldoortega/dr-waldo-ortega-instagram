# Plantilla de carruseles

- `laminas/`: copia de la plantilla maestra (artefacto de diseño "Plantilla de carrusel Instagram — Dr. Waldo Ortega"). Si la plantilla maestra cambia, se vuelve a copiar aquí.
- `fuentes/`: Barlow y Barlow Condensed (licencia SIL Open Font License, en `OFL.txt`).
- `armar_carrusel.py`: convierte un `carrusel.json` en láminas PNG de 1080×1350. Las instrucciones de uso están al inicio del archivo.

```
python3 plantilla/armar_carrusel.py carruseles/AAAA-MM-DD-tematica-tema/carrusel.json --previa /tmp/previa.png
```

Requiere Python con Playwright y Pillow. Si un texto no cabe, el programa avisa con DESBORDE: se acorta el texto, nunca se achica la letra.
