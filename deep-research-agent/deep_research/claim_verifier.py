# -*- coding: utf-8 -*-
"""Claim Ledger 与事实验证器 (P2)。

从报告和笔记中抽取关键论断，读取已保存的 source 文件，调用 Verifier 模型
判断每个 claim 是否被来源支持。

输出：
  - claims.jsonl:  每条 claim 及其 source_ids
  - verification.jsonl:  每条验证结果（SUPPORTED/PARTIAL/UNSUPPORTED/CONTRADICTED）
  - verification_summary.md:  验证摘要
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import config as cfg
from .runtime_state import get_run, append_jsonl, record_event, load_progress, update_progress


# ── Claim 抽取 ────────────────────────────────────────

def extract_claims_from_report(report_path: Path | None = None) -> list[dict]:
    """从 report.md 中抽取候选 fact claims。

    简单规则：找包含 [N] 引用标记的句子，或包含数值/比较/断言的句子。
    """
    run = get_run()
    path = report_path or run.workspace_dir / "report.md"
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8")
    claims = []

    # 策略 1：带引用标记的句子
    cited = re.finditer(
        r'(?P<sentence>[^。！？\n]{30,200}?\s*\[(?P<refs>[0-9,\-\s]+)\])',
        text,
    )
    for m in cited:
        sentence = m.group("sentence").strip()
        refs = m.group("refs")
        # 解析引用编号
        ref_nums = re.findall(r'\d+', refs)
        claims.append({
            "raw_text": sentence,
            "ref_numbers": ref_nums,
            "source": "report.md (cited)",
        })

    # 策略 2：包含 strong claim 模式的句子
    strong_patterns = [
        r'(?P<s>[^。！？\n]{20,200}?(?:比|相比|优于|不如|提升|降低|增加|减少|达到|超过)[^。！？\n]*?(?:%|\d+倍|\d+％))',
        r'(?P<s>[^。！？\n]{20,200}?(?:论文|研究|实验|调查|数据|报告|官方)[^。！？\n]{10,100}?(?:表明|显示|发现|证明|确认)[^。！？\n]*)',
    ]
    for pattern in strong_patterns:
        for m in re.finditer(pattern, text):
            s = m.group("s").strip()
            # 避免重复
            if not any(c["raw_text"] == s for c in claims):
                claims.append({
                    "raw_text": s,
                    "ref_numbers": [],
                    "source": "report.md (strong claim pattern)",
                })

    # 去重 + 排序（按出现顺序）
    seen = set()
    result = []
    for c in claims:
        if c["raw_text"] not in seen:
            seen.add(c["raw_text"])
            result.append(c)

    return result


# ── 格式化 source 用于验证 ──────────────────────────────

def _read_source_for_verification(source_id: str) -> dict | None:
    """读取 source 文件，返回供 Verifier 使用的摘要格式。"""
    run = get_run()
    src_path = run.sources_dir / f"{source_id}.txt"
    if not src_path.exists():
        # 尝试从 sources.jsonl 读取元数据
        return _read_source_ledger(source_id)

    text = src_path.read_text(encoding="utf-8")
    snippet = text[:cfg.SOURCE_SNIPPET_CHAR_LIMIT]
    if len(text) > cfg.SOURCE_SNIPPET_CHAR_LIMIT:
        snippet += f"\n[... 全文共 {len(text)} 字符]"

    return {
        "source_id": source_id,
        "excerpt": snippet,
        "full_text_path": f"/sources/{source_id}.txt",
        "content_chars": len(text),
    }


def _read_source_ledger(source_id: str) -> dict | None:
    """从 sources.jsonl 读取 source 元数据（无全文时）。"""
    run = get_run()
    ledger = run.state_dir / cfg.SOURCES_LEDGER_FILENAME
    if not ledger.exists():
        return None
    try:
        for line in ledger.read_text(encoding="utf-8").strip().split("\n"):
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("source_id") == source_id:
                return {
                    "source_id": source_id,
                    "excerpt": rec.get("title", "") + " — " + rec.get("url", ""),
                    "full_text_path": rec.get("saved_path", ""),
                    "content_chars": rec.get("content_chars", 0),
                }
    except Exception:
        pass
    return None


# ── 单条 Claim 验证 ────────────────────────────────────

def verify_claim(claim: dict) -> dict:
    """用 source 文件验证单条 claim。

    Args:
        claim: 含 claim_id, claim_text, source_ids

    Returns:
        验证结果 dict（符合 VERIFIER_PROMPT 输出 schema）
    """
    from .model_factory import make_chat_model
    from .prompts import VERIFIER_PROMPT

    # 读取相关 sources
    source_records = []
    for sid in claim.get("source_ids", []):
        src = _read_source_for_verification(sid)
        if src:
            source_records.append(src)

    if not source_records:
        return {
            "claim_id": claim.get("claim_id", ""),
            "status": "NOT_CHECKED",
            "evidence": [],
            "reasoning_summary": "无可用 source 文件",
            "recommended_action": "needs_more_sources",
        }

    # 构建验证 prompt
    sources_text = "\n\n---\n\n".join(
        f"source_id: {s['source_id']}\n{s['excerpt']}"
        for s in source_records
    )
    prompt = (
        f"claim_id: {claim.get('claim_id', '')}\n"
        f"claim: {claim.get('claim_text', claim.get('raw_text', ''))}\n\n"
        f"Sources:\n{sources_text}"
    )

    model = make_chat_model("verifier", rate_limited=True)
    try:
        response = model.invoke(VERIFIER_PROMPT + "\n\n" + prompt)
        text = response.content if hasattr(response, "content") else str(response)
        # 提取 JSON
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            return json.loads(json_match.group())
        # JSON 提取失败
        import sys
        print(f"  [verifier] JSON 解析失败，原始输出前200字符: {text[:200]}", file=sys.__stdout__, flush=True)
    except Exception as e:
        import sys
        print(f"  [verifier] 调用失败: {type(e).__name__}: {e}", file=sys.__stdout__, flush=True)

    # 降级
    return {
        "claim_id": claim.get("claim_id", ""),
        "status": "NOT_CHECKED",
        "evidence": [],
        "reasoning_summary": "Verifier 调用失败（已记录日志）",
        "recommended_action": "needs_more_sources",
    }


# ── 批量验证 ────────────────────────────────────────────

def verify_report(
    run_id: str | None = None,
    min_importance: str = "medium",
    max_claims: int = 10,
) -> dict:
    """对当前 run 的报告执行批量 claim 验证。

    Args:
        min_importance: 最低验证级别（"high" | "medium"）
        max_claims: 最多验证条数

    Returns:
        {"total_claims": N, "verified": N, "results": [...]}
    """
    run = get_run()
    report_path = run.workspace_dir / "report.md"
    if not report_path.exists():
        return {"total_claims": 0, "verified": 0, "results": [], "error": "report.md 不存在"}

    record_event("claim_verification_started", {"run_id": run.run_id})

    # 1. 抽取 claims
    raw_claims = extract_claims_from_report(report_path)
    if not raw_claims:
        record_event("claim_verification_completed", {"total_claims": 0, "verified": 0})
        return {"total_claims": 0, "verified": 0, "results": []}

    # 2. 为每个 claim 分配 source_ids（从引用编号推断）
    claims = []
    for i, rc in enumerate(raw_claims[:max_claims]):
        claim_id = f"claim_{i+1:06d}"
        source_ids = []

        # 尝试从 sources.jsonl 匹配引用编号对应的 source
        if rc.get("ref_numbers"):
            # 引用编号与 source 注册顺序的简单映射
            all_sources = _list_all_source_ids()
            for ref_num in rc["ref_numbers"]:
                idx = int(ref_num) - 1
                if 0 <= idx < len(all_sources):
                    source_ids.append(all_sources[idx])

        claims.append({
            "claim_id": claim_id,
            "run_id": run.run_id,
            "section": "",
            "claim_text": rc["raw_text"],
            "source_ids": source_ids,
            "importance": "medium",
            "created_by": "claim_verifier",
            "verification_status": "NOT_CHECKED",
        })

        # 写入 claims.jsonl
        append_jsonl(cfg.CLAIMS_LEDGER_FILENAME, claims[-1])

    record_event("claims_extracted", {"count": len(claims)})

    # 3. 逐条验证（带进度提示）
    import sys as _sys
    results = []
    total = len(claims)
    for idx, claim in enumerate(claims, 1):
        print(f"  [核验] {idx}/{total} {claim['claim_id']}...", file=_sys.__stdout__, flush=True)
        result = verify_claim(claim)
        result["verified_at"] = datetime.now(timezone.utc).isoformat()
        results.append(result)
        status = result.get("status", "?")
        print(f"  [核验] {idx}/{total} {claim['claim_id']} → {status}", file=_sys.__stdout__, flush=True)

        # 更新 claim 状态
        claim["verification_status"] = result.get("status", "NOT_CHECKED")

        # 写入 verification.jsonl
        append_jsonl(cfg.VERIFICATION_LEDGER_FILENAME, result)

        record_event("claim_verified", {
            "claim_id": claim["claim_id"],
            "status": result.get("status"),
        })

    # 4. 更新 progress
    status_counts = {"SUPPORTED": 0, "PARTIAL": 0, "UNSUPPORTED": 0, "CONTRADICTED": 0, "NOT_CHECKED": 0}
    for r in results:
        s = r.get("status", "NOT_CHECKED")
        if s in status_counts:
            status_counts[s] += 1

    update_progress(
        verification={
            "enabled": True,
            "verified": status_counts["SUPPORTED"],
            "unsupported": status_counts["UNSUPPORTED"],
            "partial": status_counts["PARTIAL"],
            "contradicted": status_counts["CONTRADICTED"],
        }
    )
    update_progress(claim_count=len(claims))

    # 5. 生成验证摘要
    _write_verification_summary(results, claims)

    record_event("claim_verification_completed", {
        "total_claims": len(claims),
        "verified": status_counts["SUPPORTED"],
        "unsupported": status_counts["UNSUPPORTED"],
    })

    return {
        "total_claims": len(claims),
        "verified": status_counts["SUPPORTED"],
        "partial": status_counts["PARTIAL"],
        "unsupported": status_counts["UNSUPPORTED"],
        "contradicted": status_counts["CONTRADICTED"],
        "results": results,
    }


# ── 验证摘要 ────────────────────────────────────────────

def _write_verification_summary(results: list[dict], claims: list[dict]) -> None:
    """生成 verification_summary.md 到 run workspace。"""
    run = get_run()
    lines = [
        "# 验证摘要",
        "",
        f"生成时间: {datetime.now(timezone.utc).isoformat()}",
        f"总 claims: {len(claims)}",
        "",
        "## 统计",
        "",
    ]
    counts = {}
    for r in results:
        s = r.get("status", "NOT_CHECKED")
        counts[s] = counts.get(s, 0) + 1
    for status in ["SUPPORTED", "PARTIAL", "UNSUPPORTED", "CONTRADICTED", "NOT_CHECKED"]:
        n = counts.get(status, 0)
        icon = {"SUPPORTED": "✅", "PARTIAL": "⚠️", "UNSUPPORTED": "❌", "CONTRADICTED": "🚫", "NOT_CHECKED": "⬜"}[status]
        lines.append(f"- {icon} {status}: {n}")

    lines.append("")
    lines.append("## 详情")
    lines.append("")
    for r in results:
        claim_text = ""
        for c in claims:
            if c["claim_id"] == r.get("claim_id"):
                claim_text = c.get("claim_text", "")[:150]
                break
        status = r.get("status", "?")
        lines.append(f"### {r.get('claim_id')} — {status}")
        lines.append(f"> {claim_text}")
        lines.append(f"- 建议: {r.get('recommended_action', 'N/A')}")
        if r.get("reasoning_summary"):
            lines.append(f"- 理由: {r['reasoning_summary']}")
        lines.append("")

    summary_path = run.workspace_dir / "verification_summary.md"
    summary_path.write_text("\n".join(lines), encoding="utf-8")


# ── 辅助 ────────────────────────────────────────────────

def _list_all_source_ids() -> list[str]:
    """列出当前 run 所有已注册 source_id。"""
    run = get_run()
    ledger = run.state_dir / cfg.SOURCES_LEDGER_FILENAME
    if not ledger.exists():
        return []
    ids = []
    try:
        for line in ledger.read_text(encoding="utf-8").strip().split("\n"):
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("source_id"):
                ids.append(rec["source_id"])
    except Exception:
        pass
    return ids
