"""
SQLite Schedule Repository - スケジュールデータの永続化

SQLiteデータベースを使用したスケジュールデータの保存・取得を実装します。
"""

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any

from ...core.result import Result, Ok, Err, ErrorInfo
from ...domain.repositories.schedule_repository import IScheduleRepository
from ...domain import Schedule, TriggerCondition, RepeatCondition
from ...domain.value_objects import ScheduleStatus, TriggerType
from ..services.encryption_service import EncryptionService
from ..services.file_service import FileService


class SqliteScheduleRepository(IScheduleRepository):
    """SQLiteスケジュールリポジトリ実装"""
    
    def __init__(self, db_path: Optional[Path] = None,
                 encryption_service: Optional[EncryptionService] = None,
                 file_service: Optional[FileService] = None):
        
        self._lock = threading.RLock()
        
        # サービス依存の初期化
        self._encryption_service = encryption_service or EncryptionService()
        self._file_service = file_service or FileService()
        
        # データベースパスの設定
        if db_path is None:
            db_path = self._file_service.get_app_data_dir() / "schedules.db"
        
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
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            self._connection_pool[thread_id] = conn
        
        return self._connection_pool[thread_id]
    
    def _initialize_database(self):
        """データベースとテーブルの初期化"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                # スケジュールテーブル
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS schedules (
                        schedule_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        recording_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        trigger_type TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        next_execution_time TEXT,
                        last_execution_time TEXT,
                        execution_count INTEGER DEFAULT 0,
                        max_executions INTEGER,
                        encrypted_data TEXT NOT NULL,
                        checksum TEXT
                    )
                """)
                
                # 実行履歴テーブル
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS execution_history (
                        execution_id TEXT PRIMARY KEY,
                        schedule_id TEXT NOT NULL,
                        recording_id TEXT NOT NULL,
                        started_at TEXT NOT NULL,
                        completed_at TEXT,
                        status TEXT NOT NULL,
                        success BOOLEAN NOT NULL,
                        error_message TEXT,
                        actions_executed INTEGER DEFAULT 0,
                        duration_ms INTEGER DEFAULT 0,
                        metadata_json TEXT,
                        FOREIGN KEY (schedule_id) REFERENCES schedules (schedule_id)
                            ON DELETE CASCADE
                    )
                """)
                
                # インデックス作成
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_schedules_status 
                    ON schedules (status)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_schedules_next_execution 
                    ON schedules (next_execution_time)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_schedules_trigger_type 
                    ON schedules (trigger_type)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_execution_history_schedule 
                    ON execution_history (schedule_id)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_execution_history_started 
                    ON execution_history (started_at)
                """)
                
                conn.commit()
                
        except Exception as e:
            raise RuntimeError(f"スケジュールデータベース初期化エラー: {str(e)}")
    
    async def save(self, schedule: Schedule) -> Result[str, str]:
        """スケジュールを保存"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                # スケジュールの暗号化
                schedule_json = self._schedule_to_json(schedule)
                
                if self._encryption_service.is_encryption_available():
                    encrypt_result = self._encryption_service.encrypt_data(schedule_json)
                    if encrypt_result.is_failure():
                        return encrypt_result
                    encrypted_data = encrypt_result.value
                else:
                    encrypted_data = schedule_json
                
                # チェックサム計算
                checksum = self._calculate_checksum(schedule_json)
                
                # 現在時刻
                now = datetime.now(timezone.utc).isoformat()
                
                # スケジュールデータの保存
                conn.execute("""
                    INSERT OR REPLACE INTO schedules (
                        schedule_id, name, description, recording_id, status,
                        trigger_type, created_at, updated_at,
                        next_execution_time, last_execution_time,
                        execution_count, max_executions,
                        encrypted_data, checksum
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    schedule.schedule_id,
                    schedule.name,
                    schedule.description,
                    schedule.recording_id,
                    schedule.status.value,
                    schedule.trigger_condition.trigger_type.value,
                    schedule.created_at.isoformat(),
                    now,
                    schedule.next_execution_time.isoformat() if schedule.next_execution_time else None,
                    schedule.last_execution_time.isoformat() if schedule.last_execution_time else None,
                    schedule.execution_count,
                    schedule.max_executions,
                    encrypted_data,
                    checksum
                ))
                
                conn.commit()
                return Ok(schedule.schedule_id)
                
        except sqlite3.IntegrityError as e:
            return Err(f"スケジュールデータ整合性エラー: {str(e)}")
        except Exception as e:
            return Err(f"スケジュール保存エラー: {str(e)}")
    
    async def get_by_id(self, schedule_id: str) -> Result[Schedule, str]:
        """IDでスケジュールを取得"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                cursor = conn.execute("""
                    SELECT * FROM schedules WHERE schedule_id = ?
                """, (schedule_id,))
                
                row = cursor.fetchone()
                if not row:
                    return Err(f"スケジュールが見つかりません: {schedule_id}")
                
                # データの復号化
                decrypt_result = self._decrypt_schedule_data(row['encrypted_data'])
                if decrypt_result.is_failure():
                    return decrypt_result
                
                schedule_data = decrypt_result.value
                
                # チェックサム検証
                expected_checksum = self._calculate_checksum(schedule_data)
                if expected_checksum != row['checksum']:
                    return Err("スケジュールデータの整合性エラー（チェックサム不一致）")
                
                # スケジュールオブジェクトの復元
                schedule = self._json_to_schedule(schedule_data)
                return Ok(schedule)
                
        except Exception as e:
            return Err(f"スケジュール取得エラー: {str(e)}")
    
    async def get_all(self) -> Result[List[Schedule], str]:
        """すべてのスケジュールを取得"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                cursor = conn.execute("""
                    SELECT schedule_id FROM schedules 
                    ORDER BY created_at DESC
                """)
                
                schedule_ids = [row['schedule_id'] for row in cursor.fetchall()]
                
                schedules = []
                for schedule_id in schedule_ids:
                    result = await self.get_by_id(schedule_id)
                    if result.is_success():
                        schedules.append(result.value)
                
                return Ok(schedules)
                
        except Exception as e:
            return Err(f"全スケジュール取得エラー: {str(e)}")
    
    async def get_by_status(self, status: ScheduleStatus) -> Result[List[Schedule], str]:
        """ステータス別スケジュール取得"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                cursor = conn.execute("""
                    SELECT schedule_id FROM schedules 
                    WHERE status = ?
                    ORDER BY next_execution_time ASC
                """, (status.value,))
                
                schedule_ids = [row['schedule_id'] for row in cursor.fetchall()]
                
                schedules = []
                for schedule_id in schedule_ids:
                    result = await self.get_by_id(schedule_id)
                    if result.is_success():
                        schedules.append(result.value)
                
                return Ok(schedules)
                
        except Exception as e:
            return Err(f"ステータス別スケジュール取得エラー: {str(e)}")
    
    async def get_by_recording_id(self, recording_id: str) -> Result[List[Schedule], str]:
        """記録IDでスケジュールを取得"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                cursor = conn.execute("""
                    SELECT schedule_id FROM schedules 
                    WHERE recording_id = ?
                    ORDER BY created_at DESC
                """, (recording_id,))
                
                schedule_ids = [row['schedule_id'] for row in cursor.fetchall()]
                
                schedules = []
                for schedule_id in schedule_ids:
                    result = await self.get_by_id(schedule_id)
                    if result.is_success():
                        schedules.append(result.value)
                
                return Ok(schedules)
                
        except Exception as e:
            return Err(f"記録別スケジュール取得エラー: {str(e)}")
    
    async def get_due_schedules(self, current_time: Optional[datetime] = None) -> Result[List[Schedule], str]:
        """実行予定のスケジュールを取得"""
        try:
            if current_time is None:
                current_time = datetime.now(timezone.utc)
            
            with self._lock:
                conn = self._get_connection()
                
                cursor = conn.execute("""
                    SELECT schedule_id FROM schedules 
                    WHERE status = ? 
                    AND next_execution_time <= ?
                    ORDER BY next_execution_time ASC
                """, (ScheduleStatus.ACTIVE.value, current_time.isoformat()))
                
                schedule_ids = [row['schedule_id'] for row in cursor.fetchall()]
                
                schedules = []
                for schedule_id in schedule_ids:
                    result = await self.get_by_id(schedule_id)
                    if result.is_success():
                        schedules.append(result.value)
                
                return Ok(schedules)
                
        except Exception as e:
            return Err(f"実行予定スケジュール取得エラー: {str(e)}")
    
    async def delete(self, schedule_id: str) -> Result[bool, str]:
        """スケジュールを削除"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                # まずスケジュールが存在するかチェック
                cursor = conn.execute("""
                    SELECT schedule_id FROM schedules WHERE schedule_id = ?
                """, (schedule_id,))
                
                if not cursor.fetchone():
                    return Ok(False)  # 存在しない場合
                
                # スケジュール削除（外部キー制約により実行履歴も自動削除）
                conn.execute("DELETE FROM schedules WHERE schedule_id = ?", 
                           (schedule_id,))
                
                conn.commit()
                return Ok(True)
                
        except Exception as e:
            return Err(f"スケジュール削除エラー: {str(e)}")
    
    async def save_execution_result(self, execution_result) -> Result[str, str]:
        """実行結果を保存"""
        from ...domain import ExecutionResult
        
        try:
            with self._lock:
                conn = self._get_connection()
                
                conn.execute("""
                    INSERT INTO execution_history (
                        execution_id, schedule_id, recording_id,
                        started_at, completed_at, status, success,
                        error_message, actions_executed, duration_ms,
                        metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    execution_result.execution_id,
                    execution_result.schedule_id,
                    execution_result.recording_id,
                    execution_result.started_at.isoformat(),
                    execution_result.completed_at.isoformat() if execution_result.completed_at else None,
                    execution_result.status.value,
                    execution_result.success,
                    execution_result.error_message,
                    execution_result.actions_executed,
                    execution_result.duration.milliseconds,
                    json.dumps(execution_result.metadata) if execution_result.metadata else None
                ))
                
                conn.commit()
                return Ok(execution_result.execution_id)
                
        except Exception as e:
            return Err(f"実行結果保存エラー: {str(e)}")
    
    async def get_execution_history(self, schedule_id: str, limit: int = 100) -> Result[List, str]:
        """実行履歴を取得"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                cursor = conn.execute("""
                    SELECT * FROM execution_history 
                    WHERE schedule_id = ?
                    ORDER BY started_at DESC
                    LIMIT ?
                """, (schedule_id, limit))
                
                histories = []
                for row in cursor.fetchall():
                    from ...domain import ExecutionResult, ExecutionStatus
                    from ...domain.value_objects import Duration
                    
                    history = ExecutionResult(
                        execution_id=row['execution_id'],
                        schedule_id=row['schedule_id'],
                        recording_id=row['recording_id'],
                        started_at=datetime.fromisoformat(row['started_at']),
                        completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
                        status=ExecutionStatus(row['status']),
                        success=bool(row['success']),
                        error_message=row['error_message'],
                        actions_executed=row['actions_executed'],
                        duration=Duration(row['duration_ms']),
                        metadata=json.loads(row['metadata_json']) if row['metadata_json'] else {}
                    )
                    histories.append(history)
                
                return Ok(histories)
                
        except Exception as e:
            return Err(f"実行履歴取得エラー: {str(e)}")
    
    async def get_statistics(self) -> Result[Dict[str, Any], str]:
        """スケジュール統計情報を取得"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                # 基本統計
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_schedules,
                        SUM(execution_count) as total_executions,
                        AVG(execution_count) as avg_executions_per_schedule
                    FROM schedules
                """)
                
                stats = dict(cursor.fetchone())
                
                # ステータス別統計
                cursor = conn.execute("""
                    SELECT status, COUNT(*) as count
                    FROM schedules
                    GROUP BY status
                """)
                
                status_stats = {row['status']: row['count'] for row in cursor.fetchall()}
                stats['status_distribution'] = status_stats
                
                # トリガータイプ別統計
                cursor = conn.execute("""
                    SELECT trigger_type, COUNT(*) as count
                    FROM schedules
                    GROUP BY trigger_type
                """)
                
                trigger_stats = {row['trigger_type']: row['count'] for row in cursor.fetchall()}
                stats['trigger_distribution'] = trigger_stats
                
                # 実行成功率
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_executions,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_executions
                    FROM execution_history
                """)
                
                exec_stats = dict(cursor.fetchone())
                if exec_stats['total_executions'] > 0:
                    stats['success_rate'] = (exec_stats['successful_executions'] / exec_stats['total_executions']) * 100
                else:
                    stats['success_rate'] = 0
                
                return Ok(stats)
                
        except Exception as e:
            return Err(f"統計情報取得エラー: {str(e)}")
    
    def _schedule_to_json(self, schedule: Schedule) -> str:
        """スケジュールオブジェクトをJSONに変換"""
        return json.dumps({
            'schedule_id': schedule.schedule_id,
            'name': schedule.name,
            'description': schedule.description,
            'recording_id': schedule.recording_id,
            'status': schedule.status.value,
            'trigger_condition': schedule.trigger_condition.to_dict(),
            'repeat_condition': schedule.repeat_condition.to_dict() if schedule.repeat_condition else None,
            'created_at': schedule.created_at.isoformat(),
            'updated_at': schedule.updated_at.isoformat(),
            'next_execution_time': schedule.next_execution_time.isoformat() if schedule.next_execution_time else None,
            'last_execution_time': schedule.last_execution_time.isoformat() if schedule.last_execution_time else None,
            'execution_count': schedule.execution_count,
            'max_executions': schedule.max_executions
        })
    
    def _json_to_schedule(self, json_data: str) -> Schedule:
        """JSONからスケジュールオブジェクトを復元"""
        data = json.loads(json_data)
        
        # トリガー条件の復元
        trigger_data = data['trigger_condition']
        trigger_condition = TriggerCondition.from_dict(trigger_data)
        
        # リピート条件の復元
        repeat_condition = None
        if data['repeat_condition']:
            repeat_condition = RepeatCondition.from_dict(data['repeat_condition'])
        
        # スケジュールオブジェクトの作成
        schedule = Schedule(
            schedule_id=data['schedule_id'],
            name=data['name'],
            description=data['description'],
            recording_id=data['recording_id'],
            trigger_condition=trigger_condition,
            repeat_condition=repeat_condition,
            max_executions=data.get('max_executions')
        )
        
        # 状態の復元
        schedule.status = ScheduleStatus(data['status'])
        schedule.created_at = datetime.fromisoformat(data['created_at'])
        schedule.updated_at = datetime.fromisoformat(data['updated_at'])
        if data['next_execution_time']:
            schedule.next_execution_time = datetime.fromisoformat(data['next_execution_time'])
        if data['last_execution_time']:
            schedule.last_execution_time = datetime.fromisoformat(data['last_execution_time'])
        schedule.execution_count = data['execution_count']
        
        return schedule
    
    def _decrypt_schedule_data(self, encrypted_data: str) -> Result[str, str]:
        """スケジュールデータを復号化"""
        if self._encryption_service.is_encryption_available():
            return self._encryption_service.decrypt_data(encrypted_data)
        else:
            return Ok(encrypted_data)
    
    def _calculate_checksum(self, data: str) -> str:
        """データのチェックサムを計算"""
        import hashlib
        return hashlib.sha256(data.encode('utf-8')).hexdigest()
    
    def close(self):
        """データベース接続を閉じる"""
        with self._lock:
            for conn in self._connection_pool.values():
                conn.close()
            self._connection_pool.clear()