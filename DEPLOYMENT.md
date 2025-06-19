# EZRPA v2.0 - デプロイメントガイド

## 概要

EZRPA v2.0は、Clean Architectureパターンに基づいて設計されたWindows専用のRPAアプリケーションです。このドキュメントでは、アプリケーションのデプロイメント、インストール、設定について説明します。

## システム要件

### 最小要件
- **OS**: Windows 10 (Version 1903以降) または Windows 11
- **CPU**: Intel Core i3 2.0GHz または AMD Ryzen 3相当以上
- **メモリ**: 4GB RAM
- **ストレージ**: 1GB 空き容量
- **画面解像度**: 1024x768以上
- **ネットワーク**: インターネット接続（初期セットアップ時）

### 推奨要件
- **OS**: Windows 11 (最新バージョン)
- **CPU**: Intel Core i5 3.0GHz または AMD Ryzen 5相当以上
- **メモリ**: 8GB RAM以上
- **ストレージ**: 2GB 空き容量（SSD推奨）
- **画面解像度**: 1920x1080以上（高DPI対応）

### 必須ソフトウェア
- **Python**: 3.9以上 3.12以下 (開発版のみ)
- **Microsoft Visual C++ 再頒布可能パッケージ** (実行版のみ)

## インストール方法

### 方法1: 実行可能ファイル版（推奨）

1. **ダウンロード**
   ```
   EZRPA-v2.0-Setup.exe をダウンロード
   ```

2. **インストール実行**
   - `EZRPA-v2.0-Setup.exe` を管理者として実行
   - インストールウィザードの指示に従って進める
   - インストール先を選択（デフォルト: `C:\Program Files\EZRPA`）

3. **初回起動**
   - デスクトップまたはスタートメニューから「EZRPA v2.0」を起動
   - 初回起動時に自動的に設定ファイルが作成されます

### 方法2: 開発版（Python環境）

1. **Python環境の準備**
   ```cmd
   # Python 3.9-3.12のインストール確認
   python --version
   ```

2. **プロジェクトクローン**
   ```cmd
   git clone https://github.com/ezrpa/ezrpa2.git
   cd ezrpa2
   ```

3. **環境セットアップ**
   ```cmd
   # 環境セットアップスクリプトを実行
   setup_environment.bat
   ```

4. **アプリケーション起動**
   ```cmd
   # 起動スクリプトを実行
   run_ezrpa.bat
   ```

## 設定

### 設定ファイルの場所

- **ユーザー設定**: `%APPDATA%\EZRPA\config.json`
- **ログファイル**: `%APPDATA%\EZRPA\logs\ezrpa.log`
- **データファイル**: `%USERPROFILE%\Documents\EZRPA\recordings\`

### 主要設定項目

```json
{
  "app": {
    "name": "EZRPA",
    "version": "2.0.0",
    "debug": false,
    "language": "ja"
  },
  "ui": {
    "theme": "light",
    "window_width": 1200,
    "window_height": 800,
    "remember_position": true
  },
  "recording": {
    "auto_save": true,
    "capture_screenshots": true,
    "max_history": 100
  },
  "security": {
    "encrypt_recordings": true,
    "session_timeout": 3600
  },
  "logging": {
    "level": "INFO",
    "file_rotation": true,
    "max_file_size": "10MB",
    "backup_count": 5
  }
}
```

## セキュリティ設定

### データ暗号化

EZRPA v2.0では、記録データのセキュリティを保護するため、以下の暗号化機能を提供：

- **記録データ暗号化**: AES-256-CBC暗号化
- **パスワード保護**: PBKDF2による鍵導出
- **セッション管理**: 自動ログアウト機能

### 暗号化の有効化

```json
{
  "security": {
    "encrypt_recordings": true,
    "session_timeout": 3600,
    "require_password": true
  }
}
```

## 運用・保守

### ログ管理

- **ログレベル**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **ログローテーション**: 10MB毎に自動ローテーション
- **保存期間**: 5世代まで保存

### バックアップ

記録データの自動バックアップ機能：

```json
{
  "backup": {
    "enabled": true,
    "interval_hours": 24,
    "max_backups": 7,
    "backup_location": "%APPDATA%\\EZRPA\\backups"
  }
}
```

### パフォーマンス監視

- **メモリ使用量**: 通常時200MB以下
- **CPU使用率**: アイドル時5%以下
- **ディスク使用量**: 記録1時間あたり約1-5MB

## トラブルシューティング

### 一般的な問題

#### 1. アプリケーションが起動しない

**症状**: ダブルクリックしても何も起こらない

**解決方法**:
```cmd
# 1. 管理者権限で実行
# 2. Windows Defenderの除外設定を確認
# 3. イベントログを確認
eventvwr.msc
```

#### 2. 記録が正常に動作しない

**症状**: マウス・キーボード操作が記録されない

**解決方法**:
```cmd
# 1. 管理者権限での実行確認
# 2. ウイルス対策ソフトの除外設定
# 3. Windows UAC設定の確認
```

#### 3. 暗号化エラー

**症状**: "暗号化に失敗しました"エラー

**解決方法**:
```cmd
# 1. パスワードの再設定
# 2. 設定ファイルの再作成
del "%APPDATA%\EZRPA\config.json"
```

### ログ解析

重要なログメッセージ：

```
ERROR - ENCRYPTION_FAILED: パスワードの確認
WARNING - HIGH_MEMORY_USAGE: メモリ不足の可能性
INFO - SERVICE_INITIALIZED: 正常な起動
```

### サポート情報収集

問題報告時に含める情報：

```cmd
# システム情報収集スクリプト
echo "=== EZRPA v2.0 診断情報 ===" > diagnostic.txt
echo "日時: %date% %time%" >> diagnostic.txt
echo "OS: %OS%" >> diagnostic.txt
python --version >> diagnostic.txt 2>&1
echo "アプリケーションバージョン:" >> diagnostic.txt
type "%APPDATA%\EZRPA\config.json" >> diagnostic.txt 2>&1
echo "最新ログ（最後の50行）:" >> diagnostic.txt
powershell "Get-Content '%APPDATA%\EZRPA\logs\ezrpa.log' -Tail 50" >> diagnostic.txt 2>&1
```

## アップデート

### 自動アップデート（計画中）

現在のバージョンでは手動アップデートのみ対応。

### 手動アップデート

1. **バックアップ作成**
   ```cmd
   # 設定とデータのバックアップ
   xcopy "%APPDATA%\EZRPA" "backup_EZRPA" /E /I
   ```

2. **新バージョンのインストール**
   - 既存バージョンをアンインストール
   - 新バージョンをインストール

3. **設定の復元**
   - 必要に応じて設定ファイルを復元

## パフォーマンス最適化

### システム最適化

1. **Windows設定**
   ```cmd
   # 視覚効果を最適化
   SystemPropertiesPerformance.exe
   ```

2. **除外設定**
   - Windows Defender除外設定
   - ウイルス対策ソフト除外設定

3. **リソース監視**
   ```cmd
   # リソースモニターでEZRPAプロセスを監視
   resmon.exe
   ```

## セキュリティ考慮事項

### ネットワークセキュリティ

- EZRPA v2.0はローカルアプリケーションとして動作
- 外部通信は最小限（アップデート確認のみ）
- プライベートネットワーク環境での使用を推奨

### データプライバシー

- ユーザーデータはローカルに保存
- クラウド同期機能なし（データ漏洩リスク最小化）
- 暗号化による機密データ保護

## 技術サポート

### サポートチャンネル

- **GitHub Issues**: https://github.com/ezrpa/ezrpa2/issues
- **ドキュメント**: https://ezrpa.readthedocs.io/
- **メール**: support@ezrpa.dev

### サポート範囲

- **インストール支援**: ○
- **基本操作指導**: ○
- **トラブルシューティング**: ○
- **カスタム開発**: 別途相談

---

## 付録

### A. システム要件詳細

| 項目 | 最小要件 | 推奨要件 |
|------|----------|----------|
| CPU | 2.0GHz デュアルコア | 3.0GHz クアッドコア |
| RAM | 4GB | 8GB以上 |
| GPU | DirectX 11対応 | DirectX 12対応 |
| HDD | 1GB | 2GB (SSD) |

### B. 対応形式

| データ形式 | 拡張子 | 説明 |
|------------|--------|------|
| 記録ファイル | .ezrpa | EZRPA独自形式 |
| 設定ファイル | .json | JSON形式 |
| ログファイル | .log | プレーンテキスト |

### C. ライセンス情報

EZRPA v2.0は[MITライセンス](LICENSE)の下で配布されています。

---

*このドキュメントは EZRPA v2.0 向けに作成されています。*
*最終更新: 2025-06-18*