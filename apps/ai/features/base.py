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
