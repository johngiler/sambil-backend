"""
Carga datos demo en BD (ejecutar: python manage.py shell < scripts/seed_demo_bulk.py).
Elimina filas previas con prefijo DEMO_SEED_* y recrea:
- 20 centros, 6 clientes, 3 usuarios cliente (perfil asociado a cliente),
- 24 tomas, 20 pedidos + ítems, 20 bloques disponibilidad, 20 facturas,
- 20 transiciones workflow, 20 eventos de estado.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from apps.ad_spaces.models import AdSpace, AdSpaceStatus, AdSpaceType
from apps.availability.models import AvailabilityBlock, AvailabilityBlockType
from apps.billing.models import Invoice, InvoiceStatus
from apps.clients.models import Client, ClientStatus
from apps.malls.models import ShoppingCenter
from apps.orders.models import Order, OrderItem, OrderStatus, OrderStatusEvent
from apps.users.models import UserProfile
from apps.workflow.models import WorkflowTransition
from apps.workspaces.utils import get_default_workspace

DEMO_CENTER_CODES = [f"DS{i:02d}" for i in range(1, 21)]


def main():
    with transaction.atomic():
        # Borrado en orden inverso (FKs)
        OrderStatusEvent.objects.filter(note__startswith="DEMO_SEED").delete()
        WorkflowTransition.objects.filter(note__startswith="DEMO_SEED").delete()
        Invoice.objects.filter(number__startswith="DEMO-INV-").delete()
        OrderItem.objects.filter(order__client__rif__startswith="DEMO-RIF-").delete()
        Order.objects.filter(client__rif__startswith="DEMO-RIF-").delete()
        AvailabilityBlock.objects.filter(
            ad_space__code__startswith="DEMO-SPACE-"
        ).delete()
        AdSpace.objects.filter(code__startswith="DEMO-SPACE-").delete()
        ShoppingCenter.objects.filter(code__in=DEMO_CENTER_CODES).delete()

        for u in User.objects.filter(username__startswith="demo_client_"):
            u.delete()

        Client.objects.filter(rif__startswith="DEMO-RIF-").delete()

        ws = get_default_workspace()
        if not ws:
            raise RuntimeError(
                "No hay workspace activo. Crea uno (p. ej. slug «sambil») o define DEFAULT_WORKSPACE_SLUG."
            )

        # 20 centros (código único ≤8, prefijo DS para borrado idempotente)
        centers = []
        for i in range(1, 21):
            c = ShoppingCenter.objects.create(
                workspace=ws,
                name=f"Centro demo seed {i}",
                code=f"DS{i:02d}",
                city="Caracas",
                district="Chacao" if i % 2 else "La Candelaria",
                address=f"Av. Demo {i}, local",
                country="Venezuela",
                phone=f"+58-212-{1000000 + i}",
                contact_email=f"centro{i}@demo-seed.local",
                description=f"Centro comercial de prueba #{i}",
                on_homepage=True,
                listing_order=i,
                marketplace_catalog_enabled=True,
                is_active=True,
            )
            centers.append(c)

        # 6 clientes
        clients = []
        for i in range(1, 7):
            cl = Client.objects.create(
                workspace=ws,
                company_name=f"Empresa demo seed {i}",
                rif=f"DEMO-RIF-{i:03d}",
                contact_name=f"Contacto {i}",
                email=f"cliente{i}@demo-seed.local",
                phone=f"+58-424-{5000000 + i}",
                address=f"Zona industrial {i}",
                city="Caracas",
                status=ClientStatus.ACTIVE,
                is_active=True,
            )
            clients.append(cl)

        # 3 usuarios cliente → asociados a clientes 1..3
        client_users = []
        for i in range(1, 4):
            username = f"demo_client_{i}"
            u = User.objects.create_user(
                username=username,
                email=f"{username}@demo-seed.local",
                password="DemoSeed123!",
                first_name=f"Usuario",
                last_name=f"Cliente{i}",
            )
            p = u.profile
            p.role = UserProfile.Role.CLIENT
            p.client = clients[i - 1]
            p.save(update_fields=["role", "client"])
            client_users.append(u)

        types_cycle = [c[0] for c in AdSpaceType.choices]
        spaces = []
        for n in range(1, 25):
            center = centers[(n - 1) % len(centers)]
            code = f"DEMO-SPACE-{n:03d}"
            sp = AdSpace.objects.create(
                code=code,
                shopping_center=center,
                type=types_cycle[n % len(types_cycle)],
                title=f"Toma demo {n}",
                description=f"Espacio publicitario de prueba número {n}",
                width=Decimal("3.50"),
                height=Decimal("2.00"),
                monthly_price_usd=Decimal(str(200 + n * 15)),
                status=AdSpaceStatus.AVAILABLE if n % 3 else AdSpaceStatus.RESERVED,
                level=f"Nivel {(n % 5) + 1}",
                venue_zone=f"Zona {n % 7}",
                is_active=True,
            )
            spaces.append(sp)

        today = date.today()
        orders = []
        for o in range(1, 21):
            client = clients[(o - 1) % len(clients)]
            ord_ = Order.objects.create(
                client=client,
                status=OrderStatus.SUBMITTED if o % 2 else OrderStatus.DRAFT,
                total_amount=Decimal(str(o * 150)),
                submitted_at=timezone.now() if o % 2 else None,
                is_active=True,
            )
            orders.append(ord_)
            sp = spaces[(o - 1) % len(spaces)]
            OrderItem.objects.create(
                order=ord_,
                ad_space=sp,
                start_date=today + timedelta(days=10),
                end_date=today + timedelta(days=100),
                monthly_price=sp.monthly_price_usd,
                subtotal=Decimal(str(o * 150)),
                is_active=True,
            )

        for b in range(1, 21):
            sp = spaces[b % len(spaces)]
            AvailabilityBlock.objects.create(
                ad_space=sp,
                start_date=today + timedelta(days=5 + b),
                end_date=today + timedelta(days=30 + b),
                type=AvailabilityBlockType.RESERVED,
                is_active=True,
            )

        for inv_n, ord_ in enumerate(orders[:20], start=1):
            Invoice.objects.create(
                order=ord_,
                number=f"DEMO-INV-{inv_n:04d}",
                amount=ord_.total_amount,
                status=InvoiceStatus.ISSUED if inv_n % 2 else InvoiceStatus.DRAFT,
                is_active=True,
            )

        for w in range(1, 21):
            ord_ = orders[w % len(orders)]
            WorkflowTransition.objects.create(
                order=ord_,
                from_status=OrderStatus.DRAFT,
                to_status=OrderStatus.SUBMITTED,
                note=f"DEMO_SEED transición {w}",
                is_active=True,
            )

        admin_user = User.objects.filter(is_superuser=True).first()
        for e in range(1, 21):
            ord_ = orders[e % len(orders)]
            OrderStatusEvent.objects.create(
                order=ord_,
                from_status="",
                to_status=OrderStatus.SUBMITTED,
                created_at=timezone.now(),
                actor=admin_user,
                note=f"DEMO_SEED evento {e}",
            )

    print("OK seed DEMO:")
    print(f"  centros demo DS: {ShoppingCenter.objects.filter(code__in=DEMO_CENTER_CODES).count()}")
    print(f"  clientes DEMO-RIF: {Client.objects.filter(rif__startswith='DEMO-RIF-').count()}")
    print(f"  usuarios demo_client_: {User.objects.filter(username__startswith='demo_client_').count()}")
    print(f"  tomas DEMO-SPACE: {AdSpace.objects.filter(code__startswith='DEMO-SPACE-').count()}")
    print(f"  pedidos (clientes demo): {Order.objects.filter(client__rif__startswith='DEMO-RIF-').count()}")
    print("  Login prueba: demo_client_1 / DemoSeed123! (y _2, _3)")


main()
