# -*- coding: utf-8 -*-
"""一次性引导建库脚本：把 history-database/ 下已有 txt 全部向量化入库。
幂等：重复运行不会产生重复向量。"""
from pathlib import Path
from deep_research.config import PROJECT_ROOT
from deep_research.knowledge_base import index_document, get_document_count

HISTORY_DIR = PROJECT_ROOT / "history-database"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def main():
    files = list(HISTORY_DIR.rglob("*.txt"))
    if not files:
        print("history-database/ 下没有 txt 文件，无需建库。")
        return
    print(f"发现 {len(files)} 个历史研究文件，开始建库...")
    for i, f in enumerate(files, 1):
        try:
            print(f"  [{i}/{len(files)}] {index_document(f)}")
        except Exception as e:
            print(f"  [{i}/{len(files)}] 失败：{f} → {e}")
    print(f"建库完成。当前向量库文档数: {get_document_count()}")


if __name__ == "__main__":
    main()
