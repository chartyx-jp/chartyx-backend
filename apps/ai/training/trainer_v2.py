from apps.ai.ai_models.base_model import BaseAIModel
from apps.common.app_initializer import DjangoAppInitializer
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
import pandas as pd
import os
import xgboost as xgb
from apps.stocks.services.parquet_handler import ParquetHandler
from typing import Tuple



class StockAITrainer(BaseAIModel,DjangoAppInitializer):
    def __init__(self, model_name: str, *args, **kwargs) -> None:
        super().__init__(model_name=model_name, *args, **kwargs)
        self.booster = None
        self.params = {
            "objective": "reg:squarederror",
            "tree_method": "hist",
            "device": "cuda",
            "eval_metric": "mae",
        }

    def train_incrementally(self, X, y):
        dtrain = xgb.DMatrix(X, label=y)
        if self.booster is None:
            if os.path.exists(self.model_path):
                self.booster = xgb.Booster()
                self.booster.load_model(self.model_path)
                self.log.info(" 既存モデルを読み込みました")
            else:
                self.log.info(" 新規モデルで学習を開始します")

        self.booster = xgb.train(
            self.params,
            dtrain,
            num_boost_round=100,
            xgb_model=self.booster if self.booster is not None else None
        )

    def evaluate(self, X, y):
        dval = xgb.DMatrix(X)
        preds = self.booster.predict(dval)
        mae = mean_absolute_error(y, preds)
        self.log.info(f"バッチ評価: MAE={mae:.3f}")
        return mae

    def save_model(self):
        if self.booster:
            self.booster.save_model(self.model_path)
            self.log.info(f" モデル保存完了: {self.model_path}")
