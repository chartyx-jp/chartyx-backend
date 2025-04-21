# apps/common/initializer.py
import os
import django
import logging

class DjangoAppInitializer:
    _logger  =  logging.getLogger("apps")
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)


    @staticmethod
    def setup_django(settings_module: str = "config.settings") -> None:
        """
        Djangoプロジェクトをスクリプトから初期化する。
        """
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)
        django.setup()
        DjangoAppInitializer.get_logger().info("Django setup complete")


    @property
    def log(self):
        return self._logger

    @log.setter
    def logger(self, value: logging.Logger):
        self._logger = value
    
    @classmethod
    def get_logger(cls) -> logging.Logger:
        return cls._logger
