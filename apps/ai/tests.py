from apps.common.app_initializer import DjangoAppInitializer as initializer
initializer.setup_django()


import random
import pandas as pd
from datetime import date, timedelta
from apps.stocks.services.yahoo_fetcher import YahooFetcher
from apps.stocks.services.parquet_handler import ParquetHandler
from apps.ai.inference.booster_predictor import StockAIBoosterPredictor
from apps.ai.models import PredictionLog


# === 実行 ===
if __name__ == "__main__":
    pass
