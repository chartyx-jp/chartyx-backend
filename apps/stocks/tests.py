from django.test import TestCase

# Create your tests here.

from utils.utils import Utils
Utils.setup_django()

from apps.ai.features.base_v1 import BasicFeatureGeneratorV1
from apps.ai.inference.predictor import StockAIPredictor
from apps.stocks.services.yahoo_fetcher import YahooFetcher
import os
import pandas as pd
from django.conf import settings

import yfinance as yf
import pandas as pd


from apps.ai.inference.predictor import StockAIPredictor
import yfinance as yf

stock_predictor = StockAIPredictor()

# 今日のローソク足取得
ticker = yf.Ticker("7203.T")
today_raw = ticker.history(period="1d", interval="1d")
today_raw.reset_index(inplace=True)

# 今日の終値（Series → float）
actual_close = today_raw.iloc[-1]["Close"]

# ハードコーディングされた特徴量（改善余地あり）
input_features = {
    "Open": 2561.0,
    "High": 2590.0,
    "Low": 2535.0,
    "Close": 2582.0,
    "Adj Close": 2582.0,
    "Volume": 34123500,
    "Return": 0.050020,
    "LogReturn": 0.048810,
    "MA_5": 2510.8,
    "MA_20": 2514.650000,
    "Volatility_5": 51.551673,
    "High_Low_Spread": 55.0,
    "OC_Change": 21.0,
    "Year": 2025,
    "Month": 4,
    "DayOfWeek": 2
}

predicted = stock_predictor.predict(input_features)

# 結果出力
print(f"✅ 今日の実終値: {actual_close:.2f}")
print(f"🔮 AI予測終値: {predicted:.2f}")
print(f"📊 差分: {abs(predicted - actual_close):.2f}")


# def test_bulk_yahoo_download_and_save() -> None:
#     start = "2023-01-01"
#     end = "2023-01-15"
#     interval = "1d"
#     directory = str(settings.RAW_DATA_DIR)

#     fetcher = YahooFetcher(
#     start = start,
#     end = end,
#     interval = interval,
#     )

#     tickers = ["AAPL", "MSFT"]

#     # 関数を実行
#     fetcher.download_multiple_and_save(tickers=tickers)

#     # ファイルが保存されているか確認
#     for ticker in tickers:
#         filename = f"{ticker}_{interval}_{start}_to_{end}.csv"
#         path = os.path.join(directory, filename)

#         assert os.path.exists(path), f"{filename} が保存されていません"

#         df = pd.read_csv(path)
#         assert not df.empty, f"{filename} の中身が空です"
#         assert "Open" in df.columns, f"{filename} に 'Open' カラムがありません"

#     print("✅ 複数銘柄の一括保存テスト成功！")
# if __name__ == "__main__":
#     test_bulk_yahoo_download_and_save()
#     print("All tests passed!")
#     print("✅ All tests passed!")

