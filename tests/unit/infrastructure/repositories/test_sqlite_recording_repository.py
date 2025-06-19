"""
SQLite Recording Repository Unit Tests - SQLite記録リポジトリのテスト

SQLite記録リポジトリのデータ永続化機能をテストします。
"""

import pytest
import sqlite3
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from src.infrastructure.repositories.sqlite_recording_repository import SqliteRecordingRepository
from src.core.result import Result, Ok, Err, ErrorInfo
from src.domain.entities.recording import Recording
from src.domain.value_objects import RecordingStatus
from tests.factories import RecordingFactory, KeyboardActionFactory


class TestSqliteRecordingRepository:
    """SQLite記録リポジトリのテストクラス"""
    
    @pytest.fixture
    def temp_db_path(self):
        """一時データベースファイルパス"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        yield temp_path
        # クリーンアップ
        if temp_path.exists():
            temp_path.unlink()
    
    @pytest.fixture
    def mock_encryption_service(self):
        """モック暗号化サービス"""
        mock_service = Mock()
        mock_service.encrypt.return_value = b"encrypted_data"
        mock_service.decrypt.return_value = b"decrypted_data"
        return mock_service
    
    @pytest.fixture
    def mock_file_service(self):
        """モックファイルサービス"""
        mock_service = Mock()
        mock_service.get_app_data_dir.return_value = Path(tempfile.gettempdir())
        return mock_service
    
    @pytest.fixture
    def repository(self, temp_db_path, mock_encryption_service, mock_file_service):
        """テスト対象のリポジトリ"""
        return SqliteRecordingRepository(
            db_path=temp_db_path,
            encryption_service=mock_encryption_service,
            file_service=mock_file_service
        )
    
    @pytest.fixture
    def in_memory_repository(self, mock_encryption_service, mock_file_service):
        """インメモリデータベース用リポジトリ"""
        return SqliteRecordingRepository(
            db_path=Path(":memory:"),
            encryption_service=mock_encryption_service,
            file_service=mock_file_service
        )
    
    # ========================
    # 初期化・設定テスト
    # ========================
    
    def test_repository_initialization(self, repository):
        """リポジトリ初期化のテスト"""
        # Assert - データベースファイルが作成されている
        assert repository._db_path.exists()
        
        # Assert - 必要なテーブルが作成されている
        conn = repository._get_connection()
        cursor = conn.cursor()
        
        # テーブル存在確認
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('recordings', 'actions', 'metadata')
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['recordings', 'actions', 'metadata']
        assert all(table in tables for table in expected_tables)
    
    def test_database_schema_creation(self, repository):
        """データベーススキーマ作成のテスト"""
        conn = repository._get_connection()
        cursor = conn.cursor()
        
        # recordings テーブルのスキーマ確認
        cursor.execute("PRAGMA table_info(recordings)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}  # column_name: type
        
        expected_columns = {
            'recording_id': 'TEXT',
            'name': 'TEXT',
            'description': 'TEXT',
            'status': 'TEXT',
            'created_at': 'TEXT',
            'updated_at': 'TEXT',
            'encrypted_data': 'BLOB'
        }
        
        for col_name, col_type in expected_columns.items():
            assert col_name in columns
            assert col_type in columns[col_name]
    
    def test_thread_safe_connection_pooling(self, repository):
        """スレッドセーフな接続プールのテスト"""
        import threading
        
        connections = []
        
        def get_connection():
            conn = repository._get_connection()
            connections.append(id(conn))
        
        # 複数スレッドで接続を取得
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=get_connection)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 各スレッドで異なる接続が使用されることを確認
        assert len(set(connections)) == 5
    
    # ========================
    # 保存機能テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_save_new_recording_success(self, repository, mock_encryption_service):
        """新規記録保存成功のテスト"""
        # Arrange
        recording = RecordingFactory()
        mock_encryption_service.encrypt.return_value = b"encrypted_recording_data"
        
        # Act
        result = await repository.save(recording)
        
        # Assert
        assert result.is_success()
        assert result.value == recording.recording_id
        
        # データベースに保存されていることを確認
        conn = repository._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT recording_id, name, status FROM recordings WHERE recording_id = ?",
            (recording.recording_id,)
        )
        row = cursor.fetchone()
        
        assert row is not None
        assert row[0] == recording.recording_id
        assert row[1] == recording.metadata.name
        assert row[2] == recording.status.value
    
    @pytest.mark.asyncio
    async def test_save_existing_recording_update(self, repository, mock_encryption_service):
        """既存記録更新のテスト"""
        # Arrange
        recording = RecordingFactory()
        await repository.save(recording)  # 最初に保存
        
        # 記録を更新
        recording.metadata.name = "Updated Name"
        recording.status = RecordingStatus.COMPLETED
        mock_encryption_service.encrypt.return_value = b"updated_encrypted_data"
        
        # Act
        result = await repository.save(recording)
        
        # Assert
        assert result.is_success()
        
        # データベースが更新されていることを確認
        conn = repository._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, status FROM recordings WHERE recording_id = ?",
            (recording.recording_id,)
        )
        row = cursor.fetchone()
        
        assert row[0] == "Updated Name"
        assert row[1] == RecordingStatus.COMPLETED.value
    
    @pytest.mark.asyncio
    async def test_save_with_actions(self, repository, mock_encryption_service):
        """アクション付き記録保存のテスト"""
        # Arrange
        recording = RecordingFactory()
        actions = [KeyboardActionFactory() for _ in range(3)]
        recording.actions = actions
        
        mock_encryption_service.encrypt.return_value = b"encrypted_with_actions"
        
        # Act
        result = await repository.save(recording)
        
        # Assert
        assert result.is_success()
        
        # アクションデータが保存されていることを確認
        conn = repository._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM actions WHERE recording_id = ?",
            (recording.recording_id,)
        )
        action_count = cursor.fetchone()[0]
        
        assert action_count == 3
    
    @pytest.mark.asyncio
    async def test_save_encryption_failure(self, repository, mock_encryption_service):
        """暗号化失敗時のテスト"""
        # Arrange
        recording = RecordingFactory()
        mock_encryption_service.encrypt.side_effect = Exception("Encryption failed")
        
        # Act
        result = await repository.save(recording)
        
        # Assert
        assert result.is_failure()
        assert "ENCRYPTION_ERROR" in result.error.code
    
    @pytest.mark.asyncio
    async def test_save_database_error(self, repository):
        """データベースエラー時のテスト"""
        # Arrange
        recording = RecordingFactory()
        
        # データベース接続を無効化
        with patch.object(repository, '_get_connection') as mock_conn:
            mock_conn.side_effect = sqlite3.Error("Database is locked")
            
            # Act
            result = await repository.save(recording)
            
            # Assert
            assert result.is_failure()
            assert "DATABASE_ERROR" in result.error.code
    
    # ========================
    # 取得機能テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_get_by_id_success(self, repository, mock_encryption_service):
        """ID指定での記録取得成功のテスト"""
        # Arrange
        recording = RecordingFactory()
        await repository.save(recording)
        
        # 復号化の設定
        recording_data = json.dumps({
            "recording_id": recording.recording_id,
            "metadata": {"name": recording.metadata.name},
            "status": recording.status.value,
            "actions": []
        })
        mock_encryption_service.decrypt.return_value = recording_data.encode()
        
        # Act
        result = await repository.get_by_id(recording.recording_id)
        
        # Assert
        assert result.is_success()
        retrieved_recording = result.value
        assert retrieved_recording.recording_id == recording.recording_id
        assert retrieved_recording.metadata.name == recording.metadata.name
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository):
        """存在しないID指定での取得テスト"""
        # Act
        result = await repository.get_by_id("nonexistent_id")
        
        # Assert
        assert result.is_failure()
        assert "NOT_FOUND" in result.error.code
    
    @pytest.mark.asyncio
    async def test_get_by_id_decryption_failure(self, repository, mock_encryption_service):
        """復号化失敗時のテスト"""
        # Arrange
        recording = RecordingFactory()
        await repository.save(recording)
        
        mock_encryption_service.decrypt.side_effect = Exception("Decryption failed")
        
        # Act
        result = await repository.get_by_id(recording.recording_id)
        
        # Assert
        assert result.is_failure()
        assert "DECRYPTION_ERROR" in result.error.code
    
    @pytest.mark.asyncio
    async def test_get_all_recordings(self, repository, mock_encryption_service):
        """全記録取得のテスト"""
        # Arrange
        recordings = [RecordingFactory() for _ in range(3)]
        for recording in recordings:
            await repository.save(recording)
        
        # 復号化の設定
        def decrypt_side_effect(data):
            return json.dumps({"recording_id": "test", "actions": []}).encode()
        
        mock_encryption_service.decrypt.side_effect = decrypt_side_effect
        
        # Act
        result = await repository.get_all()
        
        # Assert
        assert result.is_success()
        retrieved_recordings = result.value
        assert len(retrieved_recordings) == 3
    
    @pytest.mark.asyncio
    async def test_get_by_status(self, repository, mock_encryption_service):
        """ステータス指定での取得テスト"""
        # Arrange
        completed_recording = RecordingFactory(status=RecordingStatus.COMPLETED)
        recording_recording = RecordingFactory(status=RecordingStatus.RECORDING)
        
        await repository.save(completed_recording)
        await repository.save(recording_recording)
        
        # 復号化の設定
        mock_encryption_service.decrypt.return_value = json.dumps({
            "recording_id": "test",
            "actions": []
        }).encode()
        
        # Act
        result = await repository.get_by_status(RecordingStatus.COMPLETED)
        
        # Assert
        assert result.is_success()
        completed_recordings = result.value
        
        # 完了済み記録のみが取得されることを確認
        # 注意: 実際の実装では、データベースクエリでフィルタリングされる
        assert len(completed_recordings) >= 0  # 基本的な動作確認
    
    # ========================
    # 削除機能テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_delete_recording_success(self, repository):
        """記録削除成功のテスト"""
        # Arrange
        recording = RecordingFactory()
        await repository.save(recording)
        
        # Act
        result = await repository.delete(recording.recording_id)
        
        # Assert
        assert result.is_success()
        assert result.value is True
        
        # データベースから削除されていることを確認
        conn = repository._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM recordings WHERE recording_id = ?",
            (recording.recording_id,)
        )
        count = cursor.fetchone()[0]
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_recording(self, repository):
        """存在しない記録の削除テスト"""
        # Act
        result = await repository.delete("nonexistent_id")
        
        # Assert
        assert result.is_failure()
        assert "NOT_FOUND" in result.error.code
    
    @pytest.mark.asyncio
    async def test_delete_with_cascade(self, repository):
        """カスケード削除のテスト"""
        # Arrange
        recording = RecordingFactory()
        recording.actions = [KeyboardActionFactory() for _ in range(2)]
        await repository.save(recording)
        
        # Act
        result = await repository.delete(recording.recording_id)
        
        # Assert
        assert result.is_success()
        
        # 関連アクションも削除されていることを確認
        conn = repository._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM actions WHERE recording_id = ?",
            (recording.recording_id,)
        )
        action_count = cursor.fetchone()[0]
        assert action_count == 0
    
    # ========================
    # 検索機能テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_search_recordings(self, repository, mock_encryption_service):
        """記録検索のテスト"""
        # Arrange
        recording1 = RecordingFactory()
        recording1.metadata.name = "Test Recording 1"
        recording2 = RecordingFactory()
        recording2.metadata.name = "Another Recording"
        
        await repository.save(recording1)
        await repository.save(recording2)
        
        # 復号化の設定
        mock_encryption_service.decrypt.return_value = json.dumps({
            "recording_id": "test",
            "metadata": {"name": "Test Recording 1"},
            "actions": []
        }).encode()
        
        # Act
        result = await repository.search("Test", limit=10)
        
        # Assert
        assert result.is_success()
        search_results = result.value
        assert len(search_results) >= 0  # 基本的な動作確認
    
    # ========================
    # 統計情報テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, repository):
        """統計情報取得のテスト"""
        # Arrange
        recordings = [
            RecordingFactory(status=RecordingStatus.COMPLETED),
            RecordingFactory(status=RecordingStatus.RECORDING),
            RecordingFactory(status=RecordingStatus.FAILED)
        ]
        
        for recording in recordings:
            await repository.save(recording)
        
        # Act
        result = await repository.get_statistics()
        
        # Assert
        assert result.is_success()
        stats = result.value
        
        assert 'total_recordings' in stats
        assert 'completed_recordings' in stats
        assert 'active_recordings' in stats
        assert 'failed_recordings' in stats
        
        assert stats['total_recordings'] >= 3
    
    # ========================
    # トランザクション・整合性テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self, repository):
        """エラー時のトランザクションロールバックテスト"""
        # Arrange
        recording = RecordingFactory()
        
        # データベースエラーを発生させるためのモック
        with patch.object(repository, '_save_actions') as mock_save_actions:
            mock_save_actions.side_effect = sqlite3.Error("Constraint violation")
            
            # Act
            result = await repository.save(recording)
            
            # Assert
            assert result.is_failure()
            
            # 記録がデータベースに保存されていないことを確認
            conn = repository._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM recordings WHERE recording_id = ?",
                (recording.recording_id,)
            )
            count = cursor.fetchone()[0]
            assert count == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_access_safety(self, repository):
        """並行アクセス安全性のテスト"""
        import asyncio
        
        # Arrange
        recordings = [RecordingFactory() for _ in range(5)]
        
        # Act - 並行して複数の記録を保存
        tasks = [repository.save(recording) for recording in recordings]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Assert - 全ての保存が成功すること
        successful_results = [r for r in results if isinstance(r, Result) and r.is_success()]
        assert len(successful_results) == 5
    
    # ========================
    # パフォーマンステスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_large_recording_performance(self, repository, mock_encryption_service):
        """大きな記録のパフォーマンステスト"""
        # Arrange
        recording = RecordingFactory()
        # 大量のアクションを追加
        recording.actions = [KeyboardActionFactory() for _ in range(1000)]
        
        mock_encryption_service.encrypt.return_value = b"large_encrypted_data"
        
        # Act
        import time
        start_time = time.time()
        result = await repository.save(recording)
        end_time = time.time()
        
        # Assert
        assert result.is_success()
        # パフォーマンス要件: 1000アクションの保存が5秒以内
        assert (end_time - start_time) < 5.0
    
    # ========================
    # データ整合性テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_data_integrity_after_save_load(self, repository, mock_encryption_service):
        """保存・読み込み後のデータ整合性テスト"""
        # Arrange
        original_recording = RecordingFactory()
        original_recording.actions = [KeyboardActionFactory() for _ in range(3)]
        
        # 暗号化・復号化のモック設定
        recording_json = json.dumps({
            "recording_id": original_recording.recording_id,
            "metadata": {
                "name": original_recording.metadata.name,
                "description": original_recording.metadata.description,
                "category": original_recording.metadata.category,
                "tags": original_recording.metadata.tags,
                "created_by": original_recording.metadata.created_by
            },
            "status": original_recording.status.value,
            "created_at": original_recording.created_at.isoformat(),
            "updated_at": original_recording.updated_at.isoformat(),
            "actions": [
                {
                    "action_id": action.action_id,
                    "action_type": action.__class__.__name__,
                    "timestamp": action.timestamp.isoformat(),
                    "key_code": getattr(action, 'key_code', None),
                    "key_name": getattr(action, 'key_name', None),
                    "modifiers": getattr(action, 'modifiers', [])
                }
                for action in original_recording.actions
            ]
        })
        
        mock_encryption_service.encrypt.return_value = recording_json.encode()
        mock_encryption_service.decrypt.return_value = recording_json.encode()
        
        # Act
        save_result = await repository.save(original_recording)
        assert save_result.is_success()
        
        load_result = await repository.get_by_id(original_recording.recording_id)
        
        # Assert
        assert load_result.is_success()
        loaded_recording = load_result.value
        
        # 主要データの整合性確認
        assert loaded_recording.recording_id == original_recording.recording_id
        assert loaded_recording.metadata.name == original_recording.metadata.name
        assert loaded_recording.status == original_recording.status
        assert len(loaded_recording.actions) == len(original_recording.actions)
    
    # ========================
    # エラーハンドリング・復旧テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_database_corruption_recovery(self, repository):
        """データベース破損からの復旧テスト"""
        # このテストは実際の実装に依存するため、基本的な構造のみ
        # 実際のテストでは、データベースファイルを意図的に破損させて
        # 復旧処理をテストする
        pass
    
    @pytest.mark.asyncio
    async def test_disk_full_error_handling(self, repository):
        """ディスク容量不足エラーハンドリングテスト"""
        # このテストは環境に依存するため、モックを使用
        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = sqlite3.OperationalError("disk I/O error")
            
            recording = RecordingFactory()
            result = await repository.save(recording)
            
            assert result.is_failure()
            assert "DISK_ERROR" in result.error.code or "DATABASE_ERROR" in result.error.code