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


class SMAAPIView(APIView):
    """単純移動平均（SMA）API"""
    def get(self, request):
        ticker = request.query_params.get('code')
        if not ticker:
            return Response({'error': 'code parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        ticker = ticker.strip().upper()
        
        # パラメータ取得
        try:
            period = int(request.query_params.get('period', 20))
            if period <= 0:
                return Response({'error': 'period must be positive'}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response({'error': 'period must be a valid integer'}, status=status.HTTP_400_BAD_REQUEST)
        
        # SMA計算
        result = handler.calculate_sma(ticker, period)
        
        # エラーチェック
        if 'error' in result:
            return Response(result, status=status.HTTP_404_NOT_FOUND if 'not found' in result['error'] else status.HTTP_400_BAD_REQUEST)
        
        return Response(result, status=status.HTTP_200_OK)


class EMAAPIView(APIView):
    """指数移動平均（EMA）API"""
    def get(self, request):
        ticker = request.query_params.get('code')
        if not ticker:
            return Response({'error': 'code parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        ticker = ticker.strip().upper()
        
        # パラメータ取得
        try:
            period = int(request.query_params.get('period', 12))
            if period <= 0:
                return Response({'error': 'period must be positive'}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response({'error': 'period must be a valid integer'}, status=status.HTTP_400_BAD_REQUEST)
        
        # EMA計算
        result = handler.calculate_ema(ticker, period)
        
        # エラーチェック
        if 'error' in result:
            return Response(result, status=status.HTTP_404_NOT_FOUND if 'not found' in result['error'] else status.HTTP_400_BAD_REQUEST)
        
        return Response(result, status=status.HTTP_200_OK)


class RSIAPIView(APIView):
    """RSI API"""
    def get(self, request):
        ticker = request.query_params.get('code')
        if not ticker:
            return Response({'error': 'code parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        ticker = ticker.strip().upper()
        
        # パラメータ取得
        try:
            period = int(request.query_params.get('period', 14))
            if period <= 0:
                return Response({'error': 'period must be positive'}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response({'error': 'period must be a valid integer'}, status=status.HTTP_400_BAD_REQUEST)
        
        # RSI計算
        result = handler.calculate_rsi(ticker, period)
        
        # エラーチェック
        if 'error' in result:
            return Response(result, status=status.HTTP_404_NOT_FOUND if 'not found' in result['error'] else status.HTTP_400_BAD_REQUEST)
        
        return Response(result, status=status.HTTP_200_OK)


class MACDAPIView(APIView):
    """MACD API"""
    def get(self, request):
        ticker = request.query_params.get('code')
        if not ticker:
            return Response({'error': 'code parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        ticker = ticker.strip().upper()
        
        # パラメータ取得
        try:
            fast = int(request.query_params.get('fast', 12))
            slow = int(request.query_params.get('slow', 26))
            signal = int(request.query_params.get('signal', 9))
            
            if fast <= 0 or slow <= 0 or signal <= 0:
                return Response({'error': 'all periods must be positive'}, status=status.HTTP_400_BAD_REQUEST)
            
            if fast >= slow:
                return Response({'error': 'fast period must be less than slow period'}, status=status.HTTP_400_BAD_REQUEST)
                
        except ValueError:
            return Response({'error': 'periods must be valid integers'}, status=status.HTTP_400_BAD_REQUEST)
        
        # MACD計算
        result = handler.calculate_macd(ticker, fast, slow, signal)
        
        # エラーチェック
        if 'error' in result:
            return Response(result, status=status.HTTP_404_NOT_FOUND if 'not found' in result['error'] else status.HTTP_400_BAD_REQUEST)
        
        return Response(result, status=status.HTTP_200_OK)


class BollingerBandsAPIView(APIView):
    """ボリンジャーバンド API"""
    def get(self, request):
        ticker = request.query_params.get('code')
        if not ticker:
            return Response({'error': 'code parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        ticker = ticker.strip().upper()
        
        # パラメータ取得
        try:
            period = int(request.query_params.get('period', 20))
            std_dev = float(request.query_params.get('std_dev', 2.0))
            
            if period <= 0:
                return Response({'error': 'period must be positive'}, status=status.HTTP_400_BAD_REQUEST)
            
            if std_dev <= 0:
                return Response({'error': 'std_dev must be positive'}, status=status.HTTP_400_BAD_REQUEST)
                
        except ValueError:
            return Response({'error': 'period must be integer and std_dev must be number'}, status=status.HTTP_400_BAD_REQUEST)
        
        # ボリンジャーバンド計算
        result = handler.calculate_bollinger_bands(ticker, period, std_dev)
        
        # エラーチェック
        if 'error' in result:
            return Response(result, status=status.HTTP_404_NOT_FOUND if 'not found' in result['error'] else status.HTTP_400_BAD_REQUEST)
        
        return Response(result, status=status.HTTP_200_OK)
