"""
Core Layer - 基盤機能モジュール

このモジュールはアプリケーション全体で使用される基盤機能を提供します。
- 依存性注入コンテナ
- イベントバス
- Resultパターン
- スレッド管理

使用例:
    from src.core import get_container, get_event_bus, get_thread_manager
    from src.core.result import Ok, Err, Result
    
    # 依存性注入
    container = get_container()
    
    # イベント発行
    event_bus = get_event_bus()
    
    # バックグラウンド処理
    thread_manager = get_thread_manager()
"""

from .container import (
    Container, 
    IContainer, 
    get_container, 
    dispose_container,
    WindowsServiceRegistry
)

from .event_bus import (
    Event,
    EventBus,
    IEventBus,
    get_event_bus,
    EventPriority,
    RecordingStartedEvent,
    RecordingStoppedEvent,
    PlaybackStartedEvent,
    PlaybackCompletedEvent,
    ErrorEvent,
    SystemEvent
)

from .result import (
    Result,
    Success,
    Failure,
    ResultBuilder,
    Ok,
    Err,
    ErrorInfo,
    WindowsErrorCode,
    try_catch,
    async_try_catch,
    ResultExtensions
)

from .threading import (
    ThreadManager,
    IThreadManager,
    WorkerThread,
    get_thread_manager,
    ThreadPriority,
    ThreadState,
    ThreadResult,
    run_background_task,
    run_with_progress
)

__all__ = [
    # Container
    'Container', 'IContainer', 'get_container', 'dispose_container',
    'WindowsServiceRegistry',
    
    # Event Bus
    'Event', 'EventBus', 'IEventBus', 'get_event_bus', 'EventPriority',
    'RecordingStartedEvent', 'RecordingStoppedEvent', 
    'PlaybackStartedEvent', 'PlaybackCompletedEvent',
    'ErrorEvent', 'SystemEvent',
    
    # Result Pattern
    'Result', 'Success', 'Failure', 'ResultBuilder', 'Ok', 'Err',
    'ErrorInfo', 'WindowsErrorCode', 'try_catch', 'async_try_catch',
    'ResultExtensions',
    
    # Threading
    'ThreadManager', 'IThreadManager', 'WorkerThread', 'get_thread_manager',
    'ThreadPriority', 'ThreadState', 'ThreadResult',
    'run_background_task', 'run_with_progress'
]