"""
ファイルシステムサービス - ファイル・ディレクトリ操作

Windows環境でのファイルシステム操作、バックアップ、
レジストリアクセス等を提供するサービスです。
"""

import json
import shutil
import threading
import winreg
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
import os

from ...core.result import Result, Ok, Err, ErrorInfo
from ...shared.constants import (
    WindowsPaths, RegistryPaths, ApplicationConstants, 
    ValidationConstants, PerformanceConstants
)


class FileService:
    """ファイルシステムサービス実装"""
    
    def __init__(self):
        self._lock = threading.RLock()
        
        # 主要ディレクトリの初期化
        self._app_data_dir = WindowsPaths.get_app_data_dir()
        self._documents_dir = WindowsPaths.get_documents_dir()
        self._temp_dir = WindowsPaths.get_temp_dir()
        self._logs_dir = WindowsPaths.get_logs_dir()
        self._recordings_dir = WindowsPaths.get_recordings_dir()
        self._backups_dir = WindowsPaths.get_backups_dir()
        
        self._ensure_directories()
    
    def _ensure_directories(self):
        """必要なディレクトリを作成"""
        directories = [
            self._app_data_dir,
            self._documents_dir,
            self._temp_dir,
            self._logs_dir,
            self._recordings_dir,
            self._backups_dir
        ]
        
        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass  # エラーは無視（権限不足等）
    
    def get_app_data_dir(self) -> Path:
        """アプリケーションデータディレクトリを取得"""
        return self._app_data_dir
    
    def get_documents_dir(self) -> Path:
        """ドキュメントディレクトリを取得"""
        return self._documents_dir
    
    def get_recordings_dir(self) -> Path:
        """記録ファイルディレクトリを取得"""
        return self._recordings_dir
    
    def get_backups_dir(self) -> Path:
        """バックアップディレクトリを取得"""
        return self._backups_dir
    
    def get_logs_dir(self) -> Path:
        """ログディレクトリを取得"""
        return self._logs_dir
    
    def get_temp_dir(self) -> Path:
        """一時ディレクトリを取得"""
        return self._temp_dir
    
    def read_file(self, file_path: Union[str, Path]) -> Result[str, str]:
        """ファイルを読み込み"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return Err(f"ファイルが存在しません: {file_path}")
            
            if file_path.stat().st_size > PerformanceConstants.MAX_FILE_SIZE_MB * 1024 * 1024:
                return Err(f"ファイルサイズが上限を超えています: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return Ok(content)
            
        except PermissionError:
            return Err(f"ファイルへのアクセス権限がありません: {file_path}")
        except UnicodeDecodeError:
            return Err(f"ファイルのエンコーディングが無効です: {file_path}")
        except Exception as e:
            return Err(f"ファイル読み込みエラー: {str(e)}")
    
    def write_file(self, file_path: Union[str, Path], content: str, 
                   backup: bool = True) -> Result[None, str]:
        """ファイルを書き込み"""
        try:
            file_path = Path(file_path)
            
            # ディレクトリの作成
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # バックアップ作成
            if backup and file_path.exists():
                backup_result = self.create_backup(file_path)
                if backup_result.is_failure():
                    return backup_result
            
            # ファイル書き込み
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return Ok(None)
            
        except PermissionError:
            return Err(f"ファイルへの書き込み権限がありません: {file_path}")
        except OSError as e:
            if e.errno == 28:  # No space left on device
                return Err("ディスク容量が不足しています")
            return Err(f"ファイル書き込みエラー: {str(e)}")
        except Exception as e:
            return Err(f"ファイル書き込みエラー: {str(e)}")
    
    def read_binary_file(self, file_path: Union[str, Path]) -> Result[bytes, str]:
        """バイナリファイルを読み込み"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return Err(f"ファイルが存在しません: {file_path}")
            
            if file_path.stat().st_size > PerformanceConstants.MAX_FILE_SIZE_MB * 1024 * 1024:
                return Err(f"ファイルサイズが上限を超えています: {file_path}")
            
            with open(file_path, 'rb') as f:
                content = f.read()
            
            return Ok(content)
            
        except Exception as e:
            return Err(f"バイナリファイル読み込みエラー: {str(e)}")
    
    def write_binary_file(self, file_path: Union[str, Path], content: bytes, 
                         backup: bool = True) -> Result[None, str]:
        """バイナリファイルを書き込み"""
        try:
            file_path = Path(file_path)
            
            # ディレクトリの作成
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # バックアップ作成
            if backup and file_path.exists():
                backup_result = self.create_backup(file_path)
                if backup_result.is_failure():
                    return backup_result
            
            # ファイル書き込み
            with open(file_path, 'wb') as f:
                f.write(content)
            
            return Ok(None)
            
        except Exception as e:
            return Err(f"バイナリファイル書き込みエラー: {str(e)}")
    
    def read_json_file(self, file_path: Union[str, Path]) -> Result[Dict[str, Any], str]:
        """JSONファイルを読み込み"""
        try:
            content_result = self.read_file(file_path)
            if content_result.is_failure():
                return content_result
            
            json_data = json.loads(content_result.value)
            return Ok(json_data)
            
        except json.JSONDecodeError as e:
            return Err(f"JSON解析エラー: {str(e)}")
        except Exception as e:
            return Err(f"JSONファイル読み込みエラー: {str(e)}")
    
    def write_json_file(self, file_path: Union[str, Path], data: Dict[str, Any], 
                       backup: bool = True, indent: int = 2) -> Result[None, str]:
        """JSONファイルを書き込み"""
        try:
            json_content = json.dumps(data, ensure_ascii=False, indent=indent)
            return self.write_file(file_path, json_content, backup)
            
        except (TypeError, ValueError) as e:
            return Err(f"JSONシリアライゼーションエラー: {str(e)}")
        except Exception as e:
            return Err(f"JSONファイル書き込みエラー: {str(e)}")
    
    def delete_file(self, file_path: Union[str, Path], 
                   create_backup: bool = True) -> Result[None, str]:
        """ファイルを削除"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return Ok(None)  # 既に存在しない場合は成功として扱う
            
            # バックアップ作成
            if create_backup:
                backup_result = self.create_backup(file_path)
                if backup_result.is_failure():
                    return backup_result
            
            file_path.unlink()
            return Ok(None)
            
        except PermissionError:
            return Err(f"ファイル削除権限がありません: {file_path}")
        except Exception as e:
            return Err(f"ファイル削除エラー: {str(e)}")
    
    def copy_file(self, source_path: Union[str, Path], 
                 dest_path: Union[str, Path]) -> Result[None, str]:
        """ファイルをコピー"""
        try:
            source_path = Path(source_path)
            dest_path = Path(dest_path)
            
            if not source_path.exists():
                return Err(f"コピー元ファイルが存在しません: {source_path}")
            
            # ディレクトリの作成
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(source_path, dest_path)
            return Ok(None)
            
        except PermissionError:
            return Err(f"ファイルコピー権限がありません")
        except shutil.SameFileError:
            return Err("コピー元と先が同じファイルです")
        except Exception as e:
            return Err(f"ファイルコピーエラー: {str(e)}")
    
    def move_file(self, source_path: Union[str, Path], 
                 dest_path: Union[str, Path]) -> Result[None, str]:
        """ファイルを移動"""
        try:
            source_path = Path(source_path)
            dest_path = Path(dest_path)
            
            if not source_path.exists():
                return Err(f"移動元ファイルが存在しません: {source_path}")
            
            # ディレクトリの作成
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.move(str(source_path), str(dest_path))
            return Ok(None)
            
        except PermissionError:
            return Err(f"ファイル移動権限がありません")
        except Exception as e:
            return Err(f"ファイル移動エラー: {str(e)}")
    
    def list_files(self, directory_path: Union[str, Path], 
                  pattern: str = "*", recursive: bool = False) -> Result[List[Path], str]:
        """ディレクトリ内のファイルを一覧取得"""
        try:
            directory_path = Path(directory_path)
            
            if not directory_path.exists():
                return Err(f"ディレクトリが存在しません: {directory_path}")
            
            if not directory_path.is_dir():
                return Err(f"指定されたパスはディレクトリではありません: {directory_path}")
            
            if recursive:
                files = list(directory_path.rglob(pattern))
            else:
                files = list(directory_path.glob(pattern))
            
            # ファイルのみフィルタリング
            files = [f for f in files if f.is_file()]
            
            return Ok(files)
            
        except PermissionError:
            return Err(f"ディレクトリへのアクセス権限がありません: {directory_path}")
        except Exception as e:
            return Err(f"ファイル一覧取得エラー: {str(e)}")
    
    def create_directory(self, directory_path: Union[str, Path]) -> Result[None, str]:
        """ディレクトリを作成"""
        try:
            directory_path = Path(directory_path)
            directory_path.mkdir(parents=True, exist_ok=True)
            return Ok(None)
            
        except PermissionError:
            return Err(f"ディレクトリ作成権限がありません: {directory_path}")
        except Exception as e:
            return Err(f"ディレクトリ作成エラー: {str(e)}")
    
    def delete_directory(self, directory_path: Union[str, Path], 
                        create_backup: bool = True) -> Result[None, str]:
        """ディレクトリを削除"""
        try:
            directory_path = Path(directory_path)
            
            if not directory_path.exists():
                return Ok(None)  # 既に存在しない場合は成功として扱う
            
            if not directory_path.is_dir():
                return Err(f"指定されたパスはディレクトリではありません: {directory_path}")
            
            # バックアップ作成
            if create_backup:
                backup_result = self.create_directory_backup(directory_path)
                if backup_result.is_failure():
                    return backup_result
            
            shutil.rmtree(directory_path)
            return Ok(None)
            
        except PermissionError:
            return Err(f"ディレクトリ削除権限がありません: {directory_path}")
        except Exception as e:
            return Err(f"ディレクトリ削除エラー: {str(e)}")
    
    def create_backup(self, file_path: Union[str, Path]) -> Result[Path, str]:
        """ファイルのバックアップを作成"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return Err(f"バックアップ対象ファイルが存在しません: {file_path}")
            
            # バックアップファイル名生成
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{file_path.stem}_{timestamp}{file_path.suffix}"
            backup_path = self._backups_dir / backup_filename
            
            # バックアップ実行
            copy_result = self.copy_file(file_path, backup_path)
            if copy_result.is_success():
                return Ok(backup_path)
            else:
                return copy_result
                
        except Exception as e:
            return Err(f"バックアップ作成エラー: {str(e)}")
    
    def create_directory_backup(self, directory_path: Union[str, Path]) -> Result[Path, str]:
        """ディレクトリのバックアップを作成"""
        try:
            directory_path = Path(directory_path)
            
            if not directory_path.exists():
                return Err(f"バックアップ対象ディレクトリが存在しません: {directory_path}")
            
            # バックアップディレクトリ名生成
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_dirname = f"{directory_path.name}_{timestamp}"
            backup_path = self._backups_dir / backup_dirname
            
            # バックアップ実行
            shutil.copytree(directory_path, backup_path)
            return Ok(backup_path)
            
        except Exception as e:
            return Err(f"ディレクトリバックアップ作成エラー: {str(e)}")
    
    def cleanup_old_backups(self, max_backups: int = 10) -> Result[int, str]:
        """古いバックアップファイルを削除"""
        try:
            backups_result = self.list_files(self._backups_dir, recursive=True)
            if backups_result.is_failure():
                return backups_result
            
            backups = backups_result.value
            
            # 更新日時でソート（新しい順）
            backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            deleted_count = 0
            for backup_file in backups[max_backups:]:
                try:
                    backup_file.unlink()
                    deleted_count += 1
                except Exception:
                    pass  # 個別のエラーは無視
            
            return Ok(deleted_count)
            
        except Exception as e:
            return Err(f"バックアップクリーンアップエラー: {str(e)}")
    
    def get_file_info(self, file_path: Union[str, Path]) -> Result[Dict[str, Any], str]:
        """ファイル情報を取得"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return Err(f"ファイルが存在しません: {file_path}")
            
            stat = file_path.stat()
            
            info = {
                'path': str(file_path),
                'name': file_path.name,
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime, timezone.utc).isoformat(),
                'modified': datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                'accessed': datetime.fromtimestamp(stat.st_atime, timezone.utc).isoformat(),
                'is_file': file_path.is_file(),
                'is_directory': file_path.is_dir(),
                'is_hidden': bool(stat.st_file_attributes & 2) if hasattr(stat, 'st_file_attributes') else False,
                'extension': file_path.suffix
            }
            
            return Ok(info)
            
        except Exception as e:
            return Err(f"ファイル情報取得エラー: {str(e)}")
    
    def get_disk_usage(self, path: Union[str, Path] = None) -> Result[Dict[str, int], str]:
        """ディスク使用量を取得"""
        try:
            if path is None:
                path = self._app_data_dir
            else:
                path = Path(path)
            
            usage = shutil.disk_usage(path)
            
            info = {
                'total': usage.total,
                'used': usage.used,
                'free': usage.free,
                'used_percent': round((usage.used / usage.total) * 100, 2)
            }
            
            return Ok(info)
            
        except Exception as e:
            return Err(f"ディスク使用量取得エラー: {str(e)}")
    
    # Windows レジストリ操作
    def read_registry_value(self, key_path: str, value_name: str, 
                           root_key: int = winreg.HKEY_CURRENT_USER) -> Result[Any, str]:
        """レジストリ値を読み取り"""
        try:
            with winreg.OpenKey(root_key, key_path) as key:
                value, reg_type = winreg.QueryValueEx(key, value_name)
                return Ok(value)
                
        except FileNotFoundError:
            return Err(f"レジストリキーまたは値が見つかりません: {key_path}\\{value_name}")
        except PermissionError:
            return Err(f"レジストリへのアクセス権限がありません: {key_path}")
        except Exception as e:
            return Err(f"レジストリ読み取りエラー: {str(e)}")
    
    def write_registry_value(self, key_path: str, value_name: str, value: Any, 
                           value_type: int = winreg.REG_SZ,
                           root_key: int = winreg.HKEY_CURRENT_USER) -> Result[None, str]:
        """レジストリ値を書き込み"""
        try:
            with winreg.CreateKey(root_key, key_path) as key:
                winreg.SetValueEx(key, value_name, 0, value_type, value)
                return Ok(None)
                
        except PermissionError:
            return Err(f"レジストリへの書き込み権限がありません: {key_path}")
        except Exception as e:
            return Err(f"レジストリ書き込みエラー: {str(e)}")
    
    def delete_registry_value(self, key_path: str, value_name: str,
                            root_key: int = winreg.HKEY_CURRENT_USER) -> Result[None, str]:
        """レジストリ値を削除"""
        try:
            with winreg.OpenKey(root_key, key_path, access=winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, value_name)
                return Ok(None)
                
        except FileNotFoundError:
            return Ok(None)  # 既に存在しない場合は成功として扱う
        except PermissionError:
            return Err(f"レジストリ削除権限がありません: {key_path}")
        except Exception as e:
            return Err(f"レジストリ削除エラー: {str(e)}")
    
    def is_admin_rights(self) -> bool:
        """管理者権限で実行されているかチェック"""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    
    def create_shortcut(self, target_path: str, shortcut_path: str, 
                       description: str = "") -> Result[None, str]:
        """ショートカットを作成"""
        try:
            import win32com.client
            
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = target_path
            shortcut.Description = description
            shortcut.save()
            
            return Ok(None)
            
        except ImportError:
            return Err("pywin32ライブラリが必要です")
        except Exception as e:
            return Err(f"ショートカット作成エラー: {str(e)}")
    
    def get_available_drives(self) -> List[str]:
        """利用可能なドライブ一覧を取得"""
        drives = []
        for drive_letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            drive_path = f"{drive_letter}:\\"
            if os.path.exists(drive_path):
                drives.append(drive_path)
        return drives