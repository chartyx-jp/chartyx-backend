import os
import sys
import re
import django
import pandas as pd
from typing import Any, List, Union

class Utils:
    @staticmethod
    def ensure_list(x: Union[Any, List[Any]]) -> List[Any]:
        """
        単一の値をリストに変換する。すでにリストならそのまま返す。
        """
        return x if isinstance(x, list) else [x]

    @staticmethod
    def validate_interval(interval: str, allowed: List[str] = ["1d", "1wk", "1mo"]) -> None:
        """
        指定されたintervalが許可された値の中にあるか検証する。
        """
        if interval not in allowed:
            raise ValueError(f"Invalid interval: {interval}. Allowed: {allowed}")

    @staticmethod
    def flatten_multiindex(df: pd.DataFrame) -> pd.DataFrame:
        """
        DataFrameのカラムがMultiIndexの場合、最初の階層だけを使って1層化する。
        """
        if isinstance(df.columns, pd.MultiIndex):
            print("Flattening MultiIndex columns")
            df.columns = df.columns.get_level_values(0)
        return df

    @staticmethod
    def setup_django(settings_module: str = "config.settings") -> None:
        """
        Djangoプロジェクトをスクリプトから初期化する。
        """
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)
        django.setup()
        print("Django setup complete")

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
        スペースやピリオドをアンダースコアに変換する。

        Parameters:
        - name: 元の企業名などの文字列

        Returns:
        - str: ファイル名に安全に使用できる形式の文字列
        """

        # 不正な記号を除外（英数字、スペース、アンダースコア、ハイフンのみ許可）
        name = re.sub(r"[^\w\s-]", "", name)

        # スペースとピリオドをアンダースコアに変換
        name = name.replace(" ", "_").replace(".", "_")

        # 連続アンダースコアを1つに統合（例: __ → _）
        name = re.sub(r"_+", "_", name)

        # 前後のアンダースコアを除去
        return name.strip("_")

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
            return ''.join(parts)
        else:
            return name
