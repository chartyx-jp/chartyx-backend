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
        """
        DataFrameから予測を行う。予測対象の特徴量は、split_features_for_predictionメソッドで抽出すること。
        """

        if isinstance(df, pd.Series):
            df = pd.DataFrame([df])

        if df is None or df.empty:
            raise ValueError("予測対象の特徴量が空です")

        if df.shape[0] != 1:
            raise ValueError("予測には1行のみを指定してください")

        x = self.split_features_for_prediction(df)
        # if x.isnull().values.any():
        #     raise ValueError("欠損値が含まれています。予測前に処理してください。")

        try:
            dmatrix = xgb.DMatrix(x)
            return float(self.booster.predict(dmatrix)[0])
        except Exception as e:
            raise RuntimeError(f"予測時にエラーが発生しました: {e}")
        

    @staticmethod
    def split_features_for_prediction(df: pd.DataFrame) -> pd.DataFrame:
        """
        推論用に特徴量のみを抽出する。欠損チェックは予測側で行う。
        """
        df = df.copy()
        X = df.drop(columns=["Date", "Target"], errors="ignore")
        return X