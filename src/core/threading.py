"""
Windows対応スレッド管理 - Thread Management for Windows

Windows環境でのマルチスレッド処理とQt統合を安全に行うための
スレッド管理機能を提供します。UIフリーズやクラッシュを防止します。
"""

import sys
import threading
import time
import queue
import asyncio
from typing import Callable, Any, Optional, Dict, List, Union, TypeVar
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
import weakref
from abc import ABC, abstractmethod

from .result import Result, ResultBuilder, ErrorInfo
from .event_bus import Event, get_event_bus

# Windows環境でのQt対応
try:
    if sys.platform == "win32":
        from PySide6.QtCore import QThread, QObject, Signal, QTimer, QMutex, QMutexLocker
        from PySide6.QtWidgets import QApplication
        QT_AVAILABLE = True
    else:
        QT_AVAILABLE = False
except ImportError:
    QT_AVAILABLE = False

T = TypeVar('T')


class ThreadPriority(Enum):
    """スレッド優先度（Windows準拠）"""
    IDLE = 1
    LOWEST = 2
    BELOW_NORMAL = 3
    NORMAL = 4
    ABOVE_NORMAL = 5
    HIGHEST = 6
    TIME_CRITICAL = 7


class ThreadState(Enum):
    """スレッド状態"""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ThreadResult:
    """スレッド実行結果"""
    thread_id: str
    result: Any = None
    error: Optional[Exception] = None
    execution_time: float = 0.0
    state: ThreadState = ThreadState.CREATED


@dataclass 
class ThreadStartedEvent(Event):
    """スレッド開始イベント"""
    thread_id: str = ""
    thread_name: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "thread_manager"


@dataclass
class ThreadCompletedEvent(Event):
    """スレッド完了イベント"""
    thread_id: str = ""
    thread_name: str = ""
    success: bool = True
    execution_time: float = 0.0
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "thread_manager"


class IThreadManager(ABC):
    """スレッド管理インターフェース"""
    
    @abstractmethod
    def run_in_background(self, task: Callable, *args, **kwargs) -> Future:
        """バックグラウンドタスクを実行"""
        pass
    
    @abstractmethod
    def run_with_callback(self, task: Callable, callback: Callable = None, 
                         error_callback: Callable = None) -> str:
        """コールバック付きタスクを実行"""
        pass
    
    @abstractmethod
    def shutdown(self, timeout: float = 30.0) -> bool:
        """スレッドマネージャーをシャットダウン"""
        pass


class WorkerThread(QThread if QT_AVAILABLE else threading.Thread):
    """
    安全なワーカースレッド
    
    Windows環境でのQt統合とエラーハンドリングを提供する
    ワーカースレッドの実装。
    """
    
    if QT_AVAILABLE:
        # Qtシグナル定義
        result_ready = Signal(object)
        error_occurred = Signal(str)
        progress_updated = Signal(int)
        status_changed = Signal(str)
    
    def __init__(self, task: Callable, *args, thread_name: str = None, 
                 priority: ThreadPriority = ThreadPriority.NORMAL, **kwargs):
        super().__init__()
        
        self.task = task
        self.args = args
        self.kwargs = kwargs
        self.thread_id = f"worker_{int(time.time() * 1000000)}"
        self._thread_name = thread_name or f"WorkerThread_{self.thread_id}"
        self._priority = priority
        self._start_time = 0.0
        self._result = None
        self._error = None
        self._cancelled = False
        self._pause_event = threading.Event()
        self._pause_event.set()  # 初期状態では一時停止していない
        
        # Windows環境での名前設定
        if hasattr(self, 'setObjectName'):
            self.setObjectName(self._thread_name)
        else:
            self.name = self._thread_name
    
    def run(self):
        """スレッド実行メイン処理"""
        self._start_time = time.time()
        
        try:
            # 優先度設定（Windows環境）
            if sys.platform == "win32":
                self._set_windows_priority()
            
            # イベント発行
            event_bus = get_event_bus()
            event_bus.publish(ThreadStartedEvent(
                thread_id=self.thread_id,
                thread_name=self._thread_name
            ))
            
            # タスク実行
            if self._cancelled:
                return
            
            self._pause_event.wait()  # 一時停止チェック
            
            if QT_AVAILABLE and hasattr(self, 'status_changed'):
                self.status_changed.emit("実行中")
            
            self._result = self.task(*self.args, **self.kwargs)
            
            # 成功シグナル発行
            if QT_AVAILABLE and hasattr(self, 'result_ready'):
                self.result_ready.emit(self._result)
            
            # 完了イベント発行
            execution_time = time.time() - self._start_time
            event_bus.publish(ThreadCompletedEvent(
                thread_id=self.thread_id,
                thread_name=self._thread_name,
                success=True,
                execution_time=execution_time
            ))
            
        except Exception as e:
            self._error = e
            error_msg = f"スレッドエラー [{self._thread_name}]: {str(e)}"
            
            # エラーシグナル発行
            if QT_AVAILABLE and hasattr(self, 'error_occurred'):
                self.error_occurred.emit(error_msg)
            
            # エラーイベント発行
            execution_time = time.time() - self._start_time
            event_bus.publish(ThreadCompletedEvent(
                thread_id=self.thread_id,
                thread_name=self._thread_name,
                success=False,
                execution_time=execution_time
            ))
            
            # デバッグ出力（将来的にloggerサービスを使用）
            print(error_msg)
    
    def _set_windows_priority(self):
        """Windows環境でのスレッド優先度設定"""
        if sys.platform != "win32":
            return
        
        try:
            import ctypes
            from ctypes import wintypes
            
            # Windows API定数
            priority_map = {
                ThreadPriority.IDLE: -15,
                ThreadPriority.LOWEST: -2,
                ThreadPriority.BELOW_NORMAL: -1,
                ThreadPriority.NORMAL: 0,
                ThreadPriority.ABOVE_NORMAL: 1,
                ThreadPriority.HIGHEST: 2,
                ThreadPriority.TIME_CRITICAL: 15
            }
            
            kernel32 = ctypes.windll.kernel32
            thread_handle = kernel32.GetCurrentThread()
            priority_value = priority_map.get(self._priority, 0)
            
            kernel32.SetThreadPriority(thread_handle, priority_value)
            
        except Exception as e:
            print(f"優先度設定エラー: {e}")
    
    def pause(self):
        """スレッドを一時停止"""
        self._pause_event.clear()
    
    def resume(self):
        """スレッドを再開"""
        self._pause_event.set()
    
    def cancel(self):
        """スレッドをキャンセル"""
        self._cancelled = True
        self.resume()  # 一時停止中の場合は再開してから終了
    
    def get_result(self) -> ThreadResult:
        """実行結果を取得"""
        execution_time = time.time() - self._start_time if self._start_time > 0 else 0.0
        
        if self._error:
            state = ThreadState.FAILED
        elif self._cancelled:
            state = ThreadState.CANCELLED
        elif not self.isFinished():
            state = ThreadState.RUNNING
        else:
            state = ThreadState.COMPLETED
        
        return ThreadResult(
            thread_id=self.thread_id,
            result=self._result,
            error=self._error,
            execution_time=execution_time,
            state=state
        )


class ThreadManager(IThreadManager):
    """
    スレッド管理クラス
    
    Windows環境でのマルチスレッド処理を安全に管理し、
    UIスレッドとの適切な分離を実現します。
    """
    
    def __init__(self, max_workers: int = 4, queue_size: int = 100):
        self.max_workers = max_workers
        self.active_threads: Dict[str, WorkerThread] = {}
        self.completed_threads: List[ThreadResult] = []
        self._lock = threading.RLock()
        
        # スレッドプール（CPU集約的タスク用）
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="ThreadManager"
        )
        
        # 非同期タスクキュー
        self._task_queue: queue.Queue = queue.Queue(maxsize=queue_size)
        self._is_shutdown = False
        
        # Windows環境でのリソース管理
        self._weak_refs: weakref.WeakSet = weakref.WeakSet()
        
        # Qt統合（利用可能な場合）
        if QT_AVAILABLE:
            self._qt_timer = QTimer()
            self._qt_timer.timeout.connect(self._cleanup_completed_threads)
            self._qt_timer.start(5000)  # 5秒間隔でクリーンアップ
    
    def run_in_background(self, task: Callable[[], T], 
                         thread_name: str = None,
                         priority: ThreadPriority = ThreadPriority.NORMAL,
                         timeout: Optional[float] = None) -> Future[T]:
        """
        バックグラウンドタスクを実行
        
        Args:
            task: 実行するタスク
            thread_name: スレッド名
            priority: スレッド優先度
            timeout: タイムアウト時間（秒）
            
        Returns:
            Future オブジェクト
        """
        if self._is_shutdown:
            raise RuntimeError("ThreadManagerは既にシャットダウンされています")
        
        # タイムアウト付きタスクのラップ
        def wrapped_task():
            if timeout:
                result_queue = queue.Queue()
                exception_queue = queue.Queue()
                
                def target():
                    try:
                        result = task()
                        result_queue.put(result)
                    except Exception as e:
                        exception_queue.put(e)
                
                thread = threading.Thread(target=target, name=thread_name)
                thread.start()
                thread.join(timeout)
                
                if thread.is_alive():
                    # タイムアウト処理（Windowsではタスクマネージャーから強制終了）
                    raise TimeoutError(f"タスクがタイムアウトしました ({timeout}秒)")
                
                if not exception_queue.empty():
                    raise exception_queue.get()
                
                if not result_queue.empty():
                    return result_queue.get()
                
                raise RuntimeError("タスクが予期せず終了しました")
            else:
                return task()
        
        return self._executor.submit(wrapped_task)
    
    def run_with_callback(self, task: Callable, 
                         callback: Optional[Callable] = None,
                         error_callback: Optional[Callable] = None,
                         thread_name: str = None,
                         priority: ThreadPriority = ThreadPriority.NORMAL) -> str:
        """
        コールバック付きタスクを実行
        
        Args:
            task: 実行するタスク
            callback: 成功時のコールバック
            error_callback: エラー時のコールバック
            thread_name: スレッド名
            priority: スレッド優先度
            
        Returns:
            スレッドID
        """
        if self._is_shutdown:
            raise RuntimeError("ThreadManagerは既にシャットダウンされています")
        
        worker = WorkerThread(task, thread_name=thread_name, priority=priority)
        
        # コールバック接続
        if QT_AVAILABLE:
            if callback:
                worker.result_ready.connect(callback)
            if error_callback:
                worker.error_occurred.connect(error_callback)
            
            # 完了時のクリーンアップ
            worker.finished.connect(
                lambda: self._on_thread_finished(worker.thread_id)
            )
        
        # スレッド管理に追加
        with self._lock:
            self.active_threads[worker.thread_id] = worker
        
        self._weak_refs.add(worker)
        worker.start()
        
        return worker.thread_id
    
    def run_async_task(self, coro_func: Callable, 
                      loop: Optional[asyncio.AbstractEventLoop] = None) -> Future:
        """
        非同期タスクを実行
        
        Args:
            coro_func: 非同期関数
            loop: イベントループ（指定しない場合は新規作成）
            
        Returns:
            Future オブジェクト
        """
        def run_async():
            if loop:
                return loop.run_until_complete(coro_func())
            else:
                # Windows環境での新しいイベントループ作成
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(coro_func())
                finally:
                    new_loop.close()
        
        return self.run_in_background(run_async)
    
    def pause_thread(self, thread_id: str) -> bool:
        """スレッドを一時停止"""
        with self._lock:
            if thread_id in self.active_threads:
                self.active_threads[thread_id].pause()
                return True
        return False
    
    def resume_thread(self, thread_id: str) -> bool:
        """スレッドを再開"""
        with self._lock:
            if thread_id in self.active_threads:
                self.active_threads[thread_id].resume()
                return True
        return False
    
    def cancel_thread(self, thread_id: str) -> bool:
        """スレッドをキャンセル"""
        with self._lock:
            if thread_id in self.active_threads:
                self.active_threads[thread_id].cancel()
                return True
        return False
    
    def get_thread_status(self, thread_id: str) -> Optional[ThreadResult]:
        """スレッド状態を取得"""
        with self._lock:
            if thread_id in self.active_threads:
                return self.active_threads[thread_id].get_result()
            
            # 完了済みスレッドからも検索
            for result in self.completed_threads:
                if result.thread_id == thread_id:
                    return result
        
        return None
    
    def get_active_threads(self) -> List[str]:
        """アクティブなスレッドID一覧を取得"""
        with self._lock:
            return list(self.active_threads.keys())
    
    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """すべてのスレッド完了を待機"""
        start_time = time.time()
        
        while True:
            with self._lock:
                if not self.active_threads:
                    return True
            
            if timeout and (time.time() - start_time) > timeout:
                return False
            
            time.sleep(0.1)
    
    def _on_thread_finished(self, thread_id: str):
        """スレッド完了時の処理"""
        with self._lock:
            if thread_id in self.active_threads:
                worker = self.active_threads[thread_id]
                result = worker.get_result()
                
                # 完了済みリストに移動
                self.completed_threads.append(result)
                del self.active_threads[thread_id]
                
                # 古い結果のクリーンアップ（最新100件のみ保持）
                if len(self.completed_threads) > 100:
                    self.completed_threads = self.completed_threads[-100:]
    
    def _cleanup_completed_threads(self):
        """完了済みスレッドのクリーンアップ"""
        current_time = time.time()
        
        with self._lock:
            # 1時間以上前の結果を削除
            self.completed_threads = [
                result for result in self.completed_threads
                if (current_time - result.execution_time) < 3600
            ]
    
    def shutdown(self, timeout: float = 30.0) -> bool:
        """
        スレッドマネージャーをシャットダウン
        
        Args:
            timeout: タイムアウト時間（秒）
            
        Returns:
            正常にシャットダウンできた場合True
        """
        if self._is_shutdown:
            return True
        
        self._is_shutdown = True
        
        # Qtタイマー停止
        if QT_AVAILABLE and hasattr(self, '_qt_timer'):
            self._qt_timer.stop()
        
        # アクティブスレッドのキャンセル
        with self._lock:
            for worker in self.active_threads.values():
                worker.cancel()
        
        # 完了待機
        success = self.wait_for_completion(timeout)
        
        # スレッドプールシャットダウン
        self._executor.shutdown(wait=True)
        
        # リソースクリーンアップ
        with self._lock:
            self.active_threads.clear()
            self.completed_threads.clear()
            self._weak_refs.clear()
        
        return success
    
    def __enter__(self):
        """コンテキストマネージャー対応"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャー対応"""
        self.shutdown()


# グローバルスレッドマネージャー
_global_thread_manager: Optional[ThreadManager] = None
_thread_manager_lock = threading.Lock()


def get_thread_manager() -> ThreadManager:
    """
    グローバルスレッドマネージャーインスタンスを取得
    
    Returns:
        シングルトンスレッドマネージャーインスタンス
    """
    global _global_thread_manager
    
    if _global_thread_manager is None:
        with _thread_manager_lock:
            if _global_thread_manager is None:
                _global_thread_manager = ThreadManager()
    
    return _global_thread_manager


# アプリケーション終了時のクリーンアップ
import atexit

def _cleanup_thread_manager():
    """スレッドマネージャークリーンアップ"""
    global _global_thread_manager
    if _global_thread_manager:
        _global_thread_manager.shutdown()
        _global_thread_manager = None

atexit.register(_cleanup_thread_manager)


# 便利関数
def run_background_task(task: Callable[[], T], 
                       timeout: Optional[float] = None) -> Future[T]:
    """バックグラウンドタスクを簡単に実行"""
    return get_thread_manager().run_in_background(task, timeout=timeout)


def run_with_progress(task: Callable, 
                     progress_callback: Optional[Callable] = None,
                     completion_callback: Optional[Callable] = None) -> str:
    """進捗表示付きタスクを実行"""
    return get_thread_manager().run_with_callback(
        task, 
        callback=completion_callback,
        error_callback=lambda error: print(f"タスクエラー: {error}")
    )