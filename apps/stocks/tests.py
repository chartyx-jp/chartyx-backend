from django.test import TestCase

# Create your tests here.

from apps.common.app_initializer import DjangoAppInitializer as initializer
initializer.setup_django()

from apps.stocks.services.parquet_handler import ParquetHandler
from apps.ai.features.base_v3 import BasicFeatureGeneratorV3
from apps.ai.inference.predictor import StockAIPredictor
from apps.stocks.services.yahoo_fetcher import YahooFetcher
from datetime import date, timedelta
import random
import os
import pandas as pd
import numpy as np
from django.conf import settings
import yfinance as yf
# import pandas as pd

def test_yahoo_fetcher():
    from datetime import date

    
    # 取得期間・間隔設定
    start = "1970-01-01"
    end = date.today().strftime("%Y-%m-%d")
    interval = "1d"

    # フェッチャー初期化 & 一括取得
    fetcher = YahooFetcher(start=start, end=end, interval=interval)


    fetcher.download()
    print("✅ 全ティッカーのデータ取得＆保存完了")

def test_parquet_update():
    from datetime import date

    # 取得期間・間隔設定
    start = (date.today() - timedelta(days=20)).strftime("%Y-%m-%d")
    end = date.today().strftime("%Y-%m-%d")
    interval = "1d"

    # フェッチャー初期化 & 一括取得
    fetcher = YahooFetcher(start=start, end=end, interval=interval)


    fetcher.update_parquet_files()
    print("✅ 全ティッカーのデータ取得＆保存完了")

def test_get_ticker():
    from datetime import date

    # 取得期間・間隔設定
    start = (date.today() - timedelta(days=20)).strftime("%Y-%m-%d")
    end = date.today().strftime("%Y-%m-%d")
    interval = "1d"

    # フェッチャー初期化 & 一括取得
    fetcher = YahooFetcher(start=start, end=end, interval=interval)
    import time

    # tickers = "5020.T"
    tickers = ["7203.T", "6758.T", "8306.T", "7974.T", "7751.T"]

    results = []
    # data = fetcher.fetch(tickers=tickers)
    # print(data)
    session = fetcher.make_fake_user_agent()
    for ticker in tickers:
        try:
            data = fetcher.fetch([ticker], session=session)
            print(f"✅ {ticker} OK")
            results.append(data)
            time.sleep(0.5)  # 少なくとも2秒〜5秒あける
        except Exception as e:
            print(f"❌ {ticker} 失敗: {e}")
    print(results)




def retransform_all_files():
    """
    既存のparquetファイルをすべて読み込み、
    transformを通して再加工し、上書き保存する
    """
    try:
        from apps.ai.features.base_v3 import BasicFeatureGeneratorV3
        # ディレクトリ設定
        parquet_handler = ParquetHandler()
        generator = BasicFeatureGeneratorV3()
        parquet_handler.retransform_all_files(generator=generator)
        print(" すべてのファイルを再変換しました")
    except Exception as e:
        print(f" 変換失敗: {e}")

def transform_data_to_raw():
    """
    既存のparquetファイルをすべて読み込み、
    transformを通して再加工し、上書き保存する
    """
    try:
        yf = YahooFetcher(start="1970-01-01", end=date.today().strftime("%Y-%m-%d"), interval="1d")
        # ディレクトリ設定
        countries = list(yf.COUNTRY_META.keys())
        for country in countries:
            print(f" {country} のデータを変換中")
            parquet_handler = ParquetHandler(directory=settings.RAW_DATA_DIR/yf.COUNTRY_META[country]["folder"])
            parquet_handler.retransform_all_files(column=["Date", "Open", "High", "Low", "Close", "Volume"])
        print(" すべてのファイルを再変換しました")
    except Exception as e:
        print(f" 変換失敗: {e}")

def test_view_parquet_files():
    """
    指定ディレクトリ内のparquetファイル読み込み。
    """
    try:
        parquet_handler = ParquetHandler()
        df = parquet_handler.get_latest_row_by_ticker("5020.T", n=100)
        print(" データフレームのプレビュー:")
        print(df.iloc[-2:])      
        # print(df.columns.to_list())  # 最後の5行を表示
    except Exception as e:
        print(f" 読み込み失敗: {e}")
        





def test_rate_0():
    from apps.stocks.services.parquet_handler import ParquetHandler
    handler = ParquetHandler()
    ratio = handler.calc_flat_target_ratio()
    print(f"変動がほぼない行の割合: {ratio:.2%}")


        
if __name__ == "__main__":
    # test_yahoo_fetcher()
    # test_get_ticker()
    # test_parquet_update()
    # test_view_parquet_files()
    # test_rate_0()
    # retransform_all_files()
    transform_data_to_raw()
    # test_get_file_by_ticker(n=1)
