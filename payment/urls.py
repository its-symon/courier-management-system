from django.urls import path
from .views import PaymentAPI, TokenPaymentAPI, PaymentListView

urlpatterns = [
    path('make-payment/', PaymentAPI.as_view(), name='make_payment'),
    path('make-payment-token/', TokenPaymentAPI.as_view(), name='make_payment_token'),
    path('payments/', PaymentListView.as_view(), name='payment_list'),
]