"""
ショートカットキー設定エンティティ

システムキーの除外設定とカスタムショートカットの管理を行います。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple
from enum import Enum


class KeyModifier(Enum):
    """キー修飾子"""
    CTRL = "ctrl"
    ALT = "alt"
    SHIFT = "shift"
    WIN = "win"


@dataclass
class KeyCombination:
    """キー組み合わせ定義"""
    modifiers: Set[KeyModifier] = field(default_factory=set)
    key: str = ""
    description: str = ""
    
    def __str__(self) -> str:
        """文字列表現"""
        if not self.modifiers and not self.key:
            return ""
        
        parts = []
        if KeyModifier.CTRL in self.modifiers:
            parts.append("Ctrl")
        if KeyModifier.ALT in self.modifiers:
            parts.append("Alt")
        if KeyModifier.SHIFT in self.modifiers:
            parts.append("Shift")
        if KeyModifier.WIN in self.modifiers:
            parts.append("Win")
        
        if self.key:
            parts.append(self.key)
        
        return "+".join(parts)
    
    def matches(self, modifiers: Set[KeyModifier], key: str) -> bool:
        """キー組み合わせが一致するかチェック"""
        return self.modifiers == modifiers and self.key.lower() == key.lower()


@dataclass
class ShortcutSettings:
    """ショートカットキー設定"""
    
    # システムキー除外設定
    exclude_system_keys: bool = True
    exclude_clipboard_keys: bool = True  # Ctrl+C/V/X
    exclude_window_keys: bool = True     # Alt+F4, Alt+Tab
    exclude_windows_keys: bool = True    # Win+キー組み合わせ
    exclude_app_keys: bool = True        # Ctrl+S/N/O など
    
    # デフォルトシステムキー定義
    default_system_keys: List[KeyCombination] = field(default_factory=lambda: [
        # クリップボード操作
        KeyCombination({KeyModifier.CTRL}, "c", "コピー"),
        KeyCombination({KeyModifier.CTRL}, "v", "ペースト"),
        KeyCombination({KeyModifier.CTRL}, "x", "カット"),
        KeyCombination({KeyModifier.CTRL}, "z", "元に戻す"),
        KeyCombination({KeyModifier.CTRL}, "y", "やり直し"),
        
        # ウィンドウ操作
        KeyCombination({KeyModifier.ALT}, "f4", "ウィンドウを閉じる"),
        KeyCombination({KeyModifier.ALT}, "tab", "アプリケーション切り替え"),
        KeyCombination({KeyModifier.ALT, KeyModifier.SHIFT}, "tab", "アプリケーション切り替え（逆順）"),
        
        # アプリケーション操作
        KeyCombination({KeyModifier.CTRL}, "s", "保存"),
        KeyCombination({KeyModifier.CTRL}, "n", "新規作成"),
        KeyCombination({KeyModifier.CTRL}, "o", "開く"),
        KeyCombination({KeyModifier.CTRL}, "w", "タブ/ウィンドウを閉じる"),
        KeyCombination({KeyModifier.CTRL}, "t", "新しいタブ"),
        KeyCombination({KeyModifier.CTRL}, "a", "すべて選択"),
        KeyCombination({KeyModifier.CTRL}, "f", "検索"),
        KeyCombination({KeyModifier.CTRL}, "h", "置換"),
        KeyCombination({KeyModifier.CTRL}, "p", "印刷"),
        
        # システム機能
        KeyCombination({KeyModifier.CTRL, KeyModifier.ALT}, "delete", "セキュリティオプション"),
        KeyCombination({KeyModifier.CTRL, KeyModifier.SHIFT}, "esc", "タスクマネージャー"),
        
        # ファンクションキー
        KeyCombination(set(), "f1", "ヘルプ"),
        KeyCombination(set(), "f5", "更新"),
        KeyCombination(set(), "f11", "フルスクリーン"),
        KeyCombination(set(), "f12", "開発者ツール"),
    ])
    
    # Windowsキー組み合わせ
    windows_key_combinations: List[KeyCombination] = field(default_factory=lambda: [
        KeyCombination({KeyModifier.WIN}, "d", "デスクトップ表示"),
        KeyCombination({KeyModifier.WIN}, "e", "エクスプローラー"),
        KeyCombination({KeyModifier.WIN}, "r", "ファイル名を指定して実行"),
        KeyCombination({KeyModifier.WIN}, "l", "ロック画面"),
        KeyCombination({KeyModifier.WIN}, "m", "すべてのウィンドウを最小化"),
        KeyCombination({KeyModifier.WIN}, "tab", "タスクビュー"),
        KeyCombination({KeyModifier.WIN}, "i", "設定"),
        KeyCombination({KeyModifier.WIN}, "s", "検索"),
        KeyCombination({KeyModifier.WIN}, "x", "クイックアクセスメニュー"),
    ])
    
    # カスタム除外キー
    custom_excluded_keys: List[KeyCombination] = field(default_factory=list)
    
    # RPA制御ホットキー
    recording_start_stop_key: KeyCombination = field(
        default_factory=lambda: KeyCombination({KeyModifier.CTRL, KeyModifier.SHIFT}, "r", "記録開始/停止")
    )
    recording_pause_resume_key: KeyCombination = field(
        default_factory=lambda: KeyCombination({KeyModifier.CTRL, KeyModifier.SHIFT}, "p", "記録一時停止/再開")
    )
    emergency_stop_key: KeyCombination = field(
        default_factory=lambda: KeyCombination({KeyModifier.CTRL, KeyModifier.SHIFT}, "q", "緊急停止")
    )
    
    def get_all_excluded_keys(self) -> List[KeyCombination]:
        """除外対象のすべてのキー組み合わせを取得"""
        excluded = []
        
        if self.exclude_system_keys:
            if self.exclude_clipboard_keys:
                excluded.extend([k for k in self.default_system_keys 
                               if any(mod == KeyModifier.CTRL for mod in k.modifiers) 
                               and k.key in ['c', 'v', 'x', 'z', 'y']])
            
            if self.exclude_window_keys:
                excluded.extend([k for k in self.default_system_keys 
                               if any(mod == KeyModifier.ALT for mod in k.modifiers)])
            
            if self.exclude_app_keys:
                excluded.extend([k for k in self.default_system_keys 
                               if any(mod == KeyModifier.CTRL for mod in k.modifiers) 
                               and k.key in ['s', 'n', 'o', 'w', 't', 'a', 'f', 'h', 'p']])
            
            if self.exclude_windows_keys:
                excluded.extend(self.windows_key_combinations)
        
        # カスタム除外キーを追加
        excluded.extend(self.custom_excluded_keys)
        
        return excluded
    
    def should_exclude_key(self, modifiers: Set[KeyModifier], key: str) -> bool:
        """指定されたキー組み合わせが除外対象かチェック"""
        excluded_keys = self.get_all_excluded_keys()
        
        for excluded_key in excluded_keys:
            if excluded_key.matches(modifiers, key):
                return True
        
        return False
    
    def is_rpa_control_key(self, modifiers: Set[KeyModifier], key: str) -> Tuple[bool, str]:
        """RPA制御キーかどうかをチェック"""
        if self.recording_start_stop_key.matches(modifiers, key):
            return True, "start_stop"
        elif self.recording_pause_resume_key.matches(modifiers, key):
            return True, "pause_resume"
        elif self.emergency_stop_key.matches(modifiers, key):
            return True, "emergency_stop"
        
        return False, ""
    
    def add_custom_excluded_key(self, key_combination: KeyCombination) -> bool:
        """カスタム除外キーを追加"""
        # 重複チェック
        for existing_key in self.custom_excluded_keys:
            if existing_key.modifiers == key_combination.modifiers and existing_key.key == key_combination.key:
                return False
        
        self.custom_excluded_keys.append(key_combination)
        return True
    
    def remove_custom_excluded_key(self, index: int) -> bool:
        """カスタム除外キーを削除"""
        if 0 <= index < len(self.custom_excluded_keys):
            del self.custom_excluded_keys[index]
            return True
        return False
    
    def to_dict(self) -> Dict:
        """辞書形式に変換（設定保存用）"""
        return {
            "exclude_system_keys": self.exclude_system_keys,
            "exclude_clipboard_keys": self.exclude_clipboard_keys,
            "exclude_window_keys": self.exclude_window_keys,
            "exclude_windows_keys": self.exclude_windows_keys,
            "exclude_app_keys": self.exclude_app_keys,
            "custom_excluded_keys": [
                {
                    "modifiers": [mod.value for mod in key.modifiers],
                    "key": key.key,
                    "description": key.description
                }
                for key in self.custom_excluded_keys
            ],
            "recording_start_stop_key": {
                "modifiers": [mod.value for mod in self.recording_start_stop_key.modifiers],
                "key": self.recording_start_stop_key.key,
                "description": self.recording_start_stop_key.description
            },
            "recording_pause_resume_key": {
                "modifiers": [mod.value for mod in self.recording_pause_resume_key.modifiers],
                "key": self.recording_pause_resume_key.key,
                "description": self.recording_pause_resume_key.description
            },
            "emergency_stop_key": {
                "modifiers": [mod.value for mod in self.emergency_stop_key.modifiers],
                "key": self.emergency_stop_key.key,
                "description": self.emergency_stop_key.description
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ShortcutSettings":
        """辞書から設定を復元"""
        settings = cls()
        
        settings.exclude_system_keys = data.get("exclude_system_keys", True)
        settings.exclude_clipboard_keys = data.get("exclude_clipboard_keys", True)
        settings.exclude_window_keys = data.get("exclude_window_keys", True)
        settings.exclude_windows_keys = data.get("exclude_windows_keys", True)
        settings.exclude_app_keys = data.get("exclude_app_keys", True)
        
        # カスタム除外キーの復元
        custom_keys_data = data.get("custom_excluded_keys", [])
        settings.custom_excluded_keys = []
        for key_data in custom_keys_data:
            modifiers = {KeyModifier(mod) for mod in key_data.get("modifiers", [])}
            settings.custom_excluded_keys.append(KeyCombination(
                modifiers=modifiers,
                key=key_data.get("key", ""),
                description=key_data.get("description", "")
            ))
        
        # RPA制御キーの復元
        def restore_key_combination(key_data, default_key):
            if key_data:
                modifiers = {KeyModifier(mod) for mod in key_data.get("modifiers", [])}
                return KeyCombination(
                    modifiers=modifiers,
                    key=key_data.get("key", ""),
                    description=key_data.get("description", "")
                )
            return default_key
        
        settings.recording_start_stop_key = restore_key_combination(
            data.get("recording_start_stop_key"), settings.recording_start_stop_key
        )
        settings.recording_pause_resume_key = restore_key_combination(
            data.get("recording_pause_resume_key"), settings.recording_pause_resume_key
        )
        settings.emergency_stop_key = restore_key_combination(
            data.get("emergency_stop_key"), settings.emergency_stop_key
        )
        
        return settings