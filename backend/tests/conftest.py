"""pytest conftest — テスト用の共通フィクスチャ"""

import sys
import os

# backend ディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
