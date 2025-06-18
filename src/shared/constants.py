"""
共有定数定義 - Windows環境でのRPAアプリケーション定数

Windows環境でのファイルパス、レジストリキー、API定数等を定義します。
"""

import os
from pathlib import Path
from enum import Enum, IntEnum


class WindowsKeys:
    """Windows仮想キーコード定数"""
    
    # 特殊キー
    VK_BACK = 0x08       # Backspace
    VK_TAB = 0x09        # Tab
    VK_RETURN = 0x0D     # Enter
    VK_SHIFT = 0x10      # Shift
    VK_CONTROL = 0x11    # Ctrl
    VK_MENU = 0x12       # Alt
    VK_ESCAPE = 0x1B     # Esc
    VK_SPACE = 0x20      # Space
    
    # 方向キー
    VK_LEFT = 0x25       # 左矢印
    VK_UP = 0x26         # 上矢印
    VK_RIGHT = 0x27      # 右矢印
    VK_DOWN = 0x28       # 下矢印
    
    # ファンクションキー
    VK_F1 = 0x70
    VK_F2 = 0x71
    VK_F3 = 0x72
    VK_F4 = 0x73
    VK_F5 = 0x74
    VK_F6 = 0x75
    VK_F7 = 0x76
    VK_F8 = 0x77
    VK_F9 = 0x78
    VK_F10 = 0x79
    VK_F11 = 0x7A
    VK_F12 = 0x7B
    
    # Windows固有キー
    VK_LWIN = 0x5B       # 左Windowsキー
    VK_RWIN = 0x5C       # 右Windowsキー
    VK_APPS = 0x5D       # アプリケーションキー
    
    # IME関連キー（日本語環境）
    VK_CONVERT = 0x1C     # 変換キー
    VK_NONCONVERT = 0x1D  # 無変換キー
    VK_KANJI = 0x19       # 漢字キー
    VK_KANA = 0x15        # かなキー


class MouseButton(IntEnum):
    """マウスボタン定数"""
    LEFT = 1
    RIGHT = 2
    MIDDLE = 3
    X1 = 4        # 追加ボタン1
    X2 = 5        # 追加ボタン2


class WindowsMessages:
    """Windows メッセージ定数"""
    
    # キーボードメッセージ
    WM_KEYDOWN = 0x0100
    WM_KEYUP = 0x0101
    WM_CHAR = 0x0102
    WM_SYSKEYDOWN = 0x0104
    WM_SYSKEYUP = 0x0105
    
    # マウスメッセージ
    WM_LBUTTONDOWN = 0x0201
    WM_LBUTTONUP = 0x0202
    WM_RBUTTONDOWN = 0x0204
    WM_RBUTTONUP = 0x0205
    WM_MBUTTONDOWN = 0x0207
    WM_MBUTTONUP = 0x0208
    WM_MOUSEMOVE = 0x0200
    WM_MOUSEWHEEL = 0x020A


class ApplicationConstants:
    """アプリケーション定数"""
    
    # バージョン情報
    VERSION = "2.0.0"
    APPLICATION_NAME = "EZRPA"
    VENDOR_NAME = "EZRPA Development Team"
    
    # ファイル拡張子
    RECORDING_FILE_EXTENSION = ".ezrpa"
    SETTINGS_FILE_EXTENSION = ".json"
    LOG_FILE_EXTENSION = ".log"
    
    # デフォルトタイムアウト（ミリ秒）
    DEFAULT_ACTION_TIMEOUT = 5000
    DEFAULT_PLAYBACK_DELAY = 100
    DEFAULT_WAIT_TIMEOUT = 30000
    
    # DPI設定
    DEFAULT_DPI = 96
    HIGH_DPI_THRESHOLD = 120


class WindowsPaths:
    """Windows環境でのパス定数"""
    
    @staticmethod
    def get_app_data_dir() -> Path:
        """アプリケーションデータディレクトリを取得"""
        app_data = os.environ.get('APPDATA')
        if app_data:
            return Path(app_data) / ApplicationConstants.APPLICATION_NAME
        else:
            return Path.home() / f".{ApplicationConstants.APPLICATION_NAME.lower()}"
    
    @staticmethod
    def get_documents_dir() -> Path:
        """ドキュメントディレクトリを取得"""
        return Path.home() / "Documents" / ApplicationConstants.APPLICATION_NAME
    
    @staticmethod
    def get_temp_dir() -> Path:
        """一時ディレクトリを取得"""
        return Path(os.environ.get('TEMP', 'C:\\temp')) / ApplicationConstants.APPLICATION_NAME
    
    @staticmethod
    def get_logs_dir() -> Path:
        """ログディレクトリを取得"""
        return WindowsPaths.get_app_data_dir() / "logs"
    
    @staticmethod
    def get_recordings_dir() -> Path:
        """記録ファイルディレクトリを取得"""
        return WindowsPaths.get_documents_dir() / "recordings"
    
    @staticmethod
    def get_backups_dir() -> Path:
        """バックアップディレクトリを取得"""
        return WindowsPaths.get_app_data_dir() / "backups"


class RegistryPaths:
    """Windowsレジストリパス定数"""
    
    # アプリケーション設定
    APP_SETTINGS_KEY = r"HKEY_CURRENT_USER\Software\EZRPA"
    
    # 自動起動設定
    STARTUP_KEY = r"HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run"
    
    # ファイル関連付け
    FILE_ASSOCIATION_KEY = r"HKEY_CURRENT_USER\Software\Classes"


class SecurityConstants:
    """セキュリティ関連定数"""
    
    # 暗号化設定
    AES_KEY_SIZE = 256
    AES_BLOCK_SIZE = 16
    SALT_SIZE = 32
    IV_SIZE = 16
    
    # ハッシュ設定
    HASH_ALGORITHM = "SHA-256"
    PBKDF2_ITERATIONS = 100000
    
    # セッション設定
    SESSION_TIMEOUT_MINUTES = 30
    MAX_LOGIN_ATTEMPTS = 5


class UIConstants:
    """UI関連定数"""
    
    # ウィンドウサイズ
    MIN_WINDOW_WIDTH = 800
    MIN_WINDOW_HEIGHT = 600
    DEFAULT_WINDOW_WIDTH = 1200
    DEFAULT_WINDOW_HEIGHT = 800
    
    # フォント設定
    DEFAULT_FONT_FAMILY = "Yu Gothic UI"  # Windows 10/11標準
    DEFAULT_FONT_SIZE = 9
    MONOSPACE_FONT_FAMILY = "Consolas"
    
    # 色設定（Windows 11準拠）
    PRIMARY_COLOR = "#0078D4"
    SECONDARY_COLOR = "#106EBE"
    SUCCESS_COLOR = "#107C10"
    WARNING_COLOR = "#FF8C00"
    ERROR_COLOR = "#D13438"
    
    # アイコンサイズ
    SMALL_ICON_SIZE = 16
    MEDIUM_ICON_SIZE = 24
    LARGE_ICON_SIZE = 32


class NetworkConstants:
    """ネットワーク関連定数"""
    
    # タイムアウト設定
    HTTP_TIMEOUT = 30
    CONNECTION_TIMEOUT = 10
    READ_TIMEOUT = 30
    
    # リトライ設定
    MAX_RETRY_ATTEMPTS = 3
    RETRY_DELAY_SECONDS = 1.0
    
    # ユーザーエージェント
    USER_AGENT = f"{ApplicationConstants.APPLICATION_NAME}/{ApplicationConstants.VERSION} (Windows)"


class PerformanceConstants:
    """パフォーマンス関連定数"""
    
    # スレッド設定
    DEFAULT_THREAD_POOL_SIZE = 4
    MAX_THREAD_POOL_SIZE = 16
    
    # メモリ設定
    MAX_MEMORY_USAGE_MB = 512
    GARBAGE_COLLECTION_THRESHOLD = 100
    
    # キャッシュ設定
    MAX_CACHE_SIZE = 1000
    CACHE_EXPIRY_MINUTES = 30
    
    # ファイルI/O
    BUFFER_SIZE = 8192
    MAX_FILE_SIZE_MB = 100


class ValidationConstants:
    """バリデーション関連定数"""
    
    # 文字列長制限
    MAX_RECORDING_NAME_LENGTH = 100
    MAX_DESCRIPTION_LENGTH = 1000
    MAX_PATH_LENGTH = 260  # Windows MAX_PATH
    
    # 数値制限
    MIN_COORDINATES = -32768
    MAX_COORDINATES = 32767
    MIN_DELAY_MS = 0
    MAX_DELAY_MS = 86400000  # 24時間
    
    # ファイル制限
    MAX_ACTIONS_PER_RECORDING = 10000
    MAX_RECORDINGS_PER_USER = 1000


# メインアプリケーション用定数
APP_NAME = ApplicationConstants.APPLICATION_NAME
APP_VERSION = ApplicationConstants.VERSION

# ディレクトリパス定数（main.pyで使用）
CONFIG_DIR = str(WindowsPaths.get_app_data_dir())
DATA_DIR = str(WindowsPaths.get_recordings_dir())
LOG_DIR = str(WindowsPaths.get_logs_dir())

# ファイル名定数
DEFAULT_CONFIG_FILE = f"config{ApplicationConstants.SETTINGS_FILE_EXTENSION}"
DEFAULT_LOG_FILE = f"ezrpa{ApplicationConstants.LOG_FILE_EXTENSION}"

# グローバル設定
DEBUG_MODE = os.environ.get('EZRPA_DEBUG', '').lower() in ('1', 'true', 'yes')
LOG_LEVEL = os.environ.get('EZRPA_LOG_LEVEL', 'INFO').upper()
DATA_ENCRYPTION_ENABLED = True
AUTO_BACKUP_ENABLED = True