from django.db.models import Q

from tenancy.drf import OrganizationModelViewSet

from .models import Customer
from .serializers import CustomerSerializer


class CustomerViewSet(OrganizationModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    not_found_detail = "Customer not found"

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.query_params.get("q")
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(phone_number__icontains=query)
                | Q(email__icontains=query)
            )
        return queryset