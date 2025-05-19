import shutil
import pandas as pd
from pathlib import Path
from apps.common.utils import Utils
from tqdm import tqdm
from typing import Dict, Optional
from apps.common.app_initializer import DjangoAppInitializer
from django.conf import settings


class ParquetHandler(DjangoAppInitializer):
    def __init__(self, directory: Path = settings.RAW_DATA_DIR, batch_size: int = 20, *args, ** kwargs) -> None:
        super().__init__(*args, **kwargs)
        """
        parquetの読み書きを行う基底クラス。
        ディレクトリが存在しなければ作成する。
        """

        directory.mkdir(parents=True, exist_ok=True)


        self.__directory: Path = directory
        self.__batch_size = batch_size
        self.__all_files = [f for f in self.__directory.iterdir()
                        if f.is_file() and f.suffix == ".parquet"]
        self.__current_batch_index = 0


    def refresh_all_files(self) -> None:
        """
        指定ディレクトリ内のすべてのparquetファイルを更新する。
        """
        self.__all_files = [f for f in self.__directory.iterdir()
                        if f.is_file() and f.suffix == ".parquet"]

    def save(self, df: pd.DataFrame, filename: str, folder_name: str = None) -> None:
        """
        DataFrameをparquetとして保存する。

        Parameters:
        - df: 保存するDataFrame
        - filename: ファイル名（拡張子付き）
        - folder_name: サブディレクトリ名（任意）
        """
        # ベースパスの組み立て
        try:
            path = self.__directory

            if folder_name:
                path = path / folder_name

            path.mkdir(parents=True, exist_ok=True)  # ディレクトリが存在しない場合は作成

            full_path = path / filename  # ファイルパスを結合
            df.to_parquet(full_path, index=False, compression="snappy")
        except Exception as e:
            self.log.error(f" 保存失敗: {filename} - {e}")
            raise e    
        finally:
            self.refresh_all_files()  # 保存後にファイルリストを更新
        

    def view_parquet_preview(self, filename: str) -> pd.DataFrame:
        """
        指定されたParquetファイルの最初のn行を表示するユーティリティ。

        Parameters:
        - filename (str): 読み込むParquetファイル名

        Returns:
        - pd.DataFrame: 指定ファイルのプレビュー
        """
        full_path = self.__directory / filename  # パス結合は / で

        if not full_path.exists():  # Pathオブジェクトで存在確認
            raise FileNotFoundError(f"ファイルが存在しません: {full_path}")

        df = pd.read_parquet(full_path)
        pd.set_option('display.max_columns', None)
        self.log.info(f" プレビュー表示: {filename} | 行数: {len(df)} | カラム数: {df.shape[1]}")
        return df


    def delete_all(self, suffix: str = ".parquet") -> int:
        """
        指定ディレクトリ内の指定拡張子ファイルを一括削除する。

        Parameters:
        - suffix (str): 削除対象とするファイルの拡張子や接尾辞（例: ".parquet", "_complete.parquet"）

        Returns:
        - int: 削除したファイルの数
        """
        try:
            deleted = 0

            for file in self.__all_files:
                if file.is_file() and file.suffix(suffix):
                    try:
                        file.unlink()  # ← Pathオブジェクトの削除メソッド
                        deleted += 1
                        self.log.info(f" 削除: {file.name}")
                    except Exception as e:
                        self.log.error(f" 削除失敗: {file.name} - {e}")
            

            self.log.info(f" 削除完了: {deleted} ファイル")
            return deleted
        except Exception as e:
            self.log.error(f" 削除失敗: {e}")
            raise e
        finally:
            self.refresh_all_files()

    def load(self, filename: str) -> pd.DataFrame:
        """
        __all_files の中から指定ファイルを探して読み込む。

        Parameters:
        - filename: 読み込むファイル名（ファイル名のみ）

        Returns:
        - pd.DataFrame: 読み込んだデータ
        """
        match = next((f for f in self.__all_files if f.name == filename), None)

        if not match:
            raise FileNotFoundError(f"指定されたファイルが見つかりません: {filename}")

        return pd.read_parquet(match)
    
    def load_all(self, suffix: str = ".parquet") -> pd.DataFrame:
        """
        指定ディレクトリ内のparquetファイルを一括読み込み。

        Parameters:
        - suffix: ファイル名のフィルタリング条件（例: "_complete.parquet"）

        Returns:
        - pd.DataFrame: すべてのファイルを結合したDataFrame
        """
        all_dfs = []

        for file in self.__all_files:
            if file.is_file() and file.suffix == suffix:
                try:
                    df = pd.read_parquet(file)
                    all_dfs.append(df)
                except Exception as e:
                    self.log.error(f" 読み込み失敗: {file.name} - {e}")

        if not all_dfs:
            raise FileNotFoundError(f" '{suffix}' は {self.__directory} に存在しません")

        return pd.concat(all_dfs, ignore_index=True)

    def get_next_batch_filenames(self) -> list[Path]:
            start = self.__current_batch_index * self.__batch_size
            end = start + self.__batch_size
            batch_files = self.__all_files[start:end]
            self.__current_batch_index += 1
            return batch_files
    
    def has_more_batches(self) -> bool:
            return self.__current_batch_index * self.__batch_size < len(self.__all_files)

    def load_batch(self, filenames: list[str]) -> pd.DataFrame:
        """
        指定されたファイル名リストに対して、対応するParquetファイルを読み込んで結合する。

        Parameters:
        - filenames: 読み込むファイル名のリスト（文字列）

        Returns:
        - pd.DataFrame: 結合されたDataFrame
        """
        all_dfs = []

        for filename in filenames:
            try:
                df = self.load(filename)
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
        else:
            shutil.copytree(self.__directory, r"G:\マイドライブ\chartyx-ai-colab\processed_data", dirs_exist_ok=True)

            


    def get_file_by_ticker(self, ticker_base: str) -> Optional[Path]:
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
            self.log.info(f"[WARN] 複数ファイルが見つかりました for {ticker_base} → {matching}. 最初の1件を使用。")

        return self.__directory / matching[0]

    def get_latest_row_by_ticker(self, ticker_base: str ,n:int = 1) -> Optional[pd.Series]:
        """
        - n < 10 の場合 → 該当の1行（Series）を返す（通常推論用）
        - n>=10 の場合 → 最新n行のDataFrameを返す（SHAP・分析用）
        """
        path = self.get_file_by_ticker(ticker_base)  # フルパスを取得
        if not path:
            return None

        df = self.load(path)
        df["Date"] = pd.to_datetime(df["Date"])  # 念のため日付型に
        df_sorted = df.sort_values("Date")

        if df_sorted.empty:
            return None
        
        if n >= 10:
            return df_sorted.iloc[-n:]
        else:
            return df_sorted.iloc[-n]  # 最終行（最新日）
        
    def copy_tickerFile_to(self, target_dir: str, ticker_base: str = None) -> None:
        """
        指定されたティッカーファイルをターゲットディレクトリにコピーする。

        Parameters:
        - target_dir: コピー先のディレクトリ（str or Path）
        - ticker_base: ティッカーファイルのベース名（例: '7203.T'）
        """
        source_path = self.get_file_by_ticker(ticker_base)  # ← Path を返す前提
        print(f"source_path: {source_path}")

        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir / source_path.name
        shutil.copy2(source_path, target_path)


    def calc_flat_target_ratio(self, threshold: float = 1e-4) -> float:
        """
        Target列の変動が閾値以下の行が、全行のうち何％あるかを返す。

        Parameters:
        - threshold: 絶対値でこの値以下のTargetを「変動なし」と見なす

        Returns:
        - flat_ratio: 全体に対する「ほぼ変動なし」行の割合（0〜1）
        """
        total_rows = 0
        flat_rows = 0

        for f in tqdm(self.__all_files, desc="Reransforming files"):
            df = self.load(f)

            if "Target" not in df.columns:
                self.log.info(f"Target列が見つかりません: {f}")
                continue  # Target列がない場合はスキップ

            df = df.dropna(subset=["Target"])  # 欠損値は除外
            total_rows += len(df)
            flat_rows += (df["Target"].abs() <= threshold).sum()

        if total_rows == 0:
            return 0.0

        return flat_rows / total_rows
