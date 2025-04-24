import yfinance as yf
from datetime import date
from apps.stocks.services.parquet_handler import ParquetHandler
from utils.utils import Utils
import pandas as pd
from typing import Union, List, Dict
from django.conf import settings

class YahooFetcher(ParquetHandler):
    def __init__(self, start: str, end: str = date.today().strftime("%Y-%m-%d"), interval: str = "1d",read_directory: str = settings.PROCESSED_DATA_DIR, save_directory: str = settings.RAW_DATA_DIR ) -> None:
        """
        Yahoo Finance から株価データを取得するFetcherクラス。

        Parameters:
        - start: 開始日 (例: "2021-01-01")
        - end: 終了日 (例: "2024-12-31")
        - interval: 取得間隔 ("1d", "1wk", "1mo")
        - directory: 保存先ディレクトリ
        """
        super().__init__(read_directory=read_directory, save_directory=save_directory)
        Utils.validate_interval(interval)
        self.__start: str = start
        self.__end: str = end
        self.__interval: str = interval

    def fetch(self, tickers: Union[str, List[str]]) -> Dict[str, pd.DataFrame]:
        """
        指定されたティッカーの株価データを取得し、CSVとして保存する。

        Parameters:
        - tickers: ティッカー名（単一 or リスト）

        Returns:
        - dict: {ticker: DataFrame}
        """
        tickers = Utils.ensure_list(tickers)
        result: Dict[str, pd.DataFrame] = {}

        for ticker in tickers:
            self.log.info(f"Fetching: {ticker}")
            ticker_obj: yf.Ticker = yf.Ticker(ticker)

            df: pd.DataFrame = ticker_obj.history(
                start=self.__start, end=self.__end, interval=self.__interval
            )
            df.reset_index(inplace=True)

            info: dict = ticker_obj.info
            company_name: str = info.get("longName", "N/A")
            safe_name: str = Utils.safe_filename_component(company_name)
            filename: str = f"{ticker}_{safe_name}_{self.__interval}_{self.__start}_to_{self.__end}.parquet"

            self.save(df, filename)
            result[ticker] = df

        return result


    def download_multiple_and_save(self, tickers: List[str]) -> None:
        """
        複数銘柄を一括取得して、それぞれを個別のCSVに保存するメソッド。

        Parameters:
        - tickers: ティッカーのリスト
        """
        df: pd.DataFrame = yf.download(
            tickers,
            start=self.__start,
            end=self.__end,
            interval=self.__interval,
            group_by="ticker",
            auto_adjust=False
        )

        for ticker in tickers:
            #銘柄名取得
            ticker_obj: yf.Ticker = yf.Ticker(ticker)
            info: dict = ticker_obj.info
            company_name: str = info.get("longName", "N/A")
            safe_name: str = Utils.safe_filename_component(company_name)

            ticker_df: pd.DataFrame = df[ticker].copy()
            ticker_df.reset_index(inplace=True)
            filename: str = f"{ticker}_{safe_name}_{self.__interval}_{self.__start}_to_{self.__end}.parquet"
            self.save(ticker_df, filename)
            self.log.info(f"Saved: {filename}")


    def extract_japan_tickers(self, filename: str) -> list[str]:
        """
        日本株CSVのDataFrameからティッカーコードを抽出（.Tを付与）

        Parameters:
        - filename: 日本株銘柄情報のCSVファイル名

        Returns:
        - List[str]: ["1301.T", "1332.T", ...]
        """
        jp_df = pd.read_csv(settings.LEARNING_DATA_DIR / filename)

        return [
            str(code).zfill(4) + ".T"
            for code in (jp_df["コード"])
        ]


    def extract_us_tickers(self, filename: str) -> list[str]:
        """
        米国株CSVのDataFrameからティッカーコードを抽出

        Parameters:
        - ファイル名: US株銘柄情報のCSVファイル名

        Returns:
        - List[str]: ["AAPL", "MSFT", "GOOGL", ...]
        """

        us_df = pd.read_csv(settings.LEARNING_DATA_DIR / filename)
        return [symbol for symbol in us_df["Symbol"] if pd.notna(symbol)]

