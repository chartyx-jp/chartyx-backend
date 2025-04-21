# Google Driveのマウント
# from google.colab import drive
# drive.mount('/content/drive')


# ライブラリのインストール
# !pip install pyarrow scikit-learn pandas  xgboost --quiet

# 必要なライブラリのインポート
import os
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error
class ParquetHandler:
    def __init__(self, directory: str):
        self.directory = directory
        os.makedirs(self.directory, exist_ok=True)

    def load_batch(self, files: list) -> pd.DataFrame:
        dfs = []
        for f in files:
            try:
                df = pd.read_parquet(os.path.join(self.directory, f))
                dfs.append(df)
            except Exception as e:
                print(f"❌ 読み込み失敗: {f} - {e}")
        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    @staticmethod
    def split(df: pd.DataFrame):
        df = df.copy()
        df = df.dropna(subset=["Target"])

        X = df.drop(columns=["Date", "Target"], errors="ignore")

        #  inf / -inf を NaN に変換してから dropna
        X.replace([np.inf, -np.inf], np.nan, inplace=True)
        X.dropna(inplace=True)

        y = df.loc[X.index, "Target"]
        return X, y

class StockAITrainer:
    def __init__(self):
        self.booster = None
        self.params = {
            "objective": "reg:squarederror",
            "tree_method": "hist",
            "device": "cuda",  # CPUなら削除か変更
            "eval_metric": "mae",
        }

    def train_incrementally(self, X, y):
        dtrain = xgb.DMatrix(X, label=y)
        if self.booster is None:
            self.booster = xgb.train(self.params, dtrain, num_boost_round=100)
        else:
            self.booster = xgb.train(self.params, dtrain, num_boost_round=100, xgb_model=self.booster)

    def evaluate(self, X, y):
        dval = xgb.DMatrix(X)
        preds = self.booster.predict(dval)
        mae = mean_absolute_error(y, preds)
        print(f"📊 バッチ評価 MAE={mae:.4f}")
        return mae

    def save_model(self, path):
        self.booster.save_model(path)

# メイン実行部
if __name__ == "__main__":
    PROCESSED_DIR = "/content/drive/MyDrive/chartyx-ai-colab/processed_data"
    MODEL_SAVE_PATH = "/content/drive/MyDrive/chartyx-ai-colab/models/chartyx_v2.json"
    BATCH_SIZE = 500

    print("🚀 ParquetバッチによるAI訓練を開始...")

    parquet_handler = ParquetHandler(PROCESSED_DIR)
    trainer = StockAITrainer()

    files = [f for f in os.listdir(PROCESSED_DIR) if f.endswith(".parquet")]
    total_files = len(files)
    total_rows_loaded = 0
    total_rows_used = 0
    total_batches = (total_files + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, total_files, BATCH_SIZE):
        batch_files = files[i:i + BATCH_SIZE]
        print(f"\n📂 バッチ {i//BATCH_SIZE+1}/{total_batches}: {len(batch_files)}件読み込み中...")

        df_batch = parquet_handler.load_batch(batch_files)
        if df_batch.empty:
            print("⚠️ 空のバッチ（スキップ）")
            continue

        total_rows_loaded += len(df_batch)
        print(f"📊 データ件数: {len(df_batch):,} 行")

        X, y = parquet_handler.split(df_batch)
        print(f"🧠 学習対象: {len(X):,} 行（特徴量）, {len(y):,} 行（ターゲット）")

        if X.empty or y.empty:
            print("⚠️ 有効なデータなし（スキップ）")
            continue

        trainer.train_incrementally(X, y)
        trainer.evaluate(X, y)
        total_rows_used += len(X)

    trainer.save_model(MODEL_SAVE_PATH)
    print(f"\n✅ モデル保存完了: {MODEL_SAVE_PATH}")
    print(f"📈 全体で読み込んだ行数: {total_rows_loaded:,}")
    print(f"✅ 学習に使用した行数: {total_rows_used:,}")
