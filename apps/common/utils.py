import re
import django
import pandas as pd
from apps.common.app_initializer import DjangoAppInitializer as Initializer
from typing import Any, List, Union

class Utils:
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

    @staticmethod
    def ensure_list(x: Union[Any, List[Any]]) -> List[Any]:
        """
        単一の値をリストに変換する。すでにリストならそのまま返す。
        """
        Initializer.get_logger().info("Ensuring list")
        return x if isinstance(x, list) else [x]


    @staticmethod
    def validate_interval(interval: str, allowed: List[str] = ["1d", "1wk", "1mo"]) -> None:
        """
        指定されたintervalが許可された値の中にあるか検証する。
        """
        if interval not in allowed:
            Initializer.get_logger().error(f"Invalid interval: {interval}. Allowed: {allowed}")
            raise ValueError(f"Invalid interval: {interval}. Allowed: {allowed}")

    @staticmethod
    def flatten_multiindex(df: pd.DataFrame) -> pd.DataFrame:
        """
        DataFrameのカラムがMultiIndexの場合、最初の階層だけを使って1層化する。
        """
        if isinstance(df.columns, pd.MultiIndex):
            Initializer.get_logger().info("Flattening MultiIndex columns")
            df.columns = df.columns.get_level_values(0)
        return df


    @staticmethod
    def is_valid_date(date_str: str, fmt: str = "%Y-%m-%d") -> bool:
        """
        文字列が指定された日付フォーマットに従っているか判定する。
        """
        try:
            pd.to_datetime(date_str, format=fmt)
            return True
        except ValueError:
            return False

    @staticmethod
    def safe_filename_component(name: str) -> str:
        """
        ファイル名として安全に使えるように、文字列から記号や特殊文字を除去し、
        半角・全角スペース、ピリオド、中黒などをアンダースコアに変換する。

        Parameters:
        - name: 元の企業名などの文字列

        Returns:
        - str: ファイル名に安全に使用できる形式の文字列
        """
        # 改行、スラッシュ、をアンダースコアに変換
        name = name.replace("\n", "_").replace("/", "_")

        # , を - に変換
        name = name.replace(",", "-")

        # 不正な記号を除外（英数字、スペース、アンダースコア、&、ハイフンのみ許可）
        name = re.sub(r"[^\w\s\-,.&・]", "", name)

        # 半角スペース、全角スペース、ピリオド、中黒などをアンダースコアに変換
        name = name.replace(" ", "-").replace("　", "-").replace(".", "-").replace("・", "-")


        # 連続アンダースコアを1つに統合（例: __ → _）
        name = re.sub(r"_+", "_", name)

        # 前後のアンダースコアを除去
        return name.strip("_")

    @staticmethod
    def sanitize_ticker_for_filename(ticker: str) -> str:
        # .+アルファベット（例: .T, .NS）を末尾から除去
        ticker = re.sub(r"\.[A-Za-z]+$", "", ticker)

        # 念のためその他の記号も除去（保険）
        ticker = re.sub(r"[^\w]", "", ticker)

        return ticker


    @staticmethod
    def normalize_for_search(name: str) -> str:
        # アルファベット、数字、日本語だけ残して、小文字に統一
        name = re.sub(r"[^\w\u3000-\u30FF\u4E00-\u9FFF]", "", name)
        return name.lower()

    @staticmethod
    def unix_to_datestr(series: pd.Series) -> pd.Series:
        """
        UNIXタイムスタンプを日付文字列に変換する。
        """
        return pd.to_datetime(series, unit='ms').dt.strftime('%Y/%m/%d')
    
    @staticmethod
    def squash_delimiters(name: str, delimiters: List[str] = ["-", "_"]) -> str:
        """
        指定したデリミタ（区切り文字）で文字列を分割し、全て結合して1語にする。

        Parameters:
        - name: 元の文字列
        - delimiters: 区切りに使う文字列のリスト（例: ["-", "_"]）

        Returns:
        - str: 区切り記号を除去して全て結合した文字列
        """
        # デリミタでsplit → join
        if delimiters:
            pattern = '|'.join(map(re.escape, delimiters))
            parts = re.split(pattern, name)
            return '　'.join(parts)
        else:
            return name
