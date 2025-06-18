"""
EZRPA v2.0 - 実際のRPA機能実装

マウス・キーボードの記録と再生機能を提供します。
"""

import time
import json
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
from pathlib import Path

# Windows API imports
try:
    import win32api
    import win32con
    import win32gui
    import win32hook
    import pythoncom
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

# Alternative cross-platform imports
try:
    import pynput
    from pynput import mouse, keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False


@dataclass
class RPAAction:
    """RPA アクション定義"""
    timestamp: float
    action_type: str  # 'mouse_move', 'mouse_click', 'key_press', 'key_release', 'scroll'
    data: Dict[str, Any]
    delay_after: float = 0.0


class RPARecorder:
    """RPA記録クラス"""
    
    def __init__(self):
        self.is_recording = False
        self.is_paused = False
        self.actions: List[RPAAction] = []
        self.start_time = 0
        self.mouse_listener = None
        self.keyboard_listener = None
        self.on_action_callback: Optional[Callable[[RPAAction], None]] = None
        
    def set_action_callback(self, callback: Callable[[RPAAction], None]):
        """アクション記録時のコールバック設定"""
        self.on_action_callback = callback
    
    def start_recording(self) -> bool:
        """記録開始"""
        if not HAS_PYNPUT:
            return False
            
        self.is_recording = True
        self.is_paused = False
        self.actions.clear()
        self.start_time = time.time()
        
        try:
            # マウスリスナー開始
            self.mouse_listener = mouse.Listener(
                on_move=self._on_mouse_move,
                on_click=self._on_mouse_click,
                on_scroll=self._on_mouse_scroll
            )
            self.mouse_listener.start()
            
            # キーボードリスナー開始
            self.keyboard_listener = keyboard.Listener(
                on_press=self._on_key_press,
                on_release=self._on_key_release
            )
            self.keyboard_listener.start()
            
            return True
        except Exception as e:
            print(f"記録開始エラー: {e}")
            return False
    
    def stop_recording(self) -> List[RPAAction]:
        """記録停止"""
        self.is_recording = False
        
        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None
            
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            self.keyboard_listener = None
            
        return self.actions.copy()
    
    def pause_recording(self):
        """記録一時停止"""
        self.is_paused = True
    
    def resume_recording(self):
        """記録再開"""
        self.is_paused = False
    
    def _record_action(self, action_type: str, data: Dict[str, Any]):
        """アクション記録"""
        if not self.is_recording or self.is_paused:
            return
            
        timestamp = time.time() - self.start_time
        action = RPAAction(
            timestamp=timestamp,
            action_type=action_type,
            data=data
        )
        
        self.actions.append(action)
        
        if self.on_action_callback:
            self.on_action_callback(action)
    
    def _on_mouse_move(self, x, y):
        """マウス移動イベント"""
        self._record_action('mouse_move', {'x': x, 'y': y})
    
    def _on_mouse_click(self, x, y, button, pressed):
        """マウスクリックイベント"""
        self._record_action('mouse_click', {
            'x': x, 'y': y, 
            'button': str(button), 
            'pressed': pressed
        })
    
    def _on_mouse_scroll(self, x, y, dx, dy):
        """マウススクロールイベント"""
        self._record_action('mouse_scroll', {
            'x': x, 'y': y, 
            'dx': dx, 'dy': dy
        })
    
    def _on_key_press(self, key):
        """キー押下イベント"""
        try:
            key_name = key.char if hasattr(key, 'char') and key.char else str(key)
        except AttributeError:
            key_name = str(key)
            
        self._record_action('key_press', {'key': key_name})
    
    def _on_key_release(self, key):
        """キー離脱イベント"""
        try:
            key_name = key.char if hasattr(key, 'char') and key.char else str(key)
        except AttributeError:
            key_name = str(key)
            
        self._record_action('key_release', {'key': key_name})


class RPAPlayer:
    """RPA再生クラス"""
    
    def __init__(self):
        self.is_playing = False
        self.is_paused = False
        self.current_action_index = 0
        self.actions: List[RPAAction] = []
        self.play_thread: Optional[threading.Thread] = None
        self.on_progress_callback: Optional[Callable[[int, int], None]] = None
        self.on_complete_callback: Optional[Callable[[], None]] = None
        self.speed_multiplier = 1.0
        
    def set_progress_callback(self, callback: Callable[[int, int], None]):
        """進捗コールバック設定"""
        self.on_progress_callback = callback
    
    def set_complete_callback(self, callback: Callable[[], None]):
        """完了コールバック設定"""
        self.on_complete_callback = callback
    
    def load_actions(self, actions: List[RPAAction]):
        """再生するアクションを読み込み"""
        self.actions = actions.copy()
        self.current_action_index = 0
    
    def start_playback(self, speed_multiplier: float = 1.0) -> bool:
        """再生開始"""
        if not HAS_PYNPUT or not self.actions:
            return False
            
        self.is_playing = True
        self.is_paused = False
        self.speed_multiplier = speed_multiplier
        self.current_action_index = 0
        
        self.play_thread = threading.Thread(target=self._play_actions)
        self.play_thread.daemon = True
        self.play_thread.start()
        
        return True
    
    def stop_playback(self):
        """再生停止"""
        self.is_playing = False
        self.is_paused = False
    
    def pause_playback(self):
        """再生一時停止"""
        self.is_paused = True
    
    def resume_playback(self):
        """再生再開"""
        self.is_paused = False
    
    def _play_actions(self):
        """アクション再生メインループ"""
        try:
            mouse_controller = mouse.Controller()
            keyboard_controller = keyboard.Controller()
            
            last_timestamp = 0
            
            for i, action in enumerate(self.actions):
                if not self.is_playing:
                    break
                
                # 一時停止中は待機
                while self.is_paused and self.is_playing:
                    time.sleep(0.1)
                
                if not self.is_playing:
                    break
                
                # タイミング調整
                delay = (action.timestamp - last_timestamp) / self.speed_multiplier
                if delay > 0:
                    time.sleep(delay)
                
                # アクション実行
                self._execute_action(action, mouse_controller, keyboard_controller)
                
                last_timestamp = action.timestamp
                self.current_action_index = i + 1
                
                # 進捗報告
                if self.on_progress_callback:
                    self.on_progress_callback(i + 1, len(self.actions))
            
            # 完了通知
            if self.is_playing and self.on_complete_callback:
                self.on_complete_callback()
                
        except Exception as e:
            print(f"再生エラー: {e}")
        finally:
            self.is_playing = False
    
    def _execute_action(self, action: RPAAction, mouse_controller, keyboard_controller):
        """個別アクション実行"""
        try:
            if action.action_type == 'mouse_move':
                x, y = action.data['x'], action.data['y']
                mouse_controller.position = (x, y)
                
            elif action.action_type == 'mouse_click':
                x, y = action.data['x'], action.data['y']
                button_str = action.data['button']
                pressed = action.data['pressed']
                
                mouse_controller.position = (x, y)
                
                if 'left' in button_str.lower():
                    button = mouse.Button.left
                elif 'right' in button_str.lower():
                    button = mouse.Button.right
                elif 'middle' in button_str.lower():
                    button = mouse.Button.middle
                else:
                    button = mouse.Button.left
                
                if pressed:
                    mouse_controller.press(button)
                else:
                    mouse_controller.release(button)
                    
            elif action.action_type == 'mouse_scroll':
                x, y = action.data['x'], action.data['y']
                dx, dy = action.data['dx'], action.data['dy']
                mouse_controller.position = (x, y)
                mouse_controller.scroll(dx, dy)
                
            elif action.action_type == 'key_press':
                key_name = action.data['key']
                key = self._parse_key(key_name)
                if key:
                    keyboard_controller.press(key)
                    
            elif action.action_type == 'key_release':
                key_name = action.data['key']
                key = self._parse_key(key_name)
                if key:
                    keyboard_controller.release(key)
                    
        except Exception as e:
            print(f"アクション実行エラー: {e}")
    
    def _parse_key(self, key_name: str):
        """キー名からキーオブジェクトを生成"""
        try:
            # 特殊キー処理
            if key_name.startswith('Key.'):
                key_attr = key_name.replace('Key.', '')
                return getattr(keyboard.Key, key_attr, None)
            
            # 通常の文字キー
            if len(key_name) == 1:
                return key_name
            
            # その他の特殊キー
            special_keys = {
                'space': keyboard.Key.space,
                'enter': keyboard.Key.enter,
                'tab': keyboard.Key.tab,
                'shift': keyboard.Key.shift,
                'ctrl': keyboard.Key.ctrl,
                'alt': keyboard.Key.alt,
                'esc': keyboard.Key.esc,
                'backspace': keyboard.Key.backspace,
                'delete': keyboard.Key.delete,
            }
            
            return special_keys.get(key_name.lower())
            
        except Exception:
            return None


class RPAManager:
    """RPA管理クラス"""
    
    def __init__(self):
        self.recorder = RPARecorder()
        self.player = RPAPlayer()
        self.recordings: Dict[str, List[RPAAction]] = {}
        self.data_dir = Path("recordings")
        self.data_dir.mkdir(exist_ok=True)
    
    def start_recording(self, name: str) -> bool:
        """記録開始"""
        return self.recorder.start_recording()
    
    def stop_recording(self, name: str) -> bool:
        """記録停止と保存"""
        actions = self.recorder.stop_recording()
        if actions:
            self.recordings[name] = actions
            self.save_recording(name, actions)
            return True
        return False
    
    def save_recording(self, name: str, actions: List[RPAAction]):
        """記録をファイルに保存"""
        try:
            file_path = self.data_dir / f"{name}.json"
            data = {
                'name': name,
                'created_at': datetime.now().isoformat(),
                'action_count': len(actions),
                'actions': [asdict(action) for action in actions]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"保存エラー: {e}")
    
    def load_recording(self, name: str) -> Optional[List[RPAAction]]:
        """記録をファイルから読み込み"""
        try:
            file_path = self.data_dir / f"{name}.json"
            if not file_path.exists():
                return None
                
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            actions = []
            for action_data in data['actions']:
                action = RPAAction(**action_data)
                actions.append(action)
            
            self.recordings[name] = actions
            return actions
            
        except Exception as e:
            print(f"読み込みエラー: {e}")
            return None
    
    def list_recordings(self) -> List[str]:
        """保存された記録の一覧取得"""
        recordings = []
        for file_path in self.data_dir.glob("*.json"):
            recordings.append(file_path.stem)
        return recordings
    
    def play_recording(self, name: str, speed_multiplier: float = 1.0) -> bool:
        """記録再生"""
        if name in self.recordings:
            actions = self.recordings[name]
        else:
            actions = self.load_recording(name)
            
        if actions:
            self.player.load_actions(actions)
            return self.player.start_playback(speed_multiplier)
        return False
    
    def get_available_status(self) -> Dict[str, bool]:
        """利用可能な機能の状態取得"""
        return {
            'pynput_available': HAS_PYNPUT,
            'win32_available': HAS_WIN32,
            'recording_supported': HAS_PYNPUT,
            'playback_supported': HAS_PYNPUT
        }