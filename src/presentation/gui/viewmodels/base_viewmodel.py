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

from ....core.result import Result, Ok, Err, ErrorInfo
from ....core.event_bus import EventBus, Event, SystemEvent


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


class BaseViewModel(ABC):
    """BaseViewModel - 全ViewModelの基底クラス"""
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        """
        初期化
        
        Args:
            event_bus: イベントバス（オプション）
        """
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
    
    def _initialize_common_commands(self):
        """共通コマンドの初期化"""
        self._commands.update({
            'refresh': AsyncCommand(self._refresh_async, lambda: not self.is_busy),
            'clear_errors': Command(self._clear_errors),
            'clear_notifications': Command(self._clear_notifications)
        })
    
    # プロパティ変更通知システム
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
    
    # ビジネス状態管理
    @property
    def is_busy(self) -> bool:
        """ビジー状態かどうか"""
        return self._is_busy
    
    @is_busy.setter
    def is_busy(self, value: bool):
        """ビジー状態を設定"""
        if self.set_property('is_busy', value):
            self._is_busy = value
            # コマンドの実行可能状態を更新
            self._update_commands_can_execute()
    
    @property
    def busy_message(self) -> str:
        """ビジーメッセージ"""
        return self._busy_message
    
    @busy_message.setter
    def busy_message(self, value: str):
        """ビジーメッセージを設定"""
        if self.set_property('busy_message', value):
            self._busy_message = value
    
    def set_busy(self, is_busy: bool, message: str = ""):
        """ビジー状態とメッセージを同時設定"""
        self.busy_message = message
        self.is_busy = is_busy
    
    # エラー管理
    @property
    def errors(self) -> List[ViewModelError]:
        """エラーリストを取得"""
        return self._errors.copy()
    
    @property
    def has_errors(self) -> bool:
        """エラーがあるかどうか"""
        return len([e for e in self._errors if not e.is_handled]) > 0
    
    def add_error(self, message: str, details: Optional[str] = None, error_type: str = "GENERAL") -> ViewModelError:
        """エラーを追加"""
        error = ViewModelError(
            message=message,
            details=details,
            error_type=error_type
        )
        self._errors.append(error)
        self.notify_property_changed('has_errors', not self.has_errors, True)
        
        # エラーイベントを発行
        error_event = SystemEvent(
            event_type='error_occurred',
            system_info={
                'view_model': self.__class__.__name__,
                'error': error
            }
        )
        self._event_bus.publish(error_event)
        
        return error
    
    def handle_error(self, error_id: str):
        """エラーを処理済みとしてマーク"""
        for error in self._errors:
            if error.error_id == error_id:
                error.is_handled = True
                break
        
        self.notify_property_changed('has_errors', self.has_errors, self.has_errors)
    
    def _clear_errors(self):
        """エラーをクリア"""
        self._errors.clear()
        self.notify_property_changed('has_errors', True, False)
    
    def handle_result_error(self, result: Result, context: str = "") -> bool:
        """Result型のエラーを処理"""
        if result.is_failure():
            error_msg = f"{context}: {result.error.message}" if context else result.error.message
            self.add_error(error_msg, result.error.details, result.error.code)
            return True
        return False
    
    # 通知管理
    @property
    def notifications(self) -> List[NotificationMessage]:
        """通知リストを取得"""
        return self._notifications.copy()
    
    def add_notification(self, title: str, message: str, notification_type: str = "INFO", 
                        duration_ms: int = 5000, is_persistent: bool = False) -> NotificationMessage:
        """通知を追加"""
        notification = NotificationMessage(
            title=title,
            message=message,
            notification_type=notification_type,
            duration_ms=duration_ms,
            is_persistent=is_persistent
        )
        self._notifications.append(notification)
        
        # 通知イベントを発行
        notification_event = SystemEvent(
            event_type='notification_added',
            system_info={
                'view_model': self.__class__.__name__,
                'notification': notification
            }
        )
        self._event_bus.publish(notification_event)
        
        return notification
    
    def remove_notification(self, message_id: str):
        """通知を削除"""
        self._notifications = [n for n in self._notifications if n.message_id != message_id]
    
    def _clear_notifications(self):
        """通知をクリア"""
        self._notifications.clear()
    
    # コマンド管理
    def get_command(self, command_name: str) -> Optional[Command]:
        """コマンドを取得"""
        return self._commands.get(command_name)
    
    def add_command(self, command_name: str, command: Command):
        """コマンドを追加"""
        self._commands[command_name] = command
    
    def _update_commands_can_execute(self):
        """全コマンドの実行可能状態を更新"""
        for command in self._commands.values():
            command.notify_can_execute_changed()
    
    # 非同期実行ヘルパー
    async def execute_async(self, operation: Callable, busy_message: str = "処理中...") -> Result:
        """非同期処理を実行（ビジー状態管理付き）"""
        try:
            self.set_busy(True, busy_message)
            
            if asyncio.iscoroutinefunction(operation):
                result = await operation()
            else:
                result = operation()
            
            return result if isinstance(result, Result) else Ok(result)
            
        except Exception as e:
            error_info = ErrorInfo("ASYNC_EXECUTION_ERROR", f"非同期実行エラー: {str(e)}")
            self.add_error(error_info.message, str(e), error_info.code)
            return Err(error_info)
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
    
    # ライフサイクル管理
    def dispose(self):
        """リソースを破棄"""
        if self._disposed:
            return
        
        self._disposed = True
        self._property_changed_handlers.clear()
        self._errors.clear()
        self._notifications.clear()
        self._commands.clear()
        
        # サブクラスの破棄処理
        self._dispose_resources()
    
    def _dispose_resources(self):
        """サブクラス固有のリソース破棄（オーバーライド可能）"""
        pass
    
    def __del__(self):
        """デストラクタ"""
        self.dispose()