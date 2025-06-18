"""
Result パターン実装 - 関数型エラーハンドリング

例外ではなくResultパターンを使用して、より安全で予測可能な
エラーハンドリングを実現します。Windows環境でのエラー分類も含みます。
"""

from typing import TypeVar, Generic, Union, Callable, Optional, Any, Type
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum
import traceback
import sys

T = TypeVar('T')  # 成功値の型
E = TypeVar('E')  # エラー値の型
U = TypeVar('U')  # 変換後の型


class ResultType(Enum):
    """Result型の種類"""
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass(frozen=True)
class Success(Generic[T]):
    """
    成功結果を表すクラス
    
    Attributes:
        value: 成功値
    """
    value: T
    
    def is_success(self) -> bool:
        """成功かどうかを判定"""
        return True
    
    def is_failure(self) -> bool:
        """失敗かどうかを判定"""
        return False
    
    def unwrap(self) -> T:
        """成功値を取得"""
        return self.value
    
    def unwrap_or(self, default: T) -> T:
        """成功値を取得（失敗時はデフォルト値）"""
        return self.value
    
    def map(self, func: Callable[[T], U]) -> 'Success[U]':
        """成功値を変換"""
        return Success(func(self.value))
    
    def map_error(self, func: Callable[[Any], Any]) -> 'Success[T]':
        """エラー変換（成功時は何もしない）"""
        return self
    
    def and_then(self, func: Callable[[T], 'Result[U, E]']) -> 'Result[U, E]':
        """モナド的チェーン操作"""
        return func(self.value)
    
    def or_else(self, func: Callable[[Any], 'Result[T, E]']) -> 'Success[T]':
        """エラー時の代替処理（成功時は何もしない）"""
        return self


@dataclass(frozen=True)
class Failure(Generic[E]):
    """
    失敗結果を表すクラス
    
    Attributes:
        error: エラー値
        error_type: エラータイプ（オプション）
        stack_trace: スタックトレース（オプション）
    """
    error: E
    error_type: Optional[str] = None
    stack_trace: Optional[str] = None
    
    def is_success(self) -> bool:
        """成功かどうかを判定"""
        return False
    
    def is_failure(self) -> bool:
        """失敗かどうかを判定"""
        return True
    
    def unwrap(self) -> Any:
        """失敗時の値取得（例外発生）"""
        error_msg = f"Failure値のunwrapが呼ばれました: {self.error}"
        if self.stack_trace:
            error_msg += f"\nスタックトレース:\n{self.stack_trace}"
        raise RuntimeError(error_msg)
    
    def unwrap_or(self, default: T) -> T:
        """デフォルト値を取得"""
        return default
    
    def map(self, func: Callable[[Any], Any]) -> 'Failure[E]':
        """値変換（失敗時は何もしない）"""
        return self
    
    def map_error(self, func: Callable[[E], U]) -> 'Failure[U]':
        """エラー値を変換"""
        return Failure(
            error=func(self.error),
            error_type=self.error_type,
            stack_trace=self.stack_trace
        )
    
    def and_then(self, func: Callable[[Any], 'Result[U, E]']) -> 'Failure[E]':
        """モナド的チェーン操作（失敗時は何もしない）"""
        return self
    
    def or_else(self, func: Callable[[E], 'Result[T, E]']) -> 'Result[T, E]':
        """エラー時の代替処理"""
        return func(self.error)


# Result型の定義
Result = Union[Success[T], Failure[E]]

# 便利な型エイリアス（Python 3.13対応）
def result_type(success_type: Type[T], error_type: Type[E] = str) -> type:
    """Result型を作成するヘルパー関数"""
    return Union[Success[success_type], Failure[error_type]]


class WindowsErrorCode:
    """Windows固有のエラーコード"""
    
    # システムエラー
    ACCESS_DENIED = "ERROR_ACCESS_DENIED"
    FILE_NOT_FOUND = "ERROR_FILE_NOT_FOUND"
    PATH_NOT_FOUND = "ERROR_PATH_NOT_FOUND"
    DISK_FULL = "ERROR_DISK_FULL"
    SHARING_VIOLATION = "ERROR_SHARING_VIOLATION"
    
    # アプリケーションエラー
    PERMISSION_DENIED = "permission_denied"
    DEVICE_NOT_FOUND = "device_not_found"
    STORAGE_FULL = "storage_full"
    INVALID_CONFIGURATION = "invalid_configuration"
    NETWORK_ERROR = "network_error"
    
    # RPAエラー
    RECORDING_FAILED = "recording_failed"
    PLAYBACK_FAILED = "playback_failed"
    SCHEDULER_ERROR = "scheduler_error"
    UI_AUTOMATION_ERROR = "ui_automation_error"
    
    # セキュリティエラー
    ENCRYPTION_ERROR = "encryption_error"
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"


@dataclass(frozen=True)
class ErrorInfo:
    """詳細なエラー情報"""
    code: str
    message: str
    details: Optional[str] = None
    inner_error: Optional[Exception] = None
    context: Optional[dict] = None


class ResultBuilder:
    """Result作成のためのビルダークラス"""
    
    @staticmethod
    def success(value: T) -> Success[T]:
        """成功結果を作成"""
        return Success(value)
    
    @staticmethod
    def failure(error: E, error_type: Optional[str] = None, 
               capture_stack: bool = True) -> Failure[E]:
        """失敗結果を作成"""
        stack_trace = None
        if capture_stack:
            stack_trace = traceback.format_exc() if sys.exc_info()[0] else None
        
        return Failure(
            error=error,
            error_type=error_type,
            stack_trace=stack_trace
        )
    
    @staticmethod
    def from_exception(exception: Exception, 
                      error_code: Optional[str] = None) -> Failure[ErrorInfo]:
        """例外からFailureを作成"""
        error_info = ErrorInfo(
            code=error_code or type(exception).__name__,
            message=str(exception),
            inner_error=exception,
            context={"exception_type": type(exception).__name__}
        )
        
        return Failure(
            error=error_info,
            error_type=error_code,
            stack_trace=traceback.format_exc()
        )
    
    @staticmethod
    def from_windows_error(win_error_code: int, 
                          message: str) -> Failure[ErrorInfo]:
        """Windows APIエラーからFailureを作成"""
        # Windows固有のエラーコード変換
        code_map = {
            5: WindowsErrorCode.ACCESS_DENIED,
            2: WindowsErrorCode.FILE_NOT_FOUND,
            3: WindowsErrorCode.PATH_NOT_FOUND,
            32: WindowsErrorCode.SHARING_VIOLATION,
        }
        
        error_code = code_map.get(win_error_code, f"WIN_ERROR_{win_error_code}")
        
        error_info = ErrorInfo(
            code=error_code,
            message=message,
            context={"windows_error_code": win_error_code}
        )
        
        return Failure(error=error_info, error_type="windows_api_error")


def try_catch(func: Callable[[], T], 
              error_code: Optional[str] = None) -> Result[T, ErrorInfo]:
    """
    例外をキャッチしてResultに変換するデコレータ風関数
    
    Args:
        func: 実行する関数
        error_code: エラーコード
        
    Returns:
        実行結果のResult
    """
    try:
        result = func()
        return ResultBuilder.success(result)
    except Exception as e:
        return ResultBuilder.from_exception(e, error_code)


def async_try_catch(coro_func: Callable[[], Any], 
                   error_code: Optional[str] = None):
    """
    非同期関数用の例外キャッチ
    
    Args:
        coro_func: 実行する非同期関数
        error_code: エラーコード
        
    Returns:
        実行結果のResult
    """
    import asyncio
    
    async def wrapper():
        try:
            result = await coro_func()
            return ResultBuilder.success(result)
        except Exception as e:
            return ResultBuilder.from_exception(e, error_code)
    
    return wrapper()


class ResultExtensions:
    """Result型の拡張メソッド"""
    
    @staticmethod
    def combine(*results: Result[Any, E]) -> Result[list, E]:
        """
        複数のResultを結合
        すべて成功の場合のみ成功、ひとつでも失敗があれば失敗
        """
        values = []
        for result in results:
            if result.is_failure():
                return result
            values.append(result.unwrap())
        
        return ResultBuilder.success(values)
    
    @staticmethod
    def first_success(*results: Result[T, E]) -> Result[T, E]:
        """最初に成功したResultを返す"""
        last_failure = None
        
        for result in results:
            if result.is_success():
                return result
            last_failure = result
        
        return last_failure or ResultBuilder.failure("No results provided")
    
    @staticmethod
    def retry(func: Callable[[], Result[T, E]], 
             max_attempts: int = 3, 
             delay_seconds: float = 0.5) -> Result[T, E]:
        """
        指定回数までリトライ実行
        
        Args:
            func: 実行する関数
            max_attempts: 最大試行回数
            delay_seconds: リトライ間隔（秒）
            
        Returns:
            最終実行結果
        """
        import time
        
        last_result = None
        
        for attempt in range(max_attempts):
            result = func()
            if result.is_success():
                return result
            
            last_result = result
            
            if attempt < max_attempts - 1:  # 最後の試行でなければ待機
                time.sleep(delay_seconds)
        
        return last_result or ResultBuilder.failure("Retry failed with no results")


# 便利関数
def Ok(value: T) -> Success[T]:
    """成功結果を作成する短縮関数"""
    return ResultBuilder.success(value)


def Err(error: E, error_type: Optional[str] = None) -> Failure[E]:
    """失敗結果を作成する短縮関数"""
    return ResultBuilder.failure(error, error_type)


# 型エイリアス（Python 3.13対応）
StrResult = Union[Success[str], Failure[str]]
IntResult = Union[Success[int], Failure[str]]
BoolResult = Union[Success[bool], Failure[str]]
ErrorResult = Union[Success[Any], Failure[ErrorInfo]]

# より具体的な型エイリアス
def ResultOf(success_type, error_type=str):
    """具体的なResult型を作成"""
    return Union[Success[success_type], Failure[error_type]]