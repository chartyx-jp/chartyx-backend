import os
import pandas as pd
import logging
from typing import Dict
from logs.logger import LogHelper
from django.conf import settings

class ParquetHandler:
    def __init__(self, directory: str = settings.RAW_DATA_DIR) -> None:
        """
        parquetの読み書きを行う基底クラス。
        ディレクトリが存在しなければ作成する。
        """

        self.__logger: logging.Logger = LogHelper.get_logger(self)
        self.__directory = str(directory)
        os.makedirs(self.__directory, exist_ok=True)

    def save(self, df: pd.DataFrame, filename: str) -> None:
        """
        DataFrameをparquetとして保存する。

        Parameters:
        - df: 保存するDataFrame
        - filename: ファイル名（拡張子付き）
        """
        path = os.path.join(self.__directory, filename)
        df.to_parquet(path, index=False)
        self.log.info(f"Saved: {path}")

    def delete_all(self, suffix: str = ".parquet") -> int:
        """
        指定ディレクトリ内の指定拡張子ファイルを一括削除する。

        Parameters:
        - suffix (str): 削除対象とするファイルの拡張子や接尾辞（例: ".parquet", "_complete.parquet"）

        Returns:
        - int: 削除したファイルの数
        """
        deleted = 0
        for filename in os.listdir(self.__directory):
            if filename.endswith(suffix):
                path = os.path.join(self.__directory, filename)
                try:
                    os.remove(path)
                    deleted += 1
                    self.log.info(f" 削除: {filename}")
                except Exception as e:
                    self.log.error(f" 削除失敗: {filename} - {e}")
        self.log.info(f" 削除完了: {deleted} ファイル")
        return deleted

    def load(self, filename: str) -> pd.DataFrame:
        """
        parquetファイルを読み込み、DataFrameとして返す。

        Parameters:
        - filename: 読み込むparquetファイル名

        Returns:
        - pd.DataFrame: 読み込まれたデータ
        """
        path = os.path.join(self.__directory, filename)
        return pd.read_parquet(path)

    def save_multiple(self, df_dict: Dict[str, pd.DataFrame], suffix: str = "1d") -> None:
        """
        複数のDataFrameを一括で保存する。

        Parameters:
        - df_dict: {ticker: DataFrame} の辞書
        - suffix: 出力ファイル名に使う接尾辞（例: '1d'）
        """
        for ticker, df in df_dict.items():
            filename = f"{ticker}_{suffix}.parquet"
            self.save(df, filename)

    def load_all(self, suffix: str = "_complete.parquet") -> pd.DataFrame:
        """
        指定ディレクトリ内のparquetファイルを一括読み込み。

        Parameters:
        - suffix: ファイル名のフィルタリング条件（例: "_complete.parquet"）

        Returns:
        - pd.DataFrame: すべてのファイルを結合したDataFrame
        """
        all_dfs = []
        for filename in os.listdir(self.__directory):
            if filename.endswith(suffix):
                path = os.path.join(self.__directory, filename)
                try:
                    df = pd.read_parquet(path)
                    all_dfs.append(df)
                except Exception as e:
                    self.log.error(f" 読み込み失敗: {filename} - {e}")
        if not all_dfs:
            raise FileNotFoundError(f"No files with suffix '{suffix}' in {self.__directory}")
        return pd.concat(all_dfs, ignore_index=True)
    
    @property
    def log(self) -> logging.Logger:
        """ロガーオブジェクトのアクセサ"""
        return self.__logger
