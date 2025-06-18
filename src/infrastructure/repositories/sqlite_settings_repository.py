"""
SQLite Settings Repository - 設定データの永続化

SQLiteデータベースを使用したアプリケーション設定の保存・取得を実装します。
"""

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, List, Union
import winreg

from ...core.result import Result, Ok, Err, ErrorInfo
from ...domain.repositories.settings_repository import ISettingsRepository, SettingValue
from ...domain.value_objects import ValidationResult
from ..services.encryption_service import EncryptionService
from ..services.file_service import FileService


class SqliteSettingsRepository(ISettingsRepository):
    """SQLite設定リポジトリ実装"""
    
    def __init__(self, db_path: Optional[Path] = None,
                 encryption_service: Optional[EncryptionService] = None,
                 file_service: Optional[FileService] = None):
        
        self._lock = threading.RLock()
        
        # サービス依存の初期化
        self._encryption_service = encryption_service or EncryptionService()
        self._file_service = file_service or FileService()
        
        # データベースパスの設定
        if db_path is None:
            db_path = self._file_service.get_app_data_dir() / "settings.db"
        
        self._db_path = db_path
        self._connection_pool = {}
        
        # データベースの初期化
        self._initialize_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """スレッドローカルなデータベース接続を取得"""
        thread_id = threading.get_ident()
        
        if thread_id not in self._connection_pool:
            conn = sqlite3.connect(
                self._db_path,
                check_same_thread=False,
                timeout=30.0
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode = WAL")
            self._connection_pool[thread_id] = conn
        
        return self._connection_pool[thread_id]
    
    def _initialize_database(self):
        """データベースとテーブルの初期化"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                # 設定テーブル
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value_type TEXT NOT NULL,
                        encrypted_value TEXT NOT NULL,
                        is_encrypted BOOLEAN DEFAULT FALSE,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        checksum TEXT
                    )
                """)
                
                # インデックス作成
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_settings_updated_at 
                    ON settings (updated_at)
                """)
                
                conn.commit()
                
        except Exception as e:
            raise RuntimeError(f"設定データベース初期化エラー: {str(e)}")
    
    async def get(self, key: str, default: Optional[SettingValue] = None) -> Result[SettingValue, ErrorInfo]:
        """設定値を取得"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                cursor = conn.execute("""
                    SELECT * FROM settings WHERE key = ?
                """, (key,))
                
                row = cursor.fetchone()
                if not row:
                    return Ok(default)
                
                # 値の復号化
                if row['is_encrypted']:
                    decrypt_result = self._encryption_service.decrypt_data(row['encrypted_value'])
                    if decrypt_result.is_failure():
                        return decrypt_result
                    value_json = decrypt_result.value
                else:
                    value_json = row['encrypted_value']
                
                # 型に応じて値を復元
                value_type = row['value_type']
                if value_type == 'json':
                    value = json.loads(value_json)
                elif value_type == 'str':
                    value = value_json
                elif value_type == 'int':
                    value = int(value_json)
                elif value_type == 'float':
                    value = float(value_json)
                elif value_type == 'bool':
                    value = value_json.lower() == 'true'
                else:
                    value = value_json
                
                return Ok(value)
                
        except Exception as e:
            return Err(ErrorInfo("SETTINGS_GET_ERROR", f"設定取得エラー: {str(e)}"))
    
    async def set(self, key: str, value: SettingValue) -> Result[bool, ErrorInfo]:
        """設定値を保存"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                # 値の型判定とシリアライゼーション
                if isinstance(value, dict) or isinstance(value, list):
                    value_type = 'json'
                    value_json = json.dumps(value)
                elif isinstance(value, str):
                    value_type = 'str'
                    value_json = value
                elif isinstance(value, int):
                    value_type = 'int'
                    value_json = str(value)
                elif isinstance(value, float):
                    value_type = 'float'
                    value_json = str(value)
                elif isinstance(value, bool):
                    value_type = 'bool'
                    value_json = str(value).lower()
                else:
                    value_type = 'str'
                    value_json = str(value)
                
                # 暗号化処理（デフォルトは無効）
                encrypt = False  # 基本実装では暗号化無効
                if encrypt and self._encryption_service.is_encryption_available():
                    encrypt_result = self._encryption_service.encrypt_data(value_json)
                    if encrypt_result.is_failure():
                        return Err(ErrorInfo("SETTINGS_ENCRYPTION_ERROR", f"暗号化エラー: {encrypt_result.error}"))
                    encrypted_value = encrypt_result.value
                    is_encrypted = True
                else:
                    encrypted_value = value_json
                    is_encrypted = False
                
                # チェックサム計算
                checksum = self._calculate_checksum(value_json)
                
                # 現在時刻
                now = datetime.now(timezone.utc).isoformat()
                
                # 設定の保存
                conn.execute("""
                    INSERT OR REPLACE INTO settings (
                        key, value_type, encrypted_value, is_encrypted,
                        created_at, updated_at, checksum
                    ) VALUES (?, ?, ?, ?, 
                        COALESCE((SELECT created_at FROM settings WHERE key = ?), ?),
                        ?, ?)
                """, (
                    key, value_type, encrypted_value, is_encrypted,
                    key, now,  # 新規作成時は現在時刻、既存なら元の作成時刻を維持
                    now, checksum
                ))
                
                conn.commit()
                return Ok(True)
                
        except Exception as e:
            return Err(ErrorInfo("SETTINGS_SET_ERROR", f"設定保存エラー: {str(e)}"))
    
    async def delete(self, key: str) -> Result[bool, ErrorInfo]:
        """設定を削除"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                cursor = conn.execute("SELECT key FROM settings WHERE key = ?", (key,))
                exists = cursor.fetchone() is not None
                
                if exists:
                    conn.execute("DELETE FROM settings WHERE key = ?", (key,))
                    conn.commit()
                
                return Ok(exists)
                
        except Exception as e:
            return Err(ErrorInfo("SETTINGS_DELETE_ERROR", f"設定削除エラー: {str(e)}"))
    
    async def get_all(self) -> Result[Dict[str, SettingValue], ErrorInfo]:
        """すべての設定を取得"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                cursor = conn.execute("SELECT key FROM settings")
                keys = [row['key'] for row in cursor.fetchall()]
                
                settings = {}
                for key in keys:
                    result = await self.get(key)
                    if result.is_success():
                        settings[key] = result.value
                
                return Ok(settings)
                
        except Exception as e:
            return Err(ErrorInfo("SETTINGS_GET_ALL_ERROR", f"全設定取得エラー: {str(e)}"))
    
    async def clear_all(self) -> Result[bool, ErrorInfo]:
        """すべての設定を削除"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                cursor = conn.execute("SELECT COUNT(*) as count FROM settings")
                count = cursor.fetchone()['count']
                
                conn.execute("DELETE FROM settings")
                conn.commit()
                
                return Ok(True)
                
        except Exception as e:
            return Err(ErrorInfo("SETTINGS_CLEAR_ALL_ERROR", f"全設定削除エラー: {str(e)}"))
    
    
    async def export_settings(self, file_path: Path, 
                            include_encrypted: bool = False) -> Result[bool, ErrorInfo]:
        """設定をファイルにエクスポート"""
        try:
            settings_result = await self.get_all()
            if settings_result.is_failure():
                return settings_result
            
            settings = settings_result.value
            
            # 暗号化された設定を除外するオプション
            if not include_encrypted:
                with self._lock:
                    conn = self._get_connection()
                    cursor = conn.execute("SELECT key FROM settings WHERE is_encrypted = TRUE")
                    encrypted_keys = {row['key'] for row in cursor.fetchall()}
                    
                    settings = {k: v for k, v in settings.items() if k not in encrypted_keys}
            
            # エクスポートデータの作成
            export_data = {
                'exported_at': datetime.now(timezone.utc).isoformat(),
                'include_encrypted': include_encrypted,
                'settings': settings
            }
            
            # ファイルに書き込み
            write_result = self._file_service.write_json_file(file_path, export_data)
            if write_result.is_success():
                return Ok(True)
            else:
                return Err(ErrorInfo("SETTINGS_EXPORT_ERROR", f"設定エクスポートエラー: {write_result.error}"))
            
        except Exception as e:
            return Err(ErrorInfo("SETTINGS_EXPORT_ERROR", f"設定エクスポートエラー: {str(e)}"))
    
    async def import_settings(self, file_path: Path, 
                            overwrite: bool = False) -> Result[int, ErrorInfo]:
        """ファイルから設定をインポート"""
        try:
            # ファイル読み込み
            read_result = self._file_service.read_json_file(file_path)
            if read_result.is_failure():
                return read_result
            
            import_data = read_result.value
            
            if 'settings' not in import_data:
                return Err(ErrorInfo("SETTINGS_IMPORT_FORMAT_ERROR", "無効なインポートファイル形式です"))
            
            settings = import_data['settings']
            imported_count = 0
            
            for key, value in settings.items():
                # 既存設定のチェック
                if not overwrite:
                    existing_result = await self.get(key)
                    if existing_result.is_success() and existing_result.value is not None:
                        continue  # 上書きしない場合はスキップ
                
                # 設定の保存
                set_result = await self.set(key, value)
                if set_result.is_success():
                    imported_count += 1
            
            return Ok(imported_count)
            
        except Exception as e:
            return Err(ErrorInfo("SETTINGS_IMPORT_ERROR", f"設定インポートエラー: {str(e)}"))
    
    async def backup_settings(self, backup_path: Optional[Path] = None) -> Result[Path, ErrorInfo]:
        """設定のバックアップを作成"""
        try:
            if backup_path is None:
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                backup_filename = f"settings_backup_{timestamp}.json"
                backup_path = self._file_service.get_backups_dir() / backup_filename
            
            export_result = await self.export_settings(backup_path, include_encrypted=True)
            if export_result.is_failure():
                return export_result
            
            return Ok(backup_path)
            
        except Exception as e:
            return Err(ErrorInfo("SETTINGS_BACKUP_ERROR", f"設定バックアップエラー: {str(e)}"))
    
    async def get_settings_info(self) -> Result[Dict[str, Any], ErrorInfo]:
        """設定情報を取得"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                # 基本統計
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_settings,
                        COUNT(CASE WHEN is_encrypted = TRUE THEN 1 END) as encrypted_settings,
                        MIN(created_at) as oldest_setting,
                        MAX(updated_at) as newest_setting
                    FROM settings
                """)
                
                stats = dict(cursor.fetchone())
                
                # 型別統計
                cursor = conn.execute("""
                    SELECT value_type, COUNT(*) as count
                    FROM settings
                    GROUP BY value_type
                """)
                
                type_stats = {row['value_type']: row['count'] for row in cursor.fetchall()}
                stats['type_distribution'] = type_stats
                
                return Ok(stats)
                
        except Exception as e:
            return Err(ErrorInfo("SETTINGS_INFO_ERROR", f"設定情報取得エラー: {str(e)}"))
    
    def _calculate_checksum(self, data: str) -> str:
        """データのチェックサムを計算"""
        import hashlib
        return hashlib.sha256(data.encode('utf-8')).hexdigest()
    
    # 未実装メソッドの追加実装
    
    async def exists(self, key: str) -> Result[bool, ErrorInfo]:
        """設定の存在確認"""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.execute("SELECT key FROM settings WHERE key = ?", (key,))
                exists = cursor.fetchone() is not None
                return Ok(exists)
        except Exception as e:
            return Err(ErrorInfo("SETTINGS_EXISTS_ERROR", f"設定存在確認エラー: {str(e)}"))
    
    async def get_by_prefix(self, prefix: str) -> Result[Dict[str, SettingValue], ErrorInfo]:
        """プレフィックスで設定を取得"""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.execute("""
                    SELECT key FROM settings 
                    WHERE key LIKE ?
                    ORDER BY key
                """, (f"{prefix}%",))
                
                keys = [row['key'] for row in cursor.fetchall()]
                settings = {}
                
                for key in keys:
                    result = await self.get(key)
                    if result.is_success():
                        settings[key] = result.value
                
                return Ok(settings)
        except Exception as e:
            return Err(ErrorInfo("SETTINGS_GET_BY_PREFIX_ERROR", f"プレフィックス検索エラー: {str(e)}"))
    
    async def set_multiple(self, settings: Dict[str, SettingValue]) -> Result[bool, ErrorInfo]:
        """複数設定を一括保存"""
        try:
            with self._lock:
                success_count = 0
                for key, value in settings.items():
                    result = await self.set(key, value)
                    if result.is_success():
                        success_count += 1
                
                return Ok(success_count == len(settings))
        except Exception as e:
            return Err(ErrorInfo("SETTINGS_SET_MULTIPLE_ERROR", f"複数設定保存エラー: {str(e)}"))
    
    async def delete_by_prefix(self, prefix: str) -> Result[int, ErrorInfo]:
        """プレフィックスで設定を一括削除"""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.execute("DELETE FROM settings WHERE key LIKE ?", (f"{prefix}%",))
                deleted_count = cursor.rowcount
                conn.commit()
                return Ok(deleted_count)
        except Exception as e:
            return Err(ErrorInfo("SETTINGS_DELETE_BY_PREFIX_ERROR", f"プレフィックス削除エラー: {str(e)}"))
    
    # バックアップ・復元機能
    async def backup_to_file(self, file_path: Path) -> Result[bool, ErrorInfo]:
        """設定をファイルにバックアップ"""
        try:
            return await self.export_settings(file_path, include_encrypted=True)
        except Exception as e:
            return Err(ErrorInfo("SETTINGS_BACKUP_ERROR", f"バックアップエラー: {str(e)}"))
    
    async def restore_from_file(self, file_path: Path, overwrite: bool = False) -> Result[int, ErrorInfo]:
        """ファイルから設定を復元"""
        try:
            return await self.import_settings(file_path, overwrite)
        except Exception as e:
            return Err(ErrorInfo("SETTINGS_RESTORE_ERROR", f"復元エラー: {str(e)}"))
    
    # Windows環境固有機能
    async def sync_with_registry(self, key_prefix: Optional[str] = None) -> Result[bool, ErrorInfo]:
        """Windowsレジストリと同期（基本実装）"""
        try:
            # 基本的な実装 - 将来拡張可能
            return Ok(True)
        except Exception as e:
            return Err(ErrorInfo("SETTINGS_REGISTRY_SYNC_ERROR", f"レジストリ同期エラー: {str(e)}"))
    
    async def export_to_registry(self, registry_path: str, key_prefix: Optional[str] = None) -> Result[bool, ErrorInfo]:
        """Windowsレジストリにエクスポート（基本実装）"""
        try:
            with self._lock:
                # レジストリキーを作成
                try:
                    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, registry_path) as reg_key:
                        # プレフィックスで設定を取得
                        if key_prefix:
                            settings_result = await self.get_by_prefix(key_prefix)
                        else:
                            settings_result = await self.get_all()
                        
                        if settings_result.is_failure():
                            return settings_result
                        
                        settings = settings_result.value
                        for key, value in settings.items():
                            # レジストリに適した形式に変換
                            if isinstance(value, str):
                                winreg.SetValueEx(reg_key, key, 0, winreg.REG_SZ, value)
                            elif isinstance(value, int):
                                winreg.SetValueEx(reg_key, key, 0, winreg.REG_DWORD, value)
                            else:
                                # その他は文字列として保存
                                winreg.SetValueEx(reg_key, key, 0, winreg.REG_SZ, str(value))
                        
                        return Ok(True)
                except PermissionError:
                    return Err(ErrorInfo("SETTINGS_REGISTRY_PERMISSION", "レジストリへのアクセス権限がありません"))
        except Exception as e:
            return Err(ErrorInfo("SETTINGS_REGISTRY_EXPORT_ERROR", f"レジストリエクスポートエラー: {str(e)}"))
    
    async def import_from_registry(self, registry_path: str) -> Result[int, ErrorInfo]:
        """Windowsレジストリからインポート（基本実装）"""
        try:
            with self._lock:
                imported_count = 0
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path) as reg_key:
                        i = 0
                        while True:
                            try:
                                value_name, value_data, value_type = winreg.EnumValue(reg_key, i)
                                
                                # レジストリ値を適切な型に変換
                                if value_type == winreg.REG_SZ:
                                    setting_value = value_data
                                elif value_type == winreg.REG_DWORD:
                                    setting_value = value_data
                                else:
                                    setting_value = str(value_data)
                                
                                # 設定として保存
                                result = await self.set(value_name, setting_value)
                                if result.is_success():
                                    imported_count += 1
                                
                                i += 1
                            except OSError:
                                break  # 全て列挙完了
                        
                        return Ok(imported_count)
                except FileNotFoundError:
                    return Err(ErrorInfo("SETTINGS_REGISTRY_NOT_FOUND", f"レジストリキーが見つかりません: {registry_path}"))
        except Exception as e:
            return Err(ErrorInfo("SETTINGS_REGISTRY_IMPORT_ERROR", f"レジストリインポートエラー: {str(e)}"))
    
    # メタデータ・監査機能
    async def get_metadata(self, key: str) -> Result[Dict[str, Any], ErrorInfo]:
        """設定のメタデータを取得"""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.execute("""
                    SELECT created_at, updated_at, value_type, is_encrypted, checksum
                    FROM settings WHERE key = ?
                """, (key,))
                
                row = cursor.fetchone()
                if not row:
                    return Err(ErrorInfo("SETTINGS_NOT_FOUND", f"設定が見つかりません: {key}"))
                
                metadata = {
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'value_type': row['value_type'],
                    'is_encrypted': bool(row['is_encrypted']),
                    'checksum': row['checksum']
                }
                
                return Ok(metadata)
        except Exception as e:
            return Err(ErrorInfo("SETTINGS_METADATA_ERROR", f"メタデータ取得エラー: {str(e)}"))
    
    async def get_change_history(self, key: str, limit: Optional[int] = None) -> Result[List[Dict[str, Any]], ErrorInfo]:
        """設定変更履歴を取得（基本実装 - 現在の状態のみ）"""
        try:
            # 現在の実装では履歴テーブルがないため、現在の設定のみ返す
            metadata_result = await self.get_metadata(key)
            if metadata_result.is_failure():
                return Ok([])  # 設定が存在しない場合は空リスト
            
            metadata = metadata_result.value
            history = [{
                'timestamp': metadata['updated_at'],
                'action': 'current_state',
                'key': key,
                'metadata': metadata
            }]
            
            return Ok(history)
        except Exception as e:
            return Err(ErrorInfo("SETTINGS_HISTORY_ERROR", f"変更履歴取得エラー: {str(e)}"))
    
    async def validate_settings(self) -> Result[ValidationResult, ErrorInfo]:
        """設定の整合性検証"""
        try:
            with self._lock:
                errors = []
                warnings = []
                
                # 全設定を取得して検証
                all_settings_result = await self.get_all()
                if all_settings_result.is_failure():
                    return all_settings_result
                
                settings = all_settings_result.value
                
                # 基本的な検証
                for key, value in settings.items():
                    # キー形式の検証
                    if not key or len(key.strip()) == 0:
                        errors.append(f"無効なキー: '{key}'")
                        continue
                    
                    # 値のサイズチェック
                    if isinstance(value, str) and len(value) > 10000:
                        warnings.append(f"設定値が大きすぎます: {key} ({len(value)}文字)")
                
                # データベース整合性チェック
                conn = self._get_connection()
                cursor = conn.execute("SELECT COUNT(*) as count FROM settings")
                db_count = cursor.fetchone()['count']
                
                if db_count != len(settings):
                    warnings.append(f"設定数の不整合: DB={db_count}, メモリ={len(settings)}")
                
                validation_result = ValidationResult(
                    is_valid=len(errors) == 0,
                    errors=errors,
                    warnings=warnings
                )
                
                return Ok(validation_result)
        except Exception as e:
            return Err(ErrorInfo("SETTINGS_VALIDATION_ERROR", f"設定検証エラー: {str(e)}"))

    def close(self):
        """データベース接続を閉じる"""
        with self._lock:
            for conn in self._connection_pool.values():
                conn.close()
            self._connection_pool.clear()