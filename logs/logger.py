import logging

class LogHelper:
    """
    ログ出力のヘルパークラス。
    - ロガーの取得を簡略化するためのメソッドを提供
    - ロガーのレベルはに設定settings.pyのLOGGINGに従う
    - ロガーのフォーマットはsettings.pyのLOGGINGに従う
    """
    @staticmethod
    def get_logger(context_or_name):
        if isinstance(context_or_name, str):
            logger_name = context_or_name
        elif hasattr(context_or_name, '__class__'):
            logger_name = context_or_name.__class__.__name__
        else:
            logger_name = str(context_or_name)  # fallback
        return logging.getLogger(logger_name)
