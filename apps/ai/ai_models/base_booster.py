import os
import xgboost as xgb
from django.conf import settings
from apps.common.app_initializer import DjangoAppInitializer

class BaseBoosterModel(DjangoAppInitializer):
    """
    XGBoost Booster形式モデルの基底クラス。
    - モデルの保存・読み込み機能を提供
    - 共通ロガー・モデルパスの管理を担う
    """

    def __init__(self, model_name: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._model_path = settings.MODEL_DIR / model_name
        self._booster: xgb.Booster | None = None


    @property
    def booster(self) -> xgb.Booster:
        if self._booster is None:
            raise RuntimeError("Boosterがロードされていません")
        return self._booster

    def save_model(self) -> None:
        os.makedirs(os.path.dirname(self._model_path), exist_ok=True)
        self.booster.save_model(str(self._model_path))
        self._logger.info(f"Boosterモデル保存完了: {self._model_path}")

    def load_model(self) -> None:
        if not os.path.exists(self._model_path):
            raise FileNotFoundError(f"モデルが存在しません: {self._model_path}")
        self._booster = xgb.Booster()
        self._booster.load_model(str(self._model_path))
        self._logger.info(f"Boosterモデル読込完了: {self._model_path}")

    @property
    def model_path(self) -> str:
        return str(self._model_path)
