from django.apps import AppConfig
from pathlib import Path
from typing import Optional
from apps.stocks.services.parquet_handler import ParquetHandler

class StocksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.stocks'

    # グローバルに1つだけhandler持つ
    parquet_handler: Optional[ParquetHandler] = None  # ←型ヒントで宣言
    
    def ready(self):
        from django.conf import settings
        from apps.stocks.services.parquet_handler import ParquetHandler
        StocksConfig.parquet_handler = ParquetHandler(directory=settings.RAW_DATA_DIR)
