"""
Playback Event Handler - 再生イベントハンドラー

再生関連のドメインイベントを処理するハンドラークラスです。
再生状況の監視、パフォーマンス計測、エラー処理などを行います。
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import asyncio

from ...domain.repositories.settings_repository import ISettingsRepository
from ...infrastructure.services.file_service import FileService


class PlaybackEventHandler:
    """再生イベントハンドラー"""
    
    def __init__(self, 
                 settings_repository: ISettingsRepository,
                 file_service: FileService):
        """
        初期化
        
        Args:
            settings_repository: 設定リポジトリ
            file_service: ファイルサービス
        """
        self._settings_repository = settings_repository
        self._file_service = file_service
        self._event_listeners = {}
        self._performance_data = []  # パフォーマンスデータの蓄積
        
        # デフォルトハンドラーの登録
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """デフォルトハンドラーの登録"""
        self.subscribe("playback_started", self._on_playback_started)
        self.subscribe("playback_paused", self._on_playback_paused)
        self.subscribe("playback_resumed", self._on_playback_resumed)
        self.subscribe("playback_stopped", self._on_playback_stopped)
        self.subscribe("playback_completed", self._on_playback_completed)
        self.subscribe("playback_failed", self._on_playback_failed)
        self.subscribe("action_executed", self._on_action_executed)
        self.subscribe("action_failed", self._on_action_failed)
    
    def subscribe(self, event_type: str, handler):
        """イベントハンドラーを登録"""
        if event_type not in self._event_listeners:
            self._event_listeners[event_type] = []
        self._event_listeners[event_type].append(handler)
    
    def unsubscribe(self, event_type: str, handler):
        """イベントハンドラーを登録解除"""
        if event_type in self._event_listeners:
            try:
                self._event_listeners[event_type].remove(handler)
            except ValueError:
                pass
    
    async def publish(self, event_type: str, data: Dict[str, Any]):
        """イベントを発行"""
        if event_type in self._event_listeners:
            tasks = []
            for handler in self._event_listeners[event_type]:
                task = asyncio.create_task(self._safe_execute_handler(handler, data))
                tasks.append(task)
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _safe_execute_handler(self, handler, data: Dict[str, Any]):
        """ハンドラーの安全な実行"""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(data)
            else:
                handler(data)
        except Exception as e:
            print(f"再生イベントハンドラーエラー: {handler.__name__}: {e}")
    
    async def _on_playback_started(self, data: Dict[str, Any]):
        """再生開始時の処理"""
        try:
            session_id = data.get('session_id')
            recording_id = data.get('recording_id')
            recording_name = data.get('recording_name', 'Unknown')
            config = data.get('config', {})
            
            print(f"再生開始: {recording_name} (セッション: {session_id})")
            
            # 再生ログの保存
            await self._save_playback_log(
                session_id,
                "STARTED",
                f"再生開始: {recording_name} (記録ID: {recording_id})"
            )
            
            # パフォーマンス測定開始
            await self._start_performance_monitoring(session_id, data)
            
            # 統計情報の更新
            await self._update_playback_statistics("started")
            
            # スクリーンショット設定のチェック
            if config.get('take_screenshots', False):
                await self._prepare_screenshot_directory(session_id)
            
        except Exception as e:
            print(f"再生開始イベント処理エラー: {e}")
    
    async def _on_playback_paused(self, data: Dict[str, Any]):
        """再生一時停止時の処理"""
        try:
            session_id = data.get('session_id')
            recording_name = data.get('recording_name', 'Unknown')
            current_action = data.get('current_action_index', 0)
            
            print(f"再生一時停止: {recording_name} (アクション #{current_action})")
            
            # 一時停止ログの保存
            await self._save_playback_log(
                session_id,
                "PAUSED",
                f"再生一時停止: {recording_name} (アクション #{current_action})"
            )
            
            # パフォーマンス測定の一時停止
            await self._pause_performance_monitoring(session_id)
            
        except Exception as e:
            print(f"再生一時停止イベント処理エラー: {e}")
    
    async def _on_playback_resumed(self, data: Dict[str, Any]):
        """再生再開時の処理"""
        try:
            session_id = data.get('session_id')
            recording_name = data.get('recording_name', 'Unknown')
            current_action = data.get('current_action_index', 0)
            
            print(f"再生再開: {recording_name} (アクション #{current_action})")
            
            # 再開ログの保存
            await self._save_playback_log(
                session_id,
                "RESUMED",
                f"再生再開: {recording_name} (アクション #{current_action})"
            )
            
            # パフォーマンス測定の再開
            await self._resume_performance_monitoring(session_id)
            
        except Exception as e:
            print(f"再生再開イベント処理エラー: {e}")
    
    async def _on_playback_stopped(self, data: Dict[str, Any]):
        """再生停止時の処理"""
        try:
            session_id = data.get('session_id')
            recording_name = data.get('recording_name', 'Unknown')
            reason = data.get('reason', 'user_request')
            actions_executed = data.get('actions_executed', 0)
            total_actions = data.get('total_actions', 0)
            
            print(f"再生停止: {recording_name} ({actions_executed}/{total_actions}アクション実行)")
            
            # 停止ログの保存
            await self._save_playback_log(
                session_id,
                "STOPPED",
                f"再生停止: {recording_name} (理由: {reason}, {actions_executed}/{total_actions}アクション実行)"
            )
            
            # パフォーマンス測定終了
            await self._end_performance_monitoring(session_id, data)
            
            # 統計情報の更新
            await self._update_playback_statistics("stopped")
            
        except Exception as e:
            print(f"再生停止イベント処理エラー: {e}")
    
    async def _on_playback_completed(self, data: Dict[str, Any]):
        """再生完了時の処理"""
        try:
            session_id = data.get('session_id')
            recording_name = data.get('recording_name', 'Unknown')
            duration_seconds = data.get('duration_seconds', 0)
            actions_executed = data.get('actions_executed', 0)
            success_rate = data.get('success_rate', 0.0)
            
            print(f"再生完了: {recording_name} ({duration_seconds:.1f}秒, 成功率: {success_rate:.1%})")
            
            # 完了ログの保存
            await self._save_playback_log(
                session_id,
                "COMPLETED",
                f"再生完了: {recording_name} ({duration_seconds:.1f}秒, {actions_executed}アクション, 成功率: {success_rate:.1%})"
            )
            
            # 完了レポートの生成
            await self._generate_completion_report(session_id, data)
            
            # パフォーマンス測定終了
            await self._end_performance_monitoring(session_id, data)
            
            # 統計情報の更新
            await self._update_playback_statistics("completed")
            
            # 完了通知
            await self._send_completion_notification(data)
            
        except Exception as e:
            print(f"再生完了イベント処理エラー: {e}")
    
    async def _on_playback_failed(self, data: Dict[str, Any]):
        """再生失敗時の処理"""
        try:
            session_id = data.get('session_id')
            recording_name = data.get('recording_name', 'Unknown')
            error_message = data.get('error_message', 'Unknown error')
            failed_action = data.get('failed_action_index', 0)
            
            print(f"再生失敗: {recording_name} - {error_message} (アクション #{failed_action})")
            
            # 失敗ログの保存
            await self._save_playback_log(
                session_id,
                "FAILED",
                f"再生失敗: {recording_name} - {error_message} (アクション #{failed_action})"
            )
            
            # エラーレポートの生成
            await self._generate_error_report(session_id, data)
            
            # パフォーマンス測定終了
            await self._end_performance_monitoring(session_id, data)
            
            # 統計情報の更新
            await self._update_playback_statistics("failed")
            
            # エラー通知
            await self._send_error_notification(data)
            
        except Exception as e:
            print(f"再生失敗イベント処理エラー: {e}")
    
    async def _on_action_executed(self, data: Dict[str, Any]):
        """アクション実行時の処理"""
        try:
            session_id = data.get('session_id')
            action_id = data.get('action_id')
            action_type = data.get('action_type')
            sequence_number = data.get('sequence_number', 0)
            execution_time_ms = data.get('execution_time_ms', 0)
            
            # 詳細ログの設定確認
            verbose_logging_result = await self._settings_repository.get("debug.verbose_logging", False)
            if verbose_logging_result.is_success() and verbose_logging_result.value:
                await self._save_playback_log(
                    session_id,
                    "ACTION_EXECUTED",
                    f"アクション実行: {action_type} (#{sequence_number}, {execution_time_ms}ms)"
                )
            
            # パフォーマンスデータの記録
            await self._record_action_performance(session_id, data)
            
        except Exception as e:
            print(f"アクション実行イベント処理エラー: {e}")
    
    async def _on_action_failed(self, data: Dict[str, Any]):
        """アクション失敗時の処理"""
        try:
            session_id = data.get('session_id')
            action_id = data.get('action_id')
            action_type = data.get('action_type')
            sequence_number = data.get('sequence_number', 0)
            error_message = data.get('error_message', 'Unknown error')
            
            print(f"アクション失敗: {action_type} (#{sequence_number}) - {error_message}")
            
            # 失敗ログの保存
            await self._save_playback_log(
                session_id,
                "ACTION_FAILED",
                f"アクション失敗: {action_type} (#{sequence_number}) - {error_message}"
            )
            
            # アクション失敗の詳細記録
            await self._record_action_failure(session_id, data)
            
        except Exception as e:
            print(f"アクション失敗イベント処理エラー: {e}")
    
    async def _save_playback_log(self, session_id: str, level: str, message: str):
        """再生ログの保存"""
        try:
            log_entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'session_id': session_id,
                'level': level,
                'message': message
            }
            
            # ログファイルに保存
            logs_dir = self._file_service.get_logs_dir()
            log_file = logs_dir / f"playback_{session_id}.log"
            
            log_line = f"[{log_entry['timestamp']}] {level}: {message}\n"
            
            # ファイルに追記
            result = self._file_service.append_to_file(log_file, log_line)
            if result.is_failure():
                print(f"再生ログ保存エラー: {result.error}")
                
        except Exception as e:
            print(f"再生ログ保存エラー: {e}")
    
    async def _start_performance_monitoring(self, session_id: str, data: Dict[str, Any]):
        """パフォーマンス測定開始"""
        try:
            perf_data = {
                'session_id': session_id,
                'start_time': datetime.now(timezone.utc),
                'recording_id': data.get('recording_id'),
                'recording_name': data.get('recording_name'),
                'actions': [],
                'total_actions': data.get('total_actions', 0),
                'config': data.get('config', {})
            }
            
            self._performance_data.append(perf_data)
            
        except Exception as e:
            print(f"パフォーマンス測定開始エラー: {e}")
    
    async def _pause_performance_monitoring(self, session_id: str):
        """パフォーマンス測定の一時停止"""
        try:
            perf_data = self._find_performance_data(session_id)
            if perf_data:
                perf_data['pause_time'] = datetime.now(timezone.utc)
                
        except Exception as e:
            print(f"パフォーマンス測定一時停止エラー: {e}")
    
    async def _resume_performance_monitoring(self, session_id: str):
        """パフォーマンス測定の再開"""
        try:
            perf_data = self._find_performance_data(session_id)
            if perf_data and 'pause_time' in perf_data:
                # 一時停止時間を累積
                pause_duration = datetime.now(timezone.utc) - perf_data['pause_time']
                if 'total_pause_duration' not in perf_data:
                    perf_data['total_pause_duration'] = pause_duration
                else:
                    perf_data['total_pause_duration'] += pause_duration
                
                del perf_data['pause_time']
                
        except Exception as e:
            print(f"パフォーマンス測定再開エラー: {e}")
    
    async def _end_performance_monitoring(self, session_id: str, data: Dict[str, Any]):
        """パフォーマンス測定終了"""
        try:
            perf_data = self._find_performance_data(session_id)
            if perf_data:
                perf_data['end_time'] = datetime.now(timezone.utc)
                perf_data['duration_seconds'] = data.get('duration_seconds', 0)
                perf_data['success_rate'] = data.get('success_rate', 0.0)
                perf_data['actions_executed'] = data.get('actions_executed', 0)
                
                # パフォーマンスレポートの保存
                await self._save_performance_report(perf_data)
                
        except Exception as e:
            print(f"パフォーマンス測定終了エラー: {e}")
    
    async def _record_action_performance(self, session_id: str, data: Dict[str, Any]):
        """アクションパフォーマンスの記録"""
        try:
            perf_data = self._find_performance_data(session_id)
            if perf_data:
                action_perf = {
                    'sequence_number': data.get('sequence_number', 0),
                    'action_type': data.get('action_type'),
                    'execution_time_ms': data.get('execution_time_ms', 0),
                    'timestamp': datetime.now(timezone.utc),
                    'success': True
                }
                perf_data['actions'].append(action_perf)
                
        except Exception as e:
            print(f"アクションパフォーマンス記録エラー: {e}")
    
    async def _record_action_failure(self, session_id: str, data: Dict[str, Any]):
        """アクション失敗の記録"""
        try:
            perf_data = self._find_performance_data(session_id)
            if perf_data:
                action_failure = {
                    'sequence_number': data.get('sequence_number', 0),
                    'action_type': data.get('action_type'),
                    'error_message': data.get('error_message'),
                    'timestamp': datetime.now(timezone.utc),
                    'success': False
                }
                perf_data['actions'].append(action_failure)
                
        except Exception as e:
            print(f"アクション失敗記録エラー: {e}")
    
    def _find_performance_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """パフォーマンスデータの検索"""
        for perf_data in self._performance_data:
            if perf_data['session_id'] == session_id:
                return perf_data
        return None
    
    async def _generate_completion_report(self, session_id: str, data: Dict[str, Any]):
        """完了レポートの生成"""
        try:
            report = {
                'session_id': session_id,
                'recording_name': data.get('recording_name'),
                'completion_time': datetime.now(timezone.utc).isoformat(),
                'duration_seconds': data.get('duration_seconds', 0),
                'actions_executed': data.get('actions_executed', 0),
                'total_actions': data.get('total_actions', 0),
                'success_rate': data.get('success_rate', 0.0),
                'average_action_time': data.get('average_action_time_ms', 0)
            }
            
            # レポートファイルの保存
            reports_dir = self._file_service.get_app_data_dir() / "reports"
            reports_dir.mkdir(exist_ok=True)
            
            report_file = reports_dir / f"playback_completion_{session_id}.json"
            
            result = self._file_service.write_json_file(report_file, report)
            if result.is_success():
                print(f"完了レポート保存: {report_file.name}")
                
        except Exception as e:
            print(f"完了レポート生成エラー: {e}")
    
    async def _generate_error_report(self, session_id: str, data: Dict[str, Any]):
        """エラーレポートの生成"""
        try:
            report = {
                'session_id': session_id,
                'recording_name': data.get('recording_name'),
                'error_time': datetime.now(timezone.utc).isoformat(),
                'error_message': data.get('error_message'),
                'failed_action_index': data.get('failed_action_index', 0),
                'actions_executed': data.get('actions_executed', 0),
                'total_actions': data.get('total_actions', 0),
                'system_info': await self._collect_system_info()
            }
            
            # エラーレポートファイルの保存
            reports_dir = self._file_service.get_app_data_dir() / "reports"
            reports_dir.mkdir(exist_ok=True)
            
            report_file = reports_dir / f"playback_error_{session_id}.json"
            
            result = self._file_service.write_json_file(report_file, report)
            if result.is_success():
                print(f"エラーレポート保存: {report_file.name}")
                
        except Exception as e:
            print(f"エラーレポート生成エラー: {e}")
    
    async def _save_performance_report(self, perf_data: Dict[str, Any]):
        """パフォーマンスレポートの保存"""
        try:
            # パフォーマンス統計の計算
            actions = perf_data.get('actions', [])
            successful_actions = [a for a in actions if a.get('success', True)]
            failed_actions = [a for a in actions if not a.get('success', True)]
            
            if successful_actions:
                avg_execution_time = sum(a.get('execution_time_ms', 0) for a in successful_actions) / len(successful_actions)
            else:
                avg_execution_time = 0
            
            report = {
                'session_id': perf_data['session_id'],
                'recording_name': perf_data.get('recording_name'),
                'start_time': perf_data['start_time'].isoformat(),
                'end_time': perf_data.get('end_time', datetime.now(timezone.utc)).isoformat(),
                'total_duration_seconds': perf_data.get('duration_seconds', 0),
                'actions_executed': len(actions),
                'successful_actions': len(successful_actions),
                'failed_actions': len(failed_actions),
                'success_rate': len(successful_actions) / max(len(actions), 1),
                'average_execution_time_ms': avg_execution_time,
                'actions_detail': actions
            }
            
            # パフォーマンスレポートファイルの保存
            reports_dir = self._file_service.get_app_data_dir() / "reports"
            reports_dir.mkdir(exist_ok=True)
            
            report_file = reports_dir / f"performance_{perf_data['session_id']}.json"
            
            result = self._file_service.write_json_file(report_file, report)
            if result.is_success():
                print(f"パフォーマンスレポート保存: {report_file.name}")
                
        except Exception as e:
            print(f"パフォーマンスレポート保存エラー: {e}")
    
    async def _update_playback_statistics(self, event_type: str):
        """再生統計情報の更新"""
        try:
            stats_key = f"stats.playback.{event_type}_count"
            
            current_result = await self._settings_repository.get(stats_key, 0)
            current_count = current_result.value if current_result.is_success() else 0
            
            new_count = current_count + 1
            await self._settings_repository.set(stats_key, new_count)
            
            await self._settings_repository.set(
                "stats.playback.last_update",
                datetime.now(timezone.utc).isoformat()
            )
            
        except Exception as e:
            print(f"再生統計情報更新エラー: {e}")
    
    async def _send_completion_notification(self, data: Dict[str, Any]):
        """完了通知の送信"""
        try:
            notifications_enabled_result = await self._settings_repository.get("notifications.enabled", False)
            if not (notifications_enabled_result.is_success() and notifications_enabled_result.value):
                return
            
            completion_notifications_result = await self._settings_repository.get("notifications.playback_completion", True)
            if not (completion_notifications_result.is_success() and completion_notifications_result.value):
                return
            
            recording_name = data.get('recording_name', 'Unknown')
            duration = data.get('duration_seconds', 0)
            success_rate = data.get('success_rate', 0.0)
            
            message = f"再生完了: {recording_name} ({duration:.1f}秒, 成功率: {success_rate:.1%})"
            print(f"[通知] {message}")
            
        except Exception as e:
            print(f"完了通知送信エラー: {e}")
    
    async def _send_error_notification(self, data: Dict[str, Any]):
        """エラー通知の送信"""
        try:
            error_notifications_result = await self._settings_repository.get("notifications.playback_errors", True)
            if not (error_notifications_result.is_success() and error_notifications_result.value):
                return
            
            recording_name = data.get('recording_name', 'Unknown')
            error_message = data.get('error_message', 'Unknown error')
            
            message = f"再生エラー: {recording_name} - {error_message}"
            print(f"[エラー通知] {message}")
            
        except Exception as e:
            print(f"エラー通知送信エラー: {e}")
    
    async def _prepare_screenshot_directory(self, session_id: str):
        """スクリーンショットディレクトリの準備"""
        try:
            screenshots_dir = self._file_service.get_app_data_dir() / "screenshots" / session_id
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            print(f"スクリーンショットディレクトリ作成: {screenshots_dir}")
            
        except Exception as e:
            print(f"スクリーンショットディレクトリ準備エラー: {e}")
    
    async def _collect_system_info(self) -> Dict[str, Any]:
        """システム情報の収集"""
        try:
            import platform
            import psutil
            
            return {
                'platform': platform.platform(),
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': psutil.virtual_memory().total / (1024**3),
                'memory_available_gb': psutil.virtual_memory().available / (1024**3),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception:
            return {'error': 'システム情報収集に失敗しました'}