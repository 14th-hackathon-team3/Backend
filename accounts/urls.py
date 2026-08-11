from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
 
from .views import SignupView, LoginView, MeView, LogoutView, SocialLoginView
 
urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("social-login/", SocialLoginView.as_view(), name="social-login"),
]