"""
Schedule Application Service - スケジュールアプリケーションサービス

スケジュール関連の複数のユースケースを統合し、高レベルな業務処理を提供します。
スケジューラーエンジン、タスクキュー管理、実行履歴管理などの機能も含みます。
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import asyncio
import uuid

from ...core.result import Result, Ok, Err, ErrorInfo
from ...domain import Schedule, ScheduleStatus, TriggerType
from ...domain.repositories.schedule_repository import IScheduleRepository
from ...domain.repositories.recording_repository import IRecordingRepository
from ...domain.repositories.settings_repository import ISettingsRepository

from ..use_cases.schedule_use_cases import (
    CreateScheduleUseCase,
    UpdateScheduleUseCase,
    DeleteScheduleUseCase,
    GetScheduleUseCase,
    GetAllSchedulesUseCase,
    ActivateScheduleUseCase,
    DeactivateScheduleUseCase,
    GetScheduleExecutionHistoryUseCase,
    GetNextExecutionTimeUseCase
)

from ..dto.schedule_dto import (
    ScheduleDTO,
    CreateScheduleDTO,
    UpdateScheduleDTO,
    ScheduleListDTO,
    ScheduleStatsDTO,
    ExecutionResultDTO,
    ScheduleExecutionHistoryDTO,
    ScheduleValidationDTO,
    BulkScheduleOperationDTO
)

from .playback_application_service import PlaybackApplicationService
from ..dto.playback_dto import PlaybackConfigDTO


class ScheduleApplicationService:
    """スケジュールアプリケーションサービス"""
    
    def __init__(self,
                 schedule_repository: IScheduleRepository,
                 recording_repository: IRecordingRepository,
                 settings_repository: ISettingsRepository,
                 playback_service: PlaybackApplicationService):
        """
        初期化
        
        Args:
            schedule_repository: スケジュールリポジトリ
            recording_repository: 記録リポジトリ
            settings_repository: 設定リポジトリ
            playback_service: 再生アプリケーションサービス
        """
        self._schedule_repository = schedule_repository
        self._recording_repository = recording_repository
        self._settings_repository = settings_repository
        self._playback_service = playback_service
        
        # ユースケースの初期化
        self._create_schedule_use_case = CreateScheduleUseCase(
            schedule_repository, recording_repository, settings_repository
        )
        self._update_schedule_use_case = UpdateScheduleUseCase(schedule_repository)
        self._delete_schedule_use_case = DeleteScheduleUseCase(schedule_repository)
        self._get_schedule_use_case = GetScheduleUseCase(schedule_repository)
        self._get_all_schedules_use_case = GetAllSchedulesUseCase(schedule_repository)
        self._activate_schedule_use_case = ActivateScheduleUseCase(schedule_repository)
        self._deactivate_schedule_use_case = DeactivateScheduleUseCase(schedule_repository)
        self._get_execution_history_use_case = GetScheduleExecutionHistoryUseCase(schedule_repository)
        self._get_next_execution_time_use_case = GetNextExecutionTimeUseCase(schedule_repository)
        
        # スケジューラーエンジン状態
        self._scheduler_running = False
        self._scheduler_task = None
        self._execution_queue = []  # 実行待ちスケジュール
        self._active_executions = {}  # 実行中のスケジュール
        self._max_concurrent_executions = 3  # 同時実行数制限
        
        # 統計情報
        self._stats = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'average_execution_time': 0.0,
            'last_update': datetime.now(timezone.utc)
        }
    
    async def create_schedule(self, create_dto: CreateScheduleDTO) -> Result[str, ErrorInfo]:
        """
        新しいスケジュールを作成する
        
        Args:
            create_dto: スケジュール作成DTO
            
        Returns:
            スケジュールIDまたはエラー情報
        """
        try:
            # DTOのバリデーション
            validation_errors = create_dto.validate()
            if validation_errors:
                return Err(ErrorInfo("VALIDATION_ERROR", "; ".join(validation_errors)))
            
            # スケジュール作成
            result = await self._create_schedule_use_case.execute(
                name=create_dto.name,
                recording_id=create_dto.recording_id,
                trigger_type=TriggerType(create_dto.trigger_condition.trigger_type),
                trigger_config=create_dto.trigger_condition.config,
                description=create_dto.description
            )
            
            if result.is_failure():
                return result
            
            schedule_id = result.value
            
            # アクティブ状態の設定
            if create_dto.is_active:
                await self._activate_schedule_use_case.execute(schedule_id)
            
            return Ok(schedule_id)
            
        except Exception as e:
            return Err(ErrorInfo("CREATE_SCHEDULE_ERROR", f"スケジュール作成エラー: {str(e)}"))
    
    async def update_schedule(self, schedule_id: str, update_dto: UpdateScheduleDTO) -> Result[ScheduleDTO, ErrorInfo]:
        """
        スケジュールを更新する
        
        Args:
            schedule_id: スケジュールID
            update_dto: 更新DTO
            
        Returns:
            更新されたスケジュールDTOまたはエラー情報
        """
        try:
            # DTOのバリデーション
            validation_errors = update_dto.validate()
            if validation_errors:
                return Err(ErrorInfo("VALIDATION_ERROR", "; ".join(validation_errors)))
            
            # 更新データの準備
            updates = {}
            if update_dto.name is not None:
                updates['name'] = update_dto.name
            if update_dto.description is not None:
                updates['description'] = update_dto.description
            if update_dto.trigger_condition is not None:
                updates['trigger_config'] = update_dto.trigger_condition.config
            if update_dto.repeat_condition is not None:
                updates['repeat_config'] = update_dto.repeat_condition.config
            
            # 更新実行
            result = await self._update_schedule_use_case.execute(schedule_id, updates)
            if result.is_failure():
                return result
            
            schedule = result.value
            
            # アクティブ状態の更新
            if update_dto.is_active is not None:
                if update_dto.is_active:
                    await self._activate_schedule_use_case.execute(schedule_id)
                else:
                    await self._deactivate_schedule_use_case.execute(schedule_id)
                
                # 更新後のスケジュールを再取得
                updated_result = await self._get_schedule_use_case.execute(schedule_id)
                if updated_result.is_success():
                    schedule = updated_result.value
            
            # DTOに変換
            schedule_dto = ScheduleDTO.from_domain(schedule)
            
            return Ok(schedule_dto)
            
        except Exception as e:
            return Err(ErrorInfo("UPDATE_SCHEDULE_ERROR", f"スケジュール更新エラー: {str(e)}"))
    
    async def delete_schedule(self, schedule_id: str, force: bool = False) -> Result[bool, ErrorInfo]:
        """
        スケジュールを削除する
        
        Args:
            schedule_id: スケジュールID
            force: 強制削除フラグ
            
        Returns:
            削除成功フラグまたはエラー情報
        """
        try:
            # 削除実行
            result = await self._delete_schedule_use_case.execute(schedule_id, force)
            if result.is_failure():
                return result
            
            # 実行キューからも削除
            self._execution_queue = [item for item in self._execution_queue if item['schedule_id'] != schedule_id]
            
            # アクティブ実行からも削除
            if schedule_id in self._active_executions:
                # 実行中の場合は停止処理
                execution_info = self._active_executions[schedule_id]
                if 'session_id' in execution_info:
                    await self._playback_service.stop_playback(execution_info['session_id'])
                del self._active_executions[schedule_id]
            
            return Ok(True)
            
        except Exception as e:
            return Err(ErrorInfo("DELETE_SCHEDULE_ERROR", f"スケジュール削除エラー: {str(e)}"))
    
    async def get_schedule(self, schedule_id: str) -> Result[ScheduleDTO, ErrorInfo]:
        """
        スケジュールを取得する
        
        Args:
            schedule_id: スケジュールID
            
        Returns:
            スケジュールDTOまたはエラー情報
        """
        try:
            result = await self._get_schedule_use_case.execute(schedule_id)
            if result.is_failure():
                return result
            
            schedule = result.value
            schedule_dto = ScheduleDTO.from_domain(schedule)
            
            return Ok(schedule_dto)
            
        except Exception as e:
            return Err(ErrorInfo("GET_SCHEDULE_ERROR", f"スケジュール取得エラー: {str(e)}"))
    
    async def get_all_schedules(self, 
                               active_only: bool = False,
                               page: int = 1,
                               page_size: int = 50) -> Result[ScheduleListDTO, ErrorInfo]:
        """
        全スケジュールを取得する
        
        Args:
            active_only: アクティブなスケジュールのみ
            page: ページ番号
            page_size: ページサイズ
            
        Returns:
            スケジュール一覧DTOまたはエラー情報
        """
        try:
            result = await self._get_all_schedules_use_case.execute(active_only)
            if result.is_failure():
                return result
            
            schedules = result.value
            
            # ページング処理
            total_count = len(schedules)
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            page_schedules = schedules[start_index:end_index]
            
            # DTOに変換
            schedule_dtos = [ScheduleDTO.from_domain(schedule) for schedule in page_schedules]
            
            # 統計情報の計算
            active_count = sum(1 for s in schedules if s.status == ScheduleStatus.ACTIVE)
            inactive_count = sum(1 for s in schedules if s.status == ScheduleStatus.INACTIVE)
            running_count = sum(1 for s in schedules if s.status == ScheduleStatus.RUNNING)
            
            # 一覧DTOの作成
            list_dto = ScheduleListDTO(
                schedules=schedule_dtos,
                total_count=total_count,
                active_count=active_count,
                inactive_count=inactive_count,
                running_count=running_count,
                page=page,
                page_size=page_size,
                has_next=end_index < total_count,
                has_previous=page > 1,
                filters={"active_only": active_only}
            )
            
            return Ok(list_dto)
            
        except Exception as e:
            return Err(ErrorInfo("GET_ALL_SCHEDULES_ERROR", f"全スケジュール取得エラー: {str(e)}"))
    
    async def activate_schedule(self, schedule_id: str) -> Result[ScheduleDTO, ErrorInfo]:
        """
        スケジュールをアクティブ化する
        
        Args:
            schedule_id: スケジュールID
            
        Returns:
            アクティブ化されたスケジュールDTOまたはエラー情報
        """
        try:
            result = await self._activate_schedule_use_case.execute(schedule_id)
            if result.is_failure():
                return result
            
            schedule = result.value
            schedule_dto = ScheduleDTO.from_domain(schedule)
            
            return Ok(schedule_dto)
            
        except Exception as e:
            return Err(ErrorInfo("ACTIVATE_SCHEDULE_ERROR", f"スケジュールアクティブ化エラー: {str(e)}"))
    
    async def deactivate_schedule(self, schedule_id: str) -> Result[ScheduleDTO, ErrorInfo]:
        """
        スケジュールを非アクティブ化する
        
        Args:
            schedule_id: スケジュールID
            
        Returns:
            非アクティブ化されたスケジュールDTOまたはエラー情報
        """
        try:
            result = await self._deactivate_schedule_use_case.execute(schedule_id)
            if result.is_failure():
                return result
            
            schedule = result.value
            schedule_dto = ScheduleDTO.from_domain(schedule)
            
            return Ok(schedule_dto)
            
        except Exception as e:
            return Err(ErrorInfo("DEACTIVATE_SCHEDULE_ERROR", f"スケジュール非アクティブ化エラー: {str(e)}"))
    
    async def get_execution_history(self, 
                                   schedule_id: str, 
                                   limit: int = 100) -> Result[ScheduleExecutionHistoryDTO, ErrorInfo]:
        """
        スケジュールの実行履歴を取得する
        
        Args:
            schedule_id: スケジュールID
            limit: 取得件数制限
            
        Returns:
            実行履歴DTOまたはエラー情報
        """
        try:
            result = await self._get_execution_history_use_case.execute(schedule_id, limit)
            if result.is_failure():
                return result
            
            history_data = result.value
            
            # ExecutionResultDTOリストの作成
            executions = []
            for item in history_data:
                execution_dto = ExecutionResultDTO(
                    execution_id=item.get('execution_id', ''),
                    schedule_id=schedule_id,
                    recording_id=item.get('recording_id', ''),
                    started_at=item.get('started_at', datetime.now(timezone.utc)),
                    completed_at=item.get('completed_at'),
                    status=item.get('status', 'unknown'),
                    success=item.get('success', False),
                    error_message=item.get('error_message'),
                    duration_seconds=item.get('duration_seconds', 0.0)
                )
                executions.append(execution_dto)
            
            # 統計情報の計算
            total_executions = len(executions)
            successful_executions = sum(1 for e in executions if e.success)
            failed_executions = total_executions - successful_executions
            average_duration = sum(e.duration_seconds for e in executions) / max(total_executions, 1)
            last_execution = max((e.completed_at for e in executions if e.completed_at), default=None)
            
            # 次回実行時刻の取得
            next_execution_result = await self._get_next_execution_time_use_case.execute(schedule_id)
            next_execution = next_execution_result.value if next_execution_result.is_success() else None
            
            # 履歴DTOの作成
            history_dto = ScheduleExecutionHistoryDTO(
                schedule_id=schedule_id,
                executions=executions,
                total_executions=total_executions,
                successful_executions=successful_executions,
                failed_executions=failed_executions,
                average_duration_seconds=average_duration,
                last_execution=last_execution,
                next_execution=next_execution
            )
            
            return Ok(history_dto)
            
        except Exception as e:
            return Err(ErrorInfo("GET_EXECUTION_HISTORY_ERROR", f"実行履歴取得エラー: {str(e)}"))
    
    async def start_scheduler(self) -> Result[bool, ErrorInfo]:
        """
        スケジューラーを開始する
        
        Returns:
            開始成功フラグまたはエラー情報
        """
        try:
            if self._scheduler_running:
                return Ok(True)  # 既に開始済み
            
            self._scheduler_running = True
            self._scheduler_task = asyncio.create_task(self._scheduler_loop())
            
            return Ok(True)
            
        except Exception as e:
            return Err(ErrorInfo("START_SCHEDULER_ERROR", f"スケジューラー開始エラー: {str(e)}"))
    
    async def stop_scheduler(self) -> Result[bool, ErrorInfo]:
        """
        スケジューラーを停止する
        
        Returns:
            停止成功フラグまたはエラー情報
        """
        try:
            if not self._scheduler_running:
                return Ok(True)  # 既に停止済み
            
            self._scheduler_running = False
            
            if self._scheduler_task:
                self._scheduler_task.cancel()
                try:
                    await self._scheduler_task
                except asyncio.CancelledError:
                    pass
                self._scheduler_task = None
            
            return Ok(True)
            
        except Exception as e:
            return Err(ErrorInfo("STOP_SCHEDULER_ERROR", f"スケジューラー停止エラー: {str(e)}"))
    
    async def _scheduler_loop(self):
        """スケジューラーのメインループ"""
        while self._scheduler_running:
            try:
                # アクティブなスケジュールを取得
                schedules_result = await self._get_all_schedules_use_case.execute(active_only=True)
                if schedules_result.is_success():
                    schedules = schedules_result.value
                    
                    # 実行すべきスケジュールをチェック
                    for schedule in schedules:
                        if await self._should_execute_schedule(schedule):
                            await self._execute_schedule(schedule)
                
                # 実行中のスケジュールの監視
                await self._monitor_active_executions()
                
                # 1分間隔でチェック
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                # ログ出力（実装時に適切なロガーを使用）
                print(f"スケジューラーループエラー: {e}")
                await asyncio.sleep(60)
    
    async def _should_execute_schedule(self, schedule: Schedule) -> bool:
        """スケジュールが実行すべきかどうかを判定"""
        try:
            if schedule.status != ScheduleStatus.ACTIVE:
                return False
            
            if schedule.schedule_id in self._active_executions:
                return False  # 既に実行中
            
            next_time = schedule.get_next_execution_time()
            if next_time and next_time <= datetime.now(timezone.utc):
                return True
            
            return False
            
        except Exception:
            return False
    
    async def _execute_schedule(self, schedule: Schedule):
        """スケジュールを実行する"""
        try:
            # 同時実行数制限のチェック
            if len(self._active_executions) >= self._max_concurrent_executions:
                return
            
            # 実行情報の作成
            execution_id = str(uuid.uuid4())
            execution_info = {
                'execution_id': execution_id,
                'schedule_id': schedule.schedule_id,
                'recording_id': schedule.recording_id,
                'started_at': datetime.now(timezone.utc)
            }
            
            # アクティブ実行に追加
            self._active_executions[schedule.schedule_id] = execution_info
            
            # 再生設定の作成（デフォルト設定）
            playback_config = PlaybackConfigDTO()
            
            # 再生開始
            playback_result = await self._playback_service.start_playback(
                schedule.recording_id,
                playback_config
            )
            
            if playback_result.is_success():
                session_id = playback_result.value
                execution_info['session_id'] = session_id
                execution_info['status'] = 'running'
            else:
                # 実行失敗
                execution_info['status'] = 'failed'
                execution_info['error_message'] = playback_result.error
                execution_info['completed_at'] = datetime.now(timezone.utc)
                
                # アクティブ実行から削除
                del self._active_executions[schedule.schedule_id]
                
                # 統計更新
                self._stats['failed_executions'] += 1
                
        except Exception as e:
            # エラー処理
            if schedule.schedule_id in self._active_executions:
                del self._active_executions[schedule.schedule_id]
    
    async def _monitor_active_executions(self):
        """アクティブな実行を監視"""
        completed_schedules = []
        
        for schedule_id, execution_info in self._active_executions.items():
            try:
                if 'session_id' in execution_info:
                    session_id = execution_info['session_id']
                    
                    # 再生ステータスをチェック
                    status_result = await self._playback_service.get_playback_status(session_id)
                    if status_result.is_success():
                        status = status_result.value
                        
                        if status.is_finished:
                            # 実行完了
                            execution_info['completed_at'] = datetime.now(timezone.utc)
                            execution_info['status'] = 'completed' if status.status == 'completed' else 'failed'
                            execution_info['success'] = status.status == 'completed'
                            
                            duration = (execution_info['completed_at'] - execution_info['started_at']).total_seconds()
                            execution_info['duration_seconds'] = duration
                            
                            completed_schedules.append(schedule_id)
                            
                            # 統計更新
                            self._stats['total_executions'] += 1
                            if execution_info['success']:
                                self._stats['successful_executions'] += 1
                            else:
                                self._stats['failed_executions'] += 1
                
            except Exception:
                # 個別エラーは無視
                continue
        
        # 完了したスケジュールをアクティブ実行から削除
        for schedule_id in completed_schedules:
            del self._active_executions[schedule_id]
    
    async def get_statistics(self) -> Result[ScheduleStatsDTO, ErrorInfo]:
        """
        スケジュール統計情報を取得する
        
        Returns:
            統計情報DTOまたはエラー情報
        """
        try:
            # 基本統計の取得
            all_schedules_result = await self._get_all_schedules_use_case.execute()
            if all_schedules_result.is_failure():
                return all_schedules_result
            
            schedules = all_schedules_result.value
            
            # 統計計算
            total_schedules = len(schedules)
            active_schedules = sum(1 for s in schedules if s.status == ScheduleStatus.ACTIVE)
            inactive_schedules = sum(1 for s in schedules if s.status == ScheduleStatus.INACTIVE)
            running_schedules = sum(1 for s in schedules if s.status == ScheduleStatus.RUNNING)
            
            # 実行統計
            total_executions = self._stats['total_executions']
            successful_executions = self._stats['successful_executions']
            failed_executions = self._stats['failed_executions']
            overall_success_rate = successful_executions / max(total_executions, 1)
            
            # 統計DTOの作成
            stats_dto = ScheduleStatsDTO(
                total_schedules=total_schedules,
                active_schedules=active_schedules,
                inactive_schedules=inactive_schedules,
                running_schedules=running_schedules,
                total_executions=total_executions,
                successful_executions=successful_executions,
                failed_executions=failed_executions,
                average_success_rate=overall_success_rate,
                total_execution_time_seconds=0.0  # 実装時に計算
            )
            
            return Ok(stats_dto)
            
        except Exception as e:
            return Err(ErrorInfo("GET_STATISTICS_ERROR", f"統計情報取得エラー: {str(e)}"))
    
    def is_scheduler_running(self) -> bool:
        """スケジューラーが実行中かどうか"""
        return self._scheduler_running