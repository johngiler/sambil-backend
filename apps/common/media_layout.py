"""
Convención de rutas bajo ``MEDIA_ROOT`` (relativas al storage).

- **Centros comerciales** → ``centers/covers/AÑO/MES/`` (solo portadas de centro).
- **Tomas (AdSpace)** → ``spaces/gallery/AÑO/MES/`` (galería) y ``spaces/covers/AÑO/MES/`` (portada copiada).

Así ``tree media/`` agrupa por dominio (``centers/`` vs ``spaces/``), sin mezclar con
``covers/users`` u otros prefijos legacy.
"""

# Valores para ImageField(upload_to=…)
UPLOAD_CENTERS_COVERS = "centers/covers/%Y/%m/"
UPLOAD_SPACES_COVERS = "spaces/covers/%Y/%m/"
UPLOAD_SPACES_GALLERY = "spaces/gallery/%Y/%m/"
