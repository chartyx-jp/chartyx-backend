from django.urls import path
from apps.stocks.views import (
    TickerDataAPIView,
    TickerListAPIView,
    TickerSearchAPIView,)

urlpatterns = [
    path('ticker/', TickerDataAPIView.as_view()),
    path('tickers/', TickerListAPIView.as_view()),
    path('search/', TickerSearchAPIView.as_view()),
    # ほかのAPIもここに
]