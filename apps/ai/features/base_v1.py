# apps/ai/features/base_v1.py

import numpy as np
import pandas as pd
from apps.ai.features.base import FeatureGeneratorBase


class BasicFeatureGeneratorV1(FeatureGeneratorBase):
    """
    特徴量生成器（バージョン1）
    株価時系列データに対して基本的なテクニカル指標・日付特徴量を追加する。
    """

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        特徴量を追加したDataFrameを返す。

        Parameters:
        - df (pd.DataFrame): 元データ（"Date", "Open", "High", "Low", "Close" などを含む）

        Returns:
        - pd.DataFrame: 特徴量追加＆整形済みのデータ
        """
        df = df.copy()

        # 日付整形と並び替え
        df["Date"] = pd.to_datetime(df["Date"])
        df.sort_values("Date", inplace=True)

        # 基本的なテクニカル特徴量の追加
        df["Return"] = df["Close"].pct_change()  # 日次リターン
        df["LogReturn"] = np.log(df["Close"] / df["Close"].shift(1))  # 対数リターン
        df["MA_5"] = df["Close"].rolling(5).mean()  # 5日移動平均
        df["MA_20"] = df["Close"].rolling(20).mean()  # 20日移動平均
        df["Volatility_5"] = df["Close"].rolling(5).std()  # 5日標準偏差
        df["High_Low_Spread"] = df["High"] - df["Low"]  # 日中レンジ
        df["OC_Change"] = df["Close"] - df["Open"]  # 始値終値の差分

        # 日付由来の特徴量
        df["Year"] = df["Date"].dt.year
        df["Month"] = df["Date"].dt.month
        df["DayOfWeek"] = df["Date"].dt.dayofweek

        # 教師データ（翌日終値）
        df["Target"] = df["Close"].shift(-1)

        # 欠損除去（移動平均・シフト後）
        df.dropna(inplace=True)

        return df
    

    def split(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
        """
        特徴量と目的変数（ターゲット）を分離する。

        Parameters:
        - df: 特徴量を含むDataFrame（Target列含む）

        Returns:
        - X: 特徴量のみのDataFrame（Date, Targetを除外）
        - y: 目的変数（Target列）

        """
        df = df.copy()
        X = df.drop(columns=["Date", "Target"])
        y = df["Target"]
        return X, y