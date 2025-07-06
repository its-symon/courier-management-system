import stripe
from django.conf import settings
from rest_framework import status, generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from .serializers import CardInformationSerializer, OrderPaymentSerializer, PaymentSerializer, TokenPaymentSerializer
from .models import Payment
from order.models import Order


class PaymentAPI(APIView):
    serializer_class = OrderPaymentSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.serializer_class(data=request.data)

        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': "Validation error occurred.",
                'errorDetails': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        data_dict = serializer.validated_data

        # Check if order exists and belongs to user
        try:
            order = Order.objects.get(id=data_dict['order_id'], user=request.user)
        except Order.DoesNotExist:
            return Response({
                'success': False,
                'message': "Order not found or you don't have permission to pay for this order.",
            }, status=status.HTTP_404_NOT_FOUND)

        # Check if payment already exists
        if hasattr(order, 'payment') and order.payment.status == 'succeeded':
            return Response({
                'success': False,
                'message': "Payment already completed for this order.",
            }, status=status.HTTP_400_BAD_REQUEST)

        stripe.api_key = settings.STRIPE_SECRET_KEY

        # Prepare payment data
        payment_data = {}
        if data_dict.get('payment_method_id'):
            payment_data['payment_method_id'] = data_dict['payment_method_id']
        else:
            payment_data.update(data_dict['card_info'])

        response = self.stripe_card_payment(
            data_dict=payment_data,
            amount=data_dict['amount'],
            order=order,
            user=request.user
        )

        return Response(response, status=response.get('status', 200))

    def stripe_card_payment(self, data_dict, amount, order, user):
        try:
            # Create or get existing payment record
            payment, created = Payment.objects.get_or_create(
                order=order,
                defaults={
                    'user': user,
                    'amount': amount,
                    'currency': 'usd',
                    'status': 'pending'
                }
            )


            if 'payment_method_id' in data_dict:
                payment_method_id = data_dict['payment_method_id']
            else:
                card_details = stripe.PaymentMethod.create(
                    type="card",
                    card={
                        "number": data_dict['card_number'],
                        "exp_month": data_dict['expiry_month'],
                        "exp_year": data_dict['expiry_year'],
                        "cvc": data_dict['cvc'],
                    },
                )
                payment_method_id = card_details.id

            payment_intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),
                currency='usd',
                payment_method=payment_method_id,
                confirm=True,
                automatic_payment_methods={
                    'enabled': True,
                    'allow_redirects': 'never'
                }
            )

            payment.stripe_payment_intent_id = payment_intent.id

            if payment_intent.status == 'succeeded':
                payment.status = 'succeeded'
                payment.save()

                order.payment_status = 'paid'
                order.payment_intent_id = payment_intent.id
                order.delivery_cost = amount
                order.save()

                response = {
                    'success': True,
                    'message': "Payment successful",
                    'status': 200,
                    'data': {
                        'payment_id': payment.id,
                        'order_id': order.id,
                        'amount': float(amount),
                        'payment_intent_id': payment_intent.id
                    }
                }
            else:
                payment.status = 'failed'
                payment.save()

                response = {
                    'success': False,
                    'message': "Payment failed",
                    'status': 400,
                    'data': {
                        'payment_intent_status': payment_intent.status
                    }
                }

        except stripe.error.CardError as e:
            # Update payment status to failed
            if 'payment' in locals():
                payment.status = 'failed'
                payment.save()

            response = {
                'success': False,
                'message': "Card error occurred",
                'error': str(e),
                'status': 400,
            }
        except Exception as e:
            if 'payment' in locals():
                payment.status = 'failed'
                payment.save()

            response = {
                'success': False,
                'message': "Payment processing failed",
                'error': str(e),
                'status': 400,
            }

        return response


class TokenPaymentAPI(APIView):
    serializer_class = TokenPaymentSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.serializer_class(data=request.data)

        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': "Validation error occurred.",
                'errorDetails': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        data_dict = serializer.validated_data

        try:
            order = Order.objects.get(id=data_dict['order_id'], user=request.user)
        except Order.DoesNotExist:
            return Response({
                'success': False,
                'message': "Order not found or you don't have permission to pay for this order.",
            }, status=status.HTTP_404_NOT_FOUND)

        # Check if payment already exists
        if hasattr(order, 'payment') and order.payment.status == 'succeeded':
            return Response({
                'success': False,
                'message': "Payment already completed for this order.",
            }, status=status.HTTP_400_BAD_REQUEST)

        stripe.api_key = settings.STRIPE_SECRET_KEY
        response = self.stripe_token_payment(
            payment_method_id=data_dict['payment_method_id'],
            amount=data_dict['amount'],
            order=order,
            user=request.user
        )

        return Response(response, status=response.get('status', 200))

    def stripe_token_payment(self, payment_method_id, amount, order, user):
        try:
            # Create or get existing payment record
            payment, created = Payment.objects.get_or_create(
                order=order,
                defaults={
                    'user': user,
                    'amount': amount,
                    'currency': 'usd',
                    'status': 'pending'
                }
            )

            payment_intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Stripe expects amount in cents
                currency='usd',
                payment_method=payment_method_id,
                confirm=True,
                automatic_payment_methods={
                    'enabled': True,
                    'allow_redirects': 'never'
                }
            )

            # Update payment record
            payment.stripe_payment_intent_id = payment_intent.id

            if payment_intent.status == 'succeeded':
                payment.status = 'succeeded'
                payment.save()

                order.payment_status = 'paid'
                order.payment_intent_id = payment_intent.id
                order.delivery_cost = amount
                order.save()

                response = {
                    'success': True,
                    'message': "Payment successful",
                    'status': 200,
                    'data': {
                        'payment_id': payment.id,
                        'order_id': order.id,
                        'amount': float(amount),
                        'payment_intent_id': payment_intent.id
                    }
                }

            else:
                payment.status = 'failed'
                payment.save()

                response = {
                    'success': False,
                    'message': "Payment failed",
                    'status': 400,
                    'data': {
                        'payment_intent_status': payment_intent.status
                    }
                }

        except stripe.error.CardError as e:
            if 'payment' in locals():
                payment.status = 'failed'
                payment.save()

            response = {
                'success': False,
                'message': "Card error occurred",
                'error': str(e),
                'status': 400,
            }
        except Exception as e:
            if 'payment' in locals():
                payment.status = 'failed'
                payment.save()

            response = {
                'success': False,
                'message': "Payment processing failed",
                'error': str(e),
                'status': 400,
            }

        return response

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.role == 'admin':
            payments = Payment.objects.all()
        else:
            payments = Payment.objects.filter(user=user)

        serializer = PaymentSerializer(payments, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })
class PaymentListPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class PaymentListView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PaymentListPagination

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'role') and user.role == 'admin':
            return Payment.objects.all().order_by('-created_at')
        return Payment.objects.filter(user=user).order_by('-created_at')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({
                'success': True,
                'data': serializer.data
            })

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })