from apps.common.app_initializer import DjangoAppInitializer as initializer
initializer.setup_django()

from django.conf import settings
import pandas as pd
from datetime import date
from apps.stocks.services.parquet_handler import ParquetHandler
from apps.ai.features.base_v2 import BasicFeatureGeneratorV2
from apps.ai.features.base_v3 import BasicFeatureGeneratorV3
from apps.stocks.services.yahoo_fetcher import YahooFetcher
from apps.ai.evaluators.booster_evaluator import BoosterEvaluator
from apps.ai.ai_models.base_booster import BaseBoosterModel



TICKERS = {"5020.T":"ENEOS",
"7203.T":"トヨタ自動車",
"6758.T":"ソニーグループ",
"7974.T":"任天堂", 
"8306.T":"三菱UFJ銀行",
"9983.T":"ファーストリテイリング",
"6594.T":"日本電産"}

def get_ticker_list(tickers: dict) -> list:
    """
    引数で渡されたティッカーのリストを取得する関数
    """
    tickers = list(tickers.keys())
    return tickers


# 共通インスタンス（1回だけ生成）
today = date.today().strftime("%Y-%m-%d")
fetcher = YahooFetcher(start=today, end=today, interval="1d")
handler = ParquetHandler(directory=settings.ANALYTICS_DATA_DIR)
generator = BasicFeatureGeneratorV3()

def load_model():
    model = BaseBoosterModel("chartyx_v3")
    model.load_model()
    return model

def test_single_ticker_latest():
    print("=== Running: test_single_ticker_latest ===")
    # tickers = fetcher.get_tickers_list_random("data_2025_03.csv", "constituents.csv", 5)
    tickers = get_ticker_list(TICKERS)
    df = handler.get_latest_row_by_ticker(tickers[0], n=3)
    X, y = generator.split(df,remove_zero_target=False)
    evaluator = BoosterEvaluator(load_model())
    evaluator.evaluate(X, y)

def test_multi_ticker_latest():
    print("=== Running: test_multi_ticker_latest ===")
    # tickers = fetcher.get_tickers_list_random("data_2025_03.csv", "constituents.csv", 5)
    tickers = get_ticker_list(TICKERS)
    X_all, y_all = [], []
    for t in tickers:
        df = handler.get_latest_row_by_ticker(t, n=3)
        X, y = generator.split(df,remove_zero_target=False)
        if not X.empty and not y.empty:
            X_all.append(X)
            y_all.append(y)
    X = pd.concat(X_all)
    y = pd.concat(y_all)
    evaluator = BoosterEvaluator(load_model())
    evaluator.evaluate(X, y)

def test_single_ticker_multi_rows():
    print("=== Running: test_single_ticker_multi_rows ===")
    # tickers = fetcher.get_tickers_list_random("data_2025_03.csv", "constituents.csv", 5)
    tickers = get_ticker_list(TICKERS)
    df = handler.get_latest_row_by_ticker(tickers[0], n=100)
    X, y = generator.split(df,remove_zero_target=False)
    evaluator = BoosterEvaluator(load_model())
    evaluator.evaluate(X, y)

def main():
    # test_single_ticker_latest()
    # test_multi_ticker_latest()
    test_single_ticker_multi_rows()
    print("=== 全評価完了 ===")

if __name__ == "__main__":
    main()
