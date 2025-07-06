from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .serializers import RegisterSerializer, ProfileSerializer

class Home(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        content = {'message': 'Hello, World!'}
        return Response(content)


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'success': True,
                'message': 'User registered successfully',
                'user': RegisterSerializer(user).data
            }, status=status.HTTP_201_CREATED)

        field, error = next(iter(serializer.errors.items()))
        return Response({
            'success': False,
            'message': 'Validation error occurred.',
            'errorDetails': {
                'field': field,
                'message': error[0] if isinstance(error, list) else str(error)
            }
        }, status=status.HTTP_400_BAD_REQUEST)

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        return token

class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response({
                "success": False,
                "statusCode": 401,
                "message": "Invalid credentials",
                "data": "null"
            }, status=status.HTTP_401_UNAUTHORIZED)

        return Response({
            "success": True,
            "statusCode": 200,
            "message": "Login successful",
            "data": {
                "access": serializer.validated_data.get("access"),
                "refresh": serializer.validated_data.get("refresh")
            }
        }, status=status.HTTP_200_OK)



class ProfileView(RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user