from ast import Is
from pathlib import Path
from re import I
from rest_framework.permissions import IsAuthenticated, AllowAny
from apps.stocks.services.parquet_handler import ParquetHandler
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from apps.common.utils import Utils

handler = ParquetHandler(directory=Path(settings.RAW_DATA_DIR))

class TickerDataAPIView(APIView):
    """
    指定されたティッカーコードに基づいて、パーケットファイルから株価データを取得するAPIビュー。
    """
    permission_classes = [IsAuthenticated] 
    def get(self, request):
        ticker = request.query_params.get('code').strip().upper() if request.query_params.get('code') else None
        if not ticker:
            return Response({'error': 'ticker parameter required'}, status=400)
        
        parquet_file = handler.get_file_by_ticker(ticker_base=ticker)
        if not parquet_file:
            return Response({'error': 'ticker not found'}, status=404)

        df = handler.load(parquet_file)
        df['Date'] = Utils.unix_to_datestr(df['Date'])
        
        data = df.to_dict(orient='records')
        
        return Response(data, status=status.HTTP_200_OK)
    
class TickerListAPIView(APIView):
    permission_classes = [IsAuthenticated] 
    
    def get(self, request):
        tickers = handler.get_all_tickers()
        if not tickers:
            return Response({'error': 'No tickers found'}, status=404)
        
        return Response(tickers, status=status.HTTP_200_OK)
    
class TickerSearchAPIView(APIView):
    """
    ティッカーコードの部分一致検索を行うAPIビュー。
    """
    permission_classes = [IsAuthenticated] 
    
    def get(self, request):
        query = request.query_params.get('query', '').strip().upper()
        if not query:
            return Response({'error': 'query parameter required'}, status=400)
        
        tickers = handler.search_tickers_by_ticker(query)
        if not tickers:
            return Response({'error': 'No matching tickers found'}, status=404)
        
        return Response(tickers, status=status.HTTP_200_OK)

        
        
        
        
        
