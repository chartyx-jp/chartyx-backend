import xgboost as xgb
from pathlib import Path
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
        self.__model_name:str = model_name
        self.__model_file:str = f"{model_name}.json"
        self.__model_path:Path = settings.MODEL_DIR / self.__model_file
        self.__booster: xgb.Booster | None = None


    @property
    def booster(self) -> xgb.Booster:
        if self.__booster is None:
            raise RuntimeError("Boosterがロードされていません")
        return self.__booster
    
    @property
    def model_path(self) -> str:
        return str(self.__model_path)
    
    @property
    def model_name(self) -> str:
        return self.__model_name

    def save_model(self) -> None:
        self.__model_path.parent.mkdir(parents=True, exist_ok=True)        
        self.booster.save_model(self.__model_path)
        self.logger.info(f"Boosterモデル保存完了: {self.__model_path}")

    def load_model(self) -> None:
        if not self.__model_path.exists():            
            raise FileNotFoundError(f"モデルが存在しません: {self.__model_path}")
        self.__booster = xgb.Booster()
        self.__booster.load_model(str(self.__model_path))
        self.logger.info(f"Boosterモデル読込完了: {self.__model_path}")

    @property
    def model_path(self) -> Path:
        return self.__model_path
