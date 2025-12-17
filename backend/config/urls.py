from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.views import HealthView, LoginView, RegisterView, ProfileView, BrokerApplicationView

import transactions.urls

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", HealthView.as_view(), name="health"),
    path("api/auth/login/", LoginView.as_view(), name="login"),
    path("api/auth/register/", RegisterView.as_view(), name="register"),
    path("api/auth/profile/", ProfileView.as_view(), name="profile"),
    path("api/broker/application/", BrokerApplicationView.as_view(), name="broker-application"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/", include(transactions.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
