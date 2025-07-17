from django.urls import path
from .views import (
    TickerDataAPIView,
    SMAAPIView,
    EMAAPIView,
    RSIAPIView,
    MACDAPIView,
    BollingerBandsAPIView
)

urlpatterns = [
    path('ticker/', TickerDataAPIView.as_view()),
    # テクニカル指標API
    path('technical/sma/', SMAAPIView.as_view()),
    path('technical/ema/', EMAAPIView.as_view()),
    path('technical/rsi/', RSIAPIView.as_view()),
    path('technical/macd/', MACDAPIView.as_view()),
    path('technical/bollinger/', BollingerBandsAPIView.as_view()),
]
