"""
Action エンティティの単体テスト

アクションエンティティとその派生クラスのテスト
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import List

from src.domain.entities.action import (
    Action, ActionTypes, 
    KeyboardAction, MouseAction, DelayAction,
    WindowAction, ImageAction, ConditionalAction
)
from tests.factories import (
    KeyboardActionFactory, MouseActionFactory, DelayActionFactory
)


class TestAction:
    """基本アクションクラスのテスト"""
    
    def test_action_is_abstract(self):
        """Actionクラスが抽象クラスであることを確認"""
        # Abstract クラスなので直接インスタンス化できない
        with pytest.raises(TypeError):
            Action(
                action_id="test",
                timestamp=datetime.now(timezone.utc)
            )
    
    def test_action_types_enum(self):
        """ActionTypesEnumの値確認"""
        expected_types = {
            'KEYBOARD', 'MOUSE', 'DELAY', 'WINDOW', 'IMAGE', 'CONDITIONAL'
        }
        actual_types = {action_type.value for action_type in ActionTypes}
        assert actual_types == expected_types
    
    def test_action_subclass_creation(self):
        """アクションサブクラスの作成"""
        # KeyboardAction の作成
        keyboard_action = KeyboardActionFactory()
        assert isinstance(keyboard_action, Action)
        assert keyboard_action.action_type == ActionTypes.KEYBOARD
        
        # MouseAction の作成
        mouse_action = MouseActionFactory()
        assert isinstance(mouse_action, Action)
        assert mouse_action.action_type == ActionTypes.MOUSE
        
        # DelayAction の作成
        delay_action = DelayActionFactory()
        assert isinstance(delay_action, Action)
        assert delay_action.action_type == ActionTypes.DELAY


class TestKeyboardAction:
    """キーボードアクションのテスト"""
    
    def test_keyboard_action_creation(self):
        """キーボードアクション作成"""
        # Arrange
        timestamp = datetime.now(timezone.utc)
        
        # Act
        action = KeyboardAction(
            action_id="kb_001",
            timestamp=timestamp,
            key_code="VK_A",
            key_name="A",
            modifiers=["ctrl", "shift"]
        )
        
        # Assert
        assert action.action_id == "kb_001"
        assert action.timestamp == timestamp
        assert action.action_type == ActionTypes.KEYBOARD
        assert action.key_code == "VK_A"
        assert action.key_name == "A"
        assert action.modifiers == ["ctrl", "shift"]
    
    def test_keyboard_action_factory(self):
        """ファクトリーによるキーボードアクション作成"""
        # Act
        action = KeyboardActionFactory()
        
        # Assert
        assert action.action_id is not None
        assert action.timestamp is not None
        assert action.action_type == ActionTypes.KEYBOARD
        assert action.key_code is not None
        assert action.key_name is not None
        assert isinstance(action.modifiers, list)
    
    def test_keyboard_action_estimated_duration(self):
        """キーボードアクション実行時間"""
        # Arrange
        action = KeyboardActionFactory()
        
        # Act
        duration = action.get_estimated_duration_ms()
        
        # Assert
        assert duration == 50  # デフォルトのキーボード入力時間
    
    def test_keyboard_action_validation(self):
        """キーボードアクションの妥当性検証"""
        # Arrange
        valid_action = KeyboardActionFactory()
        
        # Act & Assert - 正常ケース
        assert valid_action.is_valid() is True
        
        # 無効ケース1: 空のkey_code
        invalid_action1 = KeyboardActionFactory()
        invalid_action1.key_code = ""
        assert invalid_action1.is_valid() is False
        
        # 無効ケース2: Noneのkey_code
        invalid_action2 = KeyboardActionFactory()
        invalid_action2.key_code = None
        assert invalid_action2.is_valid() is False
    
    def test_keyboard_action_with_japanese_input(self):
        """日本語入力のキーボードアクション"""
        # Arrange & Act
        action = KeyboardAction(
            action_id="jp_001",
            timestamp=datetime.now(timezone.utc),
            key_code="VK_KANJI",
            key_name="漢字",
            modifiers=[],
            is_ime_input=True,
            ime_composition="てすと",
            ime_result="テスト"
        )
        
        # Assert
        assert action.is_ime_input is True
        assert action.ime_composition == "てすと"
        assert action.ime_result == "テスト"
        assert action.get_estimated_duration_ms() == 100  # IME入力は時間がかかる
    
    @pytest.mark.parametrize("key_code,expected_category", [
        ("VK_A", "alphanumeric"),
        ("VK_F1", "function"),
        ("VK_CTRL", "modifier"),
        ("VK_RETURN", "special"),
        ("VK_SPACE", "special"),
        ("VK_KANJI", "ime")
    ])
    def test_keyboard_action_categorization(self, key_code, expected_category):
        """キーの種類による分類"""
        # Arrange
        action = KeyboardAction(
            action_id="test",
            timestamp=datetime.now(timezone.utc),
            key_code=key_code,
            key_name=key_code.replace("VK_", ""),
            modifiers=[]
        )
        
        # Act
        category = action.get_key_category()
        
        # Assert
        assert category == expected_category


class TestMouseAction:
    """マウスアクションのテスト"""
    
    def test_mouse_action_creation(self):
        """マウスアクション作成"""
        # Arrange
        timestamp = datetime.now(timezone.utc)
        
        # Act
        action = MouseAction(
            action_id="mouse_001",
            timestamp=timestamp,
            action_type="click",
            x=100,
            y=200,
            button="left"
        )
        
        # Assert
        assert action.action_id == "mouse_001"
        assert action.timestamp == timestamp
        assert action.action_type == ActionTypes.MOUSE
        assert action.mouse_action_type == "click"
        assert action.x == 100
        assert action.y == 200
        assert action.button == "left"
    
    def test_mouse_action_factory(self):
        """ファクトリーによるマウスアクション作成"""
        # Act
        action = MouseActionFactory()
        
        # Assert
        assert action.action_id is not None
        assert action.timestamp is not None
        assert action.action_type == ActionTypes.MOUSE
        assert action.mouse_action_type is not None
        assert isinstance(action.x, int)
        assert isinstance(action.y, int)
        assert action.button is not None
    
    @pytest.mark.parametrize("mouse_action_type,expected_duration", [
        ("click", 100),
        ("double_click", 150),
        ("right_click", 100),
        ("move", 50),
        ("drag", 200),
        ("scroll", 75)
    ])
    def test_mouse_action_estimated_duration(self, mouse_action_type, expected_duration):
        """マウスアクション種別による実行時間"""
        # Arrange
        action = MouseAction(
            action_id="test",
            timestamp=datetime.now(timezone.utc),
            action_type=mouse_action_type,
            x=100,
            y=200,
            button="left"
        )
        
        # Act
        duration = action.get_estimated_duration_ms()
        
        # Assert
        assert duration == expected_duration
    
    def test_mouse_action_validation(self):
        """マウスアクションの妥当性検証"""
        # Arrange
        valid_action = MouseActionFactory()
        
        # Act & Assert - 正常ケース
        assert valid_action.is_valid() is True
        
        # 無効ケース1: 負の座標
        invalid_action1 = MouseActionFactory()
        invalid_action1.x = -10
        assert invalid_action1.is_valid() is False
        
        # 無効ケース2: 画面外の座標（10000以上）
        invalid_action2 = MouseActionFactory()
        invalid_action2.x = 15000
        assert invalid_action2.is_valid() is False
    
    def test_mouse_action_with_additional_data(self):
        """追加データを持つマウスアクション"""
        # Arrange & Act
        action = MouseAction(
            action_id="complex_mouse",
            timestamp=datetime.now(timezone.utc),
            action_type="drag",
            x=100,
            y=200,
            button="left",
            end_x=300,
            end_y=400,
            scroll_delta=5,
            modifier_keys=["ctrl"]
        )
        
        # Assert
        assert action.end_x == 300
        assert action.end_y == 400
        assert action.scroll_delta == 5
        assert action.modifier_keys == ["ctrl"]
    
    def test_mouse_position_validation(self):
        """マウス座標の妥当性検証"""
        # Valid positions
        valid_positions = [(0, 0), (1920, 1080), (100, 200)]
        for x, y in valid_positions:
            action = MouseAction(
                action_id="test",
                timestamp=datetime.now(timezone.utc),
                action_type="click",
                x=x,
                y=y,
                button="left"
            )
            assert action.is_valid() is True
        
        # Invalid positions
        invalid_positions = [(-1, 0), (0, -1), (20000, 0), (0, 20000)]
        for x, y in invalid_positions:
            action = MouseAction(
                action_id="test",
                timestamp=datetime.now(timezone.utc),
                action_type="click",
                x=x,
                y=y,
                button="left"
            )
            assert action.is_valid() is False


class TestDelayAction:
    """遅延アクションのテスト"""
    
    def test_delay_action_creation(self):
        """遅延アクション作成"""
        # Arrange
        timestamp = datetime.now(timezone.utc)
        
        # Act
        action = DelayAction(
            action_id="delay_001",
            timestamp=timestamp,
            duration_ms=1000
        )
        
        # Assert
        assert action.action_id == "delay_001"
        assert action.timestamp == timestamp
        assert action.action_type == ActionTypes.DELAY
        assert action.duration_ms == 1000
    
    def test_delay_action_factory(self):
        """ファクトリーによる遅延アクション作成"""
        # Act
        action = DelayActionFactory()
        
        # Assert
        assert action.action_id is not None
        assert action.timestamp is not None
        assert action.action_type == ActionTypes.DELAY
        assert isinstance(action.duration_ms, int)
        assert action.duration_ms > 0
    
    def test_delay_action_estimated_duration(self):
        """遅延アクションの実行時間（遅延時間と同じ）"""
        # Arrange
        duration = 2500
        action = DelayAction(
            action_id="test",
            timestamp=datetime.now(timezone.utc),
            duration_ms=duration
        )
        
        # Act
        estimated = action.get_estimated_duration_ms()
        
        # Assert
        assert estimated == duration
    
    def test_delay_action_validation(self):
        """遅延アクションの妥当性検証"""
        # 正常ケース
        valid_action = DelayAction(
            action_id="test",
            timestamp=datetime.now(timezone.utc),
            duration_ms=1000
        )
        assert valid_action.is_valid() is True
        
        # 無効ケース1: 0以下の遅延時間
        invalid_action1 = DelayAction(
            action_id="test",
            timestamp=datetime.now(timezone.utc),
            duration_ms=0
        )
        assert invalid_action1.is_valid() is False
        
        # 無効ケース2: 負の遅延時間
        invalid_action2 = DelayAction(
            action_id="test",
            timestamp=datetime.now(timezone.utc),
            duration_ms=-100
        )
        assert invalid_action2.is_valid() is False
        
        # 無効ケース3: 極端に長い遅延時間（1時間以上）
        invalid_action3 = DelayAction(
            action_id="test",
            timestamp=datetime.now(timezone.utc),
            duration_ms=3600000 + 1  # 1時間 + 1ms
        )
        assert invalid_action3.is_valid() is False


class TestWindowAction:
    """ウィンドウアクションのテスト"""
    
    def test_window_action_creation(self):
        """ウィンドウアクション作成"""
        # Arrange
        timestamp = datetime.now(timezone.utc)
        
        # Act
        action = WindowAction(
            action_id="win_001",
            timestamp=timestamp,
            window_action_type="activate",
            window_title="Notepad",
            window_class="Notepad",
            process_name="notepad.exe"
        )
        
        # Assert
        assert action.action_id == "win_001"
        assert action.timestamp == timestamp
        assert action.action_type == ActionTypes.WINDOW
        assert action.window_action_type == "activate"
        assert action.window_title == "Notepad"
        assert action.window_class == "Notepad"
        assert action.process_name == "notepad.exe"
    
    @pytest.mark.parametrize("window_action_type,expected_duration", [
        ("activate", 200),
        ("minimize", 150),
        ("maximize", 150),
        ("close", 100),
        ("resize", 300),
        ("move", 200)
    ])
    def test_window_action_estimated_duration(self, window_action_type, expected_duration):
        """ウィンドウアクション種別による実行時間"""
        # Arrange
        action = WindowAction(
            action_id="test",
            timestamp=datetime.now(timezone.utc),
            window_action_type=window_action_type,
            window_title="Test Window"
        )
        
        # Act
        duration = action.get_estimated_duration_ms()
        
        # Assert
        assert duration == expected_duration


class TestImageAction:
    """画像アクションのテスト"""
    
    def test_image_action_creation(self):
        """画像アクション作成"""
        # Arrange
        timestamp = datetime.now(timezone.utc)
        
        # Act
        action = ImageAction(
            action_id="img_001",
            timestamp=timestamp,
            image_action_type="click",
            image_path="test_button.png",
            confidence_threshold=0.8,
            search_region=(100, 100, 500, 400)
        )
        
        # Assert
        assert action.action_id == "img_001"
        assert action.timestamp == timestamp
        assert action.action_type == ActionTypes.IMAGE
        assert action.image_action_type == "click"
        assert action.image_path == "test_button.png"
        assert action.confidence_threshold == 0.8
        assert action.search_region == (100, 100, 500, 400)
    
    def test_image_action_validation(self):
        """画像アクションの妥当性検証"""
        # 正常ケース
        valid_action = ImageAction(
            action_id="test",
            timestamp=datetime.now(timezone.utc),
            image_action_type="click",
            image_path="button.png",
            confidence_threshold=0.9
        )
        assert valid_action.is_valid() is True
        
        # 無効ケース1: 空の画像パス
        invalid_action1 = ImageAction(
            action_id="test",
            timestamp=datetime.now(timezone.utc),
            image_action_type="click",
            image_path="",
            confidence_threshold=0.9
        )
        assert invalid_action1.is_valid() is False
        
        # 無効ケース2: 無効な信頼度閾値
        invalid_action2 = ImageAction(
            action_id="test",
            timestamp=datetime.now(timezone.utc),
            image_action_type="click",
            image_path="button.png",
            confidence_threshold=1.5  # > 1.0
        )
        assert invalid_action2.is_valid() is False


class TestConditionalAction:
    """条件付きアクションのテスト"""
    
    def test_conditional_action_creation(self):
        """条件付きアクション作成"""
        # Arrange
        timestamp = datetime.now(timezone.utc)
        
        # Act
        action = ConditionalAction(
            action_id="cond_001",
            timestamp=timestamp,
            condition_type="window_exists",
            condition_target="Calculator",
            true_actions=[
                KeyboardActionFactory(),
                MouseActionFactory()
            ],
            false_actions=[
                DelayActionFactory()
            ]
        )
        
        # Assert
        assert action.action_id == "cond_001"
        assert action.timestamp == timestamp
        assert action.action_type == ActionTypes.CONDITIONAL
        assert action.condition_type == "window_exists"
        assert action.condition_target == "Calculator"
        assert len(action.true_actions) == 2
        assert len(action.false_actions) == 1
    
    def test_conditional_action_estimated_duration(self):
        """条件付きアクションの実行時間（最大値を使用）"""
        # Arrange
        true_actions = [
            DelayAction("delay1", datetime.now(timezone.utc), 1000),
            DelayAction("delay2", datetime.now(timezone.utc), 500)
        ]
        false_actions = [
            DelayAction("delay3", datetime.now(timezone.utc), 2000)
        ]
        
        action = ConditionalAction(
            action_id="test",
            timestamp=datetime.now(timezone.utc),
            condition_type="test",
            condition_target="test",
            true_actions=true_actions,
            false_actions=false_actions
        )
        
        # Act
        duration = action.get_estimated_duration_ms()
        
        # Assert
        # 条件判定時間(100ms) + max(true_actions合計, false_actions合計)
        # true: 1000 + 500 = 1500ms
        # false: 2000ms
        # 結果: 100 + max(1500, 2000) = 2100ms
        assert duration == 2100


class TestActionComparison:
    """アクション比較とソートのテスト"""
    
    def test_action_timestamp_sorting(self):
        """タイムスタンプによるアクションソート"""
        # Arrange
        base_time = datetime.now(timezone.utc)
        
        action1 = KeyboardActionFactory()
        action1.timestamp = base_time + timedelta(seconds=3)
        
        action2 = MouseActionFactory()
        action2.timestamp = base_time + timedelta(seconds=1)
        
        action3 = DelayActionFactory()
        action3.timestamp = base_time + timedelta(seconds=2)
        
        actions = [action1, action2, action3]
        
        # Act
        sorted_actions = sorted(actions, key=lambda a: a.timestamp)
        
        # Assert
        assert sorted_actions[0] == action2  # 最も早い
        assert sorted_actions[1] == action3  # 中間
        assert sorted_actions[2] == action1  # 最も遅い
    
    def test_action_equality(self):
        """アクション等価性"""
        # Arrange
        timestamp = datetime.now(timezone.utc)
        
        action1 = KeyboardAction(
            action_id="test_001",
            timestamp=timestamp,
            key_code="VK_A",
            key_name="A",
            modifiers=[]
        )
        
        action2 = KeyboardAction(
            action_id="test_001", 
            timestamp=timestamp,
            key_code="VK_A",
            key_name="A",
            modifiers=[]
        )
        
        action3 = KeyboardAction(
            action_id="test_002",  # 異なるID
            timestamp=timestamp,
            key_code="VK_A",
            key_name="A",
            modifiers=[]
        )
        
        # Act & Assert
        assert action1 == action2  # 同じID
        assert action1 != action3  # 異なるID
        assert hash(action1) == hash(action2)
        assert hash(action1) != hash(action3)


class TestActionSerialization:
    """アクションシリアライゼーションのテスト"""
    
    def test_keyboard_action_to_dict(self):
        """キーボードアクションの辞書変換"""
        # Arrange
        action = KeyboardActionFactory()
        
        # Act
        action_dict = action.to_dict()
        
        # Assert
        assert action_dict["action_id"] == action.action_id
        assert action_dict["action_type"] == ActionTypes.KEYBOARD.value
        assert action_dict["key_code"] == action.key_code
        assert action_dict["key_name"] == action.key_name
        assert action_dict["modifiers"] == action.modifiers
    
    def test_mouse_action_to_dict(self):
        """マウスアクションの辞書変換"""
        # Arrange
        action = MouseActionFactory()
        
        # Act
        action_dict = action.to_dict()
        
        # Assert
        assert action_dict["action_id"] == action.action_id
        assert action_dict["action_type"] == ActionTypes.MOUSE.value
        assert action_dict["mouse_action_type"] == action.mouse_action_type
        assert action_dict["x"] == action.x
        assert action_dict["y"] == action.y
        assert action_dict["button"] == action.button
    
    def test_action_from_dict(self):
        """辞書からのアクション復元"""
        # Arrange
        action_dict = {
            "action_id": "test_001",
            "action_type": "KEYBOARD",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "key_code": "VK_A",
            "key_name": "A",
            "modifiers": ["ctrl"]
        }
        
        # Act
        action = KeyboardAction.from_dict(action_dict)
        
        # Assert
        assert action.action_id == "test_001"
        assert action.action_type == ActionTypes.KEYBOARD
        assert action.key_code == "VK_A"
        assert action.key_name == "A"
        assert action.modifiers == ["ctrl"]


class TestActionPerformance:
    """アクションパフォーマンステスト"""
    
    @pytest.mark.slow
    def test_large_action_list_operations(self):
        """大量アクションリストの操作"""
        # Arrange
        action_count = 10000
        actions = []
        
        # Act - 作成
        import time
        start_time = time.time()
        
        for i in range(action_count):
            if i % 3 == 0:
                actions.append(KeyboardActionFactory())
            elif i % 3 == 1:
                actions.append(MouseActionFactory())
            else:
                actions.append(DelayActionFactory())
        
        creation_time = time.time() - start_time
        
        # Act - ソート
        start_time = time.time()
        sorted_actions = sorted(actions, key=lambda a: a.timestamp)
        sort_time = time.time() - start_time
        
        # Act - 総実行時間計算
        start_time = time.time()
        total_duration = sum(action.get_estimated_duration_ms() for action in actions)
        calc_time = time.time() - start_time
        
        # Assert
        assert len(actions) == action_count
        assert len(sorted_actions) == action_count
        assert creation_time < 5.0  # 5秒以内
        assert sort_time < 1.0      # 1秒以内
        assert calc_time < 1.0      # 1秒以内
        assert total_duration > 0
    
    def test_action_memory_usage(self):
        """アクションのメモリ使用量"""
        # Arrange
        import sys
        
        # Act
        keyboard_action = KeyboardActionFactory()
        mouse_action = MouseActionFactory()
        delay_action = DelayActionFactory()
        
        # Assert - 合理的なサイズであること
        kb_size = sys.getsizeof(keyboard_action)
        mouse_size = sys.getsizeof(mouse_action)
        delay_size = sys.getsizeof(delay_action)
        
        # 各アクションが1KB以下であること
        assert kb_size < 1024
        assert mouse_size < 1024
        assert delay_size < 1024