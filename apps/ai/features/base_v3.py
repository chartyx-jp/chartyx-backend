import numpy as np
from apps.stocks.services.yahoo_fetcher import ParquetHandler
from apps.ai.features.base import FeatureGeneratorBase
import pandas as pd
from apps.common.app_initializer import DjangoAppInitializer

from django.conf import settings


class BasicFeatureGeneratorV3(FeatureGeneratorBase, DjangoAppInitializer):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)



    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df[["Date", "Open", "High", "Low", "Close", "Volume"]].copy()
        df = df[df["Open"].notna() & (df["Open"] != 0)]

        df["Date"] = pd.to_datetime(df["Date"])
        df.sort_values("Date", inplace=True)

        # log価格とターゲット
        df["LogClose"] = np.log(df["Close"])
        df["Target"] = df["LogClose"].shift(-1) - df["LogClose"]

        # logベースのMAとボラティリティ
        for window in [5, 20, 50, 200]:
            df[f"LogMA_{window}"] = df["LogClose"].rolling(window).mean()
            df[f"LogVolatility_{window}"] = df["LogClose"].rolling(window).std()
            df[f"Price_to_LogMA_{window}"] = df["LogClose"] - df[f"LogMA_{window}"]

        # ボリンジャーバンド上・下・幅
        ma20 = df["LogMA_20"]
        std20 = df["LogClose"].rolling(20).std()
        df["LogBB_Upper"] = ma20 + 2 * std20
        df["LogBB_Lower"] = ma20 - 2 * std20
        df["LogBB_Width"] = df["LogBB_Upper"] - df["LogBB_Lower"]

        # 52週安値・高値（logスケール）
        df["Log52WeekLow"] = df["LogClose"].rolling(252).min()
        df["Log52WeekHigh"] = df["LogClose"].rolling(252).max()
        df["LogRange_to_High"] = df["Log52WeekHigh"] - df["LogClose"]
        df["LogRange_to_Low"] = df["LogClose"] - df["Log52WeekLow"]

        # 出来高系
        df["Volume_Change_1D"] = df["Volume"].pct_change(fill_method=None)
        df["Volume_Ratio"] = df["Volume"] / df["Volume"].rolling(5).mean().replace(0, np.nan)
        df["AverageVolume3M"] = df["Volume"].rolling(63).mean()
        df["Vol_Surge_5"] = (df["Volume_Ratio"] > 1.5).astype(int)
        df["Volume_to_AvgRatio"] = df["Volume"] / df["AverageVolume3M"]

        # RSI & ストリーク
        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        df["RSI_14"] = 100 - (100 / (1 + rs))
        df["RSI_Trend"] = df["RSI_14"] - df["RSI_14"].shift(3)
        df["RSI_Over70"] = (df["RSI_14"] > 70).astype(int)
        df["RSI_Over70_Streak"] = df["RSI_Over70"] * (
            df["RSI_Over70"].groupby((df["RSI_Over70"] != df["RSI_Over70"].shift()).cumsum()).cumcount() + 1
        )

        # MACD
        ema12 = df["LogClose"].ewm(span=12, adjust=False).mean()
        ema26 = df["LogClose"].ewm(span=26, adjust=False).mean()
        df["MACD"] = ema12 - ema26
        df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
        df["MACD_Above0"] = (df["MACD"] > 0).astype(int)
        df["MACD_Above_0_Streak"] = df["MACD_Above0"] * (
            df["MACD_Above0"].groupby((df["MACD_Above0"] != df["MACD_Above0"].shift()).cumsum()).cumcount() + 1
        )

        # トレンド系（log差分）
        for lag in [1, 3, 5, 10, 20]:
            df[f"LogReturn_{lag}"] = df["LogClose"] - df["LogClose"].shift(lag)

        # ローソク足系
        df["CandleBody"] = (df["Close"] - df["Open"]).abs()
        df["UpperShadow"] = df["High"] - df[["Open", "Close"]].max(axis=1)
        df["LowerShadow"] = df[["Open", "Close"]].min(axis=1) - df["Low"]
        df["GapUpDown"] = df["Open"] - df["Close"].shift(1)
        df["IsBullish"] = (df["Close"] > df["Open"]).astype(int)
        df["IsBearish"] = (df["Close"] < df["Open"]).astype(int)

        # 比率系
        df["Pct_Open_to_Close"] = (df["Close"] - df["Open"]) / df["Open"]
        df["Pct_High_to_Low"] = (df["High"] - df["Low"]) / df["Low"]
        df["Pct_Close_to_High"] = (df["High"] - df["Close"]) / df["Close"]
        df["Open_to_High"] = (df["High"] - df["Open"]) / df["Open"]
        df["Open_to_Low"] = (df["Open"] - df["Low"]) / df["Open"]
        df["Close_to_Open"] = (df["Close"] - df["Open"]) / df["Open"]
        df["Close_to_High"] = (df["High"] - df["Close"]) / df["High"]
        df["Close_to_Low"] = (df["Close"] - df["Low"]) / df["Low"]
        df["Range_Pct"] = (df["High"] - df["Low"]) / df["Open"]
        df["LogRange"] = np.log(df["High"]) - np.log(df["Low"])
        df["LogBody"] = np.log(df["Close"]) - np.log(df["Open"])

        # 時系列特徴量（循環）
        df["Month_sin"] = np.sin(2 * np.pi * df["Date"].dt.month / 12)
        df["Month_cos"] = np.cos(2 * np.pi * df["Date"].dt.month / 12)
        df["DOW_sin"] = np.sin(2 * np.pi * df["Date"].dt.dayofweek / 5)
        df["DOW_cos"] = np.cos(2 * np.pi * df["Date"].dt.dayofweek / 5)

        return df  

    @staticmethod
    def split(df: pd.DataFrame, remove_zero_target: bool = True):
        if isinstance(df, pd.Series):
            df = pd.DataFrame([df])

        df = df.copy()
        initial_len = len(df)

        # Target 欠損を除去
        df = df.dropna(subset=["Target"])
        after_target_len = len(df)
        print(f"{initial_len - after_target_len}行のTARGETに欠損値がありました")

        # Targetが0に極めて近いデータを除外（変動なしとして扱う）
        if remove_zero_target:
            threshold = 1e-4
            df = df[df["Target"].abs() > threshold]
            print(f"{after_target_len - len(df)}行のTARGETが閾値以下（±{threshold}）だったため除外しました")

        # 特徴量とターゲット分離（元の生データを除く）
        drop_cols = ["Date", "Target", "Open", "High", "Low", "Close", "Volume"]
        X = df.drop(columns=drop_cols, errors="ignore")

        # Inf除去 + NaN除去
        X.replace([np.inf, -np.inf], np.nan, inplace=True)
        inf_nan_rows = X.isna().any(axis=1).sum()
        X.dropna(inplace=True)
        print(f"{inf_nan_rows} 行のINFまたはNaNがありました　（DROP）")

        y = df.loc[X.index, "Target"]

        print(f"最終サンプル数: {len(X)} 行, {X.shape[1]} 特徴量")
        return X, y


    def get_week_of_month(self, date):
        first_day = date.replace(day=1)
        dom = date.day
        adjusted_dom = dom + first_day.weekday()  # 月曜起点（weekday=0）
        return int(np.ceil(adjusted_dom / 7.0))
    
