"""
PyAutoGUI Windows キー組み合わせテスト

このスクリプトはPyAutoGUIでWindows キー組み合わせが正常に動作するかテストします。
"""

import time
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.rpa_core import RPAManager

def test_key_combinations():
    """キー組み合わせテスト"""
    print("PyAutoGUI Windows キー組み合わせテスト開始")
    
    # RPAManagerを初期化
    rpa_manager = RPAManager()
    
    # 利用可能な機能をチェック
    status = rpa_manager.get_available_status()
    print(f"利用可能な機能: {status}")
    
    if not status.get("pyautogui_available", False):
        print("PyAutoGUIが利用できません。テストを終了します。")
        return False
    
    # テスト対象のキー組み合わせ
    test_cases = [
        {
            "name": "Win+R (ファイル名を指定して実行)",
            "modifiers": ["win"],
            "key": "r",
            "wait": 3
        },
        {
            "name": "Win+D (デスクトップ表示)",
            "modifiers": ["win"],
            "key": "d",
            "wait": 2
        },
        {
            "name": "Win+E (エクスプローラー)",
            "modifiers": ["win"],
            "key": "e",
            "wait": 2
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\n{i+1}. {test_case['name']} をテスト中...")
        print("3秒後に実行されます...")
        
        # 実行前に少し待機
        time.sleep(3)
        
        # キー組み合わせを実行
        success = rpa_manager.execute_key_combination(
            test_case["modifiers"], 
            test_case["key"]
        )
        
        if success:
            print(f"✓ {test_case['name']} 実行成功")
        else:
            print(f"✗ {test_case['name']} 実行失敗")
        
        # 次のテストまで待機
        if i < len(test_cases) - 1:
            print(f"{test_case['wait']}秒待機...")
            time.sleep(test_case["wait"])
    
    print("\nテスト完了")
    return True

if __name__ == "__main__":
    print("警告: このテストは実際にWindowsキーの組み合わせを実行します。")
    print("テスト中にデスクトップが表示されたり、プログラムが起動する可能性があります。")
    
    answer = input("続行しますか？ (y/N): ")
    if answer.lower() != 'y':
        print("テストをキャンセルしました。")
        sys.exit(0)
    
    test_key_combinations()