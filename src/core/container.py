"""
依存性注入コンテナ - Dependency Injection Container

Windows環境でのサービス管理とライフサイクル制御を提供します。
クリーンアーキテクチャにおける依存関係の逆転を実現します。
"""

from typing import Dict, Type, TypeVar, Callable, Any, Optional, cast
from abc import ABC, abstractmethod
import threading
import weakref
from pathlib import Path
import os

T = TypeVar('T')


class IContainer(ABC):
    """依存性注入コンテナのインターフェース"""
    
    @abstractmethod
    def register(self, interface: Type[T], implementation: Callable[[], T], 
                singleton: bool = False) -> None:
        """サービスを登録"""
        pass
    
    @abstractmethod
    def register_instance(self, interface: Type[T], instance: T) -> None:
        """インスタンスを直接登録"""
        pass
    
    @abstractmethod
    def get(self, interface: Type[T]) -> T:
        """サービスを取得"""
        pass
    
    @abstractmethod
    def is_registered(self, interface: Type[T]) -> bool:
        """サービスが登録されているかチェック"""
        pass


class ServiceLifetime:
    """サービスライフタイム定数"""
    TRANSIENT = "transient"      # 毎回新しいインスタンス
    SINGLETON = "singleton"      # アプリケーション全体で1つ
    SCOPED = "scoped"           # スコープ内で1つ


class ServiceDescriptor:
    """サービス記述子"""
    
    def __init__(self, interface: Type, implementation: Callable, 
                 lifetime: str = ServiceLifetime.TRANSIENT):
        self.interface = interface
        self.implementation = implementation
        self.lifetime = lifetime
        self.instance: Optional[Any] = None


class Container(IContainer):
    """
    依存性注入コンテナ
    
    Windows環境でのスレッドセーフティとリソース管理を考慮した実装。
    シングルトンインスタンスの適切な破棄処理を含みます。
    """
    
    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._lock = threading.RLock()  # Windows環境での再帰的ロック
        self._scoped_instances: Dict[Type, Any] = {}
        self._is_disposed = False
        
        # Windows環境での適切なリソース管理
        self._weak_refs: weakref.WeakSet = weakref.WeakSet()
    
    def register(self, interface: Type[T], implementation: Callable[[], T], 
                singleton: bool = False) -> None:
        """
        サービスを登録
        
        Args:
            interface: サービスインターフェース
            implementation: 実装ファクトリ
            singleton: シングルトンとして登録するか
        
        Raises:
            RuntimeError: コンテナが破棄済みの場合
            ValueError: 無効な引数の場合
        """
        if self._is_disposed:
            raise RuntimeError("コンテナは既に破棄されています")
        
        if not interface or not implementation:
            raise ValueError("インターフェースと実装は必須です")
        
        lifetime = ServiceLifetime.SINGLETON if singleton else ServiceLifetime.TRANSIENT
        
        with self._lock:
            descriptor = ServiceDescriptor(interface, implementation, lifetime)
            self._services[interface] = descriptor
    
    def register_instance(self, interface: Type[T], instance: T) -> None:
        """
        インスタンスを直接登録
        
        Args:
            interface: サービスインターフェース
            instance: 登録するインスタンス
        """
        if self._is_disposed:
            raise RuntimeError("コンテナは既に破棄されています")
        
        if not interface or instance is None:
            raise ValueError("インターフェースとインスタンスは必須です")
        
        with self._lock:
            descriptor = ServiceDescriptor(interface, lambda: instance, 
                                         ServiceLifetime.SINGLETON)
            descriptor.instance = instance
            self._services[interface] = descriptor
            
            # Windows環境でのメモリリーク防止
            if hasattr(instance, '__del__'):
                self._weak_refs.add(instance)
    
    def get(self, interface: Type[T]) -> T:
        """
        サービスを取得
        
        Args:
            interface: 取得するサービスのインターフェース
            
        Returns:
            サービスインスタンス
            
        Raises:
            RuntimeError: サービスが登録されていない場合
        """
        if self._is_disposed:
            raise RuntimeError("コンテナは既に破棄されています")
        
        with self._lock:
            if interface not in self._services:
                raise RuntimeError(f"サービス {interface.__name__} が登録されていません")
            
            descriptor = self._services[interface]
            
            if descriptor.lifetime == ServiceLifetime.SINGLETON:
                if descriptor.instance is None:
                    descriptor.instance = descriptor.implementation()
                    if hasattr(descriptor.instance, '__del__'):
                        self._weak_refs.add(descriptor.instance)
                return cast(T, descriptor.instance)
            
            elif descriptor.lifetime == ServiceLifetime.SCOPED:
                if interface not in self._scoped_instances:
                    self._scoped_instances[interface] = descriptor.implementation()
                return cast(T, self._scoped_instances[interface])
            
            else:  # TRANSIENT
                return cast(T, descriptor.implementation())
    
    def is_registered(self, interface: Type[T]) -> bool:
        """
        サービスが登録されているかチェック
        
        Args:
            interface: チェックするインターフェース
            
        Returns:
            登録されている場合True
        """
        with self._lock:
            return interface in self._services
    
    def clear_scoped(self) -> None:
        """スコープ付きインスタンスをクリア"""
        with self._lock:
            self._scoped_instances.clear()
    
    def dispose(self) -> None:
        """
        コンテナを破棄し、リソースをクリーンアップ
        Windows環境での適切なリソース解放を行います。
        """
        if self._is_disposed:
            return
        
        with self._lock:
            self._is_disposed = True
            
            # シングルトンインスタンスの破棄
            for descriptor in self._services.values():
                if descriptor.instance and hasattr(descriptor.instance, 'dispose'):
                    try:
                        descriptor.instance.dispose()
                    except Exception as e:
                        # ログに記録（将来的にloggerサービスを使用）
                        print(f"サービス破棄エラー: {e}")
            
            # スコープ付きインスタンスの破棄
            for instance in self._scoped_instances.values():
                if hasattr(instance, 'dispose'):
                    try:
                        instance.dispose()
                    except Exception as e:
                        print(f"スコープ付きサービス破棄エラー: {e}")
            
            self._services.clear()
            self._scoped_instances.clear()
            self._weak_refs.clear()
    
    def __enter__(self):
        """コンテキストマネージャー対応"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャー対応"""
        self.dispose()


class WindowsServiceRegistry:
    """
    Windows環境固有のサービス登録補助クラス
    
    Windows APIやレジストリアクセスなど、プラットフォーム固有の
    サービスを登録するためのヘルパー機能を提供します。
    """
    
    @staticmethod
    def register_windows_services(container: Container) -> None:
        """Windows固有サービスを登録"""
        import sys
        
        if sys.platform != "win32":
            return
        
        # Windows環境でのみ利用可能なサービス
        try:
            # レジストリサービス（後で実装）
            # container.register(IRegistryService, lambda: WindowsRegistryService())
            
            # Windowsイベントログサービス（後で実装）
            # container.register(IEventLogService, lambda: WindowsEventLogService())
            
            pass  # 実装は後のフェーズで行う
            
        except ImportError:
            # Windows APIが利用できない場合はスキップ
            pass
    
    @staticmethod
    def get_windows_app_data_path() -> Path:
        """Windows AppDataフォルダーのパスを取得"""
        app_data = os.environ.get('APPDATA')
        if app_data:
            return Path(app_data) / "EZRPA"
        else:
            # フォールバック
            return Path.home() / ".ezrpa"


# グローバルコンテナインスタンス
_global_container: Optional[Container] = None
_container_lock = threading.Lock()


def get_container() -> Container:
    """
    グローバルコンテナインスタンスを取得
    
    Returns:
        シングルトンコンテナインスタンス
    """
    global _global_container
    
    if _global_container is None:
        with _container_lock:
            if _global_container is None:
                _global_container = Container()
                # Windows環境固有サービスの登録
                WindowsServiceRegistry.register_windows_services(_global_container)
    
    return _global_container


def dispose_container() -> None:
    """グローバルコンテナを破棄"""
    global _global_container
    
    if _global_container:
        with _container_lock:
            if _global_container:
                _global_container.dispose()
                _global_container = None


# Windows環境でのアプリケーション終了時のクリーンアップ
import atexit
atexit.register(dispose_container)