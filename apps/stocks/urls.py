from django.urls import path
from apps.stocks.views import (
    TickerDataAPIView,
    TickerListAPIView)

urlpatterns = [
    path('ticker/', TickerDataAPIView.as_view()),
    path('tickers/', TickerListAPIView.as_view()),
    # ほかのAPIもここに
]