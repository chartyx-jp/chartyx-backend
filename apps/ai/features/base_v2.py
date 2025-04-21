import numpy as np
from apps.ai.features.base import FeatureGeneratorBase
import pandas as pd
from apps.common.app_initializer import DjangoAppInitializer

class BasicFeatureGeneratorV2(FeatureGeneratorBase, DjangoAppInitializer):
    """
    特徴量生成器（バージョン2）
    より多くのテクニカル指標・ファンダメンタル情報を含んだ高度な特徴量群を追加。
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        df = df[df["Open"].notna() & (df["Open"] != 0)]

        df["Date"] = pd.to_datetime(df["Date"])
        df.sort_values("Date", inplace=True)

        # 基本価格系指標
        df["Return"] = df["Close"].pct_change(fill_method=None)
        df["LogReturn"] = np.log(df["Close"] / df["Close"].shift(1))
        df["MA_5"] = df["Close"].rolling(5).mean()
        df["MA_20"] = df["Close"].rolling(20).mean()
        df["MA_50"] = df["Close"].rolling(50).mean()
        df["MA_200"] = df["Close"].rolling(200).mean()
        df["FiftyTwoWeekLow"] = df["Close"].rolling(252).min()
        df["FiftyTwoWeekHigh"] = df["Close"].rolling(252).max()
        df["Volatility_5"] = df["Close"].rolling(5).std()
        df["Volatility_20"] = df["Close"].rolling(20).std()

        # 出来高平均系
        df["AverageVolume10D"] = df["Volume"].rolling(10).mean()
        df["AverageVolume3M"] = df["Volume"].rolling(63).mean()

        # ボリンジャーバンド
        ma20 = df["MA_20"]
        std20 = df["Close"].rolling(20).std()
        df["BB_Upper"] = ma20 + 2 * std20
        df["BB_Lower"] = ma20 - 2 * std20
        df["BB_Width"] = df["BB_Upper"] - df["BB_Lower"]

        # 出来高系
        df["Volume_Ratio"] = df["Volume"] / df["Volume"].rolling(5).mean()
        df["Vol_Surge_5"] = (df["Volume_Ratio"] > 1.5).astype(int)
        df["Volume_Change_1D"] = df["Volume"].pct_change(fill_method=None)

        # RSI
        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss
        df["RSI_14"] = 100 - (100 / (1 + rs))
        df["RSI_Trend"] = df["RSI_14"] - df["RSI_14"].shift(3)
        df["RSI_Over70"] = (df["RSI_14"] > 70).astype(int)
        df["RSI_Over70_Streak"] = df["RSI_Over70"] * (
            df["RSI_Over70"].groupby((df["RSI_Over70"] != df["RSI_Over70"].shift()).cumsum()).cumcount() + 1
        )

        # MACD
        ema12 = df["Close"].ewm(span=12, adjust=False).mean()
        ema26 = df["Close"].ewm(span=26, adjust=False).mean()
        df["MACD"] = ema12 - ema26
        df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
        df["MACD_Above0"] = (df["MACD"] > 0).astype(int)
        df["MACD_Above_0_Streak"] = df["MACD_Above0"] * (
            df["MACD_Above0"].groupby((df["MACD_Above0"] != df["MACD_Above0"].shift()).cumsum()).cumcount() + 1
        )

        # ローソク足・ヒゲ系
        df["DailyRange"] = df["High"] - df["Low"]
        df["CandleBody"] = (df["Close"] - df["Open"]).abs()
        df["UpperShadow"] = df["High"] - df[["Open", "Close"]].max(axis=1)
        df["LowerShadow"] = df[["Open", "Close"]].min(axis=1) - df["Low"]
        df["GapUpDown"] = df["Open"] - df["Close"].shift(1)

        # トレンド指標
        df["Close_Trend_5"] = df["Close"] - df["Close"].shift(5)
        df["Momentum_10"] = df["Close"] - df["Close"].shift(10)
        df["Momentum_20"] = df["Close"] - df["Close"].shift(20)
        df["MA_5_Slope"] = df["MA_5"] - df["MA_5"].shift(1)
        df["MA_20_Slope"] = df["MA_20"] - df["MA_20"].shift(1)
        df["MA5_to_MA20"] = df["MA_5"] / df["MA_20"]
        df["Close_to_MA5"] = df["Close"] / df["MA_5"]
        df["Close_to_MA20"] = df["Close"] / df["MA_20"]

        # 日付特徴量
        df["Year"] = df["Date"].dt.year
        df["Month"] = df["Date"].dt.month
        df["DayOfWeek"] = df["Date"].dt.dayofweek

        # ターゲット
        df["Target"] = df["Close"].shift(-1)


        return df

    @staticmethod
    def split(df: pd.DataFrame):
        df = df.copy()
        df = df.dropna(subset=["Target"])

        X = df.drop(columns=["Date", "Target"], errors="ignore")

        #  inf / -inf を NaN に変換してから dropna
        X.replace([np.inf, -np.inf], np.nan, inplace=True)
        X.dropna(inplace=True)

        y = df.loc[X.index, "Target"]
        return X, y
