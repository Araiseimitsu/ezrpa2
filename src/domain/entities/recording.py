"""
Recording エンティティ - RPAレコーディングの集約ルート

一連のRPAアクションとその実行設定を管理するドメインエンティティです。
Windows環境での記録・再生機能の中核を担います。
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from .action import ActionTypes, ActionBase
from ..value_objects import (
    RecordingStatus,
    Duration,
    ValidationResult,
    CommonDurations,
    FileInfo,
)
from ...core.result import Result, Ok, Err, ErrorInfo
from ...shared.constants import ValidationConstants, ApplicationConstants


@dataclass
class RecordingMetadata:
    """記録メタデータ"""

    author: str = ""
    version: str = ApplicationConstants.VERSION
    description: str = ""
    tags: List[str] = field(default_factory=list)
    category: str = "general"
    priority: int = 0  # 0=通常, 1=高, -1=低
    estimated_duration: Optional[Duration] = None

    # システム情報
    recorded_on: str = ""  # コンピュータ名
    recorded_resolution: Optional[str] = None  # "1920x1080"
    recorded_dpi: Optional[float] = None
    windows_version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = {
            "author": self.author,
            "version": self.version,
            "description": self.description,
            "tags": self.tags,
            "category": self.category,
            "priority": self.priority,
            "recorded_on": self.recorded_on,
            "recorded_resolution": self.recorded_resolution,
            "recorded_dpi": self.recorded_dpi,
            "windows_version": self.windows_version,
        }

        if self.estimated_duration:
            data["estimated_duration"] = self.estimated_duration.milliseconds

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RecordingMetadata":
        """辞書から復元"""
        estimated_duration = None
        if "estimated_duration" in data:
            estimated_duration = Duration(data["estimated_duration"])

        return cls(
            author=data.get("author", ""),
            version=data.get("version", ApplicationConstants.VERSION),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            category=data.get("category", "general"),
            priority=data.get("priority", 0),
            estimated_duration=estimated_duration,
            recorded_on=data.get("recorded_on", ""),
            recorded_resolution=data.get("recorded_resolution"),
            recorded_dpi=data.get("recorded_dpi"),
            windows_version=data.get("windows_version"),
        )


@dataclass
class PlaybackSettings:
    """再生設定"""

    speed_multiplier: float = 1.0  # 再生速度倍率
    default_delay: Duration = CommonDurations.SHORT
    max_retry_attempts: int = 3
    stop_on_error: bool = True
    take_screenshots: bool = False
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR

    # Windows固有設定
    restore_window_positions: bool = True
    ensure_foreground: bool = True
    handle_uac_dialogs: bool = False  # UAC対話処理

    def validate(self) -> ValidationResult:
        """再生設定のバリデーション"""
        errors = []
        warnings = []

        if self.speed_multiplier <= 0 or self.speed_multiplier > 10:
            errors.append("再生速度倍率は0より大きく10以下である必要があります")

        if self.max_retry_attempts < 0 or self.max_retry_attempts > 10:
            errors.append("最大リトライ回数は0以上10以下である必要があります")

        if self.speed_multiplier > 5.0:
            warnings.append("再生速度が非常に高く設定されています")

        return ValidationResult(
            is_valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "speed_multiplier": self.speed_multiplier,
            "default_delay": self.default_delay.milliseconds,
            "max_retry_attempts": self.max_retry_attempts,
            "stop_on_error": self.stop_on_error,
            "take_screenshots": self.take_screenshots,
            "log_level": self.log_level,
            "restore_window_positions": self.restore_window_positions,
            "ensure_foreground": self.ensure_foreground,
            "handle_uac_dialogs": self.handle_uac_dialogs,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlaybackSettings":
        """辞書から復元"""
        return cls(
            speed_multiplier=data.get("speed_multiplier", 1.0),
            default_delay=Duration(data.get("default_delay", 500)),
            max_retry_attempts=data.get("max_retry_attempts", 3),
            stop_on_error=data.get("stop_on_error", True),
            take_screenshots=data.get("take_screenshots", False),
            log_level=data.get("log_level", "INFO"),
            restore_window_positions=data.get("restore_window_positions", True),
            ensure_foreground=data.get("ensure_foreground", True),
            handle_uac_dialogs=data.get("handle_uac_dialogs", False),
        )


@dataclass
class Recording:
    """
    Recording エンティティ - RPAレコーディング集約ルート

    一連のアクションとその実行設定を管理する中核エンティティです。
    ドメインルールの実装とビジネス不変条件の維持を担います。
    """

    # 識別情報
    recording_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""

    # 状態管理
    status: RecordingStatus = RecordingStatus.CREATED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    # アクション管理
    actions: List[ActionTypes] = field(default_factory=list)

    # 設定・メタデータ
    metadata: RecordingMetadata = field(default_factory=RecordingMetadata)
    playback_settings: PlaybackSettings = field(default_factory=PlaybackSettings)

    # 実行統計
    total_executions: int = 0
    last_execution_time: Optional[datetime] = None
    last_execution_duration: Optional[Duration] = None
    last_execution_success: Optional[bool] = None

    # ファイル情報
    file_path: Optional[Path] = None
    file_size: int = 0
    checksum: Optional[str] = None

    def __post_init__(self):
        """初期化後の処理"""
        if not self.name:
            self.name = f"記録_{self.created_at.strftime('%Y%m%d_%H%M%S')}"

        # アクションのシーケンス番号を更新
        self._update_action_sequences()

    def add_action(self, action: ActionTypes) -> Result[None, str]:
        """
        アクションを追加

        Args:
            action: 追加するアクション

        Returns:
            追加結果
        """
        # ビジネスルール検証
        if len(self.actions) >= ValidationConstants.MAX_ACTIONS_PER_RECORDING:
            return Err(
                f"アクション数の上限({ValidationConstants.MAX_ACTIONS_PER_RECORDING})に達しています"
            )

        if self.status not in [RecordingStatus.CREATED, RecordingStatus.RECORDING]:
            return Err(f"現在の状態({self.status.value})ではアクションを追加できません")

        # アクションのバリデーション
        validation_result = action.validate()
        if not validation_result.is_valid:
            return Err(
                f"アクションバリデーションエラー: {', '.join(validation_result.errors)}"
            )

        # アクションを追加
        action.sequence_number = len(self.actions)
        self.actions.append(action)

        # 状態更新
        self._update_timestamp()

        return Ok(None)

    def remove_action(self, action_id: str) -> Result[None, str]:
        """
        アクションを削除

        Args:
            action_id: 削除するアクションID

        Returns:
            削除結果
        """
        if self.status not in [RecordingStatus.CREATED, RecordingStatus.RECORDING]:
            return Err(f"現在の状態({self.status.value})ではアクションを削除できません")

        # アクションを検索・削除
        for i, action in enumerate(self.actions):
            if action.action_id == action_id:
                del self.actions[i]
                self._update_action_sequences()
                self._update_timestamp()
                return Ok(None)

        return Err(f"アクションID {action_id} が見つかりません")

    def insert_action(self, index: int, action: ActionTypes) -> Result[None, str]:
        """
        指定位置にアクションを挿入

        Args:
            index: 挿入位置
            action: 挿入するアクション

        Returns:
            挿入結果
        """
        if index < 0 or index > len(self.actions):
            return Err(f"無効なインデックスです: {index}")

        if len(self.actions) >= ValidationConstants.MAX_ACTIONS_PER_RECORDING:
            return Err(f"アクション数の上限に達しています")

        # バリデーション
        validation_result = action.validate()
        if not validation_result.is_valid:
            return Err(
                f"アクションバリデーションエラー: {', '.join(validation_result.errors)}"
            )

        # 挿入
        self.actions.insert(index, action)
        self._update_action_sequences()
        self._update_timestamp()

        return Ok(None)

    def get_action(self, action_id: str) -> Optional[ActionTypes]:
        """アクションを取得"""
        for action in self.actions:
            if action.action_id == action_id:
                return action
        return None

    def get_actions_by_type(self, action_type: type) -> List[ActionTypes]:
        """タイプ別アクション取得"""
        return [action for action in self.actions if isinstance(action, action_type)]

    def start_recording(self) -> Result[None, str]:
        """記録開始"""
        if self.status != RecordingStatus.CREATED:
            return Err(f"記録開始できない状態です: {self.status.value}")

        self.status = RecordingStatus.RECORDING
        self._update_timestamp()

        return Ok(None)

    def pause_recording(self) -> Result[None, str]:
        """記録一時停止"""
        if self.status != RecordingStatus.RECORDING:
            return Err(f"記録中ではありません: {self.status.value}")

        self.status = RecordingStatus.PAUSED
        self._update_timestamp()

        return Ok(None)

    def resume_recording(self) -> Result[None, str]:
        """記録再開"""
        if self.status != RecordingStatus.PAUSED:
            return Err(f"一時停止中ではありません: {self.status.value}")

        self.status = RecordingStatus.RECORDING
        self._update_timestamp()

        return Ok(None)

    def complete_recording(self) -> Result[None, str]:
        """記録完了"""
        if self.status not in [RecordingStatus.RECORDING, RecordingStatus.PAUSED]:
            return Err(f"記録完了できない状態です: {self.status.value}")

        if len(self.actions) == 0:
            return Err("アクションが1つもありません")

        self.status = RecordingStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self._update_timestamp()

        # 推定実行時間を計算
        self._calculate_estimated_duration()

        return Ok(None)

    def cancel_recording(self) -> Result[None, str]:
        """記録キャンセル"""
        if self.status in [RecordingStatus.COMPLETED, RecordingStatus.FAILED]:
            return Err(f"キャンセルできない状態です: {self.status.value}")

        self.status = RecordingStatus.CANCELLED
        self._update_timestamp()

        return Ok(None)

    def validate(self) -> ValidationResult:
        """レコーディング全体のバリデーション"""
        errors = []
        warnings = []

        # 名前のバリデーション
        if not self.name or len(self.name.strip()) == 0:
            errors.append("記録名が空です")
        elif len(self.name) > ValidationConstants.MAX_RECORDING_NAME_LENGTH:
            errors.append(
                f"記録名が長すぎます（{ValidationConstants.MAX_RECORDING_NAME_LENGTH}文字以内）"
            )

        # アクション数のチェック
        if len(self.actions) == 0 and self.status == RecordingStatus.COMPLETED:
            errors.append("完了状態なのにアクションがありません")

        if len(self.actions) > ValidationConstants.MAX_ACTIONS_PER_RECORDING:
            errors.append(
                f"アクション数が上限を超えています（{ValidationConstants.MAX_ACTIONS_PER_RECORDING}個以内）"
            )

        # 個別アクションのバリデーション
        for i, action in enumerate(self.actions):
            action_validation = action.validate()
            if not action_validation.is_valid:
                errors.extend(
                    [f"アクション{i+1}: {error}" for error in action_validation.errors]
                )
            warnings.extend(
                [
                    f"アクション{i+1}: {warning}"
                    for warning in action_validation.warnings
                ]
            )

        # 再生設定のバリデーション
        settings_validation = self.playback_settings.validate()
        if not settings_validation.is_valid:
            errors.extend(
                [f"再生設定: {error}" for error in settings_validation.errors]
            )
        warnings.extend(
            [f"再生設定: {warning}" for warning in settings_validation.warnings]
        )

        # 警告レベルのチェック
        if len(self.actions) > 1000:
            warnings.append("アクション数が多く、実行時間が長くなる可能性があります")

        return ValidationResult(
            is_valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    def clone(self, new_name: Optional[str] = None) -> "Recording":
        """レコーディングのクローンを作成"""
        cloned_actions = [action.clone() for action in self.actions]

        cloned = Recording(
            recording_id=str(uuid.uuid4()),
            name=new_name or f"{self.name}_コピー",
            status=RecordingStatus.CREATED,
            actions=cloned_actions,
            metadata=RecordingMetadata.from_dict(self.metadata.to_dict()),
            playback_settings=PlaybackSettings.from_dict(
                self.playback_settings.to_dict()
            ),
        )

        return cloned

    def get_estimated_duration(self) -> Duration:
        """推定実行時間を取得"""
        if self.metadata.estimated_duration:
            return self.metadata.estimated_duration

        self._calculate_estimated_duration()
        return self.metadata.estimated_duration or Duration(0)

    def mark_execution(self, success: bool, duration: Duration) -> None:
        """実行結果をマーク"""
        self.total_executions += 1
        self.last_execution_time = datetime.now(timezone.utc)
        self.last_execution_duration = duration
        self.last_execution_success = success
        self._update_timestamp()

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = {
            "recording_id": self.recording_id,
            "name": self.name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "actions": [action.to_dict() for action in self.actions],
            "metadata": self.metadata.to_dict(),
            "playback_settings": self.playback_settings.to_dict(),
            "total_executions": self.total_executions,
            "file_size": self.file_size,
            "checksum": self.checksum,
        }

        if self.completed_at:
            data["completed_at"] = self.completed_at.isoformat()

        if self.last_execution_time:
            data["last_execution_time"] = self.last_execution_time.isoformat()

        if self.last_execution_duration:
            data["last_execution_duration"] = self.last_execution_duration.milliseconds

        if self.last_execution_success is not None:
            data["last_execution_success"] = self.last_execution_success

        if self.file_path:
            data["file_path"] = str(self.file_path)

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Recording":
        """辞書から復元"""
        # アクションの復元
        actions = []
        for action_data in data.get("actions", []):
            action_type = action_data.get("action_type")

            # アクションタイプに応じて適切なクラスで復元
            if action_type in ["key_press", "text_input", "key_combination"]:
                from .action import KeyboardAction

                actions.append(KeyboardAction.from_dict(action_data))
            elif action_type in ["mouse_click", "mouse_double_click", "mouse_wheel"]:
                from .action import MouseAction

                actions.append(MouseAction.from_dict(action_data))
            elif action_type in ["window_activate", "window_resize"]:
                from .action import WindowAction

                actions.append(WindowAction.from_dict(action_data))
            elif action_type == "wait":
                from .action import WaitAction

                actions.append(WaitAction.from_dict(action_data))

        # レコーディング作成
        recording = cls(
            recording_id=data['recording_id'],
            name=data['name'],
            status=RecordingStatus(data['status']),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            actions=actions,
            metadata=RecordingMetadata.from_dict(data.get('metadata', {})),
            playback_settings=PlaybackSettings.from_dict(data.get('playback_settings', {})),
            total_executions=data.get('total_executions', 0),
            file_size=data.get('file_size', 0),
            checksum=data.get('checksum')
        )
        
        # オプショナル属性の復元
        if 'completed_at' in data:
            recording.completed_at = datetime.fromisoformat(data['completed_at'])
        
        if 'last_execution_time' in data:
            recording.last_execution_time = datetime.fromisoformat(data['last_execution_time'])
        
        if 'last_execution_duration' in data:
            recording.last_execution_duration = Duration(data['last_execution_duration'])
        
        if 'last_execution_success' in data:
            recording.last_execution_success = data['last_execution_success']
        
        if 'file_path' in data:
            recording.file_path = Path(data['file_path'])
        
        return recording

    def _update_action_sequences(self) -> None:
        """アクションのシーケンス番号を更新"""
        for i, action in enumerate(self.actions):
            action.sequence_number = i

    def _update_timestamp(self) -> None:
        """更新日時を現在時刻に設定"""
        self.updated_at = datetime.now(timezone.utc)

    def _calculate_estimated_duration(self) -> None:
        """推定実行時間を計算"""
        total_ms = 0

        for action in self.actions:
            # アクション固有の時間
            if hasattr(action, "wait_duration"):
                total_ms += action.wait_duration.milliseconds

            # 遅延時間
            total_ms += action.delay_before.milliseconds
            total_ms += action.delay_after.milliseconds

            # デフォルト実行時間（アクションタイプに応じて）
            if hasattr(action, "text") and action.text:
                # テキスト入力は文字数に比例
                total_ms += len(action.text) * 50
            else:
                # その他のアクションは固定時間
                total_ms += 100

        # 再生設定の速度倍率を適用
        total_ms = int(total_ms / self.playback_settings.speed_multiplier)

        self.metadata.estimated_duration = Duration(total_ms)

    # プロパティ
    @property
    def action_count(self) -> int:
        """アクション数"""
        return len(self.actions)

    @property
    def is_empty(self) -> bool:
        """空のレコーディングかどうか"""
        return len(self.actions) == 0

    @property
    def can_be_executed(self) -> bool:
        """実行可能かどうか"""
        return (
            self.status == RecordingStatus.COMPLETED
            and len(self.actions) > 0
            and self.validate().is_valid
        )

    @property
    def can_be_edited(self) -> bool:
        """編集可能かどうか"""
        return self.status in [
            RecordingStatus.CREATED,
            RecordingStatus.RECORDING,
            RecordingStatus.PAUSED,
        ]

    def __len__(self) -> int:
        """アクション数を返す"""
        return len(self.actions)

    def __iter__(self) -> Iterator[ActionTypes]:
        """アクションのイテレータ"""
        return iter(self.actions)

    def __getitem__(self, index: int) -> ActionTypes:
        """インデックスでアクションにアクセス"""
        return self.actions[index]
