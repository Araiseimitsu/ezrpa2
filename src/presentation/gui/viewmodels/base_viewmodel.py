"""
Base ViewModel - MVVMパターンの基盤クラス

全てのViewModelクラスの基底クラスとして、共通機能を提供します。
プロパティ変更通知、コマンドパターン、エラーハンドリングを統一的に実装します。
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, Set
from datetime import datetime, timezone
from dataclasses import dataclass, field
import uuid

try:
    from PySide6.QtCore import QObject, Signal
    QT_AVAILABLE = True
except ImportError:
    try:
        from PyQt6.QtCore import QObject, pyqtSignal as Signal
        QT_AVAILABLE = True
    except ImportError:
        # Qt not available, create a dummy QObject and Signal
        class QObject:
            def __init__(self):
                pass
        
        class Signal:
            def __init__(self, *args):
                pass
            def connect(self, func):
                pass
            def emit(self, *args):
                pass
        
        QT_AVAILABLE = False

from ....core.result import Result, Ok, Err, ErrorInfo
from ....core.event_bus import EventBus, Event, SystemEvent

# Qt関連のエクスポート
__all__ = ['BaseViewModel', 'Command', 'AsyncCommand', 'ViewModelError', 'NotificationMessage', 'PropertyChangedEventArgs', 'QObject', 'Signal']


@dataclass
class ViewModelError:
    """ViewModelエラー情報"""
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message: str = ""
    details: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error_type: str = "GENERAL"
    is_handled: bool = False


@dataclass
class NotificationMessage:
    """通知メッセージ"""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    message: str = ""
    notification_type: str = "INFO"  # INFO, WARNING, ERROR, SUCCESS
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: int = 5000
    is_persistent: bool = False


class PropertyChangedEventArgs:
    """プロパティ変更イベント引数"""
    
    def __init__(self, property_name: str, old_value: Any = None, new_value: Any = None):
        self.property_name = property_name
        self.old_value = old_value
        self.new_value = new_value
        self.timestamp = datetime.now(timezone.utc)


class Command:
    """コマンドパターンの実装"""
    
    def __init__(self, execute_func: Callable, can_execute_func: Optional[Callable] = None):
        self._execute_func = execute_func
        self._can_execute_func = can_execute_func or (lambda: True)
        self._can_execute_changed_handlers = []
    
    def execute(self, parameter: Any = None):
        """コマンドを実行"""
        if self.can_execute(parameter):
            return self._execute_func(parameter)
    
    def can_execute(self, parameter: Any = None) -> bool:
        """実行可能かどうかを判定"""
        return self._can_execute_func(parameter)
    
    def add_can_execute_changed_handler(self, handler: Callable):
        """実行可能状態変更ハンドラーを追加"""
        self._can_execute_changed_handlers.append(handler)
    
    def remove_can_execute_changed_handler(self, handler: Callable):
        """実行可能状態変更ハンドラーを削除"""
        if handler in self._can_execute_changed_handlers:
            self._can_execute_changed_handlers.remove(handler)
    
    def notify_can_execute_changed(self):
        """実行可能状態の変更を通知"""
        for handler in self._can_execute_changed_handlers:
            try:
                handler()
            except Exception as e:
                print(f"コマンド状態変更通知エラー: {e}")


class AsyncCommand(Command):
    """非同期コマンドの実装"""
    
    def __init__(self, execute_func: Callable, can_execute_func: Optional[Callable] = None):
        super().__init__(execute_func, can_execute_func)
        self._is_executing = False
    
    async def execute_async(self, parameter: Any = None):
        """非同期でコマンドを実行"""
        if not self.can_execute(parameter) or self._is_executing:
            return
        
        self._is_executing = True
        self.notify_can_execute_changed()
        
        try:
            if asyncio.iscoroutinefunction(self._execute_func):
                return await self._execute_func(parameter)
            else:
                return self._execute_func(parameter)
        finally:
            self._is_executing = False
            self.notify_can_execute_changed()
    
    def can_execute(self, parameter: Any = None) -> bool:
        """実行可能かどうかを判定（実行中は不可）"""
        return not self._is_executing and super().can_execute(parameter)


# カスタムメタクラスでABCとQObjectの競合を解決
if QT_AVAILABLE:
    class ViewModelMeta(type(ABC), type(QObject)):
        """BaseViewModel用のカスタムメタクラス"""
        pass
    
    class BaseViewModel(ABC, QObject, metaclass=ViewModelMeta):
        """BaseViewModel - 全ViewModelの基底クラス"""
        
        def __init__(self, event_bus: Optional[EventBus] = None):
            """初期化"""
            QObject.__init__(self)
            self._initialize_base(event_bus)
        
        def _initialize_base(self, event_bus: Optional[EventBus] = None):
            """基底クラスの初期化"""
            self._event_bus = event_bus or EventBus()
            self._property_changed_handlers = []
            self._properties = {}
            self._errors = []
            self._notifications = []
            self._is_busy = False
            self._busy_message = ""
            self._commands = {}
            self._disposed = False
            
            # 共通コマンドの初期化
            self._initialize_common_commands()
else:
    class BaseViewModel(ABC):
        """BaseViewModel - 全ViewModelの基底クラス（Qt無し版）"""
        
        def __init__(self, event_bus: Optional[EventBus] = None):
            """初期化"""
            self._initialize_base(event_bus)
        
        def _initialize_base(self, event_bus: Optional[EventBus] = None):
            """基底クラスの初期化"""
            self._event_bus = event_bus or EventBus()
            self._property_changed_handlers = []
            self._properties = {}
            self._errors = []
            self._notifications = []
            self._is_busy = False
            self._busy_message = ""
            self._commands = {}
            self._disposed = False
            
            # 共通コマンドの初期化
            self._initialize_common_commands()


# BaseViewModelの共通メソッドを定義
def _initialize_common_commands(self):
    """共通コマンドの初期化"""
    self._commands.update({
        'refresh': AsyncCommand(self._refresh_async, lambda: not self.is_busy),
        'clear_errors': Command(self._clear_errors),
        'clear_notifications': Command(self._clear_notifications)
    })

def add_property_changed_handler(self, handler: Callable[[PropertyChangedEventArgs], None]):
    """プロパティ変更ハンドラーを追加"""
    self._property_changed_handlers.append(handler)

def remove_property_changed_handler(self, handler: Callable[[PropertyChangedEventArgs], None]):
    """プロパティ変更ハンドラーを削除"""
    if handler in self._property_changed_handlers:
        self._property_changed_handlers.remove(handler)

def notify_property_changed(self, property_name: str, old_value: Any = None, new_value: Any = None):
    """プロパティ変更を通知"""
    args = PropertyChangedEventArgs(property_name, old_value, new_value)
    
    for handler in self._property_changed_handlers:
        try:
            handler(args)
        except Exception as e:
            print(f"プロパティ変更通知エラー: {e}")
    
    # イベントバスへの通知
    event = SystemEvent(
        event_type='property_changed',
        system_info={
            'view_model': self.__class__.__name__,
            'property_name': property_name,
            'old_value': old_value,
            'new_value': new_value
        }
    )
    self._event_bus.publish(event)

def set_property(self, property_name: str, value: Any) -> bool:
    """プロパティを設定し、変更があれば通知"""
    old_value = self._properties.get(property_name)
    
    if old_value != value:
        self._properties[property_name] = value
        self.notify_property_changed(property_name, old_value, value)
        return True
    
    return False

def get_property(self, property_name: str, default_value: Any = None) -> Any:
    """プロパティを取得"""
    return self._properties.get(property_name, default_value)

@property
def is_busy(self) -> bool:
    """ビジー状態かどうか"""
    return self._is_busy

@property
def busy_message(self) -> str:
    """ビジーメッセージ"""
    return self._busy_message

def set_busy(self, is_busy: bool, message: str = ""):
    """ビジー状態を設定"""
    if self.set_property('is_busy', is_busy):
        self._is_busy = is_busy
    
    if self.set_property('busy_message', message):
        self._busy_message = message

@property
def errors(self) -> List[ViewModelError]:
    """エラー一覧"""
    return self._errors.copy()

@property
def notifications(self) -> List[NotificationMessage]:
    """通知一覧"""
    return self._notifications.copy()

def add_error(self, message: str, details: Optional[str] = None, error_type: str = "GENERAL"):
    """エラーを追加"""
    error = ViewModelError(message=message, details=details, error_type=error_type)
    self._errors.append(error)
    self.notify_property_changed('errors')

def add_notification(self, title: str, message: str, notification_type: str = "INFO", duration_ms: int = 5000):
    """通知を追加"""
    notification = NotificationMessage(
        title=title,
        message=message,
        notification_type=notification_type,
        duration_ms=duration_ms
    )
    self._notifications.append(notification)
    self.notify_property_changed('notifications')

def clear_errors(self):
    """エラーをクリア"""
    self._errors.clear()
    self.notify_property_changed('errors')

def _clear_errors(self, parameter: Any = None):
    """エラークリアコマンド"""
    self.clear_errors()

def clear_notifications(self):
    """通知をクリア"""
    self._notifications.clear()
    self.notify_property_changed('notifications')

def _clear_notifications(self, parameter: Any = None):
    """通知クリアコマンド"""
    self.clear_notifications()

def add_command(self, name: str, command: Command):
    """コマンドを追加"""
    self._commands[name] = command

def get_command(self, name: str) -> Optional[Command]:
    """コマンドを取得"""
    return self._commands.get(name)

def remove_command(self, name: str):
    """コマンドを削除"""
    if name in self._commands:
        del self._commands[name]

async def refresh_async(self, parameter: Any = None):
    """リフレッシュ処理の公開メソッド"""
    try:
        self.set_busy(True, "更新中...")
        await self._refresh_async(parameter)
    except Exception as e:
        self.add_error("更新エラー", str(e), "REFRESH_ERROR")
    finally:
        self.set_busy(False)

# 抽象メソッド
@abstractmethod
async def initialize_async(self):
    """非同期初期化（サブクラスで実装）"""
    pass

@abstractmethod
async def _refresh_async(self, parameter: Any = None):
    """リフレッシュ処理（サブクラスで実装）"""
    pass

def dispose(self):
    """リソースを破棄"""
    if self._disposed:
        return
    
    self._disposed = True
    self._property_changed_handlers.clear()
    self._commands.clear()
    self._errors.clear()
    self._notifications.clear()
    
    # 具象クラスでのリソース破棄をサポート
    if hasattr(self, '_dispose_resources'):
        self._dispose_resources()

# メソッドをBaseViewModelクラスに追加
BaseViewModel._initialize_common_commands = _initialize_common_commands
BaseViewModel.add_property_changed_handler = add_property_changed_handler
BaseViewModel.remove_property_changed_handler = remove_property_changed_handler
BaseViewModel.notify_property_changed = notify_property_changed
BaseViewModel.set_property = set_property
BaseViewModel.get_property = get_property
BaseViewModel.is_busy = is_busy
BaseViewModel.busy_message = busy_message
BaseViewModel.set_busy = set_busy
BaseViewModel.errors = errors
BaseViewModel.notifications = notifications
BaseViewModel.add_error = add_error
BaseViewModel.add_notification = add_notification
BaseViewModel.clear_errors = clear_errors
BaseViewModel._clear_errors = _clear_errors
BaseViewModel.clear_notifications = clear_notifications
BaseViewModel._clear_notifications = _clear_notifications
BaseViewModel.add_command = add_command
BaseViewModel.get_command = get_command
BaseViewModel.remove_command = remove_command
BaseViewModel.refresh_async = refresh_async
BaseViewModel.initialize_async = initialize_async
BaseViewModel._refresh_async = _refresh_async
BaseViewModel.dispose = dispose