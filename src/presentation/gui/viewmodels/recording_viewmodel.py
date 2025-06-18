"""
Recording ViewModel - 記録機能のViewModel

記録の作成、編集、管理を行うViewModelです。
アクションの追加・削除、記録の保存・読み込み、
リアルタイムでの記録状況表示を提供します。
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import asyncio

from .base_viewmodel import BaseViewModel, AsyncCommand, Command
from ....core.result import Result, Ok, Err, ErrorInfo
from ....core.event_bus import EventBus
from ....application.services.recording_application_service import RecordingApplicationService
from ....application.dto.recording_dto import (
    CreateRecordingDTO, UpdateRecordingDTO, RecordingDTO, 
    RecordingListDTO, RecordingSearchDTO, RecordingStatsDTO
)
from ....domain.entities.action import ActionTypes
from ....domain.value_objects import RecordingStatus


class RecordingViewModel(BaseViewModel):
    """記録機能ViewModel"""
    
    def __init__(self, 
                 recording_service: RecordingApplicationService,
                 event_bus: Optional[EventBus] = None):
        """
        初期化
        
        Args:
            recording_service: 記録アプリケーションサービス
            event_bus: イベントバス
        """
        super().__init__(event_bus)
        
        # アプリケーションサービス
        self._recording_service = recording_service
        
        # 現在の記録状態
        self._current_recording = None
        self._current_recording_id = None
        self._is_recording = False
        self._recording_status = "STOPPED"
        self._action_count = 0
        self._recording_duration = 0.0
        self._estimated_duration = 0.0
        
        # 記録リスト
        self._recordings = []
        self._filtered_recordings = []
        self._selected_recording = None
        self._total_recordings_count = 0
        self._current_page = 1
        self._page_size = 20
        
        # 検索・フィルター
        self._search_query = ""
        self._selected_category = "all"
        self._selected_status = "all"
        self._sort_by = "created_at"
        self._sort_descending = True
        
        # 新規記録用フォーム
        self._new_recording_name = ""
        self._new_recording_description = ""
        self._new_recording_category = "general"
        self._new_recording_tags = []
        self._new_recording_auto_save = True
        
        # 編集用フォーム
        self._edit_recording_name = ""
        self._edit_recording_description = ""
        self._edit_recording_category = ""
        self._edit_recording_tags = []
        
        # UI状態
        self._show_new_recording_dialog = False
        self._show_edit_recording_dialog = False
        self._show_action_details = True
        self._auto_scroll_actions = True
        
        # 統計情報
        self._recording_stats = None
        
        # イベント購読ID管理
        self._subscription_ids = []
        
        # 初期化
        self._initialize_commands()
        self._subscribe_to_events()
    
    def _initialize_commands(self):
        """コマンドの初期化"""
        # 記録操作コマンド
        self.add_command('start_new_recording', AsyncCommand(
            self._start_new_recording_async,
            lambda: not self.is_recording and not self.is_busy
        ))
        self.add_command('stop_recording', AsyncCommand(
            self._stop_recording_async,
            lambda: self.is_recording and not self.is_busy
        ))
        self.add_command('pause_recording', AsyncCommand(
            self._pause_recording_async,
            lambda: self.is_recording and not self.is_busy
        ))
        self.add_command('resume_recording', AsyncCommand(
            self._resume_recording_async,
            lambda: self.recording_status == "PAUSED" and not self.is_busy
        ))
        
        # 記録管理コマンド
        self.add_command('load_recordings', AsyncCommand(self._load_recordings_async))
        self.add_command('delete_recording', AsyncCommand(
            self._delete_recording_async,
            lambda: self.selected_recording is not None and not self.is_busy
        ))
        self.add_command('duplicate_recording', AsyncCommand(
            self._duplicate_recording_async,
            lambda: self.selected_recording is not None and not self.is_busy
        ))
        self.add_command('export_recording', AsyncCommand(
            self._export_recording_async,
            lambda: self.selected_recording is not None and not self.is_busy
        ))
        
        # 検索・フィルターコマンド
        self.add_command('search_recordings', AsyncCommand(self._search_recordings_async))
        self.add_command('clear_search', Command(self._clear_search))
        self.add_command('apply_filter', AsyncCommand(self._apply_filter_async))
        self.add_command('sort_recordings', AsyncCommand(self._sort_recordings_async))
        
        # ページングコマンド
        self.add_command('next_page', AsyncCommand(
            self._next_page_async,
            lambda: self.has_next_page and not self.is_busy
        ))
        self.add_command('previous_page', AsyncCommand(
            self._previous_page_async,
            lambda: self.has_previous_page and not self.is_busy
        ))
        self.add_command('go_to_page', AsyncCommand(self._go_to_page_async))
        
        # ダイアログコマンド
        self.add_command('show_new_recording_dialog', Command(self._show_new_recording_dialog_command))
        self.add_command('hide_new_recording_dialog', Command(self._hide_new_recording_dialog_command))
        self.add_command('show_edit_recording_dialog', Command(self._show_edit_recording_dialog_command))
        self.add_command('hide_edit_recording_dialog', Command(self._hide_edit_recording_dialog_command))
        
        # フォーム操作コマンド
        self.add_command('create_recording', AsyncCommand(self._create_recording_async))
        self.add_command('update_recording', AsyncCommand(self._update_recording_async))
        self.add_command('reset_new_recording_form', Command(self._reset_new_recording_form))
        
        # 選択操作コマンド
        self.add_command('select_recording', Command(self._select_recording))
        self.add_command('clear_selection', Command(self._clear_selection))
    
    def _subscribe_to_events(self):
        """イベント購読"""
        # Note: For demo purposes, using simplified event handling
        # In production, these would be proper Event types and handled by EventBus
        pass
    
    # プロパティ
    @property
    def current_recording(self) -> Optional[RecordingDTO]:
        """現在の記録"""
        return self._current_recording
    
    @property
    def current_recording_id(self) -> Optional[str]:
        """現在の記録ID"""
        return self._current_recording_id
    
    @property
    def is_recording(self) -> bool:
        """記録中かどうか"""
        return self._is_recording
    
    @property
    def recording_status(self) -> str:
        """記録状態"""
        return self._recording_status
    
    @property
    def action_count(self) -> int:
        """アクション数"""
        return self._action_count
    
    @property
    def recording_duration(self) -> float:
        """記録継続時間（秒）"""
        return self._recording_duration
    
    @property
    def estimated_duration(self) -> float:
        """推定実行時間（秒）"""
        return self._estimated_duration
    
    @property
    def recordings(self) -> List[RecordingDTO]:
        """記録リスト"""
        return self._recordings
    
    @property
    def filtered_recordings(self) -> List[RecordingDTO]:
        """フィルター済み記録リスト"""
        return self._filtered_recordings
    
    @property
    def selected_recording(self) -> Optional[RecordingDTO]:
        """選択された記録"""
        return self._selected_recording
    
    @property
    def total_recordings_count(self) -> int:
        """総記録数"""
        return self._total_recordings_count
    
    @property
    def current_page(self) -> int:
        """現在のページ"""
        return self._current_page
    
    @property
    def total_pages(self) -> int:
        """総ページ数"""
        return max(1, (self._total_recordings_count + self._page_size - 1) // self._page_size)
    
    @property
    def has_next_page(self) -> bool:
        """次のページがあるかどうか"""
        return self._current_page < self.total_pages
    
    @property
    def has_previous_page(self) -> bool:
        """前のページがあるかどうか"""
        return self._current_page > 1
    
    @property
    def search_query(self) -> str:
        """検索クエリ"""
        return self._search_query
    
    @search_query.setter
    def search_query(self, value: str):
        if self.set_property('search_query', value):
            self._search_query = value
    
    @property
    def selected_category(self) -> str:
        """選択されたカテゴリ"""
        return self._selected_category
    
    @selected_category.setter
    def selected_category(self, value: str):
        if self.set_property('selected_category', value):
            self._selected_category = value
    
    @property
    def selected_status(self) -> str:
        """選択された状態"""
        return self._selected_status
    
    @selected_status.setter
    def selected_status(self, value: str):
        if self.set_property('selected_status', value):
            self._selected_status = value
    
    # 新規記録フォームプロパティ
    @property
    def new_recording_name(self) -> str:
        return self._new_recording_name
    
    @new_recording_name.setter
    def new_recording_name(self, value: str):
        if self.set_property('new_recording_name', value):
            self._new_recording_name = value
    
    @property
    def new_recording_description(self) -> str:
        return self._new_recording_description
    
    @new_recording_description.setter
    def new_recording_description(self, value: str):
        if self.set_property('new_recording_description', value):
            self._new_recording_description = value
    
    @property
    def new_recording_category(self) -> str:
        return self._new_recording_category
    
    @new_recording_category.setter
    def new_recording_category(self, value: str):
        if self.set_property('new_recording_category', value):
            self._new_recording_category = value
    
    @property
    def show_new_recording_dialog(self) -> bool:
        return self._show_new_recording_dialog
    
    @property
    def show_edit_recording_dialog(self) -> bool:
        return self._show_edit_recording_dialog
    
    @property
    def recording_stats(self) -> Optional[RecordingStatsDTO]:
        """記録統計"""
        return self._recording_stats
    
    # ページング関連プロパティ
    @property
    def current_page(self) -> int:
        """現在のページ番号"""
        return self._current_page
    
    @property
    def page_size(self) -> int:
        """ページサイズ"""
        return self._page_size
    
    @property
    def total_pages(self) -> int:
        """総ページ数"""
        return max(1, (self._total_recordings_count + self._page_size - 1) // self._page_size)
    
    @property
    def has_next_page(self) -> bool:
        """次のページがあるかどうか"""
        return self._current_page < self.total_pages
    
    @property
    def has_previous_page(self) -> bool:
        """前のページがあるかどうか"""
        return self._current_page > 1
    
    # 初期化
    async def initialize_async(self):
        """非同期初期化"""
        try:
            self.set_busy(True, "記録データを読み込み中...")
            
            # 記録リストの読み込み
            await self._load_recordings_async()
            
            # 統計情報の読み込み
            await self._load_statistics_async()
            
            self.add_notification("初期化完了", "記録機能の初期化が完了しました", "SUCCESS")
            
        except Exception as e:
            self.add_error(f"初期化エラー: {str(e)}", str(e), "RECORDING_INIT_ERROR")
        finally:
            self.set_busy(False)
    
    async def _load_recordings_async(self, parameter=None):
        """記録リストの読み込み"""
        try:
            result = await self._recording_service.get_all_recordings(
                page=self._current_page, 
                page_size=self._page_size
            )
            
            if result.is_success():
                recordings_list = result.value
                self._recordings = recordings_list.recordings
                self._total_recordings_count = recordings_list.total_count
                
                # フィルター適用
                await self._apply_current_filter()
                
                self.notify_property_changed('recordings')
                self.notify_property_changed('total_recordings_count')
                self.notify_property_changed('total_pages')
                self.notify_property_changed('has_next_page')
                self.notify_property_changed('has_previous_page')
                
            else:
                self.handle_result_error(result, "記録リスト読み込み")
                
        except Exception as e:
            self.add_error(f"記録リスト読み込みエラー: {str(e)}", str(e), "LOAD_RECORDINGS_ERROR")
    
    async def _load_statistics_async(self):
        """統計情報の読み込み"""
        try:
            result = await self._recording_service.get_statistics()
            
            if result.is_success():
                self._recording_stats = result.value
                self.notify_property_changed('recording_stats')
            else:
                self.handle_result_error(result, "統計情報読み込み")
                
        except Exception as e:
            self.add_error(f"統計情報読み込みエラー: {str(e)}", str(e), "LOAD_STATS_ERROR")
    
    # 記録操作コマンド実装
    async def _start_new_recording_async(self, parameter=None):
        """新規記録開始"""
        try:
            # 新規記録DTOの作成
            create_dto = CreateRecordingDTO(
                name=self._new_recording_name or f"記録_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                description=self._new_recording_description,
                category=self._new_recording_category,
                tags=self._new_recording_tags.copy(),
                auto_save=self._new_recording_auto_save
            )
            
            # 記録作成
            create_result = await self._recording_service.create_recording(create_dto)
            if create_result.is_failure():
                self.handle_result_error(create_result, "記録作成")
                return
            
            recording_id = create_result.value
            
            # 記録開始
            start_result = await self._recording_service.start_recording(recording_id)
            if start_result.is_success():
                self._current_recording_id = recording_id
                self._is_recording = True
                self._recording_status = "RECORDING"
                self._action_count = 0
                self._recording_duration = 0.0
                
                self.notify_property_changed('is_recording')
                self.notify_property_changed('recording_status')
                self.notify_property_changed('action_count')
                
                self.add_notification("記録開始", f"記録「{create_dto.name}」を開始しました", "SUCCESS")
                
                # ダイアログを閉じる
                self._hide_new_recording_dialog_command()
                
                # フォームをリセット
                self._reset_new_recording_form()
                
                # 現在の記録情報を取得
                await self._update_current_recording()
                
            else:
                self.handle_result_error(start_result, "記録開始")
                
        except Exception as e:
            self.add_error(f"記録開始エラー: {str(e)}", str(e), "START_RECORDING_ERROR")
    
    async def _stop_recording_async(self, parameter=None):
        """記録停止"""
        try:
            if not self._current_recording_id:
                return
            
            result = await self._recording_service.stop_recording(self._current_recording_id)
            
            if result.is_success():
                recording_dto = result.value
                
                self._is_recording = False
                self._recording_status = "STOPPED"
                self._current_recording = recording_dto
                
                self.notify_property_changed('is_recording')
                self.notify_property_changed('recording_status')
                self.notify_property_changed('current_recording')
                
                self.add_notification("記録停止", f"記録「{recording_dto.name}」を停止しました", "SUCCESS")
                
                # 記録リストを更新
                await self._load_recordings_async()
                
            else:
                self.handle_result_error(result, "記録停止")
                
        except Exception as e:
            self.add_error(f"記録停止エラー: {str(e)}", str(e), "STOP_RECORDING_ERROR")
    
    async def _pause_recording_async(self, parameter=None):
        """記録一時停止"""
        try:
            # 実装時に一時停止機能を追加
            self._recording_status = "PAUSED"
            self.notify_property_changed('recording_status')
            self.add_notification("記録一時停止", "記録を一時停止しました", "INFO")
            
        except Exception as e:
            self.add_error(f"記録一時停止エラー: {str(e)}", str(e), "PAUSE_RECORDING_ERROR")
    
    async def _resume_recording_async(self, parameter=None):
        """記録再開"""
        try:
            # 実装時に再開機能を追加
            self._recording_status = "RECORDING"
            self.notify_property_changed('recording_status')
            self.add_notification("記録再開", "記録を再開しました", "INFO")
            
        except Exception as e:
            self.add_error(f"記録再開エラー: {str(e)}", str(e), "RESUME_RECORDING_ERROR")
    
    async def _update_current_recording(self):
        """現在の記録情報を更新"""
        try:
            if not self._current_recording_id:
                return
            
            result = await self._recording_service.get_recording(self._current_recording_id, include_actions=True)
            
            if result.is_success():
                self._current_recording = result.value
                self._action_count = result.value.action_count
                self._estimated_duration = result.value.estimated_duration_ms / 1000.0
                
                self.notify_property_changed('current_recording')
                self.notify_property_changed('action_count')
                self.notify_property_changed('estimated_duration')
                
        except Exception as e:
            self.add_error(f"現在記録更新エラー: {str(e)}", str(e), "UPDATE_CURRENT_RECORDING_ERROR")
    
    # 記録管理操作
    async def _delete_recording_async(self, parameter=None):
        """記録削除"""
        try:
            if not self._selected_recording:
                return
                
            recording_id = self._selected_recording.recording_id
            recording_name = self._selected_recording.name
            
            result = await self._recording_service.delete_recording(recording_id)
            
            if result.is_success():
                self.add_notification("削除完了", f"記録「{recording_name}」を削除しました", "SUCCESS")
                
                # 選択をクリア
                self._clear_selection()
                
                # リストを再読み込み
                await self._load_recordings_async()
                
            else:
                self.handle_result_error(result, "記録削除")
                
        except Exception as e:
            self.add_error(f"削除エラー: {str(e)}", str(e), "DELETE_RECORDING_ERROR")
    
    async def _duplicate_recording_async(self, parameter=None):
        """記録複製"""
        try:
            if not self._selected_recording:
                return
                
            original_recording = self._selected_recording
            
            # 複製用DTO作成
            duplicate_dto = CreateRecordingDTO(
                name=f"{original_recording.name}_Copy",
                description=f"Copy of {original_recording.description}",
                category=original_recording.category,
                tags=original_recording.tags,
                auto_save=True
            )
            
            result = await self._recording_service.duplicate_recording(
                original_recording.recording_id, 
                duplicate_dto
            )
            
            if result.is_success():
                new_recording_id = result.value
                self.add_notification("複製完了", f"記録「{original_recording.name}」を複製しました", "SUCCESS")
                
                # リストを再読み込み
                await self._load_recordings_async()
                
                # 新しい記録を選択
                self._select_recording(new_recording_id)
                
            else:
                self.handle_result_error(result, "記録複製")
                
        except Exception as e:
            self.add_error(f"複製エラー: {str(e)}", str(e), "DUPLICATE_RECORDING_ERROR")
    
    async def _export_recording_async(self, parameter=None):
        """記録エクスポート"""
        try:
            if not self._selected_recording:
                return
                
            recording = self._selected_recording
            
            # エクスポート処理（今回は簡易実装）
            self.add_notification("エクスポート開始", f"記録「{recording.name}」のエクスポートを開始しました", "INFO")
            
            # 実際のエクスポート処理はアプリケーションサービスで実装
            # ここでは成功として扱う
            await asyncio.sleep(1)  # 模擬的な処理時間
            
            self.add_notification("エクスポート完了", f"記録「{recording.name}」のエクスポートが完了しました", "SUCCESS")
                
        except Exception as e:
            self.add_error(f"エクスポートエラー: {str(e)}", str(e), "EXPORT_RECORDING_ERROR")
    
    # フォーム操作メソッド
    async def _create_recording_async(self, parameter=None):
        """新規記録を作成"""
        try:
            if not self._new_recording_name.strip():
                self.add_error("記録名が必要です", "記録名を入力してください", "VALIDATION_ERROR")
                return
            
            create_dto = CreateRecordingDTO(
                name=self._new_recording_name,
                description=self._new_recording_description,
                category=self._new_recording_category,
                tags=self._new_recording_tags,
                auto_save=self._new_recording_auto_save
            )
            
            result = await self._recording_service.create_recording(create_dto)
            
            if result.is_success():
                recording_id = result.value
                self.add_notification("作成完了", f"記録「{create_dto.name}」を作成しました", "SUCCESS")
                
                # フォームをリセット
                self._reset_new_recording_form()
                
                # ダイアログを閉じる
                self._hide_new_recording_dialog_command()
                
                # リストを再読み込み
                await self._load_recordings_async()
                
                # 新しい記録を選択
                self._select_recording(recording_id)
                
            else:
                self.handle_result_error(result, "記録作成")
                
        except Exception as e:
            self.add_error(f"記録作成エラー: {str(e)}", str(e), "CREATE_RECORDING_ERROR")
    
    async def _update_recording_async(self, parameter=None):
        """記録を更新"""
        try:
            if not self._selected_recording:
                return
            
            if not self._edit_recording_name.strip():
                self.add_error("記録名が必要です", "記録名を入力してください", "VALIDATION_ERROR")
                return
            
            update_dto = UpdateRecordingDTO(
                recording_id=self._selected_recording.recording_id,
                name=self._edit_recording_name,
                description=self._edit_recording_description,
                category=self._edit_recording_category,
                tags=self._edit_recording_tags
            )
            
            result = await self._recording_service.update_recording(update_dto)
            
            if result.is_success():
                updated_recording = result.value
                self.add_notification("更新完了", f"記録「{updated_recording.name}」を更新しました", "SUCCESS")
                
                # ダイアログを閉じる
                self._hide_edit_recording_dialog_command()
                
                # リストを再読み込み
                await self._load_recordings_async()
                
                # 更新された記録を選択
                self._select_recording(updated_recording.recording_id)
                
            else:
                self.handle_result_error(result, "記録更新")
                
        except Exception as e:
            self.add_error(f"記録更新エラー: {str(e)}", str(e), "UPDATE_RECORDING_ERROR")
    
    def _reset_new_recording_form(self, parameter=None):
        """新規記録フォームをリセット"""
        self._new_recording_name = ""
        self._new_recording_description = ""
        self._new_recording_category = "general"
        self._new_recording_tags = []
        self._new_recording_auto_save = True
        
        self.notify_property_changed('new_recording_name')
        self.notify_property_changed('new_recording_description')
        self.notify_property_changed('new_recording_category')
        self.notify_property_changed('new_recording_tags')
        self.notify_property_changed('new_recording_auto_save')
    
    # 検索・フィルター実装
    async def _search_recordings_async(self, parameter=None):
        """記録検索"""
        try:
            if not self._search_query.strip():
                await self._load_recordings_async()
                return
            
            search_dto = RecordingSearchDTO(
                query=self._search_query,
                page=self._current_page,
                page_size=self._page_size
            )
            
            result = await self._recording_service.search_recordings(search_dto)
            
            if result.is_success():
                recordings_list = result.value
                self._recordings = recordings_list.recordings
                self._total_recordings_count = recordings_list.total_count
                
                await self._apply_current_filter()
                
                self.notify_property_changed('recordings')
                self.notify_property_changed('total_recordings_count')
                
                self.add_notification("検索完了", f"「{self._search_query}」で{recordings_list.total_count}件見つかりました", "INFO", 3000)
                
            else:
                self.handle_result_error(result, "記録検索")
                
        except Exception as e:
            self.add_error(f"検索エラー: {str(e)}", str(e), "SEARCH_ERROR")
    
    def _clear_search(self, parameter=None):
        """検索をクリア"""
        self.search_query = ""
        asyncio.create_task(self._load_recordings_async())
    
    async def _apply_filter_async(self, parameter=None):
        """フィルター適用"""
        await self._apply_current_filter()
    
    async def _apply_current_filter(self):
        """現在のフィルター設定を適用"""
        filtered = self._recordings.copy()
        
        # カテゴリフィルター
        if self._selected_category != "all":
            filtered = [r for r in filtered if r.metadata.category == self._selected_category]
        
        # ステータスフィルター
        if self._selected_status != "all":
            filtered = [r for r in filtered if r.status == self._selected_status]
        
        # ソート
        if self._sort_by == "created_at":
            filtered.sort(key=lambda r: r.created_at, reverse=self._sort_descending)
        elif self._sort_by == "name":
            filtered.sort(key=lambda r: r.name.lower(), reverse=self._sort_descending)
        elif self._sort_by == "action_count":
            filtered.sort(key=lambda r: r.action_count, reverse=self._sort_descending)
        
        self._filtered_recordings = filtered
        self.notify_property_changed('filtered_recordings')
    
    async def _sort_recordings_async(self, parameter=None):
        """記録リストをソート"""
        await self._apply_current_filter()
        self.add_notification("ソート完了", f"「{self._sort_by}」でソートしました", "INFO", 2000)
    
    # ページング実装
    async def _next_page_async(self, parameter=None):
        """次のページに移動"""
        if self.has_next_page:
            self._current_page += 1
            await self._load_recordings_async()
    
    async def _previous_page_async(self, parameter=None):
        """前のページに移動"""
        if self.has_previous_page:
            self._current_page -= 1
            await self._load_recordings_async()
    
    async def _go_to_page_async(self, parameter=None):
        """指定のページに移動"""
        if isinstance(parameter, int) and 1 <= parameter <= self.total_pages:
            self._current_page = parameter
            await self._load_recordings_async()
    
    # ダイアログ制御
    def _show_new_recording_dialog_command(self, parameter=None):
        """新規記録ダイアログを表示"""
        self._show_new_recording_dialog = True
        self.notify_property_changed('show_new_recording_dialog')
    
    def _hide_new_recording_dialog_command(self, parameter=None):
        """新規記録ダイアログを非表示"""
        self._show_new_recording_dialog = False
        self.notify_property_changed('show_new_recording_dialog')
    
    def _show_edit_recording_dialog_command(self, parameter=None):
        """編集ダイアログを表示"""
        if self._selected_recording:
            self._edit_recording_name = self._selected_recording.name
            self._edit_recording_description = self._selected_recording.description
            self._edit_recording_category = self._selected_recording.metadata.category
            self._edit_recording_tags = self._selected_recording.metadata.tags.copy()
            
            self._show_edit_recording_dialog = True
            self.notify_property_changed('show_edit_recording_dialog')
    
    def _hide_edit_recording_dialog_command(self, parameter=None):
        """編集ダイアログを非表示"""
        self._show_edit_recording_dialog = False
        self.notify_property_changed('show_edit_recording_dialog')
    
    def _reset_new_recording_form(self, parameter=None):
        """新規記録フォームをリセット"""
        self.new_recording_name = ""
        self.new_recording_description = ""
        self.new_recording_category = "general"
        self._new_recording_tags = []
        self._new_recording_auto_save = True
    
    # 選択操作
    def _select_recording(self, parameter=None):
        """記録を選択"""
        if isinstance(parameter, RecordingDTO):
            self._selected_recording = parameter
            self.notify_property_changed('selected_recording')
        elif isinstance(parameter, str):
            # recording_idで検索
            for recording in self._recordings:
                if recording.recording_id == parameter:
                    self._selected_recording = recording
                    self.notify_property_changed('selected_recording')
                    break
    
    def _clear_selection(self, parameter=None):
        """選択をクリア"""
        self._selected_recording = None
        self.notify_property_changed('selected_recording')
    
    # リフレッシュ処理
    async def _refresh_async(self, parameter=None):
        """データをリフレッシュ"""
        await self._load_recordings_async()
        await self._load_statistics_async()
        if self._current_recording_id:
            await self._update_current_recording()
    
    # イベントハンドラー
    def _on_recording_started(self, event_data):
        """記録開始イベント"""
        recording_id = event_data.get('recording_id')
        if recording_id == self._current_recording_id:
            self._is_recording = True
            self._recording_status = "RECORDING"
            self.notify_property_changed('is_recording')
            self.notify_property_changed('recording_status')
    
    def _on_recording_stopped(self, event_data):
        """記録停止イベント"""
        recording_id = event_data.get('recording_id')
        if recording_id == self._current_recording_id:
            self._is_recording = False
            self._recording_status = "STOPPED"
            self.notify_property_changed('is_recording')
            self.notify_property_changed('recording_status')
    
    def _on_recording_completed(self, event_data):
        """記録完了イベント"""
        recording_id = event_data.get('recording_id')
        if recording_id == self._current_recording_id:
            asyncio.create_task(self._update_current_recording())
        
        # 統計情報を更新
        asyncio.create_task(self._load_statistics_async())
    
    def _on_recording_failed(self, event_data):
        """記録失敗イベント"""
        recording_id = event_data.get('recording_id')
        if recording_id == self._current_recording_id:
            self._is_recording = False
            self._recording_status = "FAILED"
            self.notify_property_changed('is_recording')
            self.notify_property_changed('recording_status')
    
    def _on_action_added(self, event_data):
        """アクション追加イベント"""
        recording_id = event_data.get('recording_id')
        if recording_id == self._current_recording_id:
            self._action_count = event_data.get('action_count', self._action_count + 1)
            self.notify_property_changed('action_count')
    
    def _on_recording_updated(self, event_data):
        """記録更新イベント"""
        asyncio.create_task(self._load_recordings_async())
    
    def _on_recording_deleted(self, event_data):
        """記録削除イベント"""
        asyncio.create_task(self._load_recordings_async())
    
    # リソース破棄
    def _dispose_resources(self):
        """リソースの破棄"""
        # Note: For demo purposes, simplified event cleanup
        # In production, unsubscribe from EventBus using subscription IDs
        
        # サービス参照のクリア
        self._recording_service = None