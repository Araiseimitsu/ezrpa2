"""
Schedule リポジトリインターフェース

スケジュールデータの永続化を抽象化するリポジトリパターンの実装。
Windows環境でのタスクスケジューラ連携を含む設計です。
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from ..entities.schedule import Schedule, ExecutionResult
from ..value_objects import ScheduleStatus, TriggerType, ValidationResult
from ...core.result import Result, ErrorInfo


class IScheduleRepository(ABC):
    """
    Schedule リポジトリインターフェース
    
    スケジュールの永続化操作を定義する抽象基底クラス。
    Windows環境でのタスクスケジューラ統合も考慮した設計です。
    """
    
    @abstractmethod
    async def save(self, schedule: Schedule) -> Result[str, ErrorInfo]:
        """
        スケジュールを保存
        
        Args:
            schedule: 保存するスケジュール
            
        Returns:
            保存されたスケジュールIDまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, schedule_id: str) -> Result[Schedule, ErrorInfo]:
        """
        IDでスケジュールを取得
        
        Args:
            schedule_id: スケジュールID
            
        Returns:
            スケジュールまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def get_by_recording_id(self, recording_id: str) -> Result[List[Schedule], ErrorInfo]:
        """
        レコーディングIDでスケジュールを取得
        
        Args:
            recording_id: レコーディングID
            
        Returns:
            該当スケジュールリストまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def get_all(self) -> Result[List[Schedule], ErrorInfo]:
        """
        全スケジュールを取得
        
        Returns:
            スケジュールリストまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def get_active_schedules(self) -> Result[List[Schedule], ErrorInfo]:
        """
        アクティブなスケジュールを取得
        
        Returns:
            アクティブスケジュールリストまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def get_schedules_due_for_execution(self, 
                                            current_time: Optional[datetime] = None) -> Result[List[Schedule], ErrorInfo]:
        """
        実行予定のスケジュールを取得
        
        Args:
            current_time: 現在時刻（None=現在時刻を使用）
            
        Returns:
            実行予定スケジュールリストまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def get_by_trigger_type(self, trigger_type: TriggerType) -> Result[List[Schedule], ErrorInfo]:
        """
        トリガータイプでスケジュールを取得
        
        Args:
            trigger_type: トリガータイプ
            
        Returns:
            該当スケジュールリストまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def update(self, schedule: Schedule) -> Result[bool, ErrorInfo]:
        """
        スケジュールを更新
        
        Args:
            schedule: 更新するスケジュール
            
        Returns:
            更新成功フラグまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def delete(self, schedule_id: str) -> Result[bool, ErrorInfo]:
        """
        スケジュールを削除
        
        Args:
            schedule_id: 削除するスケジュールID
            
        Returns:
            削除成功フラグまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def exists(self, schedule_id: str) -> Result[bool, ErrorInfo]:
        """
        スケジュールの存在確認
        
        Args:
            schedule_id: 確認するスケジュールID
            
        Returns:
            存在フラグまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def count_by_status(self, status: ScheduleStatus) -> Result[int, ErrorInfo]:
        """
        ステータス別スケジュール数を取得
        
        Args:
            status: スケジュールステータス
            
        Returns:
            該当スケジュール数またはエラー情報
        """
        pass
    
    # 実行履歴管理
    @abstractmethod
    async def add_execution_result(self, schedule_id: str, 
                                 execution_result: ExecutionResult) -> Result[bool, ErrorInfo]:
        """
        実行結果を追加
        
        Args:
            schedule_id: スケジュールID
            execution_result: 実行結果
            
        Returns:
            追加成功フラグまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def get_execution_history(self, schedule_id: str, 
                                  limit: Optional[int] = None) -> Result[List[ExecutionResult], ErrorInfo]:
        """
        実行履歴を取得
        
        Args:
            schedule_id: スケジュールID
            limit: 取得件数制限
            
        Returns:
            実行履歴リストまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def cleanup_old_execution_history(self, 
                                          older_than_days: int = 90) -> Result[int, ErrorInfo]:
        """
        古い実行履歴をクリーンアップ
        
        Args:
            older_than_days: 保持日数
            
        Returns:
            削除された履歴数またはエラー情報
        """
        pass
    
    # Windows環境固有機能
    @abstractmethod
    async def sync_with_windows_task_scheduler(self, schedule_id: str) -> Result[bool, ErrorInfo]:
        """
        Windowsタスクスケジューラーと同期
        
        Args:
            schedule_id: 同期するスケジュールID
            
        Returns:
            同期成功フラグまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def register_windows_task(self, schedule: Schedule) -> Result[str, ErrorInfo]:
        """
        Windowsタスクとして登録
        
        Args:
            schedule: 登録するスケジュール
            
        Returns:
            WindowsタスクIDまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def unregister_windows_task(self, schedule_id: str) -> Result[bool, ErrorInfo]:
        """
        Windowsタスクの登録解除
        
        Args:
            schedule_id: 解除するスケジュールID
            
        Returns:
            解除成功フラグまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def get_windows_task_status(self, schedule_id: str) -> Result[Dict[str, Any], ErrorInfo]:
        """
        Windowsタスクのステータスを取得
        
        Args:
            schedule_id: スケジュールID
            
        Returns:
            タスクステータス情報またはエラー情報
        """
        pass


class IScheduleQueryBuilder(ABC):
    """
    Schedule クエリビルダーインターフェース
    
    複雑な検索条件を組み立てるためのビルダーパターン実装。
    """
    
    @abstractmethod
    def where_name_contains(self, text: str) -> 'IScheduleQueryBuilder':
        """名前に指定テキストを含む"""
        pass
    
    @abstractmethod
    def where_status(self, status: ScheduleStatus) -> 'IScheduleQueryBuilder':
        """指定ステータス"""
        pass
    
    @abstractmethod
    def where_recording_id(self, recording_id: str) -> 'IScheduleQueryBuilder':
        """指定レコーディングID"""
        pass
    
    @abstractmethod
    def where_trigger_type(self, trigger_type: TriggerType) -> 'IScheduleQueryBuilder':
        """指定トリガータイプ"""
        pass
    
    @abstractmethod
    def where_enabled(self, enabled: bool = True) -> 'IScheduleQueryBuilder':
        """有効/無効フィルター"""
        pass
    
    @abstractmethod
    def where_next_execution_before(self, date: datetime) -> 'IScheduleQueryBuilder':
        """次回実行が指定日時以前"""
        pass
    
    @abstractmethod
    def where_next_execution_after(self, date: datetime) -> 'IScheduleQueryBuilder':
        """次回実行が指定日時以降"""
        pass
    
    @abstractmethod
    def where_success_rate_greater_than(self, rate: float) -> 'IScheduleQueryBuilder':
        """成功率が指定値より大きい"""
        pass
    
    @abstractmethod
    def order_by_name(self, ascending: bool = True) -> 'IScheduleQueryBuilder':
        """名前順ソート"""
        pass
    
    @abstractmethod
    def order_by_next_execution(self, ascending: bool = True) -> 'IScheduleQueryBuilder':
        """次回実行時刻順ソート"""
        pass
    
    @abstractmethod
    def order_by_success_rate(self, ascending: bool = False) -> 'IScheduleQueryBuilder':
        """成功率順ソート"""
        pass
    
    @abstractmethod
    def limit(self, count: int) -> 'IScheduleQueryBuilder':
        """結果数制限"""
        pass
    
    @abstractmethod
    async def execute(self) -> Result[List[Schedule], ErrorInfo]:
        """クエリを実行"""
        pass
    
    @abstractmethod
    async def count(self) -> Result[int, ErrorInfo]:
        """該当件数を取得"""
        pass


class IScheduleEventHandler(ABC):
    """
    Schedule イベントハンドラーインターフェース
    
    スケジュール操作に関するイベント処理を定義。
    """
    
    @abstractmethod
    async def on_schedule_created(self, schedule: Schedule) -> None:
        """スケジュール作成時"""
        pass
    
    @abstractmethod
    async def on_schedule_activated(self, schedule: Schedule) -> None:
        """スケジュール有効化時"""
        pass
    
    @abstractmethod
    async def on_schedule_deactivated(self, schedule: Schedule) -> None:
        """スケジュール無効化時"""
        pass
    
    @abstractmethod
    async def on_schedule_executed(self, schedule: Schedule, 
                                 execution_result: ExecutionResult) -> None:
        """スケジュール実行時"""
        pass
    
    @abstractmethod
    async def on_schedule_failed(self, schedule: Schedule, 
                               error_message: str) -> None:
        """スケジュール実行失敗時"""
        pass
    
    @abstractmethod
    async def on_schedule_deleted(self, schedule_id: str) -> None:
        """スケジュール削除時"""
        pass


# 検索・フィルター用の型定義
class ScheduleFilter:
    """スケジュールフィルター条件"""
    
    def __init__(self):
        self.name_pattern: Optional[str] = None
        self.status_list: Optional[List[ScheduleStatus]] = None
        self.trigger_type_list: Optional[List[TriggerType]] = None
        self.recording_id: Optional[str] = None
        self.enabled_only: Optional[bool] = None
        self.next_execution_before: Optional[datetime] = None
        self.next_execution_after: Optional[datetime] = None
        self.min_success_rate: Optional[float] = None
        self.max_success_rate: Optional[float] = None
        self.has_execution_history: Optional[bool] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = {}
        
        if self.name_pattern:
            data['name_pattern'] = self.name_pattern
        
        if self.status_list:
            data['status_list'] = [status.value for status in self.status_list]
        
        if self.trigger_type_list:
            data['trigger_type_list'] = [t.value for t in self.trigger_type_list]
        
        if self.recording_id:
            data['recording_id'] = self.recording_id
        
        if self.enabled_only is not None:
            data['enabled_only'] = self.enabled_only
        
        if self.next_execution_before:
            data['next_execution_before'] = self.next_execution_before.isoformat()
        
        if self.next_execution_after:
            data['next_execution_after'] = self.next_execution_after.isoformat()
        
        if self.min_success_rate is not None:
            data['min_success_rate'] = self.min_success_rate
        
        if self.max_success_rate is not None:
            data['max_success_rate'] = self.max_success_rate
        
        if self.has_execution_history is not None:
            data['has_execution_history'] = self.has_execution_history
        
        return data


class ScheduleSortOrder:
    """スケジュールソート順序"""
    
    def __init__(self, field: str, ascending: bool = True):
        self.field = field
        self.ascending = ascending
    
    @classmethod
    def by_name(cls, ascending: bool = True) -> 'ScheduleSortOrder':
        return cls('name', ascending)
    
    @classmethod
    def by_next_execution(cls, ascending: bool = True) -> 'ScheduleSortOrder':
        return cls('next_execution_time', ascending)
    
    @classmethod
    def by_created_date(cls, ascending: bool = True) -> 'ScheduleSortOrder':
        return cls('created_at', ascending)
    
    @classmethod
    def by_success_rate(cls, ascending: bool = False) -> 'ScheduleSortOrder':
        return cls('success_rate', ascending)
    
    @classmethod
    def by_total_executions(cls, ascending: bool = False) -> 'ScheduleSortOrder':
        return cls('total_executions', ascending)


class ScheduleStatistics:
    """スケジュール統計情報"""
    
    def __init__(self):
        self.total_count: int = 0
        self.active_count: int = 0
        self.inactive_count: int = 0
        self.running_count: int = 0
        self.failed_count: int = 0
        self.total_executions: int = 0
        self.successful_executions: int = 0
        self.average_success_rate: float = 0.0
        self.next_scheduled_execution: Optional[datetime] = None
        self.most_executed_schedule_id: Optional[str] = None
        self.trigger_type_distribution: Dict[str, int] = {}
    
    @property
    def overall_success_rate(self) -> float:
        """全体成功率"""
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = {
            'total_count': self.total_count,
            'active_count': self.active_count,
            'inactive_count': self.inactive_count,
            'running_count': self.running_count,
            'failed_count': self.failed_count,
            'total_executions': self.total_executions,
            'successful_executions': self.successful_executions,
            'average_success_rate': self.average_success_rate,
            'overall_success_rate': self.overall_success_rate,
            'most_executed_schedule_id': self.most_executed_schedule_id,
            'trigger_type_distribution': self.trigger_type_distribution
        }
        
        if self.next_scheduled_execution:
            data['next_scheduled_execution'] = self.next_scheduled_execution.isoformat()
        
        return data