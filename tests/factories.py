"""
テストデータファクトリー

テストに使用するエンティティやDTOの生成を統一化するファクトリークラス群
"""

import factory
from factory import Faker, SubFactory, LazyAttribute, LazyFunction
from datetime import datetime, timezone, timedelta
import uuid
from typing import List, Optional, Dict, Any

# テスト対象のインポート  
from src.domain.entities.recording import Recording
from src.domain.entities.action import Action, KeyboardAction, MouseAction, DelayAction
from src.domain.entities.schedule import Schedule
from src.domain.value_objects import (
    RecordingMetadata, RecordingStatus, 
    ScheduleMetadata, ScheduleStatus, Trigger
)
from src.application.dto.recording_dto import (
    CreateRecordingDTO, UpdateRecordingDTO, RecordingDTO
)
from src.application.dto.schedule_dto import (
    CreateScheduleDTO, UpdateScheduleDTO, ScheduleDTO
)


# ========================
# 基本ファクトリー
# ========================

class TimestampFactory(factory.Factory):
    """タイムスタンプファクトリー"""
    
    class Meta:
        model = datetime
    
    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return datetime.now(timezone.utc)


class UUIDFactory(factory.Factory):
    """UUID ファクトリー"""
    
    class Meta:
        model = str
    
    @classmethod  
    def _create(cls, model_class, *args, **kwargs):
        return str(uuid.uuid4())


# ========================
# Value Object ファクトリー
# ========================

class RecordingMetadataFactory(factory.Factory):
    """記録メタデータファクトリー"""
    
    class Meta:
        model = RecordingMetadata
    
    name = Faker('sentence', nb_words=3)
    description = Faker('text', max_nb_chars=200)
    category = Faker('random_element', elements=('general', 'office', 'web', 'system'))
    tags = factory.LazyFunction(lambda: Faker('words', nb=3).generate())
    created_by = Faker('user_name')
    
    @factory.post_generation
    def japanese_names(obj, create, extracted, **kwargs):
        """日本語名のバリエーション"""
        if extracted:
            obj.name = extracted
        else:
            japanese_names = [
                "Webページ自動操作",
                "データ入力作業",
                "レポート生成処理", 
                "メール一括送信",
                "ファイル整理作業"
            ]
            obj.name = Faker('random_element', elements=japanese_names).generate()


class ScheduleMetadataFactory(factory.Factory):
    """スケジュールメタデータファクトリー"""
    
    class Meta:
        model = ScheduleMetadata
    
    name = Faker('sentence', nb_words=2)
    description = Faker('text', max_nb_chars=150)
    created_by = Faker('user_name')


class TriggerFactory(factory.Factory):
    """トリガーファクトリー"""
    
    class Meta:
        model = Trigger
    
    trigger_type = Faker('random_element', elements=('interval', 'daily', 'weekly', 'monthly'))
    interval_minutes = Faker('random_int', min=1, max=1440)
    start_time = LazyFunction(lambda: datetime.now(timezone.utc))
    end_time = LazyAttribute(lambda obj: obj.start_time + timedelta(days=30))
    is_active = True


# ========================
# Entity ファクトリー
# ========================

class RecordingFactory(factory.Factory):
    """記録エンティティファクトリー"""
    
    class Meta:
        model = Recording
    
    recording_id = LazyFunction(lambda: str(uuid.uuid4()))
    metadata = SubFactory(RecordingMetadataFactory)
    status = Faker('random_element', elements=list(RecordingStatus))
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = LazyAttribute(lambda obj: obj.created_at)
    actions = factory.LazyFunction(list)  # 空のリストから開始
    
    @factory.post_generation
    def add_actions(obj, create, extracted, **kwargs):
        """アクションを追加"""
        if extracted:
            obj.actions = extracted
        elif create:
            # デフォルトで2-5個のアクションを追加
            action_count = Faker('random_int', min=2, max=5).generate()
            for i in range(action_count):
                if i % 3 == 0:
                    action = KeyboardActionFactory()
                elif i % 3 == 1:
                    action = MouseActionFactory()
                else:
                    action = DelayActionFactory()
                obj.actions.append(action)


class ActionFactory(factory.Factory):
    """基本アクションファクトリー"""
    
    class Meta:
        model = Action
        abstract = True
    
    action_id = LazyFunction(lambda: str(uuid.uuid4()))
    timestamp = LazyFunction(lambda: datetime.now(timezone.utc))


class KeyboardActionFactory(ActionFactory):
    """キーボードアクションファクトリー"""
    
    class Meta:
        model = KeyboardAction
    
    key_code = Faker('random_element', elements=[
        'VK_A', 'VK_B', 'VK_C', 'VK_RETURN', 'VK_SPACE', 'VK_TAB'
    ])
    key_name = LazyAttribute(lambda obj: obj.key_code.replace('VK_', ''))
    modifiers = factory.LazyFunction(lambda: Faker('random_elements', 
        elements=['ctrl', 'shift', 'alt'], length=Faker('random_int', min=0, max=2).generate()
    ).generate())
    
    @factory.post_generation
    def japanese_input(obj, create, extracted, **kwargs):
        """日本語入力のバリエーション"""
        if extracted:
            obj.key_name = extracted
            obj.modifiers = []


class MouseActionFactory(ActionFactory):
    """マウスアクションファクトリー"""
    
    class Meta:
        model = MouseAction
    
    action_type = Faker('random_element', elements=['click', 'double_click', 'right_click', 'move'])
    x = Faker('random_int', min=0, max=1920)
    y = Faker('random_int', min=0, max=1080)
    button = Faker('random_element', elements=['left', 'right', 'middle'])


class DelayActionFactory(ActionFactory):
    """遅延アクションファクトリー"""
    
    class Meta:
        model = DelayAction
    
    duration_ms = Faker('random_int', min=100, max=5000)


class ScheduleFactory(factory.Factory):
    """スケジュールエンティティファクトリー"""
    
    class Meta:
        model = Schedule
    
    schedule_id = LazyFunction(lambda: str(uuid.uuid4()))
    recording_id = LazyFunction(lambda: str(uuid.uuid4()))
    metadata = SubFactory(ScheduleMetadataFactory)
    trigger = SubFactory(TriggerFactory)
    status = Faker('random_element', elements=list(ScheduleStatus))
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = LazyAttribute(lambda obj: obj.created_at)
    last_execution = None
    next_execution = LazyAttribute(lambda obj: obj.created_at + timedelta(hours=1))
    execution_count = Faker('random_int', min=0, max=100)
    success_count = LazyAttribute(lambda obj: Faker('random_int', min=0, max=obj.execution_count).generate())


# ========================
# DTO ファクトリー
# ========================

class CreateRecordingDTOFactory(factory.Factory):
    """記録作成DTOファクトリー"""
    
    class Meta:
        model = CreateRecordingDTO
    
    name = Faker('sentence', nb_words=3)
    description = Faker('text', max_nb_chars=200)
    category = Faker('random_element', elements=('general', 'office', 'web', 'system'))
    tags = factory.LazyFunction(lambda: Faker('words', nb=3).generate())
    auto_save = True


class UpdateRecordingDTOFactory(factory.Factory):
    """記録更新DTOファクトリー"""
    
    class Meta:
        model = UpdateRecordingDTO
    
    recording_id = LazyFunction(lambda: str(uuid.uuid4()))
    name = Faker('sentence', nb_words=3)
    description = Faker('text', max_nb_chars=200)
    category = Faker('random_element', elements=('general', 'office', 'web', 'system'))
    tags = factory.LazyFunction(lambda: Faker('words', nb=3).generate())


class RecordingDTOFactory(factory.Factory):
    """記録DTOファクトリー"""
    
    class Meta:
        model = RecordingDTO
    
    recording_id = LazyFunction(lambda: str(uuid.uuid4()))
    name = Faker('sentence', nb_words=3)
    description = Faker('text', max_nb_chars=200)
    category = Faker('random_element', elements=('general', 'office', 'web', 'system'))
    tags = factory.LazyFunction(lambda: Faker('words', nb=3).generate())
    status = Faker('random_element', elements=['RECORDING', 'STOPPED', 'COMPLETED'])
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = LazyAttribute(lambda obj: obj.created_at)
    action_count = Faker('random_int', min=0, max=100)
    estimated_duration_ms = Faker('random_int', min=1000, max=300000)


class CreateScheduleDTOFactory(factory.Factory):
    """スケジュール作成DTOファクトリー"""
    
    class Meta:
        model = CreateScheduleDTO
    
    recording_id = LazyFunction(lambda: str(uuid.uuid4()))
    name = Faker('sentence', nb_words=2)
    description = Faker('text', max_nb_chars=150)
    trigger_type = Faker('random_element', elements=('interval', 'daily', 'weekly'))
    interval_minutes = Faker('random_int', min=1, max=1440)
    start_time = LazyFunction(lambda: datetime.now(timezone.utc))
    end_time = LazyAttribute(lambda obj: obj.start_time + timedelta(days=30))
    is_active = True


# ========================
# バッチファクトリー（大量データ生成用）
# ========================

class RecordingBatchFactory:
    """記録データのバッチ生成"""
    
    @staticmethod
    def create_batch(count: int, **kwargs) -> List[Recording]:
        """指定された数の記録を生成"""
        return [RecordingFactory(**kwargs) for _ in range(count)]
    
    @staticmethod
    def create_with_categories(categories: List[str]) -> List[Recording]:
        """カテゴリ別の記録を生成"""
        recordings = []
        for category in categories:
            recording = RecordingFactory()
            recording.metadata.category = category
            recordings.append(recording)
        return recordings
    
    @staticmethod
    def create_with_date_range(start_date: datetime, end_date: datetime, count: int) -> List[Recording]:
        """日付範囲内の記録を生成"""
        recordings = []
        time_delta = (end_date - start_date) / count
        
        for i in range(count):
            created_at = start_date + (time_delta * i)
            recording = RecordingFactory()
            recording.created_at = created_at
            recording.updated_at = created_at
            recordings.append(recording)
        
        return recordings


class PerformanceTestDataFactory:
    """パフォーマンステスト用データ生成"""
    
    @staticmethod
    def create_large_recording() -> Recording:
        """大きな記録データを生成（アクション数: 1000-5000）"""
        recording = RecordingFactory()
        
        # 大量のアクションを追加
        action_count = Faker('random_int', min=1000, max=5000).generate()
        actions = []
        
        for i in range(action_count):
            if i % 3 == 0:
                actions.append(KeyboardActionFactory())
            elif i % 3 == 1:
                actions.append(MouseActionFactory())
            else:
                actions.append(DelayActionFactory())
        
        recording.actions = actions
        return recording
    
    @staticmethod
    def create_complex_schedule_set(count: int = 100) -> List[Schedule]:
        """複雑なスケジュールセットを生成"""
        schedules = []
        
        for i in range(count):
            schedule = ScheduleFactory()
            
            # 複雑な実行履歴を追加
            schedule.execution_count = Faker('random_int', min=50, max=500).generate()
            schedule.success_count = Faker('random_int', min=0, max=schedule.execution_count).generate()
            
            schedules.append(schedule)
        
        return schedules


# ========================
# エラーケース用ファクトリー
# ========================

class CorruptedDataFactory:
    """破損データのファクトリー"""
    
    @staticmethod
    def create_invalid_recording() -> Dict[str, Any]:
        """無効な記録データ"""
        return {
            "recording_id": None,  # 無効なID
            "metadata": {
                "name": "",  # 空の名前
                "category": "invalid_category",  # 無効なカテゴリ
                "tags": None  # 無効なタグ
            },
            "status": "INVALID_STATUS",  # 無効なステータス
            "created_at": "invalid_date",  # 無効な日付
            "actions": [
                {
                    "action_type": "invalid_action",  # 無効なアクション
                    "data": None
                }
            ]
        }
    
    @staticmethod
    def create_oversized_data() -> Dict[str, Any]:
        """過大なデータ"""
        return {
            "name": "A" * 10000,  # 過大な名前
            "description": "B" * 100000,  # 過大な説明
            "tags": ["tag"] * 1000,  # 過大なタグ数
            "actions": [KeyboardActionFactory() for _ in range(100000)]  # 過大なアクション数
        }


# ========================
# セキュリティテスト用ファクトリー
# ========================

class SecurityTestDataFactory:
    """セキュリティテスト用データ"""
    
    @staticmethod
    def create_sql_injection_payloads() -> List[str]:
        """SQLインジェクションペイロード"""
        return [
            "'; DROP TABLE recordings; --",
            "' UNION SELECT * FROM users --",
            "' OR '1'='1",
            "'; DELETE FROM schedules; --",
            "' AND 1=1 UNION SELECT password FROM users --"
        ]
    
    @staticmethod
    def create_xss_payloads() -> List[str]:
        """XSSペイロード"""
        return [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<svg onload=alert('xss')>",
            "';alert(String.fromCharCode(88,83,83))//';alert(String.fromCharCode(88,83,83))//\";alert(String.fromCharCode(88,83,83))//\";alert(String.fromCharCode(88,83,83))//--></SCRIPT>\">'><SCRIPT>alert(String.fromCharCode(88,83,83))</SCRIPT>"
        ]
    
    @staticmethod
    def create_path_traversal_payloads() -> List[str]:
        """パストラバーサルペイロード"""
        return [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc//passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc%252fpasswd"
        ]


# ========================
# 統合テスト用シナリオファクトリー
# ========================

class IntegrationScenarioFactory:
    """統合テスト用シナリオ"""
    
    @staticmethod
    def create_complete_workflow() -> Dict[str, Any]:
        """完全なワークフローシナリオ"""
        recording = RecordingFactory()
        schedule = ScheduleFactory()
        schedule.recording_id = recording.recording_id
        
        return {
            "recording": recording,
            "schedule": schedule,
            "workflow_steps": [
                "create_recording",
                "add_actions", 
                "save_recording",
                "create_schedule",
                "activate_schedule",
                "execute_schedule",
                "validate_results"
            ]
        }
    
    @staticmethod
    def create_error_recovery_scenario() -> Dict[str, Any]:
        """エラー回復シナリオ"""
        return {
            "initial_state": RecordingFactory(),
            "error_points": [
                "disk_full_during_save",
                "network_failure_during_sync", 
                "power_failure_during_execution",
                "memory_overflow_during_processing"
            ],
            "recovery_actions": [
                "retry_with_backoff",
                "fallback_to_local_storage",
                "partial_data_recovery",
                "user_notification"
            ],
            "expected_final_state": "stable_with_data_integrity"
        }


# ========================
# テストデータ検証ユーティリティ
# ========================

class TestDataValidator:
    """テストデータの検証"""
    
    @staticmethod
    def validate_recording(recording: Recording) -> bool:
        """記録データの妥当性チェック"""
        if not recording.recording_id:
            return False
        if not recording.metadata.name:
            return False
        if recording.created_at > recording.updated_at:
            return False
        return True
    
    @staticmethod
    def validate_schedule(schedule: Schedule) -> bool:
        """スケジュールデータの妥当性チェック"""
        if not schedule.schedule_id:
            return False
        if not schedule.recording_id:
            return False
        if schedule.trigger.start_time > schedule.trigger.end_time:
            return False
        return True
    
    @staticmethod  
    def validate_dto_consistency(dto: Any) -> bool:
        """DTOの一貫性チェック"""
        # DTOの必須フィールドチェック
        required_fields = getattr(dto.__class__, '__annotations__', {})
        for field_name in required_fields:
            if not hasattr(dto, field_name):
                return False
        return True