"""
Playback DTO - 再生データ転送オブジェクト

再生データをレイヤー間で転送するためのDTOクラス群です。
再生設定、ステータス、結果などの情報を含みます。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


@dataclass
class PlaybackConfigDTO:
    """再生設定DTO"""
    speed_multiplier: float = 1.0
    delay_between_actions: int = 500  # ミリ秒
    stop_on_error: bool = True
    take_screenshots: bool = False
    screenshot_interval: int = 1000  # ミリ秒
    log_actions: bool = True
    simulate_mode: bool = False  # シミュレーション（実際の操作なし）
    start_from_action: int = 0
    end_at_action: Optional[int] = None
    repeat_count: int = 1
    repeat_delay: int = 5000  # ミリ秒
    
    def validate(self) -> List[str]:
        """バリデーション"""
        errors = []
        
        if self.speed_multiplier <= 0 or self.speed_multiplier > 10:
            errors.append("再生速度は0より大きく10以下で指定してください")
        
        if self.delay_between_actions < 0 or self.delay_between_actions > 60000:
            errors.append("アクション間隔は0-60000ms（60秒）の範囲で指定してください")
        
        if self.screenshot_interval < 100:
            errors.append("スクリーンショット間隔は100ms以上で指定してください")
        
        if self.start_from_action < 0:
            errors.append("開始アクション番号は0以上で指定してください")
        
        if self.end_at_action is not None and self.end_at_action <= self.start_from_action:
            errors.append("終了アクション番号は開始アクション番号より大きくしてください")
        
        if self.repeat_count < 1 or self.repeat_count > 1000:
            errors.append("繰り返し回数は1-1000の範囲で指定してください")
        
        if self.repeat_delay < 0:
            errors.append("繰り返し間隔は0以上で指定してください")
        
        return errors


@dataclass
class PlaybackStatusDTO:
    """再生ステータスDTO"""
    session_id: str
    status: str  # ready, playing, paused, completed, failed, cancelled
    recording_id: str
    recording_name: str
    current_action_index: int
    total_actions: int
    progress_percentage: float
    start_time: datetime
    elapsed_seconds: float
    estimated_remaining_seconds: Optional[float]
    current_repeat: int
    total_repeats: int
    error_message: Optional[str] = None
    last_action_executed: Optional[str] = None
    
    @property
    def is_active(self) -> bool:
        """アクティブな再生かどうか"""
        return self.status in ["playing", "paused"]
    
    @property
    def is_finished(self) -> bool:
        """再生が終了したかどうか"""
        return self.status in ["completed", "failed", "cancelled"]


@dataclass
class PlaybackActionResultDTO:
    """再生アクション結果DTO"""
    action_id: str
    action_type: str
    sequence_number: int
    executed_at: datetime
    success: bool
    execution_time_ms: int
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlaybackResultDTO:
    """再生結果DTO"""
    session_id: str
    recording_id: str
    recording_name: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    total_actions: int
    actions_executed: int
    actions_succeeded: int
    actions_failed: int
    completion_rate: float
    success_rate: float
    status: str  # completed, failed, cancelled
    error_message: Optional[str] = None
    action_results: List[PlaybackActionResultDTO] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def was_successful(self) -> bool:
        """再生が成功したかどうか"""
        return self.status == "completed" and self.success_rate > 0.9
    
    @property
    def average_action_time_ms(self) -> float:
        """平均アクション実行時間（ミリ秒）"""
        if not self.action_results:
            return 0.0
        return sum(r.execution_time_ms for r in self.action_results) / len(self.action_results)


@dataclass
class PlaybackDTO:
    """再生情報DTO"""
    session_id: str
    recording_id: str
    recording_name: str
    config: PlaybackConfigDTO
    status: PlaybackStatusDTO
    result: Optional[PlaybackResultDTO] = None
    
    @classmethod
    def create_new(cls, session_id: str, recording_id: str, recording_name: str, 
                   config: PlaybackConfigDTO) -> 'PlaybackDTO':
        """新しい再生DTOを作成"""
        status = PlaybackStatusDTO(
            session_id=session_id,
            status="ready",
            recording_id=recording_id,
            recording_name=recording_name,
            current_action_index=0,
            total_actions=0,
            progress_percentage=0.0,
            start_time=datetime.now(),
            elapsed_seconds=0.0,
            estimated_remaining_seconds=None,
            current_repeat=1,
            total_repeats=config.repeat_count
        )
        
        return cls(
            session_id=session_id,
            recording_id=recording_id,
            recording_name=recording_name,
            config=config,
            status=status
        )


@dataclass
class PlaybackQueueItemDTO:
    """再生キューアイテムDTO"""
    queue_id: str
    recording_id: str
    recording_name: str
    config: PlaybackConfigDTO
    scheduled_time: Optional[datetime] = None
    priority: int = 0  # 0=低, 1=通常, 2=高
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "queued"  # queued, running, completed, failed, cancelled
    
    def validate(self) -> List[str]:
        """バリデーション"""
        errors = []
        
        if not self.queue_id:
            errors.append("キューIDは必須です")
        
        if not self.recording_id:
            errors.append("記録IDは必須です")
        
        if self.priority < 0 or self.priority > 2:
            errors.append("優先度は0-2の範囲で指定してください")
        
        if self.scheduled_time and self.scheduled_time < datetime.now():
            errors.append("実行予定時刻は現在時刻より後で指定してください")
        
        config_errors = self.config.validate()
        errors.extend(config_errors)
        
        return errors


@dataclass
class PlaybackQueueDTO:
    """再生キューDTO"""
    queue_items: List[PlaybackQueueItemDTO] = field(default_factory=list)
    current_item: Optional[PlaybackQueueItemDTO] = None
    total_items: int = 0
    completed_items: int = 0
    failed_items: int = 0
    cancelled_items: int = 0
    
    @property
    def pending_items(self) -> List[PlaybackQueueItemDTO]:
        """待機中のアイテム"""
        return [item for item in self.queue_items if item.status == "queued"]
    
    @property
    def running_items(self) -> List[PlaybackQueueItemDTO]:
        """実行中のアイテム"""
        return [item for item in self.queue_items if item.status == "running"]
    
    @property
    def completion_rate(self) -> float:
        """完了率"""
        if self.total_items == 0:
            return 0.0
        return self.completed_items / self.total_items


@dataclass
class PlaybackValidationDTO:
    """再生検証DTO"""
    recording_id: str
    is_playable: bool
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    action_count: int = 0
    estimated_duration_seconds: float = 0.0
    system_requirements: Dict[str, Any] = field(default_factory=dict)
    compatibility_issues: List[str] = field(default_factory=list)
    
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
class PlaybackScheduleDTO:
    """再生スケジュールDTO"""
    schedule_id: str
    recording_id: str
    recording_name: str
    config: PlaybackConfigDTO
    trigger_type: str  # immediate, time, interval, condition
    trigger_config: Dict[str, Any] = field(default_factory=dict)
    next_execution: Optional[datetime] = None
    last_execution: Optional[datetime] = None
    execution_count: int = 0
    is_active: bool = True
    
    def validate(self) -> List[str]:
        """バリデーション"""
        errors = []
        
        if not self.schedule_id:
            errors.append("スケジュールIDは必須です")
        
        if not self.recording_id:
            errors.append("記録IDは必須です")
        
        valid_trigger_types = ["immediate", "time", "interval", "condition"]
        if self.trigger_type not in valid_trigger_types:
            errors.append(f"トリガー種別は次のいずれかを指定してください: {', '.join(valid_trigger_types)}")
        
        config_errors = self.config.validate()
        errors.extend(config_errors)
        
        return errors


@dataclass
class PlaybackHistoryDTO:
    """再生履歴DTO"""
    executions: List[PlaybackResultDTO] = field(default_factory=list)
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    average_duration_seconds: float = 0.0
    average_success_rate: float = 0.0
    most_recent_execution: Optional[datetime] = None
    
    @property
    def overall_success_rate(self) -> float:
        """全体成功率"""
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions
    
    @classmethod
    def from_results(cls, results: List[PlaybackResultDTO]) -> 'PlaybackHistoryDTO':
        """再生結果リストから履歴DTOを作成"""
        if not results:
            return cls()
        
        successful = sum(1 for r in results if r.was_successful)
        total_duration = sum(r.duration_seconds for r in results)
        total_success_rate = sum(r.success_rate for r in results)
        
        return cls(
            executions=results,
            total_executions=len(results),
            successful_executions=successful,
            failed_executions=len(results) - successful,
            average_duration_seconds=total_duration / len(results),
            average_success_rate=total_success_rate / len(results),
            most_recent_execution=max(r.end_time for r in results)
        )