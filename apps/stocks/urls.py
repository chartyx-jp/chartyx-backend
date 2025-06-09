from django.urls import path
from .views import TickerDataAPIView

urlpatterns = [
    path('ticker/', TickerDataAPIView.as_view()),
    # ほかのAPIもここに
]