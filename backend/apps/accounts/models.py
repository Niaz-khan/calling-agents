from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    """Email-based user account.

    Login identity is email; ``username`` is not used.
    """

    class PlatformRole(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", "Super admin"
        PLATFORM_ADMIN = "PLATFORM_ADMIN", "Platform admin"
        SUPPORT_ADMIN = "SUPPORT_ADMIN", "Support admin"
        CONTENT_ADMIN = "CONTENT_ADMIN", "Content admin"

    username = None
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    platform_role = models.CharField(
        max_length=32,
        choices=PlatformRole.choices,
        default="",
        blank=True,
        help_text="Platform-level role. Empty means a normal business user.",
    )
    default_organization = models.ForeignKey(
        "tenancy.Organization",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="default_for_users",
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "accounts_user"

    @property
    def is_platform_user(self):
        """True for anyone authorized to use the /admin platform area."""
        return bool(self.platform_role) or self.is_superuser

    def set_platform_role(self, role):
        """Promote/demote a user to a platform role (implies Django staff)."""
        self.platform_role = role
        self.is_staff = bool(role)
        self.save(update_fields=["platform_role", "is_staff"])

    def __str__(self):
        return self.email