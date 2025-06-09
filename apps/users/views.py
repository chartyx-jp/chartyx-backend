import os
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

import json
from .models import Member
from apps.common.db_operator import DBOperator
import random
import hashlib
import datetime
import secrets
import string
import time
# import pyotp

# ----
from email.header import Header
from email.mime.text import MIMEText
import smtplib

# 環境変数からメール設定を取得
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD')
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
otp_storage = {}

db_operator = DBOperator()
# import pyotp

# 会員情報の取得
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

def generate_otp(length=6):
    otp = ''.join(secrets.choice(string.digits) for _ in range(length))
    return otp
otp = generate_otp()
print(f"生成されたOTP: {otp}")

def send_otp_email(receiver_email, otp):
    subject = "2段階認証コード"
    message = f"あなたの2段階認証コードは {otp} です。"
    from_email = settings.DEFAULT_FROM_EMAIL
    try:
        send_mail(
            subject,
            message,  # ← ここにMIMETextではなく文字列を渡す
            from_email,
            [receiver_email],
            fail_silently=False,
        )
        print(f"OTPを {receiver_email} に送信しました。")
        return True
    except Exception as e:
        print(f"メール送信エラー: {e}")
        return False

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
                # ユーザー認証は成功、ここから2段階認証のフロー
                otp = generate_otp()
                
                # OTPを一時保存 (例: 5分間有効)
                otp_expiration_time = time.time() + 300 # 300秒 = 5分
                otp_storage[member.id] = {'otp': otp, 'expires_at': otp_expiration_time}
                print(otp_storage)
                # OTPをメールで送信
                # member.emailAddress が登録されているメールアドレスだと仮定
                print(emailAddress)
                if send_otp_email(emailAddress, otp):
                    # ここではまだログイン完了ではない。OTP入力待ちの状態を示す
                    return JsonResponse({'status': 'OTP送信完了', 'member_id': member.id}, status=202) # 202 Accepted
                else:
                    return JsonResponse({'status': 'OTPメール送信失敗', 'error': 'メール送信中にエラーが発生しました。'}, status=500)
            else:
                return JsonResponse({'status': 'ログイン失敗', 'error':'メールアドレスまたはパスワードが違うよ'}, status=401)
        except Exception as e:
            return JsonResponse({'status': 'ログインに失敗しました。', 'error': str(e)}, status=400)
    else:
        return JsonResponse({'error': 'POST request required'}, status=405)

#logout-ログアウト
@csrf_exempt
def logout(request):
    if request.method == 'POST':
        try:
            if 'member_id' in request.session:
                del request.session['member_id']
            return JsonResponse({'status': 'ログアウト成功'}, status=200)
        except Exception as e:
            return JsonResponse({'status': 'ログアウトに失敗しました。', 'error': str(e)}, status=400)
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
def sendAuthCodeEmail(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            member_id = data.get('member_id')
            entered_otp = data.get('otp')

            if member_id not in otp_storage:
                return JsonResponse({'status': '検証失敗', 'error': '無効なOTP検証リクエストです。'}, status=400)

            stored_data = otp_storage[member_id]
            stored_otp = stored_data['otp']
            expires_at = stored_data['expires_at']

            # OTPの有効期限チェック
            if time.time() > expires_at:
                del otp_storage[member_id] # 期限切れのOTPを削除
                return JsonResponse({'status': '検証失敗', 'error': 'OTPの有効期限が切れました。再度ログインしてください。'}, status=400)

            # OTPの一致チェック
            if entered_otp == stored_otp:
                # OTPが正しい場合、セッションにmember_idを設定してログイン完了
                request.session['member_id'] = member_id
                del otp_storage[member_id]
                return redirect('/top') # ページリンクは仮だよ
            else:
                return redirect('/sendAuthCodeEmail')
        except Exception as e:
            return JsonResponse({'status': 'OTP検証に失敗しました。', 'error': str(e)}, status=400)
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
def profileSettings(request):
    if request.method == 'GET':
        # セッションやクエリパラメータからuserIdを取得（例: ?userId=xxx）
        userId = request.GET.get('userId')
        if not userId:
            return JsonResponse({'error': 'userIdが指定されていません。'}, status=400)
        member = DBOperator(Member).get_or_none(id=userId)
        if member:
            # 既存のユーザー情報を返す
            member_data = {
                'firstName': member.firstName,
                'lastName': member.lastName,
                'gender': member.gender,
                'birthday': member.birthday,
                'emailAddress': member.emailAddress,
                'phoneNumber': member.phoneNumber,
                'address': member.address,
                # パスワードは返さないのが一般的
            }
            return JsonResponse({'member': member_data}, status=200)
        else:
            return JsonResponse({'error': '会員情報が見つかりません。'}, status=404)
        
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            userId = data.get('userId')
            member_data = get_member_data(data)
            member = DBOperator.get_or_none(userId=userId)
            if member:
                update_fields = ['firstName', 'lastName', 'gender', 'birthday', 'emailAddress', 'phoneNumber', 'address']
                for field in update_fields:
                    if field in data and data[field] is not None:
                        setattr(member, field, data[field])
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
    
# user情報ページ
# @csrf_exempt
# def myPage(request):
#     if request.method == 'POST':
#         try:
