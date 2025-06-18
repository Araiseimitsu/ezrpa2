"""
Settings リポジトリインターフェース

アプリケーション設定の永続化を抽象化するリポジトリパターンの実装。
Windows環境での設定管理（レジストリ・ファイル）を考慮した設計です。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from datetime import datetime

from ..value_objects import ValidationResult
from ...core.result import Result, ErrorInfo


SettingValue = Union[str, int, float, bool, List[Any], Dict[str, Any]]


class ISettingsRepository(ABC):
    """
    Settings リポジトリインターフェース
    
    アプリケーション設定の永続化操作を定義する抽象基底クラス。
    Windows環境でのレジストリとファイルベース設定を統合管理します。
    """
    
    @abstractmethod
    async def get(self, key: str, default: Optional[SettingValue] = None) -> Result[SettingValue, ErrorInfo]:
        """
        設定値を取得
        
        Args:
            key: 設定キー
            default: デフォルト値
            
        Returns:
            設定値またはエラー情報
        """
        pass
    
    @abstractmethod
    async def set(self, key: str, value: SettingValue) -> Result[bool, ErrorInfo]:
        """
        設定値を保存
        
        Args:
            key: 設定キー
            value: 設定値
            
        Returns:
            保存成功フラグまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> Result[bool, ErrorInfo]:
        """
        設定を削除
        
        Args:
            key: 削除する設定キー
            
        Returns:
            削除成功フラグまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> Result[bool, ErrorInfo]:
        """
        設定の存在確認
        
        Args:
            key: 確認する設定キー
            
        Returns:
            存在フラグまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def get_all(self) -> Result[Dict[str, SettingValue], ErrorInfo]:
        """
        全設定を取得
        
        Returns:
            設定辞書またはエラー情報
        """
        pass
    
    @abstractmethod
    async def get_by_prefix(self, prefix: str) -> Result[Dict[str, SettingValue], ErrorInfo]:
        """
        プレフィックスで設定を取得
        
        Args:
            prefix: キープレフィックス
            
        Returns:
            該当設定辞書またはエラー情報
        """
        pass
    
    @abstractmethod
    async def set_multiple(self, settings: Dict[str, SettingValue]) -> Result[bool, ErrorInfo]:
        """
        複数設定を一括保存
        
        Args:
            settings: 設定辞書
            
        Returns:
            保存成功フラグまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def delete_by_prefix(self, prefix: str) -> Result[int, ErrorInfo]:
        """
        プレフィックスで設定を一括削除
        
        Args:
            prefix: キープレフィックス
            
        Returns:
            削除された設定数またはエラー情報
        """
        pass
    
    @abstractmethod
    async def clear_all(self) -> Result[bool, ErrorInfo]:
        """
        全設定をクリア
        
        Returns:
            クリア成功フラグまたはエラー情報
        """
        pass
    
    # バックアップ・復元機能
    @abstractmethod
    async def backup_to_file(self, file_path: Path) -> Result[bool, ErrorInfo]:
        """
        設定をファイルにバックアップ
        
        Args:
            file_path: バックアップファイルパス
            
        Returns:
            バックアップ成功フラグまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def restore_from_file(self, file_path: Path, 
                               overwrite: bool = False) -> Result[int, ErrorInfo]:
        """
        ファイルから設定を復元
        
        Args:
            file_path: 復元ファイルパス
            overwrite: 既存設定の上書きフラグ
            
        Returns:
            復元された設定数またはエラー情報
        """
        pass
    
    # Windows環境固有機能
    @abstractmethod
    async def sync_with_registry(self, key_prefix: Optional[str] = None) -> Result[bool, ErrorInfo]:
        """
        Windowsレジストリと同期
        
        Args:
            key_prefix: 同期対象キープレフィックス（None=全て）
            
        Returns:
            同期成功フラグまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def export_to_registry(self, registry_path: str, 
                                key_prefix: Optional[str] = None) -> Result[bool, ErrorInfo]:
        """
        Windowsレジストリにエクスポート
        
        Args:
            registry_path: レジストリパス
            key_prefix: エクスポート対象キープレフィックス
            
        Returns:
            エクスポート成功フラグまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def import_from_registry(self, registry_path: str) -> Result[int, ErrorInfo]:
        """
        Windowsレジストリからインポート
        
        Args:
            registry_path: レジストリパス
            
        Returns:
            インポートされた設定数またはエラー情報
        """
        pass
    
    # メタデータ・監査機能
    @abstractmethod
    async def get_metadata(self, key: str) -> Result[Dict[str, Any], ErrorInfo]:
        """
        設定のメタデータを取得
        
        Args:
            key: 設定キー
            
        Returns:
            メタデータ辞書またはエラー情報
        """
        pass
    
    @abstractmethod
    async def get_change_history(self, key: str, 
                               limit: Optional[int] = None) -> Result[List[Dict[str, Any]], ErrorInfo]:
        """
        設定変更履歴を取得
        
        Args:
            key: 設定キー
            limit: 取得件数制限
            
        Returns:
            変更履歴リストまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def validate_settings(self) -> Result[ValidationResult, ErrorInfo]:
        """
        設定の整合性検証
        
        Returns:
            検証結果またはエラー情報
        """
        pass


class ISettingsEventHandler(ABC):
    """
    Settings イベントハンドラーインターフェース
    
    設定変更に関するイベント処理を定義。
    """
    
    @abstractmethod
    async def on_setting_changed(self, key: str, old_value: Optional[SettingValue], 
                                new_value: SettingValue) -> None:
        """設定値変更時"""
        pass
    
    @abstractmethod
    async def on_setting_deleted(self, key: str, old_value: SettingValue) -> None:
        """設定削除時"""
        pass
    
    @abstractmethod
    async def on_settings_imported(self, count: int, source: str) -> None:
        """設定インポート時"""
        pass
    
    @abstractmethod
    async def on_settings_exported(self, count: int, destination: str) -> None:
        """設定エクスポート時"""
        pass


class SettingsCategory:
    """設定カテゴリ定数"""
    
    # アプリケーション基本設定
    APPLICATION = "application"
    
    # UI設定
    UI = "ui"
    
    # 記録・再生設定
    RECORDING = "recording"
    PLAYBACK = "playback"
    
    # スケジュール設定
    SCHEDULER = "scheduler"
    
    # セキュリティ設定
    SECURITY = "security"
    
    # ログ設定
    LOGGING = "logging"
    
    # Windows固有設定
    WINDOWS = "windows"
    
    # 開発・デバッグ設定
    DEBUG = "debug"


class SettingsKeys:
    """標準設定キー定数"""
    
    # アプリケーション設定
    APP_VERSION = "application.version"
    APP_LANGUAGE = "application.language"
    APP_THEME = "application.theme"
    APP_AUTO_START = "application.auto_start"
    APP_CHECK_UPDATES = "application.check_updates"
    
    # UI設定
    UI_WINDOW_WIDTH = "ui.window.width"
    UI_WINDOW_HEIGHT = "ui.window.height"
    UI_WINDOW_X = "ui.window.x"
    UI_WINDOW_Y = "ui.window.y"
    UI_WINDOW_MAXIMIZED = "ui.window.maximized"
    UI_FONT_SIZE = "ui.font.size"
    UI_FONT_FAMILY = "ui.font.family"
    
    # 記録設定
    RECORDING_AUTO_SAVE = "recording.auto_save"
    RECORDING_SAVE_SCREENSHOTS = "recording.save_screenshots"
    RECORDING_MAX_ACTIONS = "recording.max_actions"
    RECORDING_HOTKEY_START = "recording.hotkey.start"
    RECORDING_HOTKEY_STOP = "recording.hotkey.stop"
    
    # 再生設定
    PLAYBACK_DEFAULT_SPEED = "playback.default_speed"
    PLAYBACK_DEFAULT_DELAY = "playback.default_delay"
    PLAYBACK_STOP_ON_ERROR = "playback.stop_on_error"
    PLAYBACK_TAKE_SCREENSHOTS = "playback.take_screenshots"
    
    # スケジュール設定
    SCHEDULER_ENABLED = "scheduler.enabled"
    SCHEDULER_CHECK_INTERVAL = "scheduler.check_interval"
    SCHEDULER_MAX_PARALLEL = "scheduler.max_parallel"
    
    # セキュリティ設定
    SECURITY_ENCRYPTION_ENABLED = "security.encryption.enabled"
    SECURITY_AUTO_LOCK_MINUTES = "security.auto_lock.minutes"
    SECURITY_REQUIRE_PASSWORD = "security.require_password"
    
    # ログ設定
    LOG_LEVEL = "logging.level"
    LOG_MAX_SIZE_MB = "logging.max_size_mb"
    LOG_MAX_FILES = "logging.max_files"
    LOG_DIRECTORY = "logging.directory"
    
    # Windows設定
    WINDOWS_ADMIN_MODE = "windows.admin_mode"
    WINDOWS_TASK_SCHEDULER = "windows.task_scheduler"
    WINDOWS_REGISTRY_BACKUP = "windows.registry_backup"
    
    # 開発設定
    DEBUG_MODE = "debug.mode"
    DEBUG_VERBOSE_LOGGING = "debug.verbose_logging"
    DEBUG_SAVE_TEMP_FILES = "debug.save_temp_files"


class SettingsDefaults:
    """デフォルト設定値"""
    
    DEFAULT_VALUES: Dict[str, SettingValue] = {
        # アプリケーション設定
        SettingsKeys.APP_LANGUAGE: "ja-JP",
        SettingsKeys.APP_THEME: "system",
        SettingsKeys.APP_AUTO_START: False,
        SettingsKeys.APP_CHECK_UPDATES: True,
        
        # UI設定
        SettingsKeys.UI_WINDOW_WIDTH: 1200,
        SettingsKeys.UI_WINDOW_HEIGHT: 800,
        SettingsKeys.UI_WINDOW_MAXIMIZED: False,
        SettingsKeys.UI_FONT_SIZE: 9,
        SettingsKeys.UI_FONT_FAMILY: "Yu Gothic UI",
        
        # 記録設定
        SettingsKeys.RECORDING_AUTO_SAVE: True,
        SettingsKeys.RECORDING_SAVE_SCREENSHOTS: False,
        SettingsKeys.RECORDING_MAX_ACTIONS: 10000,
        SettingsKeys.RECORDING_HOTKEY_START: "Ctrl+Shift+F1",
        SettingsKeys.RECORDING_HOTKEY_STOP: "Ctrl+Shift+F2",
        
        # 再生設定
        SettingsKeys.PLAYBACK_DEFAULT_SPEED: 1.0,
        SettingsKeys.PLAYBACK_DEFAULT_DELAY: 500,
        SettingsKeys.PLAYBACK_STOP_ON_ERROR: True,
        SettingsKeys.PLAYBACK_TAKE_SCREENSHOTS: False,
        
        # スケジュール設定
        SettingsKeys.SCHEDULER_ENABLED: True,
        SettingsKeys.SCHEDULER_CHECK_INTERVAL: 60,
        SettingsKeys.SCHEDULER_MAX_PARALLEL: 3,
        
        # セキュリティ設定
        SettingsKeys.SECURITY_ENCRYPTION_ENABLED: True,
        SettingsKeys.SECURITY_AUTO_LOCK_MINUTES: 30,
        SettingsKeys.SECURITY_REQUIRE_PASSWORD: False,
        
        # ログ設定
        SettingsKeys.LOG_LEVEL: "INFO",
        SettingsKeys.LOG_MAX_SIZE_MB: 10,
        SettingsKeys.LOG_MAX_FILES: 5,
        
        # Windows設定
        SettingsKeys.WINDOWS_ADMIN_MODE: False,
        SettingsKeys.WINDOWS_TASK_SCHEDULER: True,
        SettingsKeys.WINDOWS_REGISTRY_BACKUP: True,
        
        # 開発設定
        SettingsKeys.DEBUG_MODE: False,
        SettingsKeys.DEBUG_VERBOSE_LOGGING: False,
        SettingsKeys.DEBUG_SAVE_TEMP_FILES: False,
    }


class SettingsValidator:
    """設定値バリデーター"""
    
    @staticmethod
    def validate_key(key: str) -> bool:
        """設定キーの妥当性チェック"""
        if not key or len(key.strip()) == 0:
            return False
        
        # キー形式チェック（カテゴリ.サブカテゴリ.名前）
        import re
        pattern = r'^[a-z_]+(\.[a-z_]+)*$'
        return bool(re.match(pattern, key))
    
    @staticmethod
    def validate_value(key: str, value: SettingValue) -> ValidationResult:
        """設定値の妥当性チェック"""
        errors = []
        warnings = []
        
        # キー固有のバリデーション
        if key == SettingsKeys.UI_WINDOW_WIDTH:
            if not isinstance(value, int) or value < 400 or value > 10000:
                errors.append("ウィンドウ幅は400-10000の範囲で指定してください")
        
        elif key == SettingsKeys.UI_WINDOW_HEIGHT:
            if not isinstance(value, int) or value < 300 or value > 10000:
                errors.append("ウィンドウ高さは300-10000の範囲で指定してください")
        
        elif key == SettingsKeys.PLAYBACK_DEFAULT_SPEED:
            if not isinstance(value, (int, float)) or value <= 0 or value > 10:
                errors.append("再生速度は0より大きく10以下で指定してください")
        
        elif key == SettingsKeys.LOG_LEVEL:
            if value not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
                errors.append("ログレベルはDEBUG/INFO/WARNING/ERRORのいずれかを指定してください")
        
        elif key == SettingsKeys.RECORDING_MAX_ACTIONS:
            if not isinstance(value, int) or value < 1 or value > 100000:
                errors.append("最大アクション数は1-100000の範囲で指定してください")
        
        # 一般的なバリデーション
        if isinstance(value, str) and len(value) > 1000:
            warnings.append("文字列値が長すぎます（1000文字以内推奨）")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    @staticmethod
    def validate_settings_dict(settings: Dict[str, SettingValue]) -> ValidationResult:
        """設定辞書の一括バリデーション"""
        all_errors = []
        all_warnings = []
        
        for key, value in settings.items():
            if not SettingsValidator.validate_key(key):
                all_errors.append(f"無効な設定キー: {key}")
                continue
            
            value_validation = SettingsValidator.validate_value(key, value)
            all_errors.extend([f"{key}: {error}" for error in value_validation.errors])
            all_warnings.extend([f"{key}: {warning}" for warning in value_validation.warnings])
        
        return ValidationResult(
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings
        )