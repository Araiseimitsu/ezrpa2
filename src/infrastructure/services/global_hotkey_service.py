"""
グローバルホットキー監視・実行サービス

カスタムショートカットコマンドの監視と実行を管理します。
"""

import threading
import time
from typing import Dict, Optional, Callable, Set
from dataclasses import dataclass
import logging

try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False

from src.domain.entities.shortcut_settings import ShortcutSettings, KeyModifier
from src.domain.entities.custom_shortcut_command import CustomShortcutCommand
from src.core.event_bus import EventBus
from src.core.result import Result, ResultOf, Ok, Err


@dataclass
class HotkeyInfo:
    """ホットキー情報"""
    key_combination: str
    command: CustomShortcutCommand
    registered: bool = False


class GlobalHotkeyService:
    """グローバルホットキー監視・実行サービス"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)
        
        # ホットキー管理
        self.hotkeys: Dict[str, HotkeyInfo] = {}
        self.settings: Optional[ShortcutSettings] = None
        
        # サービス状態
        self.is_running = False
        self.is_enabled = True
        
        # 監視スレッド
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # keyboard ライブラリの状態チェック
        self.keyboard_available = HAS_KEYBOARD
        
        if not self.keyboard_available:
            self.logger.warning("keyboard ライブラリが利用できません。グローバルホットキー機能は無効です。")
    
    def start(self) -> ResultOf(None, str):
        """サービス開始"""
        try:
            if self.is_running:
                return Ok(None)
            
            if not self.keyboard_available:
                return Err("keyboard ライブラリが利用できません")
            
            self.is_running = True
            self._stop_event.clear()
            
            # 監視スレッド開始
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop,
                daemon=True,
                name="GlobalHotkeyMonitor"
            )
            self._monitor_thread.start()
            
            self.logger.info("グローバルホットキーサービスを開始しました")
            
            # イベント通知
            self.event_bus.emit("hotkey_service_started", {})
            
            return Ok(None)
            
        except Exception as e:
            self.logger.error(f"グローバルホットキーサービス開始エラー: {e}")
            return Err(f"サービス開始エラー: {e}")
    
    def stop(self) -> ResultOf(None, str):
        """サービス停止"""
        try:
            if not self.is_running:
                return Ok(None)
            
            self.is_running = False
            self._stop_event.set()
            
            # 全ホットキーの解除
            self._unregister_all_hotkeys()
            
            # 監視スレッド終了待機
            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=5.0)
            
            self.logger.info("グローバルホットキーサービスを停止しました")
            
            # イベント通知
            self.event_bus.emit("hotkey_service_stopped", {})
            
            return Ok(None)
            
        except Exception as e:
            self.logger.error(f"グローバルホットキーサービス停止エラー: {e}")
            return Err(f"サービス停止エラー: {e}")
    
    def update_settings(self, settings: ShortcutSettings) -> ResultOf(None, str):
        """設定更新"""
        try:
            self.settings = settings
            
            if self.is_running:
                # 現在のホットキーを解除
                self._unregister_all_hotkeys()
                
                # 新しい設定でホットキーを登録
                self._register_hotkeys_from_settings()
            
            self.logger.debug("ホットキー設定を更新しました")
            return Ok(None)
            
        except Exception as e:
            self.logger.error(f"設定更新エラー: {e}")
            return Err(f"設定更新エラー: {e}")
    
    def enable(self) -> ResultOf(None, str):
        """ホットキー監視を有効化"""
        try:
            if self.is_enabled:
                return Ok(None)
            
            self.is_enabled = True
            
            if self.is_running and self.settings:
                self._register_hotkeys_from_settings()
            
            self.logger.info("ホットキー監視を有効化しました")
            return Ok(None)
            
        except Exception as e:
            self.logger.error(f"ホットキー有効化エラー: {e}")
            return Err(f"有効化エラー: {e}")
    
    def disable(self) -> ResultOf(None, str):
        """ホットキー監視を無効化"""
        try:
            if not self.is_enabled:
                return Ok(None)
            
            self.is_enabled = False
            self._unregister_all_hotkeys()
            
            self.logger.info("ホットキー監視を無効化しました")
            return Ok(None)
            
        except Exception as e:
            self.logger.error(f"ホットキー無効化エラー: {e}")
            return Err(f"無効化エラー: {e}")
    
    def _monitor_loop(self):
        """監視ループ"""
        try:
            # 設定からホットキーを登録
            if self.settings:
                self._register_hotkeys_from_settings()
            
            self.logger.info("グローバルホットキー監視ループを開始しました")
            
            # 監視ループ - keyboard ライブラリはイベントドリブンなので、単純に待機
            while not self._stop_event.is_set():
                try:
                    # 0.1秒間隔でストップイベントをチェック
                    if self._stop_event.wait(timeout=0.1):
                        break
                        
                except Exception as e:
                    self.logger.error(f"キーボード監視エラー: {e}")
                    time.sleep(1)  # エラー時は少し待機
                    
        except Exception as e:
            self.logger.error(f"監視ループエラー: {e}")
        finally:
            self.logger.info("グローバルホットキー監視ループを終了しました")
            self._unregister_all_hotkeys()
    
    def _register_hotkeys_from_settings(self):
        """設定からホットキーを登録"""
        if not self.settings or not self.is_enabled or not self.keyboard_available:
            return
        
        try:
            commands = self.settings.get_custom_shortcut_commands()
            
            for command in commands:
                if command.enabled and command.key_combination:
                    self._register_hotkey(command)
                    
        except Exception as e:
            self.logger.error(f"ホットキー登録エラー: {e}")
    
    def _register_hotkey(self, command: CustomShortcutCommand):
        """個別ホットキー登録"""
        try:
            if not self.keyboard_available:
                return
            
            # キー組み合わせを keyboard ライブラリ形式に変換
            key_combo = self._convert_key_combination(command.key_combination)
            if not key_combo:
                return
            
            # コールバック関数を作成
            callback = lambda: self._execute_command(command)
            
            # ホットキー登録
            keyboard.add_hotkey(key_combo, callback, suppress=True)
            
            # 管理リストに追加
            self.hotkeys[command.id] = HotkeyInfo(
                key_combination=key_combo,
                command=command,
                registered=True
            )
            
            self.logger.debug(f"ホットキー登録: {command.name} ({key_combo})")
            
        except Exception as e:
            self.logger.error(f"ホットキー登録エラー [{command.name}]: {e}")
    
    def _unregister_all_hotkeys(self):
        """全ホットキー解除"""
        if not self.keyboard_available:
            return
        
        try:
            # keyboard ライブラリの全ホットキーを解除
            keyboard.unhook_all_hotkeys()
            
            # 管理リストをクリア
            for hotkey_info in self.hotkeys.values():
                hotkey_info.registered = False
            
            self.hotkeys.clear()
            
            self.logger.debug("全ホットキーを解除しました")
            
        except Exception as e:
            self.logger.error(f"ホットキー解除エラー: {e}")
    
    def _convert_key_combination(self, key_combination) -> Optional[str]:
        """キー組み合わせを keyboard ライブラリ形式に変換"""
        try:
            if not key_combination or not key_combination.key:
                return None
            
            parts = []
            
            # 修飾キーを追加
            if KeyModifier.CTRL in key_combination.modifiers:
                parts.append("ctrl")
            if KeyModifier.ALT in key_combination.modifiers:
                parts.append("alt")
            if KeyModifier.SHIFT in key_combination.modifiers:
                parts.append("shift")
            if KeyModifier.WIN in key_combination.modifiers:
                parts.append("windows")
            
            # 通常キーを追加
            key = key_combination.key.lower()
            
            # 特殊キーの変換マップ
            key_map = {
                "space": "space",
                "enter": "enter",
                "tab": "tab",
                "backspace": "backspace",
                "delete": "delete",
                "esc": "escape",
                "escape": "escape",
                "insert": "insert",
                "home": "home",
                "end": "end",
                "page_up": "page up",
                "page_down": "page down",
                "up": "up",
                "down": "down",
                "left": "left",
                "right": "right"
            }
            
            # ファンクションキーの処理
            if key.startswith("f") and key[1:].isdigit():
                mapped_key = key  # f1, f2, etc.
            else:
                mapped_key = key_map.get(key, key)
            
            parts.append(mapped_key)
            
            return "+".join(parts)
            
        except Exception as e:
            self.logger.error(f"キー組み合わせ変換エラー: {e}")
            return None
    
    def _execute_command(self, command: CustomShortcutCommand):
        """コマンド実行"""
        try:
            if not command.enabled:
                return
            
            self.logger.debug(f"カスタムコマンド実行: {command.name}")
            
            # イベント通知（実行前）
            self.event_bus.emit("custom_command_executing", {
                "command_id": command.id,
                "command_name": command.name
            })
            
            # コマンド実行
            success = command.execute()
            
            # イベント通知（実行後）
            self.event_bus.emit("custom_command_executed", {
                "command_id": command.id,
                "command_name": command.name,
                "success": success
            })
            
            if success:
                self.logger.info(f"カスタムコマンド実行成功: {command.name}")
            else:
                self.logger.warning(f"カスタムコマンド実行失敗: {command.name}")
                
        except Exception as e:
            self.logger.error(f"カスタムコマンド実行エラー [{command.name}]: {e}")
            
            # エラー通知
            self.event_bus.emit("custom_command_error", {
                "command_id": command.id,
                "command_name": command.name,
                "error": str(e)
            })
    
    def get_status(self) -> Dict[str, any]:
        """サービス状態取得"""
        return {
            "running": self.is_running,
            "enabled": self.is_enabled,
            "keyboard_available": self.keyboard_available,
            "registered_hotkeys": len(self.hotkeys),
            "hotkey_details": [
                {
                    "command_name": info.command.name,
                    "key_combination": info.key_combination,
                    "registered": info.registered
                }
                for info in self.hotkeys.values()
            ]
        }
    
    def execute_command_by_id(self, command_id: str) -> ResultOf(None, str):
        """IDでコマンドを手動実行"""
        try:
            hotkey_info = self.hotkeys.get(command_id)
            if hotkey_info:
                self._execute_command(hotkey_info.command)
                return Ok(None)
            else:
                return Err(f"コマンドが見つかりません: {command_id}")
                
        except Exception as e:
            self.logger.error(f"手動コマンド実行エラー: {e}")
            return Err(f"実行エラー: {e}")


# Windows 専用実装（オプション）
class WindowsGlobalHotkeyService(GlobalHotkeyService):
    """Windows 専用グローバルホットキーサービス"""
    
    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus)
        
        # Windows API を使用する場合の追加実装
        # 現在は基本実装を継承
        pass


def create_global_hotkey_service(event_bus: EventBus) -> GlobalHotkeyService:
    """プラットフォーム固有のグローバルホットキーサービスを作成"""
    import platform
    
    if platform.system() == "Windows":
        return WindowsGlobalHotkeyService(event_bus)
    else:
        return GlobalHotkeyService(event_bus)