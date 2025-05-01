from typing import Dict
import pandas as pd
import numpy as np
import xgboost as xgb
from apps.ai.ai_models.base_booster import BaseBoosterModel
from  apps.ai.features.base_v2 import BasicFeatureGeneratorV2


class StockAIBoosterPredictor(BaseBoosterModel):
    def __init__(self, model_name: str, *args, **kwargs):
        self.__generator = BasicFeatureGeneratorV2()
        super().__init__(model_name, *args, **kwargs)
        self.load_model()

    def predict_from_df(self, df: pd.DataFrame) -> float:
        x = self.split_features_for_prediction(df)
        if x.empty:
            self.log.warning("予測不可: 特徴量が空")
            return float("nan")
        dmatrix = xgb.DMatrix(x)
        pred = self.booster.predict(dmatrix)[0]
        return pred

    @staticmethod
    def split_features_for_prediction(df: pd.DataFrame) -> pd.DataFrame:
        """
        推論用に特徴量のみを抽出する。欠損チェックは予測側で行う。
        """
        df = df.copy()
        X = df.drop(columns=["Date", "Target"], errors="ignore")
        return X