"""
Recording エンティティの単体テスト

記録エンティティのビジネスロジックと不変条件をテスト
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import List

from src.domain.entities.recording import Recording
from src.domain.entities.action import Action, KeyboardAction, MouseAction, DelayAction
from src.domain.value_objects import RecordingMetadata, RecordingStatus
from tests.factories import RecordingFactory, KeyboardActionFactory, RecordingMetadataFactory


class TestRecording:
    """Recording エンティティのテスト"""
    
    def test_recording_creation_with_valid_data(self):
        """有効なデータでの記録作成"""
        # Arrange
        metadata = RecordingMetadataFactory()
        created_at = datetime.now(timezone.utc)
        
        # Act
        recording = Recording(
            recording_id="test_001",
            metadata=metadata,
            status=RecordingStatus.STOPPED,
            created_at=created_at,
            updated_at=created_at
        )
        
        # Assert
        assert recording.recording_id == "test_001"
        assert recording.metadata == metadata
        assert recording.status == RecordingStatus.STOPPED
        assert recording.created_at == created_at
        assert recording.updated_at == created_at
        assert recording.actions == []
        assert recording.action_count == 0
        assert recording.estimated_duration_ms == 0
    
    def test_recording_creation_with_factory(self):
        """ファクトリーを使用した記録作成"""
        # Act
        recording = RecordingFactory()
        
        # Assert
        assert recording.recording_id is not None
        assert recording.metadata is not None
        assert recording.metadata.name is not None
        assert recording.status in RecordingStatus
        assert recording.created_at <= recording.updated_at
        assert isinstance(recording.actions, list)
    
    def test_add_action_to_recording(self):
        """記録にアクションを追加"""
        # Arrange
        recording = RecordingFactory()
        action = KeyboardActionFactory()
        initial_count = recording.action_count
        
        # Act
        recording.add_action(action)
        
        # Assert
        assert recording.action_count == initial_count + 1
        assert action in recording.actions
        assert recording.actions[-1] == action
    
    def test_add_multiple_actions(self):
        """複数のアクションを追加"""
        # Arrange
        recording = RecordingFactory()
        actions = [
            KeyboardActionFactory(),
            MouseAction(
                action_id="mouse_001",
                timestamp=datetime.now(timezone.utc),
                action_type="click",
                x=100,
                y=200,
                button="left"
            ),
            DelayAction(
                action_id="delay_001", 
                timestamp=datetime.now(timezone.utc),
                duration_ms=1000
            )
        ]
        
        # Act
        for action in actions:
            recording.add_action(action)
        
        # Assert
        assert recording.action_count == len(actions)
        assert all(action in recording.actions for action in actions)
    
    def test_remove_action_from_recording(self):
        """記録からアクションを削除"""
        # Arrange
        recording = RecordingFactory()
        action = KeyboardActionFactory()
        recording.add_action(action)
        initial_count = recording.action_count
        
        # Act
        result = recording.remove_action(action.action_id)
        
        # Assert
        assert result is True
        assert recording.action_count == initial_count - 1
        assert action not in recording.actions
    
    def test_remove_nonexistent_action(self):
        """存在しないアクションの削除"""
        # Arrange
        recording = RecordingFactory()
        
        # Act
        result = recording.remove_action("nonexistent_id")
        
        # Assert
        assert result is False
        assert recording.action_count == 0
    
    def test_get_action_by_id(self):
        """IDによるアクション取得"""
        # Arrange
        recording = RecordingFactory()
        action = KeyboardActionFactory()
        recording.add_action(action)
        
        # Act
        found_action = recording.get_action(action.action_id)
        
        # Assert
        assert found_action == action
    
    def test_get_nonexistent_action(self):
        """存在しないアクションの取得"""
        # Arrange
        recording = RecordingFactory()
        
        # Act
        found_action = recording.get_action("nonexistent_id")
        
        # Assert
        assert found_action is None
    
    def test_clear_actions(self):
        """全アクションのクリア"""
        # Arrange
        recording = RecordingFactory()
        for _ in range(5):
            recording.add_action(KeyboardActionFactory())
        
        # Act
        recording.clear_actions()
        
        # Assert
        assert recording.action_count == 0
        assert recording.actions == []
    
    def test_estimated_duration_calculation(self):
        """推定実行時間の計算"""
        # Arrange
        recording = RecordingFactory()
        recording.clear_actions()
        
        # 各種アクションを追加
        keyboard_action = KeyboardActionFactory()
        mouse_action = MouseAction(
            action_id="mouse_001",
            timestamp=datetime.now(timezone.utc),
            action_type="click",
            x=100,
            y=200,
            button="left"
        )
        delay_action = DelayAction(
            action_id="delay_001",
            timestamp=datetime.now(timezone.utc),
            duration_ms=2000
        )
        
        recording.add_action(keyboard_action)
        recording.add_action(mouse_action)
        recording.add_action(delay_action)
        
        # Act
        estimated_duration = recording.estimated_duration_ms
        
        # Assert
        # キーボード(50ms) + マウス(100ms) + 遅延(2000ms) = 2150ms
        expected_duration = 50 + 100 + 2000
        assert estimated_duration == expected_duration
    
    def test_update_status(self):
        """ステータス更新"""
        # Arrange
        recording = RecordingFactory()
        original_updated_at = recording.updated_at
        
        # Act
        recording.update_status(RecordingStatus.RECORDING)
        
        # Assert
        assert recording.status == RecordingStatus.RECORDING
        assert recording.updated_at > original_updated_at
    
    def test_update_metadata(self):
        """メタデータ更新"""
        # Arrange
        recording = RecordingFactory()
        new_metadata = RecordingMetadataFactory()
        new_metadata.name = "Updated Recording Name"
        original_updated_at = recording.updated_at
        
        # Act
        recording.update_metadata(new_metadata)
        
        # Assert
        assert recording.metadata == new_metadata
        assert recording.metadata.name == "Updated Recording Name"
        assert recording.updated_at > original_updated_at
    
    def test_recording_status_transitions(self):
        """記録ステータスの遷移"""
        # Arrange
        recording = RecordingFactory()
        
        # 正常な遷移パターンをテスト
        transitions = [
            (RecordingStatus.STOPPED, RecordingStatus.RECORDING),
            (RecordingStatus.RECORDING, RecordingStatus.PAUSED),
            (RecordingStatus.PAUSED, RecordingStatus.RECORDING),
            (RecordingStatus.RECORDING, RecordingStatus.STOPPED),
            (RecordingStatus.STOPPED, RecordingStatus.COMPLETED)
        ]
        
        for from_status, to_status in transitions:
            # Act
            recording.update_status(from_status)
            recording.update_status(to_status)
            
            # Assert
            assert recording.status == to_status
    
    def test_actions_sorted_by_timestamp(self):
        """アクションがタイムスタンプでソートされること"""
        # Arrange
        recording = RecordingFactory()
        recording.clear_actions()
        
        base_time = datetime.now(timezone.utc)
        
        # タイムスタンプが逆順のアクションを追加
        action3 = KeyboardActionFactory()
        action3.timestamp = base_time + timedelta(seconds=3)
        
        action1 = KeyboardActionFactory()
        action1.timestamp = base_time + timedelta(seconds=1)
        
        action2 = KeyboardActionFactory()
        action2.timestamp = base_time + timedelta(seconds=2)
        
        recording.add_action(action3)
        recording.add_action(action1)
        recording.add_action(action2)
        
        # Act
        sorted_actions = recording.get_actions_sorted()
        
        # Assert
        assert len(sorted_actions) == 3
        assert sorted_actions[0] == action1
        assert sorted_actions[1] == action2
        assert sorted_actions[2] == action3
        
        # タイムスタンプが昇順になっていることを確認
        for i in range(1, len(sorted_actions)):
            assert sorted_actions[i-1].timestamp <= sorted_actions[i].timestamp
    
    def test_get_actions_by_type(self):
        """タイプ別のアクション取得"""
        # Arrange
        recording = RecordingFactory()
        recording.clear_actions()
        
        keyboard_actions = [KeyboardActionFactory() for _ in range(3)]
        mouse_actions = [MouseAction(
            action_id=f"mouse_{i}",
            timestamp=datetime.now(timezone.utc),
            action_type="click",
            x=100 + i,
            y=200 + i,
            button="left"
        ) for i in range(2)]
        
        for action in keyboard_actions + mouse_actions:
            recording.add_action(action)
        
        # Act
        found_keyboard = recording.get_actions_by_type(KeyboardAction)
        found_mouse = recording.get_actions_by_type(MouseAction)
        
        # Assert
        assert len(found_keyboard) == 3
        assert len(found_mouse) == 2
        assert all(isinstance(action, KeyboardAction) for action in found_keyboard)
        assert all(isinstance(action, MouseAction) for action in found_mouse)
    
    def test_recording_validation(self):
        """記録の妥当性検証"""
        # Arrange
        recording = RecordingFactory()
        
        # Act & Assert - 正常ケース
        assert recording.is_valid() is True
        
        # 無効なケース1: 空のrecording_id
        recording.recording_id = ""
        assert recording.is_valid() is False
        
        # 無効なケース2: Noneのrecording_id
        recording.recording_id = None
        assert recording.is_valid() is False
        
        # 無効なケース3: created_at > updated_at
        recording.recording_id = "valid_id"
        recording.updated_at = recording.created_at - timedelta(minutes=1)
        assert recording.is_valid() is False
    
    def test_recording_equality(self):
        """記録の等価性"""
        # Arrange
        metadata = RecordingMetadataFactory()
        timestamp = datetime.now(timezone.utc)
        
        recording1 = Recording(
            recording_id="test_001",
            metadata=metadata,
            status=RecordingStatus.STOPPED,
            created_at=timestamp,
            updated_at=timestamp
        )
        
        recording2 = Recording(
            recording_id="test_001",
            metadata=metadata,
            status=RecordingStatus.STOPPED,
            created_at=timestamp,
            updated_at=timestamp
        )
        
        recording3 = Recording(
            recording_id="test_002",
            metadata=metadata,
            status=RecordingStatus.STOPPED,
            created_at=timestamp,
            updated_at=timestamp
        )
        
        # Act & Assert
        assert recording1 == recording2  # 同じID
        assert recording1 != recording3  # 異なるID
        assert hash(recording1) == hash(recording2)  # ハッシュも同じ
        assert hash(recording1) != hash(recording3)  # ハッシュが異なる
    
    def test_recording_string_representation(self):
        """記録の文字列表現"""
        # Arrange
        recording = RecordingFactory()
        recording.metadata.name = "Test Recording"
        
        # Act
        str_repr = str(recording)
        repr_repr = repr(recording)
        
        # Assert
        assert "Test Recording" in str_repr
        assert recording.recording_id in str_repr
        assert "Recording" in repr_repr
        assert recording.recording_id in repr_repr
    
    def test_recording_action_count_consistency(self):
        """アクション数の一貫性"""
        # Arrange
        recording = RecordingFactory()
        recording.clear_actions()
        
        # Act & Assert - 初期状態
        assert recording.action_count == 0
        assert len(recording.actions) == 0
        
        # アクション追加後
        action = KeyboardActionFactory()
        recording.add_action(action)
        assert recording.action_count == 1
        assert len(recording.actions) == 1
        
        # アクション削除後
        recording.remove_action(action.action_id)
        assert recording.action_count == 0
        assert len(recording.actions) == 0
    
    @pytest.mark.parametrize("status", list(RecordingStatus))
    def test_all_recording_statuses(self, status):
        """全ての記録ステータスのテスト"""
        # Arrange
        recording = RecordingFactory()
        
        # Act
        recording.update_status(status)
        
        # Assert
        assert recording.status == status
        assert recording.status in RecordingStatus
    
    def test_recording_with_large_number_of_actions(self):
        """大量のアクションを持つ記録"""
        # Arrange
        recording = RecordingFactory()
        recording.clear_actions()
        action_count = 1000
        
        # Act
        for i in range(action_count):
            action = KeyboardActionFactory()
            recording.add_action(action)
        
        # Assert
        assert recording.action_count == action_count
        assert len(recording.actions) == action_count
        
        # パフォーマンス: 推定時間計算が合理的な時間で完了すること
        import time
        start_time = time.time()
        _ = recording.estimated_duration_ms
        end_time = time.time()
        
        calculation_time = end_time - start_time
        assert calculation_time < 1.0  # 1秒以内に完了
    
    def test_recording_immutability_constraints(self):
        """記録の不変条件"""
        # Arrange
        recording = RecordingFactory()
        original_created_at = recording.created_at
        
        # Act & Assert
        # created_atは変更されないこと
        recording.update_status(RecordingStatus.RECORDING)
        assert recording.created_at == original_created_at
        
        # updated_atは常にcreated_at以降であること
        assert recording.updated_at >= recording.created_at
        
        # recording_idは変更されないこと（実際のビジネスルール）
        original_id = recording.recording_id
        # recording_idを変更するメソッドは存在しないことを確認
        assert not hasattr(recording, 'update_recording_id')
        assert recording.recording_id == original_id