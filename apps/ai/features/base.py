from abc import ABC, abstractmethod
import pandas as pd

class FeatureGeneratorBase(ABC):
    """
    特徴量生成器の基底クラス。
    """

    @abstractmethod
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        DataFrame に対して特徴量を生成する処理を定義する。

        Returns:
        - pd.DataFrame: 特徴量を追加し、整形済みのDataFrame
        """
        pass


    safe_feature = [
    'Ticker：100.0％',
    'open：99.8％',
    'high：99.8％',
    'low：99.8％',
    'close：99.8％',
    'volume：99.8％',
    'symbol：100.0％',
    'shortName：100.0％',
    'twoHundredDayAverage：100.0％',
    'fiftyTwoWeekLow：100.0％',
    'averageDailyVolume10Day：100.0％',
    'averageDailyVolume3Month：100.0％',
    'fiftyTwoWeekHigh：100.0％',
    'fiftyDayAverage：100.0％',
    'longName：96.1％',
    'trailingAnnualDividendRate：93.6％',
    'trailingAnnualDividendYield：93.6％',
    'marketCap：92.1％',
    'recommendationKey：90.2％',
    'sharesOutstanding：92.1％',
    'priceToBook：90.1％',
    'bookValue：90.1％'
    ]

#特徴量名 | 意味・内容
# Ticker | 銘柄コード（例: 7203.T トヨタ）
# open | その日の始値（取引開始時の価格）
# high | その日の高値（その日で一番高い価格）
# low | その日の安値（その日で一番低い価格）
# close | その日の終値（取引終了時の価格）
# volume | 出来高（その日の取引量）
# symbol | Tickerとほぼ同じ。ティッカーシンボル（コード）
# shortName | 銘柄の短縮名（例: "トヨタ自動車"）
# twoHundredDayAverage | 過去200営業日の平均株価（200日移動平均線）
# fiftyTwoWeekLow | 過去52週間（約1年）の最安値
# averageDailyVolume10Day | 過去10営業日の平均出来高
# averageDailyVolume3Month | 過去3か月（約60営業日）の平均出来高
# fiftyTwoWeekHigh | 過去52週間（約1年）の最高値
# fiftyDayAverage | 過去50営業日の平均株価（50日移動平均線）
# longName | 銘柄の正式名称（例: "トヨタ自動車株式会社"）
# trailingAnnualDividendRate | 過去1年の1株あたり配当金額（単位：通貨）
# trailingAnnualDividendYield | 過去1年の配当利回り（配当÷株価, ％表示）
# marketCap | 時価総額（株価 × 発行済株式数）
# recommendationKey | アナリストの推奨評価（例: "buy", "hold", "sell")
# sharesOutstanding | 発行済株式数（会社全体で発行している株数）
# priceToBook | PBR（株価純資産倍率、株価÷1株あたり純資産）
# bookValue | 1株あたり純資産（BPS）
