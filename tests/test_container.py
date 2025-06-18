"""
テスト用DIコンテナ

テスト環境に特化した依存性注入コンテナの実装
実際のサービスとモックを柔軟に切り替え可能
"""

from typing import Dict, Type, Any, Optional, Callable
from unittest.mock import Mock, AsyncMock
import tempfile
from pathlib import Path

from src.core.container import Container
from src.core.event_bus import EventBus
from src.core.result import Result, Ok, Err

# Domain層インポート
from src.domain.repositories.recording_repository import RecordingRepository
from src.domain.repositories.schedule_repository import ScheduleRepository
from src.domain.repositories.settings_repository import SettingsRepository

# Infrastructure層インポート
from src.infrastructure.repositories.sqlite_recording_repository import SqliteRecordingRepository
from src.infrastructure.repositories.sqlite_schedule_repository import SqliteScheduleRepository
from src.infrastructure.repositories.sqlite_settings_repository import SqliteSettingsRepository
from src.infrastructure.services.encryption_service import EncryptionService
from src.infrastructure.services.file_service import FileService
from src.infrastructure.services.windows_api_service import WindowsApiService

# Application層インポート
from src.application.services.recording_application_service import RecordingApplicationService
from src.application.services.playback_application_service import PlaybackApplicationService
from src.application.services.schedule_application_service import ScheduleApplicationService

# Presentation層インポート
from src.presentation.gui.viewmodels.main_viewmodel import MainViewModel
from src.presentation.gui.viewmodels.recording_viewmodel import RecordingViewModel


class TestContainerMode:
    """テストコンテナのモード定義"""
    UNIT_TEST = "unit_test"          # 全てモック
    INTEGRATION_TEST = "integration_test"  # 一部実サービス
    E2E_TEST = "e2e_test"           # 全て実サービス（テスト用設定）
    PERFORMANCE_TEST = "performance_test"  # パフォーマンス測定用


class TestContainer(Container):
    """テスト専用DIコンテナ"""
    
    def __init__(self, mode: str = TestContainerMode.UNIT_TEST, test_config: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            mode: テストモード
            test_config: テスト固有の設定
        """
        super().__init__()
        self.mode = mode
        self.test_config = test_config or {}
        self._temp_dir: Optional[Path] = None
        self._registered_mocks: Dict[Type, Mock] = {}
        
        self._setup_test_environment()
        self._register_services()
    
    def _setup_test_environment(self):
        """テスト環境のセットアップ"""
        # 一時ディレクトリの作成
        self._temp_dir = Path(tempfile.mkdtemp(prefix="ezrpa_test_"))
        
        # テスト用設定のデフォルト値
        default_config = {
            "data_dir": str(self._temp_dir),
            "database_path": str(self._temp_dir / "test.db"),
            "encryption_key": "test_key_12345678901234567890123456",
            "log_level": "DEBUG",
            "max_actions_per_recording": 10000,
            "max_recording_duration_minutes": 60
        }
        
        # ユーザー設定とマージ
        self.test_config = {**default_config, **self.test_config}
    
    def _register_services(self):
        """サービスの登録"""
        if self.mode == TestContainerMode.UNIT_TEST:
            self._register_unit_test_services()
        elif self.mode == TestContainerMode.INTEGRATION_TEST:
            self._register_integration_test_services()
        elif self.mode == TestContainerMode.E2E_TEST:
            self._register_e2e_test_services()
        elif self.mode == TestContainerMode.PERFORMANCE_TEST:
            self._register_performance_test_services()
    
    def _register_unit_test_services(self):
        """単体テスト用サービス登録（全てモック）"""
        
        # Core層
        mock_event_bus = Mock(spec=EventBus)
        mock_event_bus.publish.return_value = Ok(True)
        mock_event_bus.subscribe.return_value = "test_subscription_id"
        mock_event_bus.unsubscribe.return_value = True
        self.register(EventBus, lambda: mock_event_bus, singleton=True)
        self._registered_mocks[EventBus] = mock_event_bus
        
        # Infrastructure層 - Services
        mock_encryption = Mock(spec=EncryptionService)
        mock_encryption.encrypt.return_value = b"encrypted_test_data"
        mock_encryption.decrypt.return_value = b"decrypted_test_data"
        mock_encryption.generate_key.return_value = b"test_generated_key"
        self.register(EncryptionService, lambda: mock_encryption, singleton=True)
        self._registered_mocks[EncryptionService] = mock_encryption
        
        mock_file_service = Mock(spec=FileService)
        mock_file_service.read_file.return_value = Ok("test_file_content")
        mock_file_service.write_file.return_value = Ok(True)
        mock_file_service.delete_file.return_value = Ok(True)
        mock_file_service.file_exists.return_value = True
        self.register(FileService, lambda: mock_file_service, singleton=True)
        self._registered_mocks[FileService] = mock_file_service
        
        mock_windows_api = Mock(spec=WindowsApiService)
        mock_windows_api.get_cursor_position.return_value = (100, 100)
        mock_windows_api.send_key.return_value = Ok(True)
        mock_windows_api.send_mouse_click.return_value = Ok(True)
        self.register(WindowsApiService, lambda: mock_windows_api, singleton=True)
        self._registered_mocks[WindowsApiService] = mock_windows_api
        
        # Infrastructure層 - Repositories
        mock_recording_repo = Mock(spec=RecordingRepository)
        mock_recording_repo.save.return_value = self._create_async_result(Ok("test_recording_id"))
        mock_recording_repo.get_by_id.return_value = self._create_async_result(Ok(None))
        mock_recording_repo.get_all.return_value = self._create_async_result(Ok([]))
        mock_recording_repo.delete.return_value = self._create_async_result(Ok(True))
        self.register(RecordingRepository, lambda: mock_recording_repo, singleton=True)
        self._registered_mocks[RecordingRepository] = mock_recording_repo
        
        mock_schedule_repo = Mock(spec=ScheduleRepository)
        mock_schedule_repo.save.return_value = self._create_async_result(Ok("test_schedule_id"))
        mock_schedule_repo.get_by_id.return_value = self._create_async_result(Ok(None))
        mock_schedule_repo.get_all.return_value = self._create_async_result(Ok([]))
        mock_schedule_repo.delete.return_value = self._create_async_result(Ok(True))
        self.register(ScheduleRepository, lambda: mock_schedule_repo, singleton=True)
        self._registered_mocks[ScheduleRepository] = mock_schedule_repo
        
        mock_settings_repo = Mock(spec=SettingsRepository)
        mock_settings_repo.get.return_value = self._create_async_result(Ok("default_value"))
        mock_settings_repo.set.return_value = self._create_async_result(Ok(True))
        mock_settings_repo.get_all.return_value = self._create_async_result(Ok({}))
        self.register(SettingsRepository, lambda: mock_settings_repo, singleton=True)
        self._registered_mocks[SettingsRepository] = mock_settings_repo
        
        # Application層
        self._register_application_services_with_mocks()
    
    def _register_integration_test_services(self):
        """統合テスト用サービス登録（リポジトリは実装、外部依存はモック）"""
        
        # Core層 - 実サービス
        self.register(EventBus, lambda: EventBus(), singleton=True)
        
        # Infrastructure層 - 実サービス（テスト用設定）
        self.register(EncryptionService, 
                     lambda: EncryptionService(key=self.test_config["encryption_key"]), 
                     singleton=True)
        
        self.register(FileService, 
                     lambda: FileService(base_dir=self.test_config["data_dir"]), 
                     singleton=True)
        
        # Windows API はモック（統合テストでは実際のシステム操作は避ける）
        mock_windows_api = Mock(spec=WindowsApiService)
        mock_windows_api.get_cursor_position.return_value = (100, 100)
        mock_windows_api.send_key.return_value = Ok(True)
        mock_windows_api.send_mouse_click.return_value = Ok(True)
        self.register(WindowsApiService, lambda: mock_windows_api, singleton=True)
        self._registered_mocks[WindowsApiService] = mock_windows_api
        
        # Infrastructure層 - 実リポジトリ（インメモリDB）
        self.register(RecordingRepository, 
                     lambda: SqliteRecordingRepository(
                         ":memory:", 
                         self.get(EncryptionService)
                     ), 
                     singleton=True)
        
        self.register(ScheduleRepository, 
                     lambda: SqliteScheduleRepository(":memory:"), 
                     singleton=True)
        
        self.register(SettingsRepository, 
                     lambda: SqliteSettingsRepository(":memory:"), 
                     singleton=True)
        
        # Application層 - 実サービス
        self._register_application_services()
    
    def _register_e2e_test_services(self):
        """E2Eテスト用サービス登録（全て実サービス）"""
        
        # Core層
        self.register(EventBus, lambda: EventBus(), singleton=True)
        
        # Infrastructure層 - 実サービス
        self.register(EncryptionService, 
                     lambda: EncryptionService(key=self.test_config["encryption_key"]), 
                     singleton=True)
        
        self.register(FileService, 
                     lambda: FileService(base_dir=self.test_config["data_dir"]), 
                     singleton=True)
        
        self.register(WindowsApiService, 
                     lambda: WindowsApiService(), 
                     singleton=True)
        
        # Infrastructure層 - 実リポジトリ（ファイルDB）
        self.register(RecordingRepository, 
                     lambda: SqliteRecordingRepository(
                         self.test_config["database_path"], 
                         self.get(EncryptionService)
                     ), 
                     singleton=True)
        
        self.register(ScheduleRepository, 
                     lambda: SqliteScheduleRepository(self.test_config["database_path"]), 
                     singleton=True)
        
        self.register(SettingsRepository, 
                     lambda: SqliteSettingsRepository(self.test_config["database_path"]), 
                     singleton=True)
        
        # Application層 - 実サービス
        self._register_application_services()
    
    def _register_performance_test_services(self):
        """パフォーマンステスト用サービス登録"""
        # E2Eテストと同じ構成だが、パフォーマンス計測用の設定を追加
        self._register_e2e_test_services()
        
        # パフォーマンス計測用の設定を追加
        self.test_config.update({
            "enable_performance_logging": True,
            "max_actions_per_recording": 100000,  # より多くのアクションを許可
            "enable_caching": True
        })
    
    def _register_application_services(self):
        """Application層の実サービス登録"""
        self.register(RecordingApplicationService, 
                     lambda: RecordingApplicationService(
                         self.get(RecordingRepository),
                         self.get(EventBus)
                     ), 
                     singleton=True)
        
        self.register(PlaybackApplicationService, 
                     lambda: PlaybackApplicationService(
                         self.get(RecordingRepository),
                         self.get(WindowsApiService),
                         self.get(EventBus)
                     ), 
                     singleton=True)
        
        self.register(ScheduleApplicationService, 
                     lambda: ScheduleApplicationService(
                         self.get(ScheduleRepository),
                         self.get(RecordingRepository),
                         self.get(PlaybackApplicationService),
                         self.get(EventBus)
                     ), 
                     singleton=True)
    
    def _register_application_services_with_mocks(self):
        """Application層のモック版サービス登録"""
        # RecordingApplicationService
        mock_recording_app = Mock(spec=RecordingApplicationService)
        mock_recording_app.create_recording.return_value = self._create_async_result(Ok("test_recording_id"))
        mock_recording_app.start_recording.return_value = self._create_async_result(Ok(True))
        mock_recording_app.stop_recording.return_value = self._create_async_result(Ok(None))
        mock_recording_app.get_recording.return_value = self._create_async_result(Ok(None))
        self.register(RecordingApplicationService, lambda: mock_recording_app, singleton=True)
        self._registered_mocks[RecordingApplicationService] = mock_recording_app
        
        # PlaybackApplicationService
        mock_playback_app = Mock(spec=PlaybackApplicationService)
        mock_playback_app.start_playback.return_value = self._create_async_result(Ok("test_playback_id"))
        mock_playback_app.stop_playback.return_value = self._create_async_result(Ok(True))
        mock_playback_app.get_playback_status.return_value = self._create_async_result(Ok("STOPPED"))
        self.register(PlaybackApplicationService, lambda: mock_playback_app, singleton=True)
        self._registered_mocks[PlaybackApplicationService] = mock_playback_app
        
        # ScheduleApplicationService
        mock_schedule_app = Mock(spec=ScheduleApplicationService)
        mock_schedule_app.create_schedule.return_value = self._create_async_result(Ok("test_schedule_id"))
        mock_schedule_app.start_scheduler.return_value = self._create_async_result(Ok(True))
        mock_schedule_app.stop_scheduler.return_value = self._create_async_result(Ok(True))
        self.register(ScheduleApplicationService, lambda: mock_schedule_app, singleton=True)
        self._registered_mocks[ScheduleApplicationService] = mock_schedule_app
    
    def _create_async_result(self, result: Result) -> AsyncMock:
        """非同期結果のモック作成"""
        import asyncio
        future = asyncio.Future()
        future.set_result(result)
        async_mock = AsyncMock()
        async_mock.return_value = result
        return async_mock
    
    def get_mock(self, service_type: Type) -> Optional[Mock]:
        """登録されたモックを取得"""
        return self._registered_mocks.get(service_type)
    
    def reset_mocks(self):
        """全てのモックをリセット"""
        for mock in self._registered_mocks.values():
            mock.reset_mock()
    
    def configure_mock(self, service_type: Type, **kwargs):
        """特定のモックを設定"""
        mock = self.get_mock(service_type)
        if mock:
            for attr, value in kwargs.items():
                setattr(mock, attr, value)
    
    def inject_failure(self, service_type: Type, method_name: str, error: Exception):
        """モックにエラーを注入"""
        mock = self.get_mock(service_type)
        if mock:
            getattr(mock, method_name).side_effect = error
    
    def inject_async_failure(self, service_type: Type, method_name: str, error: Exception):
        """非同期モックにエラーを注入"""
        mock = self.get_mock(service_type)
        if mock:
            async_mock = AsyncMock()
            async_mock.side_effect = error
            setattr(mock, method_name, async_mock)
    
    def cleanup(self):
        """テスト環境のクリーンアップ"""
        try:
            # イベントバスのシャットダウン
            if not self.mode == TestContainerMode.UNIT_TEST:
                event_bus = self.get(EventBus)
                if hasattr(event_bus, 'shutdown'):
                    event_bus.shutdown()
            
            # 一時ディレクトリの削除
            if self._temp_dir and self._temp_dir.exists():
                import shutil
                shutil.rmtree(self._temp_dir, ignore_errors=True)
                
        except Exception as e:
            # クリーンアップエラーは無視（テスト結果に影響させない）
            print(f"Warning: Cleanup error: {e}")
    
    def __enter__(self):
        """コンテキストマネージャー"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャー"""
        self.cleanup()


# ========================
# ファクトリー関数
# ========================

def create_unit_test_container(**config) -> TestContainer:
    """単体テスト用コンテナ作成"""
    return TestContainer(TestContainerMode.UNIT_TEST, config)


def create_integration_test_container(**config) -> TestContainer:
    """統合テスト用コンテナ作成"""
    return TestContainer(TestContainerMode.INTEGRATION_TEST, config)


def create_e2e_test_container(**config) -> TestContainer:
    """E2Eテスト用コンテナ作成"""
    return TestContainer(TestContainerMode.E2E_TEST, config)


def create_performance_test_container(**config) -> TestContainer:
    """パフォーマンステスト用コンテナ作成"""
    return TestContainer(TestContainerMode.PERFORMANCE_TEST, config)


# ========================
# テストヘルパー関数
# ========================

def assert_mock_called_with_result(mock, method_name: str, expected_args=None, expected_kwargs=None):
    """モックが期待された引数で呼ばれたことをアサート"""
    method_mock = getattr(mock, method_name)
    if expected_args and expected_kwargs:
        method_mock.assert_called_with(*expected_args, **expected_kwargs)
    elif expected_args:
        method_mock.assert_called_with(*expected_args)
    elif expected_kwargs:
        method_mock.assert_called_with(**expected_kwargs)
    else:
        method_mock.assert_called()


def create_test_scenario(container: TestContainer, scenario_name: str) -> Dict[str, Any]:
    """テストシナリオの作成"""
    scenarios = {
        "successful_recording": {
            "description": "正常な記録作成から保存まで",
            "setup": lambda: container.reset_mocks(),
            "expected_calls": ["create_recording", "start_recording", "stop_recording", "save"]
        },
        "recording_failure": {
            "description": "記録作成の失敗",
            "setup": lambda: container.inject_async_failure(
                RecordingApplicationService, "create_recording", 
                Exception("Database connection failed")
            ),
            "expected_error": "Database connection failed"
        },
        "disk_full_scenario": {
            "description": "ディスク容量不足",
            "setup": lambda: container.inject_async_failure(
                RecordingRepository, "save",
                Exception("No space left on device")
            ),
            "expected_error": "No space left on device"
        }
    }
    
    return scenarios.get(scenario_name, {})


# ========================
# テストメトリクス収集
# ========================

class TestMetricsCollector:
    """テストメトリクス収集"""
    
    def __init__(self):
        self.call_counts: Dict[str, int] = {}
        self.execution_times: Dict[str, float] = {}
        self.memory_usage: Dict[str, float] = {}
    
    def record_call(self, service_name: str, method_name: str):
        """メソッド呼び出しを記録"""
        key = f"{service_name}.{method_name}"
        self.call_counts[key] = self.call_counts.get(key, 0) + 1
    
    def record_execution_time(self, test_name: str, duration: float):
        """実行時間を記録"""
        self.execution_times[test_name] = duration
    
    def record_memory_usage(self, test_name: str, memory_mb: float):
        """メモリ使用量を記録"""
        self.memory_usage[test_name] = memory_mb
    
    def get_summary(self) -> Dict[str, Any]:
        """メトリクスサマリーを取得"""
        return {
            "total_calls": sum(self.call_counts.values()),
            "unique_methods": len(self.call_counts),
            "avg_execution_time": sum(self.execution_times.values()) / len(self.execution_times) if self.execution_times else 0,
            "max_memory_usage": max(self.memory_usage.values()) if self.memory_usage else 0,
            "call_distribution": self.call_counts,
            "slow_tests": {k: v for k, v in self.execution_times.items() if v > 1.0}
        }


# グローバルメトリクス収集インスタンス
test_metrics = TestMetricsCollector()