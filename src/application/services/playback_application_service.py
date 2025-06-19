"""
Playback Application Service - 再生アプリケーションサービス

再生関連の複数のユースケースを統合し、高レベルな業務処理を提供します。
再生キュー管理、同時実行制御、パフォーマンス監視などの機能も含みます。
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import asyncio
import uuid

from ...core.result import Result, Ok, Err, ErrorInfo
from ...domain import Recording, PlaybackStatus
from ...domain.repositories.recording_repository import IRecordingRepository
from ...domain.repositories.settings_repository import ISettingsRepository
from ...infrastructure.adapters.keyboard_adapter import KeyboardAdapter
from ...infrastructure.adapters.mouse_adapter import MouseAdapter
from ...infrastructure.services.windows_api_service import WindowsApiService

from ..use_cases.playback_use_cases import (
    PlayRecordingUseCase,
    PausePlaybackUseCase,
    StopPlaybackUseCase,
    GetPlaybackStatusUseCase,
    ResumePlaybackUseCase,
    ValidateRecordingUseCase,
)

from ..dto.playback_dto import (
    PlaybackDTO,
    PlaybackConfigDTO,
    PlaybackStatusDTO,
    PlaybackResultDTO,
    PlaybackQueueDTO,
    PlaybackQueueItemDTO,
    PlaybackValidationDTO,
    PlaybackHistoryDTO,
)


class PlaybackApplicationService:
    """再生アプリケーションサービス"""

    def __init__(
        self,
        recording_repository: IRecordingRepository,
        settings_repository: ISettingsRepository,
        keyboard_adapter: KeyboardAdapter,
        mouse_adapter: MouseAdapter,
        windows_api_service: Optional[WindowsApiService] = None,
    ):
        """
        初期化

        Args:
            recording_repository: 記録リポジトリ
            settings_repository: 設定リポジトリ
            keyboard_adapter: キーボードアダプター
            mouse_adapter: マウスアダプター
            windows_api_service: Windows APIサービス
        """
        self._recording_repository = recording_repository
        self._settings_repository = settings_repository
        self._keyboard_adapter = keyboard_adapter
        self._mouse_adapter = mouse_adapter
        self._windows_api_service = windows_api_service

        # ユースケースの初期化
        self._play_recording_use_case = PlayRecordingUseCase(
            recording_repository,
            settings_repository,
            keyboard_adapter,
            mouse_adapter,
            windows_api_service,
        )
        self._pause_playback_use_case = PausePlaybackUseCase(
            self._play_recording_use_case
        )
        self._stop_playback_use_case = StopPlaybackUseCase(
            self._play_recording_use_case
        )
        self._get_playback_status_use_case = GetPlaybackStatusUseCase(
            self._play_recording_use_case
        )
        self._resume_playback_use_case = ResumePlaybackUseCase(
            self._play_recording_use_case
        )
        self._validate_recording_use_case = ValidateRecordingUseCase(
            recording_repository
        )

        # 再生キュー管理
        self._playback_queue = PlaybackQueueDTO()
        self._active_sessions = {}  # session_id -> PlaybackDTO
        self._playback_history = []  # 再生履歴
        self._max_concurrent_playbacks = 1  # 同時再生数制限

        # パフォーマンス監視
        self._performance_metrics = {
            "total_playbacks": 0,
            "successful_playbacks": 0,
            "failed_playbacks": 0,
            "average_duration": 0.0,
            "last_update": datetime.now(timezone.utc),
        }

    async def start_playback(
        self, recording_id: str, config: PlaybackConfigDTO
    ) -> Result[str, ErrorInfo]:
        """
        再生を開始する

        Args:
            recording_id: 記録ID
            config: 再生設定

        Returns:
            セッションIDまたはエラー情報
        """
        try:
            # 設定のバリデーション
            validation_errors = config.validate()
            if validation_errors:
                return Err(ErrorInfo("VALIDATION_ERROR", "; ".join(validation_errors)))

            # 同時再生数チェック
            if len(self._active_sessions) >= self._max_concurrent_playbacks:
                return Err(
                    ErrorInfo(
                        "MAX_CONCURRENT_PLAYBACKS",
                        f"同時再生数上限に達しています: {self._max_concurrent_playbacks}",
                    )
                )

            # 記録の検証
            validation_result = await self._validate_recording_use_case.execute(
                recording_id
            )
            if validation_result.is_failure():
                return validation_result

            validation = validation_result.value
            if not validation["is_playable"]:
                return Err(
                    ErrorInfo(
                        "RECORDING_NOT_PLAYABLE",
                        f"記録が再生できません: {', '.join(validation['errors'])}",
                    )
                )

            # 記録の取得
            recording_result = await self._recording_repository.get_by_id(recording_id)
            if recording_result.is_failure():
                return recording_result

            recording = recording_result.value

            # 再生開始
            play_result = await self._play_recording_use_case.execute(
                recording_id=recording_id,
                speed_multiplier=config.speed_multiplier,
                start_from_action=config.start_from_action,
            )

            if play_result.is_failure():
                return play_result

            session_id = play_result.value

            # セッション情報を作成
            playback_dto = PlaybackDTO.create_new(
                session_id=session_id,
                recording_id=recording_id,
                recording_name=recording.name,
                config=config,
            )

            # アクティブセッションに追加
            self._active_sessions[session_id] = playback_dto

            # パフォーマンスメトリクスの更新
            self._performance_metrics["total_playbacks"] += 1

            return Ok(session_id)

        except Exception as e:
            return Err(ErrorInfo("START_PLAYBACK_ERROR", f"再生開始エラー: {str(e)}"))

    async def pause_playback(self, session_id: str) -> Result[bool, ErrorInfo]:
        """
        再生を一時停止する

        Args:
            session_id: セッションID

        Returns:
            成功フラグまたはエラー情報
        """
        try:
            # セッションの確認
            if session_id not in self._active_sessions:
                return Err(ErrorInfo("INVALID_SESSION", "無効なセッションIDです"))

            # 一時停止
            result = await self._pause_playback_use_case.execute(session_id)
            if result.is_failure():
                return result

            # セッション情報の更新
            playback_dto = self._active_sessions[session_id]
            playback_dto.status.status = "paused"

            return Ok(True)

        except Exception as e:
            return Err(
                ErrorInfo("PAUSE_PLAYBACK_ERROR", f"再生一時停止エラー: {str(e)}")
            )

    async def resume_playback(self, session_id: str) -> Result[bool, ErrorInfo]:
        """
        再生を再開する

        Args:
            session_id: セッションID

        Returns:
            成功フラグまたはエラー情報
        """
        try:
            # セッションの確認
            if session_id not in self._active_sessions:
                return Err(ErrorInfo("INVALID_SESSION", "無効なセッションIDです"))

            # 再開
            result = await self._resume_playback_use_case.execute(session_id)
            if result.is_failure():
                return result

            # セッション情報の更新
            playback_dto = self._active_sessions[session_id]
            playback_dto.status.status = "playing"

            return Ok(True)

        except Exception as e:
            return Err(ErrorInfo("RESUME_PLAYBACK_ERROR", f"再生再開エラー: {str(e)}"))

    async def stop_playback(
        self, session_id: str
    ) -> Result[PlaybackResultDTO, ErrorInfo]:
        """
        再生を停止する

        Args:
            session_id: セッションID

        Returns:
            再生結果DTOまたはエラー情報
        """
        try:
            # セッションの確認
            if session_id not in self._active_sessions:
                return Err(ErrorInfo("INVALID_SESSION", "無効なセッションIDです"))

            # 停止
            result = await self._stop_playback_use_case.execute(session_id)
            if result.is_failure():
                return result

            result_data = result.value

            # 結果DTOの作成
            playback_dto = self._active_sessions[session_id]
            result_dto = PlaybackResultDTO(
                session_id=session_id,
                recording_id=playback_dto.recording_id,
                recording_name=playback_dto.recording_name,
                start_time=result_data["start_time"],
                end_time=result_data["end_time"],
                duration_seconds=result_data["duration_seconds"],
                total_actions=result_data["total_actions"],
                actions_executed=result_data["actions_executed"],
                actions_succeeded=result_data["actions_executed"],  # 簡易実装
                actions_failed=0,  # 簡易実装
                completion_rate=result_data["completion_rate"],
                success_rate=1.0 if result_data["status"] == "completed" else 0.0,
                status=result_data["status"],
            )

            # 履歴に追加
            self._playback_history.append(result_dto)

            # アクティブセッションから削除
            del self._active_sessions[session_id]

            # パフォーマンスメトリクスの更新
            if result_dto.was_successful:
                self._performance_metrics["successful_playbacks"] += 1
            else:
                self._performance_metrics["failed_playbacks"] += 1

            self._update_performance_metrics()

            return Ok(result_dto)

        except Exception as e:
            return Err(ErrorInfo("STOP_PLAYBACK_ERROR", f"再生停止エラー: {str(e)}"))

    async def get_playback_status(
        self, session_id: Optional[str] = None
    ) -> Result[PlaybackStatusDTO, ErrorInfo]:
        """
        再生ステータスを取得する

        Args:
            session_id: セッションID（省略時は全セッション）

        Returns:
            ステータスDTOまたはエラー情報
        """
        try:
            # 特定セッションの場合
            if session_id:
                if session_id not in self._active_sessions:
                    return Err(ErrorInfo("INVALID_SESSION", "無効なセッションIDです"))

                result = await self._get_playback_status_use_case.execute(session_id)
                if result.is_failure():
                    return result

                status_info = result.value

                # DTOに変換
                status_dto = PlaybackStatusDTO(
                    session_id=status_info["session_id"],
                    status=status_info["status"],
                    recording_id=status_info["recording_id"],
                    recording_name=status_info["recording_name"],
                    current_action_index=status_info["current_action_index"],
                    total_actions=status_info["total_actions"],
                    progress_percentage=status_info["progress_percentage"],
                    start_time=status_info["start_time"],
                    elapsed_seconds=status_info["elapsed_seconds"],
                    estimated_remaining_seconds=None,  # 計算が必要
                    current_repeat=1,  # 簡易実装
                    total_repeats=1,  # 簡易実装
                )

                return Ok(status_dto)

            # 全セッションの場合（最初のアクティブセッション）
            else:
                if not self._active_sessions:
                    return Err(
                        ErrorInfo(
                            "NO_ACTIVE_SESSION", "アクティブなセッションがありません"
                        )
                    )

                first_session_id = next(iter(self._active_sessions.keys()))
                return await self.get_playback_status(first_session_id)

        except Exception as e:
            return Err(
                ErrorInfo(
                    "GET_PLAYBACK_STATUS_ERROR", f"ステータス取得エラー: {str(e)}"
                )
            )

    async def validate_recording_for_playback(
        self, recording_id: str
    ) -> Result[PlaybackValidationDTO, ErrorInfo]:
        """
        記録の再生可能性を検証する

        Args:
            recording_id: 記録ID

        Returns:
            検証結果DTOまたはエラー情報
        """
        try:
            # 検証の実行
            result = await self._validate_recording_use_case.execute(recording_id)
            if result.is_failure():
                return result

            validation_data = result.value

            # DTOに変換
            validation_dto = PlaybackValidationDTO(
                recording_id=recording_id,
                is_playable=validation_data["is_playable"],
                warnings=validation_data["warnings"],
                errors=validation_data["errors"],
                action_count=validation_data["action_count"],
                estimated_duration_seconds=validation_data[
                    "estimated_duration_seconds"
                ],
            )

            return Ok(validation_dto)

        except Exception as e:
            return Err(
                ErrorInfo("VALIDATE_RECORDING_ERROR", f"記録検証エラー: {str(e)}")
            )

    async def add_to_queue(
        self,
        recording_id: str,
        config: PlaybackConfigDTO,
        priority: int = 0,
        scheduled_time: Optional[datetime] = None,
    ) -> Result[str, ErrorInfo]:
        """
        再生キューに追加する

        Args:
            recording_id: 記録ID
            config: 再生設定
            priority: 優先度
            scheduled_time: 実行予定時刻

        Returns:
            キューIDまたはエラー情報
        """
        try:
            # 記録の取得
            recording_result = await self._recording_repository.get_by_id(recording_id)
            if recording_result.is_failure():
                return recording_result

            recording = recording_result.value

            # キューアイテムの作成
            queue_id = str(uuid.uuid4())
            queue_item = PlaybackQueueItemDTO(
                queue_id=queue_id,
                recording_id=recording_id,
                recording_name=recording.name,
                config=config,
                priority=priority,
                scheduled_time=scheduled_time,
            )

            # バリデーション
            validation_errors = queue_item.validate()
            if validation_errors:
                return Err(ErrorInfo("VALIDATION_ERROR", "; ".join(validation_errors)))

            # キューに追加（優先度順でソート）
            self._playback_queue.queue_items.append(queue_item)
            self._playback_queue.queue_items.sort(
                key=lambda x: (-x.priority, x.created_at)
            )
            self._playback_queue.total_items += 1

            return Ok(queue_id)

        except Exception as e:
            return Err(ErrorInfo("ADD_TO_QUEUE_ERROR", f"キュー追加エラー: {str(e)}"))

    async def get_queue_status(self) -> Result[PlaybackQueueDTO, ErrorInfo]:
        """
        再生キューの状態を取得する

        Returns:
            キューDTOまたはエラー情報
        """
        try:
            return Ok(self._playback_queue)

        except Exception as e:
            return Err(
                ErrorInfo("GET_QUEUE_STATUS_ERROR", f"キュー状態取得エラー: {str(e)}")
            )

    async def process_queue(self) -> Result[List[str], ErrorInfo]:
        """
        キューを処理する（バックグラウンド処理）

        Returns:
            処理されたセッションIDリストまたはエラー情報
        """
        try:
            processed_sessions = []

            # 実行可能なアイテムを処理
            for queue_item in self._playback_queue.pending_items:
                # 同時実行数チェック
                if len(self._active_sessions) >= self._max_concurrent_playbacks:
                    break

                # 実行時刻チェック
                if (
                    queue_item.scheduled_time
                    and queue_item.scheduled_time > datetime.now(timezone.utc)
                ):
                    continue

                # 再生開始
                session_result = await self.start_playback(
                    queue_item.recording_id, queue_item.config
                )

                if session_result.is_success():
                    session_id = session_result.value
                    processed_sessions.append(session_id)

                    # キューアイテムの状態更新
                    queue_item.status = "running"
                    self._playback_queue.current_item = queue_item
                else:
                    # 失敗した場合
                    queue_item.status = "failed"
                    self._playback_queue.failed_items += 1

            return Ok(processed_sessions)

        except Exception as e:
            return Err(ErrorInfo("PROCESS_QUEUE_ERROR", f"キュー処理エラー: {str(e)}"))

    async def get_playback_history(
        self, recording_id: Optional[str] = None, limit: int = 100
    ) -> Result[PlaybackHistoryDTO, ErrorInfo]:
        """
        再生履歴を取得する

        Args:
            recording_id: 記録ID（省略時は全記録）
            limit: 取得件数制限

        Returns:
            履歴DTOまたはエラー情報
        """
        try:
            # 履歴のフィルタリング
            filtered_history = self._playback_history
            if recording_id:
                filtered_history = [
                    h for h in filtered_history if h.recording_id == recording_id
                ]

            # 件数制限
            filtered_history = filtered_history[-limit:]

            # 履歴DTOの作成
            history_dto = PlaybackHistoryDTO.from_results(filtered_history)

            return Ok(history_dto)

        except Exception as e:
            return Err(
                ErrorInfo("GET_PLAYBACK_HISTORY_ERROR", f"履歴取得エラー: {str(e)}")
            )

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        パフォーマンスメトリクスを取得する

        Returns:
            メトリクス情報
        """
        return self._performance_metrics.copy()

    def _update_performance_metrics(self):
        """パフォーマンスメトリクスの更新"""
        if self._playback_history:
            total_duration = sum(h.duration_seconds for h in self._playback_history)
            self._performance_metrics["average_duration"] = total_duration / len(
                self._playback_history
            )

        self._performance_metrics["last_update"] = datetime.now(timezone.utc)

    async def cleanup_finished_sessions(self):
        """完了したセッションのクリーンアップ"""
        try:
            sessions_to_remove = []

            for session_id, playback_dto in self._active_sessions.items():
                status_result = await self.get_playback_status(session_id)
                if status_result.is_success():
                    status = status_result.value
                    if status.is_finished:
                        sessions_to_remove.append(session_id)

            for session_id in sessions_to_remove:
                del self._active_sessions[session_id]

        except Exception:
            pass  # クリーンアップエラーは無視
