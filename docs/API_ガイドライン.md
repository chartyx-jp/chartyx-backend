# Chartyx Backend API ガイドライン

## 概要

このドキュメントは、Chartyx BackendのREST APIの完全なリファレンスです。すべてのエンドポイント、リクエスト/レスポンス形式、認証要件について説明しています。

### ベースURL
```
http://localhost:8000/
```

### 認証方式
- **セッション認証**: Django標準のセッション認証を使用
- **CSRF保護**: POST/PUT/DELETE リクエストにはCSRFトークンが必要
- **権限レベル**:
  - `AllowAny`: 認証不要（パブリックAPI）
  - `IsAuthenticated`: ログイン必須

---

## ユーザーAPI (`/api/users/`)

### 1. CSRFトークン取得

**エンドポイント**: `GET /api/users/auth/csrf-token/`  
**認証**: 不要 (`AllowAny`)  
**説明**: CSRF保護のためのトークンを取得

#### レスポンス
```json
{
  "message": "csrfTokenをヘッダーにセットしました"
}
```

**ステータスコード**: `200 OK`

---

### 2. ユーザー情報取得

**エンドポイント**: `GET /api/users/auth/user-info/`  
**認証**: 必須 (`IsAuthenticated`)  
**説明**: ログイン中のユーザー情報を取得

#### レスポンス
```json
{
  "id": 1,
  "emailAddress": "user@example.com"
}
```

**ステータスコード**: 
- `200 OK`: 成功
- `401 Unauthorized`: 認証されていない

---

### 3. メールアドレス可用性確認

**エンドポイント**: `GET /api/users/auth/check-email/`  
**認証**: 不要 (`AllowAny`)  
**説明**: メールアドレスが既に登録済みかを確認

#### リクエストパラメータ
| パラメータ | 型 | 必須 | 説明 |
|-----------|----|----|------|
| `emailAddress` | string | ✓ | 確認するメールアドレス |

#### レスポンス
```json
{
  "exists": false,
  "message": "このメールアドレスは利用可能です。"
}
```

**ステータスコード**:
- `200 OK`: 成功
- `400 Bad Request`: メールアドレスが未提供
- `500 Internal Server Error`: サーバーエラー

---

### 4. サインアップ用OTP送信

**エンドポイント**: `POST /api/users/auth/send-otp-signup/`  
**認証**: 不要 (`AllowAny`)  
**説明**: 新規登録用のOTPをメールに送信

#### リクエストボディ
```json
{
  "emailAddress": "user@example.com"
}
```

#### レスポンス
```json
{
  "message": "認証コードを送信しました。メールをご確認ください。"
}
```

**ステータスコード**:
- `200 OK`: 送信成功
- `400 Bad Request`: メールアドレス未提供
- `409 Conflict`: 既に登録済みのメールアドレス
- `500 Internal Server Error`: 送信失敗

---

### 5. サインアップ用OTP検証

**エンドポイント**: `POST /api/users/auth/verify-otp-signup/`  
**認証**: 不要 (`AllowAny`)  
**説明**: サインアップ用OTPを検証

#### リクエストボディ
```json
{
  "emailAddress": "user@example.com",
  "otp": "123456"
}
```

#### レスポンス
```json
{
  "message": "認証が完了しました。サインアップを続行してください。",
  "status": "認証成功"
}
```

**ステータスコード**:
- `200 OK`: 検証成功
- `400 Bad Request`: パラメータ不足または検証失敗
- `500 Internal Server Error`: サーバーエラー

---

### 6. サインアップ

**エンドポイント**: `POST /api/users/auth/signup/`  
**認証**: 不要 (`AllowAny`)  
**説明**: 新規ユーザー登録（OTP検証済み前提）

#### リクエストボディ
```json
{
  "password": "securepassword123",
  "firstName": "太郎",
  "lastName": "田中",
  "gender": "male",
  "birthday": "1990-01-01",
  "phoneNumber": "090-1234-5678",
  "address": "東京都渋谷区"
}
```

#### レスポンス
成功時は空のレスポンス

**ステータスコード**:
- `201 Created`: 登録成功
- `400 Bad Request`: パラメータ不足または重複
- `403 Forbidden`: OTP認証未完了
- `500 Internal Server Error`: サーバーエラー

---

### 7. ログイン

**エンドポイント**: `POST /api/users/auth/login/`  
**認証**: 不要 (`AllowAny`)  
**説明**: ユーザーログイン

#### リクエストボディ
```json
{
  "emailAddress": "user@example.com",
  "password": "securepassword123"
}
```

#### レスポンス
```json
{
  "message": "ログイン成功。2段階認証のOTPを送信しました。",
  "id": 1
}
```

**ステータスコード**:
- `202 Accepted`: ログイン成功
- `400 Bad Request`: パラメータ不足
- `401 Unauthorized`: 認証失敗
- `500 Internal Server Error`: サーバーエラー

---

### 8. ログアウト

**エンドポイント**: `POST /api/users/logout/`  
**認証**: 必須 (`IsAuthenticated`)  
**説明**: ユーザーログアウト

#### レスポンス
成功時は空のレスポンス

**ステータスコード**:
- `200 OK`: ログアウト成功
- `500 Internal Server Error`: サーバーエラー

---

### 9. プラン設定更新

**エンドポイント**: `POST /api/users/plan-settings/`  
**認証**: 必須 (`IsAuthenticated`)  
**説明**: ユーザーのプラン設定を更新

#### リクエストボディ
```json
{
  "plan": "premium"
}
```

#### レスポンス
成功時は空のレスポンス

**ステータスコード**:
- `200 OK`: 更新成功
- `400 Bad Request`: プラン未指定
- `401 Unauthorized`: 認証されていない
- `404 Not Found`: ユーザーが見つからない
- `500 Internal Server Error`: サーバーエラー

---

### 10. プロフィール取得

**エンドポイント**: `GET /api/users/profile-settings/`  
**認証**: 必須 (`IsAuthenticated`)  
**説明**: ユーザーのプロフィール情報を取得

#### レスポンス
```json
{
  "member": {
    "firstName": "太郎",
    "lastName": "田中",
    "gender": "male",
    "birthday": "1990-01-01",
    "emailAddress": "user@example.com",
    "phoneNumber": "090-1234-5678",
    "address": "東京都渋谷区"
  }
}
```

**ステータスコード**:
- `200 OK`: 取得成功
- `401 Unauthorized`: 認証されていない
- `404 Not Found`: ユーザーが見つからない
- `500 Internal Server Error`: サーバーエラー

---

### 11. プロフィール更新

**エンドポイント**: `POST /api/users/profile-settings/`  
**認証**: 必須 (`IsAuthenticated`)  
**説明**: ユーザーのプロフィール情報を更新

#### リクエストボディ
```json
{
  "firstName": "次郎",
  "lastName": "佐藤",
  "gender": "male",
  "birthday": "1985-05-15",
  "phoneNumber": "080-9876-5432",
  "address": "大阪府大阪市",
  "emailAddress": "newuser@example.com",
  "password": "newpassword123"
}
```

#### レスポンス
成功時は空のレスポンス

**ステータスコード**:
- `200 OK`: 更新成功
- `400 Bad Request`: メールアドレス重複
- `401 Unauthorized`: 認証されていない
- `404 Not Found`: ユーザーが見つからない
- `500 Internal Server Error`: サーバーエラー

---

### 12. アカウント削除

**エンドポイント**: `DELETE /api/users/delete-account/`  
**認証**: 必須 (`IsAuthenticated`)  
**説明**: ログイン中のユーザーアカウントを削除

#### レスポンス
```json
{
  "message": "アカウントを削除しました。"
}
```

**ステータスコード**:
- `200 OK`: 削除成功
- `500 Internal Server Error`: サーバーエラー

---

## 株式API (`/api/stocks/`)

### 1. ティッカーデータ取得

**エンドポイント**: `GET /api/stocks/ticker/`  
**認証**: 必須 (`IsAuthenticated`)  
**説明**: 指定されたティッカーコードの株価データを取得

#### リクエストパラメータ
| パラメータ | 型 | 必須 | 説明 |
|-----------|----|----|------|
| `code` | string | ✓ | ティッカーコード（例: "7203"） |

#### レスポンス
```json
[
  {
    "Date": "2024-01-01",
    "Open": 2500.0,
    "High": 2550.0,
    "Low": 2480.0,
    "Close": 2520.0,
    "Volume": 1000000
  }
]
```

**ステータスコード**:
- `200 OK`: 取得成功
- `400 Bad Request`: ティッカーコード未指定
- `404 Not Found`: ティッカーが見つからない

---

### 2. ティッカー一覧取得

**エンドポイント**: `GET /api/stocks/tickers/`  
**認証**: 必須 (`IsAuthenticated`)  
**説明**: 利用可能な全ティッカーの一覧を取得

#### レスポンス
```json
[
  "7203",
  "6758",
  "8306",
  "9983"
]
```

**ステータスコード**:
- `200 OK`: 取得成功
- `404 Not Found`: ティッカーが見つからない

---

### 3. ティッカー検索

**エンドポイント**: `GET /api/stocks/search/`  
**認証**: 必須 (`IsAuthenticated`)  
**説明**: ティッカーコードの部分一致検索

#### リクエストパラメータ
| パラメータ | 型 | 必須 | 説明 |
|-----------|----|----|------|
| `query` | string | ✓ | 検索クエリ（部分一致） |

#### レスポンス
```json
[
  "7203",
  "7201"
]
```

**ステータスコード**:
- `200 OK`: 検索成功
- `400 Bad Request`: クエリ未指定
- `404 Not Found`: 該当するティッカーが見つからない

---

## エラーハンドリング

### 共通エラーレスポンス形式
```json
{
  "error": "エラーメッセージ"
}
```

### 主要なHTTPステータスコード
- `200 OK`: リクエスト成功
- `201 Created`: リソース作成成功
- `202 Accepted`: リクエスト受理（処理継続中）
- `400 Bad Request`: リクエストパラメータエラー
- `401 Unauthorized`: 認証が必要
- `403 Forbidden`: アクセス権限なし
- `404 Not Found`: リソースが見つからない
- `409 Conflict`: リソースの競合
- `500 Internal Server Error`: サーバー内部エラー

---

## 認証フロー

### サインアップフロー
1. `GET /api/users/auth/csrf-token/` - CSRFトークン取得
2. `GET /api/users/auth/check-email/` - メールアドレス確認
3. `POST /api/users/auth/send-otp-signup/` - OTP送信
4. `POST /api/users/auth/verify-otp-signup/` - OTP検証
5. `POST /api/users/auth/signup/` - サインアップ完了

### ログインフロー
1. `GET /api/users/auth/csrf-token/` - CSRFトークン取得
2. `POST /api/users/auth/login/` - ログイン

### セッション管理
- ログイン成功後、セッションCookieが設定される
- 認証が必要なAPIは自動的にセッション情報を確認
- `POST /api/users/logout/` でセッション終了

---

## 注意事項

1. **CSRF保護**: POST/PUT/DELETEリクエストには適切なCSRFトークンが必要
2. **セッション有効期限**: 一定時間非アクティブの場合、再ログインが必要
3. **OTP有効期限**: OTPには有効期限があり、期限切れの場合は再送信が必要
4. **データ形式**: 日付は`YYYY-MM-DD`形式、数値は適切な型で送信
5. **エラーログ**: サーバー側でエラーログが記録される

---

## 開発者向け情報

### テスト用エンドポイント
開発環境では、一部のAPIでCSRF保護が無効化されている場合があります。

### ログ出力
すべてのAPI呼び出しは適切なログレベルで記録されます：
- `INFO`: 正常な処理
- `WARNING`: 注意が必要な状況
- `ERROR`: エラー発生時

### パフォーマンス
- 株式データAPIは大量のデータを返す可能性があるため、適切なページネーションの実装を検討してください
- セッション情報はサーバー側で管理されるため、適切なセッション管理が重要です
