import json

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from django.contrib.auth import get_user_model

from .models import BrokerApplication

User = get_user_model()



class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ("id", "email", "password", "first_name", "last_name")
        read_only_fields = ("id",)

    def validate_email(self, value: str) -> str:
        # normalize + prevent duplicates (case-insensitive)
        return value.strip().lower()

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "email"

    def validate(self, attrs):
        raw_email = attrs.get("email")
        raw_password = attrs.get("password")

        email = (raw_email or "").strip().lower()
        password = raw_password or ""

        if not email:
            raise serializers.ValidationError({"email": "Email is required."})
        if not password:
            raise serializers.ValidationError({"password": "Password is required."})

        serializers.EmailField().run_validation(email)

        user = authenticate(
            request=self.context.get("request"),
            email=email,
            password=password
        )

        if user is None:
            raise serializers.ValidationError({"detail": "Invalid email or password"})

        credentials: dict[str, str] = {"email": email, "password": password}
        data = super().validate(credentials)
        data["user"] = {
            "id": self.user.id,
            "email": self.user.email,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
        }
        return data


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "is_broker")


class BrokerApplicationSerializer(serializers.ModelSerializer):
    date_of_birth = serializers.DateField(required=False)
    curp = serializers.CharField(required=False, allow_blank=True)
    rfc = serializers.CharField(required=False, allow_blank=True)
    nationality = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    mobile_phone = serializers.CharField(required=False, allow_blank=True)
    occupation = serializers.CharField(required=False, allow_blank=True)
    additional_details = serializers.DictField(
        child=serializers.CharField(allow_blank=True), required=False, allow_empty=True, write_only=True
    )
    is_broker = serializers.SerializerMethodField(read_only=True)
    details = serializers.DictField(read_only=True)

    class Meta:
        model = BrokerApplication
        fields = (
            "id",
            "status",
            "id_document_primary",
            "id_document_secondary",
            "selfie_with_id",
            "date_of_birth",
            "curp",
            "rfc",
            "nationality",
            "address",
            "mobile_phone",
            "occupation",
            "additional_details",
            "details",
            "submitted_at",
            "updated_at",
            "is_broker",
        )
        read_only_fields = ("status", "details", "submitted_at", "updated_at", "is_broker")
        extra_kwargs = {
            "id_document_primary": {"required": False},
            "id_document_secondary": {"required": False},
            "selfie_with_id": {"required": False},
        }

    def get_is_broker(self, obj):
        return obj.user.is_broker

    @property
    def _detail_keys(self):
        return ["date_of_birth", "curp", "rfc", "nationality", "address", "mobile_phone", "occupation"]

    def _merge_details(self, instance, validated_data):
        details = dict(getattr(instance, "details", {}) or {})
        additional_details = validated_data.pop("additional_details", {}) or {}

        for key in self._detail_keys:
            if key in validated_data:
                value = validated_data.pop(key)
                if value is not None:
                    details[key] = value.isoformat() if hasattr(value, "isoformat") else value

        for key, value in additional_details.items():
            details[key] = value

        return details

    def validate(self, attrs):
        if isinstance(attrs.get("additional_details"), str):
            try:
                attrs["additional_details"] = json.loads(attrs["additional_details"])
            except (TypeError, ValueError):
                raise serializers.ValidationError({"additional_details": "Must be valid JSON when provided as text."})

        required_files = ["id_document_primary", "id_document_secondary", "selfie_with_id"]
        if self.instance is None:
            missing = [field for field in required_files if not attrs.get(field)]
            if missing:
                raise serializers.ValidationError({field: "This file is required to start the broker application." for field in missing})
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        details = self._merge_details(None, validated_data)

        application = BrokerApplication.objects.create(user=user, details=details, **validated_data)
        user.is_broker = True
        user.save(update_fields=["is_broker"])
        return application

    def update(self, instance, validated_data):
        details = self._merge_details(instance, validated_data)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.details = details
        instance.save()

        instance.user.is_broker = True
        instance.user.save(update_fields=["is_broker"])

        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        for key in self._detail_keys:
            representation[key] = instance.details.get(key)
        return representation
