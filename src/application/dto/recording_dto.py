"""
Recording DTO - 記録データ転送オブジェクト

記録データをレイヤー間で転送するためのDTOクラス群です。
UIや外部APIとの境界でドメインオブジェクトを適切な形式に変換します。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

from ...domain.value_objects import RecordingStatus, ActionType


@dataclass
class ActionDTO:
    """アクションDTO"""
    action_id: str
    action_type: str
    sequence_number: int
    timestamp: datetime
    data: Dict[str, Any]
    description: Optional[str] = None
    
    @classmethod
    def from_domain(cls, action) -> 'ActionDTO':
        """ドメインオブジェクトからDTOを作成"""
        return cls(
            action_id=action.action_id,
            action_type=action.action_type.value,
            sequence_number=action.sequence_number,
            timestamp=action.timestamp,
            data=action.to_dict(),
            description=getattr(action, 'description', None)
        )


@dataclass
class RecordingMetadataDTO:
    """記録メタデータDTO"""
    author: str
    category: str
    tags: List[str]
    description: str
    auto_save: bool
    version: str
    application_context: Dict[str, Any]
    
    @classmethod
    def from_domain(cls, metadata) -> 'RecordingMetadataDTO':
        """ドメインオブジェクトからDTOを作成"""
        return cls(
            author=metadata.author,
            category=metadata.category,
            tags=metadata.tags.copy(),
            description=metadata.description,
            auto_save=metadata.auto_save,
            version=metadata.version,
            application_context=metadata.application_context.copy()
        )


@dataclass
class PlaybackSettingsDTO:
    """再生設定DTO"""
    speed_multiplier: float
    delay_between_actions: int
    stop_on_error: bool
    take_screenshots: bool
    screenshot_settings: Dict[str, Any]
    
    @classmethod
    def from_domain(cls, settings) -> 'PlaybackSettingsDTO':
        """ドメインオブジェクトからDTOを作成"""
        return cls(
            speed_multiplier=settings.speed_multiplier,
            delay_between_actions=settings.delay_between_actions,
            stop_on_error=settings.stop_on_error,
            take_screenshots=settings.take_screenshots,
            screenshot_settings=settings.screenshot_settings.copy()
        )


@dataclass
class RecordingDTO:
    """記録DTO"""
    recording_id: str
    name: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    action_count: int
    estimated_duration_ms: int
    metadata: RecordingMetadataDTO
    playback_settings: PlaybackSettingsDTO
    actions: List[ActionDTO] = field(default_factory=list)
    
    @classmethod
    def from_domain(cls, recording, include_actions: bool = True) -> 'RecordingDTO':
        """ドメインオブジェクトからDTOを作成"""
        actions = []
        if include_actions:
            actions = [ActionDTO.from_domain(action) for action in recording.actions]
        
        return cls(
            recording_id=recording.recording_id,
            name=recording.name,
            description=recording.description,
            status=recording.status.value,
            created_at=recording.created_at,
            updated_at=recording.updated_at,
            completed_at=recording.completed_at,
            action_count=recording.action_count,
            estimated_duration_ms=recording.get_estimated_duration().milliseconds,
            metadata=RecordingMetadataDTO.from_domain(recording.metadata),
            playback_settings=PlaybackSettingsDTO.from_domain(recording.playback_settings),
            actions=actions
        )
    
    def to_summary(self) -> 'RecordingSummaryDTO':
        """サマリーDTOに変換"""
        return RecordingSummaryDTO(
            recording_id=self.recording_id,
            name=self.name,
            description=self.description,
            status=self.status,
            created_at=self.created_at,
            updated_at=self.updated_at,
            completed_at=self.completed_at,
            action_count=self.action_count,
            estimated_duration_ms=self.estimated_duration_ms,
            category=self.metadata.category,
            tags=self.metadata.tags
        )


@dataclass
class RecordingSummaryDTO:
    """記録サマリーDTO（一覧表示用）"""
    recording_id: str
    name: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    action_count: int
    estimated_duration_ms: int
    category: str
    tags: List[str]


@dataclass
class CreateRecordingDTO:
    """記録作成用DTO"""
    name: str
    description: Optional[str] = None
    category: str = "default"
    tags: List[str] = field(default_factory=list)
    auto_save: bool = True
    author: str = "Unknown"
    
    def validate(self) -> List[str]:
        """バリデーション"""
        errors = []
        
        if not self.name or not self.name.strip():
            errors.append("記録名は必須です")
        
        if len(self.name) > 255:
            errors.append("記録名は255文字以内で入力してください")
        
        if self.description and len(self.description) > 1000:
            errors.append("説明は1000文字以内で入力してください")
        
        if self.category and len(self.category) > 100:
            errors.append("カテゴリは100文字以内で入力してください")
        
        for tag in self.tags:
            if len(tag) > 50:
                errors.append(f"タグは50文字以内で入力してください: {tag}")
        
        return errors


@dataclass
class UpdateRecordingDTO:
    """記録更新用DTO"""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    playback_settings: Optional[Dict[str, Any]] = None
    
    def validate(self) -> List[str]:
        """バリデーション"""
        errors = []
        
        if self.name is not None:
            if not self.name.strip():
                errors.append("記録名は空にできません")
            elif len(self.name) > 255:
                errors.append("記録名は255文字以内で入力してください")
        
        if self.description is not None and len(self.description) > 1000:
            errors.append("説明は1000文字以内で入力してください")
        
        if self.category is not None and len(self.category) > 100:
            errors.append("カテゴリは100文字以内で入力してください")
        
        if self.tags is not None:
            for tag in self.tags:
                if len(tag) > 50:
                    errors.append(f"タグは50文字以内で入力してください: {tag}")
        
        return errors


@dataclass
class RecordingListDTO:
    """記録一覧DTO"""
    recordings: List[RecordingSummaryDTO]
    total_count: int
    page: int = 1
    page_size: int = 50
    has_next: bool = False
    has_previous: bool = False
    filters: Dict[str, Any] = field(default_factory=dict)
    sort_by: str = "updated_at"
    sort_order: str = "desc"


@dataclass
class RecordingStatsDTO:
    """記録統計DTO"""
    total_recordings: int
    total_actions: int
    avg_actions_per_recording: float
    total_duration_seconds: float
    status_distribution: Dict[str, int]
    category_distribution: Dict[str, int]
    recent_activity: List[Dict[str, Any]]
    
    @classmethod
    def from_repository_stats(cls, stats: Dict[str, Any]) -> 'RecordingStatsDTO':
        """リポジトリ統計からDTOを作成"""
        return cls(
            total_recordings=stats.get('total_recordings', 0),
            total_actions=stats.get('total_actions', 0),
            avg_actions_per_recording=stats.get('avg_actions_per_recording', 0.0),
            total_duration_seconds=stats.get('total_duration', 0) / 1000.0,  # msから秒に変換
            status_distribution=stats.get('status_distribution', {}),
            category_distribution=stats.get('category_distribution', {}),
            recent_activity=stats.get('recent_activity', [])
        )


@dataclass
class RecordingSearchDTO:
    """記録検索用DTO"""
    query: str
    filters: Dict[str, Any] = field(default_factory=dict)
    sort_by: str = "relevance"
    sort_order: str = "desc"
    page: int = 1
    page_size: int = 50
    
    def validate(self) -> List[str]:
        """バリデーション"""
        errors = []
        
        if not self.query or not self.query.strip():
            errors.append("検索クエリは必須です")
        
        if len(self.query) > 500:
            errors.append("検索クエリは500文字以内で入力してください")
        
        if self.page < 1:
            errors.append("ページ番号は1以上で指定してください")
        
        if self.page_size < 1 or self.page_size > 1000:
            errors.append("ページサイズは1-1000の範囲で指定してください")
        
        valid_sort_fields = ["name", "created_at", "updated_at", "action_count", "duration", "relevance"]
        if self.sort_by not in valid_sort_fields:
            errors.append(f"ソート項目は次のいずれかを指定してください: {', '.join(valid_sort_fields)}")
        
        valid_sort_orders = ["asc", "desc"]
        if self.sort_order not in valid_sort_orders:
            errors.append(f"ソート順は次のいずれかを指定してください: {', '.join(valid_sort_orders)}")
        
        return errors


@dataclass
class RecordingExportDTO:
    """記録エクスポート用DTO"""
    recording_ids: List[str]
    format: str = "json"  # json, xml, csv
    include_actions: bool = True
    include_metadata: bool = True
    include_playback_settings: bool = True
    compression: bool = False
    
    def validate(self) -> List[str]:
        """バリデーション"""
        errors = []
        
        if not self.recording_ids:
            errors.append("エクスポート対象の記録を選択してください")
        
        if len(self.recording_ids) > 1000:
            errors.append("一度にエクスポートできる記録は1000件までです")
        
        valid_formats = ["json", "xml", "csv"]
        if self.format not in valid_formats:
            errors.append(f"エクスポート形式は次のいずれかを指定してください: {', '.join(valid_formats)}")
        
        return errors


@dataclass
class RecordingImportDTO:
    """記録インポート用DTO"""
    file_path: str
    format: str = "json"  # json, xml, csv
    overwrite_existing: bool = False
    validate_before_import: bool = True
    import_metadata: bool = True
    import_playback_settings: bool = True
    
    def validate(self) -> List[str]:
        """バリデーション"""
        errors = []
        
        if not self.file_path:
            errors.append("インポートファイルパスは必須です")
        
        valid_formats = ["json", "xml", "csv"]
        if self.format not in valid_formats:
            errors.append(f"インポート形式は次のいずれかを指定してください: {', '.join(valid_formats)}")
        
        return errors