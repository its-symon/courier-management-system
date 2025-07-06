import datetime
from rest_framework import serializers
from .models import Payment


def check_expiry_month(value):
    if not 1 <= int(value) <= 12:
        raise serializers.ValidationError("Invalid expiry month.")


def check_expiry_year(value):
    today = datetime.datetime.now()
    if not int(value) >= today.year:
        raise serializers.ValidationError("Invalid expiry year.")


def check_cvc(value):
    if not 3 <= len(value) <= 4:
        raise serializers.ValidationError("Invalid cvc number.")


class CardInformationSerializer(serializers.Serializer):
    card_number = serializers.CharField(max_length=150, required=True)
    expiry_month = serializers.CharField(
        max_length=150,
        required=True,
        validators=[check_expiry_month],
    )
    expiry_year = serializers.CharField(
        max_length=150,
        required=True,
        validators=[check_expiry_year],
    )
    cvc = serializers.CharField(
        max_length=150,
        required=True,
        validators=[check_cvc],
    )


# Alternative: Use Stripe test tokens (recommended for testing)
class TokenPaymentSerializer(serializers.Serializer):
    order_id = serializers.IntegerField(required=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    payment_method_id = serializers.CharField(max_length=255, required=True)
    # payment_method_id should be a Stripe test token like "pm_card_visa"


class OrderPaymentSerializer(serializers.Serializer):
    order_id = serializers.IntegerField(required=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    card_info = CardInformationSerializer(required=False)
    payment_method_id = serializers.CharField(max_length=255, required=False)

    def validate(self, data):
        if not data.get('card_info') and not data.get('payment_method_id'):
            raise serializers.ValidationError("Either card_info or payment_method_id is required")
        return data


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'user', 'amount', 'currency',
            'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'stripe_payment_intent_id', 'created_at', 'updated_at']