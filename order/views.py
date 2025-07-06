from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Order
from .serializers import (
    OrderSerializer,
    OrderCreateSerializer,
    OrderStatusUpdateSerializer
)
from accounts.models import User


class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.role == 'admin':
            return Order.objects.all()
        elif user.role == 'delivery_man':
            return Order.objects.filter(delivery_man=user)
        else:
            return Order.objects.filter(user=user)

    def get_serializer_class(self):
        user = self.request.user
        action = self.action

        if action == 'create':
            return OrderCreateSerializer
        elif action in ['partial_update', 'update']:
            if user.role == 'delivery_man':
                return OrderStatusUpdateSerializer
        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def update(self, request, *args, **kwargs):
        order = self.get_object()

        if request.user.role == 'delivery_man':
            if order.delivery_man != request.user:
                return Response({"detail": "Not allowed to update this order."}, status=status.HTTP_403_FORBIDDEN)
            return super().update(request, *args, **kwargs)

        if request.user.role == 'admin':
            delivery_man_id = request.data.get("delivery_man_id")
            if delivery_man_id:
                try:
                    delivery_man = User.objects.get(id=delivery_man_id, role='delivery_man')
                    order.delivery_man = delivery_man
                    order.save()
                except User.DoesNotExist:
                    return Response({"detail": "Invalid delivery man ID"}, status=status.HTTP_400_BAD_REQUEST)

        return super().update(request, *args, **kwargs)
