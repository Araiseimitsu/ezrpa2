"""
pytest設定とグローバルフィクスチャ

EZRPA v2.0のテスト基盤の中央設定ファイル
"""

import pytest
import asyncio
import os
import tempfile
import shutil
from typing import Any, Dict, Generator
from unittest.mock import Mock, AsyncMock
from pathlib import Path

# テスト対象のインポート
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.container import Container
from src.core.event_bus import EventBus
from src.core.result import Result, Ok, Err
from src.domain.entities.recording import Recording
from src.domain.entities.action import Action
from src.domain.entities.schedule import Schedule
from src.infrastructure.services.encryption_service import EncryptionService
from src.infrastructure.services.file_service import FileService


# テストマーカー自動追加
def pytest_collection_modifyitems(config, items):
    """テストアイテムに自動的にマーカーを追加"""
    for item in items:
        # パスベースのマーカー追加
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        
        # ファイル名ベースのマーカー追加
        if "database" in item.name:
            item.add_marker(pytest.mark.database)
        if "gui" in item.name:
            item.add_marker(pytest.mark.gui)
        if "slow" in item.name:
            item.add_marker(pytest.mark.slow)


# ========================
# 基本フィクスチャ
# ========================

@pytest.fixture(scope="session")
def event_loop():
    """セッション全体で使用するイベントループ"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """一時ディレクトリ"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def test_data_dir() -> Path:
    """テストデータディレクトリ"""
    return Path(__file__).parent / "fixtures"


# ========================
# DI コンテナフィクスチャ
# ========================

@pytest.fixture
def mock_container() -> Container:
    """テスト用DIコンテナ"""
    container = Container()
    
    # モックサービスを登録
    container.register(EventBus, lambda: Mock(spec=EventBus))
    container.register(EncryptionService, lambda: Mock(spec=EncryptionService))
    container.register(FileService, lambda: Mock(spec=FileService))
    
    return container


@pytest.fixture
def real_container() -> Container:
    """実際のサービスを含むDIコンテナ（統合テスト用）"""
    container = Container()
    
    # 実際のサービスを登録
    container.register(EventBus, EventBus, singleton=True)
    container.register(EncryptionService, EncryptionService, singleton=True)
    container.register(FileService, FileService, singleton=True)
    
    return container


# ========================
# イベントバスフィクスチャ
# ========================

@pytest.fixture
def event_bus() -> EventBus:
    """実際のイベントバス"""
    bus = EventBus()
    yield bus
    bus.shutdown()


@pytest.fixture
def mock_event_bus() -> Mock:
    """モックイベントバス"""
    mock_bus = Mock(spec=EventBus)
    mock_bus.publish.return_value = Ok(True)
    mock_bus.subscribe.return_value = "subscription_id"
    mock_bus.unsubscribe.return_value = True
    return mock_bus


# ========================
# エンティティフィクスチャ
# ========================

@pytest.fixture
def sample_recording() -> Recording:
    """サンプル記録エンティティ"""
    from src.domain.value_objects import RecordingMetadata, RecordingStatus
    from datetime import datetime, timezone
    
    metadata = RecordingMetadata(
        name="テスト記録",
        description="テスト用の記録です",
        category="test",
        tags=["test", "sample"],
        created_by="test_user"
    )
    
    return Recording(
        recording_id="test_recording_001",
        metadata=metadata,
        status=RecordingStatus.STOPPED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def sample_action() -> Action:
    """サンプルアクションエンティティ"""
    from src.domain.entities.action import ActionTypes, KeyboardAction
    from datetime import datetime, timezone
    
    return KeyboardAction(
        action_id="test_action_001",
        timestamp=datetime.now(timezone.utc),
        key_code="VK_A",
        key_name="A",
        modifiers=[]
    )


@pytest.fixture
def sample_schedule() -> Schedule:
    """サンプルスケジュールエンティティ"""
    from src.domain.value_objects import ScheduleMetadata, ScheduleStatus, Trigger
    from datetime import datetime, timezone, timedelta
    
    metadata = ScheduleMetadata(
        name="テストスケジュール",
        description="テスト用のスケジュールです",
        created_by="test_user"
    )
    
    trigger = Trigger(
        trigger_type="interval",
        interval_minutes=60,
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(days=1)
    )
    
    return Schedule(
        schedule_id="test_schedule_001",
        recording_id="test_recording_001",
        metadata=metadata,
        trigger=trigger,
        status=ScheduleStatus.ACTIVE,
        created_at=datetime.now(timezone.utc)
    )


# ========================
# リポジトリモックフィクスチャ
# ========================

@pytest.fixture
def mock_recording_repository():
    """モック記録リポジトリ"""
    from src.domain.repositories.recording_repository import RecordingRepository
    
    mock_repo = Mock(spec=RecordingRepository)
    mock_repo.save.return_value = asyncio.create_future()
    mock_repo.save.return_value.set_result(Ok("saved_id"))
    
    mock_repo.get_by_id.return_value = asyncio.create_future()
    mock_repo.get_by_id.return_value.set_result(Ok(None))
    
    mock_repo.get_all.return_value = asyncio.create_future() 
    mock_repo.get_all.return_value.set_result(Ok([]))
    
    mock_repo.delete.return_value = asyncio.create_future()
    mock_repo.delete.return_value.set_result(Ok(True))
    
    return mock_repo


@pytest.fixture
def mock_schedule_repository():
    """モックスケジュールリポジトリ"""
    from src.domain.repositories.schedule_repository import ScheduleRepository
    
    mock_repo = Mock(spec=ScheduleRepository)
    mock_repo.save.return_value = asyncio.create_future()
    mock_repo.save.return_value.set_result(Ok("saved_id"))
    
    mock_repo.get_by_id.return_value = asyncio.create_future()
    mock_repo.get_by_id.return_value.set_result(Ok(None))
    
    mock_repo.get_all.return_value = asyncio.create_future()
    mock_repo.get_all.return_value.set_result(Ok([]))
    
    mock_repo.delete.return_value = asyncio.create_future()
    mock_repo.delete.return_value.set_result(Ok(True))
    
    return mock_repo


# ========================
# サービスモックフィクスチャ 
# ========================

@pytest.fixture
def mock_encryption_service():
    """モック暗号化サービス"""
    mock_service = Mock(spec=EncryptionService)
    mock_service.encrypt.return_value = b"encrypted_data"
    mock_service.decrypt.return_value = b"decrypted_data"
    mock_service.generate_key.return_value = b"test_key"
    return mock_service


@pytest.fixture
def mock_file_service():
    """モックファイルサービス"""
    mock_service = Mock(spec=FileService)
    mock_service.read_file.return_value = Ok("file_content")
    mock_service.write_file.return_value = Ok(True)
    mock_service.delete_file.return_value = Ok(True)
    mock_service.file_exists.return_value = True
    return mock_service


# ========================
# データベーステスト用フィクスチャ
# ========================

@pytest.fixture
def in_memory_db_path() -> str:
    """インメモリSQLiteデータベースパス"""
    return ":memory:"


@pytest.fixture
def temp_db_path(temp_dir: Path) -> str:
    """一時ファイルSQLiteデータベースパス"""
    db_path = temp_dir / "test.db"
    return str(db_path)


# ========================
# 環境設定フィクスチャ
# ========================

@pytest.fixture
def test_environment():
    """テスト環境設定"""
    original_env = dict(os.environ)
    
    # テスト用環境変数設定
    os.environ.update({
        "EZRPA_ENV": "test",
        "EZRPA_LOG_LEVEL": "DEBUG",
        "EZRPA_DATA_DIR": tempfile.mkdtemp(),
        "EZRPA_ENCRYPTION_KEY": "test_key_123456789012345678901234"
    })
    
    yield
    
    # 環境変数復元
    os.environ.clear()
    os.environ.update(original_env)


# ========================
# パフォーマンステスト用フィクスチャ
# ========================

@pytest.fixture
def performance_config() -> Dict[str, Any]:
    """パフォーマンステスト設定"""
    return {
        "max_execution_time": 1.0,  # 秒
        "max_memory_usage": 100,     # MB
        "benchmark_rounds": 10,
        "warmup_rounds": 3
    }


# ========================
# GUIテスト用フィクスチャ
# ========================

@pytest.fixture
def qt_app():
    """Qt アプリケーション（GUI テスト用）"""
    try:
        from PySide6.QtWidgets import QApplication
        import sys
        
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        yield app
        
        # クリーンアップ
        app.quit()
    except ImportError:
        pytest.skip("PySide6 not installed, skipping GUI tests")


# ========================
# 統合テスト用フィクスチャ
# ========================

@pytest.fixture
async def integrated_system(real_container: Container, temp_dir: Path):
    """統合テスト用の完全なシステム"""
    # システムの初期化
    system_config = {
        "data_dir": str(temp_dir),
        "encryption_enabled": True,
        "log_level": "DEBUG"
    }
    
    # 統合されたサービス群の初期化
    event_bus = real_container.get(EventBus)
    
    yield {
        "container": real_container,
        "event_bus": event_bus,
        "config": system_config,
        "data_dir": temp_dir
    }
    
    # クリーンアップ
    event_bus.shutdown()


# ========================
# セキュリティテスト用フィクスチャ
# ========================

@pytest.fixture
def security_test_data():
    """セキュリティテスト用のデータセット"""
    return {
        "sql_injection_payloads": [
            "'; DROP TABLE recordings; --",
            "' UNION SELECT * FROM users --",
            "' OR '1'='1",
        ],
        "xss_payloads": [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
        ],
        "file_path_traversal": [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc//passwd",
        ],
        "large_inputs": "A" * 10000,
        "unicode_attacks": [
            "\u0000",  # null byte
            "\ufeff",  # BOM
            "\u202e",  # right-to-left override
        ]
    }


# ========================
# エラーハンドリングテスト用フィクスチャ
# ========================

@pytest.fixture
def error_scenarios():
    """エラーシナリオ用のテストデータ"""
    return {
        "network_errors": [
            "Connection timeout",
            "Connection refused", 
            "DNS resolution failed"
        ],
        "file_errors": [
            "Permission denied",
            "File not found",
            "Disk full"
        ],
        "database_errors": [
            "Connection lost",
            "Lock timeout",
            "Constraint violation"
        ],
        "memory_errors": [
            "Out of memory",
            "Stack overflow"
        ]
    }


# ========================
# カスタムアサーション
# ========================

def assert_result_success(result: Result, message: str = ""):
    """Result が成功していることをアサート"""
    assert result.is_success(), f"Expected success but got failure: {result.error if hasattr(result, 'error') else 'Unknown error'}. {message}"


def assert_result_failure(result: Result, message: str = ""):
    """Result が失敗していることをアサート"""
    assert result.is_failure(), f"Expected failure but got success: {result.value if hasattr(result, 'value') else 'Unknown value'}. {message}"


# pytestプラグインとして登録
pytest.assert_result_success = assert_result_success
pytest.assert_result_failure = assert_result_failure