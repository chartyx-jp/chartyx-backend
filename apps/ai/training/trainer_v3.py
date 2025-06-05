from apps.ai.ai_models.base_booster import BaseBoosterModel
from apps.common.app_initializer import DjangoAppInitializer
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
import pandas as pd
import os
import xgboost as xgb


class StockAITrainer:
    def __init__(self):
        self.booster = None
        self.params = {
            "objective": "reg:squarederror",
            "tree_method": "hist",
            "device": "cuda",  # CPUなら削除か変更
            "eval_metric": "mae",
            "enable_categorical": True,   #カテゴリ変数使用可。
        }

    def train_incrementally(self, X, y):
        dtrain = xgb.DMatrix(X, label=y)
        if self.booster is None:
            self.booster = xgb.train(self.params, dtrain, num_boost_round=100)
        else:
            self.booster = xgb.train(self.params, dtrain, num_boost_round=100, xgb_model=self.booster)

    def evaluate(self, X, y):
        dval = xgb.DMatrix(X)
        preds = self.booster.predict(dval)
        print(pd.DataFrame({"pred": preds, "actual": y}).head(10))
        mae = mean_absolute_error(y, preds)
        print(f"📊 バッチ評価 MAE={mae:.4f}")
        return mae

    def save_model(self, path):
        self.booster.save_model(path)
