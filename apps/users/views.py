# apps/users/views.py (修正版)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from .services.user_manager import UserManager
from apps.users.services.authenticator import Authenticator 
from django.db import IntegrityError
from typing import Optional, Dict, Any, Tuple
import logging
import time 
import datetime

logger = logging.getLogger(__name__)


class CheckEmailAvailabilityAPIView(APIView):
    """
    メールアドレスが既に登録済みかを確認するAPIビュー。
    """
    def post(self, request) -> Response:
        email_address: Optional[str] = request.data.get('emailAddress')

        if not email_address:
            logger.warning("メールアドレス存在確認失敗: メールアドレスが提供されていません。")
            return Response(
                {'error': 'メールアドレスは必須です。'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            member = UserManager.search_member_by_email(email_address)
            if member:
                logger.info(f"メールアドレス '{email_address}' は既に登録済みです。")
                return Response({'exists': True, 'message': 'このメールアドレスは既に登録済みです。'}, status=status.HTTP_200_OK)
            else:
                logger.info(f"メールアドレス '{email_address}' は利用可能です。")
                return Response({'exists': False, 'message': 'このメールアドレスは利用可能です。'}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception(f"メールアドレス存在確認中に予期せぬエラーが発生しました。メールアドレス: {email_address}")
            return Response(
                {'error': f'メールアドレス確認中にエラーが発生しました。 ({e})'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class SendOtpForSignupAPIView(APIView):
    """
    新規登録のためにOTPを生成し、メールアドレスに送信するAPIビュー。
    未登録のメールアドレスにのみ送信を許可します。
    """
    def post(self, request) -> Response:
        email_address: Optional[str] = request.data.get('emailAddress')

        if not email_address:
            logger.warning("OTP送信失敗 (サインアップ): メールアドレスが提供されていません。")
            return Response(
                {'error': 'メールアドレスは必須です。'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 既に登録済みのメールアドレスでないか確認
            if UserManager.search_member_by_email(email_address):
                logger.warning(f"OTP送信失敗 (サインアップ): 登録済みのメールアドレス '{email_address}' にOTPが要求されました。")
                return Response(
                    {'error': 'このメールアドレスは既に登録済みです。'},
                    status=status.HTTP_409_CONFLICT # Conflict を返すのが適切
                )
            
            otp: str = Authenticator.generate_otp()
            # サインアップフローとしてOTPとメールアドレスをセッションに保存
            Authenticator.store_otp_for_signup(request.session, email_address, otp)

            if Authenticator.send_otp_email(email_address, otp):
                logger.info(f"サインアップ用OTPをメールアドレス '{email_address}' に送信し、セッションに保存しました。")
                return Response(
                    {'message': '認証コードを送信しました。メールをご確認ください。'},
                    status=status.HTTP_200_OK
                )
            else:
                logger.error(f"OTPメール送信失敗 (サインアップ): メールアドレス '{email_address}'")
                return Response(
                    {'error': '認証コードの送信に失敗しました。しばらくしてから再度お試しください。'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            logger.exception(f"OTP送信中に予期せぬエラーが発生しました。メールアドレス: {email_address}")
            return Response(
                {'error': f'認証コード送信中にエラーが発生しました。 ({e})'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class VerifyOtpForSignupAPIView(APIView):
    """
    新規登録のために送信されたOTPを検証するAPIビュー。
    成功した場合、セッションにメールアドレスが検証済みであることを記録します。
    """
    def post(self, request) -> Response:
        email_address: Optional[str] = request.data.get('emailAddress') # フロントからメールアドレスも受け取る
        entered_otp: Optional[str] = request.data.get('otp')

        if not email_address or not entered_otp:
            logger.warning("OTP検証失敗 (サインアップ): メールアドレスまたはOTPが提供されていません。")
            return Response(
                {'error': 'メールアドレスとOTPは必須です。'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Authenticatorクラスのverify_otp_for_signupメソッドを呼び出す
            is_valid, message = Authenticator.verify_otp_for_signup(request.session, email_address, entered_otp)

            if is_valid:
                logger.info(f"メールアドレス '{email_address}' のOTP検証が成功しました。サインアップを続行できます。")
                # フロントエンドには認証成功メッセージのみ返し、次のステップへ促す
                return Response({'message': message, 'status': '認証成功'}, status=status.HTTP_200_OK)
            else:
                logger.warning(f"メールアドレス '{email_address}' のOTP検証が失敗しました: {message}")
                return Response({'error': message, 'status': '検証失敗'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(f"OTP検証中に予期せぬエラーが発生しました。メールアドレス: {email_address}")
            return Response(
                {'error': f'OTP検証中に予期せぬエラーが発生しました。 ({e})'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# --- 既存APIの修正 ---

class SignupAPIView(APIView):
    """
    新規ユーザー登録のためのAPIビュー。
    このAPIを呼び出す前に、メールアドレスがOTP認証済みであることを前提とします。
    """
    def post(self, request) -> Response:
        data: Dict[str, Any] = request.data
        
        plain_password: Optional[str] = data.get('password') # 平文パスワード

        try:
            if not plain_password:
                logger.warning("サインアップ失敗: パスワードが提供されていません。")
                return Response(
                    {'error': 'パスワードは必須です。'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # --- セッションからOTP認証済みのメールアドレスを取得 ---
            authenticated_email: Optional[str] = Authenticator.get_verified_email_for_signup(request.session)

            if not authenticated_email:
                logger.warning("サインアップ失敗: セッションにOTP認証済みのメールアドレスが見つかりません。")
                return Response(
                    {'error': 'メールアドレスの認証が完了していません。再度認証を行ってください。'},
                    status=status.HTTP_403_FORBIDDEN # 認証不足による拒否
                )
            
            # (オプション) リクエストデータにメールアドレスが含まれている場合、セッションのものと一致するか確認
            email_address_from_request: Optional[str] = data.get('emailAddress')
            if email_address_from_request and email_address_from_request != authenticated_email:
                logger.warning(f"サインアップ失敗: リクエストのメールアドレス '{email_address_from_request}' とセッションの認証済みメールアドレス '{authenticated_email}' が一致しません。")
                return Response(
                    {'error': '提供されたメールアドレスが認証済みメールアドレスと一致しません。'},
                    status=status.HTTP_400_BAD_REQUEST
                )


            # パスワードをハッシュ化して安全に保存
            hashed_password: str = Authenticator.hash_password(plain_password)
            
            member_data_for_creation: Dict[str, Any] = {
                'emailAddress': authenticated_email, # ここでセッションから取得した認証済みメールアドレスを使用
                'password': hashed_password,
                # その他の必須フィールドをリクエストデータから取得し、UserManagerで処理されるように渡す
                'firstName': data.get('firstName'),
                'lastName': data.get('lastName'),
                'gender': data.get('gender'),
                'birthday': data.get('birthday'),
                'phoneNumber': data.get('phoneNumber'),
                'address': data.get('address')
            }
            
            # UserManagerのformat_required_member_dataでさらに整形が必要な場合
            final_member_data = UserManager.format_required_member_data(member_data_for_creation)
            
            member = UserManager.create_member(final_member_data)
            
            # サインアップ成功後、セッションからOTP関連データをクリア
            Authenticator.clear_signup_otp_session(request.session)
            
            logger.info(f"新規メンバーが作成されました: ID={member.id}, Email={member.emailAddress}")
            return Response(status=status.HTTP_201_CREATED)
            
        except IntegrityError:
            logger.warning(f"サインアップ失敗: 既存のメールアドレス '{authenticated_email}' が使用されました。OTP認証済みだが、既に登録済み。")
            return Response(
                {'error': '登録に失敗しました。このメールアドレスは既に登録済みです。'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception(f"サインアップ中に予期せぬエラーが発生しました。メールアドレス: {authenticated_email}")
            return Response(
                {'error': f'登録中に予期せぬエラーが発生しました。しばらくしてから再度お試しください。 ({e})'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# --- ログインAPI (OTPによる2段階認証はそのまま) ---
# このAPIはサインアップ後の通常のログインフローで使用します。

class LoginAPIView(APIView):
    """
    ユーザーログインと2段階認証 (OTP) の開始のためのAPIビュー。
    """
    def post(self, request) -> Response:
        data: Dict[str, Any] = request.data
        email: Optional[str] = data.get('emailAddress')
        plain_password: Optional[str] = data.get('password')

        if not email or not plain_password:
            logger.warning("ログイン失敗: メールアドレスまたはパスワードが提供されていません。")
            return Response(
                {'error': 'メールアドレスとパスワードは必須です。'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            member = UserManager.search_member_by_email(email)
            
            if member and Authenticator.check_password(plain_password, member.password):
                otp: str = Authenticator.generate_otp()
                # ログインフロー用のOTPをセッションに保存（メールアドレスをキーのプレフィックスに含める）
                # Authenticator.store_otp_for_login は Authenticatorクラスに別途実装が必要です
                # 今回は既存の store_otp_in_session を is_signup_flow=False で呼び出す形で仮対応
                # (Authenticator.store_otp_in_session の is_signup_flow=False 時のロジックも適切に修正してください)
                # より堅牢には、store_otp_for_login(request.session, member.id, otp) のようなメソッドが望ましい
                request.session[f"{Authenticator.LOGIN_OTP_SESSION_KEY_PREFIX}{member.id}"] = { # member.idをキーにする
                    'otp': otp,
                    'expires_at': time.time() + Authenticator.OTP_EXPIRATION_SECONDS
                }
                request.session.modified = True
                
                logger.info(f"ログイン試行成功、OTPを送信しました: MemberID={member.id}, Email={email}")
                # フロントエンドには、次のOTP検証ステップのためにmember_idを返す
                return Response({'member_id': member.id, 'message': '認証コードを送信しました。'}, status=status.HTTP_202_ACCEPTED)
            else:
                logger.warning(f"ログイン失敗: 無効な認証情報。メールアドレス: '{email}'")
                return Response(
                    {'error':'ログイン失敗。メールアドレスまたはパスワードが違います。'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        except Exception as e:
            logger.exception(f"ログイン中に予期せぬエラーが発生しました。メールアドレス: {email}")
            return Response(
                {'error': f'ログイン中に予期せぬエラーが発生しました。 ({e})'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class OTPVerifyAPIView(APIView):
    """
    ログイン時の2段階認証 (OTP) の検証のためのAPIビュー。
    """
    def post(self, request) -> Response:
        data: Dict[str, Any] = request.data
        member_id: Optional[int] = request.session.get('member_id')
        entered_otp: Optional[str] = data.get('otp')

        if not member_id or not entered_otp:
            logger.warning("OTP検証失敗 (ログイン): member_id または OTP が提供されていません。")
            return Response(
                {'error': 'メンバーIDとOTPは必須です。'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # ログイン時のOTP検証フローを呼び出す
            session_key = f"{Authenticator.LOGIN_OTP_SESSION_KEY_PREFIX}{member_id}"
            stored_data = request.session.get(session_key)

            if not stored_data:
                logger.warning(f"OTP検証失敗 (ログイン): メンバーID {member_id} のOTPセッションデータが見つかりません。")
                return Response({'error': '無効なOTP検証リクエストです。'}, status=status.HTTP_400_BAD_REQUEST)

            stored_otp = stored_data['otp']
            expires_at = stored_data['expires_at']

            if time.time() > expires_at:
                del request.session[session_key]
                request.session.modified = True
                logger.warning(f"OTP検証失敗 (ログイン): メンバーID {member_id} のOTPが有効期限切れです。")
                return Response({'error': 'OTPの有効期限が切れました。再度ログインしてください。'}, status=status.HTTP_400_BAD_REQUEST)

            if entered_otp == stored_otp:
                del request.session[session_key] # 成功したらセッションから削除
                request.session.modified = True
                
                # 認証成功の場合、実際のメンバー情報を取得し、セッションにmember_idを保存（最終ログイン）
                # (OTPVerifyAPIViewがmember_idを受け取る前提なので、UserManager.get_member_by_idが必要)
                member = UserManager.get_member_by_id(member_id) # UserManagerにget_member_by_idを追加している前提
                if member:
                    request.session['member_id'] = member_id # ユーザーIDをセッションに保存
                    request.session.modified = True
                    logger.info(f"メンバーID {member_id} のログイン用OTP認証が成功し、セッションに保存されました。")
                    return Response({'message': 'ログイン成功'}, status=status.HTTP_200_OK)
                else:
                    logger.error(f"ログイン用OTP認証成功後、メンバーID '{member_id}' が見つかりません。データ不整合の可能性。")
                    return Response({'error': '認証は成功しましたが、ユーザー情報が見つかりません。'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                logger.warning(f"メンバーID {member_id} のログイン用OTPが一致しません。")
                return Response({'error': 'OTPが違います。'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(f"ログイン用OTP検証中に予期せぬエラーが発生しました。MemberID: {member_id}")
            return Response(
                {'error': f'OTP検証中に予期せぬエラーが発生しました。 ({e})'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# --- 既存API (Logout, PlanSettings, ProfileSettings, DeleteAccount は基本的に変更なし) ---
# これらのAPIは、request.session.get('member_id') を使用して認証済みユーザーIDを取得するようにしてください。
# ProfileSettingsAPIViewのgetメソッドにUserManager.get_member_by_idの利用を反映させます。

class LogoutAPIView(APIView):
    """
    ユーザーのログアウトのためのAPIビュー。
    """
    def post(self, request) -> Response:
        try:
            member_id = request.session.get('member_id') # セッションから取得

            if member_id: # member_idがセッションにあればログアウト処理
                del request.session['member_id']
                request.session.modified = True
                logger.info(f"メンバーID {member_id} がログアウトしました。")
            else:
                logger.info("セッションにmember_idがない状態でログアウトリクエストがありました。")
            return Response(status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception(f"ログアウト中にエラーが発生しました: {e}")
            return Response(
                {'error': f'ログアウトに失敗しました。 ({e})'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PlanSettingsAPIView(APIView):
    """
    メンバーのプラン設定を更新するためのAPIビュー。
    """
    def post(self, request) -> Response:
        # このAPIも認証済みユーザーのみが利用すべきなので、member_idはセッションから取得する
        current_member_id: Optional[int] = request.session.get('member_id')
        if not current_member_id:
            logger.warning("プラン設定更新失敗: 認証されていません。")
            return Response({'error': '認証されていません。再ログインしてください。'}, status=status.HTTP_401_UNAUTHORIZED)
        
        data: Dict[str, Any] = request.data
        # リクエストボディからのmember_idは無視し、セッションのmember_idを使用する
        plan: Optional[str] = data.get('plan')

        if not plan:
            logger.warning(f"プラン設定更新失敗: プランが提供されていません。MemberID={current_member_id}")
            return Response(
                {'error': 'プランは必須です。'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            update_data = {
                'plan': plan,
                'subscriptionRegistrationDate': datetime.date.today()
            }
            member = UserManager.update_member(current_member_id, update_data) # セッションのmember_idを使用
            if member:
                logger.info(f"メンバーID {current_member_id} のプラン設定を更新しました。プラン: {plan}")
                return Response(status=status.HTTP_200_OK)
            else:
                logger.error(f"プラン設定更新中にメンバーID {current_member_id} が見つかりません。データ不整合の可能性。")
                return Response(
                    {'error': '会員情報が見つかりません。'},
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            logger.exception(f"プラン設定更新中に予期せぬエラーが発生しました。MemberID={current_member_id}")
            return Response(
                {'error': f'プラン設定中に予期せぬエラーが発生しました。 ({e})'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProfileSettingsAPIView(APIView):
    """
    ユーザーのプロフィール情報を取得・更新するためのAPIビュー。
    認証済みユーザーの情報をセッションIDに基づいて返します。
    """
    def get(self, request) -> Response:
        # member_id はリクエストGETパラメータからではなく、セッションから取得する
        current_member_id: Optional[int] = request.session.get('member_id')

        if not current_member_id:
            logger.warning("プロフィール取得失敗: 認証されていません。")
            return Response({'error': '認証されていません。再ログインしてください。'}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            # UserManagerにget_member_by_idメソッドが存在することを前提とする
            member = UserManager.get_member_by_id(current_member_id) 
            
            if member:
                member_data: Dict[str, Any] = {
                    'firstName': member.firstName,
                    'lastName': member.lastName,
                    'gender': member.gender,
                    'birthday': member.birthday,
                    'emailAddress': member.emailAddress,
                    'phoneNumber': member.phoneNumber,
                    'address': member.address,
                }
                logger.info(f"メンバーID {current_member_id} のプロフィール情報を取得しました。")
                return Response({'member': member_data}, status=status.HTTP_200_OK)
            else:
                logger.error(f"プロフィール取得失敗: セッションのmember_id {current_member_id} に対応する会員情報がDBに見つかりません。")
                return Response(
                    {'error': '会員情報が見つかりません。'},
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            logger.exception(f"プロフィール取得中に予期せぬエラーが発生しました。MemberID={current_member_id}")
            return Response(
                {'error': f'プロフィール取得中に予期せぬエラーが発生しました。 ({e})'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request) -> Response:
        # member_id はリクエストボディからではなく、セッションから取得する
        current_member_id: Optional[int] = request.session.get('member_id')
        if not current_member_id:
            logger.warning("プロフィール更新失敗: 認証されていません。")
            return Response({'error': '認証されていません。再ログインしてください。'}, status=status.HTTP_401_UNAUTHORIZED)
        
        data: Dict[str, Any] = request.data
        
        try:
            update_data: Dict[str, Any] = {}
            update_fields = [
                'firstName', 'lastName', 'gender', 'birthday',
                'phoneNumber', 'address'
            ]
            for field in update_fields:
                if field in data and data[field] is not None:
                    update_data[field] = data[field]
            
            if 'emailAddress' in data and data['emailAddress'] is not None:
                # メールアドレスの更新は機密性が高く、専用のフロー（OTP再認証など）を推奨
                # ここでは単純に更新に含めるが、実運用では注意
                logger.warning(f"プロフィール更新リクエストにメールアドレスの更新が含まれています。MemberID={current_member_id}")
                update_data['emailAddress'] = data['emailAddress']
                
            if 'password' in data and data['password'] is not None:
                # パスワードの更新も専用API（古いパスワードの確認など）を推奨
                logger.warning(f"プロフィール更新リクエストにパスワードの更新が含まれています。MemberID={current_member_id}")
                update_data['password'] = Authenticator.hash_password(data['password']) # ハッシュ化して更新
            
            member = UserManager.update_member(current_member_id, update_data) # セッションのmember_idを使用
            if member:
                logger.info(f"メンバーID {current_member_id} のプロフィールを更新しました。更新データ: {update_data.keys()}")
                return Response(status=status.HTTP_200_OK)
            else:
                logger.error(f"プロフィール更新失敗: セッションのmember_id {current_member_id} に対応する会員情報がDBに見つかりません。")
                return Response(
                    {'error': '会員情報が見つかりません。'},
                    status=status.HTTP_404_NOT_FOUND
                )
        except IntegrityError: # メールアドレス重複など
            logger.warning(f"プロフィール更新失敗: メールアドレス '{data.get('emailAddress')}' が既に登録済みです。MemberID={current_member_id}")
            return Response(
                {'error': 'メールアドレスは既に登録済みです。'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception(f"プロフィール更新中に予期せぬエラーが発生しました。MemberID={current_member_id}")
            return Response(
                {'error': f'プロフィール更新中に予期せぬエラーが発生しました。 ({e})'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DeleteAccountAPIView(APIView):
    """
    ユーザーアカウントの削除のためのAPIビュー。
    """
    def post(self, request) -> Response:
        # member_id はリクエストボディからではなく、セッションから取得する
        current_member_id: Optional[int] = request.session.get('member_id')
        if not current_member_id:
            logger.warning("アカウント削除失敗: 認証されていません。")
            return Response({'error': '認証されていません。再ログインしてください。'}, status=status.HTTP_401_UNAUTHORIZED)

        data: Dict[str, Any] = request.data
        # メールアドレスは確認のためにリクエストボディから受け取る
        email_address_from_request: Optional[str] = data.get('emailAddress')

        if not email_address_from_request:
            logger.warning(f"アカウント削除失敗: メールアドレスが提供されていません。MemberID={current_member_id}")
            return Response(
                {'error': 'メールアドレスは必須です。'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 削除対象のユーザーを取得し、提供されたメールアドレスが一致するか確認
            member_to_delete = UserManager.get_member_by_id(current_member_id)
            if not member_to_delete or member_to_delete.emailAddress != email_address_from_request:
                logger.warning(f"アカウント削除失敗: メンバーID {current_member_id} またはメールアドレス '{email_address_from_request}' が一致しません。")
                return Response(
                    {'error': '認証情報が一致しません。'},
                    status=status.HTTP_403_FORBIDDEN # 権限がない、または情報が不一致
                )

            success: bool = UserManager.delete_member(current_member_id, email_address_from_request) # セッションのIDとリクエストのメールアドレス
            if success:
                logger.info(f"メンバーID {current_member_id} のアカウントを削除しました。")
                # アカウント削除成功後、セッションも破棄する
                if 'member_id' in request.session:
                    del request.session['member_id']
                    request.session.modified = True
                return Response(status=status.HTTP_200_OK)
            else:
                logger.error(f"アカウント削除失敗（予期せぬ状態）：MemberID {current_member_id} のDB削除に失敗。")
                return Response(
                    {'error': 'アカウント削除に失敗しました。'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            logger.exception(f"アカウント削除中に予期せぬエラーが発生しました。MemberID={current_member_id}")
            return Response(
                {'error': f'アカウント削除中に予期せぬエラーが発生しました。 ({e})'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )