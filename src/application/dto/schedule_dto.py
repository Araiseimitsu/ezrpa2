"""
Schedule DTO - スケジュールデータ転送オブジェクト

スケジュールデータをレイヤー間で転送するためのDTOクラス群です。
スケジュール設定、実行結果、統計情報などの情報を含みます。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
from enum import Enum


@dataclass
class TriggerConditionDTO:
    """トリガー条件DTO"""
    trigger_type: str  # time, interval, file_watch, hotkey, startup, idle
    config: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> List[str]:
        """バリデーション"""
        errors = []
        
        valid_trigger_types = ["time", "interval", "file_watch", "hotkey", "startup", "idle"]
        if self.trigger_type not in valid_trigger_types:
            errors.append(f"トリガー種別は次のいずれかを指定してください: {', '.join(valid_trigger_types)}")
        
        # 種別ごとの設定チェック
        if self.trigger_type == "time":
            if "datetime" not in self.config:
                errors.append("時刻トリガーには実行日時の設定が必要です")
            elif isinstance(self.config["datetime"], str):
                try:
                    datetime.fromisoformat(self.config["datetime"])
                except ValueError:
                    errors.append("実行日時の形式が正しくありません")
        
        elif self.trigger_type == "interval":
            if "interval_seconds" not in self.config:
                errors.append("間隔トリガーには実行間隔の設定が必要です")
            elif not isinstance(self.config["interval_seconds"], (int, float)) or self.config["interval_seconds"] <= 0:
                errors.append("実行間隔は正の数値で指定してください")
        
        elif self.trigger_type == "file_watch":
            if "file_path" not in self.config:
                errors.append("ファイル監視トリガーには監視対象ファイルパスの設定が必要です")
            if "watch_type" not in self.config:
                errors.append("ファイル監視トリガーには監視種別の設定が必要です")
            elif self.config["watch_type"] not in ["created", "modified", "deleted", "any"]:
                errors.append("監視種別はcreated/modified/deleted/anyのいずれかを指定してください")
        
        elif self.trigger_type == "hotkey":
            if "key_combination" not in self.config:
                errors.append("ホットキートリガーにはキー組み合わせの設定が必要です")
        
        elif self.trigger_type == "idle":
            if "idle_minutes" not in self.config:
                errors.append("アイドルトリガーにはアイドル時間の設定が必要です")
            elif not isinstance(self.config["idle_minutes"], (int, float)) or self.config["idle_minutes"] <= 0:
                errors.append("アイドル時間は正の数値で指定してください")
        
        return errors


@dataclass
class RepeatConditionDTO:
    """繰り返し条件DTO"""
    enabled: bool = False
    repeat_type: str = "none"  # none, count, until_date, infinite
    config: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> List[str]:
        """バリデーション"""
        errors = []
        
        if self.enabled:
            valid_repeat_types = ["none", "count", "until_date", "infinite"]
            if self.repeat_type not in valid_repeat_types:
                errors.append(f"繰り返し種別は次のいずれかを指定してください: {', '.join(valid_repeat_types)}")
            
            if self.repeat_type == "count":
                if "count" not in self.config:
                    errors.append("回数指定繰り返しには実行回数の設定が必要です")
                elif not isinstance(self.config["count"], int) or self.config["count"] <= 0:
                    errors.append("実行回数は正の整数で指定してください")
            
            elif self.repeat_type == "until_date":
                if "end_date" not in self.config:
                    errors.append("日時指定繰り返しには終了日時の設定が必要です")
                elif isinstance(self.config["end_date"], str):
                    try:
                        end_date = datetime.fromisoformat(self.config["end_date"])
                        if end_date <= datetime.now():
                            errors.append("終了日時は現在時刻より後で指定してください")
                    except ValueError:
                        errors.append("終了日時の形式が正しくありません")
        
        return errors


@dataclass
class ExecutionResultDTO:
    """実行結果DTO"""
    execution_id: str
    schedule_id: str
    recording_id: str
    started_at: datetime
    completed_at: Optional[datetime]
    status: str  # running, completed, failed, cancelled
    success: bool
    error_message: Optional[str] = None
    actions_executed: int = 0
    total_actions: int = 0
    duration_seconds: float = 0.0
    logs: List[str] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)
    
    @property
    def is_running(self) -> bool:
        """実行中かどうか"""
        return self.status == "running"
    
    @property
    def completion_rate(self) -> float:
        """完了率"""
        if self.total_actions == 0:
            return 0.0
        return self.actions_executed / self.total_actions


@dataclass
class ScheduleDTO:
    """スケジュールDTO"""
    schedule_id: str
    name: str
    description: str
    recording_id: str
    recording_name: str
    status: str  # active, inactive, running, completed, failed
    is_active: bool
    trigger_condition: TriggerConditionDTO
    repeat_condition: RepeatConditionDTO
    created_at: datetime
    updated_at: datetime
    last_execution: Optional[datetime] = None
    next_execution: Optional[datetime] = None
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    
    @classmethod
    def from_domain(cls, schedule) -> 'ScheduleDTO':
        """ドメインオブジェクトからDTOを作成"""
        return cls(
            schedule_id=schedule.schedule_id,
            name=schedule.name,
            description=schedule.description,
            recording_id=schedule.recording_id,
            recording_name=getattr(schedule, 'recording_name', ''),
            status=schedule.status.value,
            is_active=schedule.is_active,
            trigger_condition=TriggerConditionDTO(
                trigger_type=schedule.trigger_condition.trigger_type.value,
                config=schedule.trigger_condition.to_dict()
            ),
            repeat_condition=RepeatConditionDTO(
                enabled=schedule.repeat_condition.enabled,
                repeat_type=schedule.repeat_condition.repeat_type.value if schedule.repeat_condition.enabled else "none",
                config=schedule.repeat_condition.to_dict()
            ),
            created_at=schedule.created_at,
            updated_at=schedule.updated_at,
            last_execution=schedule.last_execution,
            next_execution=schedule.get_next_execution_time(),
            execution_count=schedule.execution_count,
            success_count=schedule.success_count,
            failure_count=schedule.failure_count
        )
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.execution_count == 0:
            return 0.0
        return self.success_count / self.execution_count


@dataclass
class CreateScheduleDTO:
    """スケジュール作成用DTO"""
    name: str
    description: str
    recording_id: str
    trigger_condition: TriggerConditionDTO
    repeat_condition: RepeatConditionDTO = field(default_factory=lambda: RepeatConditionDTO())
    is_active: bool = True
    
    def validate(self) -> List[str]:
        """バリデーション"""
        errors = []
        
        if not self.name or not self.name.strip():
            errors.append("スケジュール名は必須です")
        elif len(self.name) > 255:
            errors.append("スケジュール名は255文字以内で入力してください")
        
        if self.description and len(self.description) > 1000:
            errors.append("説明は1000文字以内で入力してください")
        
        if not self.recording_id:
            errors.append("実行する記録の選択は必須です")
        
        # トリガー条件のバリデーション
        trigger_errors = self.trigger_condition.validate()
        errors.extend(trigger_errors)
        
        # 繰り返し条件のバリデーション
        repeat_errors = self.repeat_condition.validate()
        errors.extend(repeat_errors)
        
        return errors


@dataclass
class UpdateScheduleDTO:
    """スケジュール更新用DTO"""
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_condition: Optional[TriggerConditionDTO] = None
    repeat_condition: Optional[RepeatConditionDTO] = None
    is_active: Optional[bool] = None
    
    def validate(self) -> List[str]:
        """バリデーション"""
        errors = []
        
        if self.name is not None:
            if not self.name.strip():
                errors.append("スケジュール名は空にできません")
            elif len(self.name) > 255:
                errors.append("スケジュール名は255文字以内で入力してください")
        
        if self.description is not None and len(self.description) > 1000:
            errors.append("説明は1000文字以内で入力してください")
        
        if self.trigger_condition is not None:
            trigger_errors = self.trigger_condition.validate()
            errors.extend(trigger_errors)
        
        if self.repeat_condition is not None:
            repeat_errors = self.repeat_condition.validate()
            errors.extend(repeat_errors)
        
        return errors


@dataclass
class ScheduleListDTO:
    """スケジュール一覧DTO"""
    schedules: List[ScheduleDTO]
    total_count: int
    active_count: int
    inactive_count: int
    running_count: int
    page: int = 1
    page_size: int = 50
    has_next: bool = False
    has_previous: bool = False
    filters: Dict[str, Any] = field(default_factory=dict)
    sort_by: str = "updated_at"
    sort_order: str = "desc"


@dataclass
class ScheduleStatsDTO:
    """スケジュール統計DTO"""
    total_schedules: int
    active_schedules: int
    inactive_schedules: int
    running_schedules: int
    total_executions: int
    successful_executions: int
    failed_executions: int
    average_success_rate: float
    total_execution_time_seconds: float
    most_active_schedule: Optional[str] = None
    recent_executions: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def overall_success_rate(self) -> float:
        """全体成功率"""
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions


@dataclass
class ScheduleExecutionHistoryDTO:
    """スケジュール実行履歴DTO"""
    schedule_id: str
    executions: List[ExecutionResultDTO] = field(default_factory=list)
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    average_duration_seconds: float = 0.0
    last_execution: Optional[datetime] = None
    next_execution: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions


@dataclass
class ScheduleValidationDTO:
    """スケジュール検証DTO"""
    schedule_id: Optional[str]
    is_valid: bool
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    recording_validation: Optional[Dict[str, Any]] = None
    trigger_validation: List[str] = field(default_factory=list)
    repeat_validation: List[str] = field(default_factory=list)
    system_compatibility: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def has_issues(self) -> bool:
        """問題があるかどうか"""
        return len(self.errors) > 0 or len(self.warnings) > 0
    
    @property
    def severity_level(self) -> str:
        """重要度レベル"""
        if self.errors:
            return "error"
        elif self.warnings:
            return "warning"
        else:
            return "info"


@dataclass
class ScheduleImportExportDTO:
    """スケジュールインポート・エクスポートDTO"""
    schedules: List[Dict[str, Any]] = field(default_factory=list)
    format_version: str = "1.0"
    export_timestamp: datetime = field(default_factory=datetime.now)
    include_execution_history: bool = False
    include_statistics: bool = False
    
    def validate(self) -> List[str]:
        """バリデーション"""
        errors = []
        
        if not self.schedules:
            errors.append("エクスポート対象のスケジュールがありません")
        
        if len(self.schedules) > 1000:
            errors.append("一度にエクスポートできるスケジュールは1000件までです")
        
        return errors


@dataclass
class BulkScheduleOperationDTO:
    """一括スケジュール操作DTO"""
    schedule_ids: List[str]
    operation: str  # activate, deactivate, delete, export
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> List[str]:
        """バリデーション"""
        errors = []
        
        if not self.schedule_ids:
            errors.append("操作対象のスケジュールを選択してください")
        
        if len(self.schedule_ids) > 100:
            errors.append("一度に操作できるスケジュールは100件までです")
        
        valid_operations = ["activate", "deactivate", "delete", "export"]
        if self.operation not in valid_operations:
            errors.append(f"操作種別は次のいずれかを指定してください: {', '.join(valid_operations)}")
        
        return errors