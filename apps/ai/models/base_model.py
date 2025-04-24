import os
import joblib
import logging
from logs.logger import LogHelper
from django.conf import settings


class BaseAIModel:
    """
    AIモデルの基底クラス。
    - モデルの保存・読み込み機能を提供
    - 共通ロガーをプロパティとして提供
    """

    def __init__(self, model_path: str = settings.MODEL_DIR) -> None:
        """
        初期化メソッド

        Parameters:
        - model_path (str): モデルの保存先／読込先パス
        """
        self.__model_path: str = model_path
        self.__model: object | None = None
        self.__logger: logging.Logger = LogHelper.get_logger(self)

    @property
    def model(self) -> object | None:
        """モデルオブジェクトへのアクセサ"""
        return self.__model

    @model.setter
    def model(self, model_obj: object) -> None:
        """モデルオブジェクトのセッター"""
        self.__model = model_obj

    def save_model(self) -> None:
        """モデルをファイルに保存"""
        os.makedirs(os.path.dirname(self.__model_path), exist_ok=True)
        joblib.dump(self.model, self.__model_path)
        self.log.info(f" モデル保存完了: {self.__model_path}")

    def load_model(self) -> None:
        """ファイルからモデルを読み込む"""
        if not os.path.exists(self.__model_path):
            raise FileNotFoundError(f" モデルファイルが存在しません: {self.__model_path}")
        self.model = joblib.load(self.__model_path)
        self.log.info(f" モデル読込完了: {self.__model_path}")

    @property
    def model_path(self) -> str:
        """モデルのパスを取得"""
        return self.__model_path

    @property
    def log(self) -> logging.Logger:
        """ロガーオブジェクトのアクセサ"""
        return self.__logger
