import os
import pandas as pd
from apps.common.utils import Utils
from tqdm import tqdm
from typing import Dict, Optional
from apps.common.app_initializer import DjangoAppInitializer
from django.conf import settings

class ParquetHandler(DjangoAppInitializer):
    def __init__(self, directory: str = settings.PROCESSED_DATA_DIR, batch_size: int = 20, *args, ** kwargs) -> None:
        super().__init__(*args, **kwargs)
        """
        parquetの読み書きを行う基底クラス。
        ディレクトリが存在しなければ作成する。
        """

        os.makedirs(directory, exist_ok=True)


        self.__directory: str = directory
        self.__batch_size = batch_size
        self.__all_files = [f for f in os.listdir(directory) if f.endswith(".parquet")]
        self.__current_batch_index = 0



    def save(self, df: pd.DataFrame, filename: str) -> None:
        """
        DataFrameをparquetとして保存する。

        Parameters:
        - df: 保存するDataFrame
        - filename: ファイル名（拡張子付き）
        """
        path = os.path.join(self.__directory, filename)
        df.to_parquet(path, index=False,compression="snappy")


    def view_parquet_preview(self, filename: str, n: int = 5) -> pd.DataFrame:
        """
        指定されたParquetファイルの最初のn行を表示するユーティリティ。

        Parameters:
        - filename (str): 読み込むParquetファイル名
        - n (int): 表示する行数（デフォルト5）

        Returns:
        - pd.DataFrame: 指定ファイルのプレビュー
        """
        import os
        import pandas as pd

        full_path = os.path.join(self.__directory, filename)

        if not os.path.exists(full_path):
            raise FileNotFoundError(f"ファイルが見つかりません: {full_path}")

        df = pd.read_parquet(full_path)
        self.log.info(f" プレビュー表示: {filename} | 行数: {len(df)} | カラム数: {df.shape[1]}")
        return df.head(n)


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


    def load_all(self, suffix: str = ".parquet") -> pd.DataFrame:
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


    def get_next_batch_filenames(self) -> list[str]:
            start = self.__current_batch_index * self.__batch_size
            end = start + self.__batch_size
            batch_files = self.__all_files[start:end]
            self.__current_batch_index += 1
            return batch_files
    
    def has_more_batches(self) -> bool:
            return self.__current_batch_index * self.__batch_size < len(self.__all_files)

    def load_batch(self, filenames: list[str]) -> pd.DataFrame:
        all_dfs = []
        for filename in filenames:
            path = os.path.join(self.__directory, filename)
            try:
                df = pd.read_parquet(path)
                all_dfs.append(df)
            except Exception as e:
                self.log.info(f" 読み込み失敗: {filename} - {e}")
        if not all_dfs:
            raise FileNotFoundError("バッチに読み込めるファイルが存在しません")
        return pd.concat(all_dfs, ignore_index=True)
    
    
    def retransform_all_files(self, generator) -> None:
        """
        既存のparquetファイルをすべて読み込み、
        transformを通して再加工し、上書き保存する
        """
        for f in tqdm(self.__all_files, desc="Reransforming files"):
            try:
                df = self.load(f)
                df_transformed = generator.transform(df)
                self.save(df_transformed, f)
            except Exception as e:
                self.log.error(f" 変換失敗: {f} - {e}")


    def get_file_by_ticker(self, ticker_base: str) -> Optional[str]:
        """
        指定された ticker_base に対応する Parquet ファイル（先頭一致）を1つ返す。
        複数ある場合は最初の1件、なければ None。
        """

        ticker_base = Utils.sanitize_ticker_for_filename(ticker_base)

        matching = [
            f for f in self.__all_files
            if f.startswith(f"{ticker_base}_")
        ]
        if not matching:
            return None

        if len(matching) > 1:
            print(f"[WARN] 複数ファイルが見つかりました for {ticker_base} → {matching}. 最初の1件を使用。")

        return os.path.join(self.__directory, matching[0])

    def get_latest_row_by_ticker(self, ticker_base: str) -> Optional[pd.Series]:
        """
        指定された ticker_base に一致するParquetファイルの最終行（最新日付の行）を返す。
        """
        path = self.get_file_by_ticker(ticker_base)  # フルパスを取得
        if not path:
            return None

        df = self.load(path)
        df["Date"] = pd.to_datetime(df["Date"])  # 念のため日付型に
        df_sorted = df.sort_values("Date")

        if df_sorted.empty:
            return None

        # return df_sorted.tail(5)
        return df_sorted.iloc[-1]  # 最終行（最新日）
