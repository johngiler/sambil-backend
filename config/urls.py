from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from apps.ad_spaces.admin_viewsets import AdSpaceAdminViewSet
from apps.ad_spaces.views import AdSpaceViewSet
from apps.clients.views import ClientViewSet, MyCompanyView
from apps.malls.admin_viewsets import ShoppingCenterAdminViewSet
from apps.malls.views import ShoppingCenterViewSet
from apps.orders.views import OrderViewSet
from apps.users.admin_viewsets import UserAdminViewSet
from apps.users.views import MePasswordView, MeView, RegisterView

router = DefaultRouter()
router.register(r"centers", ShoppingCenterViewSet, basename="center")
router.register(r"spaces", AdSpaceViewSet, basename="space")
router.register(r"clients", ClientViewSet, basename="client")
router.register(r"orders", OrderViewSet, basename="order")

router.register(r"admin/centers", ShoppingCenterAdminViewSet, basename="admin-center")
router.register(r"admin/spaces", AdSpaceAdminViewSet, basename="admin-space")
router.register(r"admin/users", UserAdminViewSet, basename="admin-user")

catalog_router = DefaultRouter()
catalog_router.register(r"centers", ShoppingCenterViewSet, basename="catalog-center")
catalog_router.register(r"spaces", AdSpaceViewSet, basename="catalog-space")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("api/catalog/", include(catalog_router.urls)),
    path("api/me/company/", MyCompanyView.as_view(), name="my-company"),
    path("api/auth/me/", MeView.as_view(), name="auth-me"),
    path("api/auth/me/password/", MePasswordView.as_view(), name="auth-me-password"),
    path("api/auth/register/", RegisterView.as_view(), name="register"),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
