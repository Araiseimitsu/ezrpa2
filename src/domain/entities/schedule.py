"""
Schedule エンティティ - RPAレコーディングの自動実行スケジュール

Windows環境でのタスクスケジューラ連携を含む、
レコーディングの時間ベース実行管理を行うドメインエンティティです。
"""

import uuid
from datetime import datetime, timezone, timedelta, time
from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import re

from ..value_objects import (
    ScheduleStatus, TriggerType, Duration, ValidationResult
)
from ...core.result import Result, Ok, Err, ErrorInfo
from ...shared.constants import ValidationConstants


class WeekDay(Enum):
    """曜日定義"""
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7


class RepeatUnit(Enum):
    """繰り返し単位"""
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"


@dataclass
class TimeCondition:
    """時間条件"""
    hour: int = 0
    minute: int = 0
    second: int = 0
    
    def __post_init__(self):
        if not (0 <= self.hour <= 23):
            raise ValueError(f"時間は0-23の範囲で指定してください: {self.hour}")
        if not (0 <= self.minute <= 59):
            raise ValueError(f"分は0-59の範囲で指定してください: {self.minute}")
        if not (0 <= self.second <= 59):
            raise ValueError(f"秒は0-59の範囲で指定してください: {self.second}")
    
    def to_time(self) -> time:
        """datetime.timeオブジェクトに変換"""
        return time(self.hour, self.minute, self.second)
    
    def to_dict(self) -> Dict[str, int]:
        """辞書形式に変換"""
        return {
            'hour': self.hour,
            'minute': self.minute,
            'second': self.second
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> 'TimeCondition':
        """辞書から復元"""
        return cls(
            hour=data.get('hour', 0),
            minute=data.get('minute', 0),
            second=data.get('second', 0)
        )
    
    @classmethod
    def from_time_string(cls, time_str: str) -> 'TimeCondition':
        """文字列から作成 (例: "14:30:00", "9:15")"""
        parts = time_str.split(':')
        if len(parts) < 2 or len(parts) > 3:
            raise ValueError(f"無効な時間形式です: {time_str}")
        
        hour = int(parts[0])
        minute = int(parts[1])
        second = int(parts[2]) if len(parts) == 3 else 0
        
        return cls(hour, minute, second)
    
    def __str__(self) -> str:
        return f"{self.hour:02d}:{self.minute:02d}:{self.second:02d}"


@dataclass
class RepeatCondition:
    """繰り返し条件"""
    unit: RepeatUnit
    interval: int = 1
    max_occurrences: Optional[int] = None
    end_date: Optional[datetime] = None
    
    def __post_init__(self):
        if self.interval <= 0:
            raise ValueError("間隔は正の値である必要があります")
        
        if self.max_occurrences is not None and self.max_occurrences <= 0:
            raise ValueError("最大実行回数は正の値である必要があります")
    
    def validate(self) -> ValidationResult:
        """繰り返し条件のバリデーション"""
        errors = []
        warnings = []
        
        # 合理的な間隔チェック
        if self.unit == RepeatUnit.MINUTES and self.interval > 1440:  # 24時間
            warnings.append("分単位で24時間以上の間隔が設定されています")
        elif self.unit == RepeatUnit.HOURS and self.interval > 168:  # 7日
            warnings.append("時間単位で1週間以上の間隔が設定されています")
        elif self.unit == RepeatUnit.DAYS and self.interval > 365:  # 1年
            warnings.append("日単位で1年以上の間隔が設定されています")
        
        # 終了条件チェック
        if self.end_date and self.end_date <= datetime.now(timezone.utc):
            errors.append("終了日時が過去に設定されています")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def calculate_next_execution(self, last_execution: datetime) -> Optional[datetime]:
        """次回実行時刻を計算"""
        if self.unit == RepeatUnit.MINUTES:
            next_time = last_execution + timedelta(minutes=self.interval)
        elif self.unit == RepeatUnit.HOURS:
            next_time = last_execution + timedelta(hours=self.interval)
        elif self.unit == RepeatUnit.DAYS:
            next_time = last_execution + timedelta(days=self.interval)
        elif self.unit == RepeatUnit.WEEKS:
            next_time = last_execution + timedelta(weeks=self.interval)
        elif self.unit == RepeatUnit.MONTHS:
            # 月単位は複雑なので簡易実装
            year = last_execution.year
            month = last_execution.month + self.interval
            while month > 12:
                year += 1
                month -= 12
            next_time = last_execution.replace(year=year, month=month)
        else:
            return None
        
        # 終了条件チェック
        if self.end_date and next_time > self.end_date:
            return None
        
        return next_time
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = {
            'unit': self.unit.value,
            'interval': self.interval
        }
        
        if self.max_occurrences is not None:
            data['max_occurrences'] = self.max_occurrences
        
        if self.end_date:
            data['end_date'] = self.end_date.isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RepeatCondition':
        """辞書から復元"""
        end_date = None
        if 'end_date' in data:
            end_date = datetime.fromisoformat(data['end_date'])
        
        return cls(
            unit=RepeatUnit(data['unit']),
            interval=data['interval'],
            max_occurrences=data.get('max_occurrences'),
            end_date=end_date
        )


@dataclass
class TriggerCondition:
    """トリガー条件"""
    trigger_type: TriggerType
    
    # 時間ベーストリガー
    execution_time: Optional[TimeCondition] = None
    weekdays: Set[WeekDay] = field(default_factory=set)
    repeat_condition: Optional[RepeatCondition] = None
    
    # イベントベーストリガー
    file_path: Optional[str] = None
    hotkey_combination: Optional[str] = None
    idle_duration: Optional[Duration] = None
    
    # システムトリガー
    startup_delay: Optional[Duration] = None
    
    def validate(self) -> ValidationResult:
        """トリガー条件のバリデーション"""
        errors = []
        warnings = []
        
        if self.trigger_type == TriggerType.SCHEDULED:
            if not self.execution_time:
                errors.append("スケジュール実行には実行時刻が必要です")
        
        elif self.trigger_type == TriggerType.FILE_WATCHER:
            if not self.file_path:
                errors.append("ファイル監視には監視対象パスが必要です")
            elif len(self.file_path) > ValidationConstants.MAX_PATH_LENGTH:
                errors.append("ファイルパスが長すぎます")
        
        elif self.trigger_type == TriggerType.HOTKEY:
            if not self.hotkey_combination:
                errors.append("ホットキートリガーにはキー組み合わせが必要です")
            elif not self._validate_hotkey_format(self.hotkey_combination):
                errors.append("無効なホットキー形式です")
        
        elif self.trigger_type == TriggerType.IDLE:
            if not self.idle_duration:
                errors.append("アイドルトリガーには待機時間が必要です")
            elif self.idle_duration.milliseconds < 60000:  # 1分未満
                warnings.append("アイドル時間が短すぎます（1分以上推奨）")
        
        elif self.trigger_type == TriggerType.STARTUP:
            if self.startup_delay and self.startup_delay.milliseconds > 300000:  # 5分超過
                warnings.append("起動遅延時間が長すぎます（5分以内推奨）")
        
        # 繰り返し条件のバリデーション
        if self.repeat_condition:
            repeat_validation = self.repeat_condition.validate()
            errors.extend(repeat_validation.errors)
            warnings.extend(repeat_validation.warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _validate_hotkey_format(self, hotkey: str) -> bool:
        """ホットキー形式のバリデーション"""
        # 簡易チェック（Ctrl+Alt+F1 等の形式）
        pattern = r'^(Ctrl\+)?(Alt\+)?(Shift\+)?(Win\+)?[A-Z0-9]$|^(Ctrl\+)?(Alt\+)?(Shift\+)?(Win\+)?F[1-9][0-2]?$'
        return bool(re.match(pattern, hotkey, re.IGNORECASE))
    
    def is_time_based(self) -> bool:
        """時間ベースのトリガーかどうか"""
        return self.trigger_type in [TriggerType.SCHEDULED, TriggerType.STARTUP]
    
    def is_event_based(self) -> bool:
        """イベントベースのトリガーかどうか"""
        return self.trigger_type in [TriggerType.FILE_WATCHER, TriggerType.HOTKEY, TriggerType.IDLE]
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = {
            'trigger_type': self.trigger_type.value
        }
        
        if self.execution_time:
            data['execution_time'] = self.execution_time.to_dict()
        
        if self.weekdays:
            data['weekdays'] = [day.value for day in self.weekdays]
        
        if self.repeat_condition:
            data['repeat_condition'] = self.repeat_condition.to_dict()
        
        if self.file_path:
            data['file_path'] = self.file_path
        
        if self.hotkey_combination:
            data['hotkey_combination'] = self.hotkey_combination
        
        if self.idle_duration:
            data['idle_duration'] = self.idle_duration.milliseconds
        
        if self.startup_delay:
            data['startup_delay'] = self.startup_delay.milliseconds
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TriggerCondition':
        """辞書から復元"""
        execution_time = None
        if 'execution_time' in data:
            execution_time = TimeCondition.from_dict(data['execution_time'])
        
        weekdays = set()
        if 'weekdays' in data:
            weekdays = {WeekDay(day) for day in data['weekdays']}
        
        repeat_condition = None
        if 'repeat_condition' in data:
            repeat_condition = RepeatCondition.from_dict(data['repeat_condition'])
        
        idle_duration = None
        if 'idle_duration' in data:
            idle_duration = Duration(data['idle_duration'])
        
        startup_delay = None
        if 'startup_delay' in data:
            startup_delay = Duration(data['startup_delay'])
        
        return cls(
            trigger_type=TriggerType(data['trigger_type']),
            execution_time=execution_time,
            weekdays=weekdays,
            repeat_condition=repeat_condition,
            file_path=data.get('file_path'),
            hotkey_combination=data.get('hotkey_combination'),
            idle_duration=idle_duration,
            startup_delay=startup_delay
        )


@dataclass
class ExecutionResult:
    """実行結果"""
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    success: bool = False
    error_message: Optional[str] = None
    actions_executed: int = 0
    total_actions: int = 0
    
    @property
    def duration(self) -> Optional[Duration]:
        """実行時間を取得"""
        if self.end_time:
            delta = self.end_time - self.start_time
            return Duration(int(delta.total_seconds() * 1000))
        return None
    
    @property
    def completion_rate(self) -> float:
        """完了率を取得（0.0-1.0）"""
        if self.total_actions == 0:
            return 0.0
        return min(1.0, self.actions_executed / self.total_actions)
    
    def mark_completed(self, success: bool, error_message: Optional[str] = None) -> None:
        """実行完了をマーク"""
        self.end_time = datetime.now(timezone.utc)
        self.success = success
        self.error_message = error_message
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = {
            'execution_id': self.execution_id,
            'start_time': self.start_time.isoformat(),
            'success': self.success,
            'actions_executed': self.actions_executed,
            'total_actions': self.total_actions
        }
        
        if self.end_time:
            data['end_time'] = self.end_time.isoformat()
        
        if self.error_message:
            data['error_message'] = self.error_message
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionResult':
        """辞書から復元"""
        end_time = None
        if 'end_time' in data:
            end_time = datetime.fromisoformat(data['end_time'])
        
        return cls(
            execution_id=data['execution_id'],
            start_time=datetime.fromisoformat(data['start_time']),
            end_time=end_time,
            success=data['success'],
            error_message=data.get('error_message'),
            actions_executed=data.get('actions_executed', 0),
            total_actions=data.get('total_actions', 0)
        )


@dataclass
class Schedule:
    """
    Schedule エンティティ - RPAレコーディングスケジュール
    
    レコーディングの自動実行スケジュールを管理するドメインエンティティです。
    Windows環境でのタスクスケジューラ連携も含みます。
    """
    
    # 識別情報
    schedule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    
    # 関連エンティティ
    recording_id: str = ""
    
    # スケジュール設定
    trigger_condition: TriggerCondition = field(default_factory=lambda: TriggerCondition(TriggerType.MANUAL))
    status: ScheduleStatus = ScheduleStatus.INACTIVE
    
    # 実行制御
    enabled: bool = True
    max_parallel_executions: int = 1
    execution_timeout: Duration = Duration(3600000)  # 1時間
    
    # 日時情報
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    next_execution_time: Optional[datetime] = None
    last_execution_time: Optional[datetime] = None
    
    # 実行履歴
    execution_history: List[ExecutionResult] = field(default_factory=list)
    total_executions: int = 0
    successful_executions: int = 0
    
    # Windows環境設定
    run_as_admin: bool = False
    window_state: str = "normal"  # "normal", "minimized", "maximized"
    
    def __post_init__(self):
        """初期化後の処理"""
        if not self.name:
            self.name = f"スケジュール_{self.created_at.strftime('%Y%m%d_%H%M%S')}"
        
        # 次回実行時刻の初期化
        if self.trigger_condition.trigger_type == TriggerType.SCHEDULED:
            self._calculate_next_execution_time()
    
    def activate(self) -> Result[None, str]:
        """スケジュールを有効化"""
        if not self.enabled:
            return Err("無効なスケジュールは有効化できません")
        
        if not self.recording_id:
            return Err("レコーディングIDが設定されていません")
        
        # バリデーション
        validation_result = self.validate()
        if not validation_result.is_valid:
            return Err(f"スケジュールバリデーションエラー: {', '.join(validation_result.errors)}")
        
        self.status = ScheduleStatus.ACTIVE
        self._update_timestamp()
        
        # 次回実行時刻を計算
        self._calculate_next_execution_time()
        
        return Ok(None)
    
    def deactivate(self) -> Result[None, str]:
        """スケジュールを無効化"""
        if self.status == ScheduleStatus.RUNNING:
            return Err("実行中のスケジュールは無効化できません")
        
        self.status = ScheduleStatus.INACTIVE
        self.next_execution_time = None
        self._update_timestamp()
        
        return Ok(None)
    
    def start_execution(self) -> Result[ExecutionResult, str]:
        """実行開始"""
        if self.status != ScheduleStatus.ACTIVE:
            return Err(f"実行できない状態です: {self.status.value}")
        
        if not self.enabled:
            return Err("無効なスケジュールです")
        
        # 並列実行制限チェック
        running_executions = [r for r in self.execution_history 
                            if r.end_time is None]
        if len(running_executions) >= self.max_parallel_executions:
            return Err("並列実行数の上限に達しています")
        
        # 実行結果を作成
        execution_result = ExecutionResult()
        self.execution_history.append(execution_result)
        
        # 状態更新
        self.status = ScheduleStatus.RUNNING
        self.last_execution_time = datetime.now(timezone.utc)
        self._update_timestamp()
        
        return Ok(execution_result)
    
    def complete_execution(self, execution_id: str, success: bool, 
                          actions_executed: int = 0, total_actions: int = 0,
                          error_message: Optional[str] = None) -> Result[None, str]:
        """実行完了"""
        # 実行結果を検索
        execution_result = None
        for result in self.execution_history:
            if result.execution_id == execution_id:
                execution_result = result
                break
        
        if not execution_result:
            return Err(f"実行ID {execution_id} が見つかりません")
        
        # 実行結果を更新
        execution_result.mark_completed(success, error_message)
        execution_result.actions_executed = actions_executed
        execution_result.total_actions = total_actions
        
        # 統計更新
        self.total_executions += 1
        if success:
            self.successful_executions += 1
        
        # 状態更新
        self.status = ScheduleStatus.ACTIVE if success else ScheduleStatus.FAILED
        self._update_timestamp()
        
        # 次回実行時刻を計算
        if success and self.trigger_condition.repeat_condition:
            self._calculate_next_execution_time()
        
        # 実行履歴のクリーンアップ（最新100件のみ保持）
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]
        
        return Ok(None)
    
    def should_execute_now(self) -> bool:
        """現在実行すべきかどうか"""
        if not self.enabled or self.status != ScheduleStatus.ACTIVE:
            return False
        
        if not self.next_execution_time:
            return False
        
        current_time = datetime.now(timezone.utc)
        return current_time >= self.next_execution_time
    
    def get_next_execution_time(self) -> Optional[datetime]:
        """次回実行時刻を取得"""
        return self.next_execution_time
    
    def validate(self) -> ValidationResult:
        """スケジュールのバリデーション"""
        errors = []
        warnings = []
        
        # 基本情報チェック
        if not self.name or len(self.name.strip()) == 0:
            errors.append("スケジュール名が空です")
        elif len(self.name) > ValidationConstants.MAX_RECORDING_NAME_LENGTH:
            errors.append("スケジュール名が長すぎます")
        
        if not self.recording_id:
            errors.append("レコーディングIDが設定されていません")
        
        # トリガー条件のバリデーション
        trigger_validation = self.trigger_condition.validate()
        errors.extend(trigger_validation.errors)
        warnings.extend(trigger_validation.warnings)
        
        # 実行設定チェック
        if self.max_parallel_executions <= 0:
            errors.append("並列実行数は正の値である必要があります")
        elif self.max_parallel_executions > 10:
            warnings.append("並列実行数が多すぎます（10以下推奨）")
        
        if self.execution_timeout.milliseconds < 1000:
            warnings.append("実行タイムアウトが短すぎます（1秒以上推奨）")
        elif self.execution_timeout.milliseconds > 86400000:  # 24時間
            warnings.append("実行タイムアウトが長すぎます（24時間以内推奨）")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def clone(self, new_name: Optional[str] = None) -> 'Schedule':
        """スケジュールのクローンを作成"""
        cloned = Schedule(
            schedule_id=str(uuid.uuid4()),
            name=new_name or f"{self.name}_コピー",
            description=self.description,
            recording_id=self.recording_id,
            trigger_condition=TriggerCondition.from_dict(self.trigger_condition.to_dict()),
            status=ScheduleStatus.INACTIVE,
            enabled=self.enabled,
            max_parallel_executions=self.max_parallel_executions,
            execution_timeout=self.execution_timeout,
            run_as_admin=self.run_as_admin,
            window_state=self.window_state
        )
        
        return cloned
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = {
            'schedule_id': self.schedule_id,
            'name': self.name,
            'description': self.description,
            'recording_id': self.recording_id,
            'trigger_condition': self.trigger_condition.to_dict(),
            'status': self.status.value,
            'enabled': self.enabled,
            'max_parallel_executions': self.max_parallel_executions,
            'execution_timeout': self.execution_timeout.milliseconds,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'total_executions': self.total_executions,
            'successful_executions': self.successful_executions,
            'run_as_admin': self.run_as_admin,
            'window_state': self.window_state,
            'execution_history': [result.to_dict() for result in self.execution_history]
        }
        
        if self.next_execution_time:
            data['next_execution_time'] = self.next_execution_time.isoformat()
        
        if self.last_execution_time:
            data['last_execution_time'] = self.last_execution_time.isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Schedule':
        """辞書から復元"""
        # 実行履歴の復元
        execution_history = []
        for result_data in data.get('execution_history', []):
            execution_history.append(ExecutionResult.from_dict(result_data))
        
        schedule = cls(
            schedule_id=data['schedule_id'],
            name=data['name'],
            description=data.get('description', ''),
            recording_id=data['recording_id'],
            trigger_condition=TriggerCondition.from_dict(data['trigger_condition']),
            status=ScheduleStatus(data['status']),
            enabled=data.get('enabled', True),
            max_parallel_executions=data.get('max_parallel_executions', 1),
            execution_timeout=Duration(data.get('execution_timeout', 3600000)),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            total_executions=data.get('total_executions', 0),
            successful_executions=data.get('successful_executions', 0),
            run_as_admin=data.get('run_as_admin', False),
            window_state=data.get('window_state', 'normal'),
            execution_history=execution_history
        )
        
        # オプショナル属性の復元
        if 'next_execution_time' in data:
            schedule.next_execution_time = datetime.fromisoformat(data['next_execution_time'])
        
        if 'last_execution_time' in data:
            schedule.last_execution_time = datetime.fromisoformat(data['last_execution_time'])
        
        return schedule
    
    def _calculate_next_execution_time(self) -> None:
        """次回実行時刻を計算"""
        if self.trigger_condition.trigger_type != TriggerType.SCHEDULED:
            self.next_execution_time = None
            return
        
        if not self.trigger_condition.execution_time:
            self.next_execution_time = None
            return
        
        current_time = datetime.now(timezone.utc)
        exec_time = self.trigger_condition.execution_time
        
        # 今日の実行時刻を計算
        today_execution = current_time.replace(
            hour=exec_time.hour,
            minute=exec_time.minute,
            second=exec_time.second,
            microsecond=0
        )
        
        # 曜日指定がある場合
        if self.trigger_condition.weekdays:
            # 今日から7日間で最初に該当する曜日を検索
            for i in range(7):
                check_date = current_time + timedelta(days=i)
                weekday = WeekDay(check_date.isoweekday())
                
                if weekday in self.trigger_condition.weekdays:
                    candidate_time = check_date.replace(
                        hour=exec_time.hour,
                        minute=exec_time.minute,
                        second=exec_time.second,
                        microsecond=0
                    )
                    
                    if candidate_time > current_time:
                        self.next_execution_time = candidate_time
                        return
        else:
            # 曜日指定がない場合
            if today_execution > current_time:
                self.next_execution_time = today_execution
            else:
                self.next_execution_time = today_execution + timedelta(days=1)
    
    def _update_timestamp(self) -> None:
        """更新日時を現在時刻に設定"""
        self.updated_at = datetime.now(timezone.utc)
    
    # プロパティ
    @property
    def success_rate(self) -> float:
        """成功率（0.0-1.0）"""
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions
    
    @property
    def is_active(self) -> bool:
        """アクティブかどうか"""
        return self.enabled and self.status == ScheduleStatus.ACTIVE
    
    @property
    def is_running(self) -> bool:
        """実行中かどうか"""
        return self.status == ScheduleStatus.RUNNING
    
    @property
    def last_execution_result(self) -> Optional[ExecutionResult]:
        """最後の実行結果"""
        if not self.execution_history:
            return None
        return self.execution_history[-1]


# スケジュールファクトリー
class ScheduleFactory:
    """スケジュール生成ファクトリー"""
    
    @staticmethod
    def create_daily_schedule(recording_id: str, execution_time: TimeCondition, 
                            name: str = "") -> Schedule:
        """毎日実行スケジュールを作成"""
        trigger = TriggerCondition(
            trigger_type=TriggerType.SCHEDULED,
            execution_time=execution_time,
            repeat_condition=RepeatCondition(RepeatUnit.DAYS, 1)
        )
        
        return Schedule(
            name=name or f"毎日_{execution_time}",
            recording_id=recording_id,
            trigger_condition=trigger
        )
    
    @staticmethod
    def create_weekly_schedule(recording_id: str, execution_time: TimeCondition,
                             weekdays: Set[WeekDay], name: str = "") -> Schedule:
        """週単位実行スケジュールを作成"""
        trigger = TriggerCondition(
            trigger_type=TriggerType.SCHEDULED,
            execution_time=execution_time,
            weekdays=weekdays
        )
        
        weekday_names = [day.name[:3] for day in weekdays]
        
        return Schedule(
            name=name or f"週間_{execution_time}_{''.join(weekday_names)}",
            recording_id=recording_id,
            trigger_condition=trigger
        )
    
    @staticmethod
    def create_hotkey_schedule(recording_id: str, hotkey: str, 
                             name: str = "") -> Schedule:
        """ホットキートリガースケジュールを作成"""
        trigger = TriggerCondition(
            trigger_type=TriggerType.HOTKEY,
            hotkey_combination=hotkey
        )
        
        return Schedule(
            name=name or f"ホットキー_{hotkey}",
            recording_id=recording_id,
            trigger_condition=trigger
        )
    
    @staticmethod
    def create_startup_schedule(recording_id: str, delay: Duration = Duration(10000),
                              name: str = "") -> Schedule:
        """起動時実行スケジュールを作成"""
        trigger = TriggerCondition(
            trigger_type=TriggerType.STARTUP,
            startup_delay=delay
        )
        
        return Schedule(
            name=name or f"起動時_{delay.seconds}秒後",
            recording_id=recording_id,
            trigger_condition=trigger
        )