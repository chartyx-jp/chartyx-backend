# apps/users/urls.py (またはプロジェクト全体のurls.pyでincludeする場合)

from django.urls import path
from .views import (
    SignupAPIView,
    LoginAPIView,
    LogoutAPIView,
    OTPVerifyAPIView, # これはログイン時のOTP検証用として残す
    PlanSettingsAPIView,
    ProfileSettingsAPIView,
    DeleteAccountAPIView,
    CheckEmailAvailabilityAPIView,
    SendOtpForSignupAPIView,
    VerifyOtpForSignupAPIView,
    # ForgotPasswordAPIView, # 実装済みなら
)

urlpatterns = [
    # --- サインアップフローのAPI ---
    path('auth/check-email/', CheckEmailAvailabilityAPIView.as_view(), name='auth_check_email'),
    path('auth/send-otp-signup/', SendOtpForSignupAPIView.as_view(), name='auth_send_otp_signup'),
    path('auth/verify-otp-signup/', VerifyOtpForSignupAPIView.as_view(), name='auth_verify_otp_signup'),
    path('auth/signup/', SignupAPIView.as_view(), name='auth_signup'), # 最終的なサインアップ

    # --- ログインフローのAPI ---
    path('auth/login/', LoginAPIView.as_view(), name='auth_login'),
    path('auth/verify-otp-login/', OTPVerifyAPIView.as_view(), name='auth_verify_otp_login'), # ログイン時のOTP検証

    # --- ユーザー設定・管理API ---
    path('user/logout/', LogoutAPIView.as_view(), name='user_logout'),
    path('user/plan-settings/', PlanSettingsAPIView.as_view(), name='user_plan_settings'),
    path('user/profile-settings/', ProfileSettingsAPIView.as_view(), name='user_profile_settings'),
    path('user/delete-account/', DeleteAccountAPIView.as_view(), name='user_delete_account'),

    # path('auth/forgot-password/', ForgotPasswordAPIView.as_view(), name='auth_forgot_password'), # パスワード忘れAPI
]