from apps.common.app_initializer import DjangoAppInitializer as initializer
initializer.setup_django()

from django.conf import settings
import pandas as pd
from datetime import date
from apps.stocks.services.parquet_handler import ParquetHandler
from apps.ai.features.base_v4 import BasicFeatureGeneratorV4
from apps.ai.evaluators.booster_evaluator_v2 import BoosterEvaluatorV2
from apps.ai.ai_models.base_booster import BaseBoosterModel


TICKER_GROUPS = [
    {"small": {
        "5020.T": "ENEOS",
        "7201.T": "日産自動車",
        "8601.T": "大和証券G",
        "7011.T": "三菱重工業",
        "8002.T": "丸紅"
    }},
    {"medium": {
        "7203.T": "トヨタ自動車",
        "6758.T": "ソニーグループ",
        "8306.T": "三菱UFJ銀行",
        "7974.T": "任天堂",
        "7751.T": "キヤノン"
    }},
    {"large": {
        "6861.T": "キーエンス",
        "9983.T": "ファーストリテイリング",
        "8035.T": "東京エレクトロン",
        "4063.T": "信越化学工業",
        "6098.T": "リクルートHD"
    }}
]

MODELNAME = "chartyx_v5"

today = date.today().strftime("%Y-%m-%d")
handler = ParquetHandler(directory=settings.PROCESSED_DATA_DIR)
pro_handler = ParquetHandler()

# 特徴量生成器切り替え
GENERATOR = BasicFeatureGeneratorV4()


def test_file_copy():
    for group in TICKER_GROUPS:
        for label, tickers in group.items():
            for code, name in tickers.items():
                print(f"Copying {code} ({name}) - {label}")
                pro_handler.copy_tickerFile_to(target_dir=settings.ANALYTICS_DATA_DIR, ticker_base=code)

def load_model():
    model = BaseBoosterModel(MODELNAME)
    model.load_model()
    return model


def test_representative_each_group(generator):
    """
    各価格帯から1銘柄ずつ選び、100行で3回評価
    """
    print("=== Running: test_representative_each_group ===")
    model = load_model()

    for group in TICKER_GROUPS:
        for label, tickers in group.items():
            code, name = list(tickers.items())[0]  # 最初の1銘柄
            print(f"{code} ({name}) - {label}")
            df = handler.get_latest_row_by_ticker(code, n=100)
            X, y = generator.split(df, remove_zero_target=True)
            evaluator = BoosterEvaluatorV2(model, group_label=label, ticker_name=name)
            Xmetrics = evaluator.evaluate(X, y)
            evaluator.save_to_excel(model_name=MODELNAME, metrics=Xmetrics)


def test_all_five_in_each_group(generator):
    """
    各価格帯で5銘柄すべてを使い、3回一斉検証
    """
    print("=== Running: test_all_five_in_each_group ===")
    model = load_model()

    for group in TICKER_GROUPS:
        for label, tickers in group.items():
            X_all, y_all = [], []
            for code, name in tickers.items():
                df = handler.get_latest_row_by_ticker(code, n=25)
                X, y = generator.split(df, remove_zero_target=True)
                if not X.empty and not y.empty:
                    X_all.append(X)
                    y_all.append(y)
            if X_all and y_all:
                X = pd.concat(X_all)
                y = pd.concat(y_all)
                evaluator = BoosterEvaluatorV2(model, group_label=label, ticker_name="GroupAvg_" + label)
                Xmetrics = evaluator.evaluate(X, y)
                evaluator.save_to_excel(model_name=MODELNAME, metrics=Xmetrics)


def main():
    print("========== V3 (変換済データ) ==========")
    test_representative_each_group(GENERATOR)
    test_all_five_in_each_group(GENERATOR)
    print("=== 全評価完了 ===")


if __name__ == "__main__":
    main()
    # test_file_copy()
