# -*- coding: utf-8 -*-
"""向量库引导脚本。
  python build_index.py           → 增量索引（幂等，跳过已索引文件）
  python build_index.py --rebuild → 删库重建（老 schema → 新 schema 迁移）
"""
import os
import shutil
import sys
from pathlib import Path

from deep_research.config import PROJECT_ROOT, VECTOR_STORE_DIR
from deep_research.knowledge_base import index_document, get_document_count

HISTORY_DIR = PROJECT_ROOT / "history-database"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def rebuild_all():
    """删除向量库，重建所有历史文件。"""
    if VECTOR_STORE_DIR.exists():
        shutil.rmtree(VECTOR_STORE_DIR)
        print(f"已删除: {VECTOR_STORE_DIR}")

    count = 0
    for category_dir in sorted(HISTORY_DIR.iterdir()):
        if not category_dir.is_dir() or category_dir.name.startswith("."):
            continue
        for fn in sorted(category_dir.iterdir()):
            if not fn.suffix == ".txt":
                continue
            path = str(fn)
            date_str = fn.stem[:10] if len(fn.stem) >= 10 else "unknown"
            topic = fn.stem[11:] if len(fn.stem) > 11 else fn.stem
            try:
                n = index_document(path, category=category_dir.name, topic=topic, date_str=date_str)
                print(f"  [{n} chunk(s)] {category_dir.name} / {topic}")
                count += 1
            except Exception as e:
                print(f"  失败: {fn} → {e}")
    print(f"重建完成: {count} 个文件, {get_document_count()} chunk(s)")


def incremental():
    """增量索引，幂等。"""
    files = list(HISTORY_DIR.rglob("*.txt"))
    if not files:
        print("history-database/ 下没有 txt 文件，无需建库。")
        return
    print(f"发现 {len(files)} 个历史研究文件...")
    for i, f in enumerate(files, 1):
        try:
            n = index_document(str(f))
            print(f"  [{i}/{len(files)}] [{n} chunk(s)] {f.parent.name} / {f.stem}")
        except Exception as e:
            print(f"  [{i}/{len(files)}] 失败: {f} → {e}")
    print(f"完成: {get_document_count()} chunk(s)")


if __name__ == "__main__":
    if "--rebuild" in sys.argv:
        rebuild_all()
    else:
        incremental()
