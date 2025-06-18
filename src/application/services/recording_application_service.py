"""
Recording Application Service - 記録アプリケーションサービス

記録関連の複数のユースケースを統合し、高レベルな業務処理を提供します。
トランザクション管理、イベント発行、キャッシュ管理などの横断的関心事も担当します。
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from ...core.result import Result, Ok, Err, ErrorInfo
from ...domain import Recording, ActionTypes, RecordingStatus
from ...domain.repositories.recording_repository import IRecordingRepository
from ...domain.repositories.settings_repository import ISettingsRepository
from ...infrastructure.services.encryption_service import EncryptionService
from ...infrastructure.services.file_service import FileService

from ..use_cases.recording_use_cases import (
    StartRecordingUseCase,
    StopRecordingUseCase,
    AddActionUseCase,
    GetRecordingUseCase,
    GetAllRecordingsUseCase,
    DeleteRecordingUseCase,
    SearchRecordingsUseCase,
    GetRecordingsByStatusUseCase,
)

from ..dto.recording_dto import (
    RecordingDTO,
    CreateRecordingDTO,
    UpdateRecordingDTO,
    RecordingListDTO,
    RecordingSummaryDTO,
    RecordingStatsDTO,
    RecordingSearchDTO,
    RecordingExportDTO,
    RecordingImportDTO,
)


class RecordingApplicationService:
    """記録アプリケーションサービス"""

    def __init__(
        self,
        recording_repository: IRecordingRepository,
        settings_repository: ISettingsRepository,
        encryption_service: EncryptionService,
        file_service: FileService,
    ):
        """
        初期化

        Args:
            recording_repository: 記録リポジトリ
            settings_repository: 設定リポジトリ
            encryption_service: 暗号化サービス
            file_service: ファイルサービス
        """
        self._recording_repository = recording_repository
        self._settings_repository = settings_repository
        self._encryption_service = encryption_service
        self._file_service = file_service

        # ユースケースの初期化
        self._start_recording_use_case = StartRecordingUseCase(
            recording_repository, settings_repository
        )
        self._stop_recording_use_case = StopRecordingUseCase(recording_repository)
        self._add_action_use_case = AddActionUseCase(recording_repository)
        self._get_recording_use_case = GetRecordingUseCase(recording_repository)
        self._get_all_recordings_use_case = GetAllRecordingsUseCase(
            recording_repository
        )
        self._delete_recording_use_case = DeleteRecordingUseCase(recording_repository)
        self._search_recordings_use_case = SearchRecordingsUseCase(recording_repository)
        self._get_recordings_by_status_use_case = GetRecordingsByStatusUseCase(
            recording_repository
        )

        # キャッシュ（簡易実装）
        self._cache = {}
        self._cache_timeout = 300  # 5分

    async def create_recording(
        self, create_dto: CreateRecordingDTO
    ) -> Result[str, ErrorInfo]:
        """
        新しい記録を作成する

        Args:
            create_dto: 記録作成DTO

        Returns:
            記録IDまたはエラー情報
        """
        try:
            # DTOのバリデーション
            validation_errors = create_dto.validate()
            if validation_errors:
                return Err(ErrorInfo("VALIDATION_ERROR", "; ".join(validation_errors)))

            # 記録の開始
            result = await self._start_recording_use_case.execute(
                name=create_dto.name, description=create_dto.description
            )

            if result.is_failure():
                return result

            recording_id = result.value

            # メタデータの更新
            recording_result = await self._get_recording_use_case.execute(recording_id)
            if recording_result.is_success():
                recording = recording_result.value
                recording.metadata.category = create_dto.category
                recording.metadata.tags = create_dto.tags.copy()
                recording.metadata.author = create_dto.author
                recording.metadata.auto_save = create_dto.auto_save

                await self._recording_repository.save(recording)

            # キャッシュをクリア
            self._clear_cache()

            return Ok(recording_id)

        except Exception as e:
            return Err(ErrorInfo("CREATE_RECORDING_ERROR", f"記録作成エラー: {str(e)}"))

    async def start_recording(self, recording_id: str) -> Result[bool, ErrorInfo]:
        """
        記録を開始する

        Args:
            recording_id: 記録ID

        Returns:
            成功フラグまたはエラー情報
        """
        try:
            # 記録の取得
            recording_result = await self._get_recording_use_case.execute(recording_id)
            if recording_result.is_failure():
                return recording_result

            recording = recording_result.value

            # 既に記録中の場合はエラー
            if recording.status == RecordingStatus.RECORDING:
                return Err(
                    ErrorInfo("RECORDING_ALREADY_STARTED", "記録は既に開始されています")
                )

            # 記録を開始
            recording.start_recording()

            # 保存
            save_result = await self._recording_repository.save(recording)
            if save_result.is_failure():
                return save_result

            # キャッシュをクリア
            self._clear_cache()

            return Ok(True)

        except Exception as e:
            return Err(ErrorInfo("START_RECORDING_ERROR", f"記録開始エラー: {str(e)}"))

    async def stop_recording(
        self, recording_id: str
    ) -> Result[RecordingDTO, ErrorInfo]:
        """
        記録を停止する

        Args:
            recording_id: 記録ID

        Returns:
            停止された記録DTOまたはエラー情報
        """
        try:
            # 記録の停止
            result = await self._stop_recording_use_case.execute(recording_id)
            if result.is_failure():
                return result

            recording = result.value

            # DTOに変換
            recording_dto = RecordingDTO.from_domain(recording)

            # キャッシュをクリア
            self._clear_cache()

            return Ok(recording_dto)

        except Exception as e:
            return Err(ErrorInfo("STOP_RECORDING_ERROR", f"記録停止エラー: {str(e)}"))

    async def add_action(
        self, recording_id: str, action: ActionTypes
    ) -> Result[bool, ErrorInfo]:
        """
        記録にアクションを追加する

        Args:
            recording_id: 記録ID
            action: 追加するアクション

        Returns:
            成功フラグまたはエラー情報
        """
        try:
            # アクションの追加
            result = await self._add_action_use_case.execute(recording_id, action)
            if result.is_failure():
                return result

            # キャッシュをクリア（該当記録のみ）
            self._clear_cache_for_recording(recording_id)

            return Ok(True)

        except Exception as e:
            return Err(ErrorInfo("ADD_ACTION_ERROR", f"アクション追加エラー: {str(e)}"))

    async def get_recording(
        self, recording_id: str, include_actions: bool = True
    ) -> Result[RecordingDTO, ErrorInfo]:
        """
        記録を取得する

        Args:
            recording_id: 記録ID
            include_actions: アクションを含むかどうか

        Returns:
            記録DTOまたはエラー情報
        """
        try:
            # キャッシュチェック
            cache_key = f"recording_{recording_id}_{include_actions}"
            cached = self._get_from_cache(cache_key)
            if cached:
                return Ok(cached)

            # 記録の取得
            result = await self._get_recording_use_case.execute(recording_id)
            if result.is_failure():
                return result

            recording = result.value

            # DTOに変換
            recording_dto = RecordingDTO.from_domain(recording, include_actions)

            # キャッシュに保存
            self._save_to_cache(cache_key, recording_dto)

            return Ok(recording_dto)

        except Exception as e:
            return Err(ErrorInfo("GET_RECORDING_ERROR", f"記録取得エラー: {str(e)}"))

    async def get_all_recordings(
        self,
        page: int = 1,
        page_size: int = 50,
        status_filter: Optional[RecordingStatus] = None,
    ) -> Result[RecordingListDTO, ErrorInfo]:
        """
        全記録を取得する（ページング対応）

        Args:
            page: ページ番号
            page_size: ページサイズ
            status_filter: ステータスフィルター

        Returns:
            記録一覧DTOまたはエラー情報
        """
        try:
            # 記録の取得
            if status_filter:
                result = await self._get_recordings_by_status_use_case.execute(
                    status_filter
                )
            else:
                result = await self._get_all_recordings_use_case.execute()

            if result.is_failure():
                return result

            recordings = result.value

            # ページング処理
            total_count = len(recordings)
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            page_recordings = recordings[start_index:end_index]

            # DTOに変換
            recording_summaries = [
                RecordingDTO.from_domain(recording, include_actions=False).to_summary()
                for recording in page_recordings
            ]

            # 一覧DTOを作成
            list_dto = RecordingListDTO(
                recordings=recording_summaries,
                total_count=total_count,
                page=page,
                page_size=page_size,
                has_next=end_index < total_count,
                has_previous=page > 1,
                filters={"status": status_filter.value if status_filter else None},
            )

            return Ok(list_dto)

        except Exception as e:
            return Err(
                ErrorInfo("GET_ALL_RECORDINGS_ERROR", f"全記録取得エラー: {str(e)}")
            )

    async def search_recordings(
        self, search_dto: RecordingSearchDTO
    ) -> Result[RecordingListDTO, ErrorInfo]:
        """
        記録を検索する

        Args:
            search_dto: 検索DTO

        Returns:
            検索結果DTOまたはエラー情報
        """
        try:
            # DTOのバリデーション
            validation_errors = search_dto.validate()
            if validation_errors:
                return Err(ErrorInfo("VALIDATION_ERROR", "; ".join(validation_errors)))

            # 検索の実行
            result = await self._search_recordings_use_case.execute(
                search_dto.query, search_dto.page_size * search_dto.page  # 簡易実装
            )

            if result.is_failure():
                return result

            recordings = result.value

            # ページング処理
            total_count = len(recordings)
            start_index = (search_dto.page - 1) * search_dto.page_size
            end_index = start_index + search_dto.page_size
            page_recordings = recordings[start_index:end_index]

            # DTOに変換
            recording_summaries = [
                RecordingDTO.from_domain(recording, include_actions=False).to_summary()
                for recording in page_recordings
            ]

            # 検索結果DTOを作成
            list_dto = RecordingListDTO(
                recordings=recording_summaries,
                total_count=total_count,
                page=search_dto.page,
                page_size=search_dto.page_size,
                has_next=end_index < total_count,
                has_previous=search_dto.page > 1,
                filters=search_dto.filters,
                sort_by=search_dto.sort_by,
                sort_order=search_dto.sort_order,
            )

            return Ok(list_dto)

        except Exception as e:
            return Err(
                ErrorInfo("SEARCH_RECORDINGS_ERROR", f"記録検索エラー: {str(e)}")
            )

    async def update_recording(
        self, recording_id: str, update_dto: UpdateRecordingDTO
    ) -> Result[RecordingDTO, ErrorInfo]:
        """
        記録を更新する

        Args:
            recording_id: 記録ID
            update_dto: 更新DTO

        Returns:
            更新された記録DTOまたはエラー情報
        """
        try:
            # DTOのバリデーション
            validation_errors = update_dto.validate()
            if validation_errors:
                return Err(ErrorInfo("VALIDATION_ERROR", "; ".join(validation_errors)))

            # 記録の取得
            recording_result = await self._get_recording_use_case.execute(recording_id)
            if recording_result.is_failure():
                return recording_result

            recording = recording_result.value

            # 更新処理
            if update_dto.name is not None:
                recording.name = update_dto.name

            if update_dto.description is not None:
                recording.description = update_dto.description

            if update_dto.category is not None:
                recording.metadata.category = update_dto.category

            if update_dto.tags is not None:
                recording.metadata.tags = update_dto.tags.copy()

            if update_dto.playback_settings is not None:
                # プレイバック設定の更新
                for key, value in update_dto.playback_settings.items():
                    if hasattr(recording.playback_settings, key):
                        setattr(recording.playback_settings, key, value)

            # 更新時刻を設定
            recording.updated_at = datetime.now(timezone.utc)

            # 保存
            save_result = await self._recording_repository.save(recording)
            if save_result.is_failure():
                return save_result

            # DTOに変換
            recording_dto = RecordingDTO.from_domain(recording)

            # キャッシュをクリア
            self._clear_cache_for_recording(recording_id)

            return Ok(recording_dto)

        except Exception as e:
            return Err(ErrorInfo("UPDATE_RECORDING_ERROR", f"記録更新エラー: {str(e)}"))

    async def delete_recording(self, recording_id: str) -> Result[bool, ErrorInfo]:
        """
        記録を削除する

        Args:
            recording_id: 記録ID

        Returns:
            削除成功フラグまたはエラー情報
        """
        try:
            # 削除前に記録情報を取得（イベント発行用）
            recording_result = await self._get_recording_use_case.execute(recording_id)
            recording_name = "Unknown"
            if recording_result.is_success():
                recording_name = recording_result.value.name

            # 記録の削除
            result = await self._delete_recording_use_case.execute(recording_id)
            if result.is_failure():
                return result

            # 削除成功時にイベントを発行
            if result.value:  # 削除が成功した場合
                # イベントバスが利用可能な場合のみイベント発行
                try:
                    from ...core.event_bus import get_event_bus

                    event_bus = get_event_bus()

                    # 削除イベントを発行
                    event_bus.publish_async(
                        {
                            "event_type": "recording_deleted",
                            "recording_id": recording_id,
                            "recording_name": recording_name,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                except Exception as e:
                    # イベント発行失敗はログに記録するが、削除処理は成功とする
                    print(f"削除イベント発行エラー: {e}")

            # キャッシュをクリア
            self._clear_cache_for_recording(recording_id)

            return Ok(True)

        except Exception as e:
            return Err(ErrorInfo("DELETE_RECORDING_ERROR", f"記録削除エラー: {str(e)}"))

    async def get_statistics(self) -> Result[RecordingStatsDTO, ErrorInfo]:
        """
        記録統計情報を取得する

        Returns:
            統計情報DTOまたはエラー情報
        """
        try:
            # キャッシュチェック
            cache_key = "recording_stats"
            cached = self._get_from_cache(cache_key)
            if cached:
                return Ok(cached)

            # 統計情報の取得
            result = await self._recording_repository.get_statistics()
            if result.is_failure():
                return result

            stats = result.value

            # DTOに変換
            stats_dto = RecordingStatsDTO.from_repository_stats(stats)

            # キャッシュに保存（短時間）
            self._save_to_cache(cache_key, stats_dto, timeout=60)

            return Ok(stats_dto)

        except Exception as e:
            return Err(
                ErrorInfo("GET_STATISTICS_ERROR", f"統計情報取得エラー: {str(e)}")
            )

    # キャッシュ管理メソッド
    def _get_from_cache(self, key: str):
        """キャッシュから取得"""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if (datetime.now().timestamp() - timestamp) < self._cache_timeout:
                return data
            else:
                del self._cache[key]
        return None

    def _save_to_cache(self, key: str, data, timeout: Optional[int] = None):
        """キャッシュに保存"""
        timeout = timeout or self._cache_timeout
        self._cache[key] = (data, datetime.now().timestamp())

    def _clear_cache(self):
        """全キャッシュをクリア"""
        self._cache.clear()

    def _clear_cache_for_recording(self, recording_id: str):
        """特定の記録に関するキャッシュをクリア"""
        keys_to_remove = [key for key in self._cache.keys() if recording_id in key]
        for key in keys_to_remove:
            del self._cache[key]
