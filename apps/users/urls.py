from django.urls import path
from .views import (
    SignupAPIView,
    LoginAPIView,
    LogoutAPIView,
    OTPVerifyAPIView,
    PlanSettingsAPIView,
    ProfileSettingsAPIView,
    DeleteAccountAPIView,
    # ForgotPasswordAPIView,  # 実装済みなら
)

urlpatterns = [
    path('signup/', SignupAPIView.as_view(), name='signup'),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('logout/', LogoutAPIView.as_view(), name='logout'),
    path('verify-otp/', OTPVerifyAPIView.as_view(), name='verify_otp'),
    path('plan-settings/', PlanSettingsAPIView.as_view(), name='plan_settings'),
    path('profile-settings/', ProfileSettingsAPIView.as_view(), name='profile_settings'),
    path('delete-account/', DeleteAccountAPIView.as_view(), name='delete_account'),
    # path('forgot-password/', ForgotPasswordAPIView.as_view(), name='forgot_password'),  # 実装済みなら
]
