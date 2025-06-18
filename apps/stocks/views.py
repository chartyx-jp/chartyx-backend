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
    
    

        
        
        
        
        
