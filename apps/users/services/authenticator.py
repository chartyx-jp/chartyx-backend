# apps/users/services/authenticator.py

import secrets
import string
import time
import logging
from typing import Optional, Dict, Any, Tuple

# Djangoのパスワードハッシュ化関数をインポート
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)

class Authenticator:
    """
    ユーザー認証、パスワードハッシュ化、OTP生成・検証、メール送信などの
    認証関連ロジックを管理するクラス。
    """
    OTP_EXPIRATION_SECONDS = 300 # OTPの有効期限（5分）

    # サインアップフローのOTP情報をセッションに保存する際の固定キー
    # このキーの下に、対象のメールアドレス、OTP、有効期限、検証済みフラグを辞書として保存します。
    SIGNUP_OTP_SESSION_KEY = 'signup_otp_data' 

    # ログインフローのOTP情報をセッションに保存する際の固定キー
    # こちらはユーザーID（またはメールアドレス）と紐付ける必要があるので、
    # 実際には member_id をキーの一部にするか、単一のキーで管理する方法を別途検討が必要です。
    # 今回はSignupフローに焦点を当てます。
    LOGIN_OTP_SESSION_KEY_PREFIX = 'login_otp_data_'


    @staticmethod
    def hash_password(plain_password: str) -> str:
        """
        平文のパスワードをハッシュ化します。
        Djangoのデフォルトハッシュアルゴリズムを使用します。
        """
        if not plain_password:
            logger.warning("空のパスワードがハッシュ化関数に渡されました。")
            return "" 
        return make_password(plain_password)

    @staticmethod
    def check_password(plain_password: str, hashed_password: str) -> bool:
        """
        平文のパスワードとハッシュ化されたパスワードを比較します。
        """
        return check_password(plain_password, hashed_password)

    @staticmethod
    def generate_otp(length: int = 6) -> str:
        """
        指定された長さの数字のみで構成されるワンタイムパスワード (OTP) を生成します。
        """
        return ''.join(secrets.choice(string.digits) for _ in range(length))

    @staticmethod
    def store_otp_for_signup(session: Dict[str, Any], email: str, otp: str) -> None:
        """
        サインアップフロー用のOTPとメールアドレスをセッションに保存します。
        
        Args:
            session (Dict[str, Any]): Djangoのリクエストセッションオブジェクト。
            email (str): OTPを関連付けるメールアドレス。
            otp (str): 生成されたOTP。
        """
        otp_expiration_time = time.time() + Authenticator.OTP_EXPIRATION_SECONDS
        session[Authenticator.SIGNUP_OTP_SESSION_KEY] = {
            'email': email, # ここでメールアドレス自体をセッションデータとして保存
            'otp': otp,
            'expires_at': otp_expiration_time,
            'is_verified': False # 初期状態では未検証
        }
        session.modified = True 
        logger.info(f"サインアップ用OTPをセッションに保存しました。メールアドレス: {email}, otp:{otp}, 有効期限: {Authenticator.OTP_EXPIRATION_SECONDS}秒後")

    @staticmethod
    def verify_otp_for_signup(session: Dict[str, Any], email: str, entered_otp: str) -> Tuple[bool, str]:
        """
        サインアップフロー用にセッションに保存されたOTPを検証します。
        有効期限切れチェックと、メールアドレスの一致チェックも行います。
        成功すれば、セッション内の`is_verified`フラグをTrueに設定します。

        Args:
            session (Dict[str, Any]): Djangoのリクエストセッションオブジェクト。
            email (str): ユーザーが入力したメールアドレス（セッションに保存されているものと一致するか確認するため）。
            entered_otp (str): ユーザーが入力したOTP。

        Returns:
            Tuple[bool, str]: 検証結果（True:成功、False:失敗）とメッセージのタプル。
        """
        stored_data = session.get(Authenticator.SIGNUP_OTP_SESSION_KEY)

        if not stored_data:
            logger.warning("OTP検証失敗 (サインアップ): セッションにOTPデータが見つかりません。")
            return False, '無効なOTP検証リクエストです。'

        # 保存されているメールアドレスと入力されたメールアドレスが一致するか確認
        if stored_data.get('email') != email:
            logger.warning(f"OTP検証失敗 (サインアップ): メールアドレスが一致しません。入力: {email}, 保存: {stored_data.get('email')}")
            return False, '無効なメールアドレスまたはOTPデータです。'

        stored_otp = stored_data['otp']
        expires_at = stored_data['expires_at']

        if time.time() > expires_at:
            del session[Authenticator.SIGNUP_OTP_SESSION_KEY] # 有効期限切れのOTPをセッションから削除
            session.modified = True
            logger.warning(f"OTP検証失敗 (サインアップ): メールアドレス '{email}' のOTPが有効期限切れです。")
            return False, 'OTPの有効期限が切れました。再度OTPを送信してください。'

        if entered_otp == stored_otp:
            # OTPが一致したら、検証済みフラグを立てる
            stored_data['is_verified'] = True
            session[Authenticator.SIGNUP_OTP_SESSION_KEY] = stored_data # セッションに更新を反映
            session.modified = True
            logger.info(f"メールアドレス '{email}' のOTP認証が成功しました。")
            return True, 'OTP認証成功'
        else:
            logger.warning(f"OTP検証失敗 (サインアップ): メールアドレス '{email}' のOTPが一致しません。")
            return False, 'OTPが違います。'

    @staticmethod
    def get_verified_email_for_signup(session: Dict[str, Any]) -> Optional[str]:
        """
        セッション内でサインアップ用のメールアドレスがOTP認証済みであるかを確認し、
        認証済みであればそのメールアドレスを返します。
        有効期限も同時に確認します。

        Args:
            session (Dict[str, Any]): Djangoのリクエストセッションオブジェクト。

        Returns:
            Optional[str]: OTP認証済みであればメールアドレス文字列、そうでなければNone。
        """
        stored_data = session.get(Authenticator.SIGNUP_OTP_SESSION_KEY)
        
        if stored_data:
            # 有効期限内であり、かつ `is_verified` が True であることを確認
            if time.time() <= stored_data.get('expires_at', 0) and stored_data.get('is_verified', False):
                return stored_data.get('email')
            else:
                Authenticator.clear_signup_otp_session(session)  # 有効期限切れや未検証の場合はセッションをクリア
        return None

    @staticmethod
    def clear_signup_otp_session(session: Dict[str, Any]) -> None:
        """
        サインアップフローのOTP関連セッションデータをクリアします。
        サインアップ完了後や、認証フローを中断する場合に呼び出します。
        """
        if Authenticator.SIGNUP_OTP_SESSION_KEY in session:
            del session[Authenticator.SIGNUP_OTP_SESSION_KEY]
            session.modified = True
            logger.info("サインアップ用OTPセッションデータをクリアしました。")
        else:
            logger.debug("クリア対象のサインアップ用OTPセッションデータが見つかりませんでした。")

    @staticmethod
    def send_otp_email(receiver_email: str, otp: str) -> bool:
        """
        指定されたメールアドレスにOTPを送信します。
        """
        subject = "【重要】あなたの認証コード"
        message = (
            f"お客様の認証コードは {otp} です。\n"
            f"このコードは {Authenticator.OTP_EXPIRATION_SECONDS // 60} 分間有効です。\n"
            "セキュリティのため、このコードを他者に開示しないでください。"
        )
        from_email = settings.DEFAULT_FROM_EMAIL
        try:
            send_mail(
                subject, message, from_email, [receiver_email], fail_silently=False,
            )
            logger.info(f"OTPメールを '{receiver_email}' に送信しました。")
            return True
        except Exception as e:
            logger.exception(f"OTPメールの送信中にエラーが発生しました。宛先: '{receiver_email}'")
            return False
    
    # 既存のログインフロー用OTP保存・検証メソッドはここでは割愛しますが、
    # store_otp_for_login(session, member_id, otp)
    # verify_otp_for_login(session, member_id, entered_otp)
    # clear_login_otp_session(session, member_id)
    # のように、別々に管理することを推奨します。