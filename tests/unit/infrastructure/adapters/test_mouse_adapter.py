"""
Mouse Adapter Unit Tests - マウスアダプターのテスト

Windows APIを使用したマウス操作アダプターの機能をテストします。
"""

import pytest
import threading
import time
from unittest.mock import Mock, patch, MagicMock

from src.infrastructure.adapters.mouse_adapter import MouseAdapter
from src.core.result import Result, Ok, Err, ErrorInfo
from src.domain.entities.action import MouseAction
from src.domain.value_objects import ActionType
from tests.factories import MouseActionFactory


class TestMouseAdapter:
    """マウスアダプターのテストクラス"""
    
    @pytest.fixture
    def mock_windows_api_service(self):
        """モックWindows APIサービス"""
        mock_service = Mock()
        mock_service.move_mouse.return_value = Ok(True)
        mock_service.click_mouse.return_value = Ok(True)
        mock_service.double_click_mouse.return_value = Ok(True)
        mock_service.right_click_mouse.return_value = Ok(True)
        mock_service.scroll_mouse.return_value = Ok(True)
        mock_service.get_cursor_position.return_value = Ok((100, 200))
        mock_service.set_cursor_position.return_value = Ok(True)
        return mock_service
    
    @pytest.fixture
    def adapter(self, mock_windows_api_service):
        """テスト対象のマウスアダプター"""
        return MouseAdapter(windows_api_service=mock_windows_api_service)
    
    # ========================
    # 初期化・設定テスト
    # ========================
    
    def test_adapter_initialization(self, adapter):
        """アダプター初期化のテスト"""
        # Assert
        assert adapter._windows_api_service is not None
        assert adapter._lock is not None
        assert adapter._current_position is not None
        assert adapter._button_states is not None
        assert adapter._click_threshold > 0
        assert adapter._double_click_interval > 0
    
    def test_button_states_initialization(self, adapter):
        """マウスボタン状態初期化のテスト"""
        # Assert
        states = adapter._button_states
        assert 'left' in states
        assert 'right' in states
        assert 'middle' in states
        
        # 初期状態は全てFalse（押下されていない）
        assert all(not state for state in states.values())
    
    def test_position_tracking_initialization(self, adapter):
        """位置追跡初期化のテスト"""
        # Assert
        assert adapter._current_position == (0, 0)
        assert adapter._previous_position == (0, 0)
        assert adapter._movement_history == []
    
    # ========================
    # マウス移動テスト
    # ========================
    
    def test_execute_mouse_move_success(self, adapter, mock_windows_api_service):
        """マウス移動実行成功のテスト"""
        # Arrange
        action = MouseAction(
            action_id="test_move",
            action_type=ActionType.MOUSE_MOVE,
            x=300,
            y=400,
            timestamp=time.time()
        )
        
        # Act
        result = adapter.execute_action(action)
        
        # Assert
        assert result.is_success()
        mock_windows_api_service.move_mouse.assert_called_once_with(300, 400)
        assert adapter._current_position == (300, 400)
    
    def test_execute_relative_mouse_move(self, adapter, mock_windows_api_service):
        """相対マウス移動のテスト"""
        # Arrange
        adapter._current_position = (100, 100)
        action = MouseAction(
            action_id="test_relative_move",
            action_type=ActionType.MOUSE_MOVE,
            x=50,
            y=75,
            relative=True,
            timestamp=time.time()
        )
        
        # Act
        result = adapter.execute_action(action)
        
        # Assert
        assert result.is_success()
        # 相対移動: (100,100) + (50,75) = (150,175)
        mock_windows_api_service.move_mouse.assert_called_once_with(150, 175)
        assert adapter._current_position == (150, 175)
    
    def test_smooth_mouse_movement(self, adapter, mock_windows_api_service):
        """スムーズマウス移動のテスト"""
        # Arrange
        adapter._current_position = (0, 0)
        action = MouseAction(
            action_id="test_smooth_move",
            action_type=ActionType.MOUSE_MOVE,
            x=200,
            y=200,
            smooth=True,
            duration_ms=100,
            timestamp=time.time()
        )
        
        # Act
        result = adapter.execute_action(action)
        
        # Assert
        assert result.is_success()
        # スムーズ移動では複数回のmove_mouseが呼ばれる
        assert mock_windows_api_service.move_mouse.call_count > 1
        assert adapter._current_position == (200, 200)
    
    def test_mouse_move_out_of_bounds(self, adapter, mock_windows_api_service):
        """範囲外マウス移動のテスト"""
        # Arrange
        action = MouseAction(
            action_id="test_out_of_bounds",
            action_type=ActionType.MOUSE_MOVE,
            x=-100,  # 負の座標
            y=10000,  # 画面外の座標
            timestamp=time.time()
        )
        
        # 境界チェックを有効にした場合の動作確認
        mock_windows_api_service.move_mouse.return_value = Err("COORDINATES_OUT_OF_BOUNDS")
        
        # Act
        result = adapter.execute_action(action)
        
        # Assert
        assert result.is_failure()
        assert "COORDINATES_OUT_OF_BOUNDS" in result.error
    
    # ========================
    # マウスクリックテスト
    # ========================
    
    def test_execute_left_click_success(self, adapter, mock_windows_api_service):
        """左クリック実行成功のテスト"""
        # Arrange
        action = MouseAction(
            action_id="test_left_click",
            action_type=ActionType.MOUSE_CLICK,
            x=150,
            y=250,
            button="left",
            timestamp=time.time()
        )
        
        # Act
        result = adapter.execute_action(action)
        
        # Assert
        assert result.is_success()
        mock_windows_api_service.click_mouse.assert_called_once_with(150, 250, "left")
    
    def test_execute_right_click_success(self, adapter, mock_windows_api_service):
        """右クリック実行成功のテスト"""
        # Arrange
        action = MouseAction(
            action_id="test_right_click",
            action_type=ActionType.MOUSE_CLICK,
            x=300,
            y=400,
            button="right",
            timestamp=time.time()
        )
        
        # Act
        result = adapter.execute_action(action)
        
        # Assert
        assert result.is_success()
        mock_windows_api_service.right_click_mouse.assert_called_once_with(300, 400)
    
    def test_execute_double_click_success(self, adapter, mock_windows_api_service):
        """ダブルクリック実行成功のテスト"""
        # Arrange
        action = MouseAction(
            action_id="test_double_click",
            action_type=ActionType.MOUSE_DOUBLE_CLICK,
            x=200,
            y=300,
            button="left",
            timestamp=time.time()
        )
        
        # Act
        result = adapter.execute_action(action)
        
        # Assert
        assert result.is_success()
        mock_windows_api_service.double_click_mouse.assert_called_once_with(200, 300, "left")
    
    def test_execute_middle_click(self, adapter, mock_windows_api_service):
        """中クリック実行のテスト"""
        # Arrange
        action = MouseAction(
            action_id="test_middle_click",
            action_type=ActionType.MOUSE_CLICK,
            x=100,
            y=150,
            button="middle",
            timestamp=time.time()
        )
        
        # Act
        result = adapter.execute_action(action)
        
        # Assert
        assert result.is_success()
        mock_windows_api_service.click_mouse.assert_called_once_with(100, 150, "middle")
    
    def test_click_with_modifiers(self, adapter, mock_windows_api_service):
        """修飾キー付きクリックのテスト"""
        # Arrange
        action = MouseAction(
            action_id="test_ctrl_click",
            action_type=ActionType.MOUSE_CLICK,
            x=250,
            y=350,
            button="left",
            modifiers=["ctrl"],
            timestamp=time.time()
        )
        
        # Act
        result = adapter.execute_action(action)
        
        # Assert
        assert result.is_success()
        # 修飾キー付きクリックが正しく処理される
        mock_windows_api_service.click_mouse.assert_called()
    
    # ========================
    # マウススクロールテスト
    # ========================
    
    def test_execute_vertical_scroll_up(self, adapter, mock_windows_api_service):
        """垂直スクロール（上）のテスト"""
        # Arrange
        action = MouseAction(
            action_id="test_scroll_up",
            action_type=ActionType.MOUSE_SCROLL,
            x=200,
            y=300,
            scroll_direction="up",
            scroll_amount=3,
            timestamp=time.time()
        )
        
        # Act
        result = adapter.execute_action(action)
        
        # Assert
        assert result.is_success()
        mock_windows_api_service.scroll_mouse.assert_called_once_with(200, 300, "up", 3)
    
    def test_execute_vertical_scroll_down(self, adapter, mock_windows_api_service):
        """垂直スクロール（下）のテスト"""
        # Arrange
        action = MouseAction(
            action_id="test_scroll_down",
            action_type=ActionType.MOUSE_SCROLL,
            x=150,
            y=250,
            scroll_direction="down",
            scroll_amount=5,
            timestamp=time.time()
        )
        
        # Act
        result = adapter.execute_action(action)
        
        # Assert
        assert result.is_success()
        mock_windows_api_service.scroll_mouse.assert_called_once_with(150, 250, "down", 5)
    
    def test_execute_horizontal_scroll(self, adapter, mock_windows_api_service):
        """水平スクロールのテスト"""
        # Arrange
        action = MouseAction(
            action_id="test_scroll_left",
            action_type=ActionType.MOUSE_SCROLL,
            x=300,
            y=400,
            scroll_direction="left",
            scroll_amount=2,
            timestamp=time.time()
        )
        
        # Act
        result = adapter.execute_action(action)
        
        # Assert
        assert result.is_success()
        mock_windows_api_service.scroll_mouse.assert_called_once_with(300, 400, "left", 2)
    
    # ========================
    # ドラッグ&ドロップテスト
    # ========================
    
    def test_execute_drag_and_drop_success(self, adapter, mock_windows_api_service):
        """ドラッグ&ドロップ実行成功のテスト"""
        # Arrange
        action = MouseAction(
            action_id="test_drag_drop",
            action_type=ActionType.MOUSE_DRAG,
            x=100,
            y=100,
            target_x=300,
            target_y=300,
            button="left",
            timestamp=time.time()
        )
        
        # Act
        result = adapter.execute_action(action)
        
        # Assert
        assert result.is_success()
        # ドラッグ&ドロップでは、開始位置でのpress、移動、終了位置でのreleaseが実行される
        assert mock_windows_api_service.move_mouse.call_count >= 2
    
    def test_smooth_drag_operation(self, adapter, mock_windows_api_service):
        """スムーズドラッグ操作のテスト"""
        # Arrange
        action = MouseAction(
            action_id="test_smooth_drag",
            action_type=ActionType.MOUSE_DRAG,
            x=50,
            y=50,
            target_x=250,
            target_y=250,
            button="left",
            smooth=True,
            duration_ms=200,
            timestamp=time.time()
        )
        
        # Act
        result = adapter.execute_action(action)
        
        # Assert
        assert result.is_success()
        # スムーズドラッグでは複数の中間位置を経由する
        assert mock_windows_api_service.move_mouse.call_count > 2
    
    # ========================
    # 位置取得・設定テスト
    # ========================
    
    def test_get_current_position(self, adapter, mock_windows_api_service):
        """現在位置取得のテスト"""
        # Arrange
        mock_windows_api_service.get_cursor_position.return_value = Ok((350, 450))
        
        # Act
        result = adapter.get_current_position()
        
        # Assert
        assert result.is_success()
        position = result.value
        assert position == (350, 450)
        mock_windows_api_service.get_cursor_position.assert_called_once()
    
    def test_set_cursor_position(self, adapter, mock_windows_api_service):
        """カーソル位置設定のテスト"""
        # Act
        result = adapter.set_cursor_position(400, 500)
        
        # Assert
        assert result.is_success()
        mock_windows_api_service.set_cursor_position.assert_called_once_with(400, 500)
        assert adapter._current_position == (400, 500)
    
    def test_position_tracking_update(self, adapter):
        """位置追跡更新のテスト"""
        # Arrange
        initial_position = (100, 100)
        new_position = (200, 200)
        
        adapter._current_position = initial_position
        
        # Act
        adapter._update_position(new_position[0], new_position[1])
        
        # Assert
        assert adapter._current_position == new_position
        assert adapter._previous_position == initial_position
        assert len(adapter._movement_history) == 1
        assert adapter._movement_history[0] == new_position
    
    # ========================
    # ボタン状態管理テスト
    # ========================
    
    def test_button_press_and_release(self, adapter, mock_windows_api_service):
        """ボタン押下・離脱のテスト"""
        # Act - ボタン押下
        press_result = adapter.press_button("left", 100, 200)
        
        # Assert
        assert press_result.is_success()
        assert adapter._button_states["left"] is True
        
        # Act - ボタン離脱
        release_result = adapter.release_button("left", 100, 200)
        
        # Assert
        assert release_result.is_success()
        assert adapter._button_states["left"] is False
    
    def test_invalid_button_press(self, adapter):
        """無効なボタン押下のテスト"""
        # Act
        result = adapter.press_button("invalid_button", 100, 200)
        
        # Assert
        assert result.is_failure()
        assert "INVALID_BUTTON" in result.error
    
    def test_multiple_button_states(self, adapter, mock_windows_api_service):
        """複数ボタン状態管理のテスト"""
        # Act - 複数ボタンを押下
        adapter.press_button("left", 100, 200)
        adapter.press_button("right", 100, 200)
        
        # Assert
        assert adapter._button_states["left"] is True
        assert adapter._button_states["right"] is True
        assert adapter._button_states["middle"] is False
        
        # Act - 一部ボタンを離脱
        adapter.release_button("left", 100, 200)
        
        # Assert
        assert adapter._button_states["left"] is False
        assert adapter._button_states["right"] is True  # まだ押下中
    
    # ========================
    # エラーハンドリングテスト
    # ========================
    
    def test_windows_api_service_failure(self, adapter, mock_windows_api_service):
        """Windows APIサービス失敗時のテスト"""
        # Arrange
        mock_windows_api_service.click_mouse.return_value = Err("API_ERROR")
        
        action = MouseAction(
            action_id="test_action",
            action_type=ActionType.MOUSE_CLICK,
            x=100,
            y=200,
            button="left",
            timestamp=time.time()
        )
        
        # Act
        result = adapter.execute_action(action)
        
        # Assert
        assert result.is_failure()
        assert "API_ERROR" in result.error
    
    def test_unsupported_action_type(self, adapter):
        """サポートされていないアクションタイプのテスト"""
        # Arrange
        action = MouseAction(
            action_id="test_action",
            action_type="UNSUPPORTED_TYPE",
            x=100,
            y=200,
            timestamp=time.time()
        )
        
        # Act
        result = adapter.execute_action(action)
        
        # Assert
        assert result.is_failure()
        assert "UNSUPPORTED_ACTION" in result.error
    
    def test_action_execution_exception(self, adapter, mock_windows_api_service):
        """アクション実行時の例外処理テスト"""
        # Arrange
        mock_windows_api_service.click_mouse.side_effect = Exception("Unexpected error")
        
        action = MouseAction(
            action_id="test_action",
            action_type=ActionType.MOUSE_CLICK,
            x=100,
            y=200,
            button="left",
            timestamp=time.time()
        )
        
        # Act
        result = adapter.execute_action(action)
        
        # Assert
        assert result.is_failure()
        assert "EXECUTION_ERROR" in result.error
    
    # ========================
    # スレッドセーフティテスト
    # ========================
    
    def test_concurrent_mouse_operations(self, adapter, mock_windows_api_service):
        """並行マウス操作のテスト"""
        import threading
        
        results = []
        errors = []
        
        def execute_mouse_action(action_id):
            try:
                action = MouseAction(
                    action_id=f"concurrent_action_{action_id}",
                    action_type=ActionType.MOUSE_CLICK,
                    x=100 + action_id * 10,
                    y=200 + action_id * 10,
                    button="left",
                    timestamp=time.time()
                )
                result = adapter.execute_action(action)
                if result.is_success():
                    results.append(action_id)
                else:
                    errors.append(f"Failed for {action_id}: {result.error}")
            except Exception as e:
                errors.append(f"Exception for {action_id}: {e}")
        
        # Act - 複数スレッドで並行実行
        threads = []
        for i in range(5):
            thread = threading.Thread(target=execute_mouse_action, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Assert
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5, f"Expected 5 results, got {len(results)}"
    
    def test_position_tracking_thread_safety(self, adapter):
        """位置追跡のスレッドセーフティテスト"""
        import threading
        
        final_positions = []
        
        def update_position(x, y):
            adapter._update_position(x, y)
            final_positions.append(adapter._current_position)
        
        # Act - 複数スレッドで位置更新
        threads = []
        for i in range(10):
            thread = threading.Thread(target=update_position, args=(i * 10, i * 20))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Assert - 全ての更新が完了し、データ競合が発生していない
        assert len(final_positions) == 10
        assert adapter._current_position in final_positions
    
    # ========================
    # パフォーマンステスト
    # ========================
    
    def test_rapid_click_performance(self, adapter, mock_windows_api_service):
        """高速クリックパフォーマンステスト"""
        # Arrange
        actions = []
        for i in range(50):
            action = MouseAction(
                action_id=f"rapid_click_{i}",
                action_type=ActionType.MOUSE_CLICK,
                x=100 + i,
                y=200 + i,
                button="left",
                timestamp=time.time()
            )
            actions.append(action)
        
        # Act
        start_time = time.time()
        for action in actions:
            result = adapter.execute_action(action)
            assert result.is_success()
        end_time = time.time()
        
        # Assert - パフォーマンス要件: 50クリックの実行が1秒以内
        assert (end_time - start_time) < 1.0
    
    def test_smooth_movement_performance(self, adapter, mock_windows_api_service):
        """スムーズ移動パフォーマンステスト"""
        # Arrange
        action = MouseAction(
            action_id="performance_smooth_move",
            action_type=ActionType.MOUSE_MOVE,
            x=1000,
            y=1000,
            smooth=True,
            duration_ms=500,
            timestamp=time.time()
        )
        
        # Act
        start_time = time.time()
        result = adapter.execute_action(action)
        end_time = time.time()
        
        # Assert
        assert result.is_success()
        # スムーズ移動の時間が指定した時間内に完了
        assert (end_time - start_time) < 1.0  # 500ms + 余裕
    
    # ========================
    # 統合テスト
    # ========================
    
    def test_complete_mouse_workflow(self, adapter, mock_windows_api_service):
        """完全なマウスワークフローのテスト"""
        # Arrange - 複雑なマウス操作シナリオ
        workflow_actions = [
            # 移動
            MouseAction(
                action_id="step1",
                action_type=ActionType.MOUSE_MOVE,
                x=100,
                y=100,
                timestamp=time.time()
            ),
            # 左クリック
            MouseAction(
                action_id="step2",
                action_type=ActionType.MOUSE_CLICK,
                x=100,
                y=100,
                button="left",
                timestamp=time.time()
            ),
            # ドラッグ
            MouseAction(
                action_id="step3",
                action_type=ActionType.MOUSE_DRAG,
                x=100,
                y=100,
                target_x=300,
                target_y=300,
                button="left",
                timestamp=time.time()
            ),
            # 右クリック
            MouseAction(
                action_id="step4",
                action_type=ActionType.MOUSE_CLICK,
                x=300,
                y=300,
                button="right",
                timestamp=time.time()
            ),
            # スクロール
            MouseAction(
                action_id="step5",
                action_type=ActionType.MOUSE_SCROLL,
                x=300,
                y=300,
                scroll_direction="up",
                scroll_amount=3,
                timestamp=time.time()
            )
        ]
        
        # Act - ワークフロー実行
        for action in workflow_actions:
            result = adapter.execute_action(action)
            assert result.is_success(), f"Failed at action: {action.action_id}"
        
        # Assert - 全てのAPIコールが実行された
        assert mock_windows_api_service.move_mouse.call_count >= 2
        assert mock_windows_api_service.click_mouse.call_count >= 1
        assert mock_windows_api_service.right_click_mouse.call_count >= 1
        assert mock_windows_api_service.scroll_mouse.call_count >= 1
        
        # 最終位置が正しく更新されている
        assert adapter._current_position == (300, 300)