from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from tenancy.models import OrganizationMember

from .models import User


class RegisterRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    full_name = serializers.CharField(min_length=3, max_length=255)
    password = serializers.CharField(min_length=6, max_length=255, write_only=True)


class LoginSerializer(TokenObtainPairSerializer):
    """JWT login matching the legacy ``{access_token, token_type}`` contract."""

    def validate(self, attrs):
        email = attrs.get(self.username_field)
        if email:
            attrs[self.username_field] = email.lower()
        try:
            data = super().validate(attrs)
        except AuthenticationFailed:
            raise AuthenticationFailed("Invalid email or password")
        return {
            "access_token": data["access"],
            "token_type": "bearer",
            "refresh": data["refresh"],
        }


class OrganizationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    role = serializers.CharField()


class OrganizationRefSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class UserSerializer(serializers.ModelSerializer):
    organizations = serializers.SerializerMethodField()
    default_organization = OrganizationRefSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "default_organization", "organizations"]

    def get_organizations(self, obj):
        memberships = list(
            OrganizationMember.objects.filter(user=obj)
            .select_related("organization")
            .order_by("organization__name")
        )
        return OrganizationSerializer(
            [
                {"id": m.organization_id, "name": m.organization.name, "role": m.role}
                for m in memberships
            ],
            many=True,
        ).data