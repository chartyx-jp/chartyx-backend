# Chartyx Backend API 仕様書

このディレクトリには、Chartyx Backend APIのOpenAPI 3.0.3仕様書が含まれています。

## ファイル構成

- `api-spec.yaml` - メインのAPI仕様書（OpenAPI 3.0.3形式）
- `README.md` - このファイル（使用方法の説明）

## API仕様書の概要

### バージョン
- **API Version**: v1.0.0
- **OpenAPI Version**: 3.0.3

### 主要な機能

#### 1. ユーザーAPI (`/api/users/`)
- **認証・セッション管理**
  - CSRFトークン取得
  - ユーザー情報取得
  - メールアドレス可用性確認
  - OTP送信・検証
  - サインアップ・ログイン・ログアウト

- **ユーザー管理**
  - プラン設定更新
  - プロフィール取得・更新
  - アカウント削除

#### 2. 株式API (`/api/stocks/`)
- **基本データ**
  - ティッカーデータ取得
  - ティッカー一覧取得
  - ティッカー検索

#### 3. テクニカル指標API (`/api/stocks/technical/`)
- **SMA** - 単純移動平均
- **EMA** - 指数移動平均
- **RSI** - 相対力指数
- **MACD** - 移動平均収束拡散法
- **ボリンジャーバンド**

### 認証方式

- **セッション認証**: Django標準のセッション認証
- **CSRF保護**: POST/PUT/DELETEリクエストにはCSRFトークンが必要
- **権限レベル**:
  - `AllowAny`: 認証不要
  - `IsAuthenticated`: ログイン必須

## 仕様書の使用方法

### 1. Swagger UIでの表示

```bash
# Swagger UIを使用してAPI仕様書を表示
npx swagger-ui-serve docs/api-spec.yaml
```

### 2. オンラインエディタでの編集

[Swagger Editor](https://editor.swagger.io/) にYAMLファイルの内容をコピー&ペーストして編集・プレビューできます。

### 3. コード生成

OpenAPI Generatorを使用してクライアントコードを生成できます：

```bash
# JavaScript/TypeScriptクライアント生成
openapi-generator-cli generate -i docs/api-spec.yaml -g typescript-axios -o generated/typescript-client

# Pythonクライアント生成
openapi-generator-cli generate -i docs/api-spec.yaml -g python -o generated/python-client
```

### 4. APIテスト

Postmanなどのツールでインポートしてテストできます：

1. Postmanを開く
2. Import → File → `api-spec.yaml` を選択
3. コレクションが自動生成される

## 開発者向け情報

### 仕様書の更新

API実装に変更があった場合は、以下の手順で仕様書を更新してください：

1. `docs/api-spec.yaml` を編集
2. 変更内容をテスト
3. バージョン番号を適切に更新（セマンティックバージョニング）

### バージョニング

セマンティックバージョニング（`MAJOR.MINOR.PATCH`）を採用：

- **MAJOR**: 互換性のない変更
- **MINOR**: 後方互換性のある機能追加
- **PATCH**: 後方互換性のあるバグ修正

### 注意事項

1. **CSRF保護**: 本仕様書ではCSRF保護ありで記載していますが、開発環境では一部無効化されている場合があります
2. **認証**: セッション認証を使用しているため、ログイン後のセッションCookieが必要です
3. **エラーハンドリング**: 統一されたエラーレスポンス形式を使用しています

## サポート

- **GitHub**: [chartyx-backend](https://github.com/chartyx-jp/chartyx-backend)
- **Issues**: バグ報告や機能要望はGitHub Issuesまで

## ライセンス

MIT License
