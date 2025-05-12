# apps/ai_models/evaluators/booster_evaluator.py

import matplotlib.pyplot as plt
import xgboost as xgb
import shap
import pandas as pd
import numpy as np
from operator import itemgetter
from sklearn.metrics import mean_absolute_error, root_mean_squared_error,r2_score
from apps.common.app_initializer import DjangoAppInitializer
from apps.ai.ai_models.base_booster import BaseBoosterModel


class BoosterEvaluator(DjangoAppInitializer):
    """
    XGBoost Booster形式のモデル評価クラス。
    - BaseBoosterModel を受け取り、特徴量重要度分析や予測評価を行う。
    """

    def __init__(self, model: BaseBoosterModel, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.__model = model
        self.__booster = self.__model.booster

    def print_feature_importance(self, top_n: int = 20):
        """
        特徴量重要度を出力（Gainベース）。
        """
        score = self.__booster.get_score(importance_type='gain')
        sorted_items = sorted(score.items(), key=lambda x: x[1], reverse=True)

        self.log.info(f"[特徴量重要度TOP{top_n}（gain）]")
        for feature, importance in sorted_items[:top_n]:
            self.log.info(f"{feature}: {importance:.4f}")

    def plot_feature_importance(self, top_n: int = 20):
        """
        特徴量重要度を棒グラフで可視化（Gainベース）。
        """
        score = self.__booster.get_score(importance_type='gain')
        sorted_items = sorted(score.items(), key=lambda x: x[1], reverse=True)[:top_n]

        features = [f for f, _ in sorted_items]
        importances = [s for _, s in sorted_items]

        plt.figure(figsize=(10, 6))
        plt.barh(features[::-1], importances[::-1])
        plt.title("Feature Importance (gain)")
        plt.xlabel("Gain")
        plt.tight_layout()
        plt.show()
    
    def plot_prediction_vs_actual(self, y_true: pd.Series, y_pred: pd.Series):
        """
        実測値と予測値の散布図を表示。
        """
        plt.figure(figsize=(6, 6))
        plt.scatter(y_true, y_pred, alpha=0.5)
        plt.plot([y_true.min(), y_true.max()], [y_true.min(), y_true.max()], 'r--')
        plt.xlabel("Actual")
        plt.ylabel("Predicted")
        plt.title("Predicted vs Actual")
        plt.tight_layout()
        plt.show()


    def plot_error_histogram(self, y_true: pd.Series, y_pred: pd.Series):
        """
        誤差分布（予測値 - 実測値）のヒストグラムを表示。
        """
        errors = y_pred - y_true
        plt.figure(figsize=(8, 4))
        plt.hist(errors, bins=30, color='skyblue', edgecolor='black')
        plt.title("Prediction Error Distribution")
        plt.xlabel("Prediction Error")
        plt.ylabel("Frequency")
        plt.tight_layout()
        plt.show()



    def plot_shap_summary(self, X: pd.DataFrame):
        """
        SHAP値を用いた特徴量の重要度の可視化。
        Xは学習時と同じ特徴量構造を持つDataFrameを渡してください。
        """
        try:
            explainer = shap.TreeExplainer(self.__booster)
            shap_values = explainer.shap_values(X)
            shap.summary_plot(shap_values, X)
            plt.tight_layout()
        except Exception as e:
            self.log.error(f"SHAPプロット中にエラーが発生しました: {e}")

    def evaluate_predictions(self, X: pd.DataFrame, y_true: pd.Series):
        """
        予測結果の精度を評価（MAE, RMSE）。
        Xは学習時と同一の特徴量構造・順序である必要があります。
        """
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
            return None, None
    
    def safe_mape(self, y_true, y_pred):
        mask = y_true != 0
        return (abs((y_true[mask] - y_pred[mask]) / y_true[mask])).mean() * 100

        
    def evaluate(self, X: pd.DataFrame, y: pd.Series):
        if X.empty or y.empty:
            self.log.warning("評価対象データが空のため、スキップします。")
            return

        # self.print_feature_importance()
        self.plot_feature_importance()
        self.plot_shap_summary(X)
        mae, rmse, mape, r2 = itemgetter("mae", "rmse", "mape", "r2")(self.evaluate_predictions(X, y))
        self.log.info(f"MAE: {mae:.2f}, RMSE: {rmse:.2f}, MAPE: {mape:.2f}%, R²: {r2:.4f}")

