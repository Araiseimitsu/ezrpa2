"""
Recording Use Cases - 記録関連ユースケース

記録の開始、停止、アクション追加などの具体的なビジネス処理を実装します。
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime, timezone

from ...core.result import Result, Ok, Err, ErrorInfo
from ...domain import Recording, ActionTypes, RecordingStatus
from ...domain.repositories.recording_repository import IRecordingRepository
from ...domain.repositories.settings_repository import ISettingsRepository


class UseCase(ABC):
    """ユースケース基底クラス"""
    pass


class StartRecordingUseCase(UseCase):
    """記録開始ユースケース"""
    
    def __init__(self, 
                 recording_repository: IRecordingRepository,
                 settings_repository: ISettingsRepository):
        self._recording_repository = recording_repository
        self._settings_repository = settings_repository
    
    async def execute(self, name: str, description: Optional[str] = None) -> Result[str, ErrorInfo]:
        """
        記録を開始する
        
        Args:
            name: 記録名
            description: 記録の説明
            
        Returns:
            記録IDまたはエラー情報
        """
        try:
            # 重複記録名のチェック
            existing_result = await self._recording_repository.get_by_name(name)
            if existing_result.is_success():
                return Err(ErrorInfo(
                    "RECORDING_NAME_DUPLICATE", 
                    f"同名の記録が既に存在します: {name}"
                ))
            
            # 新しい記録を作成
            recording = Recording(name=name)
            if description:
                recording.metadata.description = description
            
            # 設定から自動保存オプションを取得
            auto_save_result = await self._settings_repository.get("recording.auto_save", True)
            if auto_save_result.is_success():
                recording.metadata.auto_save = auto_save_result.value
            
            # 記録を開始
            recording.start_recording()
            
            # 記録を保存
            save_result = await self._recording_repository.save(recording)
            if save_result.is_failure():
                return save_result
            
            return Ok(recording.recording_id)
            
        except Exception as e:
            return Err(ErrorInfo("START_RECORDING_ERROR", f"記録開始エラー: {str(e)}"))


class StopRecordingUseCase(UseCase):
    """記録停止ユースケース"""
    
    def __init__(self, recording_repository: IRecordingRepository):
        self._recording_repository = recording_repository
    
    async def execute(self, recording_id: str) -> Result[Recording, ErrorInfo]:
        """
        記録を停止する
        
        Args:
            recording_id: 記録ID
            
        Returns:
            停止された記録またはエラー情報
        """
        try:
            # 記録を取得
            recording_result = await self._recording_repository.get_by_id(recording_id)
            if recording_result.is_failure():
                return recording_result
            
            recording = recording_result.value
            
            # 記録中でない場合はエラー
            if recording.status != RecordingStatus.RECORDING:
                return Err(ErrorInfo(
                    "RECORDING_NOT_ACTIVE", 
                    f"記録が開始されていません: {recording.status.value}"
                ))
            
            # 記録を完了
            recording.complete_recording()
            
            # 記録を保存
            save_result = await self._recording_repository.save(recording)
            if save_result.is_failure():
                return save_result
            
            return Ok(recording)
            
        except Exception as e:
            return Err(ErrorInfo("STOP_RECORDING_ERROR", f"記録停止エラー: {str(e)}"))


class AddActionUseCase(UseCase):
    """アクション追加ユースケース"""
    
    def __init__(self, recording_repository: IRecordingRepository):
        self._recording_repository = recording_repository
    
    async def execute(self, recording_id: str, action: ActionTypes) -> Result[bool, ErrorInfo]:
        """
        記録にアクションを追加する
        
        Args:
            recording_id: 記録ID
            action: 追加するアクション
            
        Returns:
            成功フラグまたはエラー情報
        """
        try:
            # 記録を取得
            recording_result = await self._recording_repository.get_by_id(recording_id)
            if recording_result.is_failure():
                return recording_result
            
            recording = recording_result.value
            
            # 記録中でない場合はエラー
            if recording.status != RecordingStatus.RECORDING:
                return Err(ErrorInfo(
                    "RECORDING_NOT_ACTIVE", 
                    f"記録が開始されていません: {recording.status.value}"
                ))
            
            # アクションを追加
            recording.add_action(action)
            
            # 記録を保存
            save_result = await self._recording_repository.save(recording)
            if save_result.is_failure():
                return save_result
            
            return Ok(True)
            
        except Exception as e:
            return Err(ErrorInfo("ADD_ACTION_ERROR", f"アクション追加エラー: {str(e)}"))


class GetRecordingUseCase(UseCase):
    """記録取得ユースケース"""
    
    def __init__(self, recording_repository: IRecordingRepository):
        self._recording_repository = recording_repository
    
    async def execute(self, recording_id: str) -> Result[Recording, ErrorInfo]:
        """
        記録を取得する
        
        Args:
            recording_id: 記録ID
            
        Returns:
            記録またはエラー情報
        """
        try:
            return await self._recording_repository.get_by_id(recording_id)
            
        except Exception as e:
            return Err(ErrorInfo("GET_RECORDING_ERROR", f"記録取得エラー: {str(e)}"))


class GetAllRecordingsUseCase(UseCase):
    """全記録取得ユースケース"""
    
    def __init__(self, recording_repository: IRecordingRepository):
        self._recording_repository = recording_repository
    
    async def execute(self) -> Result[List[Recording], ErrorInfo]:
        """
        全記録を取得する
        
        Returns:
            記録リストまたはエラー情報
        """
        try:
            return await self._recording_repository.get_all()
            
        except Exception as e:
            return Err(ErrorInfo("GET_ALL_RECORDINGS_ERROR", f"全記録取得エラー: {str(e)}"))


class DeleteRecordingUseCase(UseCase):
    """記録削除ユースケース"""
    
    def __init__(self, recording_repository: IRecordingRepository):
        self._recording_repository = recording_repository
    
    async def execute(self, recording_id: str) -> Result[bool, ErrorInfo]:
        """
        記録を削除する
        
        Args:
            recording_id: 記録ID
            
        Returns:
            削除成功フラグまたはエラー情報
        """
        try:
            # 記録の存在確認
            exists_result = await self._recording_repository.exists(recording_id)
            if exists_result.is_failure():
                return exists_result
            
            if not exists_result.value:
                return Err(ErrorInfo("RECORDING_NOT_FOUND", f"記録が見つかりません: {recording_id}"))
            
            # 記録を削除
            return await self._recording_repository.delete(recording_id)
            
        except Exception as e:
            return Err(ErrorInfo("DELETE_RECORDING_ERROR", f"記録削除エラー: {str(e)}"))


class SearchRecordingsUseCase(UseCase):
    """記録検索ユースケース"""
    
    def __init__(self, recording_repository: IRecordingRepository):
        self._recording_repository = recording_repository
    
    async def execute(self, query: str, limit: int = 100) -> Result[List[Recording], ErrorInfo]:
        """
        記録を検索する
        
        Args:
            query: 検索クエリ
            limit: 最大取得件数
            
        Returns:
            検索結果リストまたはエラー情報
        """
        try:
            if not query.strip():
                return Err(ErrorInfo("INVALID_SEARCH_QUERY", "検索クエリが空です"))
            
            return await self._recording_repository.search(query, limit)
            
        except Exception as e:
            return Err(ErrorInfo("SEARCH_RECORDINGS_ERROR", f"記録検索エラー: {str(e)}"))


class GetRecordingsByStatusUseCase(UseCase):
    """ステータス別記録取得ユースケース"""
    
    def __init__(self, recording_repository: IRecordingRepository):
        self._recording_repository = recording_repository
    
    async def execute(self, status: RecordingStatus) -> Result[List[Recording], ErrorInfo]:
        """
        指定ステータスの記録を取得する
        
        Args:
            status: 記録ステータス
            
        Returns:
            記録リストまたはエラー情報
        """
        try:
            return await self._recording_repository.get_by_status(status)
            
        except Exception as e:
            return Err(ErrorInfo("GET_RECORDINGS_BY_STATUS_ERROR", f"ステータス別記録取得エラー: {str(e)}"))