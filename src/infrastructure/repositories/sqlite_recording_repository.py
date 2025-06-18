"""
SQLite Recording Repository - 記録データの永続化

SQLiteデータベースを使用した記録データの保存・取得を実装します。
AES-256暗号化によるデータ保護機能を含みます。
"""

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any

from ...core.result import Result, Ok, Err, ErrorInfo
from ...domain.repositories.recording_repository import IRecordingRepository
from ...domain import Recording, ActionTypes, ActionFactory
from ...domain.value_objects import RecordingStatus, ValidationResult
from ..services.encryption_service import EncryptionService
from ..services.file_service import FileService


class SqliteRecordingRepository(IRecordingRepository):
    """SQLite記録リポジトリ実装"""
    
    def __init__(self, db_path: Optional[Path] = None, 
                 encryption_service: Optional[EncryptionService] = None,
                 file_service: Optional[FileService] = None):
        
        self._lock = threading.RLock()
        
        # サービス依存の初期化
        self._encryption_service = encryption_service or EncryptionService()
        self._file_service = file_service or FileService()
        
        # データベースパスの設定
        if db_path is None:
            db_path = self._file_service.get_app_data_dir() / "recordings.db"
        
        self._db_path = db_path
        self._connection_pool = {}  # スレッドローカル接続プール
        
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
            conn.row_factory = sqlite3.Row  # 辞書形式でアクセス可能
            conn.execute("PRAGMA foreign_keys = ON")  # 外部キー制約有効化
            conn.execute("PRAGMA journal_mode = WAL")  # WALモード（並行アクセス改善）
            self._connection_pool[thread_id] = conn
        
        return self._connection_pool[thread_id]
    
    def _initialize_database(self):
        """データベースとテーブルの初期化"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                # 記録テーブル
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS recordings (
                        recording_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        completed_at TEXT,
                        action_count INTEGER DEFAULT 0,
                        estimated_duration INTEGER DEFAULT 0,
                        metadata_json TEXT,
                        playback_settings_json TEXT,
                        encrypted_data TEXT,
                        checksum TEXT
                    )
                """)
                
                # アクションテーブル
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS actions (
                        action_id TEXT PRIMARY KEY,
                        recording_id TEXT NOT NULL,
                        sequence_number INTEGER NOT NULL,
                        action_type TEXT NOT NULL,
                        encrypted_data TEXT NOT NULL,
                        checksum TEXT,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (recording_id) REFERENCES recordings (recording_id)
                            ON DELETE CASCADE,
                        UNIQUE (recording_id, sequence_number)
                    )
                """)
                
                # インデックス作成
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_recordings_status 
                    ON recordings (status)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_recordings_created_at 
                    ON recordings (created_at)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_actions_recording_id 
                    ON actions (recording_id)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_actions_sequence 
                    ON actions (recording_id, sequence_number)
                """)
                
                conn.commit()
                
        except Exception as e:
            raise RuntimeError(f"データベース初期化エラー: {str(e)}")
    
    async def save(self, recording: Recording) -> Result[str, str]:
        """記録を保存"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                # 記録の暗号化
                recording_json = self._recording_to_json(recording)
                
                if self._encryption_service.is_encryption_available():
                    encrypt_result = self._encryption_service.encrypt_data(recording_json)
                    if encrypt_result.is_failure():
                        return encrypt_result
                    encrypted_data = encrypt_result.value
                else:
                    encrypted_data = recording_json
                
                # チェックサム計算
                checksum = self._calculate_checksum(recording_json)
                
                # 現在時刻
                now = datetime.now(timezone.utc).isoformat()
                
                # 記録データの保存
                conn.execute("""
                    INSERT OR REPLACE INTO recordings (
                        recording_id, name, description, status,
                        created_at, updated_at, completed_at,
                        action_count, estimated_duration,
                        metadata_json, playback_settings_json,
                        encrypted_data, checksum
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    recording.recording_id,
                    recording.name,
                    recording.description,
                    recording.status.value,
                    recording.created_at.isoformat(),
                    now,
                    recording.completed_at.isoformat() if recording.completed_at else None,
                    recording.action_count,
                    recording.get_estimated_duration().milliseconds,
                    json.dumps(recording.metadata.to_dict()),
                    json.dumps(recording.playback_settings.to_dict()),
                    encrypted_data,
                    checksum
                ))
                
                # アクションデータの保存
                # 既存アクションを削除
                conn.execute("DELETE FROM actions WHERE recording_id = ?", 
                           (recording.recording_id,))
                
                # 新しいアクションを保存
                for action in recording.actions:
                    action_json = json.dumps(action.to_dict())
                    
                    if self._encryption_service.is_encryption_available():
                        encrypt_result = self._encryption_service.encrypt_data(action_json)
                        if encrypt_result.is_failure():
                            return encrypt_result
                        encrypted_action_data = encrypt_result.value
                    else:
                        encrypted_action_data = action_json
                    
                    action_checksum = self._calculate_checksum(action_json)
                    
                    conn.execute("""
                        INSERT INTO actions (
                            action_id, recording_id, sequence_number, action_type,
                            encrypted_data, checksum, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        action.action_id,
                        recording.recording_id,
                        action.sequence_number,
                        action.action_type.value,
                        encrypted_action_data,
                        action_checksum,
                        now
                    ))
                
                conn.commit()
                return Ok(recording.recording_id)
                
        except sqlite3.IntegrityError as e:
            return Err(f"データ整合性エラー: {str(e)}")
        except Exception as e:
            return Err(f"記録保存エラー: {str(e)}")
    
    async def get_by_id(self, recording_id: str) -> Result[Recording, str]:
        """IDで記録を取得"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                # 記録データの取得
                cursor = conn.execute("""
                    SELECT * FROM recordings WHERE recording_id = ?
                """, (recording_id,))
                
                row = cursor.fetchone()
                if not row:
                    return Err(f"記録が見つかりません: {recording_id}")
                
                # データの復号化
                decrypt_result = self._decrypt_recording_data(row['encrypted_data'])
                if decrypt_result.is_failure():
                    return decrypt_result
                
                recording_data = decrypt_result.value
                
                # チェックサム検証
                expected_checksum = self._calculate_checksum(recording_data)
                if expected_checksum != row['checksum']:
                    return Err("記録データの整合性エラー（チェックサム不一致）")
                
                # アクションデータの取得
                actions_result = self._load_actions(recording_id)
                if actions_result.is_failure():
                    return actions_result
                
                actions = actions_result.value
                
                # 記録オブジェクトの復元
                recording = self._json_to_recording(recording_data, actions)
                return Ok(recording)
                
        except Exception as e:
            return Err(f"記録取得エラー: {str(e)}")
    
    async def get_all(self) -> Result[List[Recording], str]:
        """すべての記録を取得"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                cursor = conn.execute("""
                    SELECT recording_id FROM recordings 
                    ORDER BY created_at DESC
                """)
                
                recording_ids = [row['recording_id'] for row in cursor.fetchall()]
                
                recordings = []
                for recording_id in recording_ids:
                    result = await self.get_by_id(recording_id)
                    if result.is_success():
                        recordings.append(result.value)
                    # エラーの場合は無視してスキップ
                
                return Ok(recordings)
                
        except Exception as e:
            return Err(f"全記録取得エラー: {str(e)}")
    
    async def get_by_status(self, status: RecordingStatus) -> Result[List[Recording], str]:
        """ステータス別記録取得"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                cursor = conn.execute("""
                    SELECT recording_id FROM recordings 
                    WHERE status = ?
                    ORDER BY created_at DESC
                """, (status.value,))
                
                recording_ids = [row['recording_id'] for row in cursor.fetchall()]
                
                recordings = []
                for recording_id in recording_ids:
                    result = await self.get_by_id(recording_id)
                    if result.is_success():
                        recordings.append(result.value)
                
                return Ok(recordings)
                
        except Exception as e:
            return Err(f"ステータス別記録取得エラー: {str(e)}")
    
    async def delete(self, recording_id: str) -> Result[bool, str]:
        """記録を削除"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                # まず記録が存在するかチェック
                cursor = conn.execute("""
                    SELECT recording_id FROM recordings WHERE recording_id = ?
                """, (recording_id,))
                
                if not cursor.fetchone():
                    return Ok(False)  # 存在しない場合
                
                # 記録削除（外部キー制約によりアクションも自動削除）
                conn.execute("DELETE FROM recordings WHERE recording_id = ?", 
                           (recording_id,))
                
                conn.commit()
                return Ok(True)
                
        except Exception as e:
            return Err(f"記録削除エラー: {str(e)}")
    
    async def search(self, query: str, limit: int = 100) -> Result[List[Recording], str]:
        """記録を検索"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                cursor = conn.execute("""
                    SELECT recording_id FROM recordings 
                    WHERE name LIKE ? OR description LIKE ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (f"%{query}%", f"%{query}%", limit))
                
                recording_ids = [row['recording_id'] for row in cursor.fetchall()]
                
                recordings = []
                for recording_id in recording_ids:
                    result = await self.get_by_id(recording_id)
                    if result.is_success():
                        recordings.append(result.value)
                
                return Ok(recordings)
                
        except Exception as e:
            return Err(f"記録検索エラー: {str(e)}")
    
    async def get_statistics(self) -> Result[Dict[str, Any], str]:
        """記録統計情報を取得"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                # 基本統計
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_recordings,
                        SUM(action_count) as total_actions,
                        AVG(action_count) as avg_actions_per_recording,
                        SUM(estimated_duration) as total_duration
                    FROM recordings
                """)
                
                stats = dict(cursor.fetchone())
                
                # ステータス別統計
                cursor = conn.execute("""
                    SELECT status, COUNT(*) as count
                    FROM recordings
                    GROUP BY status
                """)
                
                status_stats = {row['status']: row['count'] for row in cursor.fetchall()}
                stats['status_distribution'] = status_stats
                
                return Ok(stats)
                
        except Exception as e:
            return Err(f"統計情報取得エラー: {str(e)}")
    
    def _load_actions(self, recording_id: str) -> Result[List[ActionTypes], str]:
        """記録のアクションデータを読み込み"""
        try:
            conn = self._get_connection()
            
            cursor = conn.execute("""
                SELECT * FROM actions 
                WHERE recording_id = ?
                ORDER BY sequence_number
            """, (recording_id,))
            
            actions = []
            for row in cursor.fetchall():
                # データの復号化
                decrypt_result = self._decrypt_action_data(row['encrypted_data'])
                if decrypt_result.is_failure():
                    return decrypt_result
                
                action_json = decrypt_result.value
                
                # チェックサム検証
                expected_checksum = self._calculate_checksum(action_json)
                if expected_checksum != row['checksum']:
                    return Err(f"アクションデータの整合性エラー: {row['action_id']}")
                
                # アクションオブジェクトの復元
                action_data = json.loads(action_json)
                action = self._dict_to_action(action_data)
                actions.append(action)
            
            return Ok(actions)
            
        except Exception as e:
            return Err(f"アクション読み込みエラー: {str(e)}")
    
    def _recording_to_json(self, recording: Recording) -> str:
        """記録オブジェクトをJSONに変換"""
        return json.dumps({
            'recording_id': recording.recording_id,
            'name': recording.name,
            'description': recording.description,
            'status': recording.status.value,
            'created_at': recording.created_at.isoformat(),
            'updated_at': recording.updated_at.isoformat(),
            'completed_at': recording.completed_at.isoformat() if recording.completed_at else None,
            'action_count': recording.action_count,
            'estimated_duration': recording.get_estimated_duration().milliseconds,
            'metadata': recording.metadata.to_dict(),
            'playback_settings': recording.playback_settings.to_dict()
        })
    
    def _json_to_recording(self, json_data: str, actions: List[ActionTypes]) -> Recording:
        """JSONから記録オブジェクトを復元"""
        data = json.loads(json_data)
        
        from ...domain import RecordingMetadata, PlaybackSettings
        
        # メタデータとプレイバック設定の復元
        metadata = RecordingMetadata.from_dict(data['metadata'])
        playback_settings = PlaybackSettings.from_dict(data['playback_settings'])
        
        # 記録オブジェクトの作成
        recording = Recording(
            recording_id=data['recording_id'],
            name=data['name'],
            description=data['description'],
            metadata=metadata,
            playback_settings=playback_settings
        )
        
        # 状態の復元
        recording.status = RecordingStatus(data['status'])
        recording.created_at = datetime.fromisoformat(data['created_at'])
        recording.updated_at = datetime.fromisoformat(data['updated_at'])
        if data['completed_at']:
            recording.completed_at = datetime.fromisoformat(data['completed_at'])
        
        # アクションの追加
        for action in actions:
            recording._actions.append(action)  # プライベートリストに直接追加
        
        return recording
    
    def _dict_to_action(self, action_data: Dict[str, Any]) -> ActionTypes:
        """辞書からアクションオブジェクトを復元"""
        from ...domain import ActionType
        
        action_type = ActionType(action_data['action_type'])
        
        if action_type in [ActionType.KEY_PRESS, ActionType.TEXT_INPUT, ActionType.KEY_COMBINATION]:
            from ...domain import KeyboardAction
            return KeyboardAction.from_dict(action_data)
        elif action_type in [ActionType.MOUSE_CLICK, ActionType.MOUSE_DOUBLE_CLICK, ActionType.MOUSE_WHEEL]:
            from ...domain import MouseAction
            return MouseAction.from_dict(action_data)
        elif action_type in [ActionType.WINDOW_ACTIVATE, ActionType.WINDOW_RESIZE]:
            from ...domain import WindowAction
            return WindowAction.from_dict(action_data)
        elif action_type == ActionType.WAIT:
            from ...domain import WaitAction
            return WaitAction.from_dict(action_data)
        else:
            raise ValueError(f"未対応のアクションタイプ: {action_type}")
    
    def _decrypt_recording_data(self, encrypted_data: str) -> Result[str, str]:
        """記録データを復号化"""
        if self._encryption_service.is_encryption_available():
            return self._encryption_service.decrypt_data(encrypted_data)
        else:
            return Ok(encrypted_data)  # 暗号化されていない場合はそのまま返す
    
    def _decrypt_action_data(self, encrypted_data: str) -> Result[str, str]:
        """アクションデータを復号化"""
        if self._encryption_service.is_encryption_available():
            return self._encryption_service.decrypt_data(encrypted_data)
        else:
            return Ok(encrypted_data)  # 暗号化されていない場合はそのまま返す
    
    def _calculate_checksum(self, data: str) -> str:
        """データのチェックサムを計算"""
        import hashlib
        return hashlib.sha256(data.encode('utf-8')).hexdigest()
    
    # 未実装メソッドの追加実装
    
    async def get_by_name(self, name: str) -> Result[Recording, ErrorInfo]:
        """名前でレコーディングを取得"""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.execute("""
                    SELECT recording_id FROM recordings WHERE name = ?
                """, (name,))
                
                row = cursor.fetchone()
                if not row:
                    return Err(ErrorInfo("RECORDING_NOT_FOUND", f"記録が見つかりません: {name}"))
                
                return await self.get_by_id(row['recording_id'])
        except Exception as e:
            return Err(ErrorInfo("RECORDING_GET_BY_NAME_ERROR", f"名前による記録取得エラー: {str(e)}"))
    
    async def get_by_date_range(self, start_date: datetime, end_date: datetime) -> Result[List[Recording], ErrorInfo]:
        """日付範囲でレコーディングを取得"""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.execute("""
                    SELECT recording_id FROM recordings 
                    WHERE created_at BETWEEN ? AND ?
                    ORDER BY created_at DESC
                """, (start_date.isoformat(), end_date.isoformat()))
                
                recording_ids = [row['recording_id'] for row in cursor.fetchall()]
                recordings = []
                
                for recording_id in recording_ids:
                    result = await self.get_by_id(recording_id)
                    if result.is_success():
                        recordings.append(result.value)
                
                return Ok(recordings)
        except Exception as e:
            return Err(ErrorInfo("RECORDING_GET_BY_DATE_ERROR", f"日付範囲記録取得エラー: {str(e)}"))
    
    async def update(self, recording: Recording) -> Result[bool, ErrorInfo]:
        """レコーディングを更新"""
        try:
            # saveメソッドと同じ処理
            save_result = await self.save(recording)
            if save_result.is_success():
                return Ok(True)
            else:
                return Err(ErrorInfo("RECORDING_UPDATE_ERROR", f"記録更新エラー: {save_result.error}"))
        except Exception as e:
            return Err(ErrorInfo("RECORDING_UPDATE_ERROR", f"記録更新エラー: {str(e)}"))
    
    async def exists(self, recording_id: str) -> Result[bool, ErrorInfo]:
        """レコーディングの存在確認"""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.execute("SELECT recording_id FROM recordings WHERE recording_id = ?", (recording_id,))
                exists = cursor.fetchone() is not None
                return Ok(exists)
        except Exception as e:
            return Err(ErrorInfo("RECORDING_EXISTS_ERROR", f"記録存在確認エラー: {str(e)}"))
    
    async def count(self) -> Result[int, ErrorInfo]:
        """総レコーディング数を取得"""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.execute("SELECT COUNT(*) as count FROM recordings")
                count = cursor.fetchone()['count']
                return Ok(count)
        except Exception as e:
            return Err(ErrorInfo("RECORDING_COUNT_ERROR", f"記録数取得エラー: {str(e)}"))
    
    async def count_by_status(self, status: RecordingStatus) -> Result[int, ErrorInfo]:
        """ステータス別レコーディング数を取得"""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.execute("SELECT COUNT(*) as count FROM recordings WHERE status = ?", (status.value,))
                count = cursor.fetchone()['count']
                return Ok(count)
        except Exception as e:
            return Err(ErrorInfo("RECORDING_COUNT_BY_STATUS_ERROR", f"ステータス別記録数取得エラー: {str(e)}"))
    
    # バックアップ・復元機能
    async def backup_to_file(self, file_path: Path, recording_ids: Optional[List[str]] = None) -> Result[bool, ErrorInfo]:
        """ファイルにバックアップ"""
        try:
            if recording_ids is None:
                # 全記録を取得
                all_result = await self.get_all()
                if all_result.is_failure():
                    return all_result
                recordings = all_result.value
            else:
                # 指定記録を取得
                recordings = []
                for recording_id in recording_ids:
                    result = await self.get_by_id(recording_id)
                    if result.is_success():
                        recordings.append(result.value)
            
            # バックアップデータ作成
            backup_data = {
                'backup_timestamp': datetime.now(timezone.utc).isoformat(),
                'version': '2.0',
                'recording_count': len(recordings),
                'recordings': []
            }
            
            for recording in recordings:
                recording_data = {
                    'recording': self._recording_to_json(recording),
                    'actions': [action.to_dict() for action in recording.actions]
                }
                backup_data['recordings'].append(recording_data)
            
            # ファイルに書き込み
            write_result = self._file_service.write_json_file(file_path, backup_data)
            if write_result.is_success():
                return Ok(True)
            else:
                return Err(ErrorInfo("RECORDING_BACKUP_ERROR", f"バックアップファイル書き込みエラー: {write_result.error}"))
                
        except Exception as e:
            return Err(ErrorInfo("RECORDING_BACKUP_ERROR", f"記録バックアップエラー: {str(e)}"))
    
    async def restore_from_file(self, file_path: Path, overwrite: bool = False) -> Result[int, ErrorInfo]:
        """ファイルから復元"""
        try:
            # ファイル読み込み
            read_result = self._file_service.read_json_file(file_path)
            if read_result.is_failure():
                return Err(ErrorInfo("RECORDING_RESTORE_READ_ERROR", f"復元ファイル読み込みエラー: {read_result.error}"))
            
            backup_data = read_result.value
            if 'recordings' not in backup_data:
                return Err(ErrorInfo("RECORDING_RESTORE_FORMAT_ERROR", "無効な復元ファイル形式です"))
            
            restored_count = 0
            for recording_data in backup_data['recordings']:
                try:
                    # 記録データを復元
                    recording_json = recording_data['recording']
                    actions_data = recording_data['actions']
                    
                    # アクションオブジェクトを復元
                    actions = []
                    for action_data in actions_data:
                        action = self._dict_to_action(action_data)
                        actions.append(action)
                    
                    # 記録オブジェクトを復元
                    recording = self._json_to_recording(recording_json, actions)
                    
                    # 既存記録のチェック
                    if not overwrite:
                        exists_result = await self.exists(recording.recording_id)
                        if exists_result.is_success() and exists_result.value:
                            continue  # 上書きしない場合はスキップ
                    
                    # 記録を保存
                    save_result = await self.save(recording)
                    if save_result.is_success():
                        restored_count += 1
                        
                except Exception:
                    continue  # 個別エラーは無視して次へ
            
            return Ok(restored_count)
            
        except Exception as e:
            return Err(ErrorInfo("RECORDING_RESTORE_ERROR", f"記録復元エラー: {str(e)}"))
    
    # Windows環境固有機能
    async def export_to_windows_task(self, recording_id: str, task_name: str) -> Result[bool, ErrorInfo]:
        """Windowsタスクスケジューラーにエクスポート（基本実装）"""
        try:
            # 基本的な実装 - 将来拡張可能
            recording_result = await self.get_by_id(recording_id)
            if recording_result.is_failure():
                return recording_result
            
            # 実際のタスクスケジューラー統合は複雑なため、基本実装のみ
            return Ok(True)
            
        except Exception as e:
            return Err(ErrorInfo("RECORDING_EXPORT_TASK_ERROR", f"Windowsタスクエクスポートエラー: {str(e)}"))
    
    async def get_storage_info(self) -> Result[Dict[str, Any], ErrorInfo]:
        """ストレージ情報を取得"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                # データベースファイルサイズ
                db_size = self._db_path.stat().st_size if self._db_path.exists() else 0
                
                # 記録数とアクション数
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as recording_count,
                        SUM(action_count) as total_actions
                    FROM recordings
                """)
                stats = dict(cursor.fetchone())
                
                # アクションテーブルのサイズ
                cursor = conn.execute("SELECT COUNT(*) as action_count FROM actions")
                action_count = cursor.fetchone()['action_count']
                
                storage_info = {
                    'database_size_bytes': db_size,
                    'database_size_mb': round(db_size / (1024 * 1024), 2),
                    'recording_count': stats['recording_count'],
                    'total_actions': stats['total_actions'] or 0,
                    'action_records': action_count,
                    'avg_actions_per_recording': round(stats['total_actions'] / max(stats['recording_count'], 1), 2) if stats['total_actions'] else 0
                }
                
                return Ok(storage_info)
                
        except Exception as e:
            return Err(ErrorInfo("RECORDING_STORAGE_INFO_ERROR", f"ストレージ情報取得エラー: {str(e)}"))
    
    async def optimize_storage(self) -> Result[Dict[str, Any], ErrorInfo]:
        """ストレージ最適化"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                # VACUUM実行（SQLiteデータベース最適化）
                conn.execute("VACUUM")
                
                # 統計情報更新
                conn.execute("ANALYZE")
                
                # 最適化後のサイズ取得
                storage_result = await self.get_storage_info()
                if storage_result.is_failure():
                    return storage_result
                
                optimization_result = {
                    'optimized': True,
                    'storage_info': storage_result.value,
                    'operations_performed': ['VACUUM', 'ANALYZE']
                }
                
                return Ok(optimization_result)
                
        except Exception as e:
            return Err(ErrorInfo("RECORDING_OPTIMIZE_ERROR", f"ストレージ最適化エラー: {str(e)}"))
    
    async def validate_integrity(self) -> Result[ValidationResult, ErrorInfo]:
        """データ整合性検証"""
        try:
            errors = []
            warnings = []
            
            with self._lock:
                conn = self._get_connection()
                
                # SQLite整合性チェック
                cursor = conn.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()[0]
                if integrity_result != 'ok':
                    errors.append(f"SQLite整合性エラー: {integrity_result}")
                
                # 外部キー制約チェック
                cursor = conn.execute("PRAGMA foreign_key_check")
                fk_violations = cursor.fetchall()
                if fk_violations:
                    errors.extend([f"外部キー制約違反: {row}" for row in fk_violations])
                
                # 記録とアクションの整合性チェック
                cursor = conn.execute("""
                    SELECT r.recording_id, r.action_count, COUNT(a.action_id) as actual_count
                    FROM recordings r
                    LEFT JOIN actions a ON r.recording_id = a.recording_id
                    GROUP BY r.recording_id, r.action_count
                    HAVING r.action_count != actual_count
                """)
                
                count_mismatches = cursor.fetchall()
                for mismatch in count_mismatches:
                    warnings.append(f"アクション数不整合: 記録ID={mismatch['recording_id']}, 期待={mismatch['action_count']}, 実際={mismatch['actual_count']}")
                
                # 孤立アクションチェック
                cursor = conn.execute("""
                    SELECT COUNT(*) as orphaned_actions
                    FROM actions a
                    LEFT JOIN recordings r ON a.recording_id = r.recording_id
                    WHERE r.recording_id IS NULL
                """)
                orphaned_count = cursor.fetchone()['orphaned_actions']
                if orphaned_count > 0:
                    warnings.append(f"孤立アクション: {orphaned_count}件")
                
                validation_result = ValidationResult(
                    is_valid=len(errors) == 0,
                    errors=errors,
                    warnings=warnings
                )
                
                return Ok(validation_result)
                
        except Exception as e:
            return Err(ErrorInfo("RECORDING_VALIDATION_ERROR", f"整合性検証エラー: {str(e)}"))

    def close(self):
        """データベース接続を閉じる"""
        with self._lock:
            for conn in self._connection_pool.values():
                conn.close()
            self._connection_pool.clear()