from pathlib import Path
from apps.stocks.services.parquet_handler import ParquetHandler
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from apps.common.utils import Utils

handler = ParquetHandler(directory=Path(settings.RAW_DATA_DIR))

class TickerDataAPIView(APIView):
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

        
        
        
        
        
