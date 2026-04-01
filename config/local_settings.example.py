"""
`config/local_settings.py` no se versiona (ver `backend/.gitignore`).

En producción debe alinearse con **`local_settings.production.example.py`**
(activa ajustes solo si `POSTGRES_DB` existe y `USE_SQLITE` no está en true).

En desarrollo, con `USE_SQLITE=true` en `.env`, este archivo no fuerza modo producción.
"""
