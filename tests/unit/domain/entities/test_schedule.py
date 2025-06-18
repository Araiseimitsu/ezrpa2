"""
Schedule エンティティの単体テスト

スケジュールエンティティのビジネスロジックと実行管理のテスト
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from src.domain.entities.schedule import Schedule
from src.domain.value_objects import (
    ScheduleMetadata, ScheduleStatus, Trigger, 
    ExecutionHistory, ExecutionResult
)
from tests.factories import ScheduleFactory, ScheduleMetadataFactory, TriggerFactory


class TestSchedule:
    """Schedule エンティティのテスト"""
    
    def test_schedule_creation_with_valid_data(self):
        """有効なデータでのスケジュール作成"""
        # Arrange
        metadata = ScheduleMetadataFactory()
        trigger = TriggerFactory()
        created_at = datetime.now(timezone.utc)
        
        # Act
        schedule = Schedule(
            schedule_id="sched_001",
            recording_id="rec_001",
            metadata=metadata,
            trigger=trigger,
            status=ScheduleStatus.ACTIVE,
            created_at=created_at,
            updated_at=created_at
        )
        
        # Assert
        assert schedule.schedule_id == "sched_001"
        assert schedule.recording_id == "rec_001"
        assert schedule.metadata == metadata
        assert schedule.trigger == trigger
        assert schedule.status == ScheduleStatus.ACTIVE
        assert schedule.created_at == created_at
        assert schedule.updated_at == created_at
        assert schedule.execution_history == []
        assert schedule.execution_count == 0
        assert schedule.success_count == 0
        assert schedule.last_execution is None
        assert schedule.next_execution is not None
    
    def test_schedule_creation_with_factory(self):
        """ファクトリーを使用したスケジュール作成"""
        # Act
        schedule = ScheduleFactory()
        
        # Assert
        assert schedule.schedule_id is not None
        assert schedule.recording_id is not None
        assert schedule.metadata is not None
        assert schedule.trigger is not None
        assert schedule.status in ScheduleStatus
        assert schedule.created_at <= schedule.updated_at
        assert isinstance(schedule.execution_history, list)
    
    def test_calculate_next_execution_interval(self):
        """インターバル実行の次回実行時間計算"""
        # Arrange
        trigger = Trigger(
            trigger_type="interval",
            interval_minutes=30,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(days=1),
            is_active=True
        )
        
        schedule = ScheduleFactory()
        schedule.trigger = trigger
        
        # Act
        next_exec = schedule.calculate_next_execution()
        
        # Assert
        assert next_exec is not None
        assert next_exec > datetime.now(timezone.utc)
        # 30分後であることを確認（誤差5秒以内）
        expected_time = datetime.now(timezone.utc) + timedelta(minutes=30)
        time_diff = abs((next_exec - expected_time).total_seconds())
        assert time_diff < 5
    
    def test_calculate_next_execution_daily(self):
        """日次実行の次回実行時間計算"""
        # Arrange
        now = datetime.now(timezone.utc)
        target_time = now.replace(hour=14, minute=30, second=0, microsecond=0)
        
        trigger = Trigger(
            trigger_type="daily",
            daily_time=target_time.time(),
            start_time=now,
            end_time=now + timedelta(days=30),
            is_active=True
        )
        
        schedule = ScheduleFactory()
        schedule.trigger = trigger
        
        # Act
        next_exec = schedule.calculate_next_execution()
        
        # Assert
        assert next_exec is not None
        assert next_exec.hour == 14
        assert next_exec.minute == 30
        
        # 今日の14:30を過ぎている場合は明日、そうでなければ今日
        if now.time() > target_time.time():
            expected_date = now.date() + timedelta(days=1)
        else:
            expected_date = now.date()
        
        assert next_exec.date() == expected_date
    
    def test_calculate_next_execution_weekly(self):
        """週次実行の次回実行時間計算"""
        # Arrange
        now = datetime.now(timezone.utc)
        trigger = Trigger(
            trigger_type="weekly",
            weekly_days=[1, 3, 5],  # 月・水・金
            weekly_time=datetime.strptime("09:00", "%H:%M").time(),
            start_time=now,
            end_time=now + timedelta(days=30),
            is_active=True
        )
        
        schedule = ScheduleFactory()
        schedule.trigger = trigger
        
        # Act
        next_exec = schedule.calculate_next_execution()
        
        # Assert
        assert next_exec is not None
        assert next_exec.weekday() in [1, 3, 5]  # 月・水・金
        assert next_exec.hour == 9
        assert next_exec.minute == 0
    
    def test_is_execution_time_true(self):
        """実行時間判定 - True ケース"""
        # Arrange
        now = datetime.now(timezone.utc)
        schedule = ScheduleFactory()
        schedule.next_execution = now - timedelta(minutes=1)  # 1分前に実行予定
        
        # Act
        result = schedule.is_execution_time(now)
        
        # Assert
        assert result is True
    
    def test_is_execution_time_false(self):
        """実行時間判定 - False ケース"""
        # Arrange
        now = datetime.now(timezone.utc)
        schedule = ScheduleFactory()
        schedule.next_execution = now + timedelta(minutes=10)  # 10分後に実行予定
        
        # Act
        result = schedule.is_execution_time(now)
        
        # Assert
        assert result is False
    
    def test_add_execution_result_success(self):
        """実行結果追加 - 成功"""
        # Arrange
        schedule = ScheduleFactory()
        execution_time = datetime.now(timezone.utc)
        initial_count = schedule.execution_count
        initial_success = schedule.success_count
        
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
        schedule.add_execution_result(result)
        
        # Assert
        assert schedule.execution_count == initial_count + 1
        assert schedule.success_count == initial_success + 1
        assert schedule.last_execution == execution_time
        assert len(schedule.execution_history) == 1
        assert schedule.execution_history[0].result == result
        assert schedule.success_rate > 0
    
    def test_add_execution_result_failure(self):
        """実行結果追加 - 失敗"""
        # Arrange
        schedule = ScheduleFactory()
        execution_time = datetime.now(timezone.utc)
        initial_count = schedule.execution_count
        initial_success = schedule.success_count
        
        result = ExecutionResult(
            execution_id="exec_002",
            execution_time=execution_time,
            start_time=execution_time,
            end_time=execution_time + timedelta(seconds=15),
            success=False,
            error_message="Application not found",
            actions_executed=3,
            actions_failed=7
        )
        
        # Act
        schedule.add_execution_result(result)
        
        # Assert
        assert schedule.execution_count == initial_count + 1
        assert schedule.success_count == initial_success  # 成功数は変わらず
        assert schedule.last_execution == execution_time
        assert len(schedule.execution_history) == 1
        assert schedule.execution_history[0].result.error_message == "Application not found"
    
    def test_success_rate_calculation(self):
        """成功率の計算"""
        # Arrange
        schedule = ScheduleFactory()
        execution_time = datetime.now(timezone.utc)
        
        # 成功2回、失敗1回を追加
        for i, success in enumerate([True, False, True]):
            result = ExecutionResult(
                execution_id=f"exec_{i}",
                execution_time=execution_time + timedelta(minutes=i),
                start_time=execution_time + timedelta(minutes=i),
                end_time=execution_time + timedelta(minutes=i, seconds=30),
                success=success,
                error_message=None if success else "Test error",
                actions_executed=10,
                actions_failed=0 if success else 5
            )
            schedule.add_execution_result(result)
        
        # Act
        success_rate = schedule.success_rate
        
        # Assert
        assert schedule.execution_count == 3
        assert schedule.success_count == 2
        assert success_rate == 2/3  # 約0.667
    
    def test_success_rate_no_executions(self):
        """実行履歴なしの成功率"""
        # Arrange
        schedule = ScheduleFactory()
        
        # Act
        success_rate = schedule.success_rate
        
        # Assert
        assert success_rate == 0.0
    
    def test_update_status(self):
        """ステータス更新"""
        # Arrange
        schedule = ScheduleFactory()
        original_updated_at = schedule.updated_at
        
        # Act
        schedule.update_status(ScheduleStatus.PAUSED)
        
        # Assert
        assert schedule.status == ScheduleStatus.PAUSED
        assert schedule.updated_at > original_updated_at
    
    def test_update_metadata(self):
        """メタデータ更新"""
        # Arrange
        schedule = ScheduleFactory()
        new_metadata = ScheduleMetadataFactory()
        new_metadata.name = "Updated Schedule"
        original_updated_at = schedule.updated_at
        
        # Act
        schedule.update_metadata(new_metadata)
        
        # Assert
        assert schedule.metadata == new_metadata
        assert schedule.metadata.name == "Updated Schedule"
        assert schedule.updated_at > original_updated_at
    
    def test_update_trigger(self):
        """トリガー更新"""
        # Arrange
        schedule = ScheduleFactory()
        new_trigger = TriggerFactory()
        new_trigger.interval_minutes = 60
        original_updated_at = schedule.updated_at
        
        # Act
        schedule.update_trigger(new_trigger)
        
        # Assert
        assert schedule.trigger == new_trigger
        assert schedule.trigger.interval_minutes == 60
        assert schedule.updated_at > original_updated_at
        # 次回実行時間も更新されること
        assert schedule.next_execution is not None
    
    def test_activate_schedule(self):
        """スケジュールのアクティブ化"""
        # Arrange
        schedule = ScheduleFactory()
        schedule.status = ScheduleStatus.PAUSED
        
        # Act
        schedule.activate()
        
        # Assert
        assert schedule.status == ScheduleStatus.ACTIVE
        assert schedule.trigger.is_active is True
        assert schedule.next_execution is not None
    
    def test_deactivate_schedule(self):
        """スケジュールの非アクティブ化"""
        # Arrange
        schedule = ScheduleFactory()
        schedule.status = ScheduleStatus.ACTIVE
        
        # Act
        schedule.deactivate()
        
        # Assert
        assert schedule.status == ScheduleStatus.INACTIVE
        assert schedule.trigger.is_active is False
        assert schedule.next_execution is None
    
    def test_pause_schedule(self):
        """スケジュールの一時停止"""
        # Arrange
        schedule = ScheduleFactory()
        schedule.status = ScheduleStatus.ACTIVE
        
        # Act
        schedule.pause()
        
        # Assert
        assert schedule.status == ScheduleStatus.PAUSED
        assert schedule.trigger.is_active is False
        # 次回実行時間は保持される
        assert schedule.next_execution is not None
    
    def test_resume_schedule(self):
        """スケジュールの再開"""
        # Arrange
        schedule = ScheduleFactory()
        schedule.status = ScheduleStatus.PAUSED
        
        # Act
        schedule.resume()
        
        # Assert
        assert schedule.status == ScheduleStatus.ACTIVE
        assert schedule.trigger.is_active is True
        assert schedule.next_execution is not None
    
    def test_schedule_validation(self):
        """スケジュールの妥当性検証"""
        # Arrange
        schedule = ScheduleFactory()
        
        # Act & Assert - 正常ケース
        assert schedule.is_valid() is True
        
        # 無効ケース1: 空のschedule_id
        schedule.schedule_id = ""
        assert schedule.is_valid() is False
        
        # 無効ケース2: 空のrecording_id
        schedule.schedule_id = "valid_id"
        schedule.recording_id = ""
        assert schedule.is_valid() is False
        
        # 無効ケース3: created_at > updated_at
        schedule.recording_id = "valid_recording_id"
        schedule.updated_at = schedule.created_at - timedelta(minutes=1)
        assert schedule.is_valid() is False
    
    def test_trigger_expiration_check(self):
        """トリガーの有効期限チェック"""
        # Arrange
        now = datetime.now(timezone.utc)
        
        # 期限切れトリガー
        expired_trigger = TriggerFactory()
        expired_trigger.end_time = now - timedelta(days=1)
        
        schedule = ScheduleFactory()
        schedule.trigger = expired_trigger
        
        # Act
        is_expired = schedule.is_trigger_expired()
        
        # Assert
        assert is_expired is True
        
        # 有効なトリガー
        valid_trigger = TriggerFactory()
        valid_trigger.end_time = now + timedelta(days=1)
        schedule.trigger = valid_trigger
        
        assert schedule.is_trigger_expired() is False
    
    def test_execution_history_limit(self):
        """実行履歴の制限"""
        # Arrange
        schedule = ScheduleFactory()
        execution_time = datetime.now(timezone.utc)
        
        # 履歴制限を超える数の実行結果を追加
        for i in range(105):  # デフォルト制限は100
            result = ExecutionResult(
                execution_id=f"exec_{i}",
                execution_time=execution_time + timedelta(minutes=i),
                start_time=execution_time + timedelta(minutes=i),
                end_time=execution_time + timedelta(minutes=i, seconds=30),
                success=True,
                error_message=None,
                actions_executed=10,
                actions_failed=0
            )
            schedule.add_execution_result(result)
        
        # Act & Assert
        assert schedule.execution_count == 105  # カウントは正確
        assert len(schedule.execution_history) <= 100  # 履歴は制限内
        
        # 最新の履歴が保持されていることを確認
        latest_history = schedule.execution_history[-1]
        assert latest_history.result.execution_id == "exec_104"
    
    def test_get_recent_executions(self):
        """最近の実行履歴取得"""
        # Arrange
        schedule = ScheduleFactory()
        execution_time = datetime.now(timezone.utc)
        
        # 10個の実行結果を追加
        for i in range(10):
            result = ExecutionResult(
                execution_id=f"exec_{i}",
                execution_time=execution_time + timedelta(minutes=i),
                start_time=execution_time + timedelta(minutes=i),
                end_time=execution_time + timedelta(minutes=i, seconds=30),
                success=i % 2 == 0,  # 偶数は成功、奇数は失敗
                error_message=None if i % 2 == 0 else f"Error {i}",
                actions_executed=10,
                actions_failed=0 if i % 2 == 0 else 5
            )
            schedule.add_execution_result(result)
        
        # Act
        recent_5 = schedule.get_recent_executions(5)
        recent_3 = schedule.get_recent_executions(3)
        all_recent = schedule.get_recent_executions()
        
        # Assert
        assert len(recent_5) == 5
        assert len(recent_3) == 3
        assert len(all_recent) == 10
        
        # 最新順になっていることを確認
        assert recent_5[0].result.execution_id == "exec_9"
        assert recent_5[4].result.execution_id == "exec_5"
    
    def test_get_failed_executions(self):
        """失敗した実行履歴取得"""
        # Arrange
        schedule = ScheduleFactory()
        execution_time = datetime.now(timezone.utc)
        
        # 成功3回、失敗2回を追加
        for i, success in enumerate([True, False, True, False, True]):
            result = ExecutionResult(
                execution_id=f"exec_{i}",
                execution_time=execution_time + timedelta(minutes=i),
                start_time=execution_time + timedelta(minutes=i),
                end_time=execution_time + timedelta(minutes=i, seconds=30),
                success=success,
                error_message=None if success else f"Error {i}",
                actions_executed=10,
                actions_failed=0 if success else 5
            )
            schedule.add_execution_result(result)
        
        # Act
        failed_executions = schedule.get_failed_executions()
        
        # Assert
        assert len(failed_executions) == 2
        assert all(not h.result.success for h in failed_executions)
        assert failed_executions[0].result.execution_id == "exec_1"
        assert failed_executions[1].result.execution_id == "exec_3"
    
    @pytest.mark.parametrize("status", list(ScheduleStatus))
    def test_all_schedule_statuses(self, status):
        """全てのスケジュールステータスのテスト"""
        # Arrange
        schedule = ScheduleFactory()
        
        # Act
        schedule.update_status(status)
        
        # Assert
        assert schedule.status == status
        assert schedule.status in ScheduleStatus
    
    def test_schedule_equality(self):
        """スケジュールの等価性"""
        # Arrange
        metadata = ScheduleMetadataFactory()
        trigger = TriggerFactory()
        timestamp = datetime.now(timezone.utc)
        
        schedule1 = Schedule(
            schedule_id="sched_001",
            recording_id="rec_001",
            metadata=metadata,
            trigger=trigger,
            status=ScheduleStatus.ACTIVE,
            created_at=timestamp,
            updated_at=timestamp
        )
        
        schedule2 = Schedule(
            schedule_id="sched_001",
            recording_id="rec_001",
            metadata=metadata,
            trigger=trigger,
            status=ScheduleStatus.ACTIVE,
            created_at=timestamp,
            updated_at=timestamp
        )
        
        schedule3 = Schedule(
            schedule_id="sched_002",  # 異なるID
            recording_id="rec_001",
            metadata=metadata,
            trigger=trigger,
            status=ScheduleStatus.ACTIVE,
            created_at=timestamp,
            updated_at=timestamp
        )
        
        # Act & Assert
        assert schedule1 == schedule2  # 同じID
        assert schedule1 != schedule3  # 異なるID
        assert hash(schedule1) == hash(schedule2)
        assert hash(schedule1) != hash(schedule3)
    
    def test_schedule_string_representation(self):
        """スケジュールの文字列表現"""
        # Arrange
        schedule = ScheduleFactory()
        schedule.metadata.name = "Test Schedule"
        
        # Act
        str_repr = str(schedule)
        repr_repr = repr(schedule)
        
        # Assert
        assert "Test Schedule" in str_repr
        assert schedule.schedule_id in str_repr
        assert "Schedule" in repr_repr
        assert schedule.schedule_id in repr_repr
    
    def test_schedule_time_zone_handling(self):
        """タイムゾーン処理のテスト"""
        # Arrange
        jst = timezone(timedelta(hours=9))  # JST
        utc = timezone.utc
        
        # UTCでの作成
        utc_time = datetime.now(utc)
        schedule = ScheduleFactory()
        schedule.created_at = utc_time
        
        # Act
        # JSTでの次回実行時間計算
        schedule.trigger.start_time = utc_time
        next_exec = schedule.calculate_next_execution()
        
        # Assert
        assert next_exec.tzinfo == utc  # 内部的にはUTC
        
        # タイムゾーン変換が正しく動作すること
        jst_time = next_exec.astimezone(jst)
        assert jst_time.tzinfo == jst
    
    def test_schedule_performance_metrics(self):
        """スケジュール性能メトリクス"""
        # Arrange
        schedule = ScheduleFactory()
        execution_time = datetime.now(timezone.utc)
        
        # 異なる実行時間の結果を追加
        durations = [10, 25, 15, 30, 20]  # 秒
        for i, duration in enumerate(durations):
            result = ExecutionResult(
                execution_id=f"exec_{i}",
                execution_time=execution_time + timedelta(minutes=i),
                start_time=execution_time + timedelta(minutes=i),
                end_time=execution_time + timedelta(minutes=i, seconds=duration),
                success=True,
                error_message=None,
                actions_executed=10,
                actions_failed=0
            )
            schedule.add_execution_result(result)
        
        # Act
        avg_duration = schedule.get_average_execution_duration()
        max_duration = schedule.get_max_execution_duration()
        min_duration = schedule.get_min_execution_duration()
        
        # Assert
        assert avg_duration == 20.0  # (10+25+15+30+20)/5
        assert max_duration == 30.0
        assert min_duration == 10.0