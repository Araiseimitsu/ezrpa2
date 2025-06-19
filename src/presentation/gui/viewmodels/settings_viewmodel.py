"""
設定画面ViewModel

ショートカットキー設定のビジネスロジックを管理します。
"""

from typing import List, Optional, Callable, Set, Tuple
from src.domain.entities.shortcut_settings import ShortcutSettings, KeyCombination, KeyModifier
from src.presentation.gui.viewmodels.base_viewmodel import BaseViewModel, Command, Signal


class SettingsViewModel(BaseViewModel):
    """設定画面ViewModel"""
    
    # シグナル定義
    settings_changed = Signal()
    custom_key_added = Signal(str)  # 追加されたキーの文字列表現
    custom_key_removed = Signal(int)  # 削除されたインデックス
    error_occurred = Signal(str)  # エラーメッセージ
    
    def __init__(self, shortcut_settings: Optional[ShortcutSettings] = None):
        super().__init__()
        self._settings = shortcut_settings or ShortcutSettings()
        
        # 設定変更コールバック
        self._on_settings_changed_callback: Optional[Callable[[ShortcutSettings], None]] = None
        
        # 一時的なキー入力状態
        self._capture_mode = False
        self._capturing_for = ""  # "custom", "start_stop", "pause_resume", "emergency_stop"
        self._temp_modifiers = set()
        self._temp_key = ""
    
    def set_settings_changed_callback(self, callback: Callable[[ShortcutSettings], None]):
        """設定変更コールバックを設定"""
        self._on_settings_changed_callback = callback
    
    def get_settings(self) -> ShortcutSettings:
        """現在の設定を取得"""
        return self._settings
    
    def update_settings(self, settings: ShortcutSettings):
        """設定を更新"""
        self._settings = settings
        self.settings_changed.emit()
    
    # システムキー除外設定のプロパティ
    def get_exclude_system_keys(self) -> bool:
        return self._settings.exclude_system_keys
    
    def set_exclude_system_keys(self, value: bool):
        if self._settings.exclude_system_keys != value:
            self._settings.exclude_system_keys = value
            self._emit_settings_changed()
    
    def get_exclude_clipboard_keys(self) -> bool:
        return self._settings.exclude_clipboard_keys
    
    def set_exclude_clipboard_keys(self, value: bool):
        if self._settings.exclude_clipboard_keys != value:
            self._settings.exclude_clipboard_keys = value
            self._emit_settings_changed()
    
    def get_exclude_window_keys(self) -> bool:
        return self._settings.exclude_window_keys
    
    def set_exclude_window_keys(self, value: bool):
        if self._settings.exclude_window_keys != value:
            self._settings.exclude_window_keys = value
            self._emit_settings_changed()
    
    def get_exclude_windows_keys(self) -> bool:
        return self._settings.exclude_windows_keys
    
    def set_exclude_windows_keys(self, value: bool):
        if self._settings.exclude_windows_keys != value:
            self._settings.exclude_windows_keys = value
            self._emit_settings_changed()
    
    def get_exclude_app_keys(self) -> bool:
        return self._settings.exclude_app_keys
    
    def set_exclude_app_keys(self, value: bool):
        if self._settings.exclude_app_keys != value:
            self._settings.exclude_app_keys = value
            self._emit_settings_changed()
    
    # カスタム除外キー管理
    def get_custom_excluded_keys(self) -> List[str]:
        """カスタム除外キーの文字列リストを取得"""
        return [str(key) for key in self._settings.custom_excluded_keys]
    
    def add_custom_excluded_key(self, key_combination: KeyCombination) -> bool:
        """カスタム除外キーを追加"""
        try:
            if self._settings.add_custom_excluded_key(key_combination):
                self.custom_key_added.emit(str(key_combination))
                self._emit_settings_changed()
                return True
            else:
                self.error_occurred.emit("同じキー組み合わせが既に存在します")
                return False
        except Exception as e:
            self.error_occurred.emit(f"キー追加エラー: {str(e)}")
            return False
    
    def remove_custom_excluded_key(self, index: int) -> bool:
        """カスタム除外キーを削除"""
        try:
            if self._settings.remove_custom_excluded_key(index):
                self.custom_key_removed.emit(index)
                self._emit_settings_changed()
                return True
            else:
                self.error_occurred.emit("無効なインデックスです")
                return False
        except Exception as e:
            self.error_occurred.emit(f"キー削除エラー: {str(e)}")
            return False
    
    # RPA制御キー設定
    def get_recording_start_stop_key(self) -> str:
        return str(self._settings.recording_start_stop_key)
    
    def set_recording_start_stop_key(self, key_combination: KeyCombination):
        self._settings.recording_start_stop_key = key_combination
        self._emit_settings_changed()
    
    def get_recording_pause_resume_key(self) -> str:
        return str(self._settings.recording_pause_resume_key)
    
    def set_recording_pause_resume_key(self, key_combination: KeyCombination):
        self._settings.recording_pause_resume_key = key_combination
        self._emit_settings_changed()
    
    def get_emergency_stop_key(self) -> str:
        return str(self._settings.emergency_stop_key)
    
    def set_emergency_stop_key(self, key_combination: KeyCombination):
        self._settings.emergency_stop_key = key_combination
        self._emit_settings_changed()
    
    # キー入力キャプチャ機能
    def start_key_capture(self, capture_for: str):
        """キー入力キャプチャを開始"""
        self._capture_mode = True
        self._capturing_for = capture_for
        self._temp_modifiers = set()
        self._temp_key = ""
    
    def stop_key_capture(self):
        """キー入力キャプチャを停止"""
        self._capture_mode = False
        self._capturing_for = ""
        self._temp_modifiers = set()
        self._temp_key = ""
    
    def is_capturing_keys(self) -> bool:
        """キー入力キャプチャ中かどうか"""
        return self._capture_mode
    
    def get_capturing_for(self) -> str:
        """何のためにキャプチャ中か"""
        return self._capturing_for
    
    def handle_key_input(self, modifiers: List[str], key: str) -> bool:
        """キー入力を処理（キャプチャ中のみ）"""
        if not self._capture_mode:
            return False
        
        try:
            # 修飾キーを変換
            modifier_set = set()
            for mod in modifiers:
                if mod.lower() == "ctrl":
                    modifier_set.add(KeyModifier.CTRL)
                elif mod.lower() == "alt":
                    modifier_set.add(KeyModifier.ALT)
                elif mod.lower() == "shift":
                    modifier_set.add(KeyModifier.SHIFT)
                elif mod.lower() == "win":
                    modifier_set.add(KeyModifier.WIN)
            
            # キー組み合わせを作成
            key_combination = KeyCombination(
                modifiers=modifier_set,
                key=key.lower(),
                description=""
            )
            
            # 用途に応じて設定
            if self._capturing_for == "custom":
                key_combination.description = f"カスタム除外キー"
                success = self.add_custom_excluded_key(key_combination)
            elif self._capturing_for == "start_stop":
                key_combination.description = "記録開始/停止"
                self.set_recording_start_stop_key(key_combination)
                success = True
            elif self._capturing_for == "pause_resume":
                key_combination.description = "記録一時停止/再開"
                self.set_recording_pause_resume_key(key_combination)
                success = True
            elif self._capturing_for == "emergency_stop":
                key_combination.description = "緊急停止"
                self.set_emergency_stop_key(key_combination)
                success = True
            else:
                success = False
            
            if success:
                self.stop_key_capture()
            
            return success
            
        except Exception as e:
            self.error_occurred.emit(f"キー入力処理エラー: {str(e)}")
            return False
    
    # デフォルト設定復元
    def restore_default_settings(self):
        """デフォルト設定に復元"""
        try:
            self._settings = ShortcutSettings()
            self.settings_changed.emit()
            self._emit_settings_changed()
        except Exception as e:
            self.error_occurred.emit(f"デフォルト復元エラー: {str(e)}")
    
    # 設定のインポート/エクスポート
    def export_settings_dict(self) -> dict:
        """設定を辞書形式でエクスポート"""
        return self._settings.to_dict()
    
    def import_settings_dict(self, settings_dict: dict) -> bool:
        """辞書形式から設定をインポート"""
        try:
            imported_settings = ShortcutSettings.from_dict(settings_dict)
            self.update_settings(imported_settings)
            return True
        except Exception as e:
            self.error_occurred.emit(f"設定インポートエラー: {str(e)}")
            return False
    
    # カスタムショートカットコマンド管理
    def get_custom_shortcut_commands(self) -> List["CustomShortcutCommand"]:
        """カスタムショートカットコマンドを取得"""
        return self._settings.get_custom_shortcut_commands()
    
    def add_custom_shortcut_command(self, command: "CustomShortcutCommand") -> bool:
        """カスタムショートカットコマンドを追加"""
        try:
            if self._settings.add_custom_shortcut_command(command):
                self._emit_settings_changed()
                return True
            else:
                self.error_occurred.emit("キー組み合わせが重複しているか、無効な設定です")
                return False
        except Exception as e:
            self.error_occurred.emit(f"コマンド追加エラー: {str(e)}")
            return False
    
    def update_custom_shortcut_command(self, command: "CustomShortcutCommand") -> bool:
        """カスタムショートカットコマンドを更新"""
        try:
            if self._settings.update_custom_shortcut_command(command):
                self._emit_settings_changed()
                return True
            else:
                self.error_occurred.emit("コマンドの更新に失敗しました")
                return False
        except Exception as e:
            self.error_occurred.emit(f"コマンド更新エラー: {str(e)}")
            return False
    
    def remove_custom_shortcut_command(self, command_id: str) -> bool:
        """カスタムショートカットコマンドを削除"""
        try:
            if self._settings.remove_custom_shortcut_command(command_id):
                self._emit_settings_changed()
                return True
            else:
                self.error_occurred.emit("コマンドの削除に失敗しました")
                return False
        except Exception as e:
            self.error_occurred.emit(f"コマンド削除エラー: {str(e)}")
            return False
    
    def validate_custom_command_key(self, modifiers: Set[KeyModifier], key: str, exclude_command_id: str = "") -> Tuple[bool, str]:
        """カスタムコマンドのキー組み合わせを検証"""
        return self._settings.has_key_conflict(modifiers, key, exclude_command_id)
    
    def execute_custom_command(self, command_id: str) -> bool:
        """カスタムコマンドを実行"""
        try:
            commands = self.get_custom_shortcut_commands()
            for command in commands:
                if command.id == command_id:
                    return command.execute()
            return False
        except Exception as e:
            self.error_occurred.emit(f"コマンド実行エラー: {str(e)}")
            return False
    
    # 設定の検証
    def validate_settings(self) -> List[str]:
        """設定の妥当性をチェック"""
        warnings = []
        
        # RPA制御キーの重複チェック
        control_keys = [
            self._settings.recording_start_stop_key,
            self._settings.recording_pause_resume_key,
            self._settings.emergency_stop_key
        ]
        
        for i, key1 in enumerate(control_keys):
            for j, key2 in enumerate(control_keys[i+1:], i+1):
                if key1.modifiers == key2.modifiers and key1.key == key2.key:
                    warnings.append(f"RPA制御キーに重複があります: {key1}")
        
        # カスタム除外キーの重複チェック
        seen_keys = set()
        for key in self._settings.custom_excluded_keys:
            key_signature = (frozenset(key.modifiers), key.key)
            if key_signature in seen_keys:
                warnings.append(f"カスタム除外キーに重複があります: {key}")
            seen_keys.add(key_signature)
        
        return warnings
    
    def _emit_settings_changed(self):
        """設定変更を通知"""
        self.settings_changed.emit()
        if self._on_settings_changed_callback:
            self._on_settings_changed_callback(self._settings)
    
    # 抽象メソッドの実装
    async def initialize_async(self):
        """非同期初期化"""
        # 設定画面では特別な非同期初期化は不要
        pass
    
    async def _refresh_async(self, parameter=None):
        """リフレッシュ処理"""
        # 設定画面では特別なリフレッシュ処理は不要
        # 必要に応じて設定ファイルから再読み込みなどを実装
        pass