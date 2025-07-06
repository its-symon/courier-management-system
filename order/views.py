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

        if not user.is_authenticated:
            return Order.objects.none()

        if user.role == 'admin':
            return Order.objects.all().select_related('payment')
        elif user.role == 'delivery_man':
            return Order.objects.filter(delivery_man=user).select_related('payment')
        else:
            return Order.objects.filter(user=user).select_related('payment')

    def get_serializer_class(self):
        user = self.request.user
        action = self.action

        if not user.is_authenticated:
            return OrderSerializer

        if action == 'create':
            return OrderCreateSerializer
        elif action in ['partial_update', 'update']:
            if user.role == 'delivery_man':
                return OrderStatusUpdateSerializer
        elif action in ['list', 'retrieve']:
            return OrderWithPaymentSerializer

        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def update(self, request, *args, **kwargs):
        order = self.get_object()
        user = request.user

        if not user.is_authenticated:
            return Response({
                "success": False,
                "message": "Unauthorized access.",
                "errorDetails": "Authentication credentials were not provided."
            }, status=status.HTTP_401_UNAUTHORIZED)

        if user.role == 'delivery_man':
            if order.delivery_man != user:
                return Response({
                    "success": False,
                    "message": "Unauthorized access.",
                    "errorDetails": "You are not assigned to this order."
                }, status=status.HTTP_403_FORBIDDEN)
            return super().update(request, *args, **kwargs)

        if user.role == 'admin':
            delivery_man_id = request.data.get("delivery_man_id")
            if delivery_man_id:
                try:
                    delivery_man = User.objects.get(id=delivery_man_id, role='delivery_man')
                    order.delivery_man = delivery_man
                    order.save()
                except User.DoesNotExist:
                    return Response({
                        "success": False,
                        "message": "Validation error occurred.",
                        "errorDetails": {
                            "field": "delivery_man_id",
                            "message": "Invalid delivery man ID."
                        }
                    }, status=status.HTTP_400_BAD_REQUEST)

            return super().update(request, *args, **kwargs)

        return Response({
            "success": False,
            "message": "Unauthorized access.",
            "errorDetails": "You must be an admin or assigned delivery man to perform this action."
        }, status=status.HTTP_403_FORBIDDEN)

