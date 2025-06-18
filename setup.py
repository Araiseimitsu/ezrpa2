"""
EZRPA v2.0 - Setup Configuration

Clean Architecture RPA Application for Windows
パッケージングとインストール設定
"""

import os
import sys
from pathlib import Path
from setuptools import setup, find_packages

# Windows環境チェック
if sys.platform != "win32":
    print("WARNING: This application is designed specifically for Windows environments.")

# プロジェクトルート取得
project_root = Path(__file__).parent

# バージョン情報を動的に読み込み
def get_version():
    """バージョン情報を取得"""
    version_file = project_root / "src" / "shared" / "constants.py"
    if version_file.exists():
        # constants.pyからバージョンを読み取り
        with open(version_file, 'r', encoding='utf-8') as f:
            content = f.read()
            for line in content.split('\n'):
                if 'VERSION = ' in line and '"' in line:
                    return line.split('"')[1]
    return "2.0.0"  # フォールバック

# READMEを読み込み
def get_long_description():
    """長い説明文を取得"""
    readme_file = project_root / "README.md"
    if readme_file.exists():
        with open(readme_file, 'r', encoding='utf-8') as f:
            return f.read()
    return "EZRPA v2.0 - Clean Architecture RPA Application for Windows"

# requirements.txtから依存関係を読み込み
def get_requirements(filename):
    """requirements.txtから依存関係を読み込み"""
    req_file = project_root / "requirements" / filename
    if req_file.exists():
        with open(req_file, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []

# パッケージデータを定義
def get_package_data():
    """パッケージデータを収集"""
    package_data = {}
    
    # 設定ファイル
    config_files = []
    for ext in ['.json', '.ini', '.yaml', '.yml']:
        config_files.extend([f"*{ext}"])
    
    # UIファイル
    ui_files = ['*.ui', '*.qrc', '*.qss']
    
    # アイコンと画像
    image_files = ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.ico', '*.svg']
    
    # ドキュメント
    doc_files = ['*.md', '*.txt', '*.rst']
    
    # スキーマファイル
    schema_files = ['*.sql', '*.json']
    
    package_data = {
        'src': config_files + doc_files,
        'src.presentation.gui': ui_files + image_files,
        'src.presentation.gui.views': ui_files,
        'src.presentation.gui.components': ui_files + image_files,
        'src.infrastructure': schema_files,
        'src.shared': config_files,
    }
    
    return package_data

# エントリーポイントを定義
def get_entry_points():
    """エントリーポイントを定義"""
    return {
        'console_scripts': [
            'ezrpa=main:main',
            'ezrpa-cli=src.presentation.cli:main',
        ],
        'gui_scripts': [
            'ezrpa-gui=main:main',
        ],
    }

# プラットフォーム固有の設定
def get_platform_specific_requirements():
    """プラットフォーム固有の要件を取得"""
    requirements = []
    
    if sys.platform == "win32":
        requirements.extend([
            'pywin32>=306',
            'pywin32-ctypes>=0.2.0',
            'wmi>=1.5.1',
        ])
    
    return requirements

# セットアップ実行
def main():
    """セットアップメイン関数"""
    
    # 基本依存関係
    install_requires = get_requirements("base.txt")
    
    # プラットフォーム固有の依存関係を追加
    install_requires.extend(get_platform_specific_requirements())
    
    # オプション依存関係
    extras_require = {
        'dev': get_requirements("development.txt"),
        'test': get_requirements("test.txt"),
        'build': [
            'setuptools>=68.0.0',
            'wheel>=0.41.0',
            'build>=0.10.0',
            'pyinstaller>=5.13.0',
        ],
        'docs': [
            'sphinx>=7.1.0',
            'sphinx-rtd-theme>=1.3.0',
            'myst-parser>=2.0.0',
        ]
    }
    
    setup(
        name="ezrpa",
        version=get_version(),
        description="Clean Architecture RPA Application for Windows",
        long_description=get_long_description(),
        long_description_content_type="text/markdown",
        author="EZRPA Development Team",
        author_email="support@ezrpa.dev",
        url="https://github.com/ezrpa/ezrpa2",
        project_urls={
            "Bug Reports": "https://github.com/ezrpa/ezrpa2/issues",
            "Source": "https://github.com/ezrpa/ezrpa2",
            "Documentation": "https://ezrpa.readthedocs.io/",
        },
        packages=find_packages(include=['src*']),
        package_data=get_package_data(),
        include_package_data=True,
        install_requires=install_requires,
        extras_require=extras_require,
        entry_points=get_entry_points(),
        python_requires=">=3.9",
        platforms=["win32"],
        classifiers=[
            "Development Status :: 4 - Beta",
            "Intended Audience :: End Users/Desktop",
            "License :: OSI Approved :: MIT License",
            "Operating System :: Microsoft :: Windows",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
            "Programming Language :: Python :: 3.12",
            "Topic :: Office/Business :: Office Suites",
            "Topic :: Software Development :: Libraries :: Application Frameworks",
            "Environment :: Win32 (MS Windows)",
            "Natural Language :: Japanese",
        ],
        keywords="rpa automation windows clean-architecture mvvm desktop",
        zip_safe=False,
        
        # Windows固有の設定
        options={
            'build_scripts': {
                'executable': sys.executable,
            },
        },
    )

if __name__ == "__main__":
    main()