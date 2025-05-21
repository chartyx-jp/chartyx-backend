import numpy as np
import pandas as pd
from apps.stocks.services.yahoo_fetcher import ParquetHandler
from apps.ai.features.base import FeatureGeneratorBase
from apps.common.app_initializer import DjangoAppInitializer
from django.conf import settings


class BasicFeatureGeneratorV4(FeatureGeneratorBase, DjangoAppInitializer):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.__read_handler = ParquetHandler(directory=settings.RAW_DATA_DIR/"japan", batch_size=20)
        self.__write_handler = ParquetHandler(directory=settings.PROCESSED_DATA_DIR, batch_size=20)



    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df[["Date", "Open", "High", "Low", "Close", "Volume"]].copy()
        df = df[df["Open"].notna() & (df["Close"] != 0)]

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

    def drop_unused_columns(self, df: pd.DataFrame,threshold:int = 1e-4) -> pd.DataFrame:
        """
        不整値を削除する。
        """
        if isinstance(df, pd.Series):
            df = pd.DataFrame([df])
        df = df.dropna(subset=["Target"])

        # Targetが0に極めて近いデータを除外（変動なしとして扱う）
        df = df[df["Target"].abs() > threshold]

        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.dropna(inplace=True)

        return df


    def get_week_of_month(self, date):
        first_day = date.replace(day=1)
        dom = date.day
        adjusted_dom = dom + first_day.weekday()  # 月曜起点（weekday=0）
        return int(np.ceil(adjusted_dom / 7.0))
    
    def plot_close_distribution(self, threshold: float = 1e-4):
        """
        Plot distribution of valid Close prices in ¥1000 price bins.
        """
        from collections import Counter
        import numpy as np
        import matplotlib.pyplot as plt

        counter = Counter()
        total_count = 0
        # price_bins = np.arange(-0.1, 0.1 + 0.01, 0.01)  # -10%〜+10%を1%刻みで LOG差分

        price_bins = np.arange(0, 100000, 1000)

        for df_transformed in self.__read_handler.load_each(suffix=".parquet"):
            df_transformed = self.transform(df_transformed)
            df_transformed = self.drop_unused_columns(df=df_transformed)
            # X,y = self.split(df_transformed, remove_zero_target=True)
            # valid_close = y

            valid_close = df_transformed[
                df_transformed["Close"] > 0
                # df_transformed["Target"].notna() &
                # (df_transformed["Target"].abs() != 0) &
                # (df_transformed["Close"] > 0)
            ]["Close"]

            bin_indices = np.digitize(valid_close, price_bins, right=False)
            for b in bin_indices:
                counter[b] += 1
            total_count += len(valid_close)

        # ラベルと割合作成（index error回避）
        labels = []
        percentages = []
        bin_counts = []  # ← 件数も記録する
        print(sorted(counter.keys()))
        for i in sorted(counter.keys()):
            if i < len(price_bins):
                label = f"{price_bins[i - 1]}–{price_bins[i]}"
            else:
                label = f"{price_bins[-1]}+"
            labels.append(label)
            
            count = counter[i]
            percentage = count / total_count * 100

            percentages.append(percentage)
            bin_counts.append(count)  # 件数保存

            # 件数と割合をログ出力
            print(f"{label}: {count}件 ({percentage:.4f}%)")
        print(f"全体件数{total_count}")

        # 描画
        plt.figure(figsize=(12, 5))

        # 棒グラフ（割合）
        bars = plt.bar(labels, percentages, label='Percentage by Price Range', color='skyblue', edgecolor='black')

        # 折れ線グラフ（滑らかに変化を見る）
        plt.plot(range(len(labels)), percentages, color='orange', marker='o', linestyle='-', linewidth=1.5, markersize=4, label='Trend Line')

        # X軸ラベル間引き（長すぎ防止）
        plt.xticks(
            ticks=np.arange(len(labels))[::2],
            labels=[labels[i] for i in range(len(labels))][::2],
            rotation=60,
            fontsize=8
        )

        plt.title("Distribution of Stocks by Price Range (per ¥1000)")
        plt.ylabel("Percentage (%)")
        plt.legend()
        plt.tight_layout()
        plt.show()


    def analyze_close_distribution(self, bins_within_iqr=4):
        import numpy as np
        import pandas as pd
        import matplotlib.pyplot as plt
        import seaborn as sns

        # すべてのClose価格を収集
        all_close = []
        for df in self.__read_handler.load_each(suffix=".parquet"):
            df = self.transform(df)
            valid = self.drop_unused_columns(df=df)
            all_close.extend(valid["Close"].dropna().tolist())

        # Series化 & 0以下除外
        close = pd.Series(all_close)
        close = close[close > 0]

        # 四分位数とIQR計算
        q1 = close.quantile(0.25)
        q3 = close.quantile(0.75)
        iqr = q3 - q1
        center = close[(close >= q1) & (close <= q3)]
        median = center.median()
        mean = center.mean()

        # bin定義（ヒストグラム区切り用）
        bin_edges = np.linspace(q1, q3, bins_within_iqr + 1)
        bin_labels = [f"{int(bin_edges[i])}-{int(bin_edges[i+1])}" for i in range(len(bin_edges) - 1)]
        bin_counts = pd.cut(center, bins=bin_edges, labels=bin_labels).value_counts().sort_index()

        # グラフ描画開始
        plt.figure(figsize=(12, 6))

        # 🔹 1. IQRヒストグラム
        plt.subplot(1, 2, 1)
        sns.histplot(center, bins=30, color="skyblue", edgecolor="black")

        # 線と凡例
        plt.axvline(q1, color='green', linestyle='--', label=f'Q1 (25%): {q1:.1f}')
        plt.axvline(median, color='orange', linestyle='-', label=f'Median (50%): {median:.1f}')
        plt.axvline(q3, color='red', linestyle='--', label=f'Q3 (75%): {q3:.1f}')
        plt.axvline(mean, color='purple', linestyle=':', label=f'Mean: {mean:.1f}')

        plt.title("Histogram of Close Prices (within IQR)")
        plt.xlabel("Close Price")
        plt.ylabel("Frequency")
        plt.legend()

        # 🔹 2. Boxplot（IQRのみで外れ値なし）
        plt.subplot(1, 2, 2)
        sns.boxplot(x=close, color="lightgreen")

        # Median注釈（boxの中央にラベル）
        plt.axvline(median, color='orange', linestyle='-', label=f'Median (50%)')
        plt.text(median, 0.05, "Median", ha='center', color='orange', transform=plt.gca().get_xaxis_transform())

        # 描画範囲を制限して「IQRの範囲を見せる」
        plt.xlim(q1 - iqr * 0.1, q3 + iqr * 0.1)  # 少し余白つける

        plt.title("Boxplot of Close Prices (within IQR)")
        plt.xlabel("Close Price")
        plt.legend()

        plt.tight_layout()
        plt.show()

        # テキストログ出力
        print("📦 IQR Stats")
        print(f"Q1: {q1:.2f}, Q3: {q3:.2f}, IQR: {iqr:.2f}")
        print(f"Median: {median:.2f}, Mean: {mean:.2f}")
        print("\n🔹 Bin Counts within IQR:")
        print(bin_counts)

if __name__ == "__main__":
    generator = BasicFeatureGeneratorV4()
    # generator.plot_close_distribution(threshold=1e-4)
    generator.analyze_close_distribution()

