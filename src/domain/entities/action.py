"""
Action エンティティ - RPAアクションの基本単位

Windows環境でのキーボード・マウス・ウィンドウ操作等の
RPAアクションを表現するドメインエンティティです。
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from ..value_objects import (
    ActionType, Coordinate, Duration, KeyInput, MouseInput, MouseButton,
    WindowInfo, FileInfo, ValidationResult, CommonDurations
)
from ...core.result import Result, Ok, Err, ErrorInfo


@dataclass
class ActionBase(ABC):
    """
    アクション基底クラス
    
    すべてのRPAアクションの共通属性とメソッドを定義します。
    """
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_type: ActionType = field(init=False)
    sequence_number: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    description: str = ""
    delay_before: Duration = CommonDurations.IMMEDIATE
    delay_after: Duration = CommonDurations.IMMEDIATE
    timeout: Duration = Duration(5000)  # 5秒
    retry_count: int = 1
    continue_on_error: bool = False
    screenshot_before: bool = False
    screenshot_after: bool = False
    
    # メタデータ
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    # 実行時情報
    execution_count: int = 0
    last_execution_time: Optional[datetime] = None
    last_execution_result: Optional[bool] = None
    last_error_message: Optional[str] = None
    
    def __post_init__(self):
        """初期化後の処理"""
        if not hasattr(self, 'action_type'):
            raise ValueError("action_typeが設定されていません")
        
        # メタデータに基本情報を追加
        self.metadata.update({
            "created_at": self.timestamp.isoformat(),
            "platform": "windows",
            "version": "2.0"
        })
    
    @abstractmethod
    def validate(self) -> ValidationResult:
        """アクションのバリデーション"""
        pass
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        pass
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActionBase':
        """辞書から復元"""
        pass
    
    def mark_executed(self, success: bool, error_message: Optional[str] = None) -> None:
        """実行結果をマーク"""
        self.execution_count += 1
        self.last_execution_time = datetime.now(timezone.utc)
        self.last_execution_result = success
        self.last_error_message = error_message
    
    def clone(self) -> 'ActionBase':
        """アクションのクローンを作成"""
        cloned_data = self.to_dict()
        cloned_data['action_id'] = str(uuid.uuid4())
        cloned_data['execution_count'] = 0
        # 実行時情報を削除
        cloned_data.pop('last_execution_time', None)
        cloned_data.pop('last_execution_result', None)
        cloned_data.pop('last_error_message', None)
        return self.__class__.from_dict(cloned_data)
    
    def add_tag(self, tag: str) -> None:
        """タグを追加"""
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: str) -> None:
        """タグを削除"""
        if tag in self.tags:
            self.tags.remove(tag)
    
    def has_tag(self, tag: str) -> bool:
        """タグを持っているかチェック"""
        return tag in self.tags


@dataclass
class KeyboardAction(ActionBase):
    """キーボード操作アクション"""
    
    key_input: Optional[KeyInput] = None
    text: Optional[str] = None
    input_method: str = "direct"  # "direct", "ime", "clipboard"
    
    def __post_init__(self):
        if self.key_input and self.text:
            self.action_type = ActionType.KEY_COMBINATION
        elif self.key_input:
            self.action_type = ActionType.KEY_PRESS
        elif self.text:
            self.action_type = ActionType.TEXT_INPUT
        else:
            raise ValueError("key_inputまたはtextのいずれかが必要です")
        
        super().__post_init__()
        
        # 日本語入力の場合のメタデータ追加
        if self.text and any('\u3040' <= c <= '\u309F' or '\u30A0' <= c <= '\u30FF' or '\u4E00' <= c <= '\u9FAF' for c in self.text):
            self.metadata['requires_ime'] = True
            if self.input_method == "direct":
                self.input_method = "ime"  # 日本語の場合は自動的にIME使用
    
    def validate(self) -> ValidationResult:
        """キーボードアクションのバリデーション"""
        errors = []
        warnings = []
        
        if not self.key_input and not self.text:
            errors.append("キー入力またはテキストが指定されていません")
        
        if self.text:
            if len(self.text) > 1000:
                warnings.append("テキストが長すぎます（1000文字以上）")
            
            # Windows環境での制御文字チェック
            invalid_chars = [c for c in self.text if ord(c) < 32 and c not in '\t\n\r']
            if invalid_chars:
                warnings.append(f"制御文字が含まれています: {invalid_chars}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = {
            'action_id': self.action_id,
            'action_type': self.action_type.value,
            'sequence_number': self.sequence_number,
            'timestamp': self.timestamp.isoformat(),
            'description': self.description,
            'delay_before': self.delay_before.milliseconds,
            'delay_after': self.delay_after.milliseconds,
            'timeout': self.timeout.milliseconds,
            'retry_count': self.retry_count,
            'continue_on_error': self.continue_on_error,
            'screenshot_before': self.screenshot_before,
            'screenshot_after': self.screenshot_after,
            'metadata': self.metadata,
            'tags': self.tags,
            'execution_count': self.execution_count,
            'text': self.text,
            'input_method': self.input_method
        }
        
        if self.key_input:
            data['key_input'] = {
                'key_code': self.key_input.key_code,
                'shift': self.key_input.shift,
                'ctrl': self.key_input.ctrl,
                'alt': self.key_input.alt,
                'win': self.key_input.win
            }
        
        if self.last_execution_time:
            data['last_execution_time'] = self.last_execution_time.isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KeyboardAction':
        """辞書から復元"""
        key_input = None
        if 'key_input' in data:
            key_data = data['key_input']
            key_input = KeyInput(
                key_code=key_data['key_code'],
                shift=key_data.get('shift', False),
                ctrl=key_data.get('ctrl', False),
                alt=key_data.get('alt', False),
                win=key_data.get('win', False)
            )
        
        action = cls(
            action_id=data['action_id'],
            sequence_number=data.get('sequence_number', 0),
            timestamp=datetime.fromisoformat(data['timestamp']),
            description=data.get('description', ''),
            delay_before=Duration(data.get('delay_before', 0)),
            delay_after=Duration(data.get('delay_after', 0)),
            timeout=Duration(data.get('timeout', 5000)),
            retry_count=data.get('retry_count', 1),
            continue_on_error=data.get('continue_on_error', False),
            screenshot_before=data.get('screenshot_before', False),
            screenshot_after=data.get('screenshot_after', False),
            metadata=data.get('metadata', {}),
            tags=data.get('tags', []),
            execution_count=data.get('execution_count', 0),
            key_input=key_input,
            text=data.get('text'),
            input_method=data.get('input_method', 'direct')
        )
        
        if 'last_execution_time' in data:
            action.last_execution_time = datetime.fromisoformat(data['last_execution_time'])
        
        return action


@dataclass
class MouseAction(ActionBase):
    """マウス操作アクション"""
    
    mouse_input: Optional[MouseInput] = None
    target_window: Optional[WindowInfo] = None
    relative_to_window: bool = False
    
    def __post_init__(self):
        if not self.mouse_input:
            raise ValueError("mouse_inputが必要です")
            
        if self.mouse_input.double_click:
            self.action_type = ActionType.MOUSE_DOUBLE_CLICK
        elif self.mouse_input.wheel_delta != 0:
            self.action_type = ActionType.MOUSE_WHEEL
        else:
            self.action_type = ActionType.MOUSE_CLICK
        
        super().__post_init__()
        
        # Windows環境での座標メタデータ
        self.metadata.update({
            'absolute_position': {
                'x': self.mouse_input.position.x,
                'y': self.mouse_input.position.y
            },
            'dpi_scale': self.mouse_input.position.dpi_scale,
            'relative_to_window': self.relative_to_window
        })
    
    def validate(self) -> ValidationResult:
        """マウスアクションのバリデーション"""
        errors = []
        warnings = []
        
        # 座標範囲チェック
        pos = self.mouse_input.position
        if pos.x < 0 or pos.y < 0:
            warnings.append("負の座標値が指定されています")
        
        if pos.x > 32767 or pos.y > 32767:
            warnings.append("座標値が大きすぎます（32767を超過）")
        
        # ウィンドウ相対座標の場合のチェック
        if self.relative_to_window and not self.target_window:
            errors.append("相対座標指定時はtarget_windowが必要です")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = {
            'action_id': self.action_id,
            'action_type': self.action_type.value,
            'sequence_number': self.sequence_number,
            'timestamp': self.timestamp.isoformat(),
            'description': self.description,
            'delay_before': self.delay_before.milliseconds,
            'delay_after': self.delay_after.milliseconds,
            'timeout': self.timeout.milliseconds,
            'retry_count': self.retry_count,
            'continue_on_error': self.continue_on_error,
            'screenshot_before': self.screenshot_before,
            'screenshot_after': self.screenshot_after,
            'metadata': self.metadata,
            'tags': self.tags,
            'execution_count': self.execution_count,
            'mouse_input': {
                'button': self.mouse_input.button.value,
                'position': {
                    'x': self.mouse_input.position.x,
                    'y': self.mouse_input.position.y,
                    'dpi_scale': self.mouse_input.position.dpi_scale
                },
                'double_click': self.mouse_input.double_click,
                'wheel_delta': self.mouse_input.wheel_delta
            },
            'relative_to_window': self.relative_to_window
        }
        
        if self.target_window:
            data['target_window'] = {
                'title': self.target_window.title,
                'class_name': self.target_window.class_name,
                'process_name': self.target_window.process_name,
                'handle': self.target_window.handle
            }
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MouseAction':
        """辞書から復元"""
        mouse_data = data['mouse_input']
        mouse_input = MouseInput(
            button=MouseButton(mouse_data['button']),
            position=Coordinate(
                x=mouse_data['position']['x'],
                y=mouse_data['position']['y'],
                dpi_scale=mouse_data['position'].get('dpi_scale', 1.0)
            ),
            double_click=mouse_data.get('double_click', False),
            wheel_delta=mouse_data.get('wheel_delta', 0)
        )
        
        target_window = None
        if 'target_window' in data:
            win_data = data['target_window']
            target_window = WindowInfo(
                title=win_data['title'],
                class_name=win_data['class_name'],
                process_name=win_data['process_name'],
                handle=win_data.get('handle')
            )
        
        return cls(
            action_id=data['action_id'],
            sequence_number=data.get('sequence_number', 0),
            timestamp=datetime.fromisoformat(data['timestamp']),
            description=data.get('description', ''),
            delay_before=Duration(data.get('delay_before', 0)),
            delay_after=Duration(data.get('delay_after', 0)),
            timeout=Duration(data.get('timeout', 5000)),
            retry_count=data.get('retry_count', 1),
            continue_on_error=data.get('continue_on_error', False),
            screenshot_before=data.get('screenshot_before', False),
            screenshot_after=data.get('screenshot_after', False),
            metadata=data.get('metadata', {}),
            tags=data.get('tags', []),
            execution_count=data.get('execution_count', 0),
            mouse_input=mouse_input,
            target_window=target_window,
            relative_to_window=data.get('relative_to_window', False)
        )


@dataclass
class WindowAction(ActionBase):
    """ウィンドウ操作アクション"""
    
    target_window: Optional[WindowInfo] = None
    new_position: Optional[Coordinate] = None
    new_size: Optional[Coordinate] = None  # 幅と高さをCoordinateで表現
    
    def __post_init__(self):
        if not self.target_window:
            raise ValueError("target_windowが必要です")
            
        # ウィンドウ操作タイプの判定
        if self.new_position and self.new_size:
            self.action_type = ActionType.WINDOW_RESIZE
        elif self.new_position:
            self.action_type = ActionType.WINDOW_ACTIVATE
        else:
            self.action_type = ActionType.WINDOW_ACTIVATE
        
        super().__post_init__()
    
    def validate(self) -> ValidationResult:
        """ウィンドウアクションのバリデーション"""
        errors = []
        warnings = []
        
        if not self.target_window.title and not self.target_window.class_name:
            errors.append("ウィンドウタイトルまたはクラス名が必要です")
        
        if self.new_size:
            if self.new_size.x <= 0 or self.new_size.y <= 0:
                errors.append("ウィンドウサイズは正の値である必要があります")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = {
            'action_id': self.action_id,
            'action_type': self.action_type.value,
            'sequence_number': self.sequence_number,
            'timestamp': self.timestamp.isoformat(),
            'description': self.description,
            'delay_before': self.delay_before.milliseconds,
            'delay_after': self.delay_after.milliseconds,
            'timeout': self.timeout.milliseconds,
            'retry_count': self.retry_count,
            'continue_on_error': self.continue_on_error,
            'screenshot_before': self.screenshot_before,
            'screenshot_after': self.screenshot_after,
            'metadata': self.metadata,
            'tags': self.tags,
            'execution_count': self.execution_count,
            'target_window': {
                'title': self.target_window.title,
                'class_name': self.target_window.class_name,
                'process_name': self.target_window.process_name,
                'handle': self.target_window.handle
            }
        }
        
        if self.new_position:
            data['new_position'] = {
                'x': self.new_position.x,
                'y': self.new_position.y
            }
        
        if self.new_size:
            data['new_size'] = {
                'width': self.new_size.x,
                'height': self.new_size.y
            }
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WindowAction':
        """辞書から復元"""
        win_data = data['target_window']
        target_window = WindowInfo(
            title=win_data['title'],
            class_name=win_data['class_name'],
            process_name=win_data['process_name'],
            handle=win_data.get('handle')
        )
        
        new_position = None
        if 'new_position' in data:
            pos_data = data['new_position']
            new_position = Coordinate(x=pos_data['x'], y=pos_data['y'])
        
        new_size = None
        if 'new_size' in data:
            size_data = data['new_size']
            new_size = Coordinate(x=size_data['width'], y=size_data['height'])
        
        return cls(
            action_id=data['action_id'],
            sequence_number=data.get('sequence_number', 0),
            timestamp=datetime.fromisoformat(data['timestamp']),
            description=data.get('description', ''),
            delay_before=Duration(data.get('delay_before', 0)),
            delay_after=Duration(data.get('delay_after', 0)),
            timeout=Duration(data.get('timeout', 5000)),
            retry_count=data.get('retry_count', 1),
            continue_on_error=data.get('continue_on_error', False),
            screenshot_before=data.get('screenshot_before', False),
            screenshot_after=data.get('screenshot_after', False),
            metadata=data.get('metadata', {}),
            tags=data.get('tags', []),
            execution_count=data.get('execution_count', 0),
            target_window=target_window,
            new_position=new_position,
            new_size=new_size
        )


@dataclass
class WaitAction(ActionBase):
    """待機アクション"""
    
    wait_duration: Optional[Duration] = None
    wait_condition: Optional[str] = None  # 待機条件（将来拡張用）
    
    def __post_init__(self):
        if not self.wait_duration:
            raise ValueError("wait_durationが必要です")
            
        self.action_type = ActionType.WAIT
        super().__post_init__()
    
    def validate(self) -> ValidationResult:
        """待機アクションのバリデーション"""
        errors = []
        warnings = []
        
        if self.wait_duration.milliseconds <= 0:
            errors.append("待機時間は正の値である必要があります")
        
        if self.wait_duration.milliseconds > 60000:
            warnings.append("待機時間が1分を超えています")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'action_id': self.action_id,
            'action_type': self.action_type.value,
            'sequence_number': self.sequence_number,
            'timestamp': self.timestamp.isoformat(),
            'description': self.description,
            'delay_before': self.delay_before.milliseconds,
            'delay_after': self.delay_after.milliseconds,
            'timeout': self.timeout.milliseconds,
            'retry_count': self.retry_count,
            'continue_on_error': self.continue_on_error,
            'screenshot_before': self.screenshot_before,
            'screenshot_after': self.screenshot_after,
            'metadata': self.metadata,
            'tags': self.tags,
            'execution_count': self.execution_count,
            'wait_duration': self.wait_duration.milliseconds,
            'wait_condition': self.wait_condition
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WaitAction':
        """辞書から復元"""
        return cls(
            action_id=data['action_id'],
            sequence_number=data.get('sequence_number', 0),
            timestamp=datetime.fromisoformat(data['timestamp']),
            description=data.get('description', ''),
            delay_before=Duration(data.get('delay_before', 0)),
            delay_after=Duration(data.get('delay_after', 0)),
            timeout=Duration(data.get('timeout', 5000)),
            retry_count=data.get('retry_count', 1),
            continue_on_error=data.get('continue_on_error', False),
            screenshot_before=data.get('screenshot_before', False),
            screenshot_after=data.get('screenshot_after', False),
            metadata=data.get('metadata', {}),
            tags=data.get('tags', []),
            execution_count=data.get('execution_count', 0),
            wait_duration=Duration(data['wait_duration']),
            wait_condition=data.get('wait_condition')
        )


# アクションファクトリー
class ActionFactory:
    """アクション生成ファクトリー"""
    
    @staticmethod
    def create_key_press(key_input: KeyInput, description: str = "") -> KeyboardAction:
        """キー押下アクションを作成"""
        return KeyboardAction(
            key_input=key_input,
            description=description or f"キー押下: {key_input.to_string()}"
        )
    
    @staticmethod
    def create_text_input(text: str, description: str = "") -> KeyboardAction:
        """テキスト入力アクションを作成"""
        return KeyboardAction(
            text=text,
            description=description or f"テキスト入力: {text[:20]}{'...' if len(text) > 20 else ''}"
        )
    
    @staticmethod
    def create_mouse_click(position: Coordinate, button: MouseButton = MouseButton.LEFT, 
                          description: str = "") -> MouseAction:
        """マウスクリックアクションを作成"""
        mouse_input = MouseInput(button=button, position=position)
        return MouseAction(
            mouse_input=mouse_input,
            description=description or f"マウスクリック: ({position.x}, {position.y})"
        )
    
    @staticmethod
    def create_wait(duration: Duration, description: str = "") -> WaitAction:
        """待機アクションを作成"""
        return WaitAction(
            wait_duration=duration,
            description=description or f"待機: {duration.seconds}秒"
        )
    
    @staticmethod
    def create_window_activate(window_info: WindowInfo, description: str = "") -> WindowAction:
        """ウィンドウアクティブ化アクションを作成"""
        return WindowAction(
            target_window=window_info,
            description=description or f"ウィンドウアクティブ化: {window_info.title}"
        )


# 型エイリアス
ActionTypes = Union[KeyboardAction, MouseAction, WindowAction, WaitAction]