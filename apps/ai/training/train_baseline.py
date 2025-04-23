import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import os
from utils.utils import Utils
Utils.setup_django()

from django.conf import settings

# # データの読み込み（必要に応じてファイルパスを変更）
# df = pd.read_parquet("stock_data/raw_data/AAPL_1d_2023-01-01_to_2023-01-15.parquet")

# # 特徴量の作成
# df["return"] = (df["Close"] - df["Open"]) / df["Open"]  # 当日の変化率
# df["volatility"] = (df["High"] - df["Low"]) / df["Open"]  # 当日のボラティリティ
# df["volume_scaled"] = df["Volume"] / df["Volume"].rolling(5).mean()  # 出来高の移動平均比

# # ラベル（翌日の終値）
# df["target"] = df["Close"].shift(-1)

# # 欠損値の除去
# df.dropna(inplace=True)

# # 特徴量とラベルを分離
# features = ["return", "volatility", "volume_scaled"]
# X = df[features]
# y = df["target"]

# # データ分割（学習：テスト = 8:2）
# X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# # モデルの学習
# model = RandomForestRegressor(n_estimators=100, random_state=42)
# model.fit(X_train, y_train)

# # 予測と評価
# y_pred = model.predict(X_test)
# print("Mean Absolute Error:", mean_absolute_error(y_test, y_pred))
# print("Mean Squared Error:", mean_squared_error(y_test, y_pred))
# print("R2 Score:", r2_score(y_test, y_pred))

# # モデル保存
# os.makedirs("apps/ai/models", exist_ok=True)
# joblib.dump(model, "apps/ai/models/stock_price_regressor.pkl")
# print("✅ モデルを保存しました")


# import joblib
# import pandas as pd

# # モデルの読み込み
# model = joblib.load("apps/ai/models/stock_price_regressor.pkl")

# # テスト用のデータ（例として1行）
# test_data = pd.DataFrame([{
#     "return": 0.015,
#     "volatility": 0.03,
#     "volume_scaled": 1.2
# }])

# # 予測
# predicted_price = model.predict(test_data)
# print("予測された終値:", predicted_price[0])





def load_all_data(processed_dir: str) -> pd.DataFrame:
    all_dfs = []

    for filename in os.listdir(processed_dir):
        if filename.endswith("_complete.parquet"):
            path = os.path.join(processed_dir, filename)
            try:
                df = pd.read_parquet(path)
                all_dfs.append(df)
            except Exception as e:
                print(f"⚠ 読み込み失敗: {filename} - {e}")

    return pd.concat(all_dfs, ignore_index=True)

def split_features_targets(df: pd.DataFrame):
    X = df.drop(columns=["Date", "Target"])  # 日付とターゲット除外
    y = df["Target"]
    return X, y

def train_baseline_model(X, y):
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)

    print(f"✅ モデル学習完了 | MAE: {mae:.3f}")
    return model

if __name__ == "__main__":
    df = load_all_data(settings.PROCESSED_DATA_DIR)
    X, y = split_features_targets(df)
    model = train_baseline_model(X, y)
    joblib.dump(model, "apps/ai/models/stock_price_regressor.pkl")
