from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from tenancy.models import Organization, OrganizationMember

from .models import User
from .serializers import LoginSerializer, RegisterRequestSerializer, UserSerializer


def _default_organization_name(user):
    basis = (user.full_name or "").strip() or user.email.split("@")[0]
    return f"{basis}'s Organization"


class RegisterView(APIView):
    """Register a user and create their personal organization (OWNER)."""

    def post(self, request):
        serializer = RegisterRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        email = data["email"].lower()

        if User.objects.filter(email=email).exists():
            return Response(
                {"detail": "Email already registered"},
                status=status.HTTP_409_CONFLICT,
            )

        with transaction.atomic():
            user = User.objects.create_user(
                email=email,
                full_name=data["full_name"],
                password=data["password"],
            )
            org = Organization.objects.create(
                name=_default_organization_name(user)
            )
            OrganizationMember.objects.create(
                organization=org, user=user, role=OrganizationMember.Role.OWNER
            )
            user.default_organization = org
            user.save(update_fields=["default_organization"])

        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)