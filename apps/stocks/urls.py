from django.urls import path
from apps.stocks.views import (
    TickerDataAPIView,
    SMAAPIView,
    EMAAPIView,
    RSIAPIView,
    MACDAPIView,
    BollingerBandsAPIView,
    TickerListAPIView,
    TickerSearchAPIView,)

urlpatterns = [
    path('ticker/', TickerDataAPIView.as_view()),
    path('tickers/', TickerListAPIView.as_view()),
    path('search/', TickerSearchAPIView.as_view()),
    # テクニカル指標API
    path('technical/sma/', SMAAPIView.as_view()),
    path('technical/ema/', EMAAPIView.as_view()),
    path('technical/rsi/', RSIAPIView.as_view()),
    path('technical/macd/', MACDAPIView.as_view()),
    path('technical/bollinger/', BollingerBandsAPIView.as_view()),
]
