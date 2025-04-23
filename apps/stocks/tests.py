from django.test import TestCase

# Create your tests here.

from utils.utils import Utils
Utils.setup_django()

from apps.stocks.services.yahoo_fetcher import YahooFetcher
import os
import pandas as pd
from django.conf import settings

# def test_yahoo_fetch_and_save() -> None:
#     tickers = ["AAPL","MSFT", "GOOGL"]
#     fetcher = YahooFetcher(start="2023-01-01", end="2023-12-31", interval="1d")
#     df_dict = fetcher.fetch(tickers)

#     print("✅ Fetch completed")
#     files = os.listdir(settings.RAW_DATA_DIR)
#     print("Files in RAW_DATA_DIR:", files)

#     matched = [f for f in files if f.startswith("AAPL_") and f.endswith(".csv")]
#     print("Matched:", matched)

#     assert matched, "ファイルが保存されていません"

#     print("✅ YahooFetcher fetch test passed!")

def test_bulk_yahoo_download_and_save() -> None:
    start = "2023-01-01"
    end = "2023-01-15"
    interval = "1d"
    directory = str(settings.RAW_DATA_DIR)

    fetcher = YahooFetcher(
    start = start,
    end = end,
    interval = interval,
    )

    tickers = ["AAPL", "MSFT"]

    # 関数を実行
    fetcher.download_multiple_and_save(tickers=tickers)

    # ファイルが保存されているか確認
    for ticker in tickers:
        filename = f"{ticker}_{interval}_{start}_to_{end}.csv"
        path = os.path.join(directory, filename)

        assert os.path.exists(path), f"{filename} が保存されていません"

        df = pd.read_csv(path)
        assert not df.empty, f"{filename} の中身が空です"
        assert "Open" in df.columns, f"{filename} に 'Open' カラムがありません"

    print("✅ 複数銘柄の一括保存テスト成功！")
if __name__ == "__main__":
    test_bulk_yahoo_download_and_save()
    print("All tests passed!")
    print("✅ All tests passed!")