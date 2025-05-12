from apps.ai.ai_models.base_booster import BaseBoosterModel
from apps.common.app_initializer import DjangoAppInitializer
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
import pandas as pd
import os
import xgboost as xgb


class StockAITrainer(DjangoAppInitializer):
    def __init__(self, model: BaseBoosterModel, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.__model = model
        self.params = {
            "objective": "reg:squarederror",
            "tree_method": "hist",
            "device": "cuda",
            "eval_metric": "mae",
        }

    def train_incrementally(self, X, y):
        dtrain = xgb.DMatrix(X, label=y)

        booster = None
        if os.path.exists(self.__model.model_path):
            self.__model.load_model()
            booster = self.__model.booster
            self.logger.info("既存モデルを読み込みました")
        else:
            self.logger.info("新規モデルで学習を開始します")

        booster = xgb.train(
            self.params,
            dtrain,
            num_boost_round=100,
            xgb_model=booster if booster is not None else None
        )

        self.__model._BaseBoosterModel__booster = booster  # 内部に保持する（保存に使う）

    def evaluate(self, X, y):
        booster = self.__model.booster
        dval = xgb.DMatrix(X)
        preds = booster.predict(dval)
        mae = mean_absolute_error(y, preds)
        self.logger.info(f"バッチ評価: MAE={mae:.3f}")
        return mae

    def save_model(self):
        self.__model.save_model()
