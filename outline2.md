# EZRPA 再設計書 - クリーンアーキテクチャによる全面再構築

## 📋 基本情報

- **プロジェクト名**: EZRPA v2.0 (再設計版)
- **作成日**: 2025-06-17
- **目的**: 堅牢で保守しやすい、テスト可能なRPAアプリケーションの再構築

## 🔍 現在のアーキテクチャ分析

### ✅ 現在の強み

1. **モジュラー設計**: 明確な責任分離
   - `src/core/`: ビジネスロジック
   - `src/gui/`: UI コンポーネント
   - `src/models/`: データモデル
   - `src/utils/`: ユーティリティ

2. **日本語IMEサポート**: Windows API統合による完全対応
   - 変換・無変換キーの記録・再生
   - UTF-8エンコーディング対応

3. **セキュリティ基盤**: AES-256暗号化とローカル保存

4. **現代的UI**: PySide6による洗練されたインターフェース

5. **包括的ログ**: 詳細なログインフラストラクチャ

### ❌ 重大な問題点

#### 1. 結合度とアーキテクチャ問題

**問題**: 密結合とサーキュラー依存
```python
# 現在の問題例
# core/recorder.py -> gui/components (UIコンポーネント直接依存)
# gui/main_window.py -> 全モジュール (600行の巨大クラス)
```

**影響**:
- テストが困難（モックが作成できない）
- 変更の影響範囲が予測不可能
- 単体テストが実質不可能

#### 2. スレッド処理とコンカレンシー

**問題**: スレッド安全性の欠如
```python
# 現在の危険な実装例
def some_background_task():
    # ワーカースレッドからQt UIを直接操作 (クラッシュリスク)
    self.main_window.update_status("完了")
```

**影響**:
- ランダムクラッシュ
- UIフリーズ
- データ競合状態

#### 3. エラーハンドリングの一貫性欠如

**問題**: 統一されていない例外処理
```python
# 現在のパターン1: 例外を握りつぶす
try:
    risky_operation()
except:
    pass  # 危険: エラーが隠される

# 現在のパターン2: ログのみ
try:
    another_operation()
except Exception as e:
    logger.error(f"エラー: {e}")
    # ユーザーには何も通知されない
```

#### 4. データ層の問題

**問題**: データアクセスの散在
- 直接ファイルアクセスがコード全体に散在
- 一貫性のないシリアライゼーション
- データ整合性の保証なし

#### 5. テスト可能性の欠如

**問題**: 現在テストカバレッジ0%
- 大きなクラス（600行以上）
- 静的依存関係
- 外部リソースへの直接依存

## 🏗️ 新アーキテクチャ設計

### 📐 クリーンアーキテクチャの採用

```
┌─────────────────────────────────────────────────────────────┐
│                        UI Layer                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   Main Window   │  │  Recording UI   │  │ Settings UI │ │
│  │    (MVVM)       │  │    (MVVM)       │  │   (MVVM)    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                │
                        ┌───────▼────────┐
                        │   Event Bus    │
                        │ (Communication │
                        │     Hub)       │
                        └───────┬────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │  Recording      │  │   Playback      │  │  Scheduler  │ │
│  │   Service       │  │   Service       │  │   Service   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                      Domain Layer                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │    Action       │  │    Recording    │  │   Schedule  │ │
│  │   Entities      │  │   Entities      │  │  Entities   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                   Infrastructure Layer                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   Repository    │  │   File System   │  │  Security   │ │
│  │ (Data Access)   │  │    Manager      │  │   Manager   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 🔧 主要コンポーネント設計

#### 1. 依存性注入コンテナ

```python
# src/core/container.py
from typing import Dict, Type, TypeVar, Callable
from abc import ABC, abstractmethod

T = TypeVar('T')

class Container:
    """依存性注入コンテナ"""
    
    def __init__(self):
        self._services: Dict[Type, Callable] = {}
        self._singletons: Dict[Type, object] = {}
    
    def register(self, interface: Type[T], implementation: Callable[[], T], singleton: bool = False):
        """サービスを登録"""
        self._services[interface] = implementation
        if singleton:
            self._singletons[interface] = None
    
    def get(self, interface: Type[T]) -> T:
        """サービスを取得"""
        if interface in self._singletons:
            if self._singletons[interface] is None:
                self._singletons[interface] = self._services[interface]()
            return self._singletons[interface]
        
        return self._services[interface]()

# グローバルコンテナ
container = Container()
```

#### 2. イベントバス

```python
# src/core/event_bus.py
from typing import Dict, List, Callable, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class Event(ABC):
    """イベントベースクラス"""
    timestamp: float
    source: str

@dataclass
class RecordingStartedEvent(Event):
    recording_id: str

@dataclass
class RecordingStoppedEvent(Event):
    recording_id: str
    action_count: int

class EventBus:
    """イベントバス - 疎結合なコンポーネント間通信"""
    
    def __init__(self):
        self._handlers: Dict[type, List[Callable]] = {}
    
    def subscribe(self, event_type: type, handler: Callable[[Event], None]):
        """イベントハンドラーを登録"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def publish(self, event: Event):
        """イベントを発行"""
        event_type = type(event)
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                try:
                    handler(event)
                except Exception as e:
                    # ログに記録するが、他のハンドラーの実行は継続
                    logger.error(f"イベントハンドラーエラー: {e}")
```

#### 3. Result パターンによるエラーハンドリング

```python
# src/core/result.py
from typing import TypeVar, Generic, Union, Callable
from dataclasses import dataclass

T = TypeVar('T')
E = TypeVar('E')

@dataclass
class Success(Generic[T]):
    value: T
    
    def is_success(self) -> bool:
        return True
    
    def is_failure(self) -> bool:
        return False

@dataclass
class Failure(Generic[E]):
    error: E
    
    def is_success(self) -> bool:
        return False
    
    def is_failure(self) -> bool:
        return True

Result = Union[Success[T], Failure[E]]

class RecordingError:
    """記録エラーの種類"""
    PERMISSION_DENIED = "permission_denied"
    DEVICE_NOT_FOUND = "device_not_found"
    STORAGE_FULL = "storage_full"

# 使用例
def start_recording(config: RecordingConfig) -> Result[str, RecordingError]:
    try:
        # 記録開始処理
        recording_id = generate_recording_id()
        return Success(recording_id)
    except PermissionError:
        return Failure(RecordingError.PERMISSION_DENIED)
    except Exception as e:
        return Failure(str(e))
```

#### 4. リポジトリパターン

```python
# src/repositories/recording_repository.py
from abc import ABC, abstractmethod
from typing import List, Optional
from src.models.recording import Recording
from src.core.result import Result

class RecordingRepository(ABC):
    """記録データのリポジトリインターフェース"""
    
    @abstractmethod
    async def save(self, recording: Recording) -> Result[str, str]:
        """記録を保存"""
        pass
    
    @abstractmethod
    async def get_by_id(self, recording_id: str) -> Result[Recording, str]:
        """IDで記録を取得"""
        pass
    
    @abstractmethod
    async def get_all(self) -> Result[List[Recording], str]:
        """全記録を取得"""
        pass
    
    @abstractmethod
    async def delete(self, recording_id: str) -> Result[bool, str]:
        """記録を削除"""
        pass

class SqliteRecordingRepository(RecordingRepository):
    """SQLite実装のリポジトリ"""
    
    def __init__(self, db_path: str, encryption_service: EncryptionService):
        self.db_path = db_path
        self.encryption_service = encryption_service
    
    async def save(self, recording: Recording) -> Result[str, str]:
        try:
            # 暗号化してSQLiteに保存
            encrypted_data = self.encryption_service.encrypt(recording.to_json())
            # SQLite操作...
            return Success(recording.id)
        except Exception as e:
            return Failure(f"保存エラー: {str(e)}")
```

#### 5. MVVM パターンのUI

```python
# src/gui/viewmodels/main_viewmodel.py
from PySide6.QtCore import QObject, Signal, Property
from src.services.recording_service import RecordingService
from src.core.result import Result

class MainViewModel(QObject):
    """メインウィンドウのビューモデル"""
    
    # シグナル定義
    recording_status_changed = Signal(str)
    error_occurred = Signal(str)
    
    def __init__(self, recording_service: RecordingService):
        super().__init__()
        self._recording_service = recording_service
        self._is_recording = False
        self._current_recording_id = ""
    
    @Property(bool, notify=recording_status_changed)
    def is_recording(self) -> bool:
        return self._is_recording
    
    def start_recording(self):
        """記録開始"""
        result = self._recording_service.start_recording()
        if result.is_success():
            self._is_recording = True
            self._current_recording_id = result.value
            self.recording_status_changed.emit("記録中")
        else:
            self.error_occurred.emit(f"記録開始エラー: {result.error}")
    
    def stop_recording(self):
        """記録停止"""
        if not self._is_recording:
            return
        
        result = self._recording_service.stop_recording(self._current_recording_id)
        if result.is_success():
            self._is_recording = False
            self.recording_status_changed.emit("記録停止")
        else:
            self.error_occurred.emit(f"記録停止エラー: {result.error}")
```

### 🧵 スレッドアーキテクチャ

```python
# src/core/threading.py
from PySide6.QtCore import QThread, QObject, Signal
from typing import Callable, Any
import asyncio

class WorkerThread(QThread):
    """安全なワーカースレッド"""
    
    result_ready = Signal(object)
    error_occurred = Signal(str)
    
    def __init__(self, task: Callable, *args, **kwargs):
        super().__init__()
        self.task = task
        self.args = args
        self.kwargs = kwargs
    
    def run(self):
        try:
            result = self.task(*self.args, **self.kwargs)
            self.result_ready.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))

class ThreadManager:
    """スレッド管理クラス"""
    
    def __init__(self):
        self.active_threads = []
    
    def run_in_background(self, task: Callable, callback: Callable = None, error_callback: Callable = None):
        """バックグラウンドタスクを実行"""
        worker = WorkerThread(task)
        
        if callback:
            worker.result_ready.connect(callback)
        if error_callback:
            worker.error_occurred.connect(error_callback)
        
        worker.finished.connect(lambda: self.active_threads.remove(worker))
        
        self.active_threads.append(worker)
        worker.start()
    
    def shutdown(self):
        """全スレッドを安全に終了"""
        for thread in self.active_threads:
            thread.quit()
            thread.wait(5000)  # 5秒でタイムアウト
```

## 🗂️ 新しいディレクトリ構造

```
ezrpa_v2/
├── src/
│   ├── core/                    # コア機能（DI、イベント、Result等）
│   │   ├── __init__.py
│   │   ├── container.py         # 依存性注入コンテナ
│   │   ├── event_bus.py         # イベントバス
│   │   ├── result.py           # Resultパターン
│   │   └── threading.py        # スレッド管理
│   │
│   ├── domain/                  # ドメイン層（ビジネスロジック）
│   │   ├── entities/
│   │   │   ├── __init__.py
│   │   │   ├── recording.py     # 記録エンティティ
│   │   │   ├── action.py        # アクションエンティティ
│   │   │   └── schedule.py      # スケジュールエンティティ
│   │   │
│   │   ├── services/            # ドメインサービス
│   │   │   ├── __init__.py
│   │   │   ├── recording_service.py
│   │   │   ├── playback_service.py
│   │   │   └── scheduler_service.py
│   │   │
│   │   └── repositories/        # リポジトリインターフェース
│   │       ├── __init__.py
│   │       ├── recording_repository.py
│   │       └── settings_repository.py
│   │
│   ├── infrastructure/          # インフラ層（外部依存）
│   │   ├── repositories/        # リポジトリ実装
│   │   │   ├── __init__.py
│   │   │   ├── sqlite_recording_repository.py
│   │   │   └── file_settings_repository.py
│   │   │
│   │   ├── services/           # 外部サービス
│   │   │   ├── __init__.py
│   │   │   ├── encryption_service.py
│   │   │   ├── file_service.py
│   │   │   └── windows_api_service.py
│   │   │
│   │   └── adapters/           # 外部API適応
│   │       ├── __init__.py
│   │       ├── keyboard_adapter.py
│   │       └── mouse_adapter.py
│   │
│   ├── application/            # アプリケーション層
│   │   ├── __init__.py
│   │   ├── use_cases/          # ユースケース
│   │   │   ├── __init__.py
│   │   │   ├── start_recording_use_case.py
│   │   │   ├── stop_recording_use_case.py
│   │   │   └── playback_use_case.py
│   │   │
│   │   └── dto/                # データ転送オブジェクト
│   │       ├── __init__.py
│   │       ├── recording_dto.py
│   │       └── playback_dto.py
│   │
│   ├── presentation/           # プレゼンテーション層
│   │   ├── gui/
│   │   │   ├── views/          # ビュー（QMLまたはPython）
│   │   │   │   ├── __init__.py
│   │   │   │   ├── main_window.py
│   │   │   │   ├── recording_window.py
│   │   │   │   └── settings_window.py
│   │   │   │
│   │   │   ├── viewmodels/     # ビューモデル
│   │   │   │   ├── __init__.py
│   │   │   │   ├── main_viewmodel.py
│   │   │   │   ├── recording_viewmodel.py
│   │   │   │   └── settings_viewmodel.py
│   │   │   │
│   │   │   └── components/     # 再利用可能コンポーネント
│   │   │       ├── __init__.py
│   │   │       ├── action_list.py
│   │   │       └── progress_bar.py
│   │   │
│   │   └── cli/               # CLI インターフェース（将来拡張）
│   │       └── __init__.py
│   │
│   └── shared/                # 共有ユーティリティ
│       ├── __init__.py
│       ├── constants.py
│       ├── utils.py
│       └── validators.py
│
├── tests/                     # テストスイート
│   ├── unit/                  # 単体テスト
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   │
│   ├── integration/           # 統合テスト
│   │   ├── repositories/
│   │   └── services/
│   │
│   ├── e2e/                   # E2Eテスト
│   │   └── gui/
│   │
│   └── fixtures/              # テストデータ
│       ├── recordings/
│       └── settings/
│
├── docs/                      # ドキュメント
│   ├── architecture/
│   ├── api/
│   └── user_guide/
│
├── data/                      # データディレクトリ
│   ├── database/
│   ├── logs/
│   └── backups/
│
├── config/                    # 設定ファイル
│   ├── development.yaml
│   ├── production.yaml
│   └── test.yaml
│
├── scripts/                   # ユーティリティスクリプト
│   ├── setup.py
│   ├── migration.py
│   └── build.py
│
├── requirements/              # 依存関係
│   ├── base.txt
│   ├── development.txt
│   └── test.txt
│
├── main.py                    # エントリーポイント
├── pytest.ini                # pytest設定
├── mypy.ini                  # 型チェック設定
├── pyproject.toml            # プロジェクト設定
└── README.md
```

## 🧪 テスト戦略

### テストピラミッド

```
       ┌─────────────────┐
       │   E2E Tests     │  <- 少数（UI全体フロー）
       │      (5%)       │
       └─────────────────┘
      ┌───────────────────┐
      │ Integration Tests │   <- 中程度（サービス間連携）
      │      (25%)        │
      └───────────────────┘
     ┌─────────────────────┐
     │    Unit Tests       │    <- 多数（個別ロジック）
     │      (70%)          │
     └─────────────────────┘
```

### 単体テスト例

```python
# tests/unit/domain/services/test_recording_service.py
import pytest
from unittest.mock import Mock, AsyncMock
from src.domain.services.recording_service import RecordingService
from src.domain.entities.recording import Recording
from src.core.result import Success, Failure

class TestRecordingService:
    
    @pytest.fixture
    def mock_repository(self):
        return Mock()
    
    @pytest.fixture
    def mock_event_bus(self):
        return Mock()
    
    @pytest.fixture
    def recording_service(self, mock_repository, mock_event_bus):
        return RecordingService(mock_repository, mock_event_bus)
    
    @pytest.mark.asyncio
    async def test_start_recording_success(self, recording_service, mock_repository):
        # Arrange
        mock_repository.save.return_value = Success("recording_123")
        
        # Act
        result = await recording_service.start_recording("test_recording")
        
        # Assert
        assert result.is_success()
        assert result.value == "recording_123"
        mock_repository.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_recording_failure(self, recording_service, mock_repository):
        # Arrange
        mock_repository.save.return_value = Failure("保存エラー")
        
        # Act
        result = await recording_service.start_recording("test_recording")
        
        # Assert
        assert result.is_failure()
        assert result.error == "保存エラー"
```

### 統合テスト例

```python
# tests/integration/test_recording_flow.py
import pytest
from src.core.container import Container
from src.domain.services.recording_service import RecordingService
from src.infrastructure.repositories.sqlite_recording_repository import SqliteRecordingRepository

class TestRecordingFlow:
    
    @pytest.fixture
    def container(self):
        """テスト用のDIコンテナ"""
        container = Container()
        container.register(RecordingRepository, 
                         lambda: SqliteRecordingRepository(":memory:"))
        container.register(RecordingService, 
                         lambda: RecordingService(container.get(RecordingRepository)))
        return container
    
    @pytest.mark.asyncio
    async def test_complete_recording_flow(self, container):
        """記録の開始から保存まで完全フロー"""
        # Arrange
        service = container.get(RecordingService)
        
        # Act & Assert
        # 記録開始
        start_result = await service.start_recording("test_flow")
        assert start_result.is_success()
        
        recording_id = start_result.value
        
        # アクション追加
        action_result = await service.add_action(recording_id, create_test_action())
        assert action_result.is_success()
        
        # 記録停止
        stop_result = await service.stop_recording(recording_id)
        assert stop_result.is_success()
        
        # 保存確認
        get_result = await service.get_recording(recording_id)
        assert get_result.is_success()
        assert len(get_result.value.actions) == 1
```

## 📈 実装計画

### Phase 1: 基盤構築 (2週間)

**Week 1: アーキテクチャ基盤**
- [ ] 依存性注入コンテナの実装
- [ ] イベントバスの実装
- [ ] Resultパターンの実装
- [ ] 基本的なエンティティクラス

**Week 2: インフラ基盤**
- [ ] SQLiteリポジトリ実装
- [ ] 暗号化サービス実装
- [ ] ログシステム統合
- [ ] 設定管理システム

### Phase 2: コアサービス (2週間)

**Week 3: 記録・再生サービス**
- [ ] RecordingService実装
- [ ] PlaybackService実装
- [ ] Windows APIアダプター
- [ ] IMEキー処理の移植

**Week 4: スケジューラー**
- [ ] SchedulerService実装
- [ ] タスク管理システム
- [ ] Windows統合（タスクスケジューラー）

### Phase 3: データ・セキュリティ (1週間)

**Week 5: データ層とセキュリティ**
- [ ] データベーススキーマ設計
- [ ] 暗号化強化（キー管理）
- [ ] データマイグレーション機能
- [ ] バックアップ・復元機能

### Phase 4: UI統合 (2週間)

**Week 6: MVVMアーキテクチャ**
- [ ] ViewModelクラス群
- [ ] データバインディング
- [ ] エラーハンドリングUI

**Week 7: GUI完成**
- [ ] 全ウィンドウの移植
- [ ] スレッド安全性の確保
- [ ] UIテスト実装

### Phase 5: テスト・最適化 (1週間)

**Week 8: 品質保証**
- [ ] 単体テスト完成（>90%カバレッジ）
- [ ] 統合テスト実装
- [ ] パフォーマンステスト
- [ ] セキュリティ監査

## 🔄 移行戦略

### 段階的移行アプローチ

1. **準備段階**: 新アーキテクチャの実装
2. **機能移行**: 既存機能の段階的移植
3. **テスト段階**: 並行運用によるテスト
4. **切り替え**: 新システムへの完全移行

### データ移行計画

```python
# scripts/migration.py
from src.legacy import LegacyDataLoader  # 既存システム
from src.infrastructure.repositories import SqliteRecordingRepository
from src.infrastructure.services import EncryptionService

class DataMigrator:
    """既存データの新システムへの移行"""
    
    def __init__(self):
        self.legacy_loader = LegacyDataLoader()
        self.new_repository = SqliteRecordingRepository()
        self.encryption_service = EncryptionService()
    
    async def migrate_recordings(self):
        """記録データの移行"""
        # 既存JSONファイルを読み込み
        legacy_recordings = self.legacy_loader.load_all_recordings()
        
        for legacy_recording in legacy_recordings:
            # 新形式に変換
            new_recording = self.convert_to_new_format(legacy_recording)
            
            # 新システムに保存
            result = await self.new_repository.save(new_recording)
            if result.is_failure():
                logger.error(f"移行失敗: {result.error}")
        
        logger.info(f"{len(legacy_recordings)}件の記録を移行しました")
```

## 📊 期待される改善効果

### 定量的改善

| 指標 | 現在 | 目標 | 改善率 |
|------|------|------|--------|
| テストカバレッジ | 0% | >90% | +90% |
| 結合度 | 高 | 低 | -50% |
| 平均クラスサイズ | 600行 | <200行 | -67% |
| バグ修正時間 | 4時間 | 1時間 | -75% |
| 新機能追加時間 | 2日 | 0.5日 | -75% |

### 定性的改善

- **保守性**: モジュラー設計により変更影響を局所化
- **テスト可能性**: 依存性注入により完全なテストカバレッジを実現
- **拡張性**: プラグインアーキテクチャで新機能追加が容易
- **安定性**: 適切なエラーハンドリングでクラッシュを防止
- **パフォーマンス**: 非同期処理とキャッシュでレスポンス向上

## 🚀 実装開始の準備

### 必要なツール

```bash
# 開発環境セットアップ
pip install -r requirements/development.txt

# 品質管理ツール
pip install black mypy pylint pytest pytest-cov pytest-asyncio

# データベース
pip install sqlalchemy alembic

# 非同期処理
pip install asyncio aiofiles
```

### 開発フロー

1. **FeatureBranch**: 機能ごとのブランチ作成
2. **TDD**: テスト駆動開発の実践
3. **CodeReview**: プルリクエストによるコードレビュー
4. **CI/CD**: 自動テスト・デプロイパイプライン

### 成功指標の測定

```python
# scripts/metrics.py
class MetricsCollector:
    """プロジェクトメトリクスの収集"""
    
    def calculate_coupling_metrics(self):
        """結合度の測定"""
        # 依存関係分析
        # サイクル複雑度計算
        pass
    
    def calculate_test_coverage(self):
        """テストカバレッジの測定"""
        # pytest-covによるカバレッジ測定
        pass
    
    def calculate_maintainability_index(self):
        """保守性指標の計算"""
        # Halstead複雑度、サイクロマティック複雑度等
        pass
```

---

## 📝 まとめ

この再設計により、EZRPAは以下の特徴を持つ近代的なアプリケーションに生まれ変わります：

- **堅牢性**: 適切なエラーハンドリングと回復機能
- **保守性**: クリーンアーキテクチャによる明確な責任分離
- **テスト可能性**: 90%以上のテストカバレッジ
- **拡張性**: 新機能追加が容易な設計
- **パフォーマンス**: 非同期処理による高速化

8週間の実装期間で、技術的負債を解消し、長期的に持続可能な高品質なRPAアプリケーションを構築します。

**開始準備完了。実装フェーズに進む準備ができました。**