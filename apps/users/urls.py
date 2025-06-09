from django.urls import path, include
from . import views

#会員登録、ログイン、ログアウト、OPT入力、プラン変更、ユーザー情報変更、アカウント削除、パスワード忘れ
urlpatterns = [
    path('signup', views.signup, name='signup'),
    path('login', views.login, name='login'),
    path('logout', views.logout, name='logout'),
    path('sendAuthCodeEmail', views.sendAuthCodeEmail, name='sendAuthCodeEmail'),
    # path('verify-otp', views.verifyOTP, name='verifyOTP'),
    path('planSettings', views.planSettings, name='planSettings'),
    path('profileSettings', views.profileSettings, name='profileSettings'),
    path('deleteAccount', views.deleteAccount, name='deleteAccount'),
    # path('forgotPassword', views.forgotPassword, name='forgotPassword'),
]


