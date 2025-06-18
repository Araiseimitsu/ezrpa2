"""
Recording リポジトリインターフェース

レコーディングデータの永続化を抽象化するリポジトリパターンの実装。
Windows環境での暗号化ストレージとデータ整合性を考慮した設計です。
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime

from ..entities.recording import Recording
from ..value_objects import RecordingStatus, ValidationResult
from ...core.result import Result, ErrorInfo


class IRecordingRepository(ABC):
    """
    Recording リポジトリインターフェース
    
    レコーディングの永続化操作を定義する抽象基底クラス。
    クリーンアーキテクチャの依存関係逆転原則に従い、
    ドメイン層がインフラ層に依存しないよう設計されています。
    """
    
    @abstractmethod
    async def save(self, recording: Recording) -> Result[str, ErrorInfo]:
        """
        レコーディングを保存
        
        Args:
            recording: 保存するレコーディング
            
        Returns:
            保存されたレコーディングIDまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, recording_id: str) -> Result[Recording, ErrorInfo]:
        """
        IDでレコーディングを取得
        
        Args:
            recording_id: レコーディングID
            
        Returns:
            レコーディングまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def get_by_name(self, name: str) -> Result[Recording, ErrorInfo]:
        """
        名前でレコーディングを取得
        
        Args:
            name: レコーディング名
            
        Returns:
            レコーディングまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def get_all(self) -> Result[List[Recording], ErrorInfo]:
        """
        全レコーディングを取得
        
        Returns:
            レコーディングリストまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def get_by_status(self, status: RecordingStatus) -> Result[List[Recording], ErrorInfo]:
        """
        ステータス別レコーディング取得
        
        Args:
            status: レコーディングステータス
            
        Returns:
            該当レコーディングリストまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def get_by_date_range(self, start_date: datetime, 
                               end_date: datetime) -> Result[List[Recording], ErrorInfo]:
        """
        日付範囲でレコーディングを取得
        
        Args:
            start_date: 開始日時
            end_date: 終了日時
            
        Returns:
            該当レコーディングリストまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def search(self, query: str, 
                    fields: Optional[List[str]] = None) -> Result[List[Recording], ErrorInfo]:
        """
        レコーディングを検索
        
        Args:
            query: 検索クエリ
            fields: 検索対象フィールド（None=全フィールド）
            
        Returns:
            検索結果リストまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def update(self, recording: Recording) -> Result[bool, ErrorInfo]:
        """
        レコーディングを更新
        
        Args:
            recording: 更新するレコーディング
            
        Returns:
            更新成功フラグまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def delete(self, recording_id: str) -> Result[bool, ErrorInfo]:
        """
        レコーディングを削除
        
        Args:
            recording_id: 削除するレコーディングID
            
        Returns:
            削除成功フラグまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def exists(self, recording_id: str) -> Result[bool, ErrorInfo]:
        """
        レコーディングの存在確認
        
        Args:
            recording_id: 確認するレコーディングID
            
        Returns:
            存在フラグまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def count(self) -> Result[int, ErrorInfo]:
        """
        総レコーディング数を取得
        
        Returns:
            レコーディング数またはエラー情報
        """
        pass
    
    @abstractmethod
    async def count_by_status(self, status: RecordingStatus) -> Result[int, ErrorInfo]:
        """
        ステータス別レコーディング数を取得
        
        Args:
            status: レコーディングステータス
            
        Returns:
            該当レコーディング数またはエラー情報
        """
        pass
    
    # バックアップ・復元機能
    @abstractmethod
    async def backup_to_file(self, file_path: Path, 
                            recording_ids: Optional[List[str]] = None) -> Result[bool, ErrorInfo]:
        """
        ファイルにバックアップ
        
        Args:
            file_path: バックアップファイルパス
            recording_ids: バックアップ対象ID（None=全て）
            
        Returns:
            バックアップ成功フラグまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def restore_from_file(self, file_path: Path, 
                               overwrite: bool = False) -> Result[int, ErrorInfo]:
        """
        ファイルから復元
        
        Args:
            file_path: 復元ファイルパス
            overwrite: 同名レコーディングの上書きフラグ
            
        Returns:
            復元されたレコーディング数またはエラー情報
        """
        pass
    
    # Windows環境固有機能
    @abstractmethod
    async def export_to_windows_task(self, recording_id: str, 
                                   task_name: str) -> Result[bool, ErrorInfo]:
        """
        Windowsタスクスケジューラーにエクスポート
        
        Args:
            recording_id: エクスポートするレコーディングID
            task_name: タスク名
            
        Returns:
            エクスポート成功フラグまたはエラー情報
        """
        pass
    
    @abstractmethod
    async def get_storage_info(self) -> Result[Dict[str, Any], ErrorInfo]:
        """
        ストレージ情報を取得
        
        Returns:
            ストレージ情報（サイズ、使用量等）またはエラー情報
        """
        pass
    
    @abstractmethod
    async def optimize_storage(self) -> Result[Dict[str, Any], ErrorInfo]:
        """
        ストレージ最適化
        
        Returns:
            最適化結果情報またはエラー情報
        """
        pass
    
    @abstractmethod
    async def validate_integrity(self) -> Result[ValidationResult, ErrorInfo]:
        """
        データ整合性検証
        
        Returns:
            検証結果またはエラー情報
        """
        pass


class IRecordingQueryBuilder(ABC):
    """
    Recording クエリビルダーインターフェース
    
    複雑な検索条件を組み立てるためのビルダーパターン実装。
    """
    
    @abstractmethod
    def where_name_contains(self, text: str) -> 'IRecordingQueryBuilder':
        """名前に指定テキストを含む"""
        pass
    
    @abstractmethod
    def where_status(self, status: RecordingStatus) -> 'IRecordingQueryBuilder':
        """指定ステータス"""
        pass
    
    @abstractmethod
    def where_created_after(self, date: datetime) -> 'IRecordingQueryBuilder':
        """指定日時以降に作成"""
        pass
    
    @abstractmethod
    def where_created_before(self, date: datetime) -> 'IRecordingQueryBuilder':
        """指定日時以前に作成"""
        pass
    
    @abstractmethod
    def where_tag_contains(self, tag: str) -> 'IRecordingQueryBuilder':
        """指定タグを含む"""
        pass
    
    @abstractmethod
    def where_action_count_greater_than(self, count: int) -> 'IRecordingQueryBuilder':
        """アクション数が指定値より大きい"""
        pass
    
    @abstractmethod
    def where_execution_count_greater_than(self, count: int) -> 'IRecordingQueryBuilder':
        """実行回数が指定値より大きい"""
        pass
    
    @abstractmethod
    def order_by_name(self, ascending: bool = True) -> 'IRecordingQueryBuilder':
        """名前順ソート"""
        pass
    
    @abstractmethod
    def order_by_created_date(self, ascending: bool = True) -> 'IRecordingQueryBuilder':
        """作成日時順ソート"""
        pass
    
    @abstractmethod
    def order_by_updated_date(self, ascending: bool = True) -> 'IRecordingQueryBuilder':
        """更新日時順ソート"""
        pass
    
    @abstractmethod
    def limit(self, count: int) -> 'IRecordingQueryBuilder':
        """結果数制限"""
        pass
    
    @abstractmethod
    def offset(self, count: int) -> 'IRecordingQueryBuilder':
        """結果オフセット"""
        pass
    
    @abstractmethod
    async def execute(self) -> Result[List[Recording], ErrorInfo]:
        """クエリを実行"""
        pass
    
    @abstractmethod
    async def count(self) -> Result[int, ErrorInfo]:
        """該当件数を取得"""
        pass


class IRecordingCache(ABC):
    """
    Recording キャッシュインターフェース
    
    パフォーマンス向上のためのキャッシュ機能を定義。
    """
    
    @abstractmethod
    async def get(self, recording_id: str) -> Optional[Recording]:
        """キャッシュからレコーディングを取得"""
        pass
    
    @abstractmethod
    async def set(self, recording: Recording, ttl_seconds: Optional[int] = None) -> None:
        """レコーディングをキャッシュに設定"""
        pass
    
    @abstractmethod
    async def delete(self, recording_id: str) -> None:
        """キャッシュからレコーディングを削除"""
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """キャッシュをクリア"""
        pass
    
    @abstractmethod
    async def get_cache_info(self) -> Dict[str, Any]:
        """キャッシュ情報を取得"""
        pass


class IRecordingEventHandler(ABC):
    """
    Recording イベントハンドラーインターフェース
    
    レコーディング操作に関するイベント処理を定義。
    """
    
    @abstractmethod
    async def on_recording_saved(self, recording: Recording) -> None:
        """レコーディング保存時"""
        pass
    
    @abstractmethod
    async def on_recording_updated(self, recording: Recording) -> None:
        """レコーディング更新時"""
        pass
    
    @abstractmethod
    async def on_recording_deleted(self, recording_id: str) -> None:
        """レコーディング削除時"""
        pass
    
    @abstractmethod
    async def on_recording_executed(self, recording: Recording, 
                                   success: bool, duration_ms: int) -> None:
        """レコーディング実行時"""
        pass


# 検索・フィルター用の型定義
class RecordingFilter:
    """レコーディングフィルター条件"""
    
    def __init__(self):
        self.name_pattern: Optional[str] = None
        self.status_list: Optional[List[RecordingStatus]] = None
        self.tag_list: Optional[List[str]] = None
        self.created_after: Optional[datetime] = None
        self.created_before: Optional[datetime] = None
        self.min_action_count: Optional[int] = None
        self.max_action_count: Optional[int] = None
        self.min_execution_count: Optional[int] = None
        self.author: Optional[str] = None
        self.category: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = {}
        
        if self.name_pattern:
            data['name_pattern'] = self.name_pattern
        
        if self.status_list:
            data['status_list'] = [status.value for status in self.status_list]
        
        if self.tag_list:
            data['tag_list'] = self.tag_list
        
        if self.created_after:
            data['created_after'] = self.created_after.isoformat()
        
        if self.created_before:
            data['created_before'] = self.created_before.isoformat()
        
        if self.min_action_count is not None:
            data['min_action_count'] = self.min_action_count
        
        if self.max_action_count is not None:
            data['max_action_count'] = self.max_action_count
        
        if self.min_execution_count is not None:
            data['min_execution_count'] = self.min_execution_count
        
        if self.author:
            data['author'] = self.author
        
        if self.category:
            data['category'] = self.category
        
        return data


class RecordingSortOrder:
    """レコーディングソート順序"""
    
    def __init__(self, field: str, ascending: bool = True):
        self.field = field
        self.ascending = ascending
    
    @classmethod
    def by_name(cls, ascending: bool = True) -> 'RecordingSortOrder':
        return cls('name', ascending)
    
    @classmethod
    def by_created_date(cls, ascending: bool = True) -> 'RecordingSortOrder':
        return cls('created_at', ascending)
    
    @classmethod
    def by_updated_date(cls, ascending: bool = True) -> 'RecordingSortOrder':
        return cls('updated_at', ascending)
    
    @classmethod
    def by_execution_count(cls, ascending: bool = False) -> 'RecordingSortOrder':
        return cls('total_executions', ascending)
    
    @classmethod
    def by_action_count(cls, ascending: bool = False) -> 'RecordingSortOrder':
        return cls('action_count', ascending)


class RecordingPagination:
    """レコーディングページネーション"""
    
    def __init__(self, page: int = 1, page_size: int = 50):
        if page < 1:
            raise ValueError("ページ番号は1以上である必要があります")
        if page_size < 1 or page_size > 1000:
            raise ValueError("ページサイズは1-1000の範囲である必要があります")
        
        self.page = page
        self.page_size = page_size
    
    @property
    def offset(self) -> int:
        """オフセット値"""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """リミット値"""
        return self.page_size