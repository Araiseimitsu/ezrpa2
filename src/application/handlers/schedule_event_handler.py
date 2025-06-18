"""
Schedule Event Handler - スケジュールイベントハンドラー

スケジュール関連のドメインイベントを処理するハンドラークラスです。
スケジュール実行の監視、ログ記録、統計情報の管理などを行います。
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import asyncio

from ...domain.repositories.settings_repository import ISettingsRepository
from ...infrastructure.services.file_service import FileService


class ScheduleEventHandler:
    """スケジュールイベントハンドラー"""
    
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
        self._execution_history = []  # 実行履歴の蓄積
        self._alert_conditions = []  # アラート条件
        
        # デフォルトハンドラーの登録
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """デフォルトハンドラーの登録"""
        self.subscribe("schedule_created", self._on_schedule_created)
        self.subscribe("schedule_updated", self._on_schedule_updated)
        self.subscribe("schedule_deleted", self._on_schedule_deleted)
        self.subscribe("schedule_activated", self._on_schedule_activated)
        self.subscribe("schedule_deactivated", self._on_schedule_deactivated)
        self.subscribe("schedule_execution_started", self._on_execution_started)
        self.subscribe("schedule_execution_completed", self._on_execution_completed)
        self.subscribe("schedule_execution_failed", self._on_execution_failed)
        self.subscribe("scheduler_started", self._on_scheduler_started)
        self.subscribe("scheduler_stopped", self._on_scheduler_stopped)
    
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
            print(f"スケジュールイベントハンドラーエラー: {handler.__name__}: {e}")
    
    async def _on_schedule_created(self, data: Dict[str, Any]):
        """スケジュール作成時の処理"""
        try:
            schedule_id = data.get('schedule_id')
            schedule_name = data.get('schedule_name', 'Unknown')
            trigger_type = data.get('trigger_type', 'unknown')
            
            print(f"スケジュール作成: {schedule_name} (ID: {schedule_id}, トリガー: {trigger_type})")
            
            # 作成ログの保存
            await self._save_schedule_log(
                schedule_id,
                "CREATED",
                f"スケジュール作成: {schedule_name} (トリガー: {trigger_type})"
            )
            
            # 統計情報の更新
            await self._update_schedule_statistics("created")
            
            # デフォルトアラート条件の設定
            await self._setup_default_alerts(schedule_id)
            
        except Exception as e:
            print(f"スケジュール作成イベント処理エラー: {e}")
    
    async def _on_schedule_updated(self, data: Dict[str, Any]):
        """スケジュール更新時の処理"""
        try:
            schedule_id = data.get('schedule_id')
            schedule_name = data.get('schedule_name', 'Unknown')
            changes = data.get('changes', {})
            
            # 重要な変更のみログ出力
            significant_changes = ['name', 'trigger_condition', 'repeat_condition', 'recording_id']
            if any(field in changes for field in significant_changes):
                await self._save_schedule_log(
                    schedule_id,
                    "UPDATED",
                    f"スケジュール更新: {schedule_name} (変更: {', '.join(changes.keys())})"
                )
            
        except Exception as e:
            print(f"スケジュール更新イベント処理エラー: {e}")
    
    async def _on_schedule_deleted(self, data: Dict[str, Any]):
        """スケジュール削除時の処理"""
        try:
            schedule_id = data.get('schedule_id')
            schedule_name = data.get('schedule_name', 'Unknown')
            
            print(f"スケジュール削除: {schedule_name}")
            
            # 削除ログの保存
            await self._save_schedule_log(
                schedule_id,
                "DELETED",
                f"スケジュール削除: {schedule_name}"
            )
            
            # 関連ファイルのクリーンアップ
            await self._cleanup_schedule_files(schedule_id)
            
            # 統計情報の更新
            await self._update_schedule_statistics("deleted")
            
        except Exception as e:
            print(f"スケジュール削除イベント処理エラー: {e}")
    
    async def _on_schedule_activated(self, data: Dict[str, Any]):
        """スケジュールアクティブ化時の処理"""
        try:
            schedule_id = data.get('schedule_id')
            schedule_name = data.get('schedule_name', 'Unknown')
            next_execution = data.get('next_execution_time')
            
            print(f"スケジュールアクティブ化: {schedule_name}")
            if next_execution:
                print(f"  次回実行予定: {next_execution}")
            
            # アクティブ化ログの保存
            message = f"スケジュールアクティブ化: {schedule_name}"
            if next_execution:
                message += f" (次回実行: {next_execution})"
            
            await self._save_schedule_log(schedule_id, "ACTIVATED", message)
            
            # アクティブ化通知
            await self._send_activation_notification(data)
            
        except Exception as e:
            print(f"スケジュールアクティブ化イベント処理エラー: {e}")
    
    async def _on_schedule_deactivated(self, data: Dict[str, Any]):
        """スケジュール非アクティブ化時の処理"""
        try:
            schedule_id = data.get('schedule_id')
            schedule_name = data.get('schedule_name', 'Unknown')
            reason = data.get('reason', 'user_request')
            
            print(f"スケジュール非アクティブ化: {schedule_name} (理由: {reason})")
            
            # 非アクティブ化ログの保存
            await self._save_schedule_log(
                schedule_id,
                "DEACTIVATED",
                f"スケジュール非アクティブ化: {schedule_name} (理由: {reason})"
            )
            
        except Exception as e:
            print(f"スケジュール非アクティブ化イベント処理エラー: {e}")
    
    async def _on_execution_started(self, data: Dict[str, Any]):
        """スケジュール実行開始時の処理"""
        try:
            execution_id = data.get('execution_id')
            schedule_id = data.get('schedule_id')
            schedule_name = data.get('schedule_name', 'Unknown')
            recording_name = data.get('recording_name', 'Unknown')
            
            print(f"スケジュール実行開始: {schedule_name} -> {recording_name}")
            
            # 実行開始ログの保存
            await self._save_schedule_log(
                schedule_id,
                "EXECUTION_STARTED",
                f"実行開始: {schedule_name} -> {recording_name} (実行ID: {execution_id})"
            )
            
            # 実行履歴への追加
            execution_record = {
                'execution_id': execution_id,
                'schedule_id': schedule_id,
                'schedule_name': schedule_name,
                'recording_name': recording_name,
                'start_time': datetime.now(timezone.utc),
                'status': 'running'
            }
            self._execution_history.append(execution_record)
            
            # 統計情報の更新
            await self._update_schedule_statistics("execution_started")
            
        except Exception as e:
            print(f"スケジュール実行開始イベント処理エラー: {e}")
    
    async def _on_execution_completed(self, data: Dict[str, Any]):
        """スケジュール実行完了時の処理"""
        try:
            execution_id = data.get('execution_id')
            schedule_id = data.get('schedule_id')
            schedule_name = data.get('schedule_name', 'Unknown')
            recording_name = data.get('recording_name', 'Unknown')
            duration_seconds = data.get('duration_seconds', 0)
            success = data.get('success', False)
            
            status_text = "成功" if success else "失敗"
            print(f"スケジュール実行完了: {schedule_name} -> {recording_name} ({status_text}, {duration_seconds:.1f}秒)")
            
            # 完了ログの保存
            await self._save_schedule_log(
                schedule_id,
                "EXECUTION_COMPLETED",
                f"実行完了: {schedule_name} -> {recording_name} ({status_text}, {duration_seconds:.1f}秒)"
            )
            
            # 実行履歴の更新
            execution_record = self._find_execution_record(execution_id)
            if execution_record:
                execution_record['end_time'] = datetime.now(timezone.utc)
                execution_record['duration_seconds'] = duration_seconds
                execution_record['success'] = success
                execution_record['status'] = 'completed'
            
            # 実行レポートの生成
            await self._generate_execution_report(execution_id, data)
            
            # 統計情報の更新
            if success:
                await self._update_schedule_statistics("execution_succeeded")
            else:
                await self._update_schedule_statistics("execution_failed")
            
            # アラート条件のチェック
            await self._check_alert_conditions(schedule_id, data)
            
            # 完了通知
            await self._send_execution_notification(data)
            
        except Exception as e:
            print(f"スケジュール実行完了イベント処理エラー: {e}")
    
    async def _on_execution_failed(self, data: Dict[str, Any]):
        """スケジュール実行失敗時の処理"""
        try:
            execution_id = data.get('execution_id')
            schedule_id = data.get('schedule_id')
            schedule_name = data.get('schedule_name', 'Unknown')
            recording_name = data.get('recording_name', 'Unknown')
            error_message = data.get('error_message', 'Unknown error')
            
            print(f"スケジュール実行失敗: {schedule_name} -> {recording_name} - {error_message}")
            
            # 失敗ログの保存
            await self._save_schedule_log(
                schedule_id,
                "EXECUTION_FAILED",
                f"実行失敗: {schedule_name} -> {recording_name} - {error_message}"
            )
            
            # 実行履歴の更新
            execution_record = self._find_execution_record(execution_id)
            if execution_record:
                execution_record['end_time'] = datetime.now(timezone.utc)
                execution_record['success'] = False
                execution_record['status'] = 'failed'
                execution_record['error_message'] = error_message
            
            # 失敗レポートの生成
            await self._generate_failure_report(execution_id, data)
            
            # 統計情報の更新
            await self._update_schedule_statistics("execution_failed")
            
            # 失敗アラートのチェック
            await self._check_failure_alerts(schedule_id, data)
            
            # エラー通知
            await self._send_error_notification(data)
            
        except Exception as e:
            print(f"スケジュール実行失敗イベント処理エラー: {e}")
    
    async def _on_scheduler_started(self, data: Dict[str, Any]):
        """スケジューラー開始時の処理"""
        try:
            print("スケジューラー開始")
            
            # スケジューラー開始ログの保存
            await self._save_system_log("SCHEDULER_STARTED", "スケジューラーを開始しました")
            
            # 開始通知
            await self._send_scheduler_notification("スケジューラーが開始されました")
            
        except Exception as e:
            print(f"スケジューラー開始イベント処理エラー: {e}")
    
    async def _on_scheduler_stopped(self, data: Dict[str, Any]):
        """スケジューラー停止時の処理"""
        try:
            reason = data.get('reason', 'user_request')
            print(f"スケジューラー停止 (理由: {reason})")
            
            # スケジューラー停止ログの保存
            await self._save_system_log("SCHEDULER_STOPPED", f"スケジューラーを停止しました (理由: {reason})")
            
            # 停止通知
            await self._send_scheduler_notification(f"スケジューラーが停止されました (理由: {reason})")
            
        except Exception as e:
            print(f"スケジューラー停止イベント処理エラー: {e}")
    
    async def _save_schedule_log(self, schedule_id: str, level: str, message: str):
        """スケジュールログの保存"""
        try:
            log_entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'schedule_id': schedule_id,
                'level': level,
                'message': message
            }
            
            # ログファイルに保存
            logs_dir = self._file_service.get_logs_dir()
            log_file = logs_dir / f"schedule_{schedule_id}.log"
            
            log_line = f"[{log_entry['timestamp']}] {level}: {message}\n"
            
            # ファイルに追記
            result = self._file_service.append_to_file(log_file, log_line)
            if result.is_failure():
                print(f"スケジュールログ保存エラー: {result.error}")
                
        except Exception as e:
            print(f"スケジュールログ保存エラー: {e}")
    
    async def _save_system_log(self, level: str, message: str):
        """システムログの保存"""
        try:
            log_entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'level': level,
                'message': message
            }
            
            # システムログファイルに保存
            logs_dir = self._file_service.get_logs_dir()
            log_file = logs_dir / "scheduler_system.log"
            
            log_line = f"[{log_entry['timestamp']}] {level}: {message}\n"
            
            # ファイルに追記
            result = self._file_service.append_to_file(log_file, log_line)
            if result.is_failure():
                print(f"システムログ保存エラー: {result.error}")
                
        except Exception as e:
            print(f"システムログ保存エラー: {e}")
    
    def _find_execution_record(self, execution_id: str) -> Dict[str, Any]:
        """実行記録の検索"""
        for record in self._execution_history:
            if record['execution_id'] == execution_id:
                return record
        return None
    
    async def _generate_execution_report(self, execution_id: str, data: Dict[str, Any]):
        """実行レポートの生成"""
        try:
            execution_record = self._find_execution_record(execution_id)
            if not execution_record:
                return
            
            report = {
                'execution_id': execution_id,
                'schedule_id': data.get('schedule_id'),
                'schedule_name': data.get('schedule_name'),
                'recording_name': data.get('recording_name'),
                'start_time': execution_record['start_time'].isoformat(),
                'end_time': execution_record.get('end_time', datetime.now(timezone.utc)).isoformat(),
                'duration_seconds': data.get('duration_seconds', 0),
                'success': data.get('success', False),
                'actions_executed': data.get('actions_executed', 0),
                'total_actions': data.get('total_actions', 0),
                'success_rate': data.get('success_rate', 0.0)
            }
            
            # レポートファイルの保存
            reports_dir = self._file_service.get_app_data_dir() / "reports"
            reports_dir.mkdir(exist_ok=True)
            
            report_file = reports_dir / f"schedule_execution_{execution_id}.json"
            
            result = self._file_service.write_json_file(report_file, report)
            if result.is_success():
                print(f"実行レポート保存: {report_file.name}")
                
        except Exception as e:
            print(f"実行レポート生成エラー: {e}")
    
    async def _generate_failure_report(self, execution_id: str, data: Dict[str, Any]):
        """失敗レポートの生成"""
        try:
            execution_record = self._find_execution_record(execution_id)
            if not execution_record:
                return
            
            report = {
                'execution_id': execution_id,
                'schedule_id': data.get('schedule_id'),
                'schedule_name': data.get('schedule_name'),
                'recording_name': data.get('recording_name'),
                'start_time': execution_record['start_time'].isoformat(),
                'failure_time': datetime.now(timezone.utc).isoformat(),
                'error_message': data.get('error_message'),
                'failed_action_index': data.get('failed_action_index', 0),
                'actions_executed': data.get('actions_executed', 0),
                'total_actions': data.get('total_actions', 0),
                'system_info': await self._collect_system_info()
            }
            
            # 失敗レポートファイルの保存
            reports_dir = self._file_service.get_app_data_dir() / "reports"
            reports_dir.mkdir(exist_ok=True)
            
            report_file = reports_dir / f"schedule_failure_{execution_id}.json"
            
            result = self._file_service.write_json_file(report_file, report)
            if result.is_success():
                print(f"失敗レポート保存: {report_file.name}")
                
        except Exception as e:
            print(f"失敗レポート生成エラー: {e}")
    
    async def _update_schedule_statistics(self, event_type: str):
        """スケジュール統計情報の更新"""
        try:
            stats_key = f"stats.schedule.{event_type}_count"
            
            current_result = await self._settings_repository.get(stats_key, 0)
            current_count = current_result.value if current_result.is_success() else 0
            
            new_count = current_count + 1
            await self._settings_repository.set(stats_key, new_count)
            
            await self._settings_repository.set(
                "stats.schedule.last_update",
                datetime.now(timezone.utc).isoformat()
            )
            
        except Exception as e:
            print(f"スケジュール統計情報更新エラー: {e}")
    
    async def _setup_default_alerts(self, schedule_id: str):
        """デフォルトアラート条件の設定"""
        try:
            # 連続失敗アラート
            alert_condition = {
                'schedule_id': schedule_id,
                'type': 'consecutive_failures',
                'threshold': 3,
                'enabled': True
            }
            self._alert_conditions.append(alert_condition)
            
        except Exception as e:
            print(f"デフォルトアラート設定エラー: {e}")
    
    async def _check_alert_conditions(self, schedule_id: str, data: Dict[str, Any]):
        """アラート条件のチェック"""
        try:
            for condition in self._alert_conditions:
                if condition['schedule_id'] == schedule_id and condition['enabled']:
                    if condition['type'] == 'consecutive_failures':
                        await self._check_consecutive_failures(schedule_id, condition)
                    # 他のアラート条件もここで追加可能
                        
        except Exception as e:
            print(f"アラート条件チェックエラー: {e}")
    
    async def _check_consecutive_failures(self, schedule_id: str, condition: Dict[str, Any]):
        """連続失敗アラートのチェック"""
        try:
            # 最近の実行履歴から連続失敗を確認
            recent_executions = [
                record for record in self._execution_history[-10:]  # 最新10件
                if record['schedule_id'] == schedule_id and record.get('end_time')
            ]
            
            if len(recent_executions) >= condition['threshold']:
                consecutive_failures = 0
                for record in reversed(recent_executions):
                    if not record.get('success', False):
                        consecutive_failures += 1
                    else:
                        break
                
                if consecutive_failures >= condition['threshold']:
                    await self._send_alert_notification(schedule_id, {
                        'type': 'consecutive_failures',
                        'count': consecutive_failures,
                        'threshold': condition['threshold']
                    })
            
        except Exception as e:
            print(f"連続失敗アラートチェックエラー: {e}")
    
    async def _check_failure_alerts(self, schedule_id: str, data: Dict[str, Any]):
        """失敗アラートのチェック"""
        try:
            # 即座に失敗通知を送信
            await self._send_alert_notification(schedule_id, {
                'type': 'execution_failure',
                'error_message': data.get('error_message', 'Unknown error')
            })
            
        except Exception as e:
            print(f"失敗アラートチェックエラー: {e}")
    
    async def _send_activation_notification(self, data: Dict[str, Any]):
        """アクティブ化通知の送信"""
        try:
            notifications_enabled_result = await self._settings_repository.get("notifications.enabled", False)
            if not (notifications_enabled_result.is_success() and notifications_enabled_result.value):
                return
            
            schedule_notifications_result = await self._settings_repository.get("notifications.schedule_activation", True)
            if not (schedule_notifications_result.is_success() and schedule_notifications_result.value):
                return
            
            schedule_name = data.get('schedule_name', 'Unknown')
            message = f"スケジュールアクティブ化: {schedule_name}"
            print(f"[通知] {message}")
            
        except Exception as e:
            print(f"アクティブ化通知送信エラー: {e}")
    
    async def _send_execution_notification(self, data: Dict[str, Any]):
        """実行通知の送信"""
        try:
            execution_notifications_result = await self._settings_repository.get("notifications.schedule_execution", False)
            if not (execution_notifications_result.is_success() and execution_notifications_result.value):
                return
            
            schedule_name = data.get('schedule_name', 'Unknown')
            success = data.get('success', False)
            duration = data.get('duration_seconds', 0)
            
            status_text = "成功" if success else "失敗"
            message = f"スケジュール実行{status_text}: {schedule_name} ({duration:.1f}秒)"
            print(f"[通知] {message}")
            
        except Exception as e:
            print(f"実行通知送信エラー: {e}")
    
    async def _send_error_notification(self, data: Dict[str, Any]):
        """エラー通知の送信"""
        try:
            error_notifications_result = await self._settings_repository.get("notifications.schedule_errors", True)
            if not (error_notifications_result.is_success() and error_notifications_result.value):
                return
            
            schedule_name = data.get('schedule_name', 'Unknown')
            error_message = data.get('error_message', 'Unknown error')
            
            message = f"スケジュール実行エラー: {schedule_name} - {error_message}"
            print(f"[エラー通知] {message}")
            
        except Exception as e:
            print(f"エラー通知送信エラー: {e}")
    
    async def _send_alert_notification(self, schedule_id: str, alert_data: Dict[str, Any]):
        """アラート通知の送信"""
        try:
            alert_notifications_result = await self._settings_repository.get("notifications.schedule_alerts", True)
            if not (alert_notifications_result.is_success() and alert_notifications_result.value):
                return
            
            alert_type = alert_data.get('type', 'unknown')
            
            if alert_type == 'consecutive_failures':
                count = alert_data.get('count', 0)
                threshold = alert_data.get('threshold', 0)
                message = f"スケジュールアラート: 連続{count}回失敗 (閾値: {threshold}回)"
            elif alert_type == 'execution_failure':
                error_message = alert_data.get('error_message', 'Unknown error')
                message = f"スケジュールアラート: 実行失敗 - {error_message}"
            else:
                message = f"スケジュールアラート: {alert_type}"
            
            print(f"[アラート] {message}")
            
        except Exception as e:
            print(f"アラート通知送信エラー: {e}")
    
    async def _send_scheduler_notification(self, message: str):
        """スケジューラー通知の送信"""
        try:
            scheduler_notifications_result = await self._settings_repository.get("notifications.scheduler_status", True)
            if not (scheduler_notifications_result.is_success() and scheduler_notifications_result.value):
                return
            
            print(f"[システム通知] {message}")
            
        except Exception as e:
            print(f"スケジューラー通知送信エラー: {e}")
    
    async def _cleanup_schedule_files(self, schedule_id: str):
        """スケジュール関連ファイルのクリーンアップ"""
        try:
            # ログファイルの削除
            logs_dir = self._file_service.get_logs_dir()
            log_file = logs_dir / f"schedule_{schedule_id}.log"
            
            if log_file.exists():
                result = self._file_service.delete_file(log_file)
                if result.is_success():
                    print(f"スケジュールログファイル削除: {log_file.name}")
            
            # レポートファイルの削除
            reports_dir = self._file_service.get_app_data_dir() / "reports"
            if reports_dir.exists():
                # schedule_id に関連するレポートファイルを削除
                # 実装時にglobパターンマッチングを使用
                pass
            
        except Exception as e:
            print(f"スケジュールファイルクリーンアップエラー: {e}")
    
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
                'disk_usage_percent': psutil.disk_usage('/').percent,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception:
            return {'error': 'システム情報収集に失敗しました'}
    
    def get_execution_history(self, schedule_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """実行履歴の取得"""
        history = self._execution_history
        
        if schedule_id:
            history = [record for record in history if record['schedule_id'] == schedule_id]
        
        return history[-limit:]
    
    def get_alert_conditions(self, schedule_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """アラート条件の取得"""
        conditions = self._alert_conditions
        
        if schedule_id:
            conditions = [condition for condition in conditions if condition['schedule_id'] == schedule_id]
        
        return conditions