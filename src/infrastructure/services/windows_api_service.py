"""
Windows API サービス - Windows システムAPIとの統合

Windows固有のシステムレベル操作を提供するサービスです。
キーボード・マウス・ウィンドウ操作、プロセス管理等を行います。
"""

import ctypes
import ctypes.wintypes
import threading
import time
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

from ...core.result import Result, Ok, Err, ErrorInfo
from ...core.event_bus import IEventBus
from ...shared.constants import WindowsKeys, WindowsMessages, ApplicationConstants


# Windows API 構造体定義
class POINT(ctypes.Structure):
    """Windows POINT 構造体"""

    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class RECT(ctypes.Structure):
    """Windows RECT 構造体"""

    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class INPUT(ctypes.Structure):
    """Windows INPUT 構造体"""

    _fields_ = [
        ("type", ctypes.wintypes.DWORD),
        (
            "union",
            ctypes.c_char * 24,
        ),  # KEYBDINPUT, MOUSEINPUT, HARDWAREINPUTの最大サイズ
    ]


@dataclass
class WindowInformation:
    """ウィンドウ情報"""

    handle: int
    title: str
    class_name: str
    process_id: int
    process_name: str
    rect: Tuple[int, int, int, int]  # left, top, right, bottom
    is_visible: bool
    is_minimized: bool
    is_maximized: bool


@dataclass
class SystemInfo:
    """システム情報"""

    screen_width: int
    screen_height: int
    dpi_x: int
    dpi_y: int
    scale_factor: float


class WindowsApiService:
    """Windows API サービス実装"""

    def __init__(self, event_bus: Optional[IEventBus] = None):
        self._event_bus = event_bus
        self._lock = threading.RLock()

        # Windows API 関数の取得
        self._user32 = ctypes.windll.user32
        self._kernel32 = ctypes.windll.kernel32
        self._gdi32 = ctypes.windll.gdi32

        # システム情報の初期化
        self._system_info = self._get_system_info()

        # IME状態管理
        self._ime_enabled = False

    def _get_system_info(self) -> SystemInfo:
        """システム情報を取得"""
        try:
            # スクリーンサイズ
            screen_width = self._user32.GetSystemMetrics(0)  # SM_CXSCREEN
            screen_height = self._user32.GetSystemMetrics(1)  # SM_CYSCREEN

            # DPI情報
            hdc = self._user32.GetDC(0)
            dpi_x = self._gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
            dpi_y = self._gdi32.GetDeviceCaps(hdc, 90)  # LOGPIXELSY
            self._user32.ReleaseDC(0, hdc)

            scale_factor = dpi_x / ApplicationConstants.DEFAULT_DPI

            return SystemInfo(
                screen_width=screen_width,
                screen_height=screen_height,
                dpi_x=dpi_x,
                dpi_y=dpi_y,
                scale_factor=scale_factor,
            )
        except Exception as e:
            # フォールバック値
            return SystemInfo(
                screen_width=1920,
                screen_height=1080,
                dpi_x=96,
                dpi_y=96,
                scale_factor=1.0,
            )

    def get_system_info(self) -> SystemInfo:
        """システム情報を取得"""
        return self._system_info

    def send_key_input(
        self,
        key_code: int,
        shift: bool = False,
        ctrl: bool = False,
        alt: bool = False,
        win: bool = False,
    ) -> Result[None, str]:
        """キー入力を送信"""
        try:
            with self._lock:
                # 修飾キーの押下
                if shift:
                    self._send_key_down(WindowsKeys.VK_SHIFT)
                if ctrl:
                    self._send_key_down(WindowsKeys.VK_CONTROL)
                if alt:
                    self._send_key_down(WindowsKeys.VK_MENU)
                if win:
                    self._send_key_down(WindowsKeys.VK_LWIN)

                # メインキーの押下・離上
                self._send_key_down(key_code)
                time.sleep(0.01)  # 短い待機
                self._send_key_up(key_code)

                # 修飾キーの離上（逆順）
                if win:
                    self._send_key_up(WindowsKeys.VK_LWIN)
                if alt:
                    self._send_key_up(WindowsKeys.VK_MENU)
                if ctrl:
                    self._send_key_up(WindowsKeys.VK_CONTROL)
                if shift:
                    self._send_key_up(WindowsKeys.VK_SHIFT)

                return Ok(None)

        except Exception as e:
            return Err(f"キー入力送信エラー: {str(e)}")

    def send_text_input(self, text: str, use_ime: bool = True) -> Result[None, str]:
        """テキスト入力を送信"""
        try:
            with self._lock:
                if use_ime and self._contains_japanese_chars(text):
                    # IME使用でのテキスト入力
                    return self._send_text_with_ime(text)
                else:
                    # 直接Unicode文字送信
                    return self._send_text_unicode(text)

        except Exception as e:
            return Err(f"テキスト入力エラー: {str(e)}")

    def send_mouse_input(
        self,
        x: int,
        y: int,
        button: int = 1,
        double_click: bool = False,
        wheel_delta: int = 0,
    ) -> Result[None, str]:
        """マウス入力を送信"""
        try:
            with self._lock:
                # DPIスケーリング調整
                scaled_x = int(x * self._system_info.scale_factor)
                scaled_y = int(y * self._system_info.scale_factor)

                # マウス移動
                self._set_cursor_pos(scaled_x, scaled_y)
                time.sleep(0.01)

                if wheel_delta != 0:
                    # ホイール操作
                    self._send_mouse_wheel(wheel_delta)
                else:
                    # クリック操作
                    if double_click:
                        self._send_mouse_click(button)
                        time.sleep(0.05)
                        self._send_mouse_click(button)
                    else:
                        self._send_mouse_click(button)

                return Ok(None)

        except Exception as e:
            return Err(f"マウス入力エラー: {str(e)}")

    def find_window(
        self,
        title: Optional[str] = None,
        class_name: Optional[str] = None,
        process_name: Optional[str] = None,
    ) -> Result[WindowInformation, str]:
        """ウィンドウを検索"""
        try:
            windows = self.enumerate_windows()

            for window in windows:
                match = True

                if title and title not in window.title:
                    match = False
                if class_name and class_name != window.class_name:
                    match = False
                if process_name and process_name not in window.process_name:
                    match = False

                if match:
                    return Ok(window)

            return Err("指定された条件のウィンドウが見つかりませんでした")

        except Exception as e:
            return Err(f"ウィンドウ検索エラー: {str(e)}")

    def enumerate_windows(self) -> List[WindowInformation]:
        """すべてのウィンドウを列挙"""
        windows = []

        def enum_proc(hwnd, lParam):
            if self._user32.IsWindow(hwnd) and self._user32.IsWindowVisible(hwnd):
                try:
                    # ウィンドウタイトル取得
                    title_length = self._user32.GetWindowTextLengthW(hwnd)
                    if title_length > 0:
                        title_buffer = ctypes.create_unicode_buffer(title_length + 1)
                        self._user32.GetWindowTextW(
                            hwnd, title_buffer, title_length + 1
                        )
                        title = title_buffer.value
                    else:
                        title = ""

                    # クラス名取得
                    class_buffer = ctypes.create_unicode_buffer(256)
                    self._user32.GetClassNameW(hwnd, class_buffer, 256)
                    class_name = class_buffer.value

                    # プロセス情報取得
                    process_id = ctypes.wintypes.DWORD()
                    self._user32.GetWindowThreadProcessId(
                        hwnd, ctypes.byref(process_id)
                    )

                    # ウィンドウ矩形取得
                    rect = RECT()
                    self._user32.GetWindowRect(hwnd, ctypes.byref(rect))

                    # ウィンドウ状態
                    placement = ctypes.wintypes.WINDOWPLACEMENT()
                    placement.length = ctypes.sizeof(placement)
                    self._user32.GetWindowPlacement(hwnd, ctypes.byref(placement))

                    window_info = WindowInformation(
                        handle=hwnd,
                        title=title,
                        class_name=class_name,
                        process_id=process_id.value,
                        process_name="",  # プロセス名は別途取得が必要
                        rect=(rect.left, rect.top, rect.right, rect.bottom),
                        is_visible=self._user32.IsWindowVisible(hwnd),
                        is_minimized=placement.showCmd == 2,  # SW_SHOWMINIMIZED
                        is_maximized=placement.showCmd == 3,  # SW_SHOWMAXIMIZED
                    )

                    windows.append(window_info)

                except Exception:
                    pass  # エラーは無視してスキップ

            return True

        try:
            EnumWindowsProc = ctypes.WINFUNCTYPE(
                ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
            )
            self._user32.EnumWindows(EnumWindowsProc(enum_proc), 0)
        except Exception:
            pass

        return windows

    def activate_window(self, handle: int) -> Result[None, str]:
        """ウィンドウをアクティブ化"""
        try:
            if not self._user32.IsWindow(handle):
                return Err("無効なウィンドウハンドルです")

            # ウィンドウを前面に表示
            self._user32.SetForegroundWindow(handle)
            self._user32.ShowWindow(handle, 9)  # SW_RESTORE

            return Ok(None)

        except Exception as e:
            return Err(f"ウィンドウアクティブ化エラー: {str(e)}")

    def minimize_all_windows(self) -> Result[None, str]:
        """すべてのウィンドウを最小化"""
        try:
            # 方法1: Shell.Application COM オブジェクトを使用（最も確実）
            try:
                import subprocess

                result = subprocess.run(
                    [
                        "powershell",
                        "-WindowStyle",
                        "Hidden",
                        "-Command",
                        "(New-Object -comObject Shell.Application).minimizeall()",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    return Ok(None)

            except Exception:
                pass  # 次の方法を試行

            # 方法2: Windows + D キーを送信
            try:
                # Windows キーを押下
                self._send_key_down(WindowsKeys.VK_LWIN)
                time.sleep(0.01)

                # D キーを押下・離上
                self._send_key_down(ord("D"))
                time.sleep(0.01)
                self._send_key_up(ord("D"))

                # Windows キーを離上
                time.sleep(0.01)
                self._send_key_up(WindowsKeys.VK_LWIN)

                return Ok(None)

            except Exception:
                pass  # 次の方法を試行

            # 方法3: pywin32を使用（利用可能な場合）
            try:
                import win32api
                import win32con

                # Windows + D を送信してデスクトップを表示
                win32api.keybd_event(win32con.VK_LWIN, 0, 0, 0)
                win32api.keybd_event(ord("D"), 0, 0, 0)
                win32api.keybd_event(ord("D"), 0, win32con.KEYEVENTF_KEYUP, 0)
                win32api.keybd_event(win32con.VK_LWIN, 0, win32con.KEYEVENTF_KEYUP, 0)

                return Ok(None)

            except ImportError:
                pass  # pywin32が利用できない
            except Exception:
                pass

            # 方法4: 手動でウィンドウを列挙して最小化
            try:
                windows = self.enumerate_windows()
                minimized_count = 0

                for window in windows:
                    # 表示されているウィンドウのみ対象
                    if (
                        window.is_visible
                        and not window.is_minimized
                        and window.title.strip()
                        and window.handle != self._get_current_window_handle()
                    ):

                        # ウィンドウを最小化
                        if self._user32.ShowWindow(window.handle, 6):  # SW_MINIMIZE
                            minimized_count += 1

                if minimized_count > 0:
                    return Ok(None)

            except Exception:
                pass

            return Err("すべてのウィンドウ最小化方法が失敗しました")

        except Exception as e:
            return Err(f"ウィンドウ最小化エラー: {str(e)}")

    def minimize_window(self, handle: int) -> Result[None, str]:
        """指定されたウィンドウを最小化"""
        try:
            if not self._user32.IsWindow(handle):
                return Err("無効なウィンドウハンドルです")

            # ウィンドウを最小化
            if self._user32.ShowWindow(handle, 6):  # SW_MINIMIZE
                return Ok(None)
            else:
                return Err("ウィンドウの最小化に失敗しました")

        except Exception as e:
            return Err(f"ウィンドウ最小化エラー: {str(e)}")

    def restore_window(self, handle: int) -> Result[None, str]:
        """指定されたウィンドウを復元"""
        try:
            if not self._user32.IsWindow(handle):
                return Err("無効なウィンドウハンドルです")

            # ウィンドウを復元
            if self._user32.ShowWindow(handle, 9):  # SW_RESTORE
                return Ok(None)
            else:
                return Err("ウィンドウの復元に失敗しました")

        except Exception as e:
            return Err(f"ウィンドウ復元エラー: {str(e)}")

    def _get_current_window_handle(self) -> int:
        """現在のアクティブウィンドウハンドルを取得"""
        try:
            return self._user32.GetForegroundWindow()
        except Exception:
            return 0

    def move_window(
        self,
        handle: int,
        x: int,
        y: int,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> Result[None, str]:
        """ウィンドウを移動・リサイズ"""
        try:
            if not self._user32.IsWindow(handle):
                return Err("無効なウィンドウハンドルです")

            if width is None or height is None:
                # 現在のサイズを取得
                rect = RECT()
                self._user32.GetWindowRect(handle, ctypes.byref(rect))
                if width is None:
                    width = rect.right - rect.left
                if height is None:
                    height = rect.bottom - rect.top

            # DPIスケーリング調整
            scaled_x = int(x * self._system_info.scale_factor)
            scaled_y = int(y * self._system_info.scale_factor)
            scaled_width = int(width * self._system_info.scale_factor)
            scaled_height = int(height * self._system_info.scale_factor)

            success = self._user32.MoveWindow(
                handle, scaled_x, scaled_y, scaled_width, scaled_height, True
            )

            if success:
                return Ok(None)
            else:
                return Err("ウィンドウの移動に失敗しました")

        except Exception as e:
            return Err(f"ウィンドウ移動エラー: {str(e)}")

    def get_cursor_position(self) -> Result[Tuple[int, int], str]:
        """現在のカーソル位置を取得"""
        try:
            point = POINT()
            if self._user32.GetCursorPos(ctypes.byref(point)):
                # DPIスケーリング逆調整
                x = int(point.x / self._system_info.scale_factor)
                y = int(point.y / self._system_info.scale_factor)
                return Ok((x, y))
            else:
                return Err("カーソル位置の取得に失敗しました")

        except Exception as e:
            return Err(f"カーソル位置取得エラー: {str(e)}")

    def is_ime_enabled(self) -> bool:
        """IMEが有効かどうかを判定"""
        try:
            # フォーカスされたウィンドウのIME状態をチェック
            hwnd = self._user32.GetForegroundWindow()
            if hwnd:
                # IMEコンテキストの確認（簡易版）
                return self._ime_enabled
            return False
        except Exception:
            return False

    def toggle_ime(self, enable: bool) -> Result[None, str]:
        """IMEの有効/無効を切り替え"""
        try:
            if enable != self._ime_enabled:
                # Alt + 漢字キーでIME切り替え
                result = self.send_key_input(WindowsKeys.VK_KANJI, alt=True)
                if result.is_success():
                    self._ime_enabled = enable
                    return Ok(None)
                else:
                    return result
            return Ok(None)

        except Exception as e:
            return Err(f"IME切り替えエラー: {str(e)}")

    # プライベートメソッド
    def _send_key_down(self, key_code: int):
        """キー押下"""
        self._user32.keybd_event(key_code, 0, 0, 0)

    def _send_key_up(self, key_code: int):
        """キー離上"""
        self._user32.keybd_event(key_code, 0, 2, 0)  # KEYEVENTF_KEYUP

    def _send_text_unicode(self, text: str) -> Result[None, str]:
        """Unicode文字の直接送信"""
        try:
            for char in text:
                char_code = ord(char)
                # WM_CHARメッセージでUnicode文字を送信
                hwnd = self._user32.GetForegroundWindow()
                if hwnd:
                    self._user32.PostMessageW(
                        hwnd, WindowsMessages.WM_CHAR, char_code, 0
                    )
                time.sleep(0.001)  # 短い間隔
            return Ok(None)
        except Exception as e:
            return Err(f"Unicode文字送信エラー: {str(e)}")

    def _send_text_with_ime(self, text: str) -> Result[None, str]:
        """IME経由でのテキスト送信"""
        try:
            # IMEが無効な場合は有効化
            if not self._ime_enabled:
                ime_result = self.toggle_ime(True)
                if ime_result.is_failure():
                    return ime_result
                time.sleep(0.1)  # IME起動待機

            # クリップボード経由でのテキスト送信（確実性を重視）
            return self._send_text_via_clipboard(text)

        except Exception as e:
            return Err(f"IMEテキスト送信エラー: {str(e)}")

    def _send_text_via_clipboard(self, text: str) -> Result[None, str]:
        """クリップボード経由でテキスト送信"""
        try:
            import subprocess

            # PowerShellを使用してクリップボードに設定
            ps_command = f'Set-Clipboard "{text}"'
            subprocess.run(
                ["powershell", "-Command", ps_command], check=True, capture_output=True
            )

            time.sleep(0.05)

            # Ctrl+Vで貼り付け
            return self.send_key_input(ord("V"), ctrl=True)

        except Exception as e:
            return Err(f"クリップボード経由送信エラー: {str(e)}")

    def _set_cursor_pos(self, x: int, y: int):
        """カーソル位置設定"""
        self._user32.SetCursorPos(x, y)

    def _send_mouse_click(self, button: int):
        """マウスクリック送信"""
        if button == 1:  # 左クリック
            self._user32.mouse_event(0x0002, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
            time.sleep(0.01)
            self._user32.mouse_event(0x0004, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP
        elif button == 2:  # 右クリック
            self._user32.mouse_event(0x0008, 0, 0, 0, 0)  # MOUSEEVENTF_RIGHTDOWN
            time.sleep(0.01)
            self._user32.mouse_event(0x0010, 0, 0, 0, 0)  # MOUSEEVENTF_RIGHTUP
        elif button == 3:  # 中央クリック
            self._user32.mouse_event(0x0020, 0, 0, 0, 0)  # MOUSEEVENTF_MIDDLEDOWN
            time.sleep(0.01)
            self._user32.mouse_event(0x0040, 0, 0, 0, 0)  # MOUSEEVENTF_MIDDLEUP

    def _send_mouse_wheel(self, delta: int):
        """マウスホイール送信"""
        self._user32.mouse_event(0x0800, 0, 0, delta * 120, 0)  # MOUSEEVENTF_WHEEL

    def _contains_japanese_chars(self, text: str) -> bool:
        """日本語文字が含まれているかチェック"""
        for char in text:
            code_point = ord(char)
            # ひらがな、カタカナ、漢字の範囲をチェック
            if (
                0x3040 <= code_point <= 0x309F  # ひらがな
                or 0x30A0 <= code_point <= 0x30FF  # カタカナ
                or 0x4E00 <= code_point <= 0x9FAF
            ):  # 漢字
                return True
        return False
