"""
Recording Event Handler - 記録イベントハンドラー

記録関連のドメインイベントを処理するハンドラークラスです。
イベントドリブンアーキテクチャによる疎結合な連携を実現します。
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
import asyncio

from ...core.result import Result, Ok, Err, ErrorInfo
from ...domain import Recording
from ...domain.repositories.settings_repository import ISettingsRepository
from ...infrastructure.services.file_service import FileService


class RecordingEventHandler:
    """記録イベントハンドラー"""
    
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
        self._event_listeners = {}  # イベント種別 -> ハンドラーリスト
        
        # デフォルトハンドラーの登録
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """デフォルトハンドラーの登録"""
        self.subscribe("recording_started", self._on_recording_started)
        self.subscribe("recording_stopped", self._on_recording_stopped)
        self.subscribe("recording_completed", self._on_recording_completed)
        self.subscribe("recording_failed", self._on_recording_failed)
        self.subscribe("action_added", self._on_action_added)
        self.subscribe("recording_deleted", self._on_recording_deleted)
        self.subscribe("recording_updated", self._on_recording_updated)
    
    def subscribe(self, event_type: str, handler):
        """
        イベントハンドラーを登録
        
        Args:
            event_type: イベント種別
            handler: ハンドラー関数
        """
        if event_type not in self._event_listeners:
            self._event_listeners[event_type] = []
        self._event_listeners[event_type].append(handler)
    
    def unsubscribe(self, event_type: str, handler):
        """
        イベントハンドラーを登録解除
        
        Args:
            event_type: イベント種別
            handler: ハンドラー関数
        """
        if event_type in self._event_listeners:
            try:
                self._event_listeners[event_type].remove(handler)
            except ValueError:
                pass
    
    async def publish(self, event_type: str, data: Dict[str, Any]):
        """
        イベントを発行
        
        Args:
            event_type: イベント種別
            data: イベントデータ
        """
        if event_type in self._event_listeners:
            # 並列実行でパフォーマンス向上
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
            # ログ出力（実装時に適切なロガーを使用）
            print(f"イベントハンドラーエラー: {handler.__name__}: {e}")
    
    async def _on_recording_started(self, data: Dict[str, Any]):
        """記録開始時の処理"""
        try:
            recording_id = data.get('recording_id')
            recording_name = data.get('recording_name', 'Unknown')
            
            # 自動保存設定のチェック
            auto_save_result = await self._settings_repository.get("recording.auto_save", True)
            if auto_save_result.is_success() and auto_save_result.value:
                # 自動保存が有効な場合の処理
                print(f"記録開始: {recording_name} (ID: {recording_id}) - 自動保存有効")
            
            # 記録開始ログの保存
            await self._save_recording_log(recording_id, "STARTED", f"記録を開始しました: {recording_name}")
            
            # 統計情報の更新
            await self._update_recording_statistics("started")
            
        except Exception as e:
            print(f"記録開始イベント処理エラー: {e}")
    
    async def _on_recording_stopped(self, data: Dict[str, Any]):
        """記録停止時の処理"""
        try:
            recording_id = data.get('recording_id')
            recording_name = data.get('recording_name', 'Unknown')
            action_count = data.get('action_count', 0)
            
            print(f"記録停止: {recording_name} (アクション数: {action_count})")
            
            # 記録停止ログの保存
            await self._save_recording_log(
                recording_id, 
                "STOPPED", 
                f"記録を停止しました: {recording_name} ({action_count}アクション)"
            )
            
            # 統計情報の更新
            await self._update_recording_statistics("stopped")
            
        except Exception as e:
            print(f"記録停止イベント処理エラー: {e}")
    
    async def _on_recording_completed(self, data: Dict[str, Any]):
        """記録完了時の処理"""
        try:
            recording = data.get('recording')
            if not recording:
                return
            
            recording_id = recording.recording_id
            recording_name = recording.name
            action_count = recording.action_count
            duration = recording.get_estimated_duration()
            
            print(f"記録完了: {recording_name} ({action_count}アクション, {duration.seconds}秒)")
            
            # 自動バックアップの実行
            auto_backup_result = await self._settings_repository.get("recording.auto_backup", True)
            if auto_backup_result.is_success() and auto_backup_result.value:
                await self._create_recording_backup(recording)
            
            # 記録完了ログの保存
            await self._save_recording_log(
                recording_id, 
                "COMPLETED", 
                f"記録を完了しました: {recording_name} ({action_count}アクション, {duration.seconds}秒)"
            )
            
            # 統計情報の更新
            await self._update_recording_statistics("completed")
            
            # 完了通知（設定で有効な場合）
            await self._send_completion_notification(recording)
            
        except Exception as e:
            print(f"記録完了イベント処理エラー: {e}")
    
    async def _on_recording_failed(self, data: Dict[str, Any]):
        """記録失敗時の処理"""
        try:
            recording_id = data.get('recording_id')
            recording_name = data.get('recording_name', 'Unknown')
            error_message = data.get('error_message', 'Unknown error')
            
            print(f"記録失敗: {recording_name} - {error_message}")
            
            # 失敗ログの保存
            await self._save_recording_log(
                recording_id, 
                "FAILED", 
                f"記録が失敗しました: {recording_name} - {error_message}"
            )
            
            # 統計情報の更新
            await self._update_recording_statistics("failed")
            
            # エラー通知
            await self._send_error_notification(recording_name, error_message)
            
        except Exception as e:
            print(f"記録失敗イベント処理エラー: {e}")
    
    async def _on_action_added(self, data: Dict[str, Any]):
        """アクション追加時の処理"""
        try:
            recording_id = data.get('recording_id')
            action = data.get('action')
            action_count = data.get('action_count', 0)
            
            if not action:
                return
            
            # アクション数制限のチェック
            max_actions_result = await self._settings_repository.get("recording.max_actions", 10000)
            if max_actions_result.is_success():
                max_actions = max_actions_result.value
                if action_count >= max_actions:
                    # 最大アクション数に達した場合の警告
                    await self._save_recording_log(
                        recording_id,
                        "WARNING",
                        f"最大アクション数に達しました: {action_count}/{max_actions}"
                    )
            
            # アクション追加ログ（詳細モードの場合のみ）
            verbose_logging_result = await self._settings_repository.get("debug.verbose_logging", False)
            if verbose_logging_result.is_success() and verbose_logging_result.value:
                await self._save_recording_log(
                    recording_id,
                    "ACTION_ADDED",
                    f"アクション追加: {action.action_type.value} (#{action.sequence_number})"
                )
            
        except Exception as e:
            print(f"アクション追加イベント処理エラー: {e}")
    
    async def _on_recording_deleted(self, data: Dict[str, Any]):
        """記録削除時の処理"""
        try:
            recording_id = data.get('recording_id')
            recording_name = data.get('recording_name', 'Unknown')
            
            print(f"記録削除: {recording_name}")
            
            # 削除ログの保存
            await self._save_recording_log(
                recording_id,
                "DELETED",
                f"記録を削除しました: {recording_name}"
            )
            
            # 関連ファイルのクリーンアップ
            await self._cleanup_recording_files(recording_id)
            
            # 統計情報の更新
            await self._update_recording_statistics("deleted")
            
        except Exception as e:
            print(f"記録削除イベント処理エラー: {e}")
    
    async def _on_recording_updated(self, data: Dict[str, Any]):
        """記録更新時の処理"""
        try:
            recording_id = data.get('recording_id')
            recording_name = data.get('recording_name', 'Unknown')
            changes = data.get('changes', {})
            
            # 重要な変更のみログ出力
            significant_changes = ['name', 'description', 'category']
            if any(field in changes for field in significant_changes):
                await self._save_recording_log(
                    recording_id,
                    "UPDATED",
                    f"記録を更新しました: {recording_name} (変更: {', '.join(changes.keys())})"
                )
            
        except Exception as e:
            print(f"記録更新イベント処理エラー: {e}")
    
    async def _save_recording_log(self, recording_id: str, level: str, message: str):
        """記録ログの保存"""
        try:
            log_entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'recording_id': recording_id,
                'level': level,
                'message': message
            }
            
            # ログファイルに保存（簡易実装）
            logs_dir = self._file_service.get_logs_dir()
            log_file = logs_dir / f"recording_{recording_id}.log"
            
            log_line = f"[{log_entry['timestamp']}] {level}: {message}\n"
            
            # ファイルに追記
            result = self._file_service.append_to_file(log_file, log_line)
            if result.is_failure():
                print(f"ログ保存エラー: {result.error}")
                
        except Exception as e:
            print(f"ログ保存エラー: {e}")
    
    async def _create_recording_backup(self, recording: Recording):
        """記録のバックアップ作成"""
        try:
            # バックアップディレクトリの取得
            backup_dir = self._file_service.get_backups_dir()
            
            # バックアップファイル名の生成
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_filename = f"recording_{recording.recording_id}_{timestamp}.json"
            backup_path = backup_dir / backup_filename
            
            # バックアップデータの作成
            backup_data = {
                'backup_timestamp': datetime.now(timezone.utc).isoformat(),
                'recording_id': recording.recording_id,
                'recording_name': recording.name,
                'recording_data': {
                    'name': recording.name,
                    'description': recording.description,
                    'action_count': recording.action_count,
                    'created_at': recording.created_at.isoformat(),
                    'completed_at': recording.completed_at.isoformat() if recording.completed_at else None,
                    'metadata': recording.metadata.to_dict(),
                    'playback_settings': recording.playback_settings.to_dict(),
                    'actions': [action.to_dict() for action in recording.actions]
                }
            }
            
            # ファイルに保存
            result = self._file_service.write_json_file(backup_path, backup_data)
            if result.is_success():
                print(f"バックアップ作成完了: {backup_filename}")
            else:
                print(f"バックアップ作成失敗: {result.error}")
                
        except Exception as e:
            print(f"バックアップ作成エラー: {e}")
    
    async def _update_recording_statistics(self, event_type: str):
        """記録統計情報の更新"""
        try:
            # 統計情報キーの設定
            stats_key = f"stats.recording.{event_type}_count"
            
            # 現在の値を取得
            current_result = await self._settings_repository.get(stats_key, 0)
            current_count = current_result.value if current_result.is_success() else 0
            
            # カウントを増加
            new_count = current_count + 1
            await self._settings_repository.set(stats_key, new_count)
            
            # 最終更新時刻も記録
            await self._settings_repository.set(
                "stats.recording.last_update",
                datetime.now(timezone.utc).isoformat()
            )
            
        except Exception as e:
            print(f"統計情報更新エラー: {e}")
    
    async def _send_completion_notification(self, recording: Recording):
        """完了通知の送信"""
        try:
            # 通知設定の確認
            notifications_enabled_result = await self._settings_repository.get("notifications.enabled", False)
            if not (notifications_enabled_result.is_success() and notifications_enabled_result.value):
                return
            
            # 完了通知の設定確認
            completion_notifications_result = await self._settings_repository.get("notifications.recording_completion", True)
            if not (completion_notifications_result.is_success() and completion_notifications_result.value):
                return
            
            # 通知メッセージの作成
            message = f"記録完了: {recording.name} ({recording.action_count}アクション)"
            
            # 実際の通知送信は実装時に行う（システムトレイ、メール等）
            print(f"[通知] {message}")
            
        except Exception as e:
            print(f"完了通知送信エラー: {e}")
    
    async def _send_error_notification(self, recording_name: str, error_message: str):
        """エラー通知の送信"""
        try:
            # エラー通知設定の確認
            error_notifications_result = await self._settings_repository.get("notifications.recording_errors", True)
            if not (error_notifications_result.is_success() and error_notifications_result.value):
                return
            
            # エラー通知メッセージの作成
            message = f"記録エラー: {recording_name} - {error_message}"
            
            # 実際の通知送信は実装時に行う
            print(f"[エラー通知] {message}")
            
        except Exception as e:
            print(f"エラー通知送信エラー: {e}")
    
    async def _cleanup_recording_files(self, recording_id: str):
        """記録関連ファイルのクリーンアップ"""
        try:
            # ログファイルの削除
            logs_dir = self._file_service.get_logs_dir()
            log_file = logs_dir / f"recording_{recording_id}.log"
            
            if log_file.exists():
                result = self._file_service.delete_file(log_file)
                if result.is_success():
                    print(f"ログファイル削除: {log_file.name}")
            
            # 一時ファイルの削除
            temp_dir = self._file_service.get_temp_dir()
            temp_pattern = f"recording_{recording_id}_*"
            
            # パターンマッチするファイルを削除（実装時にglob使用）
            # 簡易実装では省略
            
        except Exception as e:
            print(f"ファイルクリーンアップエラー: {e}")