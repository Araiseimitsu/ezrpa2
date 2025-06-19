"""
Playback Use Cases - 再生関連ユースケース

記録の再生、一時停止、停止などの具体的なビジネス処理を実装します。
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from ...core.result import Result, Ok, Err, ErrorInfo
from ...domain import Recording, PlaybackStatus
from ...domain.repositories.recording_repository import IRecordingRepository
from ...domain.repositories.settings_repository import ISettingsRepository
from ...infrastructure.adapters.keyboard_adapter import KeyboardAdapter
from ...infrastructure.adapters.mouse_adapter import MouseAdapter
from ...infrastructure.services.windows_api_service import WindowsApiService


class PlayRecordingUseCase:
    """記録再生ユースケース"""

    def __init__(
        self,
        recording_repository: IRecordingRepository,
        settings_repository: ISettingsRepository,
        keyboard_adapter: KeyboardAdapter,
        mouse_adapter: MouseAdapter,
        windows_api_service: Optional[WindowsApiService] = None,
    ):
        self._recording_repository = recording_repository
        self._settings_repository = settings_repository
        self._keyboard_adapter = keyboard_adapter
        self._mouse_adapter = mouse_adapter
        self._windows_api_service = windows_api_service
        self._current_playback = None
        self._playback_status = PlaybackStatus.READY

    async def execute(
        self,
        recording_id: str,
        speed_multiplier: float = 1.0,
        start_from_action: int = 0,
    ) -> Result[str, ErrorInfo]:
        """
        記録を再生する

        Args:
            recording_id: 記録ID
            speed_multiplier: 再生速度倍率
            start_from_action: 開始アクション番号

        Returns:
            再生セッションIDまたはエラー情報
        """
        try:
            # 記録を取得
            recording_result = await self._recording_repository.get_by_id(recording_id)
            if recording_result.is_failure():
                return recording_result

            recording = recording_result.value

            # 再生可能な状態かチェック
            if recording.status != RecordingStatus.COMPLETED:
                return Err(
                    ErrorInfo(
                        "RECORDING_NOT_PLAYABLE",
                        f"記録が再生可能な状態ではありません: {recording.status.value}",
                    )
                )

            if not recording.actions:
                return Err(ErrorInfo("RECORDING_EMPTY", "記録にアクションがありません"))

            # 再生設定を取得
            playback_config = await self._load_playback_config(speed_multiplier)

            # 再生開始前にすべてのウィンドウを最小化
            if self._windows_api_service:
                minimize_result = self._windows_api_service.minimize_all_windows()
                if minimize_result.is_failure():
                    # 最小化に失敗してもログに記録して継続
                    print(
                        f"警告: ウィンドウ最小化に失敗しました: {minimize_result.error}"
                    )

            # 再生セッションIDを生成
            import uuid

            session_id = str(uuid.uuid4())

            # 再生状態を設定
            self._current_playback = {
                "session_id": session_id,
                "recording": recording,
                "config": playback_config,
                "current_action_index": start_from_action,
                "start_time": datetime.now(timezone.utc),
                "pause_time": None,
            }
            self._playback_status = PlaybackStatus.PLAYING

            return Ok(session_id)

        except Exception as e:
            return Err(ErrorInfo("PLAY_RECORDING_ERROR", f"記録再生エラー: {str(e)}"))

    async def _load_playback_config(self, speed_multiplier: float) -> Dict[str, Any]:
        """再生設定を読み込み"""
        config = {
            "speed_multiplier": speed_multiplier,
            "default_delay": 500,  # デフォルト500ms
            "stop_on_error": True,
            "take_screenshots": False,
        }

        # 設定から値を取得
        delay_result = await self._settings_repository.get(
            "playback.default_delay", 500
        )
        if delay_result.is_success():
            config["default_delay"] = delay_result.value

        stop_on_error_result = await self._settings_repository.get(
            "playback.stop_on_error", True
        )
        if stop_on_error_result.is_success():
            config["stop_on_error"] = stop_on_error_result.value

        screenshots_result = await self._settings_repository.get(
            "playback.take_screenshots", False
        )
        if screenshots_result.is_success():
            config["take_screenshots"] = screenshots_result.value

        return config


class PausePlaybackUseCase:
    """再生一時停止ユースケース"""

    def __init__(self, play_use_case: PlayRecordingUseCase):
        self._play_use_case = play_use_case

    async def execute(self, session_id: str) -> Result[bool, ErrorInfo]:
        """
        再生を一時停止する

        Args:
            session_id: 再生セッションID

        Returns:
            成功フラグまたはエラー情報
        """
        try:
            # セッションの確認
            if (
                not self._play_use_case._current_playback
                or self._play_use_case._current_playback["session_id"] != session_id
            ):
                return Err(
                    ErrorInfo("INVALID_PLAYBACK_SESSION", "無効な再生セッションです")
                )

            # 再生中でない場合はエラー
            if self._play_use_case._playback_status != PlaybackStatus.PLAYING:
                return Err(
                    ErrorInfo(
                        "PLAYBACK_NOT_ACTIVE",
                        f"再生が開始されていません: {self._play_use_case._playback_status.value}",
                    )
                )

            # 一時停止状態に変更
            self._play_use_case._playback_status = PlaybackStatus.PAUSED
            self._play_use_case._current_playback["pause_time"] = datetime.now(
                timezone.utc
            )

            return Ok(True)

        except Exception as e:
            return Err(
                ErrorInfo("PAUSE_PLAYBACK_ERROR", f"再生一時停止エラー: {str(e)}")
            )


class StopPlaybackUseCase:
    """再生停止ユースケース"""

    def __init__(self, play_use_case: PlayRecordingUseCase):
        self._play_use_case = play_use_case

    async def execute(self, session_id: str) -> Result[Dict[str, Any], ErrorInfo]:
        """
        再生を停止する

        Args:
            session_id: 再生セッションID

        Returns:
            再生結果情報またはエラー情報
        """
        try:
            # セッションの確認
            if (
                not self._play_use_case._current_playback
                or self._play_use_case._current_playback["session_id"] != session_id
            ):
                return Err(
                    ErrorInfo("INVALID_PLAYBACK_SESSION", "無効な再生セッションです")
                )

            # 再生結果を構築
            current = self._play_use_case._current_playback
            end_time = datetime.now(timezone.utc)

            result = {
                "session_id": session_id,
                "recording_id": current["recording"].recording_id,
                "recording_name": current["recording"].name,
                "start_time": current["start_time"],
                "end_time": end_time,
                "duration_seconds": (end_time - current["start_time"]).total_seconds(),
                "actions_executed": current["current_action_index"],
                "total_actions": len(current["recording"].actions),
                "completion_rate": current["current_action_index"]
                / len(current["recording"].actions),
                "status": (
                    "completed"
                    if current["current_action_index"]
                    >= len(current["recording"].actions)
                    else "stopped"
                ),
            }

            # 再生状態をリセット
            self._play_use_case._current_playback = None
            self._play_use_case._playback_status = PlaybackStatus.READY

            return Ok(result)

        except Exception as e:
            return Err(ErrorInfo("STOP_PLAYBACK_ERROR", f"再生停止エラー: {str(e)}"))


class GetPlaybackStatusUseCase:
    """再生ステータス取得ユースケース"""

    def __init__(self, play_use_case: PlayRecordingUseCase):
        self._play_use_case = play_use_case

    async def execute(
        self, session_id: Optional[str] = None
    ) -> Result[Dict[str, Any], ErrorInfo]:
        """
        再生ステータスを取得する

        Args:
            session_id: 再生セッションID（省略時は現在のセッション）

        Returns:
            ステータス情報またはエラー情報
        """
        try:
            current = self._play_use_case._current_playback

            # セッションIDが指定されている場合は確認
            if session_id and (not current or current["session_id"] != session_id):
                return Err(
                    ErrorInfo("INVALID_PLAYBACK_SESSION", "無効な再生セッションです")
                )

            # 基本ステータス
            status_info = {
                "status": self._play_use_case._playback_status.value,
                "has_active_session": current is not None,
            }

            # アクティブセッションがある場合は詳細情報を追加
            if current:
                now = datetime.now(timezone.utc)

                status_info.update(
                    {
                        "session_id": current["session_id"],
                        "recording_id": current["recording"].recording_id,
                        "recording_name": current["recording"].name,
                        "start_time": current["start_time"],
                        "current_action_index": current["current_action_index"],
                        "total_actions": len(current["recording"].actions),
                        "progress_percentage": (
                            current["current_action_index"]
                            / len(current["recording"].actions)
                        )
                        * 100,
                        "elapsed_seconds": (
                            now - current["start_time"]
                        ).total_seconds(),
                        "speed_multiplier": current["config"]["speed_multiplier"],
                    }
                )

                # 一時停止中の場合は一時停止時間も追加
                if (
                    self._play_use_case._playback_status == PlaybackStatus.PAUSED
                    and current["pause_time"]
                ):
                    status_info["pause_time"] = current["pause_time"]
                    status_info["paused_duration_seconds"] = (
                        now - current["pause_time"]
                    ).total_seconds()

            return Ok(status_info)

        except Exception as e:
            return Err(
                ErrorInfo(
                    "GET_PLAYBACK_STATUS_ERROR", f"再生ステータス取得エラー: {str(e)}"
                )
            )


class ResumePlaybackUseCase:
    """再生再開ユースケース"""

    def __init__(self, play_use_case: PlayRecordingUseCase):
        self._play_use_case = play_use_case

    async def execute(self, session_id: str) -> Result[bool, ErrorInfo]:
        """
        一時停止中の再生を再開する

        Args:
            session_id: 再生セッションID

        Returns:
            成功フラグまたはエラー情報
        """
        try:
            # セッションの確認
            if (
                not self._play_use_case._current_playback
                or self._play_use_case._current_playback["session_id"] != session_id
            ):
                return Err(
                    ErrorInfo("INVALID_PLAYBACK_SESSION", "無効な再生セッションです")
                )

            # 一時停止中でない場合はエラー
            if self._play_use_case._playback_status != PlaybackStatus.PAUSED:
                return Err(
                    ErrorInfo(
                        "PLAYBACK_NOT_PAUSED",
                        f"再生が一時停止されていません: {self._play_use_case._playback_status.value}",
                    )
                )

            # 再生状態に変更
            self._play_use_case._playback_status = PlaybackStatus.PLAYING
            self._play_use_case._current_playback["pause_time"] = None

            return Ok(True)

        except Exception as e:
            return Err(ErrorInfo("RESUME_PLAYBACK_ERROR", f"再生再開エラー: {str(e)}"))


class ValidateRecordingUseCase:
    """記録検証ユースケース"""

    def __init__(self, recording_repository: IRecordingRepository):
        self._recording_repository = recording_repository

    async def execute(self, recording_id: str) -> Result[Dict[str, Any], ErrorInfo]:
        """
        記録の再生可能性を検証する

        Args:
            recording_id: 記録ID

        Returns:
            検証結果またはエラー情報
        """
        try:
            # 記録を取得
            recording_result = await self._recording_repository.get_by_id(recording_id)
            if recording_result.is_failure():
                return recording_result

            recording = recording_result.value

            validation_result = {
                "recording_id": recording_id,
                "is_playable": True,
                "warnings": [],
                "errors": [],
                "action_count": len(recording.actions),
                "estimated_duration_seconds": recording.get_estimated_duration().seconds,
            }

            # 基本チェック
            if recording.status != RecordingStatus.COMPLETED:
                validation_result["is_playable"] = False
                validation_result["errors"].append(
                    f"記録が完了していません: {recording.status.value}"
                )

            if not recording.actions:
                validation_result["is_playable"] = False
                validation_result["errors"].append("記録にアクションがありません")

            # アクションの妥当性チェック
            for i, action in enumerate(recording.actions):
                try:
                    # アクションの基本チェック
                    if not hasattr(action, "action_type"):
                        validation_result["warnings"].append(
                            f"アクション {i}: 不明なアクション形式"
                        )

                    # 座標の範囲チェック（マウス操作の場合）
                    if hasattr(action, "position"):
                        pos = action.position
                        if pos.x < 0 or pos.y < 0 or pos.x > 9999 or pos.y > 9999:
                            validation_result["warnings"].append(
                                f"アクション {i}: 座標が範囲外の可能性があります ({pos.x}, {pos.y})"
                            )

                except Exception as e:
                    validation_result["warnings"].append(
                        f"アクション {i}: 検証中にエラー: {str(e)}"
                    )

            return Ok(validation_result)

        except Exception as e:
            return Err(
                ErrorInfo("VALIDATE_RECORDING_ERROR", f"記録検証エラー: {str(e)}")
            )
