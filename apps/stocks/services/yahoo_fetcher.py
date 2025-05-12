import yfinance as yf
import glob
import pandas as pd
import numpy as np
import os
import random
from tqdm import tqdm
from datetime import date,timedelta
from apps.common.app_initializer import DjangoAppInitializer
from apps.stocks.services.parquet_handler import ParquetHandler
from apps.ai.features.base_v2 import BasicFeatureGeneratorV2
from apps.common.utils import Utils
from typing import Union, List, Dict
from django.conf import settings

class YahooFetcher(DjangoAppInitializer):
    def __init__(self, start: str, end: str = date.today().strftime("%Y-%m-%d"), interval: str = "1d",directory: str = settings.PROCESSED_DATA_DIR, *args, **kwargs) -> None:
        """
        Yahoo Finance から株価データを取得するFetcherクラス。

        Parameters:
        - start: 開始日 (例: "2021-01-01")
        - end: 終了日 (例: "2024-12-31")
        - interval: 取得間隔 ("1d", "1wk", "1mo")
        - directory: 保存先ディレクトリ
        """
        super().__init__(*args, **kwargs)
        Utils.validate_interval(interval)
        self.__start: str = start
        self.__end: str = end
        self.__interval: str = interval
        self.__price_columns = ["Open", "High", "Low", "Close", "Volume"]
        self.__raw_columns = ["Date"] + self.__price_columns
        self.__generator = BasicFeatureGeneratorV2()
        self.__parquet_handler = ParquetHandler(directory=directory, batch_size=20)

    def fetch(self,tickers: list[str]) -> pd.DataFrame:
        """
        指定ティッカーの当日株価（終値）をyfinanceで取得。

        Parameters:
        - tickers: ティッカーリスト
        - date_: yyyy-mm-dd形式の日付（例：today）

        Returns:
        - pd.DataFrame: yfinanceの結果（MultiIndex）
        """
        return yf.download(
            tickers=tickers,
            start=self.__start,
            end=self.__end,
            interval="1d",
            group_by="ticker",
            auto_adjust=False,
            threads=True
        )
    

    def download_and_transform(self, tickers: Union[list[str], dict[str, str]]) -> None:
        """
        指定されたティッカーの株価データを取得し、特徴量を変換後、Parquet形式で保存する。
        - 取得対象の情報はyfinanceの成功率85%以上のみに限定。
        - セクター情報はCSV等で事前取得されたものを用いる（Ticker: "MainSector_SubSector" のdict）。
        """
        if isinstance(tickers, dict):
            ticker_list = list(tickers.keys())
        else:
            ticker_list = tickers
            tickers = {t: "Unknown_Unknown" for t in ticker_list}  # fallback

        # 株価データを一括取得
        raw_data = yf.download(
            ticker_list,
            start=self.__start,
            end=self.__end,
            interval=self.__interval,
            group_by="ticker",
            auto_adjust=False
        )

        for ticker in tqdm(ticker_list , desc="Downloading and transforming data"):
            try:
                df = raw_data[ticker].copy().reset_index()

                # 特徴量変換
                transformed_df = self.__generator.transform(df)

                # ✅ データが空・NaNのみ・Date欠損ならスキップ
                if (
                    transformed_df.empty or
                    transformed_df.dropna(how="all").empty or
                    "Date" not in transformed_df.columns or
                    transformed_df["Date"].isna().all()
                ):
                    self.log.warning(f"{ticker} は変換後に有効なデータが無いためスキップ")
                    continue
        

                info = yf.Ticker(ticker).info

                # CSVなどから事前取得したセクター情報を分割
                sector_info = tickers.get(ticker, "Unknown_Unknown").replace(" ", "").replace("/", "-")
                
                # info オブジェクトから取得
                company_name = info.get("shortName", "N/A")

                # ファイル名生成・保存
                safe_ticker = Utils.sanitize_ticker_for_filename(ticker)
                safe_name = Utils.safe_filename_component(company_name)
                sector_info = Utils.safe_filename_component(sector_info)
                filename = f"{safe_ticker}_{safe_name}_{sector_info}.parquet"

                self.__parquet_handler.save(transformed_df, filename)
                self.log.info(f" 保存完了: {filename}")

            except Exception as e:
                self.log.error(f" 失敗: {ticker} - {e}")


    def update_parquet_files(self, tickers: list[str]) -> None:
        """
        各ティッカーに対応するParquetファイルを自動で更新する。
        - Parquetファイルは {Ticker}_{Company}_{Sector}.parquet 形式。
        - 直近7日間の株価データを取得し、200+n日分で特徴量を再生成。
        - 重複排除後、新規n行のみをParquetに追記。
        """
        today = date.today()
        start = (today - timedelta(days=10)).strftime("%Y-%m-%d")
        end = today.strftime("%Y-%m-%d")

        if isinstance(tickers, dict):
            ticker_list = list(tickers.keys())
        else:
            ticker_list = tickers
            tickers = {t: "Unknown_Unknown" for t in ticker_list}  # fallback

        # 株価データ一括取得
        raw_data = yf.download(
            ticker_list,
            start=start,
            end=end,
            interval=self.__interval,
            group_by="ticker",
            auto_adjust=False
        )

        for ticker in tqdm(tickers, desc="Updating parquet files"):
            try:
                parquet_path = self.__parquet_handler.get_file_by_ticker(ticker)

                if not parquet_path:
                    self.log.warning(f"No parquet file found for {ticker}. Skipping.")
                    continue

                df_existing = self.__parquet_handler.load(parquet_path).sort_values("Date")
                last_date = pd.to_datetime(df_existing["Date"].max())

                try:
                    df_new = raw_data[ticker].reset_index()
                    df_new = df_new[df_new["Date"] > last_date]
                except KeyError:
                    self.log.warning(f"No data for {ticker} in downloaded batch. Skipping.")
                    continue

                if df_new.empty:
                    continue

                df_new = df_new[self.__raw_columns]
                df_context = df_existing.tail(200)[self.__raw_columns]
                df_context = df_context

                df_merged = pd.concat([df_context, df_new]).drop_duplicates(subset="Date").sort_values("Date")

                df_features = self.__generator.transform(df_merged)
                df_new_features = df_features[df_features["Date"] > last_date]

                if df_new_features.empty:
                    continue

                df_updated = pd.concat([df_existing, df_new_features]) \
                    .drop_duplicates(subset="Date", keep="last") \
                    .sort_values("Date")

                self.__parquet_handler.save(df_updated, os.path.basename(parquet_path)) 
                self.log.info(f"Updated {os.path.basename(parquet_path)}: +{len(df_new_features)} rows")

            except Exception as e:
                self.log.error(f"[{ticker}] Failed to update: {e}")
                
    def extract_japan_tickers(self, filename: str) -> dict[str, str]:
        """
        日本株CSVのDataFrameからティッカーコードと業種情報を抽出（ETF等に対応）

        Parameters:
        - filename: 日本株銘柄情報のCSVファイル名

        Returns:
        - dict[str, str]: {"1301.T": "33業種_17業種", ...}
        """
        df = pd.read_csv(settings.LEARNING_DATA_DIR / filename)

        return {
            str(code).zfill(4) + ".T": f"{sector33 or 'Unknown'}_{sector17 or 'Unknown'}".replace(" ", "").replace("/", "-")
            for code, sector33, sector17 in zip(
                df["コード"], df.get("33業種区分", []), df.get("17業種区分", [])
            )
            if pd.notna(code)
        }

    def extract_us_tickers(self, filename: str) -> dict[str, str]:
        """
        米国株CSVのDataFrameからティッカーコードとセクター情報を抽出（NULL補完対応）

        Parameters:
        - filename: US株銘柄情報のCSVファイル名

        Returns:
        - dict[str, str]: {"AAPL": "InformationTechnology_TechnologyHardware", ...}
        """
        df = pd.read_csv(settings.LEARNING_DATA_DIR / filename)

        return {
            symbol: f"{(sector or 'Unknown')}_{(sub_sector or 'Unknown')}".replace(" ", "").replace("/", "-")
            for symbol, sector, sub_sector in zip(
                df["Symbol"], df.get("GICS Sector", []), df.get("GICS Sub-Industry", [])
            )
            if pd.notna(symbol)
        }


    def get_tickers_list(
        self,
        jp_ticker_csv: str,
        us_ticker_csv: str
    ) -> List[str]:
        """
        日本および米国のティッカーを結合してリスト化する。
        """
        jp_tickers = self.extract_japan_tickers(jp_ticker_csv)
        us_tickers = self.extract_us_tickers(us_ticker_csv)
        all_tickers = {**jp_tickers, **us_tickers}
        return list(all_tickers.keys())
    

    def get_tickers_list_random(
        self,
        jp_ticker_csv: str,
        us_ticker_csv: str,
        sample_size: int = 5
    ) -> List[str]:
        """
        日本および米国のティッカーからランダムに指定数選ぶ。
        """

        all_tickers = self.get_tickers_list(jp_ticker_csv, us_ticker_csv)
        return random.sample(all_tickers, k=sample_size)
