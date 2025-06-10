# apps/common/initializer.py
import os
import django
import logging
from typing import Any ,NoReturn

class DjangoAppInitializer:
    # クラスレベルのロガーインスタンスを初期化
    _logger: logging.Logger = logging.getLogger("apps")

    def __init__(self, *args: Any, **kwargs: Any) -> NoReturn:
        """
        DjangoAppInitializer クラスのコンストラクタ。
        現在は特別な初期化ロジックは持ちません。
        """
        super().__init__(*args, **kwargs) 
        pass # 現状では何もしないのでpass

    @staticmethod
    def setup_django(settings_module: str = "config.settings") -> None:
        """
        Djangoプロジェクトをスクリプトから初期化します。
        DJANGO_SETTINGS_MODULE 環境変数を設定し、django.setup() を呼び出します。

        Args:
            settings_module (str): Djangoの設定モジュールへのパス (例: "config.settings")。
            デフォルトは "config.settings" です。
        """
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)
        django.setup()
        # ロガーはクラスメソッドで取得するのが適切
        DjangoAppInitializer.get_logger().info(f"Django setup complete using settings: {settings_module}")

    @property
    def log(self) -> logging.Logger:
        """
        このインスタンスに関連付けられたロガーを取得します。

        Returns:
            logging.Logger: ロガーインスタンス。
        """
        return self._logger

    @log.setter
    def log(self, value: logging.Logger) -> None:
        """
        このインスタンスに関連付けられたロガーを設定します。

        Args:
            value (logging.Logger): 設定するロガーインスタンス。
        """
        self._logger = value
    
    @classmethod
    def get_logger(cls) -> logging.Logger:
        """
        クラスレベルのロガーインスタンスを取得します。
        このメソッドは、インスタンス化せずにロガーにアクセスする際に推奨されます。

        Returns:
            logging.Logger: クラスレベルのロガーインスタンス。
        """
        return cls._logger