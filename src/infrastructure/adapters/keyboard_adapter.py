"""
キーボードアダプター - キーボード操作の実装

Windows API を使用したキーボード入力の実装です。
IMEサポート、日本語入力、ホットキー処理等を含みます。
"""

import threading
import time
from typing import Optional, Dict, List

from ...core.result import Result, Ok, Err, ErrorInfo
from ...domain import KeyboardAction, KeyInput
from ...domain.value_objects import ActionType
from ..services.windows_api_service import WindowsApiService
from ...shared.constants import WindowsKeys


class KeyboardAdapter:
    """キーボード操作アダプター"""
    
    def __init__(self, windows_api_service: WindowsApiService):
        self._windows_api_service = windows_api_service
        self._lock = threading.RLock()
        
        # ホットキーリスナー用
        self._hotkey_listeners: Dict[str, callable] = {}
        self._listening = False
        self._listener_thread: Optional[threading.Thread] = None
        
        # キーマッピング（文字からVKコードへ）
        self._char_to_vk = self._initialize_char_mapping()
        
        # 修飾キー状態管理
        self._modifier_states = {
            'shift': False,
            'ctrl': False,
            'alt': False,
            'win': False
        }
    
    def execute_action(self, action: KeyboardAction) -> Result[None, str]:
        """キーボードアクションを実行"""
        try:
            with self._lock:
                if action.action_type == ActionType.TEXT_INPUT:
                    return self._execute_text_input(action)
                elif action.action_type in [ActionType.KEY_PRESS, ActionType.KEY_COMBINATION]:
                    return self._execute_key_input(action)
                else:
                    return Err(f"未対応のアクションタイプ: {action.action_type}")
                    
        except Exception as e:
            return Err(f"キーボードアクション実行エラー: {str(e)}")
    
    def _execute_text_input(self, action: KeyboardAction) -> Result[None, str]:
        """テキスト入力を実行"""
        if not action.text:
            return Err("テキストが指定されていません")
        
        # 実行前の遅延
        if action.delay_before.milliseconds > 0:
            time.sleep(action.delay_before.seconds)
        
        # IME使用判定
        use_ime = (action.input_method == "ime" or 
                  action.metadata.get('requires_ime', False))
        
        # テキスト送信
        result = self._windows_api_service.send_text_input(action.text, use_ime)
        
        # 実行後の遅延
        if action.delay_after.milliseconds > 0:
            time.sleep(action.delay_after.seconds)
        
        return result
    
    def _execute_key_input(self, action: KeyboardAction) -> Result[None, str]:
        """キー入力を実行"""
        if not action.key_input:
            return Err("キー入力が指定されていません")
        
        key_input = action.key_input
        
        # 実行前の遅延
        if action.delay_before.milliseconds > 0:
            time.sleep(action.delay_before.seconds)
        
        # キー入力送信
        result = self._windows_api_service.send_key_input(
            key_input.key_code,
            key_input.shift,
            key_input.ctrl,
            key_input.alt,
            key_input.win
        )
        
        # 実行後の遅延
        if action.delay_after.milliseconds > 0:
            time.sleep(action.delay_after.seconds)
        
        return result
    
    def send_text(self, text: str, use_ime: bool = None) -> Result[None, str]:
        """テキストを直接送信"""
        try:
            with self._lock:
                if use_ime is None:
                    # 日本語文字が含まれている場合は自動でIME使用
                    use_ime = self._contains_japanese_chars(text)
                
                return self._windows_api_service.send_text_input(text, use_ime)
                
        except Exception as e:
            return Err(f"テキスト送信エラー: {str(e)}")
    
    def send_key_combination(self, keys: List[str]) -> Result[None, str]:
        """キーコンビネーションを送信"""
        try:
            with self._lock:
                if not keys:
                    return Err("キーが指定されていません")
                
                # キーコードに変換
                key_codes = []
                modifiers = {
                    'shift': False,
                    'ctrl': False,
                    'alt': False,
                    'win': False
                }
                
                for key in keys:
                    key_lower = key.lower()
                    
                    if key_lower in ['shift', 'ctrl', 'control', 'alt', 'win', 'windows']:
                        if key_lower == 'shift':
                            modifiers['shift'] = True
                        elif key_lower in ['ctrl', 'control']:
                            modifiers['ctrl'] = True
                        elif key_lower == 'alt':
                            modifiers['alt'] = True
                        elif key_lower in ['win', 'windows']:
                            modifiers['win'] = True
                    else:
                        # メインキーコードを取得
                        key_code = self._get_key_code(key)
                        if key_code:
                            key_codes.append(key_code)
                
                # すべてのメインキーに対してコンビネーションを送信
                for key_code in key_codes:
                    result = self._windows_api_service.send_key_input(
                        key_code,
                        modifiers['shift'],
                        modifiers['ctrl'],
                        modifiers['alt'],
                        modifiers['win']
                    )
                    if result.is_failure():
                        return result
                    
                    time.sleep(0.01)  # キー間の短い遅延
                
                return Ok(None)
                
        except Exception as e:
            return Err(f"キーコンビネーション送信エラー: {str(e)}")
    
    def send_special_key(self, key_name: str) -> Result[None, str]:
        """特殊キーを送信"""
        try:
            with self._lock:
                key_code = self._get_special_key_code(key_name)
                if not key_code:
                    return Err(f"未対応の特殊キー: {key_name}")
                
                return self._windows_api_service.send_key_input(key_code)
                
        except Exception as e:
            return Err(f"特殊キー送信エラー: {str(e)}")
    
    def toggle_ime(self, enable: bool) -> Result[None, str]:
        """IMEの有効/無効を切り替え"""
        try:
            with self._lock:
                return self._windows_api_service.toggle_ime(enable)
                
        except Exception as e:
            return Err(f"IME切り替えエラー: {str(e)}")
    
    def is_ime_enabled(self) -> bool:
        """IMEが有効かどうかを判定"""
        return self._windows_api_service.is_ime_enabled()
    
    def start_hotkey_listener(self) -> Result[None, str]:
        """ホットキーリスナーを開始"""
        try:
            with self._lock:
                if self._listening:
                    return Ok(None)  # 既に開始している
                
                self._listening = True
                self._listener_thread = threading.Thread(
                    target=self._hotkey_listener_loop,
                    daemon=True
                )
                self._listener_thread.start()
                
                return Ok(None)
                
        except Exception as e:
            return Err(f"ホットキーリスナー開始エラー: {str(e)}")
    
    def stop_hotkey_listener(self) -> Result[None, str]:
        """ホットキーリスナーを停止"""
        try:
            with self._lock:
                if not self._listening:
                    return Ok(None)
                
                self._listening = False
                
                if self._listener_thread and self._listener_thread.is_alive():
                    self._listener_thread.join(timeout=1.0)
                
                return Ok(None)
                
        except Exception as e:
            return Err(f"ホットキーリスナー停止エラー: {str(e)}")
    
    def register_hotkey(self, hotkey_combination: str, callback: callable) -> Result[None, str]:
        """ホットキーを登録"""
        try:
            with self._lock:
                # ホットキー文字列を正規化
                normalized_hotkey = self._normalize_hotkey(hotkey_combination)
                self._hotkey_listeners[normalized_hotkey] = callback
                
                return Ok(None)
                
        except Exception as e:
            return Err(f"ホットキー登録エラー: {str(e)}")
    
    def unregister_hotkey(self, hotkey_combination: str) -> Result[None, str]:
        """ホットキーの登録を解除"""
        try:
            with self._lock:
                normalized_hotkey = self._normalize_hotkey(hotkey_combination)
                if normalized_hotkey in self._hotkey_listeners:
                    del self._hotkey_listeners[normalized_hotkey]
                
                return Ok(None)
                
        except Exception as e:
            return Err(f"ホットキー登録解除エラー: {str(e)}")
    
    def get_registered_hotkeys(self) -> List[str]:
        """登録済みホットキー一覧を取得"""
        with self._lock:
            return list(self._hotkey_listeners.keys())
    
    # プライベートメソッド
    def _initialize_char_mapping(self) -> Dict[str, int]:
        """文字からVKコードへのマッピングを初期化"""
        mapping = {}
        
        # 英数字
        for i in range(26):
            char = chr(ord('A') + i)
            mapping[char.lower()] = ord(char)
            mapping[char.upper()] = ord(char)
        
        for i in range(10):
            mapping[str(i)] = ord('0') + i
        
        # 記号キー
        symbol_mapping = {
            ' ': WindowsKeys.VK_SPACE,
            '\t': WindowsKeys.VK_TAB,
            '\n': WindowsKeys.VK_RETURN,
            '\r': WindowsKeys.VK_RETURN,
            '\b': WindowsKeys.VK_BACK,
        }
        
        mapping.update(symbol_mapping)
        return mapping
    
    def _get_key_code(self, key: str) -> Optional[int]:
        """キー名からVKコードを取得"""
        if len(key) == 1:
            return self._char_to_vk.get(key)
        
        # 特殊キー名からの変換
        key_lower = key.lower()
        special_keys = {
            'enter': WindowsKeys.VK_RETURN,
            'return': WindowsKeys.VK_RETURN,
            'space': WindowsKeys.VK_SPACE,
            'tab': WindowsKeys.VK_TAB,
            'backspace': WindowsKeys.VK_BACK,
            'delete': 0x2E,  # VK_DELETE
            'escape': WindowsKeys.VK_ESCAPE,
            'esc': WindowsKeys.VK_ESCAPE,
            'left': WindowsKeys.VK_LEFT,
            'right': WindowsKeys.VK_RIGHT,
            'up': WindowsKeys.VK_UP,
            'down': WindowsKeys.VK_DOWN,
            'home': 0x24,  # VK_HOME
            'end': 0x23,   # VK_END
            'pageup': 0x21,  # VK_PRIOR
            'pagedown': 0x22,  # VK_NEXT
            'insert': 0x2D,  # VK_INSERT
        }
        
        # ファンクションキー
        for i in range(1, 13):
            special_keys[f'f{i}'] = WindowsKeys.VK_F1 + (i - 1)
        
        return special_keys.get(key_lower)
    
    def _get_special_key_code(self, key_name: str) -> Optional[int]:
        """特殊キー名からVKコードを取得"""
        return self._get_key_code(key_name)
    
    def _contains_japanese_chars(self, text: str) -> bool:
        """日本語文字が含まれているかチェック"""
        for char in text:
            code_point = ord(char)
            if (0x3040 <= code_point <= 0x309F or    # ひらがな
                0x30A0 <= code_point <= 0x30FF or    # カタカナ
                0x4E00 <= code_point <= 0x9FAF):     # 漢字
                return True
        return False
    
    def _normalize_hotkey(self, hotkey_combination: str) -> str:
        """ホットキー文字列を正規化"""
        # "Ctrl+Alt+F1" -> "ctrl+alt+f1" のように正規化
        parts = [part.strip().lower() for part in hotkey_combination.split('+')]
        
        # 修飾キーの順序を統一
        modifiers = []
        main_keys = []
        
        for part in parts:
            if part in ['ctrl', 'control']:
                modifiers.append('ctrl')
            elif part == 'alt':
                modifiers.append('alt')
            elif part == 'shift':
                modifiers.append('shift')
            elif part in ['win', 'windows']:
                modifiers.append('win')
            else:
                main_keys.append(part)
        
        # 修飾キーを順序付け
        modifier_order = ['ctrl', 'alt', 'shift', 'win']
        sorted_modifiers = [mod for mod in modifier_order if mod in modifiers]
        
        return '+'.join(sorted_modifiers + main_keys)
    
    def _hotkey_listener_loop(self):
        """ホットキーリスナーのメインループ"""
        import ctypes
        from ctypes import wintypes
        
        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            
            # メッセージループ
            msg = wintypes.MSG()
            
            while self._listening:
                # メッセージをチェック
                bRet = user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1)  # PM_REMOVE
                
                if bRet != 0:  # メッセージがある場合
                    if msg.message == 0x0312:  # WM_HOTKEY
                        # ホットキーメッセージの処理
                        self._handle_hotkey_message(msg.wParam, msg.lParam)
                    
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
                
                time.sleep(0.01)  # CPU負荷軽減
                
        except Exception:
            pass  # エラーは無視（バックグラウンド処理のため）
    
    def _handle_hotkey_message(self, hotkey_id: int, lparam: int):
        """ホットキーメッセージを処理"""
        try:
            # lparamから修飾キーとVKコードを抽出
            modifiers = lparam & 0xFFFF
            vk_code = (lparam >> 16) & 0xFFFF
            
            # 修飾キー状態を判定
            ctrl_pressed = bool(modifiers & 0x0002)  # MOD_CONTROL
            alt_pressed = bool(modifiers & 0x0001)   # MOD_ALT
            shift_pressed = bool(modifiers & 0x0004) # MOD_SHIFT
            win_pressed = bool(modifiers & 0x0008)   # MOD_WIN
            
            # ホットキー文字列を構築
            hotkey_parts = []
            if ctrl_pressed:
                hotkey_parts.append('ctrl')
            if alt_pressed:
                hotkey_parts.append('alt')
            if shift_pressed:
                hotkey_parts.append('shift')
            if win_pressed:
                hotkey_parts.append('win')
            
            # VKコードからキー名を取得
            key_name = self._vk_code_to_name(vk_code)
            if key_name:
                hotkey_parts.append(key_name.lower())
            
            hotkey_string = '+'.join(hotkey_parts)
            
            # 登録されたコールバックを呼び出し
            if hotkey_string in self._hotkey_listeners:
                callback = self._hotkey_listeners[hotkey_string]
                try:
                    callback()
                except Exception:
                    pass  # コールバックエラーは無視
                    
        except Exception:
            pass  # エラーは無視
    
    def _vk_code_to_name(self, vk_code: int) -> Optional[str]:
        """VKコードからキー名を取得"""
        vk_mapping = {
            WindowsKeys.VK_RETURN: 'enter',
            WindowsKeys.VK_SPACE: 'space',
            WindowsKeys.VK_TAB: 'tab',
            WindowsKeys.VK_BACK: 'backspace',
            WindowsKeys.VK_ESCAPE: 'escape',
            WindowsKeys.VK_LEFT: 'left',
            WindowsKeys.VK_RIGHT: 'right',
            WindowsKeys.VK_UP: 'up',
            WindowsKeys.VK_DOWN: 'down',
        }
        
        # ファンクションキー
        for i in range(1, 13):
            vk_mapping[WindowsKeys.VK_F1 + (i - 1)] = f'f{i}'
        
        # 英数字
        if 0x30 <= vk_code <= 0x39:  # 0-9
            return str(vk_code - 0x30)
        elif 0x41 <= vk_code <= 0x5A:  # A-Z
            return chr(vk_code).lower()
        
        return vk_mapping.get(vk_code)
    
    def close(self):
        """アダプターを閉じる"""
        # ホットキーリスナーを停止
        self.stop_hotkey_listener()