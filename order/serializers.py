from rest_framework import serializers
from .models import Order
from accounts.models import User
from payment.serializers import PaymentSerializer

class OrderSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    delivery_man = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'user',
            'delivery_man',
            'pickup_address',
            'delivery_address',
            'package_details',
            'status',
            'delivery_cost',
            'payment_status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user', 'delivery_man', 'status', 'payment_status', 'created_at', 'updated_at']


class OrderWithPaymentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    delivery_man = serializers.StringRelatedField(read_only=True)
    payment = PaymentSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'user', 'delivery_man', 'pickup_address',
            'delivery_address', 'package_details', 'status',
            'created_at', 'updated_at', 'payment'
        ]
        read_only_fields = ['id', 'user', 'delivery_man', 'status', 'created_at', 'updated_at']

# User Create Orders
class OrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['pickup_address', 'delivery_address', 'package_details', 'delivery_cost']

# Admin Assign Delivery Man
class AdminAssignDeliverySerializer(serializers.ModelSerializer):
    delivery_man = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='delivery_man')
    )
    class Meta:
        model = Order
        fields = ['delivery_man']

    def validate_delivery_man(self, value):
        if value.role != 'delivery_man':
            raise serializers.ValidationError("Assigned user must be a delivery man")
        return value

# Delivery man change status
class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['status']

    def validate_status(self, value):
        if value not in ['pending', 'delivered', 'complete']:
            raise serializers.ValidationError("Invalid status")
        return value

    def update(self, instance, validated_data):
        instance.status = validated_data['status']
        instance.save()
        return instance

