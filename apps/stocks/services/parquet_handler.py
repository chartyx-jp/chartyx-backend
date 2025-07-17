import shutil
import pandas as pd
import numpy as np
from pathlib import Path
from apps.common.utils import Utils
from tqdm import tqdm
from typing import Dict, Optional, Generator,List, Union
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
        self.__current_batch_index = 0
        
        # ディレクトリ内のparquetファイルを取得
        self.refresh_all_files()


    @property
    def files(self) -> list[Path]:
        """
        現在のディレクトリ内のparquetファイルを返す。
        """
        return self.__all_files


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
                if file.is_file() and file.name.endswith(suffix):
                    try:
                        file.unlink()
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

    def load(self, path:Path) -> pd.DataFrame:
        """
        __all_files の中から指定ファイルを探して読み込む。

        Parameters:
        - filename: 読み込むファイル名（ファイル名のみ）

        Returns:
        - pd.DataFrame: 読み込んだデータ
        """
        if isinstance(path, str):
            path = Path(path)

        return pd.read_parquet(path)
    

    def load_each(self, suffix: str = ".parquet") -> Generator[pd.DataFrame, None, None]:
        """
        指定ディレクトリ内のparquetファイルを1つずつyieldで返す。
        メモリ節約のためconcatはしない。

        Parameters:
        - suffix: ファイル名のフィルタリング条件

        Yields:
        - pd.DataFrame: 各ファイル単位のデータフレーム
        """
        for file in tqdm(self.__all_files, desc="ファイルを読み込んでいます"):
            if file.is_file() and file.suffix == suffix:
                try:
                    df = self.load(file)
                    yield df
                except Exception as e:
                    self.log.error(f" 読み込み失敗: {file.name} - {e}")



    def get_next_batch_filenames(self) -> list[Path]:
            start = self.__current_batch_index * self.__batch_size
            end = start + self.__batch_size
            batch_files = self.__all_files[start:end]
            self.__current_batch_index += 1
            return batch_files
    
    def has_more_batches(self) -> bool:
            return self.__current_batch_index * self.__batch_size < len(self.__all_files)

    def load_batch(self, files: list[Path]) -> pd.DataFrame:
        """
        指定されたファイル名リストに対して、対応するParquetファイルを読み込んで結合する。

        Parameters:
        - filenames: 読み込むファイル名のリスト（文字列）

        Returns:
        - pd.DataFrame: 結合されたDataFrame
        """
        all_dfs = []

        for file in files:
            try:
                df = self.load(file)
                all_dfs.append(df)
            except Exception as e:
                self.log.info(f" 読み込み失敗: {file} - {e}")

        if not all_dfs:
            raise FileNotFoundError("バッチに読み込めるファイルが存在しません")

        return pd.concat(all_dfs, ignore_index=True)
    
    def retransform_all_files(self, column:Optional[List[str]]=None ,
                            generator:Optional[Generator]=None,
                            handler:Optional["ParquetHandler"]=None, 
                            google_drive:bool=False)-> None:
        """
        既存のparquetファイルをすべて読み込み、
        transformを通して再加工し、上書き保存する
        """
        try:
            for f in tqdm(self.__all_files, desc="Reransforming files"):
                try:
                    # ファイルを読み込む
                    df = self.load(f)
                    # 列指定がある場合はその列のみを選択
                    if column is not None:
                        df = df[column]
                    # 列名を変更する場合はここで行う
                    if generator is not None:
                        df = generator.transform(df)

                    #保存先の指定先がある場合はその場所に保存
                    if handler is not None:
                        handler.save(df, f.name)
                    else:
                        self.save(df, f.name)

                except Exception as e:
                    self.log.error(f" 変換失敗: {f} - {e}")
            else:
                if google_drive:
                    # Google Driveに保存する場合
                    self.log.info("Google Driveに保存中...")
                    shutil.copytree(self.__directory, r"G:\マイドライブ\chartyx-ai-colab\processed_data", dirs_exist_ok=True)
        except Exception as e:
            self.log.error(f" 変換失敗: {e}")
            raise e
        finally:
            self.refresh_all_files()  # 保存後にファイルリストを更新

            


    def get_file_by_ticker(self, ticker_base: str) -> Optional[Path]:
        """
        指定された ticker_base に対応する Parquet ファイル（先頭一致）を1つ返す。
        複数ある場合は最初の1件、なければ None。
        """

        ticker_base = Utils.sanitize_ticker_for_filename(ticker_base)
        
        matching = [
            f for f in self.__all_files
            if str(f.name).startswith(f"{ticker_base}_")
        ]
        if not matching:
            self.log.info(f"get_file_by_ticker: {ticker_base} → ファイルが見つかりません")
            return None

        if len(matching) > 1:
            self.log.info(f"[WARN] 複数ファイルが見つかりました for {ticker_base} → {matching}. 最初の1件を使用。")

        self.log.info("ファイル取得: " + str(matching[0]))
        return matching[0]


    def get_latest_row_by_ticker(self, ticker_base: str, n: int = 1) -> Optional[Union[pd.Series, pd.DataFrame]]:

        """
        - n < 10 の場合 → 該当の1行（Series）を返す（通常推論用）
        - n>=10 の場合 → 最新n行のDataFrameを返す（SHAP・分析用）
        """
        path = self.get_file_by_ticker(ticker_base)  # フルパスを取得
        if not path:
            self.log.info(f"get_latest_row_by_ticker: {ticker_base} → ファイルが見つかりません")
            return None
        df = self.load(path)
        self.log.info(f" データフレームの行数: {len(df)}")
        df["Date"] = pd.to_datetime(df["Date"])  # 念のため日付型に
        df_sorted = df.sort_values("Date")

        if df_sorted.empty:
            return None
        
        if n >= 10:
            return df_sorted.iloc[-n:]
        else:
            return df_sorted.iloc[-n]  # 最終行（最新日）
        
    def copy_tickerFile_to(self, target_dir: Path, ticker_base: Optional[str] = None) -> None:
        """
        指定されたティッカーファイルをターゲットディレクトリにコピーする。

        Parameters:
        - target_dir: コピー先のディレクトリ（str or Path）
        - ticker_base: ティッカーファイルのベース名（例: '7203.T'）
        """
        
        if ticker_base:
            source_path: Optional[Path] = self.get_file_by_ticker(ticker_base)
            if source_path is None:
                self.log.error(f"ティッカーファイルが見つかりません: {ticker_base}")
                return
            print(f"source_path: {source_path}")
        else:
            source_path = self.__directory
        
        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir / source_path.name
        shutil.copy2(source_path, target_path)
        
    
    def get_all_tickers(self) -> List[str]:
        """
        ディレクトリ内のすべてのティッカーを取得する。
        ファイル名からティッカー部分を抽出してリストで返す。

        Returns:
        - List[str]: ティッカーのリスト
        """
        tickers = []
        for file in self.__all_files:
            if file.is_file() and file.suffix == ".parquet":
                ticker = file.stem.split("_")[0]
                tickers.append(ticker)
        return sorted(set(tickers))
    
    def search_tickers_by_ticker(self, query: str) -> List[str]:
        """
        ティッカーの部分一致検索を行う。

        Parameters:
        - query: 検索クエリ（大文字小文字は区別しない）

        Returns:
        - List[str]: 一致するティッカーのリスト
        """
        query = query.strip().upper()
        return [Utils.squash_delimiters(file.stem.split("_")[1]) for file in self.__all_files if query in file.stem.split("_")[0].upper()]

    # テクニカル指標計算メソッド
    def calculate_sma(self, ticker_base: str, period: int = 20) -> dict:
        """
        単純移動平均（SMA）を計算する
        
        Parameters:
        - ticker_base: 銘柄コード
        - period: 計算期間（デフォルト: 20）
        
        Returns:
        - dict: レスポンス形式のデータ
        """
        try:
            # データファイルを取得
            parquet_file = self.get_file_by_ticker(ticker_base)
            if not parquet_file:
                return {'error': f'ticker {ticker_base} not found'}
            
            # データを読み込み
            df = self.load(parquet_file)
            
            # 必要な列が存在するかチェック
            if 'Close' not in df.columns or 'Date' not in df.columns:
                return {'error': 'Required columns (Close, Date) not found'}
            
            # データが十分にあるかチェック
            if len(df) < period:
                return {'error': f'Insufficient data. Need at least {period} records, got {len(df)}'}
            
            # 日付でソート
            df = df.sort_values('Date').reset_index(drop=True)
            
            # SMA計算
            df['sma'] = df['Close'].rolling(window=period).mean()
            
            # NaNを除去
            df_result = df.dropna(subset=['sma'])
            
            # レスポンス形式に変換
            data = []
            for _, row in df_result.iterrows():
                data.append({
                    'date': Utils.unix_to_datestr(row['Date']) if isinstance(row['Date'], (int, float)) else str(row['Date']),
                    'value': float(row['sma'])
                })
            
            return {
                'ticker': ticker_base,
                'indicator': 'sma',
                'data': data
            }
            
        except Exception as e:
            self.log.error(f"SMA計算エラー: {e}")
            return {'error': f'Calculation failed: {str(e)}'}

    def calculate_ema(self, ticker_base: str, period: int = 12) -> dict:
        """
        指数移動平均（EMA）を計算する
        
        Parameters:
        - ticker_base: 銘柄コード
        - period: 計算期間（デフォルト: 12）
        
        Returns:
        - dict: レスポンス形式のデータ
        """
        try:
            # データファイルを取得
            parquet_file = self.get_file_by_ticker(ticker_base)
            if not parquet_file:
                return {'error': f'ticker {ticker_base} not found'}
            
            # データを読み込み
            df = self.load(parquet_file)
            
            # 必要な列が存在するかチェック
            if 'Close' not in df.columns or 'Date' not in df.columns:
                return {'error': 'Required columns (Close, Date) not found'}
            
            # データが十分にあるかチェック
            if len(df) < period:
                return {'error': f'Insufficient data. Need at least {period} records, got {len(df)}'}
            
            # 日付でソート
            df = df.sort_values('Date').reset_index(drop=True)
            
            # EMA計算
            df['ema'] = df['Close'].ewm(span=period).mean()
            
            # NaNを除去
            df_result = df.dropna(subset=['ema'])
            
            # レスポンス形式に変換
            data = []
            for _, row in df_result.iterrows():
                data.append({
                    'date': Utils.unix_to_datestr(row['Date']) if isinstance(row['Date'], (int, float)) else str(row['Date']),
                    'value': float(row['ema'])
                })
            
            return {
                'ticker': ticker_base,
                'indicator': 'ema',
                'data': data
            }
            
        except Exception as e:
            self.log.error(f"EMA計算エラー: {e}")
            return {'error': f'Calculation failed: {str(e)}'}

    def calculate_rsi(self, ticker_base: str, period: int = 14) -> dict:
        """
        RSI（Relative Strength Index）を計算する
        
        Parameters:
        - ticker_base: 銘柄コード
        - period: 計算期間（デフォルト: 14）
        
        Returns:
        - dict: レスポンス形式のデータ
        """
        try:
            # データファイルを取得
            parquet_file = self.get_file_by_ticker(ticker_base)
            if not parquet_file:
                return {'error': f'ticker {ticker_base} not found'}
            
            # データを読み込み
            df = self.load(parquet_file)
            
            # 必要な列が存在するかチェック
            if 'Close' not in df.columns or 'Date' not in df.columns:
                return {'error': 'Required columns (Close, Date) not found'}
            
            # データが十分にあるかチェック
            if len(df) < period + 1:
                return {'error': f'Insufficient data. Need at least {period + 1} records, got {len(df)}'}
            
            # 日付でソート
            df = df.sort_values('Date').reset_index(drop=True)
            
            # 価格変化を計算
            df['price_change'] = df['Close'].diff()
            
            # 上昇と下降を分離
            df['gain'] = np.where(df['price_change'] > 0, df['price_change'], 0)
            df['loss'] = np.where(df['price_change'] < 0, -df['price_change'], 0)
            
            # 平均利得と平均損失を計算
            df['avg_gain'] = df['gain'].rolling(window=period).mean()
            df['avg_loss'] = df['loss'].rolling(window=period).mean()
            
            # RSを計算
            df['rs'] = df['avg_gain'] / df['avg_loss']
            
            # RSIを計算
            df['rsi'] = 100 - (100 / (1 + df['rs']))
            
            # NaNを除去
            df_result = df.dropna(subset=['rsi'])
            
            # レスポンス形式に変換
            data = []
            for _, row in df_result.iterrows():
                data.append({
                    'date': Utils.unix_to_datestr(row['Date']) if isinstance(row['Date'], (int, float)) else str(row['Date']),
                    'value': float(row['rsi'])
                })
            
            return {
                'ticker': ticker_base,
                'indicator': 'rsi',
                'data': data
            }
            
        except Exception as e:
            self.log.error(f"RSI計算エラー: {e}")
            return {'error': f'Calculation failed: {str(e)}'}

    def calculate_macd(self, ticker_base: str, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
        """
        MACD（Moving Average Convergence Divergence）を計算する
        
        Parameters:
        - ticker_base: 銘柄コード
        - fast: 短期EMA期間（デフォルト: 12）
        - slow: 長期EMA期間（デフォルト: 26）
        - signal: シグナル線期間（デフォルト: 9）
        
        Returns:
        - dict: レスポンス形式のデータ
        """
        try:
            # データファイルを取得
            parquet_file = self.get_file_by_ticker(ticker_base)
            if not parquet_file:
                return {'error': f'ticker {ticker_base} not found'}
            
            # データを読み込み
            df = self.load(parquet_file)
            
            # 必要な列が存在するかチェック
            if 'Close' not in df.columns or 'Date' not in df.columns:
                return {'error': 'Required columns (Close, Date) not found'}
            
            # データが十分にあるかチェック
            if len(df) < slow + signal:
                return {'error': f'Insufficient data. Need at least {slow + signal} records, got {len(df)}'}
            
            # 日付でソート
            df = df.sort_values('Date').reset_index(drop=True)
            
            # EMAを計算
            df['ema_fast'] = df['Close'].ewm(span=fast).mean()
            df['ema_slow'] = df['Close'].ewm(span=slow).mean()
            
            # MACDラインを計算
            df['macd'] = df['ema_fast'] - df['ema_slow']
            
            # シグナルラインを計算
            df['signal'] = df['macd'].ewm(span=signal).mean()
            
            # ヒストグラムを計算
            df['histogram'] = df['macd'] - df['signal']
            
            # NaNを除去
            df_result = df.dropna(subset=['macd', 'signal', 'histogram'])
            
            # レスポンス形式に変換
            data = []
            for _, row in df_result.iterrows():
                data.append({
                    'date': Utils.unix_to_datestr(row['Date']) if isinstance(row['Date'], (int, float)) else str(row['Date']),
                    'value': {
                        'macd': float(row['macd']),
                        'signal': float(row['signal']),
                        'histogram': float(row['histogram'])
                    }
                })
            
            return {
                'ticker': ticker_base,
                'indicator': 'macd',
                'data': data
            }
            
        except Exception as e:
            self.log.error(f"MACD計算エラー: {e}")
            return {'error': f'Calculation failed: {str(e)}'}

    def calculate_bollinger_bands(self, ticker_base: str, period: int = 20, std_dev: float = 2.0) -> dict:
        """
        ボリンジャーバンドを計算する
        
        Parameters:
        - ticker_base: 銘柄コード
        - period: 計算期間（デフォルト: 20）
        - std_dev: 標準偏差の倍数（デフォルト: 2.0）
        
        Returns:
        - dict: レスポンス形式のデータ
        """
        try:
            # データファイルを取得
            parquet_file = self.get_file_by_ticker(ticker_base)
            if not parquet_file:
                return {'error': f'ticker {ticker_base} not found'}
            
            # データを読み込み
            df = self.load(parquet_file)
            
            # 必要な列が存在するかチェック
            if 'Close' not in df.columns or 'Date' not in df.columns:
                return {'error': 'Required columns (Close, Date) not found'}
            
            # データが十分にあるかチェック
            if len(df) < period:
                return {'error': f'Insufficient data. Need at least {period} records, got {len(df)}'}
            
            # 日付でソート
            df = df.sort_values('Date').reset_index(drop=True)
            
            # 移動平均を計算
            df['sma'] = df['Close'].rolling(window=period).mean()
            
            # 標準偏差を計算
            df['std'] = df['Close'].rolling(window=period).std()
            
            # ボリンジャーバンドを計算
            df['upper_band'] = df['sma'] + (df['std'] * std_dev)
            df['lower_band'] = df['sma'] - (df['std'] * std_dev)
            
            # NaNを除去
            df_result = df.dropna(subset=['sma', 'upper_band', 'lower_band'])
            
            # レスポンス形式に変換
            data = []
            for _, row in df_result.iterrows():
                data.append({
                    'date': Utils.unix_to_datestr(row['Date']) if isinstance(row['Date'], (int, float)) else str(row['Date']),
                    'value': {
                        'middle': float(row['sma']),
                        'upper': float(row['upper_band']),
                        'lower': float(row['lower_band'])
                    }
                })
            
            return {
                'ticker': ticker_base,
                'indicator': 'bollinger',
                'data': data
            }
            
        except Exception as e:
            self.log.error(f"ボリンジャーバンド計算エラー: {e}")
            return {'error': f'Calculation failed: {str(e)}'}
