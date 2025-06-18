"""
マウスアダプター - マウス操作の実装

Windows API を使用したマウス入力の実装です。
DPIスケーリング対応、高精度マウス操作等を含みます。
"""

import threading
import time
from typing import Optional, Tuple, List

from ...core.result import Result, Ok, Err, ErrorInfo
from ...domain import MouseAction, WindowAction
from ...domain.value_objects import ActionType, MouseButton, Coordinate, WindowInfo
from ..services.windows_api_service import WindowsApiService, WindowInformation


class MouseAdapter:
    """マウス操作アダプター"""
    
    def __init__(self, windows_api_service: WindowsApiService):
        self._windows_api_service = windows_api_service
        self._lock = threading.RLock()
        
        # システム情報を取得
        self._system_info = self._windows_api_service.get_system_info()
        
        # マウス設定
        self._double_click_time = 500  # ミリ秒
        self._drag_threshold = 5  # ピクセル
        
        # 状態管理
        self._last_click_time = 0
        self._last_click_position = (0, 0)
        self._is_dragging = False
        self._drag_start_position = (0, 0)
    
    def execute_action(self, action: MouseAction) -> Result[None, str]:
        """マウスアクションを実行"""
        try:
            with self._lock:
                if action.action_type == ActionType.MOUSE_CLICK:
                    return self._execute_mouse_click(action)
                elif action.action_type == ActionType.MOUSE_DOUBLE_CLICK:
                    return self._execute_mouse_double_click(action)
                elif action.action_type == ActionType.MOUSE_WHEEL:
                    return self._execute_mouse_wheel(action)
                else:
                    return Err(f"未対応のマウスアクションタイプ: {action.action_type}")
                    
        except Exception as e:
            return Err(f"マウスアクション実行エラー: {str(e)}")
    
    def execute_window_action(self, action: WindowAction) -> Result[None, str]:
        """ウィンドウアクションを実行"""
        try:
            with self._lock:
                if action.action_type == ActionType.WINDOW_ACTIVATE:
                    return self._execute_window_activate(action)
                elif action.action_type == ActionType.WINDOW_RESIZE:
                    return self._execute_window_resize(action)
                else:
                    return Err(f"未対応のウィンドウアクションタイプ: {action.action_type}")
                    
        except Exception as e:
            return Err(f"ウィンドウアクション実行エラー: {str(e)}")
    
    def _execute_mouse_click(self, action: MouseAction) -> Result[None, str]:
        """マウスクリックを実行"""
        if not action.mouse_input:
            return Err("マウス入力が指定されていません")
        
        mouse_input = action.mouse_input
        
        # 実行前の遅延
        if action.delay_before.milliseconds > 0:
            time.sleep(action.delay_before.seconds)
        
        # 座標の調整
        target_pos = self._adjust_coordinates(mouse_input.position, action)
        
        # マウスクリック送信
        result = self._windows_api_service.send_mouse_input(
            target_pos.x,
            target_pos.y,
            mouse_input.button.value,
            double_click=False,
            wheel_delta=0
        )
        
        # クリック情報を記録
        self._last_click_time = time.time() * 1000
        self._last_click_position = (target_pos.x, target_pos.y)
        
        # 実行後の遅延
        if action.delay_after.milliseconds > 0:
            time.sleep(action.delay_after.seconds)
        
        return result
    
    def _execute_mouse_double_click(self, action: MouseAction) -> Result[None, str]:
        """マウスダブルクリックを実行"""
        if not action.mouse_input:
            return Err("マウス入力が指定されていません")
        
        mouse_input = action.mouse_input
        
        # 実行前の遅延
        if action.delay_before.milliseconds > 0:
            time.sleep(action.delay_before.seconds)
        
        # 座標の調整
        target_pos = self._adjust_coordinates(mouse_input.position, action)
        
        # ダブルクリック送信
        result = self._windows_api_service.send_mouse_input(
            target_pos.x,
            target_pos.y,
            mouse_input.button.value,
            double_click=True,
            wheel_delta=0
        )
        
        # 実行後の遅延
        if action.delay_after.milliseconds > 0:
            time.sleep(action.delay_after.seconds)
        
        return result
    
    def _execute_mouse_wheel(self, action: MouseAction) -> Result[None, str]:
        """マウスホイールを実行"""
        if not action.mouse_input:
            return Err("マウス入力が指定されていません")
        
        mouse_input = action.mouse_input
        
        # 実行前の遅延
        if action.delay_before.milliseconds > 0:
            time.sleep(action.delay_before.seconds)
        
        # 座標の調整（ホイール位置）
        target_pos = self._adjust_coordinates(mouse_input.position, action)
        
        # ホイール操作送信
        result = self._windows_api_service.send_mouse_input(
            target_pos.x,
            target_pos.y,
            button=1,  # ホイールの場合はボタンは無視
            double_click=False,
            wheel_delta=mouse_input.wheel_delta
        )
        
        # 実行後の遅延
        if action.delay_after.milliseconds > 0:
            time.sleep(action.delay_after.seconds)
        
        return result
    
    def _execute_window_activate(self, action: WindowAction) -> Result[None, str]:
        """ウィンドウをアクティブ化"""
        if not action.target_window:
            return Err("対象ウィンドウが指定されていません")
        
        # 実行前の遅延
        if action.delay_before.milliseconds > 0:
            time.sleep(action.delay_before.seconds)
        
        # ウィンドウを検索
        window_result = self._find_window(action.target_window)
        if window_result.is_failure():
            return window_result
        
        window_info = window_result.value
        
        # ウィンドウをアクティブ化
        result = self._windows_api_service.activate_window(window_info.handle)
        
        # 新しい位置が指定されている場合は移動
        if action.new_position and result.is_success():
            move_result = self._windows_api_service.move_window(
                window_info.handle,
                action.new_position.x,
                action.new_position.y
            )
            if move_result.is_failure():
                return move_result
        
        # 実行後の遅延
        if action.delay_after.milliseconds > 0:
            time.sleep(action.delay_after.seconds)
        
        return result
    
    def _execute_window_resize(self, action: WindowAction) -> Result[None, str]:
        """ウィンドウをリサイズ"""
        if not action.target_window:
            return Err("対象ウィンドウが指定されていません")
        
        # 実行前の遅延
        if action.delay_before.milliseconds > 0:
            time.sleep(action.delay_before.seconds)
        
        # ウィンドウを検索
        window_result = self._find_window(action.target_window)
        if window_result.is_failure():
            return window_result
        
        window_info = window_result.value
        
        # 位置とサイズを決定
        x = action.new_position.x if action.new_position else window_info.rect[0]
        y = action.new_position.y if action.new_position else window_info.rect[1]
        width = action.new_size.x if action.new_size else (window_info.rect[2] - window_info.rect[0])
        height = action.new_size.y if action.new_size else (window_info.rect[3] - window_info.rect[1])
        
        # ウィンドウを移動・リサイズ
        result = self._windows_api_service.move_window(
            window_info.handle, x, y, width, height
        )
        
        # 実行後の遅延
        if action.delay_after.milliseconds > 0:
            time.sleep(action.delay_after.seconds)
        
        return result
    
    def click_at(self, x: int, y: int, button: MouseButton = MouseButton.LEFT) -> Result[None, str]:
        """指定位置をクリック"""
        try:
            with self._lock:
                return self._windows_api_service.send_mouse_input(
                    x, y, button.value, double_click=False, wheel_delta=0
                )
        except Exception as e:
            return Err(f"クリック実行エラー: {str(e)}")
    
    def double_click_at(self, x: int, y: int, button: MouseButton = MouseButton.LEFT) -> Result[None, str]:
        """指定位置をダブルクリック"""
        try:
            with self._lock:
                return self._windows_api_service.send_mouse_input(
                    x, y, button.value, double_click=True, wheel_delta=0
                )
        except Exception as e:
            return Err(f"ダブルクリック実行エラー: {str(e)}")
    
    def right_click_at(self, x: int, y: int) -> Result[None, str]:
        """指定位置を右クリック"""
        return self.click_at(x, y, MouseButton.RIGHT)
    
    def scroll_at(self, x: int, y: int, delta: int) -> Result[None, str]:
        """指定位置でスクロール"""
        try:
            with self._lock:
                return self._windows_api_service.send_mouse_input(
                    x, y, button=1, double_click=False, wheel_delta=delta
                )
        except Exception as e:
            return Err(f"スクロール実行エラー: {str(e)}")
    
    def move_to(self, x: int, y: int) -> Result[None, str]:
        """マウスカーソルを移動"""
        try:
            with self._lock:
                # カーソル位置を設定（クリックなし）
                from ctypes import windll
                windll.user32.SetCursorPos(x, y)
                return Ok(None)
        except Exception as e:
            return Err(f"マウス移動エラー: {str(e)}")
    
    def get_cursor_position(self) -> Result[Coordinate, str]:
        """現在のカーソル位置を取得"""
        try:
            with self._lock:
                pos_result = self._windows_api_service.get_cursor_position()
                if pos_result.is_success():
                    x, y = pos_result.value
                    return Ok(Coordinate(x, y))
                else:
                    return pos_result
        except Exception as e:
            return Err(f"カーソル位置取得エラー: {str(e)}")
    
    def drag_and_drop(self, start_x: int, start_y: int, end_x: int, end_y: int,
                     button: MouseButton = MouseButton.LEFT, 
                     duration: float = 1.0) -> Result[None, str]:
        """ドラッグアンドドロップを実行"""
        try:
            with self._lock:
                # 開始位置に移動
                move_result = self.move_to(start_x, start_y)
                if move_result.is_failure():
                    return move_result
                
                time.sleep(0.1)
                
                # マウスボタン押下
                press_result = self._press_mouse_button(button)
                if press_result.is_failure():
                    return press_result
                
                # ドラッグ移動（スムーズに移動）
                steps = max(10, int(duration * 100))  # 100 steps per second
                step_delay = duration / steps
                
                for i in range(1, steps + 1):
                    # 線形補間で中間位置を計算
                    progress = i / steps
                    current_x = int(start_x + (end_x - start_x) * progress)
                    current_y = int(start_y + (end_y - start_y) * progress)
                    
                    move_result = self.move_to(current_x, current_y)
                    if move_result.is_failure():
                        # エラーが発生した場合もボタンを離す
                        self._release_mouse_button(button)
                        return move_result
                    
                    time.sleep(step_delay)
                
                # マウスボタン離上
                release_result = self._release_mouse_button(button)
                return release_result
                
        except Exception as e:
            return Err(f"ドラッグアンドドロップエラー: {str(e)}")
    
    def find_window_by_title(self, title: str) -> Result[WindowInformation, str]:
        """タイトルでウィンドウを検索"""
        return self._windows_api_service.find_window(title=title)
    
    def find_window_by_class(self, class_name: str) -> Result[WindowInformation, str]:
        """クラス名でウィンドウを検索"""
        return self._windows_api_service.find_window(class_name=class_name)
    
    def get_all_windows(self) -> List[WindowInformation]:
        """すべてのウィンドウを取得"""
        return self._windows_api_service.enumerate_windows()
    
    def get_screen_size(self) -> Coordinate:
        """スクリーンサイズを取得"""
        return Coordinate(
            self._system_info.screen_width,
            self._system_info.screen_height
        )
    
    def get_dpi_scale_factor(self) -> float:
        """DPIスケールファクターを取得"""
        return self._system_info.scale_factor
    
    # プライベートメソッド
    def _adjust_coordinates(self, position: Coordinate, action: MouseAction) -> Coordinate:
        """座標をDPIスケーリングに合わせて調整"""
        if action.relative_to_window and action.target_window:
            # ウィンドウ相対座標の場合
            window_result = self._find_window(action.target_window)
            if window_result.is_success():
                window_info = window_result.value
                # ウィンドウの左上を基準とした絶対座標に変換
                abs_x = window_info.rect[0] + position.x
                abs_y = window_info.rect[1] + position.y
                return Coordinate(abs_x, abs_y, position.dpi_scale)
        
        # DPIスケーリングを適用
        if position.dpi_scale != 1.0:
            scaled_x = int(position.x * position.dpi_scale)
            scaled_y = int(position.y * position.dpi_scale)
            return Coordinate(scaled_x, scaled_y, 1.0)
        
        return position
    
    def _find_window(self, window_info: WindowInfo) -> Result[WindowInformation, str]:
        """ウィンドウ情報からウィンドウを検索"""
        return self._windows_api_service.find_window(
            title=window_info.title if window_info.title else None,
            class_name=window_info.class_name if window_info.class_name else None,
            process_name=window_info.process_name if window_info.process_name else None
        )
    
    def _press_mouse_button(self, button: MouseButton) -> Result[None, str]:
        """マウスボタンを押下"""
        try:
            from ctypes import windll
            
            if button == MouseButton.LEFT:
                windll.user32.mouse_event(0x0002, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
            elif button == MouseButton.RIGHT:
                windll.user32.mouse_event(0x0008, 0, 0, 0, 0)  # MOUSEEVENTF_RIGHTDOWN
            elif button == MouseButton.MIDDLE:
                windll.user32.mouse_event(0x0020, 0, 0, 0, 0)  # MOUSEEVENTF_MIDDLEDOWN
            
            return Ok(None)
        except Exception as e:
            return Err(f"マウスボタン押下エラー: {str(e)}")
    
    def _release_mouse_button(self, button: MouseButton) -> Result[None, str]:
        """マウスボタンを離上"""
        try:
            from ctypes import windll
            
            if button == MouseButton.LEFT:
                windll.user32.mouse_event(0x0004, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP
            elif button == MouseButton.RIGHT:
                windll.user32.mouse_event(0x0010, 0, 0, 0, 0)  # MOUSEEVENTF_RIGHTUP
            elif button == MouseButton.MIDDLE:
                windll.user32.mouse_event(0x0040, 0, 0, 0, 0)  # MOUSEEVENTF_MIDDLEUP
            
            return Ok(None)
        except Exception as e:
            return Err(f"マウスボタン離上エラー: {str(e)}")
    
    def _calculate_distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """2点間の距離を計算"""
        return ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5
    
    def close(self):
        """アダプターを閉じる"""
        # 必要に応じてクリーンアップ処理
        pass