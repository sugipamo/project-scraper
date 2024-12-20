# Project Scraper

## プロジェクト概要

このプロジェクトは、ユーザーが指定したURLから必要なデータをスクレイピングするためのツールです。動的なサイトにも対応できるよう、SeleniumとLLM（大規模言語モデル）を使用しています。スクレイピングしたデータは効率的にキャッシュされ、再利用可能です。

## 主な機能

- **URLとデータの指定**: ユーザーはフォームを通じて、スクレイピングしたいURLと取得したいデータを指定します。
- **Seleniumの使用**: `selenium-standalone`イメージを使用して、ヘッドレスブラウザで自動操作を行います。
- **インタラクティブな情報取得**: Google Gemini APIを用いて、HTMLから必要なデータを抽出します。
- **効率的なキャッシュ機能**: 
  - 取得したデータはJSON形式で永続化されます
  - LRU（Least Recently Used）方式でキャッシュを管理
  - キャッシュの有効期限と最大サイズを設定可能

## 必要な環境

- Docker
- Python 3.8以上
- Google Cloud プ��ジェクト
- Vertex AI API の有効化
- k3s（Kubernetes環境での実行時）

## 依存パッケージ

詳細は`requirements.txt`を参照してください。主な依存関係：
- selenium
- google-cloud-aiplatform
- webdriver-manager

## プロジェクトのセットアップ

1. リポジトリをクローンします：
   ```bash
   git clone https://github.com/yourusername/project-scraper.git
   cd project-scraper
   ```

2. 必要なディレクトリを作成します：
   ```bash
   mkdir -p credentials data
   ```

3. 環境変数を設定します：
   ```bash
   cp .env.example .env
   # .envファイルを編集して適切な値を設定
   ```

4. Google Cloud認証情報を配置します：
   ```bash
   # サービスアカウントキーを credentials/ ディレクトリに配置
   cp /path/to/your/service-account.json credentials/
   ```

5. 依存パッケージをインストールします：
   ```bash
   pip install -r requirements.txt
   ```

## ローカルでの実行

1. Dockerでselenium-standaloneを起動します：
   ```bash
   docker-compose up -d
   ```

2. スクリプトを実行します：
   ```bash
   python src/main.py
   ```

## k3sでの実行

1. Secretの作成：
   ```bash
   # Google Cloud認証情報のSecretを作成
   kubectl create secret generic google-credentials \
     --from-file=credentials.json=credentials/service-account.json

   # 環境変数用のSecretを作成
   kubectl apply -f k8s/secret.yaml
   ```

2. PersistentVolumeClaimの作成：
   ```bash
   kubectl apply -f k8s/pvc.yaml
   ```

3. Deploymentの作成：
   ```bash
   kubectl apply -f k8s/deployment.yaml
   ```

4. ログの確認：
   ```bash
   kubectl logs -f deployment/scraper
   ```

## ディレクトリ構造

```
project-scraper/
├── src/
│   ├── main.py
│   └── cache.py
├── k8s/
│   ├── deployment.yaml
│   ├── secret.yaml
│   └── pvc.yaml
├── credentials/        # Google Cloud認証情報（.gitignore対象）
│   └── service-account.json
├── data/              # キャッシュデータ（.gitignore対象）
│   └── cache.json
├── .env               # 環境変数（.gitignore対象）
├── .env.example       # 環境変数のテンプレート
├── requirements.txt
└── README.md
```

## 設定

- キャッシュの設定（`src/cache.py`）：
  - `expiration_hours`: キャッシュの有効期限（デフォルト24時間）
  - `max_size`: キャッシュの最大エントリ数（デフォルト1000）
  - `cache_file`: キャッシュファイルの保存先（デフォルト"cache.json"）

- Selenium設定（`src/main.py`）：
  - `wait_timeout`: ページ読み込みのタイムアウト時間（デフォルト10秒）

## エラーハンドリング

スクリプトは以下の状況で適切なエラーメッセージを表示します：
- Seleniumドライバーの初期化エラー
- ページ読み込みのタイムアウト
- ブラウザ操作エラー
- キャッシュの読み書きエラー

## 注意事項

- スクレイピング対象のウェブサイトの利用規約を必ず確認してください。
- 過度なリクエストを避けるため、適切な間隔でアクセスしてください。
- Google Cloud の利用料金に注意してください。
- k3s環境では、PersistentVolumeの設定が適切に行われていることを確認してください。

## 認証情報の管理

### Gemini APIキーの取得

1. Google AI Studioでキーを取得：
   - [Google AI Studio](https://makersuite.google.com/app/apikey)にアクセス
   - 「APIキーの作成」をクリック
   - 生成されたAPIキーをコピー

### ローカル開発環境

1. 環境変数の設定：
   ```bash
   # .env.exampleをコピーして.envを作成
   cp .env.example .env
   
   # .envファイルを編集してAPIキーを設定
   # GEMINI_API_KEY=your-api-key-here の行を実際のキーで置き換え
   ```

### k3s環境（本番環境）

1. APIキーをSecretとして登録：
   ```bash
   # 環境変数用のSecretを作成
   kubectl apply -f k8s/secret.yaml
   
   # Secretを編集してAPIキーを設定
   kubectl edit secret scraper-secrets
   ```

2. Secretsの確認：
   ```bash
   # 環境変数Secretの確認
   kubectl get secret scraper-secrets
   ```

### セキュリティに関する注意事項

- APIキーは絶対にGitにコミットしないでください
- `.env`ファイルはGitにコミットしないでください
- APIキーは定期的にローテーションすることを推奨します
- APIキーの使用状況を定期的に監視してください
- 本番環境では別のAPIキーを使用することを推奨します
