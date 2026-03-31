from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.models import UserProfile
from apps.users.permissions import IsAdminRole
from apps.users.serializers import (
    RegisterSerializer,
    UserMeSerializer,
    UserMeUpdateSerializer,
    UserSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = User.objects.select_related("profile", "profile__client").get(pk=request.user.pk)
        return Response(UserMeSerializer(user).data)

    def patch(self, request):
        user = User.objects.select_related("profile", "profile__client").get(pk=request.user.pk)
        profile, _ = UserProfile.objects.get_or_create(user=user)

        ser = UserMeUpdateSerializer(user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()

        if "cover_image" in request.FILES:
            profile.cover_image = request.FILES["cover_image"]
            profile.save(update_fields=["cover_image"])
        elif request.data.get("remove_cover") in (True, "true", "1", "on"):
            if profile.cover_image:
                profile.cover_image.delete(save=False)
            profile.cover_image = None
            profile.save(update_fields=["cover_image"])

        user.refresh_from_db()
        user = User.objects.select_related("profile").get(pk=user.pk)
        return Response(UserMeSerializer(user).data)


class MePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_password = request.data.get("old_password") or ""
        new_password = request.data.get("new_password") or ""
        if len(new_password) < 8:
            return Response(
                {"detail": "La nueva contraseña debe tener al menos 8 caracteres."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not request.user.check_password(old_password):
            return Response(
                {"detail": "La contraseña actual no es correcta."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_password(new_password, user=request.user)
        except DjangoValidationError as e:
            return Response(
                {"detail": " ".join(e.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.user.set_password(new_password)
        request.user.save()
        return Response({"detail": "Contraseña actualizada."})
