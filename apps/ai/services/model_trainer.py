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
