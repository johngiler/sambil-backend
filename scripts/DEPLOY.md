# Deploy API Sambil (api.publivalla.com)

VPS Ubuntu dedicado. Código en `/home/git/backend`, Gunicorn con systemd (`sambil-api`), Nginx + Let’s Encrypt.

## Requisitos locales

- SSH: Host `sambil-api` en `~/.ssh/config` apuntando a `api.publivalla.com` (usuario con `sudo`, p. ej. `root`).
- En el servidor **no** se suben por rsync: `/home/git/backend/.env` ni `config/local_settings.py` (configurar una vez a mano).

## Deploy habitual

Desde el directorio **backend** del repo (máquina de desarrollo):

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

El script hace `rsync` (excluye `.venv`, `.env`, `local_settings.py`, `.git`, `staticfiles`, `media`), `chown` a `git`, `pip install`, `migrate`, `collectstatic` y reinicia `sambil-api` + `reload` de Nginx.

## Setup una sola vez en el servidor

### 1. Paquetes de sistema

Como root en `api.publivalla.com`:

```bash
cd /home/git/backend   # o donde tengas el repo clonado
bash scripts/setup.sh
```

**Nota (svglib / Cairo):** En `requirements.txt` está fijado `svglib==1.5.1` para que `pip install` no arrastre `pycairo` (hace falta `pkg-config` y `libcairo2-dev` en el servidor si se compila desde fuente). Si algún día subís a `svglib>=1.6`, instalad antes en el servidor algo como: `apt-get install -y pkg-config libcairo2-dev` (y herramientas de build si hace falta).

### 2. Usuario, código y entorno virtual

- Asegurar `/home/git/backend` con propietario `git:git`.
- Copiar o clonar el proyecto ahí.
- Crear carpeta de medios (Nginx sirve `/media/` desde disco):

  ```bash
  sudo -u git mkdir -p /home/git/backend/media
  ```

- Como `git`:

```bash
cd /home/git/backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 3. `.env` en el servidor

En el repo (solo en tu máquina, **no** se sube a git) puede existir **`backend/.env.production`** con Postgres, `USE_SQLITE=false`, clave Django y CORS ya definidos. Copialo al servidor:

```bash
scp backend/.env.production sambil-api:/home/git/backend/.env
```

Si generás otro entorno desde cero, usá **`.env.production.example`** como guía y reemplazá secretos.

`scripts/init_db.sh` hace `source` del `.env`: evitá caracteres tipo `!` sin comillar en valores; el `.env.production` del proyecto usa claves compatibles.

### 4. `local_settings.py`

Copiar al servidor (tampoco entra en `rsync`):

```bash
scp config/local_settings.py sambil-api:/home/git/backend/config/local_settings.py
```

Debe coincidir con **`local_settings.production.example.py`** (modo prod solo si `POSTGRES_DB` está definido y `USE_SQLITE` no es true).

### 5. Base de datos

Con `.env` ya colocado en `/home/git/backend/.env`:

```bash
sudo bash scripts/init_db.sh
```

### 6. Nginx y TLS

1. Copiar `scripts/nginx-api-http-only.conf` a `sites-available`, habilitar sitio, `nginx -t && systemctl reload nginx`.
2. Emitir certificado, por ejemplo:

   ```bash
   certbot certonly --webroot -w /var/www/letsencrypt -d api.publivalla.com
   ```

3. Copiar `scripts/nginx-api.publivalla.com.conf` a `sites-available`, enlazar en `sites-enabled`, `nginx -t && systemctl reload nginx`.

### 7. Systemd

```bash
sudo cp scripts/sambil-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sambil-api
```

### 8. Migraciones y estáticos (primera vez)

```bash
sudo -u git -H bash -c 'cd /home/git/backend && .venv/bin/python manage.py migrate --noinput && .venv/bin/python manage.py collectstatic --noinput'
```

## CORS

En producción, `local_settings.py` (plantilla) incluye `https://sambil.publivalla.com`. Orígenes extra: variable `CORS_ALLOWED_ORIGINS` o `CORS_ORIGINS` en `.env` (lista separada por comas).

## Notas

- **Media:** Nginx sirve `/media/` desde `/home/git/backend/media/`. Ese directorio no se sincroniza con `deploy.sh` para no borrar subidas en el servidor.
- **Puerto:** Gunicorn escucha en `127.0.0.1:8000`; Nginx hace proxy en HTTPS.
- **403 en `/static/` (admin sin CSS):** `www-data` debe **recorrer** `/home/git` y `/home/git/backend` (`chmod 755`). Los directorios `staticfiles/` y `media/` usan **grupo `www-data`**, `chown git:www-data` y **setgid** (`chmod 2775` en carpetas, `664` en ficheros) para que Nginx lea sin `o+r` y los nuevos ficheros de `collectstatic` hereden el grupo. `setup.sh` añade `git` al grupo `www-data` para subidas a `media/`.
