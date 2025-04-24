from apps.ai.models.base_model import BaseAIModel
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
import pandas as pd
import os
from apps.stocks.services.parquet_handler import ParquetHandler
from django.conf import settings
from typing import Tuple

class StockAITrainer(BaseAIModel):
    """
    AIモデルの学習・追学習を担うTrainerクラス。
    データ読み込み、GPU学習、追学習などを管理。
    """

    def __init__(self, data_dir: str = settings.PROCESSED_DATA_DIR):
        """
        初期化処理。

        Parameters:
        - data_dir (str): Parquetファイルの読み込み元ディレクトリ
        """
        super().__init__()
        self.__parquet_handler = ParquetHandler(read_directory=data_dir)

    def train_gpu_model(self, X: pd.DataFrame, y: pd.Series) -> XGBRegressor:
        """
        GPUを活用してXGBoostモデルの新規学習を実施。

        Parameters:
        - X (pd.DataFrame): 特徴量
        - y (pd.Series): 目的変数

        Returns:
        - XGBRegressor: 学習済みモデル
        """
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        model = XGBRegressor(
            tree_method='gpu_hist',
            gpu_id=0,
            n_estimators=100,
            random_state=42
        )

        model.fit(X_train, y_train)

        preds = model.predict(X_test)
        mae = mean_absolute_error(y_test, preds)
        self.log.info(f" GPUモデル学習完了 | MAE: {mae:.3f}")
        return model

    def continue_training(self, X_new: pd.DataFrame, y_new: pd.Series) -> XGBRegressor:
        """
        既存モデルに対して追学習を行う。
        モデルが存在しない場合は新規学習を行う。

        Parameters:
        - X_new (pd.DataFrame): 新しい特徴量
        - y_new (pd.Series): 新しい目的変数

        Returns:
        - XGBRegressor: 継続学習後のモデル
        """
        model_path = self.model_path

        if os.path.exists(model_path):
            model = XGBRegressor()
            model.load_model(model_path)
            model.fit(X_new, y_new, xgb_model=model)  # 継続学習
            self.log.info(" 既存モデルに対して追学習を実施")
        else:
            self.train_gpu_model(X=X_new,y=y_new)

        model.save_model(model_path)
        self.log.info(f" モデル保存完了: {model_path}")
        self.model = model
        return model

    @property
    def parquet(self) -> ParquetHandler:
        """
        ParquetHandler オブジェクトのアクセサ
        """
        return self.__parquet_handler
