# apps/users/serializers.py

from rest_framework import serializers
from apps.users.models import Member 
import re 
from datetime import date
import logging

logger = logging.getLogger(__name__)

# カスタムバリデータ（例：パスワードの複雑性）
def validate_password_complexity(value):
    """
    パスワードの複雑性を検証します。
    - 最低8文字
    - 大文字、小文字、数字、特殊文字をそれぞれ1つ以上含む
    """
    if len(value) < 8:
        raise serializers.ValidationError("パスワードは最低8文字以上である必要があります。")
    if not re.search(r'[A-Z]', value):
        raise serializers.ValidationError("パスワードには少なくとも1つの大文字を含める必要があります。")
    if not re.search(r'[a-z]', value):
        raise serializers.ValidationError("パスワードには少なくとも1つの小文字を含める必要があります。")
    if not re.search(r'[0-9]', value):
        raise serializers.ValidationError("パスワードには少なくとも1つの数字を含める必要があります。")
    # 特殊文字は今回は任意だが、追加するなら
    # if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
    #    raise serializers.ValidationError("パスワードには少なくとも1つの特殊文字を含める必要があります。")
    return value

# カスタムバリデータ（例：電話番号の形式）
def validate_phone_number_format(value):
    """
    電話番号の形式を検証します（例: 日本の携帯電話番号10桁または11桁の数字）。
    ハイフンは許容しない場合を想定。
    """
    if not re.fullmatch(r'^\d{10,11}$', value):
        raise serializers.ValidationError("有効な電話番号の形式ではありません（ハイフンなしで10〜11桁の数字）。")
    return value

# カスタムバリデータ（生年月日の範囲）
def validate_birthday_range(value):
    """
    生年月日が過去の日付であり、特定の範囲内にあることを検証します（例：10歳以上120歳以下）。
    """
    if value >= date.today():
        raise serializers.ValidationError("生年月日は未来の日付であってはなりません。")
    # 仮に10歳以上、120歳以下を強制する場合
    min_date = date(date.today().year - 120, date.today().month, date.today().day)
    max_date = date(date.today().year - 10, date.today().month, date.today().day)
    if not (min_date <= value <= max_date):
        raise serializers.ValidationError("有効な生年月日の範囲ではありません。")
    return value

# --- 各APIに対応するSerializer ---

class EmailOnlySerializer(serializers.Serializer):
    """
    メールアドレスのみを検証するためのSerializer。
    (CheckEmailAvailabilityAPIView, SendOtpForSignupAPIViewで使用)
    """
    emailAddress = serializers.EmailField(
        required=True,
        max_length=255,
        error_messages={
            'required': 'メールアドレスは必須です。',
            'invalid': '有効なメールアドレス形式ではありません。',
            'max_length': 'メールアドレスは255文字以内で入力してください。'
        }
    )

class OtpVerificationSerializer(serializers.Serializer):
    """
    OTP検証のためのSerializer。
    (VerifyOtpForSignupAPIView, LoginAPIView, OTPVerifyAPIViewで使用)
    """
    emailAddress = serializers.EmailField(
        required=True,
        max_length=255,
        error_messages={
            'required': 'メールアドレスは必須です。',
            'invalid': '有効なメールアドレス形式ではありません。'
        }
    )
    otp = serializers.CharField(
        required=True,
        min_length=6, # OTPの桁数に合わせる
        max_length=6, # OTPの桁数に合わせる
        error_messages={
            'required': 'OTPは必須です。',
            'min_length': 'OTPは6桁の数字である必要があります。',
            'max_length': 'OTPは6桁の数字である必要があります。'
        }
    )
    # ここでOTPが数字のみであることも検証できるが、
    # Authenticator.generate_otpが数字のみを生成するため、ここでは省略可能。
    # 必要なら validate_otp(self, value) メソッドを追加。

class SignupSerializer(serializers.Serializer):
    """
    新規ユーザー登録のためのSerializer。
    (SignupAPIViewで使用)
    """
    # 既存のMemberモデルのフィールドと合わせる
    firstName = serializers.CharField(
        required=True,
        max_length=100,
        error_messages={'required': '名（ファーストネーム）は必須です。'}
    )
    lastName = serializers.CharField(
        required=True,
        max_length=100,
        error_messages={'required': '姓（ラストネーム）は必須です。'}
    )
    gender = serializers.CharField(
        required=False, # 性別は任意か、特定の選択肢に限定されるべき
        max_length=10,
        allow_null=True, # nullを許容
        allow_blank=True # 空文字列を許容
    )
    birthday = serializers.DateField(
        required=False, # 生年月日は任意か
        allow_null=True,
        validators=[validate_birthday_range] # カスタムバリデータ適用
    )
    emailAddress = serializers.EmailField(
        required=True,
        max_length=255,
        error_messages={
            'required': 'メールアドレスは必須です。',
            'invalid': '有効なメールアドレス形式ではありません。',
            'max_length': 'メールアドレスは255文字以内で入力してください。'
        }
    )
    phoneNumber = serializers.CharField(
        required=False, # 電話番号は任意か
        max_length=15,
        allow_null=True,
        allow_blank=True,
        validators=[validate_phone_number_format] # カスタムバリデータ適用
    )
    password = serializers.CharField(
        required=True,
        max_length=128, # ハッシュ化後のパスワード長に合わせる
        write_only=True, # レスポンスには含めない
        validators=[validate_password_complexity], # カスタムバリデータ適用
        error_messages={'required': 'パスワードは必須です。'}
    )
    address = serializers.CharField(
        required=False,
        max_length=255,
        allow_null=True,
        allow_blank=True
    )

    # メールアドレスのユニーク制約はUserManager.create_memberで処理されるが、
    # ここでバリデーションすることも可能
    # def validate_emailAddress(self, value):
    #     if Member.objects.filter(emailAddress=value).exists():
    #         raise serializers.ValidationError("このメールアドレスは既に登録済みです。")
    #     return value

class LoginSerializer(serializers.Serializer):
    """
    ユーザーログインのためのSerializer。
    (LoginAPIViewで使用)
    """
    emailAddress = serializers.EmailField(required=True, max_length=255)
    password = serializers.CharField(required=True, max_length=128, write_only=True)

class PlanSettingsSerializer(serializers.Serializer):
    """
    プラン設定更新のためのSerializer。
    (PlanSettingsAPIViewで使用)
    """
    plan = serializers.CharField(required=True, max_length=50) # プラン名を想定
    # subscriptionRegistrationDate はAPI側で自動生成するので、ここでは不要

class ProfileUpdateSerializer(serializers.Serializer):
    """
    プロフィール更新のためのSerializer。
    (ProfileSettingsAPIViewのPOSTで使用)
    """
    firstName = serializers.CharField(required=False, max_length=100, allow_blank=True)
    lastName = serializers.CharField(required=False, max_length=100, allow_blank=True)
    gender = serializers.CharField(required=False, max_length=10, allow_blank=True, allow_null=True)
    birthday = serializers.DateField(required=False, allow_null=True, validators=[validate_birthday_range])
    emailAddress = serializers.EmailField(required=False, max_length=255, allow_blank=True)
    phoneNumber = serializers.CharField(required=False, max_length=15, allow_blank=True, allow_null=True, validators=[validate_phone_number_format])
    address = serializers.CharField(required=False, max_length=255, allow_blank=True, allow_null=True)
    # パスワードは含めない（専用のAPIで更新するため）

    def validate_emailAddress(self, value):
        # メールアドレスを更新する場合、重複チェックを行う
        # self.instance は更新対象のMemberモデルインスタンスを指す
        if self.instance and Member.objects.filter(emailAddress=value).exclude(id=self.instance.id).exists():
            raise serializers.ValidationError("このメールアドレスは既に他のアカウントで登録済みです。")
        elif not self.instance and Member.objects.filter(emailAddress=value).exists():
            raise serializers.ValidationError("このメールアドレスは既に登録済みです。")
        return value

class DeleteAccountSerializer(serializers.Serializer):
    """
    アカウント削除のためのSerializer。
    (DeleteAccountAPIViewで使用)
    """
    emailAddress = serializers.EmailField(
        required=True,
        max_length=255,
        error_messages={
            'required': 'メールアドレスは必須です。',
            'invalid': '有効なメールアドレス形式ではありません。'
        }
    )
    # 実際のアカウント削除では、現在のパスワード確認も必須にすべき
    # current_password = serializers.CharField(required=True, write_only=True)