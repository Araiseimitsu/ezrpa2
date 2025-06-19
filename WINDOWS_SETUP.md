# EZRPA v2.0 - Windows環境セットアップガイド

## 🚀 クイックスタート

### 1. 基本動作確認
```cmd
# クイックテスト実行
python run_quick_test.py
```

### 2. 完全環境セットアップ
```cmd
# 自動環境セットアップ（推奨）
setup_environment.bat
```

### 3. アプリケーション起動
```cmd
# アプリケーション起動
run_ezrpa.bat

# または直接実行
python main.py
```

## 🔧 トラブルシューティング

### Python 3.13 関連エラー

**エラー**: `TypeError: Too few arguments for typing.Union`

**解決方法**: 
✅ **既に修正済み** - src/core/result.py の型注釈を Python 3.13 対応済み

### PySide6 インストールエラー

**エラー**: `pip install PySide6` が失敗する

**解決方法**:
```cmd
# 管理者権限でコマンドプロンプトを開き:
pip install --upgrade pip
pip install PySide6>=6.5.0
```

### 仮想環境の問題

**エラー**: `venv` が作成できない

**解決方法**:
```cmd
# Python仮想環境の手動作成
python -m venv venv
venv\Scripts\activate
pip install -r requirements\base.txt
```

### Windows API 関連エラー

**エラー**: `pywin32` のインストールやインポートエラー

**解決方法**:
```cmd
# pywin32の手動インストール
pip install pywin32>=306
python venv\Scripts\pywin32_postinstall.py -install
```

### 管理者権限が必要な機能

**症状**: キーボード・マウスの記録が動作しない

**解決方法**:
1. アプリケーションを管理者として実行
2. Windows Defenderの除外設定に追加
3. ウイルス対策ソフトの除外設定を確認

## 📋 システム要件確認

### 必須環境
- ✅ Windows 10 (Version 1903以降) または Windows 11
- ✅ Python 3.9-3.12 (Python 3.13対応済み)
- ✅ 4GB RAM以上
- ✅ 1GB 空き容量

### 推奨環境
- ✅ Windows 11 最新版
- ✅ Python 3.11 または 3.12
- ✅ 8GB RAM以上
- ✅ SSD ストレージ

## 🛠 開発者向け情報

### テスト実行
```cmd
# 単体テスト
pytest tests/unit/

# 統合テスト  
pytest tests/integration/

# カバレッジ付きテスト
pytest --cov=src --cov-report=html

# システム統合テスト
python test_system_integration.py
```

### ビルド・パッケージング
```cmd
# 実行可能ファイル作成
build_executable.bat

# パッケージインストール (開発用)
pip install -e .

# パッケージビルド
python -m build
```

### デバッグ情報収集
```cmd
# 診断情報出力
python -c "
import sys, platform, pkg_resources
print(f'Python: {sys.version}')
print(f'OS: {platform.platform()}')
try:
    import PySide6
    print(f'PySide6: {PySide6.__version__}')
except: print('PySide6: Not installed')
try:
    import win32api
    print('pywin32: Installed')
except: print('pywin32: Not installed')
"
```

## 📞 サポート

### よくある質問

**Q: アプリケーションが起動しない**
A: 
1. `run_quick_test.py` でシステム確認
2. 管理者権限で実行
3. ログファイル確認: `%APPDATA%\EZRPA\logs\ezrpa.log`

**Q: 記録機能が動作しない**
A:
1. 管理者権限での実行確認
2. ウイルス対策ソフトの除外設定
3. Windows UAC設定確認

**Q: 暗号化エラーが発生する**
A:
1. 設定ファイルの再作成: `del "%APPDATA%\EZRPA\config.json"`
2. アプリケーション再起動
3. パスワード再設定

### エラーログの場所
- **アプリケーションログ**: `%APPDATA%\EZRPA\logs\ezrpa.log`
- **設定ファイル**: `%APPDATA%\EZRPA\config.json`
- **Windowsイベントログ**: `eventvwr.msc` で確認

### 技術サポート
- **GitHub Issues**: https://github.com/ezrpa/ezrpa2/issues
- **ドキュメント**: `DEPLOYMENT.md`
- **アーキテクチャ**: `CLAUDE.md`

---

## 🎉 正常動作の確認

以下の手順ですべて成功すれば、EZRPA v2.0は正常に動作しています：

1. ✅ `python run_quick_test.py` が成功
2. ✅ `setup_environment.bat` が正常完了  
3. ✅ `run_ezrpa.bat` でアプリケーション起動
4. ✅ メインウィンドウが表示される
5. ✅ 基本機能（記録・再生）が動作する

**おめでとうございます！EZRPA v2.0のセットアップが完了しました。** 🎉