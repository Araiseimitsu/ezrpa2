"""
イベントバス - Event Bus Implementation

疎結合なコンポーネント間通信を実現するイベント駆動アーキテクチャの実装。
Windows環境でのスレッドセーフティとパフォーマンスを考慮しています。
"""

from typing import Dict, List, Callable, Any, Type, Optional, Set, TypeVar
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
import threading
import time
import uuid
import weakref
from concurrent.futures import ThreadPoolExecutor
import queue
import asyncio
from datetime import datetime, timezone

from .result import Result, ResultBuilder, ErrorInfo

T = TypeVar('T')


class EventPriority(Enum):
    """イベント優先順位"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class EventStatus(Enum):
    """イベント処理状態"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Event(ABC):
    """
    イベントベースクラス
    
    Attributes:
        event_id: イベント一意識別子
        timestamp: 発生タイムスタンプ
        source: イベント発生元
        priority: イベント優先度
        correlation_id: 関連イベント識別子（オプション）
        metadata: 追加メタデータ
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "unknown"
    priority: EventPriority = EventPriority.NORMAL
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Windows環境での追加初期化"""
        if not self.metadata:
            self.metadata = {}
        
        # Windows固有のメタデータ
        import os
        import sys
        self.metadata.update({
            "platform": sys.platform,
            "process_id": os.getpid(),
            "thread_id": threading.get_ident()
        })
    
    def __lt__(self, other):
        """比較演算子（優先度キューでの並び順用）"""
        if not isinstance(other, Event):
            return NotImplemented
        # 優先度が高い方が先に処理される（数値が大きい方）
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value
        # 同じ優先度の場合はタイムスタンプで比較（古い方が先）
        return self.timestamp < other.timestamp
    
    def __eq__(self, other):
        """等価比較"""
        if not isinstance(other, Event):
            return NotImplemented
        return self.event_id == other.event_id
    
    def __hash__(self):
        """ハッシュ値"""
        return hash(self.event_id)


# RPA関連のイベント定義
@dataclass
class RecordingStartedEvent(Event):
    """記録開始イベント"""
    recording_id: str = ""
    recording_name: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "recording_service"


@dataclass
class RecordingStoppedEvent(Event):
    """記録停止イベント"""
    recording_id: str = ""
    action_count: int = 0
    duration_seconds: float = 0.0
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "recording_service"


@dataclass
class PlaybackStartedEvent(Event):
    """再生開始イベント"""
    recording_id: str = ""
    playback_id: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "playback_service"


@dataclass
class PlaybackCompletedEvent(Event):
    """再生完了イベント"""
    recording_id: str = ""
    playback_id: str = ""
    success: bool = True
    error_message: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "playback_service"


@dataclass
class ErrorEvent(Event):
    """エラーイベント"""
    error_code: str = ""
    error_message: str = ""
    error_details: Optional[str] = None
    recoverable: bool = False
    
    def __post_init__(self):
        super().__post_init__()
        self.priority = EventPriority.HIGH
        self.source = "error_handler"


@dataclass
class SystemEvent(Event):
    """システムイベント"""
    event_type: str = ""
    system_info: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "system"


# イベントハンドラーの型定義
EventHandler = Callable[[Event], None]
AsyncEventHandler = Callable[[Event], Any]  # async functions


@dataclass
class EventSubscription:
    """イベント購読情報"""
    event_type: Type[Event]
    handler: Callable
    is_async: bool = False
    priority: EventPriority = EventPriority.NORMAL
    filter_func: Optional[Callable[[Event], bool]] = None
    max_executions: Optional[int] = None
    executed_count: int = 0
    subscription_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class IEventBus(ABC):
    """イベントバスインターフェース"""
    
    @abstractmethod
    def subscribe(self, event_type: Type[Event], handler: EventHandler,
                 priority: EventPriority = EventPriority.NORMAL,
                 filter_func: Optional[Callable[[Event], bool]] = None) -> str:
        """イベントハンドラーを登録"""
        pass
    
    @abstractmethod
    def subscribe_async(self, event_type: Type[Event], handler: AsyncEventHandler,
                       priority: EventPriority = EventPriority.NORMAL) -> str:
        """非同期イベントハンドラーを登録"""
        pass
    
    @abstractmethod
    def unsubscribe(self, subscription_id: str) -> bool:
        """イベントハンドラーの登録を解除"""
        pass
    
    @abstractmethod
    def publish(self, event: Event) -> Result[bool, ErrorInfo]:
        """イベントを発行"""
        pass
    
    @abstractmethod
    async def publish_async(self, event: Event) -> Result[bool, ErrorInfo]:
        """非同期でイベントを発行"""
        pass


class EventBus(IEventBus):
    """
    イベントバス実装
    
    Windows環境でのマルチスレッド処理とパフォーマンスを考慮した
    イベント駆動アーキテクチャの中核実装。
    """
    
    def __init__(self, max_workers: int = 4, queue_size: int = 1000):
        self._subscriptions: Dict[Type[Event], List[EventSubscription]] = {}
        self._lock = threading.RLock()
        
        # Windows環境でのスレッドプール
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="EventBus"
        )
        
        # イベントキュー（Windows環境での高性能キュー）
        self._event_queue: queue.PriorityQueue = queue.PriorityQueue(maxsize=queue_size)
        self._processing_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._is_running = False
        
        # 統計情報
        self._stats = {
            "events_published": 0,
            "events_processed": 0,
            "handlers_executed": 0,
            "errors_occurred": 0,
            "start_time": time.time()
        }
        
        # 弱参照でのメモリリーク防止
        self._weak_refs: weakref.WeakSet = weakref.WeakSet()
        
        self._start_processing()
    
    def subscribe(self, event_type: Type[Event], handler: EventHandler,
                 priority: EventPriority = EventPriority.NORMAL,
                 filter_func: Optional[Callable[[Event], bool]] = None,
                 max_executions: Optional[int] = None) -> str:
        """
        イベントハンドラーを登録
        
        Args:
            event_type: 購読するイベントタイプ
            handler: イベントハンドラー関数
            priority: ハンドラー優先度
            filter_func: イベントフィルター関数
            max_executions: 最大実行回数
            
        Returns:
            購読ID
        """
        subscription = EventSubscription(
            event_type=event_type,
            handler=handler,
            is_async=False,
            priority=priority,
            filter_func=filter_func,
            max_executions=max_executions
        )
        
        with self._lock:
            if event_type not in self._subscriptions:
                self._subscriptions[event_type] = []
            
            self._subscriptions[event_type].append(subscription)
            # 優先度順にソート
            self._subscriptions[event_type].sort(
                key=lambda s: s.priority.value, reverse=True
            )
        
        # 弱参照登録
        self._weak_refs.add(handler)
        
        return subscription.subscription_id
    
    def subscribe_async(self, event_type: Type[Event], handler: AsyncEventHandler,
                       priority: EventPriority = EventPriority.NORMAL) -> str:
        """
        非同期イベントハンドラーを登録
        
        Args:
            event_type: 購読するイベントタイプ
            handler: 非同期イベントハンドラー関数
            priority: ハンドラー優先度
            
        Returns:
            購読ID
        """
        subscription = EventSubscription(
            event_type=event_type,
            handler=handler,
            is_async=True,
            priority=priority
        )
        
        with self._lock:
            if event_type not in self._subscriptions:
                self._subscriptions[event_type] = []
            
            self._subscriptions[event_type].append(subscription)
            self._subscriptions[event_type].sort(
                key=lambda s: s.priority.value, reverse=True
            )
        
        self._weak_refs.add(handler)
        return subscription.subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        イベントハンドラーの登録を解除
        
        Args:
            subscription_id: 購読ID
            
        Returns:
            解除成功の場合True
        """
        with self._lock:
            for event_type, subscriptions in self._subscriptions.items():
                for i, subscription in enumerate(subscriptions):
                    if subscription.subscription_id == subscription_id:
                        del subscriptions[i]
                        return True
        return False
    
    def publish(self, event: Event) -> Result[bool, ErrorInfo]:
        """
        イベントを発行（同期）
        
        Args:
            event: 発行するイベント
            
        Returns:
            発行結果
        """
        try:
            self._stats["events_published"] += 1
            
            # 優先度付きキューに追加（Eventに比較メソッドがあるので直接追加）
            self._event_queue.put(event)
            
            return ResultBuilder.success(True)
            
        except Exception as e:
            self._stats["errors_occurred"] += 1
            return ResultBuilder.from_exception(e, "event_publish_error")
    
    async def publish_async(self, event: Event) -> Result[bool, ErrorInfo]:
        """
        非同期でイベントを発行
        
        Args:
            event: 発行するイベント
            
        Returns:
            発行結果
        """
        return await asyncio.get_event_loop().run_in_executor(
            self._executor, self.publish, event
        )
    
    def _start_processing(self):
        """イベント処理スレッドを開始"""
        if self._is_running:
            return
        
        self._is_running = True
        self._processing_thread = threading.Thread(
            target=self._process_events,
            name="EventBusProcessor",
            daemon=True
        )
        self._processing_thread.start()
    
    def _process_events(self):
        """イベント処理メインループ"""
        while not self._stop_event.is_set():
            try:
                # タイムアウト付きでイベントを取得
                event = self._event_queue.get(timeout=1.0)
                
                if event is None:  # 終了シグナル
                    break
                
                self._handle_event(event)
                self._stats["events_processed"] += 1
                
            except queue.Empty:
                continue
            except Exception as e:
                self._stats["errors_occurred"] += 1
                # エラーログ（将来的にロガーサービスを使用）
                print(f"イベント処理エラー: {e}")
    
    def _handle_event(self, event: Event):
        """イベント処理"""
        event_type = type(event)
        
        # 継承関係も考慮したハンドラー検索
        matching_subscriptions = []
        with self._lock:
            for registered_type, subscriptions in self._subscriptions.items():
                if issubclass(event_type, registered_type):
                    matching_subscriptions.extend(subscriptions)
        
        # 優先度順に実行
        matching_subscriptions.sort(key=lambda s: s.priority.value, reverse=True)
        
        for subscription in matching_subscriptions:
            try:
                # フィルター条件チェック
                if subscription.filter_func and not subscription.filter_func(event):
                    continue
                
                # 最大実行回数チェック
                if (subscription.max_executions and 
                    subscription.executed_count >= subscription.max_executions):
                    continue
                
                # ハンドラー実行
                if subscription.is_async:
                    # 非同期ハンドラーは別スレッドで実行
                    self._executor.submit(self._run_async_handler, 
                                        subscription.handler, event)
                else:
                    subscription.handler(event)
                
                subscription.executed_count += 1
                self._stats["handlers_executed"] += 1
                
            except Exception as e:
                self._stats["errors_occurred"] += 1
                # エラーイベントを発行（無限ループ防止のため条件付き）
                if not isinstance(event, ErrorEvent):
                    error_event = ErrorEvent(
                        error_code="handler_execution_error",
                        error_message=str(e),
                        source="event_bus"
                    )
                    self.publish(error_event)
    
    def _run_async_handler(self, handler: AsyncEventHandler, event: Event):
        """非同期ハンドラーの実行"""
        try:
            if asyncio.iscoroutinefunction(handler):
                # 新しいイベントループで実行
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(handler(event))
                finally:
                    loop.close()
            else:
                handler(event)
        except Exception as e:
            self._stats["errors_occurred"] += 1
            print(f"非同期ハンドラーエラー: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """イベントバス統計情報を取得"""
        runtime = time.time() - self._stats["start_time"]
        
        stats = self._stats.copy()
        stats.update({
            "runtime_seconds": runtime,
            "events_per_second": self._stats["events_processed"] / max(runtime, 1),
            "queue_size": self._event_queue.qsize(),
            "active_subscriptions": sum(len(subs) for subs in self._subscriptions.values())
        })
        
        return stats
    
    def clear_subscriptions(self):
        """すべての購読を解除"""
        with self._lock:
            self._subscriptions.clear()
            self._weak_refs.clear()
    
    def shutdown(self):
        """イベントバスをシャットダウン"""
        if not self._is_running:
            return
        
        self._is_running = False
        self._stop_event.set()
        
        # 終了シグナルをキューに送信
        self._event_queue.put(None)
        
        # 処理スレッドの終了を待機
        if self._processing_thread:
            self._processing_thread.join(timeout=5.0)
        
        # スレッドプールをシャットダウン
        self._executor.shutdown(wait=True)
        
        # リソースクリーンアップ
        self.clear_subscriptions()
    
    def __enter__(self):
        """コンテキストマネージャー対応"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャー対応"""
        self.shutdown()


# グローバルイベントバスインスタンス
_global_event_bus: Optional[EventBus] = None
_event_bus_lock = threading.Lock()


def get_event_bus() -> EventBus:
    """
    グローバルイベントバスインスタンスを取得
    
    Returns:
        シングルトンイベントバスインスタンス
    """
    global _global_event_bus
    
    if _global_event_bus is None:
        with _event_bus_lock:
            if _global_event_bus is None:
                _global_event_bus = EventBus()
    
    return _global_event_bus


# アプリケーション終了時のクリーンアップ
import atexit

def _cleanup_event_bus():
    """イベントバスクリーンアップ"""
    global _global_event_bus
    if _global_event_bus:
        _global_event_bus.shutdown()
        _global_event_bus = None

atexit.register(_cleanup_event_bus)