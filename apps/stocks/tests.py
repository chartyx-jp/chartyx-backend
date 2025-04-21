from django.test import TestCase

# Create your tests here.

from apps.common.app_initializer import DjangoAppInitializer as initializer
initializer.setup_django()
from apps.stocks.services.parquet_handler import ParquetHandler
from apps.ai.features.base_v1 import BasicFeatureGeneratorV1
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


    jp_tickers = fetcher.extract_japan_tickers("data_2025_03.csv")
    us_tickers = fetcher.extract_us_tickers("constituents.csv")

    all_tickers =  {**jp_tickers, **us_tickers}
    print(f"✅ 抽出完了: {len(all_tickers)} 銘柄")

    
    fetcher.download_and_transform(all_tickers)
    print("✅ 全ティッカーのデータ取得＆保存完了")

def test_parquet_update():
    from datetime import date

    # 取得期間・間隔設定
    start = "1970-01-01"
    end = date.today().strftime("%Y-%m-%d")
    interval = "1d"

    # フェッチャー初期化 & 一括取得
    fetcher = YahooFetcher(start=start, end=end, interval=interval)


    jp_tickers = fetcher.extract_japan_tickers("data_2025_03.csv")
    us_tickers = fetcher.extract_us_tickers("constituents.csv")

    all_tickers =  {**jp_tickers, **us_tickers}
    print(f"✅ 抽出完了: {len(all_tickers)} 銘柄")

    
    fetcher.update_parquet_files(all_tickers)
    print("✅ 全ティッカーのデータ取得＆保存完了")







def test_yahoo_ticker_info(ticker: str = "AAPL") -> None:
    """
    Yahoo Financeから特定のティッカーの情報を取得し、表示するテスト関数。
    """
    # Yahoo Financeからデータを取得
    ticker = yf.Ticker(ticker)
    today_raw = ticker.history(period="1d", interval="1d")
    today_raw.reset_index(inplace=True)
    ticker_info = ticker.info
    symbol = ticker_info.get("symbol", "N/A")
    company_name = ticker_info.get("longName", "N/A")
    industry = ticker_info.get("industry", "N/A")
    sector = ticker_info.get("sector", "N/A")
    per = ticker_info.get("trailingPE", np.nan)
    market_cap = ticker_info.get("marketCap", np.nan)
    dividend_yield = ticker_info.get("dividendYield", np.nan)
    beta = ticker_info.get("beta", np.nan)
    forward_pe = ticker_info.get("forwardPE", np.nan)
    short_ratio = ticker_info.get("shortRatio", np.nan)
    recommendation = ticker_info.get("recommendationKey", "N/A")
    earnings_growth = ticker_info.get("earningsGrowth", np.nan)
    target_mean_price = ticker_info.get("targetMeanPrice", np.nan)
    shares_outstanding = ticker_info.get("sharesOutstanding", np.nan)
    revenue_growth = ticker_info.get("revenueGrowth", np.nan)
    print("Ticker Info:")
    print(f"ティッカー: {symbol}")
    print(f"企業名: {company_name}")
    print(f"セクター: {sector}")
    print(f"業種: {industry}")
    print(f"PER: {per}")
    print(f"時価総額: {market_cap}")
    print(f"配当利回り: {dividend_yield}")
    print(f"ベータ値: {beta}")
    print(f"フォワードPER: {forward_pe}")
    print(f"ショート比率: {short_ratio}")
    print(f"レコメンデーション: {recommendation}")
    print(f"予想EPS成長率: {earnings_growth}")
    print(f"目標株価: {target_mean_price}")
    print(f"発行済株式数: {shares_outstanding}")
    print(f"売上成長率: {revenue_growth}")


def retransform_all_files():
    """
    既存のparquetファイルをすべて読み込み、
    transformを通して再加工し、上書き保存する
    """
    try:
        from apps.ai.features.base_v2 import BasicFeatureGeneratorV2
        # ディレクトリ設定
        parquet_handler = ParquetHandler()
        generator = BasicFeatureGeneratorV2()
        
        parquet_handler.retransform_all_files(generator=generator)
        print(" すべてのファイルを再変換しました")
    except Exception as e:
        print(f" 変換失敗: {e}")

def test_view_parquet_files():
    """
    指定ディレクトリ内のparquetファイル読み込み。
    """
    try:
        parquet_handler = ParquetHandler()
        df = parquet_handler.view_parquet_preview("9900_SAGAMI-HOLDINGS-CORPORATION_小売業_小売.parquet")
        print(" データフレームのプレビュー:")
        print(df.iloc[-1] )  # 最後の5行を表示
    except Exception as e:
        print(f" 読み込み失敗: {e}")
        

def test_overwrite_all_parquet():
    import os
    import pandas as pd
    from apps.ai.features.base_v2 import BasicFeatureGeneratorV2

    DATA_DIR = "C:/HAL/SK/chartyx-backend/stock_data/processed_data"
    generator = BasicFeatureGeneratorV2()

    FIXED_COLUMNS = [
        "TwoHundredDayAverage", "FiftyDayAverage", "FiftyTwoWeekLow",
        "FiftyTwoWeekHigh", "AverageVolume10D", "AverageVolume3M"
    ]

    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".parquet"):
            path = os.path.join(DATA_DIR, filename)
            try:
                df = pd.read_parquet(path)
                df.drop(columns=[col for col in FIXED_COLUMNS if col in df.columns], inplace=True)
                df_transformed = generator.transform(df)
                df_transformed.to_parquet(path, index=False)
                print(f" 上書き完了: {filename}")
            except Exception as e:
                print(f" 変換失敗: {filename} - {e}")
    print(" すべてのファイルを上書きしました")


def test_get_file_by_ticker():
    """
    get_file_by_ticker の動作確認用テスト。
    """
    from apps.stocks.services.parquet_handler import ParquetHandler
    from apps.common.utils import Utils

    today = date.today()
    start_date = today.strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    fetcher = YahooFetcher(start=start_date, end=end_date, interval="1d")
    jp_tickers = fetcher.extract_japan_tickers("data_2025_03.csv")
    us_tickers = fetcher.extract_us_tickers("constituents.csv")
    all_tickers = {**jp_tickers, **us_tickers}
    selected_tickers = random.sample(list(all_tickers.keys()), k=5)

    handler = ParquetHandler()

    for ticker in selected_tickers:
        df = handler.get_latest_row_by_ticker(ticker)
        print(f"Ticker: {ticker} | Data: {df["Date"]}")
        
if __name__ == "__main__":
    test_get_file_by_ticker()