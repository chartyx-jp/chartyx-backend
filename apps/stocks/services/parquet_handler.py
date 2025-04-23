import os
import pandas as pd
from typing import Dict
from django.conf import settings

class ParquetHandler:
    def __init__(self, directory: str = settings.RAW_DATA_DIR) -> None:
        """
        parquetの読み書きを行う基底クラス。
        """
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
        print(f"Saved: {path}")

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
