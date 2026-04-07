"""
Rellena centros comerciales y tomas (AdSpace) de demostración por cada Workspace (owner) activo.

Solo crea CC y tomas: no usuarios, clientes ni pedidos.

Ejecutar desde backend:
  python manage.py shell < scripts/seed_demo_bulk.py

Idempotencia: antes de crear, elimina CC del workspace cuyo código coincide con el patrón
generado desde el slug (máx. 8 caracteres) + índice 01–10; las tomas se borran en cascada.
Códigos de toma: {código_CC}-T{n} (nomenclatura fase 1).

Variables opcionales:
  SEED_WORKSPACE_SLUG — si está definido, solo ese slug (debe existir y estar activo).
"""
from decimal import Decimal

from django.db import transaction

from apps.ad_spaces.models import AdSpace, AdSpaceStatus, AdSpaceType
from apps.malls.models import ShoppingCenter
from apps.workspaces.models import Workspace

# Diez ciudades distintas (Venezuela); cada CC usa una.
CITY_ROWS = [
    {
        "city": "Caracas",
        "district": "Chacao",
        "address": "Av. Francisco de Miranda, esquina Av. Don Esteban. Urbanización Los Palos Grandes.",
        "phone": "+58 212-276-4410",
        "blurb": "Alto tráfico peatonal y vehicular; conexión con zona residencial y oficinas.",
    },
    {
        "city": "Maracaibo",
        "district": "5 de Julio",
        "address": "Av. 5 de Julio, sector casco comercial, frente a zona bancaria.",
        "phone": "+58 261-793-2201",
        "blurb": "Núcleo financiero y retail de referencia en el estado Zulia.",
    },
    {
        "city": "Valencia",
        "district": "Prebo",
        "address": "Av. Henry Ford, centro comercial anclado en corredor vial principal.",
        "phone": "+58 241-825-1188",
        "blurb": "Flujo constante de familias y viajeros hacia el interior del país.",
    },
    {
        "city": "Barquisimeto",
        "district": "Centro",
        "address": "Carrera 19 con calle 25, sector céntrico de Barquisimeto.",
        "phone": "+58 251-231-4490",
        "blurb": "Zona de alta visibilidad en el epicentro comercial de Lara.",
    },
    {
        "city": "Maracay",
        "district": "Urbanización El Centro",
        "address": "Av. Bolívar, tramo comercial principal, acceso desde autopista regional.",
        "phone": "+58 243-551-9022",
        "blurb": "Concentración de oficinas públicas y comercio detallista.",
    },
    {
        "city": "Ciudad Guayana",
        "district": "Puerto Ordaz",
        "address": "Av. Las Américas, zona industrial y residencial en expansión.",
        "phone": "+58 286-931-7744",
        "blurb": "Corredor con fuerte componente industrial y consumo masivo.",
    },
    {
        "city": "Maturín",
        "district": "Centro",
        "address": "Av. Roscio, sector comercial céntrico de Maturín.",
        "phone": "+58 291-641-3355",
        "blurb": "Punto neurálgico del comercio en el estado Monagas.",
    },
    {
        "city": "Barinas",
        "district": "Altamira",
        "address": "Av. Alberto Arvelo Larriva, zona de crecimiento comercial.",
        "phone": "+58 273-532-8810",
        "blurb": "Área con alta afluencia de fines de semana y eventos locales.",
    },
    {
        "city": "San Cristóbal",
        "district": "Barrio Obrero",
        "address": "Av. Principal de Capacho, corredor comercial transfronterizo.",
        "phone": "+58 276-346-2299",
        "blurb": "Movimiento comercial ligado al flujo regional y turismo de compras.",
    },
    {
        "city": "Puerto La Cruz",
        "district": "Paseo Colón",
        "address": "Av. Bolívar, frente al paseo peatonal y zona gastronómica.",
        "phone": "+58 281-331-4477",
        "blurb": "Vista al mar y alta circulación en horario extendido.",
    },
]

# Diez plantillas de toma por CC: tipo, título, descripción corta, medidas, zona, nivel, precio base
SPACE_BLUEPRINTS = [
    (
        AdSpaceType.VALLA_VERTICAL,
        "Valla vertical — acceso principal",
        "Cara hacia el vestíbulo principal; iluminación LED perimetral en buen estado.",
        Decimal("4.20"),
        Decimal("6.00"),
        "Hall de ingreso",
        "Nivel feria",
        Decimal("520"),
    ),
    (
        AdSpaceType.PENDON_PASILLO,
        "Pendón pasillo central — corredor A",
        "Ubicación entre anclas de moda y cafetería; tráfico peatonal continuo.",
        Decimal("8.00"),
        Decimal("2.40"),
        "Pasillo central",
        "Primer nivel",
        Decimal("380"),
    ),
    (
        AdSpaceType.PENDON_ATRIO,
        "Pendón colgante — atrio central",
        "Doble faz visible desde planta baja y mezzanine.",
        Decimal("6.00"),
        Decimal("3.00"),
        "Atrio",
        "Doble altura",
        Decimal("610"),
    ),
    (
        AdSpaceType.VALLA_HORIZONTAL,
        "Valla horizontal — zona de ascensores",
        "Superficie panorámica junto a núcleo de ascensores y escaleras mecánicas.",
        Decimal("12.00"),
        Decimal("2.80"),
        "Núcleo vertical",
        "Segundo nivel",
        Decimal("445"),
    ),
    (
        AdSpaceType.PENDON_BALCON,
        "Pendón de balcón — vista a plaza interior",
        "Bolsillo superior estándar para lona tensada; montaje coordinado con mantenimiento.",
        Decimal("5.50"),
        Decimal("1.80"),
        "Balcón plaza interior",
        "Segundo nivel",
        Decimal("290"),
    ),
    (
        AdSpaceType.PENDON_COLUMNA,
        "Envolvente de columna — pasillo B",
        "Cuatro caras visibles; ideal para campañas de corta duración.",
        Decimal("0.90"),
        Decimal("2.60"),
        "Pasillo lateral",
        "Primer nivel",
        Decimal("175"),
    ),
    (
        AdSpaceType.GIGANTOGRAFIA_FACHADA,
        "Gigantografía — fachada peatonal",
        "Gran formato sobre muro estructural; requiere estudio de viento local.",
        Decimal("14.00"),
        Decimal("5.50"),
        "Fachada",
        "Exterior",
        Decimal("890"),
    ),
    (
        AdSpaceType.PENDON_PLAZA,
        "Pendón plaza jardín",
        "Área semiabierta con eventos los fines de semana; alta recordación de marca.",
        Decimal("7.20"),
        Decimal("2.20"),
        "Plaza jardín",
        "Nivel feria",
        Decimal("410"),
    ),
    (
        AdSpaceType.ELEVATOR,
        "Panel en cabina de ascensor — torre norte",
        "Cuatro cabinas con rotación de creatividades digitales y estáticas.",
        Decimal("1.20"),
        Decimal("1.80"),
        "Torre norte",
        "Multinivel",
        Decimal("265"),
    ),
    (
        AdSpaceType.BANNER,
        "Banner perimetral — estacionamiento cubierto",
        "Carril de ingreso y salida de vehículos; visibilidad en marcha lenta.",
        Decimal("10.00"),
        Decimal("1.20"),
        "Estacionamiento",
        "Subsuelo",
        Decimal("320"),
    ),
]


def _slug_alnum_upper(slug: str) -> str:
    return "".join(c for c in (slug or "").upper() if c.isalnum())


def center_code_for(ws: Workspace, index_1_to_10: int) -> str:
    """Código único global ≤8: prefijo del slug + dos dígitos."""
    base = _slug_alnum_upper(ws.slug)
    if len(base) < 2:
        base = f"WS{ws.pk}"
    if len(base) > 6:
        base = base[:6]
    code = f"{base}{index_1_to_10:02d}"
    return code[-8:] if len(code) > 8 else code


def ad_space_code(center_code: str, index_1_to_10: int) -> str:
    """Código de toma: {CC}-T{n} (nomenclatura fase 1), único global ≤32."""
    return f"{str(center_code).strip().upper()}-T{index_1_to_10}"


def brand_display_name(ws: Workspace) -> str:
    t = (getattr(ws, "marketplace_title", None) or "").strip()
    if t:
        return t
    return (ws.name or ws.slug).strip() or ws.slug


def contact_email_for(ws: Workspace, local_part: str) -> str:
    """Correo de muestra (dominio example.com reservado para documentación)."""
    slug = _slug_alnum_upper(ws.slug).lower() or "centro"
    return f"{local_part}.{slug}@example.com"


def workspaces_to_seed():
    import os

    only = (os.environ.get("SEED_WORKSPACE_SLUG") or "").strip().lower()
    qs = Workspace.objects.filter(is_active=True).order_by("slug")
    if only:
        qs = qs.filter(slug=only)
    return list(qs)


def main():
    import os

    wss = workspaces_to_seed()
    if not wss:
        slug = (os.environ.get("SEED_WORKSPACE_SLUG") or "").strip()
        raise RuntimeError(
            "No hay workspaces activos para sembrar."
            + (f" (slug «{slug}» no existe o está inactivo)" if slug else "")
        )

    total_centers = 0
    total_spaces = 0

    with transaction.atomic():
        for ws in wss:
            codes = [center_code_for(ws, i) for i in range(1, 11)]
            ShoppingCenter.objects.filter(workspace=ws, code__in=codes).delete()

            brand = brand_display_name(ws)

            for idx, row in enumerate(CITY_ROWS, start=1):
                cc_code = codes[idx - 1]
                name = f"{brand} · {row['city']}"
                contact = contact_email_for(ws, f"cc{idx}")

                center = ShoppingCenter.objects.create(
                    workspace=ws,
                    name=name,
                    code=cc_code,
                    city=row["city"],
                    district=row["district"],
                    address=row["address"],
                    country="Venezuela",
                    phone=row["phone"],
                    contact_email=contact,
                    description=(
                        f"Centro integrado al marketplace {brand} en {row['city']}. "
                        f"{row['blurb']} Coordinación de montajes y mantenimiento según manual del CC."
                    ),
                    on_homepage=True,
                    listing_order=idx,
                    marketplace_catalog_enabled=True,
                    is_active=True,
                )
                total_centers += 1

                for sidx, bp in enumerate(SPACE_BLUEPRINTS, start=1):
                    (
                        sp_type,
                        title,
                        desc,
                        width,
                        height,
                        zone,
                        level,
                        price,
                    ) = bp
                    # Ligera variación de precio por índice para que no queden todos idénticos
                    price_adj = price + Decimal((idx + sidx) % 7) * Decimal("12")

                    status_cycle = (
                        AdSpaceStatus.AVAILABLE,
                        AdSpaceStatus.AVAILABLE,
                        AdSpaceStatus.RESERVED,
                    )
                    status = status_cycle[sidx % 3]

                    AdSpace.objects.create(
                        code=ad_space_code(cc_code, sidx),
                        shopping_center=center,
                        type=sp_type,
                        title=title,
                        description=desc,
                        width=width,
                        height=height,
                        monthly_price_usd=price_adj,
                        status=status,
                        level=level,
                        venue_zone=zone,
                        location_description=(
                            f"Referencia interna: módulo {sidx}, {zone.lower()}, {level.lower()}."
                        ),
                        material="Lona frontlit / vinil según especificación del fabricante aprobado.",
                        is_active=True,
                    )
                    total_spaces += 1

    print("OK seed CC + tomas (por owner activo):")
    for ws in wss:
        codes = [center_code_for(ws, i) for i in range(1, 11)]
        n_cc = ShoppingCenter.objects.filter(workspace=ws, code__in=codes).count()
        n_sp = AdSpace.objects.filter(shopping_center__code__in=codes).count()
        print(f"  {ws.slug}: {n_cc} centros sembrados, {n_sp} tomas (objetivo 10 CC × 10 tomas = 100).")
    print(f"  Totales esta corrida: {total_centers} CC, {total_spaces} tomas creados.")


# Con `python manage.py shell < scripts/seed_demo_bulk.py`, __name__ no es "__main__";
# la llamada directa es la forma soportada. No importar este módulo desde otro código.
main()
