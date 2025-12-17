import logging

from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import EmailTokenObtainPairSerializer, RegisterSerializer, UserSerializer, BrokerApplicationSerializer

logger = logging.getLogger("api")
User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        logger.info("Register attempt for %s", request.data.get("email"))
        response = super().create(request, *args, **kwargs)
        return response


class LoginView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        logger.info("Login attempt for %s", request.data.get("email"))
        return super().post(request, *args, **kwargs)


class HealthView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        return Response({"status": "ok"})


class ProfileView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class BrokerApplicationView(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get(self, request, *args, **kwargs):
        application = getattr(request.user, "broker_application", None)
        data = None
        if application:
            data = BrokerApplicationSerializer(application).data
        return Response({"application": data, "is_broker": request.user.is_broker})

    def post(self, request, *args, **kwargs):
        application = getattr(request.user, "broker_application", None)
        serializer = BrokerApplicationSerializer(
            instance=application,
            data=request.data,
            partial=application is not None,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        was_existing = application is not None
        application = serializer.save()

        output = BrokerApplicationSerializer(application).data
        response_status = status.HTTP_200_OK if was_existing else status.HTTP_201_CREATED
        return Response({"application": output, "is_broker": application.user.is_broker}, status=response_status)
