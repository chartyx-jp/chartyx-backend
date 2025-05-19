import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'MS Gothic' 

import xgboost as xgb
import shap
import pandas as pd
import numpy as np
from apps.common.utils import Utils
from pathlib import Path
from operator import itemgetter
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score
from apps.common.app_initializer import DjangoAppInitializer
from apps.ai.ai_models.base_booster import BaseBoosterModel
from django.conf import settings

#デコレーター
def auto_save_plot(model_name: str = None):
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            result = func(self, *args, **kwargs)

            # 関数内で設定された self._plot_name を取得
            self.log.info("decorator: auto_save_plot")
            plot_name = getattr(self, "_plot_name", None)
            if plot_name:
                self.save_plot(plot_name=plot_name, model_name=model_name)
                plt.show()

            else:
                self.log.warning("plot_name が指定されていないため、保存をスキップしました")

            return result
        return wrapper
    return decorator



class BoosterEvaluatorV2(DjangoAppInitializer):
    """
    XGBoost Booster形式のモデル評価クラス。
    - BaseBoosterModel を受け取り、特徴量重要度分析や予測評価を行う。
    """

    def __init__(self, model: BaseBoosterModel, group_label: str = "", ticker_name: str = "", *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.__model = model
        self.__booster = self.__model.booster
        self.group_label = group_label  # e.g., "small", "medium", "large"
        self.ticker_name = ticker_name  # e.g., "トヨタ自動車"
        self._plot_name = None


    def print_feature_importance(self, top_n: int = 20):
        score = self.__booster.get_score(importance_type='gain')
        sorted_items = sorted(score.items(), key=lambda x: x[1], reverse=True)

        self.log.info(f"[特徴量重要度TOP{top_n}（gain）] for {self.group_label}/{self.ticker_name}")
        for feature, importance in sorted_items[:top_n]:
            self.log.info(f"{feature}: {importance:.4f}")

    @auto_save_plot()
    def plot_feature_importance(self, top_n: int = 20):
        score = self.__booster.get_score(importance_type='gain')
        sorted_items = sorted(score.items(), key=lambda x: x[1], reverse=True)[:top_n]
        self._plot_name = f"Feature Importance (gain)\n{self.__model.model_name}"


        features = [f for f, _ in sorted_items]
        importances = [s for _, s in sorted_items]


        plt.figure(figsize=(16, 9))
        plt.barh(features[::-1], importances[::-1])
        plt.title(self._plot_name)
        plt.xlabel("Gain")
        plt.tight_layout()
        # plt.show()
        # self.save_plot(self._plot_name)

    @auto_save_plot()
    def plot_prediction_vs_actual(self, y_true: pd.Series, y_pred: pd.Series):

        self._plot_name = f"Predicted vs Actual\n{self.group_label}/{self.ticker_name}"

        plt.figure(figsize=(16, 9))
        plt.scatter(y_true, y_pred, alpha=0.5)

        # 軸範囲を固定（例: -0.1〜0.1 に拡張）
        min_val = -0.1
        max_val = 0.1
        plt.xlim(min_val, max_val)
        plt.ylim(min_val, max_val)

        # 軸の補助線（対角線）
        plt.plot([min_val, max_val], [min_val, max_val], 'r--')

        # メモリを0.01間隔で細かく
        ticks = np.arange(min_val, max_val + 0.001, 0.01)
        plt.xticks(ticks)
        plt.yticks(ticks)

        # グリッドも細かく出す
        plt.grid(True, which='both', linestyle=':', linewidth=0.5, alpha=0.5)

        plt.xlabel("Actual")
        plt.ylabel("Predicted")
        plt.title(self._plot_name)
        plt.tight_layout()
        # plt.show()
        # self.save_plot(self._plot_name)


    @auto_save_plot()
    def plot_error_histogram(self, y_true: pd.Series, y_pred: pd.Series):
        errors = y_pred - y_true
        self._plot_name = f"Prediction Error Histogram\n{self.group_label}/{self.ticker_name}"

        plt.figure(figsize=(16,9))

        # 可変bin数
        bins = min(len(errors) // 5, 50)
        plt.hist(errors, bins=bins, color='skyblue', edgecolor='black')

        # ゼロライン
        plt.axvline(0, color='red', linestyle='--', linewidth=1)

        # 平均誤差ライン
        mean_error = errors.mean()
        plt.axvline(mean_error, color='orange', linestyle='--', linewidth=1)
        plt.text(mean_error, plt.ylim()[1]*0.9, f"mean={mean_error:.4f}", color='orange')

        # 軸設定（オプション）
        plt.xlim(-0.1, 0.1)
        plt.xticks(np.arange(-0.1, 0.11, 0.01))
        plt.grid(True, axis='x', linestyle=':', alpha=0.4)

        plt.title(self._plot_name)
        plt.xlabel("Prediction Error")
        plt.ylabel("Frequency")
        plt.tight_layout()
        # plt.show()
        # self.save_plot(self._plot_name)


    @auto_save_plot()
    def plot_shap_summary(self, X: pd.DataFrame):
        try:
            self._plot_name = f"SHAP Summary\n{self.group_label}/{self.ticker_name}"
            explainer = shap.TreeExplainer(self.__booster)
            shap_values = explainer.shap_values(X)
            plt.figure(figsize=(16, 9))  # 横長の図を準備
            shap.summary_plot(shap_values, X,show=False)
            plt.title(self._plot_name)
            plt.tight_layout()

        except Exception as e:
            self.log.error(f"SHAPプロット中にエラーが発生しました: {e}")

    def evaluate_predictions(self, X: pd.DataFrame, y_true: pd.Series):
        try:
            dmatrix = xgb.DMatrix(X)
            y_pred = self.__booster.predict(dmatrix)

            self.plot_prediction_vs_actual(y_true, y_pred)
            self.plot_error_histogram(y_true, y_pred)
            mae = mean_absolute_error(y_true, y_pred)
            rmse = root_mean_squared_error(y_true, y_pred)
            mape = self.safe_mape(y_true, y_pred)
            r2 = r2_score(y_true, y_pred)

            return {
                "mae": mae,
                "rmse": rmse,
                "r2": r2,
                "mape": mape}
        except Exception as e:
            self.log.error(f"予測評価中にエラーが発生しました: {e}")
            return None

    def safe_mape(self, y_true, y_pred):
        mask = y_true != 0
        return (abs((y_true[mask] - y_pred[mask]) / y_true[mask])).mean() * 100

    def evaluate(self, X: pd.DataFrame, y: pd.Series):
        if X.empty or y.empty:
            self.log.warning("評価対象データが空のため、スキップします。")
            return

        self.plot_feature_importance()
        self.plot_shap_summary(X)
        results = self.evaluate_predictions(X, y)
        if results:
            mae, rmse, mape, r2 = itemgetter("mae", "rmse", "mape", "r2")(results)
            self.log.info(f"[評価結果] {self.group_label}/{self.ticker_name} → MAE: {mae:.2f}, RMSE: {rmse:.2f}, MAPE: {mape:.2f}%, R²: {r2:.4f}")
            return results

    def save_to_excel(self, model_name: str, metrics: dict, path: str = f"{settings.LOG_DIR}/evaluation_log.xlsx"):
        from datetime import datetime
        import os

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = {
            "timestamp": now,
            "model": model_name,
            "group": self.group_label,
            "ticker": self.ticker_name,
            **metrics
        }
        new_df = pd.DataFrame([row])


        if os.path.exists(path):
            existing = pd.read_excel(path)
            df = pd.concat([existing, new_df], ignore_index=True)
        else:
            df = new_df

        df.to_excel(path, index=False)

    def save_plot(self, plot_name: str, model_name: str = None):
        """
        モデル名とプロット名をもとに、グラフ画像をファイル保存する。
        保存先: settings.RESEARCH_DATA_DIR / model_name / safe_plot.png
        """
        model_dir = model_name if model_name else self.__model.model_name
        dir_path = Path(settings.RESEARCH_DATA_DIR) / model_dir
        dir_path.mkdir(parents=True, exist_ok=True)

        safe_plot = Utils.safe_filename_component(plot_name)
        full_path = dir_path / safe_plot
        plt.savefig(full_path, dpi=300, bbox_inches='tight')

        self.log.info(f"[保存完了] プロット保存: {full_path}")
