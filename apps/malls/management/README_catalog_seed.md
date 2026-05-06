# Seed de catálogo (PDF → data.json)

El comando `seed_production_catalog` parsea un PDF y genera un JSON **de tránsito** que luego aplica a BD.

## Ubicación del JSON

El archivo se escribe en:

- `backend/data/catalog/data.json`

Ese directorio está **gitignored** (`backend/.gitignore`) porque es salida generada y se sobreescribe en cada corrida.

## Flujo

1) Ejecutas el comando con `--pdf`.
2) Se genera/reescribe `data.json` normalizado.
3) Se valida contra BD (evita mezclar códigos entre centros).
4) Se aplican cambios a `ShoppingCenter` y `AdSpace`.
5) Si pasas `--images-dir`, intenta cargar galería/portada (opcional).

## Comandos

Solo parseo (no escribe en BD):

```bash
python manage.py seed_production_catalog --pdf "/ruta/catalogo.pdf" --dry-run
```

Parseo + apply:

```bash
python manage.py seed_production_catalog --pdf "/ruta/catalogo.pdf"
```

Con imágenes opcionales:

```bash
python manage.py seed_production_catalog --pdf "/ruta/catalogo.pdf" --images-dir "/ruta/imagenes"
```

