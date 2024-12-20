from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import requests
import json
from cache import Cache
import os
import csv
from datetime import datetime
from dotenv import load_dotenv
import time
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import logging
import traceback

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Scraper:
    def __init__(self):
        try:
            self.driver = None
            self.cache = Cache()
            self.wait_timeout = 10
            
            # 環境変数の読み込み
            load_dotenv()
            logger.info("環境変数を読み込みました")
            
            # ベースディレクトリの設定
            self.base_dir = os.getenv('APP_DIR')
            if not self.base_dir:
                self.base_dir = os.getcwd()
                logger.warning(f"APP_DIRが設定されていません。カレントディレクトリを使用します: {self.base_dir}")
            else:
                logger.info(f"アプリケーションディレクトリ: {self.base_dir}")
            
            # データディレクトリの設定と作成
            self.data_dir = os.path.join(self.base_dir, 'data')
            os.makedirs(self.data_dir, exist_ok=True)
            logger.info(f"データディレクトリを作成しました: {self.data_dir}")
            
            # API設定の読み込み
            self.api_key = os.getenv('GEMINI_API_KEY')
            if not self.api_key:
                raise ValueError("GEMINI_API_KEYが設定されていません")
            logger.info("API設定を読み込みました")
            
            self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={self.api_key}"
            
            # レート制限の設定
            self.rate_limit = float(os.getenv('API_RATE_LIMIT_SECONDS', '1.0'))
            self.last_request_time = 0
            
            # リトライ設定
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504]
            )
            self.session = requests.Session()
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self.session.mount("https://", adapter)
            self.session.mount("http://", adapter)
        except Exception as e:
            logger.error(f"初期化中にエラーが発生しました: {str(e)}")
            logger.error(f"エラーの詳細:\n{traceback.format_exc()}")
            raise

    def setup_driver(self):
        """Seleniumドライバーの初期化"""
        max_retries = 5
        retry_interval = 3
        
        for attempt in range(max_retries):
            try:
                options = webdriver.ChromeOptions()
                options.add_argument('--headless')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                selenium_url = os.getenv('SELENIUM_URL', 'http://localhost:4444/wd/hub')
                logger.info(f"Seleniumに接続を試みます（試行{attempt + 1}/{max_retries}）: {selenium_url}")
                
                self.driver = webdriver.Remote(
                    command_executor=selenium_url,
                    options=options
                )
                logger.info("Seleniumドライバの初期化が完了しました")
                return
                
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Seleniumへの接続に失敗しました。{retry_interval}秒後に再試行します: {str(e)}")
                    time.sleep(retry_interval)
                else:
                    logger.error(f"Seleniumドライバーの初期化に失敗しました: {str(e)}")
                    logger.error(f"エラーの詳細:\n{traceback.format_exc()}")
                    raise Exception(f"ドライバーの初期化に失敗しました（{max_retries}回試行）: {e}")

    def cleanup(self):
        """ドライバーのクリーンアップ処理"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Seleniumドライバーをクリーンアップしました")
            except Exception as e:
                logger.error(f"クリーンアップ中にエラーが発生しました: {str(e)}")
                logger.error(f"エラーの詳細:\n{traceback.format_exc()}")
            finally:
                self.driver = None
        if self.session:
            self.session.close()
            logger.info("HTTPセッションを���リーンアップしまた")

    def process_csv(self, input_file='query.csv'):
        """CSVファイルからクエリを読み込んで処理"""
        try:
            # 入力ファイルのパスを解決
            input_path = os.path.join(self.base_dir, input_file)
            logger.info(f"入力ファイルのパス: {input_path}")
            logger.info(f"カレントディレクトリ: {os.getcwd()}")
            logger.info(f"ディレクトリ内容: {os.listdir(self.base_dir)}")
            
            if not os.path.exists(input_path):
                raise FileNotFoundError(f"クエリファイルが見つりません: {input_path}")
            
            # 結果を保存するための出力ファイル名を生成
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = os.path.join(self.data_dir, f'result_{timestamp}.csv')
            
            # 結果を格納するリスト
            results = []
            total_rows = 0
            
            # CSVファイルを読み込み
            logger.info(f"クエリファイルを読み込み中: {input_path}")
            with open(input_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)  # 全行を読み込んでリスト化
                total_rows = len(rows)
                logger.info(f"読み込んだ行数: {total_rows}")
                
                # 各行を処理
                for index, row in enumerate(rows, 1):
                    logger.info(f"処理中: {index}/{total_rows}")
                    try:
                        result = self.scrape(row['url'], row['target_data'])
                        results.append({
                            'url': row['url'],
                            'target_data': row['target_data'],
                            'result': result,
                            'status': 'success'
                        })
                    except Exception as e:
                        logger.error(f"エラー（{row['url']}）: {str(e)}")
                        logger.error(f"エラーの詳細:\n{traceback.format_exc()}")
                        results.append({
                            'url': row['url'],
                            'target_data': row['target_data'],
                            'result': str(e),
                            'status': 'error'
                        })
            
            # 結果をCSVファイルに保存
            logger.info(f"結果を保存中: {output_file}")
            with open(output_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['url', 'target_data', 'result', 'status'])
                writer.writeheader()
                writer.writerows(results)
            
            # 成功・エラー数を集計
            success_count = sum(1 for r in results if r['status'] == 'success')
            error_count = sum(1 for r in results if r['status'] == 'error')
            
            logger.info(f"処理完了: 成功={success_count}, エラー={error_count}")
            logger.info(f"結果は {output_file} に保存されました")
            
            return output_file
            
        except Exception as e:
            logger.error(f"CSVの処理中にエラーが発生しました: {str(e)}")
            logger.error(f"エラーの詳細:\n{traceback.format_exc()}")
            raise

    def scrape(self, url, target_data):
        """
        指定されたURLからデータをスクレイピング
        
        Args:
            url (str): スクレイピング対象のURL
            target_data (str): 抽出対象のデータの説明
            
        Returns:
            str: 抽出されたデータ
        """
        try:
            # キャッシュをチェック
            cached_html = self.cache.get(url)
            if cached_html:
                logger.info(f"キャッシュからデータを取得: {url}")
                html_content = cached_html
            else:
                logger.info(f"ページを読み込み中: {url}")
                self.driver.get(url)
                
                # ページの読み込みを待機
                WebDriverWait(self.driver, self.wait_timeout).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # HTMLを取得
                html_content = self.driver.page_source
                
                # キャッシュに保存
                self.cache.set(url, html_content)
                logger.info(f"ページをキャッシュに保存: {url}")
            
            # Gemini APIを使用してデータを抽出
            prompt = f"""
            HTMLコンテンツから特定の情報を抽出してください。

            抽出対象: {target_data}

            以下の条件に従って抽出してください：
            1. 指定された抽出対象に関連する情報のみを抽出
            2. 余分な説明や装飾は不要
            3. 可能な限り簡潔に
            4. 複数の結果がある場合はリストとして返す

            HTML:
            {html_content}
            """
            
            logger.info("APIリクエストの詳細:")
            logger.info(f"URL: {self.api_url}")
            logger.info("プロンプト内容:")
            logger.info(prompt)
            
            max_retries = 3
            base_wait_time = 2  # 基本待機時間（秒）
            
            for attempt in range(max_retries):
                try:
                    # APIリクエストを作成
                    headers = {
                        "Content-Type": "application/json"
                    }
                    
                    data = {
                        "contents": [{
                            "parts": [{
                                "text": prompt
                            }]
                        }]
                    }
                    
                    logger.info("リクエストボディ:")
                    logger.info(json.dumps(data, indent=2, ensure_ascii=False))
                    
                    # レート制限を考慮
                    time_since_last_request = time.time() - self.last_request_time
                    if time_since_last_request < self.rate_limit:
                        sleep_time = self.rate_limit - time_since_last_request
                        logger.info(f"レート制限のため {sleep_time:.2f} 秒待機")
                        time.sleep(sleep_time)
                    
                    # APIリクエストを送信
                    response = self.session.post(
                        self.api_url,
                        headers=headers,
                        json=data
                    )
                    self.last_request_time = time.time()
                    
                    logger.info(f"APIレスポンス（ステータスコード: {response.status_code}）:")
                    logger.info(json.dumps(response.json(), indent=2, ensure_ascii=False))
                    
                    if response.status_code == 200:
                        result = response.json()
                        extracted_text = result['candidates'][0]['content']['parts'][0]['text']
                        logger.info(f"データ抽出成功: {url}")
                        logger.info(f"抽出結果: {extracted_text}")
                        return extracted_text.strip()
                    elif response.status_code == 429:
                        wait_time = base_wait_time * (2 ** attempt)  # 指数バックオフ
                        logger.warning(f"APIレート制限に達しました。{wait_time}秒待機後に再試行します（試行{attempt + 1}/{max_retries}）")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(f"API呼び出しエラー: {response.status_code} - {response.text}")
                        
                except Exception as e:
                    if attempt < max_retries - 1:
                        wait_time = base_wait_time * (2 ** attempt)
                        logger.warning(f"APIリクエスト失敗。{wait_time}秒待機後に再試行します: {str(e)}")
                        time.sleep(wait_time)
                    else:
                        raise
            
            raise Exception(f"APIリクエストが{max_retries}回失敗しました")
                
        except TimeoutException:
            logger.error(f"ページの読み込みがタイムアウト: {url}")
            raise
        except Exception as e:
            logger.error(f"スクレイピング中にエラーが発生: {str(e)}")
            logger.error(f"エラーの詳細:\n{traceback.format_exc()}")
            raise

if __name__ == "__main__":
    scraper = None
    try:
        logger.info("スクレイパーを初期化中...")
        scraper = Scraper()
        
        logger.info("Seleniumドライバーを設定中...")
        scraper.setup_driver()
        
        # コマンドライン引数またはデフォルトのファイル名を使用
        input_file = os.getenv('QUERY_FILE', 'query.csv')
        logger.info(f"入力ファイル: {input_file}")
        
        output_file = scraper.process_csv(input_file)
        logger.info(f"スクレイピングが完了しました。結果は {output_file} に保存されています。")
        
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        logger.error(f"エラーの詳細:\n{traceback.format_exc()}")
    finally:
        if scraper:
            scraper.cleanup()