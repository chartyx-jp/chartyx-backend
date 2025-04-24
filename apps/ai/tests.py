from django.test import TestCase

# Create your tests here.

from utils.utils import Utils
Utils.setup_django()

from django.conf import settings
from apps.stocks.services.yahoo_fetcher import YahooFetcher
import pandas as pd

def extract_japan_tickers(jp_df: pd.DataFrame) -> list[str]:
    """
    日本株CSVのDataFrameからティッカーコードを抽出（.Tを付与）

    Parameters:
    - jp_df: 日本株銘柄情報のDataFrame（"コード", "市場・商品区分" を含む）

    Returns:
    - List[str]: ["1301.T", "1332.T", ...]
    """
    return [
        str(code).zfill(4) + ".T"
        for code in (jp_df["コード"])
    ]


def extract_us_tickers(us_df: pd.DataFrame) -> list[str]:
    """
    米国株CSVのDataFrameからティッカーコードを抽出

    Parameters:
    - us_df: 米国株銘柄情報のDataFrame（"Symbol" を含む）

    Returns:
    - List[str]: ["AAPL", "MSFT", "GOOGL", ...]
    """
    return [symbol for symbol in us_df["Symbol"] if pd.notna(symbol)]


if __name__ == "__main__":
    from datetime import date
    # ティッカー抽出
    jp_df = pd.read_csv(settings.LEARNING_DATA_DIR / "data_2025_03.csv")
    us_df = pd.read_csv(settings.LEARNING_DATA_DIR / "constituents.csv")

    jp_tickers = extract_japan_tickers(jp_df)
    us_tickers = extract_us_tickers(us_df)

    all_tickers = jp_tickers + us_tickers
    print(f"✅ 抽出完了: {len(all_tickers)} 銘柄")

    # 取得期間・間隔設定
    start = "1970-01-01"
    end = date.today().strftime("%Y-%m-%d")
    interval = "1d"

    # フェッチャー初期化 & 一括取得
    fetcher = YahooFetcher(start=start, end=end, interval=interval)
    fetcher.download_multiple_and_save(all_tickers)

    print("✅ 全ティッカーのデータ取得＆保存完了")
