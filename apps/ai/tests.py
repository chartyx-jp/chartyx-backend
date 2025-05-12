import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chartyx_backend.settings")
django.setup()

from datetime import date, timedelta
import random
import pandas as pd
import yfinance as yf
from apps.common.app_initializer import DjangoAppInitializer as initializer
from apps.stocks.services.yahoo_fetcher import YahooFetcher
from apps.stocks.services.parquet_handler import ParquetHandler
from apps.ai.inference.booster_predictor import StockAIBoosterPredictor
from apps.ai.models import PredictionLog


def test_predict_accuracy_on_latest_data(
    model_name: str,
    jp_ticker_csv: str,
    us_ticker_csv: str,
    sample_size: int = 5
):
    """
    ランダムな銘柄に対して、最新Parquetデータで予測を行い、
    当日の実株価と比較してDBに1件ずつ保存するテスト関数。
    """
    today = date.today()
    start_date = today.strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    # ① 銘柄取得
    fetcher = YahooFetcher(start=start_date, end=end_date, interval="1d")
    selected_tickers = fetcher.get_tickers_list_random(jp_ticker_csv, us_ticker_csv, sample_size)

    # ② 株価取得（当日の実株価）
    raw_data = fetcher.fetch(selected_tickers)

    # ③ 初期化
    predictor = StockAIBoosterPredictor(model_name)
    parquet_handler = ParquetHandler()
    saved_count = 0

    # ④ 推論ループ
    for ticker in selected_tickers:
        try:
            df_latest = parquet_handler.get_latest_row_by_ticker(ticker)

            pred = predictor.predict_from_df(df_latest)

            try:
                actual = raw_data[ticker]["Close"].iloc[-1]
            except Exception as e:
                print(f"⚠️ 株価取得失敗: {ticker} - {e}")
                continue

            diff = abs(pred - actual)
            sector = df_latest["Sector"].values[0] if "Sector" in df_latest.columns else None

            log = PredictionLog(
                date=today,
                ticker=ticker,
                predicted_price=pred,
                actual_price=actual,
                error=diff,
                sector=sector,
                model_version=model_name
            )

            try:
                log.save()
                saved_count += 1
                print(f"✅ {ticker}: Pred={pred:.2f} | Actual={actual:.2f} | Error={diff:.2f}")
            except Exception as e:
                print(f"❌ DB保存失敗: {ticker} - {e}")
                continue

        except Exception as e:
            print(f"❌ 予測失敗: {ticker} - {e}")
            continue

    print(f"\n📝 {saved_count} 件を PredictionLog に保存しました（{sample_size} 件中）")




def test_last_raw():

    today = date.today()
    start_date = today.strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    fetcher = YahooFetcher(start=start_date, end=end_date, interval="1d")
    predictor = StockAIBoosterPredictor("chartyx_v2.json")
    parquet = ParquetHandler()
    jp_tickers = fetcher.extract_japan_tickers("data_2025_03.csv")
    us_tickers = fetcher.extract_us_tickers("constituents.csv")
    all_tickers = {**jp_tickers, **us_tickers}
    selected_tickers = random.sample(list(all_tickers.keys()), k=1)

    for ticker in selected_tickers:
        df = parquet.get_latest_row_by_ticker(ticker)
        if isinstance(df, pd.Series):
            print(f"df {df} ここではまだあるよね")
            df = pd.DataFrame([df])
        X = predictor.split_features_for_prediction(df)
        print("X",X)
    
# === 実行 ===
if __name__ == "__main__":
    test_predict_accuracy_on_latest_data(
        model_name="chartyx_v2.json",
        jp_ticker_csv="data_2025_03.csv",
        us_ticker_csv="constituents.csv",
        sample_size=1  # ← 少数でまずテスト
    )
    # test_last_raw()
