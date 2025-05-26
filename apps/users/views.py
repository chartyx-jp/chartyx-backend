from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Member
from apps.common.db_operator import DBOperator
import random
import hashlib
import datetime
db_operator = DBOperator()
# import pyotp

# get_member
def get_member_data(data):
    return {
        'firstName': data.get('firstName'),
        'lastName': data.get('lastName'),
        'gender': data.get('gender'),
        'birthday': data.get('birthday'),
        'emailAddress': data.get('emailAddress'),
        'phoneNumber': data.get('phoneNumber'),
        'password': data.get('password'),  # パスワードのハッシュ化推奨
        'address': data.get('address')
    }

# パスワードのハッシュ化
def hash_password(password):
    if password is None:
        return None
    return hashlib.sha256(password.encode()).hexdigest()  # SHA-256

#@csrf_exempt はAPI用途でCSRFチェックを無効化（本番ではトークン認証等を推奨）。
#signup-会員登録
@csrf_exempt    
def signup(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            member_data = get_member_data(data)
            member_data['password'] = hash_password(member_data['password'])
            member = Member.objects.create(**member_data)
            return JsonResponse({'status': '登録完了しました。', 'member_id':member.id}, status=201)
        except Exception as e:
            return JsonResponse({'status': '登録に失敗しました。', 'error': str(e)}, status=400)
    else:
        return JsonResponse({'error': 'POST request required'}, status=405)

# OPT発行 6桁数字生成
@csrf_exempt
def issueOTP(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('emailAddress')
            # pyotpで6桁OTP生成
            secret = pyotp.random_base32()
            totp = pyotp.TOTP(secret, digits=6, interval=300)  #only300sec
            otp = totp.now()
            member = DBOperator(Member).get_or_none(emailAddress=email)
            if member:
                member.otp = otp
                member.otp_secret = secret
                member.save()
                # OTPをメールで送信する処理を追加
                return JsonResponse({'status': 'OTPが発行されました。', 'otp': otp}, status=200)
            else:
                return JsonResponse({'status': '会員情報が見つかりません。'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'OTP発行に失敗しました。', 'error': str(e)}, status=400)
    else:
        return JsonResponse({'error': 'POST request required'}, status=405)

# verifyOTP-OPT認証
@csrf_exempt
def verifyOTP(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('emailAddress')
            otp = data.get('otp')
            member = db_operator.get_or_none(emailAddress=email, otp=otp)
            if member and member.otp == otp:
                member.otp = None  # OTPを無効化
                member.otp_secret = None
                member.save()
                return JsonResponse({'status': '認証成功', 'member_id': member.userId}, status=200)
            else:
                return JsonResponse({'status': '認証失敗'}, status=400)
        except Exception as e:
            return JsonResponse({'status': '認証に失敗しました。', 'error': str(e)}, status=400)
    else:
        return JsonResponse({'error': 'POST request required'}, status=405)

#login-ログイン
@csrf_exempt
def login(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            emailAddress = data.get('emailAddress')
            password = hash_password(data.get('password'))
            member = DBOperator(Member).get_or_none(emailAddress=emailAddress, password=password)  # パスワードのハッシュ化推奨
            if member:
                return JsonResponse({'status': 'ログイン成功', 'member_id': member.id}, status=200)
            else:
                return JsonResponse({'status': 'ログイン失敗', 'error':'メールアドレスまたはパスワードが違うよ'}, status=401)
        except Exception as e:
            return JsonResponse({'status': 'ログインに失敗しました。', 'error': str(e)}, status=400)
    else:
        return JsonResponse({'error': 'POST request required'}, status=405)

# planSettings-プラン変更
@csrf_exempt
def planSettings(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            userId = data.get('userId')
            plan = data.get('plan') # sentakushita puran
            member = DBOperator(Member).get_or_none(id=userId)
            if member:
                member.plan = plan
                #　現在の日付を登録
                member.subscriptionRegistrationDate = datetime.date.today()
                member.save()
                return JsonResponse({'status': 'プラン変更成功。'}, status=200)
            else:
                return JsonResponse({'status': '会員情報が見つかりません。'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'プラン変更に失敗しました。', 'error': str(e)}, status=400)
    else:
        return JsonResponse({'error': 'POST request required'}, status=405)

# profileSettings-ユーザー情報変更
# 取得した情報を元にユーザー情報を更新
# 取得する情報は、時による
def profileSettings(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            userId = data.get('userId')
            member_data = get_member_data(data)
            member = DBOperator.get_or_none(userId=userId)
            if member:
                for key, value in member_data.items():
                    setattr(member, key, value)
                member.save()
                return JsonResponse({'status': 'ユーザー情報変更成功'}, status=200)
            else:
                return JsonResponse({'status': '会員情報が見つかりません。'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'ユーザー情報変更に失敗しました。', 'error': str(e)}, status=400)
    else:
        return JsonResponse({'error': 'POST request required'}, status=405)
    
# deleteAccount-アカウント削除
@csrf_exempt
def deleteAccount(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            userid = data.get('userId')
            emailAddress = data.get('emailAddress')
            member = DBOperator(Member).get_or_none(id=userid, emailAddress=emailAddress)
            if member:
                member.delete()
                return JsonResponse({'status': 'アカウント削除成功'}, status=200)
            else:
                return JsonResponse({'status': '会員情報が見つかりません。'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'アカウント削除に失敗しました。', 'error': str(e)}, status=400)
    else:
        return JsonResponse({'error': 'POST request required'}, status=405)