"""
Schedule Use Cases - スケジュール関連ユースケース

スケジュールの作成、更新、削除、実行などの具体的なビジネス処理を実装します。
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta

from ...core.result import Result, Ok, Err, ErrorInfo
from ...domain import Schedule, ScheduleStatus, TriggerType
from ...domain.repositories.schedule_repository import IScheduleRepository
from ...domain.repositories.recording_repository import IRecordingRepository
from ...domain.repositories.settings_repository import ISettingsRepository


class CreateScheduleUseCase:
    """スケジュール作成ユースケース"""
    
    def __init__(self, 
                 schedule_repository: IScheduleRepository,
                 recording_repository: IRecordingRepository,
                 settings_repository: ISettingsRepository):
        self._schedule_repository = schedule_repository
        self._recording_repository = recording_repository
        self._settings_repository = settings_repository
    
    async def execute(self, 
                     name: str,
                     recording_id: str,
                     trigger_type: TriggerType,
                     trigger_config: Dict[str, Any],
                     description: Optional[str] = None) -> Result[str, ErrorInfo]:
        """
        新しいスケジュールを作成する
        
        Args:
            name: スケジュール名
            recording_id: 実行する記録のID
            trigger_type: トリガー種別
            trigger_config: トリガー設定
            description: スケジュールの説明
            
        Returns:
            スケジュールIDまたはエラー情報
        """
        try:
            # 記録の存在確認
            recording_result = await self._recording_repository.get_by_id(recording_id)
            if recording_result.is_failure():
                return Err(ErrorInfo("RECORDING_NOT_FOUND", f"指定された記録が見つかりません: {recording_id}"))
            
            recording = recording_result.value
            if recording.status != RecordingStatus.COMPLETED:
                return Err(ErrorInfo("RECORDING_NOT_COMPLETED", "完了していない記録はスケジュール実行できません"))
            
            # 重複スケジュール名のチェック
            existing_result = await self._schedule_repository.get_by_name(name)
            if existing_result.is_success():
                return Err(ErrorInfo("SCHEDULE_NAME_DUPLICATE", f"同名のスケジュールが既に存在します: {name}"))
            
            # スケジュール作成
            from ...domain import ScheduleFactory
            
            create_result = ScheduleFactory.create_schedule(
                name=name,
                recording_id=recording_id,
                trigger_type=trigger_type,
                trigger_config=trigger_config,
                description=description
            )
            
            if create_result.is_failure():
                return create_result
            
            schedule = create_result.value
            
            # スケジュールを保存
            save_result = await self._schedule_repository.save(schedule)
            if save_result.is_failure():
                return save_result
            
            return Ok(schedule.schedule_id)
            
        except Exception as e:
            return Err(ErrorInfo("CREATE_SCHEDULE_ERROR", f"スケジュール作成エラー: {str(e)}"))


class UpdateScheduleUseCase:
    """スケジュール更新ユースケース"""
    
    def __init__(self, schedule_repository: IScheduleRepository):
        self._schedule_repository = schedule_repository
    
    async def execute(self, 
                     schedule_id: str,
                     updates: Dict[str, Any]) -> Result[Schedule, ErrorInfo]:
        """
        スケジュールを更新する
        
        Args:
            schedule_id: スケジュールID
            updates: 更新内容
            
        Returns:
            更新されたスケジュールまたはエラー情報
        """
        try:
            # スケジュールを取得
            schedule_result = await self._schedule_repository.get_by_id(schedule_id)
            if schedule_result.is_failure():
                return schedule_result
            
            schedule = schedule_result.value
            
            # 実行中の場合は更新不可
            if schedule.status == ScheduleStatus.RUNNING:
                return Err(ErrorInfo("SCHEDULE_RUNNING", "実行中のスケジュールは更新できません"))
            
            # 更新処理
            if 'name' in updates:
                schedule.name = updates['name']
            
            if 'description' in updates:
                schedule.description = updates['description']
            
            if 'trigger_config' in updates:
                schedule.trigger_condition.update_config(updates['trigger_config'])
            
            if 'repeat_config' in updates:
                schedule.repeat_condition.update_config(updates['repeat_config'])
            
            if 'is_active' in updates:
                if updates['is_active']:
                    schedule.activate()
                else:
                    schedule.deactivate()
            
            # 更新時刻を設定
            schedule.updated_at = datetime.now(timezone.utc)
            
            # スケジュールを保存
            save_result = await self._schedule_repository.save(schedule)
            if save_result.is_failure():
                return save_result
            
            return Ok(schedule)
            
        except Exception as e:
            return Err(ErrorInfo("UPDATE_SCHEDULE_ERROR", f"スケジュール更新エラー: {str(e)}"))


class DeleteScheduleUseCase:
    """スケジュール削除ユースケース"""
    
    def __init__(self, schedule_repository: IScheduleRepository):
        self._schedule_repository = schedule_repository
    
    async def execute(self, schedule_id: str, force: bool = False) -> Result[bool, ErrorInfo]:
        """
        スケジュールを削除する
        
        Args:
            schedule_id: スケジュールID
            force: 実行中でも強制削除するかどうか
            
        Returns:
            削除成功フラグまたはエラー情報
        """
        try:
            # スケジュールの存在確認
            schedule_result = await self._schedule_repository.get_by_id(schedule_id)
            if schedule_result.is_failure():
                return schedule_result
            
            schedule = schedule_result.value
            
            # 実行中の場合のチェック
            if schedule.status == ScheduleStatus.RUNNING and not force:
                return Err(ErrorInfo("SCHEDULE_RUNNING", "実行中のスケジュールは削除できません（force=Trueで強制削除可能）"))
            
            # スケジュールを削除
            return await self._schedule_repository.delete(schedule_id)
            
        except Exception as e:
            return Err(ErrorInfo("DELETE_SCHEDULE_ERROR", f"スケジュール削除エラー: {str(e)}"))


class GetScheduleUseCase:
    """スケジュール取得ユースケース"""
    
    def __init__(self, schedule_repository: IScheduleRepository):
        self._schedule_repository = schedule_repository
    
    async def execute(self, schedule_id: str) -> Result[Schedule, ErrorInfo]:
        """
        スケジュールを取得する
        
        Args:
            schedule_id: スケジュールID
            
        Returns:
            スケジュールまたはエラー情報
        """
        try:
            return await self._schedule_repository.get_by_id(schedule_id)
            
        except Exception as e:
            return Err(ErrorInfo("GET_SCHEDULE_ERROR", f"スケジュール取得エラー: {str(e)}"))


class GetAllSchedulesUseCase:
    """全スケジュール取得ユースケース"""
    
    def __init__(self, schedule_repository: IScheduleRepository):
        self._schedule_repository = schedule_repository
    
    async def execute(self, active_only: bool = False) -> Result[List[Schedule], ErrorInfo]:
        """
        全スケジュールを取得する
        
        Args:
            active_only: アクティブなスケジュールのみ取得するかどうか
            
        Returns:
            スケジュールリストまたはエラー情報
        """
        try:
            if active_only:
                return await self._schedule_repository.get_by_status(ScheduleStatus.ACTIVE)
            else:
                return await self._schedule_repository.get_all()
            
        except Exception as e:
            return Err(ErrorInfo("GET_ALL_SCHEDULES_ERROR", f"全スケジュール取得エラー: {str(e)}"))


class ActivateScheduleUseCase:
    """スケジュールアクティブ化ユースケース"""
    
    def __init__(self, schedule_repository: IScheduleRepository):
        self._schedule_repository = schedule_repository
    
    async def execute(self, schedule_id: str) -> Result[Schedule, ErrorInfo]:
        """
        スケジュールをアクティブ化する
        
        Args:
            schedule_id: スケジュールID
            
        Returns:
            アクティブ化されたスケジュールまたはエラー情報
        """
        try:
            # スケジュールを取得
            schedule_result = await self._schedule_repository.get_by_id(schedule_id)
            if schedule_result.is_failure():
                return schedule_result
            
            schedule = schedule_result.value
            
            # すでにアクティブな場合は何もしない
            if schedule.status == ScheduleStatus.ACTIVE:
                return Ok(schedule)
            
            # アクティブ化
            schedule.activate()
            
            # スケジュールを保存
            save_result = await self._schedule_repository.save(schedule)
            if save_result.is_failure():
                return save_result
            
            return Ok(schedule)
            
        except Exception as e:
            return Err(ErrorInfo("ACTIVATE_SCHEDULE_ERROR", f"スケジュールアクティブ化エラー: {str(e)}"))


class DeactivateScheduleUseCase:
    """スケジュール非アクティブ化ユースケース"""
    
    def __init__(self, schedule_repository: IScheduleRepository):
        self._schedule_repository = schedule_repository
    
    async def execute(self, schedule_id: str) -> Result[Schedule, ErrorInfo]:
        """
        スケジュールを非アクティブ化する
        
        Args:
            schedule_id: スケジュールID
            
        Returns:
            非アクティブ化されたスケジュールまたはエラー情報
        """
        try:
            # スケジュールを取得
            schedule_result = await self._schedule_repository.get_by_id(schedule_id)
            if schedule_result.is_failure():
                return schedule_result
            
            schedule = schedule_result.value
            
            # 実行中の場合は非アクティブ化不可
            if schedule.status == ScheduleStatus.RUNNING:
                return Err(ErrorInfo("SCHEDULE_RUNNING", "実行中のスケジュールは非アクティブ化できません"))
            
            # すでに非アクティブな場合は何もしない
            if schedule.status == ScheduleStatus.INACTIVE:
                return Ok(schedule)
            
            # 非アクティブ化
            schedule.deactivate()
            
            # スケジュールを保存
            save_result = await self._schedule_repository.save(schedule)
            if save_result.is_failure():
                return save_result
            
            return Ok(schedule)
            
        except Exception as e:
            return Err(ErrorInfo("DEACTIVATE_SCHEDULE_ERROR", f"スケジュール非アクティブ化エラー: {str(e)}"))


class GetScheduleExecutionHistoryUseCase:
    """スケジュール実行履歴取得ユースケース"""
    
    def __init__(self, schedule_repository: IScheduleRepository):
        self._schedule_repository = schedule_repository
    
    async def execute(self, 
                     schedule_id: str, 
                     limit: int = 100) -> Result[List[Dict[str, Any]], ErrorInfo]:
        """
        スケジュールの実行履歴を取得する
        
        Args:
            schedule_id: スケジュールID
            limit: 取得件数制限
            
        Returns:
            実行履歴リストまたはエラー情報
        """
        try:
            # スケジュールの存在確認
            schedule_result = await self._schedule_repository.get_by_id(schedule_id)
            if schedule_result.is_failure():
                return schedule_result
            
            # 実行履歴を取得
            return await self._schedule_repository.get_execution_history(schedule_id, limit)
            
        except Exception as e:
            return Err(ErrorInfo("GET_EXECUTION_HISTORY_ERROR", f"実行履歴取得エラー: {str(e)}"))


class GetNextExecutionTimeUseCase:
    """次回実行時刻取得ユースケース"""
    
    def __init__(self, schedule_repository: IScheduleRepository):
        self._schedule_repository = schedule_repository
    
    async def execute(self, schedule_id: str) -> Result[Optional[datetime], ErrorInfo]:
        """
        スケジュールの次回実行時刻を取得する
        
        Args:
            schedule_id: スケジュールID
            
        Returns:
            次回実行時刻またはエラー情報
        """
        try:
            # スケジュールを取得
            schedule_result = await self._schedule_repository.get_by_id(schedule_id)
            if schedule_result.is_failure():
                return schedule_result
            
            schedule = schedule_result.value
            
            # アクティブでない場合はNone
            if schedule.status != ScheduleStatus.ACTIVE:
                return Ok(None)
            
            # 次回実行時刻を計算
            next_time = schedule.get_next_execution_time()
            return Ok(next_time)
            
        except Exception as e:
            return Err(ErrorInfo("GET_NEXT_EXECUTION_TIME_ERROR", f"次回実行時刻取得エラー: {str(e)}"))