from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from .services import UserManager
import hashlib, time, secrets, string, datetime
from django.core.mail import send_mail


otp_storage = {}

def hash_password(password):
    if password is None:
        return None
    return hashlib.sha256(password.encode()).hexdigest()

def generate_otp(length=6):
    return ''.join(secrets.choice(string.digits) for _ in range(length))

def send_otp_email(receiver_email, otp):
    subject = "2段階認証コード"
    message = f"あなたの2段階認証コードは {otp} です。"
    from_email = settings.DEFAULT_FROM_EMAIL
    try:
        send_mail(
            subject, message, from_email, [receiver_email], fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"メール送信エラー: {e}")
        return False

def get_member_data(data):
    return {
        'firstName': data.get('firstName'),
        'lastName': data.get('lastName'),
        'gender': data.get('gender'),
        'birthday': data.get('birthday'),
        'emailAddress': data.get('emailAddress'),
        'phoneNumber': data.get('phoneNumber'),
        'password': data.get('password'),
        'address': data.get('address')
    }

from django.db import IntegrityError

class SignupAPIView(APIView):
    def post(self, request):
        data = request.data
        member_data = get_member_data(data)
        member_data['password'] = hash_password(member_data['password'])
        try:
            member = UserManager.create_member(member_data)
            #レスポンスのSTATUSはステータスコードで判定できるから↓の”登録完了しました等は不要でいいよ！！ エラーの時にどんな内容かわかればOK”
            return Response({'member_id': member.id}, status=status.HTTP_201_CREATED)
        except IntegrityError as e:
            # UNIQUE制約違反の場合は400で特定メッセージ
            return Response({'error': '登録に失敗/このメールアドレスは既に登録済'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"登録エラー: {e}")
            return Response({'error': '登録に失敗'+ str(e)}, status=status.HTTP_400_BAD_REQUEST)

class LoginAPIView(APIView):
    def post(self, request):
        data = request.data
        email = data.get('emailAddress')
        password = hash_password(data.get('password'))
        member = UserManager.get_member_by_email_and_password(email, password)
        if member:
            otp = generate_otp()
            otp_expiration_time = time.time() + 300
            otp_storage[member.id] = {'otp': otp, 'expires_at': otp_expiration_time}
            if send_otp_email(email, otp):
                return Response({'member_id': member.id}, status=status.HTTP_202_ACCEPTED)
            else:
                return Response({'error': 'OTPメール送信失敗/メール送信中にエラーが発生しました。'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({'error':'ログイン失敗/メールアドレスまたはパスワードが違う'}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutAPIView(APIView):
    def post(self, request):
        try:
            if 'member_id' in request.session:
                del request.session['member_id']
            return Response(status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error':'ログアウトに失敗' + str(e)}, status=status.HTTP_400_BAD_REQUEST)

class OTPVerifyAPIView(APIView):
    def post(self, request):
        data = request.data
        member_id = data.get('member_id')
        entered_otp = data.get('otp')
        if member_id not in otp_storage:
            return Response({'status': '検証失敗', 'error': '無効なOTP検証リクエストです。'}, status=status.HTTP_400_BAD_REQUEST)
        stored_data = otp_storage[member_id]
        stored_otp = stored_data['otp']
        expires_at = stored_data['expires_at']
        if time.time() > expires_at:
            del otp_storage[member_id]
            return Response({'status': '検証失敗', 'error': 'OTPの有効期限が切れました。再度ログインしてください。'}, status=status.HTTP_400_BAD_REQUEST)
        if entered_otp == stored_otp:
            request.session['member_id'] = member_id
            del otp_storage[member_id]
            return Response({'status': 'OTP認証成功'}, status=status.HTTP_200_OK)
        else:
            return Response({'status': 'OTPが違います'}, status=status.HTTP_400_BAD_REQUEST)

class PlanSettingsAPIView(APIView):
    def post(self, request):
        data = request.data
        member_id = data.get('member_id')
        plan = data.get('plan')
        member = UserManager.update_member(member_id, {'plan': plan, 'subscriptionRegistrationDate': datetime.date.today()})
        if member:
            return Response(status=status.HTTP_200_OK)
        else:
            return Response({'status': '会員情報が見つかりません。'}, status=status.HTTP_404_NOT_FOUND)

class ProfileSettingsAPIView(APIView):
    def get(self, request):
        member_id = request.GET.get('member_id')
        if not member_id:
            return Response({'error': 'member_idが指定されていません。'}, status=status.HTTP_400_BAD_REQUEST)
        member = UserManager.update_member(member_id, {})  # 取得専用のgetメソッド作ってもいい
        if member:
            member_data = {
                'firstName': member.firstName,
                'lastName': member.lastName,
                'gender': member.gender,
                'birthday': member.birthday,
                'emailAddress': member.emailAddress,
                'phoneNumber': member.phoneNumber,
                'address': member.address,
            }
            return Response({'member': member_data}, status=status.HTTP_200_OK)
        else:
            return Response({'error': '会員情報が見つかりません。'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        data = request.data
        member_id = data.get('member_id')
        member_data = get_member_data(data)
        member = UserManager.update_member(member_id, member_data)
        if member:
            return Response(status=status.HTTP_200_OK)
        else:
            return Response({'status': '会員情報が見つかりません。'}, status=status.HTTP_404_NOT_FOUND)

class DeleteAccountAPIView(APIView):
    def post(self, request):
        data = request.data
        member_id = data.get('member_id')
        emailAddress = data.get('emailAddress')
        success = UserManager.delete_member(member_id, emailAddress)
        if success:
            return Response(status=status.HTTP_200_OK)
        else:
            return Response({'status': '会員情報が見つかりません。'}, status=status.HTTP_404_NOT_FOUND)
