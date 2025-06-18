"""
Value Objects の単体テスト

ドメイン層のValue Objectsの不変性とビジネスルールのテスト
"""

import pytest
from datetime import datetime, timezone, timedelta, time
from typing import List

from src.domain.value_objects import (
    RecordingMetadata, RecordingStatus,
    ScheduleMetadata, ScheduleStatus, Trigger,
    ExecutionHistory, ExecutionResult,
    ActionMetadata
)


class TestRecordingMetadata:
    """RecordingMetadata Value Object のテスト"""
    
    def test_recording_metadata_creation(self):
        """記録メタデータの作成"""
        # Arrange & Act
        metadata = RecordingMetadata(
            name="Test Recording",
            description="Test description",
            category="office",
            tags=["automation", "test"],
            created_by="test_user"
        )
        
        # Assert
        assert metadata.name == "Test Recording"
        assert metadata.description == "Test description"
        assert metadata.category == "office"
        assert metadata.tags == ["automation", "test"]
        assert metadata.created_by == "test_user"
    
    def test_recording_metadata_immutability(self):
        """記録メタデータの不変性"""
        # Arrange
        metadata = RecordingMetadata(
            name="Original",
            description="Original description",
            category="general",
            tags=["tag1"],
            created_by="user1"
        )
        
        # Act & Assert - フィールドは直接変更できない（dataclassのfrozen=True）
        with pytest.raises(AttributeError):
            metadata.name = "Changed"
    
    def test_recording_metadata_validation(self):
        """記録メタデータの妥当性検証"""
        # 正常ケース
        valid_metadata = RecordingMetadata(
            name="Valid Recording",
            description="Valid description",
            category="office",
            tags=["test"],
            created_by="user"
        )
        assert valid_metadata.is_valid() is True
        
        # 無効ケース1: 空の名前
        with pytest.raises(ValueError):
            RecordingMetadata(
                name="",
                description="Description",
                category="office",
                tags=[],
                created_by="user"
            )
        
        # 無効ケース2: Noneの名前
        with pytest.raises(TypeError):
            RecordingMetadata(
                name=None,
                description="Description",
                category="office",
                tags=[],
                created_by="user"
            )
        
        # 無効ケース3: 無効なカテゴリ
        with pytest.raises(ValueError):
            RecordingMetadata(
                name="Test",
                description="Description",
                category="invalid_category",
                tags=[],
                created_by="user"
            )
    
    def test_recording_metadata_tag_operations(self):
        """タグ操作のテスト"""
        # Arrange
        metadata = RecordingMetadata(
            name="Test",
            description="Description",
            category="general",
            tags=["tag1", "tag2"],
            created_by="user"
        )
        
        # Act & Assert
        assert metadata.has_tag("tag1") is True
        assert metadata.has_tag("tag3") is False
        assert metadata.tag_count == 2
        
        # タグの追加（新しいインスタンスを返す）
        new_metadata = metadata.add_tag("tag3")
        assert new_metadata.has_tag("tag3") is True
        assert new_metadata.tag_count == 3
        assert metadata.tag_count == 2  # 元のインスタンスは変わらない
        
        # タグの削除
        removed_metadata = new_metadata.remove_tag("tag1")
        assert removed_metadata.has_tag("tag1") is False
        assert removed_metadata.tag_count == 2
    
    def test_recording_metadata_category_validation(self):
        """カテゴリの妥当性検証"""
        valid_categories = ["general", "office", "web", "system", "custom"]
        
        for category in valid_categories:
            metadata = RecordingMetadata(
                name="Test",
                description="Description",
                category=category,
                tags=[],
                created_by="user"
            )
            assert metadata.category == category
    
    def test_recording_metadata_equality(self):
        """記録メタデータの等価性"""
        # Arrange
        metadata1 = RecordingMetadata(
            name="Test",
            description="Description",
            category="general",
            tags=["tag1"],
            created_by="user"
        )
        
        metadata2 = RecordingMetadata(
            name="Test",
            description="Description",
            category="general",
            tags=["tag1"],
            created_by="user"
        )
        
        metadata3 = RecordingMetadata(
            name="Different",
            description="Description",
            category="general",
            tags=["tag1"],
            created_by="user"
        )
        
        # Act & Assert
        assert metadata1 == metadata2
        assert metadata1 != metadata3
        assert hash(metadata1) == hash(metadata2)
        assert hash(metadata1) != hash(metadata3)


class TestRecordingStatus:
    """RecordingStatus Enum のテスト"""
    
    def test_recording_status_values(self):
        """記録ステータスの値確認"""
        expected_statuses = {
            'STOPPED', 'RECORDING', 'PAUSED', 'COMPLETED', 'FAILED'
        }
        actual_statuses = {status.value for status in RecordingStatus}
        assert actual_statuses == expected_statuses
    
    def test_recording_status_transitions(self):
        """記録ステータス遷移の妥当性"""
        # 有効な遷移パターン
        valid_transitions = {
            RecordingStatus.STOPPED: [RecordingStatus.RECORDING, RecordingStatus.COMPLETED],
            RecordingStatus.RECORDING: [RecordingStatus.PAUSED, RecordingStatus.STOPPED, RecordingStatus.COMPLETED, RecordingStatus.FAILED],
            RecordingStatus.PAUSED: [RecordingStatus.RECORDING, RecordingStatus.STOPPED],
            RecordingStatus.COMPLETED: [],  # 終了状態
            RecordingStatus.FAILED: [RecordingStatus.RECORDING]  # 再開可能
        }
        
        for from_status, valid_to_statuses in valid_transitions.items():
            for to_status in RecordingStatus:
                expected_valid = to_status in valid_to_statuses
                actual_valid = from_status.can_transition_to(to_status)
                assert actual_valid == expected_valid, f"{from_status} -> {to_status}"
    
    def test_recording_status_properties(self):
        """記録ステータスのプロパティ"""
        # 実行中かどうか
        assert RecordingStatus.RECORDING.is_active() is True
        assert RecordingStatus.PAUSED.is_active() is False
        assert RecordingStatus.STOPPED.is_active() is False
        
        # 終了状態かどうか
        assert RecordingStatus.COMPLETED.is_terminal() is True
        assert RecordingStatus.FAILED.is_terminal() is True
        assert RecordingStatus.RECORDING.is_terminal() is False


class TestScheduleMetadata:
    """ScheduleMetadata Value Object のテスト"""
    
    def test_schedule_metadata_creation(self):
        """スケジュールメタデータの作成"""
        # Arrange & Act
        metadata = ScheduleMetadata(
            name="Daily Backup",
            description="Daily backup schedule",
            created_by="admin"
        )
        
        # Assert
        assert metadata.name == "Daily Backup"
        assert metadata.description == "Daily backup schedule"
        assert metadata.created_by == "admin"
    
    def test_schedule_metadata_validation(self):
        """スケジュールメタデータの妥当性検証"""
        # 正常ケース
        valid_metadata = ScheduleMetadata(
            name="Valid Schedule",
            description="Valid description",
            created_by="user"
        )
        assert valid_metadata.is_valid() is True
        
        # 無効ケース: 空の名前
        with pytest.raises(ValueError):
            ScheduleMetadata(
                name="",
                description="Description",
                created_by="user"
            )


class TestScheduleStatus:
    """ScheduleStatus Enum のテスト"""
    
    def test_schedule_status_values(self):
        """スケジュールステータスの値確認"""
        expected_statuses = {
            'ACTIVE', 'INACTIVE', 'PAUSED', 'EXPIRED', 'ERROR'
        }
        actual_statuses = {status.value for status in ScheduleStatus}
        assert actual_statuses == expected_statuses
    
    def test_schedule_status_transitions(self):
        """スケジュールステータス遷移の妥当性"""
        valid_transitions = {
            ScheduleStatus.ACTIVE: [ScheduleStatus.PAUSED, ScheduleStatus.INACTIVE, ScheduleStatus.ERROR],
            ScheduleStatus.INACTIVE: [ScheduleStatus.ACTIVE],
            ScheduleStatus.PAUSED: [ScheduleStatus.ACTIVE, ScheduleStatus.INACTIVE],
            ScheduleStatus.EXPIRED: [ScheduleStatus.INACTIVE],  # 期限切れは無効化のみ
            ScheduleStatus.ERROR: [ScheduleStatus.ACTIVE, ScheduleStatus.INACTIVE]  # エラーから復旧可能
        }
        
        for from_status, valid_to_statuses in valid_transitions.items():
            for to_status in ScheduleStatus:
                expected_valid = to_status in valid_to_statuses
                actual_valid = from_status.can_transition_to(to_status)
                assert actual_valid == expected_valid, f"{from_status} -> {to_status}"


class TestTrigger:
    """Trigger Value Object のテスト"""
    
    def test_trigger_interval_creation(self):
        """インターバルトリガーの作成"""
        # Arrange
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(days=30)
        
        # Act
        trigger = Trigger(
            trigger_type="interval",
            interval_minutes=30,
            start_time=start_time,
            end_time=end_time,
            is_active=True
        )
        
        # Assert
        assert trigger.trigger_type == "interval"
        assert trigger.interval_minutes == 30
        assert trigger.start_time == start_time
        assert trigger.end_time == end_time
        assert trigger.is_active is True
    
    def test_trigger_daily_creation(self):
        """日次トリガーの作成"""
        # Arrange
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(days=30)
        daily_time = time(14, 30)  # 14:30
        
        # Act
        trigger = Trigger(
            trigger_type="daily",
            daily_time=daily_time,
            start_time=start_time,
            end_time=end_time,
            is_active=True
        )
        
        # Assert
        assert trigger.trigger_type == "daily"
        assert trigger.daily_time == daily_time
        assert trigger.start_time == start_time
        assert trigger.end_time == end_time
    
    def test_trigger_weekly_creation(self):
        """週次トリガーの作成"""
        # Arrange
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(days=30)
        weekly_days = [1, 3, 5]  # 月・水・金
        weekly_time = time(9, 0)  # 9:00
        
        # Act
        trigger = Trigger(
            trigger_type="weekly",
            weekly_days=weekly_days,
            weekly_time=weekly_time,
            start_time=start_time,
            end_time=end_time,
            is_active=True
        )
        
        # Assert
        assert trigger.trigger_type == "weekly"
        assert trigger.weekly_days == weekly_days
        assert trigger.weekly_time == weekly_time
    
    def test_trigger_validation(self):
        """トリガーの妥当性検証"""
        now = datetime.now(timezone.utc)
        
        # 正常ケース: インターバル
        valid_trigger = Trigger(
            trigger_type="interval",
            interval_minutes=60,
            start_time=now,
            end_time=now + timedelta(days=1),
            is_active=True
        )
        assert valid_trigger.is_valid() is True
        
        # 無効ケース1: 負のインターバル
        with pytest.raises(ValueError):
            Trigger(
                trigger_type="interval",
                interval_minutes=-10,
                start_time=now,
                end_time=now + timedelta(days=1),
                is_active=True
            )
        
        # 無効ケース2: end_time < start_time
        with pytest.raises(ValueError):
            Trigger(
                trigger_type="interval",
                interval_minutes=60,
                start_time=now,
                end_time=now - timedelta(days=1),
                is_active=True
            )
        
        # 無効ケース3: 無効なトリガータイプ
        with pytest.raises(ValueError):
            Trigger(
                trigger_type="invalid",
                start_time=now,
                end_time=now + timedelta(days=1),
                is_active=True
            )
    
    def test_trigger_next_execution_calculation(self):
        """次回実行時間の計算"""
        # インターバルトリガー
        now = datetime.now(timezone.utc)
        interval_trigger = Trigger(
            trigger_type="interval",
            interval_minutes=30,
            start_time=now,
            end_time=now + timedelta(days=1),
            is_active=True
        )
        
        next_exec = interval_trigger.calculate_next_execution(now)
        expected_time = now + timedelta(minutes=30)
        assert abs((next_exec - expected_time).total_seconds()) < 1
        
        # 日次トリガー
        daily_trigger = Trigger(
            trigger_type="daily",
            daily_time=time(14, 30),
            start_time=now,
            end_time=now + timedelta(days=30),
            is_active=True
        )
        
        next_daily = daily_trigger.calculate_next_execution(now)
        assert next_daily.hour == 14
        assert next_daily.minute == 30
    
    def test_trigger_is_expired(self):
        """トリガーの期限切れ判定"""
        now = datetime.now(timezone.utc)
        
        # 有効なトリガー
        valid_trigger = Trigger(
            trigger_type="interval",
            interval_minutes=60,
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=1),
            is_active=True
        )
        assert valid_trigger.is_expired(now) is False
        
        # 期限切れトリガー
        expired_trigger = Trigger(
            trigger_type="interval",
            interval_minutes=60,
            start_time=now - timedelta(hours=2),
            end_time=now - timedelta(hours=1),
            is_active=True
        )
        assert expired_trigger.is_expired(now) is True


class TestExecutionResult:
    """ExecutionResult Value Object のテスト"""
    
    def test_execution_result_success(self):
        """成功実行結果の作成"""
        # Arrange
        execution_time = datetime.now(timezone.utc)
        start_time = execution_time
        end_time = execution_time + timedelta(seconds=30)
        
        # Act
        result = ExecutionResult(
            execution_id="exec_001",
            execution_time=execution_time,
            start_time=start_time,
            end_time=end_time,
            success=True,
            error_message=None,
            actions_executed=10,
            actions_failed=0
        )
        
        # Assert
        assert result.execution_id == "exec_001"
        assert result.success is True
        assert result.error_message is None
        assert result.actions_executed == 10
        assert result.actions_failed == 0
        assert result.duration_seconds == 30
    
    def test_execution_result_failure(self):
        """失敗実行結果の作成"""
        # Arrange
        execution_time = datetime.now(timezone.utc)
        start_time = execution_time
        end_time = execution_time + timedelta(seconds=15)
        
        # Act
        result = ExecutionResult(
            execution_id="exec_002",
            execution_time=execution_time,
            start_time=start_time,
            end_time=end_time,
            success=False,
            error_message="Application not found",
            actions_executed=3,
            actions_failed=7
        )
        
        # Assert
        assert result.execution_id == "exec_002"
        assert result.success is False
        assert result.error_message == "Application not found"
        assert result.actions_executed == 3
        assert result.actions_failed == 7
        assert result.duration_seconds == 15
    
    def test_execution_result_properties(self):
        """実行結果のプロパティ"""
        # Arrange
        execution_time = datetime.now(timezone.utc)
        start_time = execution_time
        end_time = execution_time + timedelta(seconds=45)
        
        result = ExecutionResult(
            execution_id="exec_003",
            execution_time=execution_time,
            start_time=start_time,
            end_time=end_time,
            success=True,
            error_message=None,
            actions_executed=15,
            actions_failed=3
        )
        
        # Act & Assert
        assert result.total_actions == 18  # 15 + 3
        assert result.success_rate == 15/18  # 約0.833
        assert result.duration_seconds == 45
        assert result.duration_minutes == 0.75
    
    def test_execution_result_validation(self):
        """実行結果の妥当性検証"""
        execution_time = datetime.now(timezone.utc)
        
        # 正常ケース
        valid_result = ExecutionResult(
            execution_id="valid",
            execution_time=execution_time,
            start_time=execution_time,
            end_time=execution_time + timedelta(seconds=30),
            success=True,
            error_message=None,
            actions_executed=10,
            actions_failed=0
        )
        assert valid_result.is_valid() is True
        
        # 無効ケース1: end_time < start_time
        with pytest.raises(ValueError):
            ExecutionResult(
                execution_id="invalid1",
                execution_time=execution_time,
                start_time=execution_time,
                end_time=execution_time - timedelta(seconds=10),
                success=True,
                error_message=None,
                actions_executed=10,
                actions_failed=0
            )
        
        # 無効ケース2: 負のアクション数
        with pytest.raises(ValueError):
            ExecutionResult(
                execution_id="invalid2",
                execution_time=execution_time,
                start_time=execution_time,
                end_time=execution_time + timedelta(seconds=30),
                success=True,
                error_message=None,
                actions_executed=-1,
                actions_failed=0
            )


class TestExecutionHistory:
    """ExecutionHistory Value Object のテスト"""
    
    def test_execution_history_creation(self):
        """実行履歴の作成"""
        # Arrange
        execution_time = datetime.now(timezone.utc)
        result = ExecutionResult(
            execution_id="exec_001",
            execution_time=execution_time,
            start_time=execution_time,
            end_time=execution_time + timedelta(seconds=30),
            success=True,
            error_message=None,
            actions_executed=10,
            actions_failed=0
        )
        
        # Act
        history = ExecutionHistory(
            history_id="hist_001",
            result=result,
            recorded_at=execution_time
        )
        
        # Assert
        assert history.history_id == "hist_001"
        assert history.result == result
        assert history.recorded_at == execution_time
    
    def test_execution_history_immutability(self):
        """実行履歴の不変性"""
        # Arrange
        execution_time = datetime.now(timezone.utc)
        result = ExecutionResult(
            execution_id="exec_001",
            execution_time=execution_time,
            start_time=execution_time,
            end_time=execution_time + timedelta(seconds=30),
            success=True,
            error_message=None,
            actions_executed=10,
            actions_failed=0
        )
        
        history = ExecutionHistory(
            history_id="hist_001",
            result=result,
            recorded_at=execution_time
        )
        
        # Act & Assert - フィールドは直接変更できない
        with pytest.raises(AttributeError):
            history.result = result


class TestActionMetadata:
    """ActionMetadata Value Object のテスト"""
    
    def test_action_metadata_creation(self):
        """アクションメタデータの作成"""
        # Arrange & Act
        metadata = ActionMetadata(
            name="Click Button",
            description="Click the submit button",
            category="ui_interaction",
            estimated_duration_ms=100,
            retry_count=3,
            timeout_ms=5000
        )
        
        # Assert
        assert metadata.name == "Click Button"
        assert metadata.description == "Click the submit button"
        assert metadata.category == "ui_interaction"
        assert metadata.estimated_duration_ms == 100
        assert metadata.retry_count == 3
        assert metadata.timeout_ms == 5000
    
    def test_action_metadata_validation(self):
        """アクションメタデータの妥当性検証"""
        # 正常ケース
        valid_metadata = ActionMetadata(
            name="Valid Action",
            description="Valid description",
            category="general",
            estimated_duration_ms=50,
            retry_count=1,
            timeout_ms=1000
        )
        assert valid_metadata.is_valid() is True
        
        # 無効ケース1: 負の推定時間
        with pytest.raises(ValueError):
            ActionMetadata(
                name="Invalid Action",
                description="Description",
                category="general",
                estimated_duration_ms=-10,
                retry_count=1,
                timeout_ms=1000
            )
        
        # 無効ケース2: 負のリトライ回数
        with pytest.raises(ValueError):
            ActionMetadata(
                name="Invalid Action",
                description="Description",
                category="general",
                estimated_duration_ms=50,
                retry_count=-1,
                timeout_ms=1000
            )


class TestValueObjectsIntegration:
    """Value Objects の統合テスト"""
    
    def test_complex_trigger_scenarios(self):
        """複雑なトリガーシナリオ"""
        # 平日の9時と17時に実行するトリガー
        now = datetime.now(timezone.utc)
        
        morning_trigger = Trigger(
            trigger_type="weekly",
            weekly_days=[0, 1, 2, 3, 4],  # 月-金
            weekly_time=time(9, 0),
            start_time=now,
            end_time=now + timedelta(days=30),
            is_active=True
        )
        
        evening_trigger = Trigger(
            trigger_type="weekly",
            weekly_days=[0, 1, 2, 3, 4],  # 月-金
            weekly_time=time(17, 0),
            start_time=now,
            end_time=now + timedelta(days=30),
            is_active=True
        )
        
        # 両方のトリガーが有効であること
        assert morning_trigger.is_valid() is True
        assert evening_trigger.is_valid() is True
        
        # 次回実行時間が適切に計算されること
        next_morning = morning_trigger.calculate_next_execution(now)
        next_evening = evening_trigger.calculate_next_execution(now)
        
        assert next_morning.hour == 9
        assert next_evening.hour == 17
        assert next_morning.weekday() in [0, 1, 2, 3, 4]
        assert next_evening.weekday() in [0, 1, 2, 3, 4]
    
    def test_metadata_and_status_combinations(self):
        """メタデータとステータスの組み合わせ"""
        # 様々な組み合わせが有効であること
        categories = ["general", "office", "web", "system"]
        statuses = list(RecordingStatus)
        
        for category in categories:
            metadata = RecordingMetadata(
                name=f"Test {category}",
                description=f"Test for {category}",
                category=category,
                tags=[category],
                created_by="test_user"
            )
            
            assert metadata.is_valid() is True
            
            for status in statuses:
                # ステータスが有効であること
                assert status in RecordingStatus
    
    def test_execution_result_edge_cases(self):
        """実行結果のエッジケース"""
        execution_time = datetime.now(timezone.utc)
        
        # 瞬時実行（0秒）
        instant_result = ExecutionResult(
            execution_id="instant",
            execution_time=execution_time,
            start_time=execution_time,
            end_time=execution_time,  # 同じ時間
            success=True,
            error_message=None,
            actions_executed=1,
            actions_failed=0
        )
        assert instant_result.duration_seconds == 0
        assert instant_result.is_valid() is True
        
        # 長時間実行（1時間）
        long_result = ExecutionResult(
            execution_id="long",
            execution_time=execution_time,
            start_time=execution_time,
            end_time=execution_time + timedelta(hours=1),
            success=True,
            error_message=None,
            actions_executed=1000,
            actions_failed=0
        )
        assert long_result.duration_seconds == 3600
        assert long_result.duration_minutes == 60
        assert long_result.is_valid() is True
    
    @pytest.mark.parametrize("trigger_type,expected_properties", [
        ("interval", {"interval_minutes": 30}),
        ("daily", {"daily_time": time(10, 0)}),
        ("weekly", {"weekly_days": [1, 3, 5], "weekly_time": time(14, 30)}),
        ("monthly", {"monthly_day": 15, "monthly_time": time(12, 0)})
    ])
    def test_trigger_type_specific_validation(self, trigger_type, expected_properties):
        """トリガータイプ固有の検証"""
        now = datetime.now(timezone.utc)
        
        trigger_params = {
            "trigger_type": trigger_type,
            "start_time": now,
            "end_time": now + timedelta(days=30),
            "is_active": True,
            **expected_properties
        }
        
        trigger = Trigger(**trigger_params)
        assert trigger.is_valid() is True
        assert trigger.trigger_type == trigger_type
        
        for prop, value in expected_properties.items():
            assert getattr(trigger, prop) == value