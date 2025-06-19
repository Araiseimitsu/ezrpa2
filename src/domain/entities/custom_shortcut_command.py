"""
カスタムショートカットコマンドエンティティ

ユーザー定義のショートカットキーとそれに対応するコマンドを管理します。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Any
from enum import Enum
import json
import subprocess
import os
import shutil
from pathlib import Path

from .shortcut_settings import KeyCombination, KeyModifier


class CommandType(Enum):
    """コマンドタイプ"""
    APPLICATION = "application"      # アプリケーション起動
    FILE_OPERATION = "file_operation"  # ファイル操作
    SYSTEM_COMMAND = "system_command"  # システムコマンド
    SCRIPT_EXECUTION = "script_execution"  # スクリプト実行
    URL_OPEN = "url_open"           # URL開く
    TEXT_INPUT = "text_input"       # テキスト入力


@dataclass
class CommandParameter:
    """コマンドパラメータ"""
    name: str
    value: str
    description: str = ""
    
    def to_dict(self) -> Dict[str, str]:
        """辞書形式に変換"""
        return {
            "name": self.name,
            "value": self.value,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "CommandParameter":
        """辞書から復元"""
        return cls(
            name=data.get("name", ""),
            value=data.get("value", ""),
            description=data.get("description", "")
        )


@dataclass
class CustomShortcutCommand:
    """カスタムショートカットコマンド"""
    
    # 基本情報
    id: str = ""
    name: str = ""
    description: str = ""
    enabled: bool = True
    
    # キー組み合わせ
    key_combination: KeyCombination = field(default_factory=KeyCombination)
    
    # コマンド情報
    command_type: CommandType = CommandType.APPLICATION
    command: str = ""
    parameters: List[CommandParameter] = field(default_factory=list)
    working_directory: str = ""
    
    # 実行設定
    run_as_admin: bool = False
    wait_for_completion: bool = False
    timeout_seconds: int = 30
    
    # 条件設定
    active_window_title_pattern: str = ""  # 特定のウィンドウがアクティブな時のみ実行
    active_process_name_pattern: str = ""   # 特定のプロセスが実行中の時のみ実行
    
    def __post_init__(self):
        """初期化後処理"""
        if not self.id:
            import uuid
            self.id = str(uuid.uuid4())
    
    def get_display_text(self) -> str:
        """表示用テキストを取得"""
        key_text = str(self.key_combination) if self.key_combination else "未設定"
        status = "有効" if self.enabled else "無効"
        return f"{self.name} ({key_text}) - {status}"
    
    def get_parameter_value(self, name: str) -> Optional[str]:
        """パラメータ値を取得"""
        for param in self.parameters:
            if param.name == name:
                return param.value
        return None
    
    def set_parameter_value(self, name: str, value: str, description: str = ""):
        """パラメータ値を設定"""
        for param in self.parameters:
            if param.name == name:
                param.value = value
                if description:
                    param.description = description
                return
        
        # 新しいパラメータを追加
        self.parameters.append(CommandParameter(name, value, description))
    
    def remove_parameter(self, name: str) -> bool:
        """パラメータを削除"""
        for i, param in enumerate(self.parameters):
            if param.name == name:
                del self.parameters[i]
                return True
        return False
    
    def validate(self) -> List[str]:
        """設定を検証してエラーメッセージを返す"""
        errors = []
        
        if not self.name.strip():
            errors.append("コマンド名が設定されていません")
        
        if not self.key_combination or (not self.key_combination.key and not self.key_combination.modifiers):
            errors.append("キー組み合わせが設定されていません")
        
        if not self.command.strip():
            errors.append("コマンドが設定されていません")
        
        # コマンドタイプ別の検証
        if self.command_type == CommandType.APPLICATION:
            if not os.path.exists(self.command) and not shutil.which(self.command):
                errors.append(f"実行ファイルが見つかりません: {self.command}")
        
        elif self.command_type == CommandType.FILE_OPERATION:
            # ファイル操作の場合、コマンドが有効なファイルパスかチェック
            if not os.path.exists(os.path.dirname(self.command)) if os.path.dirname(self.command) else False:
                errors.append(f"ファイルのディレクトリが存在しません: {self.command}")
        
        elif self.command_type == CommandType.SCRIPT_EXECUTION:
            if not os.path.exists(self.command):
                errors.append(f"スクリプトファイルが見つかりません: {self.command}")
        
        elif self.command_type == CommandType.URL_OPEN:
            if not (self.command.startswith("http://") or self.command.startswith("https://") or self.command.startswith("file://")):
                errors.append("有効なURL形式ではありません")
        
        # タイムアウト設定の検証
        if self.timeout_seconds < 1 or self.timeout_seconds > 3600:
            errors.append("タイムアウト時間は1秒から3600秒の間で設定してください")
        
        return errors
    
    def can_execute(self) -> bool:
        """実行可能かチェック"""
        if not self.enabled:
            return False
        
        errors = self.validate()
        return len(errors) == 0
    
    def execute(self) -> bool:
        """コマンドを実行"""
        if not self.can_execute():
            return False
        
        try:
            if self.command_type == CommandType.APPLICATION:
                return self._execute_application()
            elif self.command_type == CommandType.FILE_OPERATION:
                return self._execute_file_operation()
            elif self.command_type == CommandType.SYSTEM_COMMAND:
                return self._execute_system_command()
            elif self.command_type == CommandType.SCRIPT_EXECUTION:
                return self._execute_script()
            elif self.command_type == CommandType.URL_OPEN:
                return self._execute_url_open()
            elif self.command_type == CommandType.TEXT_INPUT:
                return self._execute_text_input()
            
        except Exception as e:
            print(f"コマンド実行エラー: {e}")
            return False
        
        return False
    
    def _execute_application(self) -> bool:
        """アプリケーション実行"""
        cmd = [self.command]
        
        # パラメータを追加
        for param in self.parameters:
            if param.value:
                cmd.append(param.value)
        
        subprocess.Popen(
            cmd,
            cwd=self.working_directory if self.working_directory else None,
            shell=True
        )
        return True
    
    def _execute_file_operation(self) -> bool:
        """ファイル操作実行"""
        # Windowsのexplorerでファイルを開く
        if os.path.exists(self.command):
            os.startfile(self.command)
            return True
        return False
    
    def _execute_system_command(self) -> bool:
        """システムコマンド実行"""
        cmd = self.command
        
        # パラメータを文字列として結合
        param_str = " ".join([param.value for param in self.parameters if param.value])
        if param_str:
            cmd = f"{cmd} {param_str}"
        
        if self.wait_for_completion:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=self.working_directory if self.working_directory else None,
                timeout=self.timeout_seconds
            )
            return result.returncode == 0
        else:
            subprocess.Popen(
                cmd,
                shell=True,
                cwd=self.working_directory if self.working_directory else None
            )
            return True
    
    def _execute_script(self) -> bool:
        """スクリプト実行"""
        if not os.path.exists(self.command):
            return False
        
        # ファイル拡張子に基づいて実行方法を決定
        ext = Path(self.command).suffix.lower()
        
        if ext == '.py':
            cmd = ['python', self.command]
        elif ext == '.bat' or ext == '.cmd':
            cmd = [self.command]
        elif ext == '.ps1':
            cmd = ['powershell', '-ExecutionPolicy', 'Bypass', '-File', self.command]
        else:
            cmd = [self.command]
        
        # パラメータを追加
        for param in self.parameters:
            if param.value:
                cmd.append(param.value)
        
        if self.wait_for_completion:
            result = subprocess.run(
                cmd,
                cwd=self.working_directory if self.working_directory else None,
                timeout=self.timeout_seconds
            )
            return result.returncode == 0
        else:
            subprocess.Popen(
                cmd,
                cwd=self.working_directory if self.working_directory else None
            )
            return True
    
    def _execute_url_open(self) -> bool:
        """URL開く"""
        import webbrowser
        webbrowser.open(self.command)
        return True
    
    def _execute_text_input(self) -> bool:
        """テキスト入力（クリップボード経由）"""
        try:
            import pyperclip
            pyperclip.copy(self.command)
            
            # Ctrl+Vでペースト
            import time
            from src.infrastructure.adapters.keyboard_adapter import KeyboardAdapter
            
            keyboard = KeyboardAdapter()
            time.sleep(0.1)  # 少し待機
            keyboard.send_key_combination(['ctrl'], 'v')
            return True
        except ImportError:
            # pyperclipが利用できない場合の代替処理
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換（設定保存用）"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "key_combination": {
                "modifiers": [mod.value for mod in self.key_combination.modifiers],
                "key": self.key_combination.key,
                "description": self.key_combination.description
            },
            "command_type": self.command_type.value,
            "command": self.command,
            "parameters": [param.to_dict() for param in self.parameters],
            "working_directory": self.working_directory,
            "run_as_admin": self.run_as_admin,
            "wait_for_completion": self.wait_for_completion,
            "timeout_seconds": self.timeout_seconds,
            "active_window_title_pattern": self.active_window_title_pattern,
            "active_process_name_pattern": self.active_process_name_pattern
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CustomShortcutCommand":
        """辞書から復元"""
        key_combo_data = data.get("key_combination", {})
        modifiers = {KeyModifier(mod) for mod in key_combo_data.get("modifiers", [])}
        key_combination = KeyCombination(
            modifiers=modifiers,
            key=key_combo_data.get("key", ""),
            description=key_combo_data.get("description", "")
        )
        
        parameters = [
            CommandParameter.from_dict(param_data) 
            for param_data in data.get("parameters", [])
        ]
        
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
            key_combination=key_combination,
            command_type=CommandType(data.get("command_type", CommandType.APPLICATION.value)),
            command=data.get("command", ""),
            parameters=parameters,
            working_directory=data.get("working_directory", ""),
            run_as_admin=data.get("run_as_admin", False),
            wait_for_completion=data.get("wait_for_completion", False),
            timeout_seconds=data.get("timeout_seconds", 30),
            active_window_title_pattern=data.get("active_window_title_pattern", ""),
            active_process_name_pattern=data.get("active_process_name_pattern", "")
        )


def create_preset_commands() -> List[CustomShortcutCommand]:
    """プリセットコマンドを作成"""
    presets = []
    
    # 電卓を開く
    calc_cmd = CustomShortcutCommand(
        name="電卓を開く",
        description="Windows電卓アプリケーションを起動",
        key_combination=KeyCombination({KeyModifier.CTRL, KeyModifier.ALT}, "c", "電卓起動"),
        command_type=CommandType.APPLICATION,
        command="calc.exe"
    )
    presets.append(calc_cmd)
    
    # メモ帳を開く
    notepad_cmd = CustomShortcutCommand(
        name="メモ帳を開く",
        description="Windowsメモ帳アプリケーションを起動",
        key_combination=KeyCombination({KeyModifier.CTRL, KeyModifier.ALT}, "n", "メモ帳起動"),
        command_type=CommandType.APPLICATION,
        command="notepad.exe"
    )
    presets.append(notepad_cmd)
    
    # エクスプローラーでデスクトップを開く
    desktop_cmd = CustomShortcutCommand(
        name="デスクトップフォルダを開く",
        description="エクスプローラーでデスクトップフォルダを開く",
        key_combination=KeyCombination({KeyModifier.CTRL, KeyModifier.ALT}, "d", "デスクトップ表示"),
        command_type=CommandType.FILE_OPERATION,
        command=os.path.join(os.path.expanduser("~"), "Desktop")
    )
    presets.append(desktop_cmd)
    
    # Google検索を開く
    google_cmd = CustomShortcutCommand(
        name="Google検索",
        description="ブラウザでGoogle検索ページを開く",
        key_combination=KeyCombination({KeyModifier.CTRL, KeyModifier.ALT}, "g", "Google検索"),
        command_type=CommandType.URL_OPEN,
        command="https://www.google.com"
    )
    presets.append(google_cmd)
    
    # 現在の日時をテキスト入力
    datetime_cmd = CustomShortcutCommand(
        name="現在日時入力",
        description="現在の日時をテキストとして入力",
        key_combination=KeyCombination({KeyModifier.CTRL, KeyModifier.ALT}, "t", "日時入力"),
        command_type=CommandType.TEXT_INPUT,
        command=""  # 実行時に動的生成
    )
    presets.append(datetime_cmd)
    
    return presets