import yfinance as yf
import glob
import pandas as pd
from pathlib import Path
from tqdm import tqdm
from datetime import date,timedelta
from apps.common.app_initializer import DjangoAppInitializer
from apps.stocks.services.parquet_handler import ParquetHandler
from apps.ai.features.base_v2 import BasicFeatureGeneratorV2
from apps.common.utils import Utils
from typing import Union, List, Dict
from django.conf import settings

class YahooFetcher(DjangoAppInitializer):
        #国ごとの設定(クラス定数)
    COUNTRY_META = {
    "japan": {
        "master_file": "japan_master.csv",
        "folder": "japan",
        "extract_func": "extract_japan_tickers"  # メソッド名で記録
    },
    "usa": {
        "master_file": "us_master.csv",
        "folder": "us",
        "extract_func": "extract_us_tickers"
        }
    }

    def __init__(self, start: str, end: str = date.today().strftime("%Y-%m-%d"), interval: str = "1d",directory: str = settings.RAW_DATA_DIR,       *args, **kwargs) -> None:
        
        """
        Yahoo Finance から株価データを取得するFetcherクラス。

        Parameters:
        - start: 開始日 (例: "2021-01-01")
        - end: 終了日 (例: "2024-12-31")
        - interval: 取得間隔 ("1d", "1wk", "1mo")
        - directory: 保存先ディレクトリ
        - generator: 特徴量生成器
        """
        super().__init__(*args, **kwargs)

        Utils.validate_interval(interval)


        self.__start: str = start
        self.__end: str = end
        self.__interval: str = interval
        self.__price_columns = ["Open", "High", "Low", "Close", "Volume"]
        self.__raw_columns = ["Date"] + self.__price_columns
        self.__parquet_handler = ParquetHandler(directory=directory, batch_size=20)

    def fetch(self,tickers: list[str] = None) -> pd.DataFrame:
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
            interval=self.__interval,
            group_by="ticker",
            auto_adjust=False
            )
    
    def download(self) -> None:
        """
        指定されたティッカーの株価データを取得し、Parquet形式で保存する。
        - 取得対象の情報はyfinanceの成功率85%以上のみに限定。
        - セクター情報はCSV等で事前取得されたものを用いる（Ticker: "MainSector_SubSector" のdict）。
        """

        all_tickers_grouped = self.get_all_tickers_grouped()



        for country, tickers in all_tickers_grouped.items():
            # 株価データを一括取得
            tickers_list = list(tickers.keys())
            raw_data = self.fetch(tickers_list)


            self.log.info(f" 取得完了: {country} - {len(tickers_list)} 銘柄")

            for ticker in tqdm(tickers_list ,desc=f"{country}のTICKER情報をダウンロードしています。"):
                try:
                    # raw_data = self.fetch(ticker)
                    df = raw_data[ticker].copy().reset_index()

                    # 特徴量変換
                    # transformed_df = self.__generator.transform(df)

                    #  データが空・NaNのみ・Date欠損ならスキップ
                    if (
                        df.empty or
                        df.dropna(how="all").empty or
                        "Date" not in df.columns or
                        df["Date"].isna().all()
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

                    self.__parquet_handler.save(df, filename,folder_name=self.COUNTRY_META[country]["folder"])
                    self.log.info(f" 保存完了: {filename}")

                except Exception as e:
                    self.log.error(f" 失敗: {ticker} - {e}")


    def update_parquet_files(self) -> None:
        """
        各ティッカーに対応するParquetファイルを自動で更新する。
        - Parquetファイルは {Ticker}_{Company}_{Sector}.parquet 形式。
        - 直近20日間の株価データを取得し、200+n日分で特徴量を再生成。
        - 重複排除後、新規n行のみをParquetに追記。
        """

        all_tickers_grouped = self.get_all_tickers_grouped()

        for country, tickers in all_tickers_grouped.items():
            # 株価データを一括取得
            tickers_list = list(tickers.keys())
            raw_data = self.fetch(tickers_list)
            self.log.info(f" 取得完了: {country} - {len(tickers_list)} 銘柄")
            for ticker in tqdm(tickers_list, desc=f"{country}のデータをアップデートしています。"):
                try:
                    parquet_path:Path = self.__parquet_handler.get_file_by_ticker(ticker)

                    if not parquet_path:
                        self.log.warning(f"{ticker}のファイルが見つかりません。スキップ。")
                        continue

                    df_existing = self.__parquet_handler.load(parquet_path).sort_values("Date")
                    last_date = pd.to_datetime(df_existing["Date"].max())

                    try:
                        df_new = raw_data[ticker].reset_index()
                        df_new = df_new[df_new["Date"] > last_date]
                    except KeyError:
                        self.log.warning(f"{ticker}のデータがありません。スキップ。")
                        continue

                    if df_new.empty:
                        self.log.warning(f"{ticker}の新しいデータがありません。スキップ。")
                        continue

                    df_new = df_new[self.__raw_columns]
                    df_context = df_existing.tail(200)[self.__raw_columns]

                    df_merged = pd.concat([df_context, df_new]).drop_duplicates(subset="Date").sort_values("Date")


                    df_updated = pd.concat([df_existing, df_merged]) \
                        .drop_duplicates(subset="Date", keep="last") \
                        .sort_values("Date")

                    self.__parquet_handler.save(df_updated, parquet_path.name, folder_name=self.COUNTRY_META[country]["folder"]) 
                    self.log.info(f"Updated {parquet_path.name}: +{len(df_merged)} rows")

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


    def get_tickers_by_country(self, country: str) -> dict[str, str]:
        """
        国に対応するマスタファイルを使ってティッカーを抽出。
        """
        meta = self.COUNTRY_META[country]
        func = getattr(self, meta["extract_func"]) # メソッド名を取得
        return func(meta["master_file"]) #各国のマスタファイルを読み込み、ティッカーを抽出

    def get_all_tickers_grouped(self) -> dict[str, dict[str, str]]:
        """
        全COUNTRYのティッカー情報を {country: {ticker: sector}} の形で返す。
        """
        return {country: self.get_tickers_by_country(country) for country in self.COUNTRY_META}

    def get_all_ticker_lists(self) -> list[list[str]]:
        """
        すべての国のティッカーリストを 2次元配列で返す。
        """
        return [list(tickers.keys()) for tickers in self.get_all_tickers_grouped().values()]