from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.ad_spaces.models import AdSpace, AdSpaceStatus, AdSpaceType
from apps.malls.models import ShoppingCenter

# Centros en portada (orden + datos dummy). SCC/SLC tienen catálogo público (`marketplace_catalog_enabled`).
CENTERS_SEED = [
    (
        "SCC",
        {
            "name": "Sambil Caracas",
            "city": "Caracas",
            "district": "Chacao",
            "address": "Av. Libertador, Chacao",
            "listing_order": 10,
        },
    ),
    (
        "SLC",
        {
            "name": "Sambil La Candelaria",
            "city": "Caracas",
            "district": "La Candelaria",
            "address": "La Candelaria, Caracas",
            "listing_order": 20,
        },
    ),
    (
        "SLV",
        {
            "name": "Sambil Valencia",
            "city": "Valencia",
            "district": "San Diego",
            "address": "Valencia — San Diego",
            "listing_order": 30,
        },
    ),
    (
        "SMZ",
        {
            "name": "Sambil Maracaibo",
            "city": "Maracaibo",
            "district": "",
            "address": "Maracaibo",
            "listing_order": 40,
        },
    ),
    (
        "SMP",
        {
            "name": "Sambil Margarita",
            "city": "Porlamar",
            "district": "Margarita",
            "address": "Porlamar, Margarita",
            "listing_order": 50,
        },
    ),
    (
        "SBQ",
        {
            "name": "Sambil Barquisimeto",
            "city": "Barquisimeto",
            "district": "",
            "address": "Barquisimeto",
            "listing_order": 60,
        },
    ),
    (
        "SPO",
        {
            "name": "Sambil Puerto Ordaz",
            "city": "Puerto Ordaz",
            "district": "",
            "address": "Puerto Ordaz",
            "listing_order": 70,
        },
    ),
    (
        "SMD",
        {
            "name": "Sambil Mérida",
            "city": "Mérida",
            "district": "",
            "address": "Mérida",
            "listing_order": 80,
        },
    ),
]


class Command(BaseCommand):
    help = "Carga centros dummy para la portada y tomas demo (SCC / SLC)."

    def handle(self, *args, **options):
        for code, fields in CENTERS_SEED:
            ShoppingCenter.objects.update_or_create(
                code=code,
                defaults={
                    **fields,
                    "on_homepage": True,
                    "country": "Venezuela",
                    "marketplace_catalog_enabled": code in ("SCC", "SLC"),
                },
            )

        scc = ShoppingCenter.objects.get(code="SCC")
        slc = ShoppingCenter.objects.get(code="SLC")
        for code, center, title, price in [
            ("SCC-T1", scc, "Fachada principal", Decimal("5000")),
            ("SCC-T2", scc, "Pendones plaza", Decimal("3500")),
            ("SLC-T1A", slc, "Ascensor vista calle", Decimal("2800")),
        ]:
            AdSpace.objects.get_or_create(
                code=code,
                defaults={
                    "shopping_center": center,
                    "type": AdSpaceType.BILLBOARD,
                    "title": title,
                    "monthly_price_usd": price,
                    "status": AdSpaceStatus.AVAILABLE,
                },
            )
        self.stdout.write(self.style.SUCCESS("Centros y tomas demo listos."))
