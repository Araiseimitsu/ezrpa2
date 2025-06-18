"""
ドメイン値オブジェクト - Domain Value Objects

不変性を持つ値オブジェクトを定義します。
Windows環境での座標系、キー入力、時間等の型安全な表現を提供します。
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union
from enum import Enum, IntEnum, auto
from datetime import datetime, timedelta
import re
from pathlib import Path

from ..shared.constants import WindowsKeys, MouseButton, ValidationConstants


class ActionType(Enum):
    """アクション種別"""
    
    # キーボード操作
    KEY_PRESS = "key_press"           # キー押下
    KEY_RELEASE = "key_release"       # キー解放
    KEY_COMBINATION = "key_combination"  # キー組み合わせ（Ctrl+C等）
    TEXT_INPUT = "text_input"         # テキスト入力
    
    # マウス操作
    MOUSE_CLICK = "mouse_click"       # マウスクリック
    MOUSE_DOUBLE_CLICK = "mouse_double_click"  # ダブルクリック
    MOUSE_DRAG = "mouse_drag"         # ドラッグ操作
    MOUSE_MOVE = "mouse_move"         # マウス移動
    MOUSE_WHEEL = "mouse_wheel"       # ホイール操作
    
    # ウィンドウ操作
    WINDOW_ACTIVATE = "window_activate"    # ウィンドウアクティブ化
    WINDOW_CLOSE = "window_close"         # ウィンドウ閉じる
    WINDOW_MINIMIZE = "window_minimize"   # 最小化
    WINDOW_MAXIMIZE = "window_maximize"   # 最大化
    WINDOW_RESIZE = "window_resize"       # サイズ変更
    
    # 待機・制御
    WAIT = "wait"                     # 待機
    SCREENSHOT = "screenshot"         # スクリーンショット
    CONDITIONAL = "conditional"       # 条件分岐
    LOOP = "loop"                    # ループ処理
    
    # ファイル・システム操作
    FILE_OPEN = "file_open"          # ファイルオープン
    FILE_SAVE = "file_save"          # ファイル保存
    DIRECTORY_CHANGE = "directory_change"  # ディレクトリ変更
    
    # IME操作（日本語環境）
    IME_ON = "ime_on"                # IMEオン
    IME_OFF = "ime_off"              # IMEオフ
    IME_CONVERT = "ime_convert"      # 変換
    IME_CANCEL = "ime_cancel"        # 変換キャンセル


class RecordingStatus(Enum):
    """記録状態"""
    CREATED = "created"              # 作成済み
    RECORDING = "recording"          # 記録中
    PAUSED = "paused"               # 一時停止
    COMPLETED = "completed"          # 完了
    FAILED = "failed"               # 失敗
    CANCELLED = "cancelled"          # キャンセル


class PlaybackStatus(Enum):
    """再生状態"""
    READY = "ready"                 # 準備完了
    PLAYING = "playing"             # 再生中
    PAUSED = "paused"              # 一時停止
    COMPLETED = "completed"         # 完了
    FAILED = "failed"              # 失敗
    CANCELLED = "cancelled"         # キャンセル


class ScheduleStatus(Enum):
    """スケジュール状態"""
    ACTIVE = "active"               # アクティブ
    INACTIVE = "inactive"           # 非アクティブ
    RUNNING = "running"             # 実行中
    COMPLETED = "completed"         # 完了
    FAILED = "failed"              # 失敗


class TriggerType(Enum):
    """トリガー種別"""
    MANUAL = "manual"               # 手動実行
    SCHEDULED = "scheduled"         # スケジュール実行
    FILE_WATCHER = "file_watcher"   # ファイル監視
    HOTKEY = "hotkey"              # ホットキー
    STARTUP = "startup"            # 起動時
    IDLE = "idle"                  # アイドル時


@dataclass(frozen=True)
class Coordinate:
    """
    Windows座標値オブジェクト
    
    Windows環境でのDPI対応座標系を表現します。
    """
    x: int
    y: int
    dpi_scale: float = 1.0
    
    def __post_init__(self):
        if not (ValidationConstants.MIN_COORDINATES <= self.x <= ValidationConstants.MAX_COORDINATES):
            raise ValueError(f"X座標が範囲外です: {self.x}")
        if not (ValidationConstants.MIN_COORDINATES <= self.y <= ValidationConstants.MAX_COORDINATES):
            raise ValueError(f"Y座標が範囲外です: {self.y}")
        if self.dpi_scale <= 0:
            raise ValueError(f"DPIスケールは正の値である必要があります: {self.dpi_scale}")
    
    def scale(self, factor: float) -> 'Coordinate':
        """座標をスケーリング"""
        return Coordinate(
            x=int(self.x * factor),
            y=int(self.y * factor),
            dpi_scale=self.dpi_scale
        )
    
    def offset(self, dx: int, dy: int) -> 'Coordinate':
        """座標をオフセット"""
        return Coordinate(
            x=self.x + dx,
            y=self.y + dy,
            dpi_scale=self.dpi_scale
        )
    
    def distance_to(self, other: 'Coordinate') -> float:
        """他の座標との距離を計算"""
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5
    
    def to_physical(self) -> 'Coordinate':
        """物理座標に変換（DPI考慮）"""
        return Coordinate(
            x=int(self.x * self.dpi_scale),
            y=int(self.y * self.dpi_scale),
            dpi_scale=1.0
        )


@dataclass(frozen=True)
class Rectangle:
    """矩形領域"""
    left: int
    top: int
    right: int
    bottom: int
    
    def __post_init__(self):
        if self.left >= self.right:
            raise ValueError("左端は右端より小さい必要があります")
        if self.top >= self.bottom:
            raise ValueError("上端は下端より小さい必要があります")
    
    @property
    def width(self) -> int:
        """幅"""
        return self.right - self.left
    
    @property
    def height(self) -> int:
        """高さ"""
        return self.bottom - self.top
    
    @property
    def center(self) -> Coordinate:
        """中心座標"""
        return Coordinate(
            x=(self.left + self.right) // 2,
            y=(self.top + self.bottom) // 2
        )
    
    def contains(self, point: Coordinate) -> bool:
        """座標が矩形内に含まれるかチェック"""
        return (self.left <= point.x <= self.right and 
                self.top <= point.y <= self.bottom)
    
    def intersects(self, other: 'Rectangle') -> bool:
        """他の矩形と交差するかチェック"""
        return not (self.right < other.left or 
                   other.right < self.left or
                   self.bottom < other.top or 
                   other.bottom < self.top)


@dataclass(frozen=True)
class Duration:
    """
    時間間隔値オブジェクト
    
    ミリ秒単位での時間表現とバリデーション機能を提供します。
    """
    milliseconds: int
    
    def __post_init__(self):
        if not (ValidationConstants.MIN_DELAY_MS <= self.milliseconds <= ValidationConstants.MAX_DELAY_MS):
            raise ValueError(f"時間間隔が範囲外です: {self.milliseconds}ms")
    
    @classmethod
    def from_seconds(cls, seconds: float) -> 'Duration':
        """秒数から作成"""
        return cls(int(seconds * 1000))
    
    @classmethod
    def from_minutes(cls, minutes: float) -> 'Duration':
        """分数から作成"""
        return cls(int(minutes * 60 * 1000))
    
    @property
    def seconds(self) -> float:
        """秒数として取得"""
        return self.milliseconds / 1000.0
    
    @property
    def minutes(self) -> float:
        """分数として取得"""
        return self.milliseconds / 60000.0
    
    def add(self, other: 'Duration') -> 'Duration':
        """時間間隔を加算"""
        return Duration(self.milliseconds + other.milliseconds)
    
    def multiply(self, factor: float) -> 'Duration':
        """時間間隔を倍数化"""
        return Duration(int(self.milliseconds * factor))


@dataclass(frozen=True)
class KeyInput:
    """
    キー入力値オブジェクト
    
    Windows仮想キーコードと修飾キーの組み合わせを表現します。
    """
    key_code: int
    shift: bool = False
    ctrl: bool = False
    alt: bool = False
    win: bool = False  # Windowsキー
    
    def __post_init__(self):
        if not (0 <= self.key_code <= 255):
            raise ValueError(f"無効なキーコードです: {self.key_code}")
    
    @classmethod
    def from_char(cls, char: str) -> 'KeyInput':
        """文字からキー入力を作成"""
        if len(char) != 1:
            raise ValueError("単一文字のみサポートされています")
        
        # ASCII文字の場合
        if char.isalpha():
            return cls(
                key_code=ord(char.upper()),
                shift=char.isupper()
            )
        elif char.isdigit():
            return cls(key_code=ord(char))
        else:
            # 特殊文字のマッピング
            special_chars = {
                ' ': WindowsKeys.VK_SPACE,
                '\t': WindowsKeys.VK_TAB,
                '\n': WindowsKeys.VK_RETURN,
                '\b': WindowsKeys.VK_BACK,
            }
            
            if char in special_chars:
                return cls(key_code=special_chars[char])
            else:
                raise ValueError(f"サポートされていない文字です: {char}")
    
    @classmethod
    def ctrl_combination(cls, key_code: int) -> 'KeyInput':
        """Ctrl+キーの組み合わせを作成"""
        return cls(key_code=key_code, ctrl=True)
    
    @classmethod
    def alt_combination(cls, key_code: int) -> 'KeyInput':
        """Alt+キーの組み合わせを作成"""
        return cls(key_code=key_code, alt=True)
    
    def to_string(self) -> str:
        """キー組み合わせを文字列表現で取得"""
        parts = []
        if self.win:
            parts.append("Win")
        if self.ctrl:
            parts.append("Ctrl")
        if self.alt:
            parts.append("Alt")
        if self.shift:
            parts.append("Shift")
        
        # キー名の取得（簡略版）
        key_name = f"Key({self.key_code})"
        if 0x41 <= self.key_code <= 0x5A:  # A-Z
            key_name = chr(self.key_code)
        elif 0x30 <= self.key_code <= 0x39:  # 0-9
            key_name = chr(self.key_code)
        
        parts.append(key_name)
        return "+".join(parts)


@dataclass(frozen=True)
class MouseInput:
    """マウス入力値オブジェクト"""
    button: MouseButton
    position: Coordinate
    double_click: bool = False
    wheel_delta: int = 0  # ホイール操作の場合
    
    def __post_init__(self):
        if self.wheel_delta != 0 and self.button != MouseButton.MIDDLE:
            raise ValueError("ホイール操作はミドルボタンでのみ有効です")


@dataclass(frozen=True)
class WindowInfo:
    """
    ウィンドウ情報値オブジェクト
    
    Windows環境でのウィンドウ識別と操作対象の情報を保持します。
    """
    title: str
    class_name: str
    process_name: str
    handle: Optional[int] = None  # Windows HWND
    bounds: Optional[Rectangle] = None
    is_visible: bool = True
    is_enabled: bool = True
    
    def __post_init__(self):
        if not self.title and not self.class_name and not self.process_name:
            raise ValueError("ウィンドウ識別情報が不足しています")
    
    def matches(self, pattern: str, match_type: str = "title") -> bool:
        """パターンマッチング"""
        target = getattr(self, match_type, "")
        if not target:
            return False
        
        # 正規表現マッチング
        try:
            return bool(re.search(pattern, target, re.IGNORECASE))
        except re.error:
            # 正規表現エラーの場合は部分文字列マッチング
            return pattern.lower() in target.lower()


@dataclass(frozen=True)
class FileInfo:
    """ファイル情報値オブジェクト"""
    path: Path
    exists: bool = False
    size: int = 0
    modified_time: Optional[datetime] = None
    
    def __post_init__(self):
        if len(str(self.path)) > ValidationConstants.MAX_PATH_LENGTH:
            raise ValueError(f"パスが長すぎます: {self.path}")


@dataclass(frozen=True)
class ValidationResult:
    """バリデーション結果値オブジェクト"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_error(self, message: str) -> 'ValidationResult':
        """エラーを追加"""
        return ValidationResult(
            is_valid=False,
            errors=self.errors + [message],
            warnings=self.warnings
        )
    
    def add_warning(self, message: str) -> 'ValidationResult':
        """警告を追加"""
        return ValidationResult(
            is_valid=self.is_valid,
            errors=self.errors,
            warnings=self.warnings + [message]
        )


# 事前定義された値オブジェクト
class CommonDurations:
    """よく使用される時間間隔"""
    IMMEDIATE = Duration(0)
    VERY_SHORT = Duration(100)    # 0.1秒
    SHORT = Duration(500)         # 0.5秒
    MEDIUM = Duration(1000)       # 1秒
    LONG = Duration(2000)         # 2秒
    VERY_LONG = Duration(5000)    # 5秒


class CommonKeys:
    """よく使用されるキー入力"""
    ENTER = KeyInput(WindowsKeys.VK_RETURN)
    ESCAPE = KeyInput(WindowsKeys.VK_ESCAPE)
    TAB = KeyInput(WindowsKeys.VK_TAB)
    BACKSPACE = KeyInput(WindowsKeys.VK_BACK)
    
    # Ctrl組み合わせ
    CTRL_C = KeyInput.ctrl_combination(ord('C'))
    CTRL_V = KeyInput.ctrl_combination(ord('V'))
    CTRL_X = KeyInput.ctrl_combination(ord('X'))
    CTRL_Z = KeyInput.ctrl_combination(ord('Z'))
    CTRL_A = KeyInput.ctrl_combination(ord('A'))
    CTRL_S = KeyInput.ctrl_combination(ord('S'))
    
    # Alt組み合わせ
    ALT_F4 = KeyInput.alt_combination(WindowsKeys.VK_F4)
    ALT_TAB = KeyInput.alt_combination(WindowsKeys.VK_TAB)
    
    # IME関連
    CONVERT = KeyInput(WindowsKeys.VK_CONVERT)
    NONCONVERT = KeyInput(WindowsKeys.VK_NONCONVERT)