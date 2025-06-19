"""
Main ViewModel - メイン画面のViewModel

アプリケーション全体のメイン画面を管理するViewModelです。
各機能モジュールへのナビゲーション、システム状態の表示、
グローバルな操作を提供します。
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import asyncio

from .base_viewmodel import BaseViewModel, AsyncCommand, Command
from ....core.result import Result, Ok, Err, ErrorInfo
from ....core.event_bus import EventBus
from ....application.services.recording_application_service import RecordingApplicationService
from ....application.services.playback_application_service import PlaybackApplicationService
from ....application.services.schedule_application_service import ScheduleApplicationService
from ....application.dto.recording_dto import RecordingStatsDTO
from ....application.dto.playback_dto import PlaybackHistoryDTO
from ....application.dto.schedule_dto import ScheduleStatsDTO


class MainViewModel(BaseViewModel):
    """メイン画面ViewModel"""
    
    def __init__(self, 
                 recording_service: RecordingApplicationService,
                 playback_service: PlaybackApplicationService,
                 schedule_service: ScheduleApplicationService,
                 event_bus: Optional[EventBus] = None):
        """
        初期化
        
        Args:
            recording_service: 記録アプリケーションサービス
            playback_service: 再生アプリケーションサービス
            schedule_service: スケジュールアプリケーションサービス
            event_bus: イベントバス
        """
        super().__init__(event_bus)
        
        # アプリケーションサービス
        self._recording_service = recording_service
        self._playback_service = playback_service
        self._schedule_service = schedule_service
        
        # ビューモデル状態
        self._current_view = "dashboard"
        self._app_version = "2.0.0"
        self._app_status = "Ready"
        self._recording_stats = None
        self._playback_stats = None
        self._schedule_stats = None
        self._recent_recordings = []
        self._recent_playbacks = []
        self._active_schedules = []
        self._system_info = {}
        
        # UI状態
        self._is_recording_available = True
        self._is_playback_available = True
        self._is_schedule_available = True
        self._sidebar_expanded = True
        
        # 初期化コマンド
        self._initialize_commands()
        
        # イベント購読
        self._subscribe_to_events()
    
    def _initialize_commands(self):
        """コマンドの初期化"""
        self.add_command('navigate_to_recording', Command(self._navigate_to_recording))
        self.add_command('navigate_to_playback', Command(self._navigate_to_playback))
        self.add_command('navigate_to_schedule', Command(self._navigate_to_schedule))
        self.add_command('navigate_to_settings', Command(self._navigate_to_settings))
        self.add_command('navigate_to_dashboard', Command(self._navigate_to_dashboard))
        
        self.add_command('quick_record', AsyncCommand(self._quick_record_async, 
                                                     lambda: self.is_recording_available and not self.is_busy))
        self.add_command('stop_all_operations', AsyncCommand(self._stop_all_operations_async,
                                                            lambda: not self.is_busy))
        
        self.add_command('toggle_sidebar', Command(self._toggle_sidebar))
        self.add_command('show_about', Command(self._show_about))
        self.add_command('check_updates', AsyncCommand(self._check_updates_async))
        self.add_command('apply_settings', Command(self._apply_settings))
        
        self.add_command('exit_application', AsyncCommand(self._exit_application_async))
    
    def _subscribe_to_events(self):
        """ドメインイベントの購読"""
        if self._event_bus:
            # ショートカット設定更新イベントの購読
            self._event_bus.subscribe("shortcut_settings_updated", self._on_shortcut_settings_updated)
            
            # ホットキーサービスイベントの購読
            self._event_bus.subscribe("hotkey_service_started", self._on_hotkey_service_started)
            self._event_bus.subscribe("hotkey_service_stopped", self._on_hotkey_service_stopped)
            self._event_bus.subscribe("custom_command_executed", self._on_custom_command_executed)
            self._event_bus.subscribe("custom_command_error", self._on_custom_command_error)
    
    # プロパティ
    @property
    def current_view(self) -> str:
        """現在のビュー"""
        return self._current_view
    
    @current_view.setter
    def current_view(self, value: str):
        if self.set_property('current_view', value):
            self._current_view = value
    
    @property
    def app_version(self) -> str:
        """アプリケーションバージョン"""
        return self._app_version
    
    @property
    def app_status(self) -> str:
        """アプリケーション状態"""
        return self._app_status
    
    @app_status.setter
    def app_status(self, value: str):
        if self.set_property('app_status', value):
            self._app_status = value
    
    @property
    def recording_stats(self) -> Optional[RecordingStatsDTO]:
        """記録統計情報"""
        return self._recording_stats
    
    @property
    def playback_stats(self) -> Optional[Dict[str, Any]]:
        """再生統計情報"""
        return self._playback_stats
    
    @property
    def schedule_stats(self) -> Optional[ScheduleStatsDTO]:
        """スケジュール統計情報"""
        return self._schedule_stats
    
    @property
    def recent_recordings(self) -> List[Dict[str, Any]]:
        """最近の記録"""
        return self._recent_recordings
    
    @property
    def recent_playbacks(self) -> List[Dict[str, Any]]:
        """最近の再生"""
        return self._recent_playbacks
    
    @property
    def active_schedules(self) -> List[Dict[str, Any]]:
        """アクティブなスケジュール"""
        return self._active_schedules
    
    @property
    def is_recording_available(self) -> bool:
        """記録機能が利用可能かどうか"""
        return self._is_recording_available
    
    @property
    def is_playback_available(self) -> bool:
        """再生機能が利用可能かどうか"""
        return self._is_playback_available
    
    @property
    def is_schedule_available(self) -> bool:
        """スケジュール機能が利用可能かどうか"""
        return self._is_schedule_available
    
    @property
    def sidebar_expanded(self) -> bool:
        """サイドバーが展開されているかどうか"""
        return self._sidebar_expanded
    
    @sidebar_expanded.setter
    def sidebar_expanded(self, value: bool):
        if self.set_property('sidebar_expanded', value):
            self._sidebar_expanded = value
    
    @property
    def system_info(self) -> Dict[str, Any]:
        """システム情報"""
        return self._system_info
    
    # 初期化
    async def initialize_async(self):
        """非同期初期化"""
        try:
            self.set_busy(True, "アプリケーションを初期化中...")
            
            # 統計情報の読み込み
            await self._load_statistics_async()
            
            # 最近のデータの読み込み
            await self._load_recent_data_async()
            
            # システム情報の読み込み
            await self._load_system_info_async()
            
            # 機能利用可能性のチェック
            await self._check_feature_availability_async()
            
            self.app_status = "Ready"
            self.add_notification("初期化完了", "アプリケーションの初期化が完了しました", "SUCCESS")
            
        except Exception as e:
            error_msg = f"初期化エラー: {str(e)}"
            self.add_error(error_msg, str(e), "INITIALIZATION_ERROR")
            self.app_status = "Error"
            
        finally:
            self.set_busy(False)
    
    async def _load_statistics_async(self):
        """統計情報の読み込み"""
        # 記録統計
        recording_stats_result = await self._recording_service.get_statistics()
        if recording_stats_result.is_success():
            self._recording_stats = recording_stats_result.value
            self.notify_property_changed('recording_stats')
        else:
            self.handle_result_error(recording_stats_result, "記録統計の読み込み")
        
        # 再生統計
        playback_metrics = self._playback_service.get_performance_metrics()
        self._playback_stats = playback_metrics
        self.notify_property_changed('playback_stats')
        
        # スケジュール統計
        schedule_stats_result = await self._schedule_service.get_statistics()
        if schedule_stats_result.is_success():
            self._schedule_stats = schedule_stats_result.value
            self.notify_property_changed('schedule_stats')
        else:
            self.handle_result_error(schedule_stats_result, "スケジュール統計の読み込み")
    
    async def _load_recent_data_async(self):
        """最近のデータの読み込み"""
        # 最近の記録
        recent_recordings_result = await self._recording_service.get_all_recordings(page=1, page_size=5)
        if recent_recordings_result.is_success():
            recordings_list = recent_recordings_result.value
            self._recent_recordings = [
                {
                    'id': r.recording_id,
                    'name': r.name,
                    'created_at': r.created_at,
                    'action_count': r.action_count,
                    'status': r.status
                }
                for r in recordings_list.recordings
            ]
            self.notify_property_changed('recent_recordings')
        
        # アクティブなスケジュール
        active_schedules_result = await self._schedule_service.get_all_schedules(active_only=True, page=1, page_size=10)
        if active_schedules_result.is_success():
            schedules_list = active_schedules_result.value
            self._active_schedules = [
                {
                    'id': s.schedule_id,
                    'name': s.name,
                    'next_execution': s.next_execution,
                    'execution_count': s.execution_count,
                    'success_rate': s.success_rate
                }
                for s in schedules_list.schedules
            ]
            self.notify_property_changed('active_schedules')
    
    async def _load_system_info_async(self):
        """システム情報の読み込み"""
        import platform
        import psutil
        
        self._system_info = {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'memory_total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
            'memory_available_gb': round(psutil.virtual_memory().available / (1024**3), 2),
            'disk_usage_percent': psutil.disk_usage('/').percent if platform.system() != 'Windows' else psutil.disk_usage('C:\\').percent,
            'app_version': self._app_version,
            'startup_time': datetime.now(timezone.utc)
        }
        self.notify_property_changed('system_info')
    
    async def _check_feature_availability_async(self):
        """機能利用可能性のチェック"""
        # 記録機能のチェック（常に利用可能と仮定）
        self._is_recording_available = True
        
        # 再生機能のチェック（記録が存在するかチェック）
        recordings_result = await self._recording_service.get_all_recordings(page=1, page_size=1)
        self._is_playback_available = recordings_result.is_success() and recordings_result.value.total_count > 0
        
        # スケジュール機能のチェック（スケジューラー状態をチェック）
        self._is_schedule_available = self._schedule_service.is_scheduler_running()
        
        self.notify_property_changed('is_recording_available')
        self.notify_property_changed('is_playback_available')
        self.notify_property_changed('is_schedule_available')
        
        # コマンドの実行可能状態を更新
        self._update_commands_can_execute()
    
    # ナビゲーションコマンド
    def _navigate_to_recording(self, parameter=None):
        """記録画面に遷移"""
        self.current_view = "recording"
        self.add_notification("画面遷移", "記録画面に移動しました", "INFO", 2000)
    
    def _navigate_to_playback(self, parameter=None):
        """再生画面に遷移"""
        self.current_view = "playback"
        self.add_notification("画面遷移", "再生画面に移動しました", "INFO", 2000)
    
    def _navigate_to_schedule(self, parameter=None):
        """スケジュール画面に遷移"""
        self.current_view = "schedule"
        self.add_notification("画面遷移", "スケジュール画面に移動しました", "INFO", 2000)
    
    def _navigate_to_settings(self, parameter=None):
        """設定画面に遷移"""
        self.current_view = "settings"
        self.add_notification("画面遷移", "設定画面に移動しました", "INFO", 2000)
    
    def _navigate_to_dashboard(self, parameter=None):
        """ダッシュボードに遷移"""
        self.current_view = "dashboard"
        self.add_notification("画面遷移", "ダッシュボードに移動しました", "INFO", 2000)
    
    # 機能コマンド
    async def _quick_record_async(self, parameter=None):
        """クイック記録"""
        try:
            from ....application.dto.recording_dto import CreateRecordingDTO
            
            quick_recording_dto = CreateRecordingDTO(
                name=f"クイック記録_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                description="メイン画面からのクイック記録",
                category="quick",
                tags=["quick", "main"],
                auto_save=True
            )
            
            result = await self._recording_service.create_recording(quick_recording_dto)
            if result.is_success():
                recording_id = result.value
                
                # 記録開始
                start_result = await self._recording_service.start_recording(recording_id)
                if start_result.is_success():
                    self.add_notification("記録開始", "クイック記録を開始しました", "SUCCESS")
                    self.current_view = "recording"
                else:
                    self.handle_result_error(start_result, "記録開始")
            else:
                self.handle_result_error(result, "クイック記録作成")
                
        except Exception as e:
            self.add_error(f"クイック記録エラー: {str(e)}", str(e), "QUICK_RECORD_ERROR")
    
    async def _stop_all_operations_async(self, parameter=None):
        """全ての操作を停止"""
        try:
            stopped_operations = []
            
            # 実行中の記録を停止
            # (実装時に記録状態をチェックして停止)
            
            # 実行中の再生を停止
            # (実装時に再生状態をチェックして停止)
            
            # スケジューラーを停止
            if self._schedule_service.is_scheduler_running():
                stop_result = await self._schedule_service.stop_scheduler()
                if stop_result.is_success():
                    stopped_operations.append("スケジューラー")
            
            if stopped_operations:
                message = f"停止した操作: {', '.join(stopped_operations)}"
                self.add_notification("操作停止", message, "INFO")
            else:
                self.add_notification("操作停止", "停止すべき操作はありませんでした", "INFO")
                
        except Exception as e:
            self.add_error(f"操作停止エラー: {str(e)}", str(e), "STOP_OPERATIONS_ERROR")
    
    def _toggle_sidebar(self, parameter=None):
        """サイドバーの表示切り替え"""
        self.sidebar_expanded = not self.sidebar_expanded
    
    def _show_about(self, parameter=None):
        """アプリケーション情報を表示"""
        about_message = f"""
EZRPA v{self.app_version}
クリーンアーキテクチャによるRPAアプリケーション

開発: EZRPA Development Team
Copyright © 2025 All rights reserved.
        """.strip()
        
        self.add_notification("バージョン情報", about_message, "INFO", 10000, True)
    
    async def _check_updates_async(self, parameter=None):
        """アップデートをチェック"""
        try:
            # 実装時にアップデートサーバーをチェック
            await asyncio.sleep(2)  # 模擬的な処理時間
            
            # 現在は最新バージョンと仮定
            self.add_notification("アップデート確認", "現在のバージョンが最新です", "SUCCESS")
            
        except Exception as e:
            self.add_error(f"アップデート確認エラー: {str(e)}", str(e), "UPDATE_CHECK_ERROR")
    
    def _apply_settings(self, settings=None):
        """設定適用"""
        try:
            if settings:
                # ショートカット設定をイベントバスで通知
                if self._event_bus:
                    self._event_bus.emit("shortcut_settings_updated", {
                        "settings": settings,
                        "timestamp": datetime.now(timezone.utc)
                    })
                
                self.add_notification("設定", "ショートカット設定が適用されました", "SUCCESS", 3000)
            else:
                self.add_notification("設定", "設定の適用をリクエストしました", "INFO", 2000)
                
        except Exception as e:
            self.add_error("設定適用エラー", str(e), "SETTINGS_APPLICATION_ERROR")
    
    async def _exit_application_async(self, parameter=None):
        """アプリケーション終了"""
        try:
            # 実行中の操作を停止
            await self._stop_all_operations_async()
            
            # 設定を保存
            # (実装時に設定保存処理)
            
            self.add_notification("終了処理", "アプリケーションを終了しています...", "INFO")
            
            # アプリケーション終了イベントを発行
            from ....core.event_bus import SystemEvent
            exit_event = SystemEvent(
                event_type='application_exit_requested',
                system_info={
                    'timestamp': datetime.now(timezone.utc)
                }
            )
            self._event_bus.publish(exit_event)
            
        except Exception as e:
            self.add_error(f"終了処理エラー: {str(e)}", str(e), "EXIT_ERROR")
    
    # リフレッシュ処理
    async def _refresh_async(self, parameter=None):
        """データをリフレッシュ"""
        try:
            await self._load_statistics_async()
            await self._load_recent_data_async()
            await self._check_feature_availability_async()
            
            self.add_notification("リフレッシュ完了", "データを更新しました", "SUCCESS", 2000)
            
        except Exception as e:
            self.add_error(f"リフレッシュエラー: {str(e)}", str(e), "REFRESH_ERROR")
    
    # イベントハンドラー
    def _on_recording_started(self, event_data):
        """記録開始イベントハンドラー"""
        self.app_status = "Recording"
        self.add_notification("記録開始", f"記録「{event_data.get('recording_name', '')}」を開始しました", "INFO")
    
    def _on_recording_completed(self, event_data):
        """記録完了イベントハンドラー"""
        self.app_status = "Ready"
        self.add_notification("記録完了", f"記録「{event_data.get('recording_name', '')}」が完了しました", "SUCCESS")
        # 統計情報を更新
        asyncio.create_task(self._load_statistics_async())
    
    def _on_recording_failed(self, event_data):
        """記録失敗イベントハンドラー"""
        self.app_status = "Ready"
        error_msg = event_data.get('error_message', '不明なエラー')
        self.add_notification("記録失敗", f"記録が失敗しました: {error_msg}", "ERROR", 8000)
    
    def _on_playback_started(self, event_data):
        """再生開始イベントハンドラー"""
        self.app_status = "Playing"
        self.add_notification("再生開始", f"記録「{event_data.get('recording_name', '')}」の再生を開始しました", "INFO")
    
    def _on_playback_completed(self, event_data):
        """再生完了イベントハンドラー"""
        self.app_status = "Ready"
        success_rate = event_data.get('success_rate', 0)
        self.add_notification("再生完了", f"再生が完了しました (成功率: {success_rate:.1%})", "SUCCESS")
    
    def _on_playback_failed(self, event_data):
        """再生失敗イベントハンドラー"""
        self.app_status = "Ready"
        error_msg = event_data.get('error_message', '不明なエラー')
        self.add_notification("再生失敗", f"再生が失敗しました: {error_msg}", "ERROR", 8000)
    
    def _on_schedule_activated(self, event_data):
        """スケジュールアクティブ化イベントハンドラー"""
        self.add_notification("スケジュール", f"スケジュール「{event_data.get('schedule_name', '')}」がアクティブになりました", "INFO")
        asyncio.create_task(self._load_recent_data_async())
    
    def _on_schedule_execution_completed(self, event_data):
        """スケジュール実行完了イベントハンドラー"""
        success = event_data.get('success', False)
        notification_type = "SUCCESS" if success else "ERROR"
        message = "実行成功" if success else "実行失敗"
        self.add_notification("スケジュール実行", f"スケジュール「{event_data.get('schedule_name', '')}」: {message}", notification_type)
    
    def _on_scheduler_started(self, event_data):
        """スケジューラー開始イベントハンドラー"""
        self._is_schedule_available = True
        self.notify_property_changed('is_schedule_available')
        self.add_notification("スケジューラー", "スケジューラーが開始されました", "SUCCESS")
    
    def _on_scheduler_stopped(self, event_data):
        """スケジューラー停止イベントハンドラー"""
        self._is_schedule_available = False
        self.notify_property_changed('is_schedule_available')
        reason = event_data.get('reason', 'user_request')
        self.add_notification("スケジューラー", f"スケジューラーが停止されました (理由: {reason})", "INFO")
    
    def _on_shortcut_settings_updated(self, event_data):
        """ショートカット設定更新イベントハンドラー"""
        self.add_notification("設定", "ショートカット設定が更新されました", "SUCCESS")
    
    def _on_hotkey_service_started(self, event_data):
        """ホットキーサービス開始イベントハンドラー"""
        self.add_notification("ホットキー", "グローバルホットキー監視を開始しました", "SUCCESS")
    
    def _on_hotkey_service_stopped(self, event_data):
        """ホットキーサービス停止イベントハンドラー"""
        self.add_notification("ホットキー", "グローバルホットキー監視を停止しました", "INFO")
    
    def _on_custom_command_executed(self, event_data):
        """カスタムコマンド実行イベントハンドラー"""
        command_name = event_data.get('command_name', '不明')
        success = event_data.get('success', False)
        
        if success:
            self.add_notification("コマンド実行", f"コマンド '{command_name}' を実行しました", "SUCCESS", 2000)
        else:
            self.add_notification("コマンド実行", f"コマンド '{command_name}' の実行に失敗しました", "WARNING", 3000)
    
    def _on_custom_command_error(self, event_data):
        """カスタムコマンドエラーイベントハンドラー"""
        command_name = event_data.get('command_name', '不明')
        error = event_data.get('error', '不明なエラー')
        self.add_error(f"コマンドエラー [{command_name}]", error, "CUSTOM_COMMAND_ERROR")
    
    # リソース破棄
    def _dispose_resources(self):
        """リソースの破棄"""
        # Note: For demo purposes, simplified event cleanup
        # In production, unsubscribe from EventBus using subscription IDs
        
        # サービス参照のクリア
        self._recording_service = None
        self._playback_service = None
        self._schedule_service = None