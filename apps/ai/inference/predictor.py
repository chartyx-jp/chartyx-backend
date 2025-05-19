from apps.ai.ai_models.base_model import BaseAIModel
import pandas as pd
from typing import Dict

class StockAIPredictor(BaseAIModel):
    """
    学習済みモデルを用いて予測を行うクラス。
    - モデルは初期化時に自動でロードされる。
    - 単一レコードの入力特徴量に対して予測値を返す。
    """

    def __init__(self, model_name: str, *args, ** kwargs) -> None:
        """
        モデル予測器の初期化。
        自動的に保存済みモデルをロードする。
        """
        super().__init__(model_name=model_name,*args, **kwargs)
        self.load_model()

    def predict(self, input_features: Dict[str, float]) -> float:
        """
        単一の特徴量辞書に対して予測を実行。

        Parameters:
        - input_features (dict): 特徴量のキーと値の辞書

        Returns:
        - float: 予測されたターゲット値（例：翌日の終値）
        """
        df = pd.DataFrame([input_features])
        prediction = self.model.predict(df)[0]
        self.log.info(f" 予測値: {prediction:.3f} | 入力: {input_features}")
        return prediction
