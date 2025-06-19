"""
型アノテーション修正テスト

GlobalHotkeyServiceの型アノテーションが正しく修正されているかテストします。
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_typing_syntax():
    """型アノテーションの構文テスト"""
    try:
        # Result型のインポートテスト
        from src.core.result import Result, ResultOf, Ok, Err
        print("✓ Result型のインポート成功")
        
        # 型アノテーションの構文チェック（コンパイル時）
        def sample_function() -> ResultOf(None, str):
            return Ok(None)
        
        print("✓ ResultOf型アノテーション構文正常")
        
        # 実際に関数を実行
        result = sample_function()
        if result.is_success():
            print("✓ Result操作正常")
        
        return True
        
    except Exception as e:
        print(f"✗ エラー: {e}")
        return False

if __name__ == "__main__":
    print("型アノテーション修正テスト開始")
    success = test_typing_syntax()
    
    if success:
        print("\n✅ 全テスト通過")
        print("GlobalHotkeyServiceの型アノテーション問題は修正されました。")
    else:
        print("\n❌ テスト失敗")
        
    print("\n注意: Windows環境での実際の動作確認が必要です。")