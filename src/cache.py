import json
from datetime import datetime, timedelta
import os
from collections import OrderedDict
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

class Cache:
    def __init__(self):
        # 環境変数の読み込み
        load_dotenv()
        
        # 設定の読み込み
        self.expiration_hours = int(os.getenv('CACHE_EXPIRATION_HOURS', '24'))
        self.max_size = int(os.getenv('CACHE_MAX_SIZE', '1000'))
        
        # キャッシュファイルのパス設定
        app_dir = os.getenv('APP_DIR', os.getcwd())
        cache_file = os.getenv('CACHE_FILE_PATH', 'cache.json')
        if not os.path.isabs(cache_file):
            # 相対パスの場合は、APP_DIRからの相対パスとして扱う
            self.cache_file = os.path.join(app_dir, 'data', cache_file)
        else:
            self.cache_file = cache_file
            
        logger.info(f"キャッシュファイルのパス: {self.cache_file}")
        
        # キャッシュディレクトリの作成
        cache_dir = os.path.dirname(self.cache_file)
        if cache_dir:  # ディレクトリパスが空でない場合のみ作成
            os.makedirs(cache_dir, exist_ok=True)
            logger.info(f"キャッシュディレクトリを作成しました: {cache_dir}")
        
        self.cache = OrderedDict()
        self.load_cache()

    def load_cache(self):
        """キャッシュファイルから永続化データを読み込む"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, value in data.items():
                        value['timestamp'] = datetime.fromisoformat(value['timestamp'])
                    self.cache = OrderedDict(data)
                # 期限切れのキャッシュを削除
                self._cleanup_expired()
                logger.info(f"キャッシュを読み込みました: {len(self.cache)}件")
            except Exception as e:
                logger.error(f"キャッシュの読み込み中にエラーが発生しました: {e}")
        else:
            logger.info("キャッシュファイルが存在しないため、新規作成します")

    def save_cache(self):
        """キャッシュデータをファイルに永続化"""
        try:
            cache_data = {k: {'data': v['data'], 'timestamp': v['timestamp'].isoformat()}
                         for k, v in self.cache.items()}
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            logger.info(f"キャッシュを保存しました: {len(self.cache)}件")
        except Exception as e:
            logger.error(f"キャッシュの保存中にエラーが発生しました: {e}")

    def _cleanup_expired(self):
        """期限切れのキャッシュエントリを削除"""
        now = datetime.now()
        expired_keys = [
            key for key, value in self.cache.items()
            if now - value['timestamp'] > timedelta(hours=self.expiration_hours)
        ]
        for key in expired_keys:
            del self.cache[key]
        if expired_keys:
            logger.info(f"期限切れのキャッシュを削除しました: {len(expired_keys)}件")
            self.save_cache()

    def set(self, key, value):
        """
        キャッシュにデータを保存
        
        Args:
            key (str): キャッシュのキー（URL）
            value (str): キャッシュする値（HTMLデータ）
        """
        # キャッシュサイズの制限を確認
        while len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)  # 最も古いアイテムを削除

        self.cache[key] = {
            'data': value,
            'timestamp': datetime.now()
        }
        # 新しいアイテムを最後に移動
        self.cache.move_to_end(key)
        self.save_cache()
        logger.info(f"キャッシュにデータを保存しました: {key}")

    def get(self, key):
        """
        キャッシュからデータを取得
        
        Args:
            key (str): キャッシュのキー（URL）
        
        Returns:
            str or None: キャッシュされたデータ、または期限切れ/未存在の場合はNone
        """
        if key not in self.cache:
            return None

        cached_data = self.cache[key]
        if datetime.now() - cached_data['timestamp'] > timedelta(hours=self.expiration_hours):
            del self.cache[key]
            self.save_cache()
            logger.info(f"期限切れのキャッシュを削除しました: {key}")
            return None

        # アクセスされたアイテムを最後に移動
        self.cache.move_to_end(key)
        logger.info(f"キャッシュからデータを取得しました: {key}")
        return cached_data['data']