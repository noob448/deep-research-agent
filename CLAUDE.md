# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A **self-learning project** to build a deep research agent from scratch using LangChain's `deepagents` library. The BUILD_GUIDE.md is the canonical pedagogical reference — follow its step order exactly when reconstructing from scratch. Each step builds on the previous one and teaches a specific concept.

**Core idea:** A plain agent fails at long research because it can't plan, its context fills with raw search output, and it can't go deep on one thread without losing others. The deep-agent harness solves this with four built-in primitives: **planning** (`write_todos`), **context offloading** (virtual filesystem), **delegation** (`task` → sub-agents), and **memory**.

## Commands

```bash
# One-time: install dependencies (in the project's conda env)
pip install -r deep-research-agent/requirements.txt

# Run a research task — two entry points, pick one:
python deep-research-agent/examples/run.py "你的研究问题"
python deep-research-agent/run_test.py "你的研究问题"  # richer real-time output

# Quick check that config loads and reranker imports
python -c "from deep_research.config import *; print('OK', AGENT_MODEL, RERANK_ENABLED)"
```

The two entry points differ in output style. `examples/run.py` is minimal (summarizes tool calls, shows final AI messages). `run_test.py` is verbose: it prints phase headers, per-researcher progress lines, tool args, and final filesystem inventory. Both stream the agent loop and both generate `workspace/report.md` + `.docx`.

## Architecture (current, implemented)

The target is a **supervisor + 3 named researchers** multi-agent system. This is already built (BUILD_GUIDE steps 1–7 are done):

```
run.py ──► agent.py (create_deep_agent → supervisor)
               │
               ├── subagents.py → 3× researcher-{1,2,3} (each owns web_search + web_fetch)
               ├── prompts.py → SUPERVISOR_PROMPT + RESEARCHER_PROMPT
               ├── config.py → all tunables (models, search, rerank, paths)
               ├── tools.py → web_search + web_fetch @tools (DuckDuckGo, not Tavily)
               ├── rerank.py → BAAI/bge-reranker-v2-m3 cross-encoder (search→re-rank→keep top-k)
               ├── report.py → Markdown → .docx (python-docx, no pandoc)
               └── skills/
                   ├── academic-report/SKILL.md → report structure + citation rules
                   └── source-quality/SKILL.md → source credibility heuristics
```

### Supervisor workflow (5 phases, encoded in SUPERVISOR_PROMPT)

1. **Plan** — `write_todos` immediately, break topic into 3–4 sub-questions
2. **Delegate** — fire 3 `task` calls in one message to researcher-1/2/3, wait for all to return
3. **Archive & review** — write researcher returns to `/notes/*.md`, check completeness, re-delegate if needed
4. **Write report** — write `/report.md` in 4 incremental sections (summary→findings→analysis→conclusion+references), never all at once
5. **Self-critique + archive** — re-read report, fix gaps, write `/research_summary.txt` as final archival step

### Researcher workflow

Each researcher has a hard cap of **8 web_search calls**. They must: break broad questions into narrow queries → search → fetch → return findings inline in the response message (with source URLs). The prompt encodes query-narrowing rules and an explicit format for the return: `[进度]` markers for heartbeat, `[完成] 研究摘要` with structured findings.

### Key design choices (deviations from the original BUILD_GUIDE plan)

- **DuckDuckGo, not Tavily.** Search uses the free `ddgs` library. This means: no API key needed for search, but also no `score` field, no `search_depth`, no domain filtering. The Tavily-based filtering plan in SEARCH_QUALITY_PLAN.md task 1 does not apply.
- **3 named researchers, not 1.** `subagents.py` creates `researcher-1`, `researcher-2`, `researcher-3` as separate SubAgent dicts (same tools and prompt, but distinct names so LangGraph can tag tool logs per-researcher).
- **Researchers return findings inline, not just file paths.** The RESEARCHER_PROMPT explicitly says: "主管无法直接读取你写入的文件" (supervisor can't read your files) so findings must be in the return message. The supervisor then writes those to `/notes/` itself. This is a pragmatic workaround for the deepagents task-result plumbing.
- **Rerank pipeline is built.** `tools.py` → `rerank.py`: search returns 10 results, `BAAI/bge-reranker-v2-m3` cross-encoder re-scores them against the query, only top 4 survive. This is the single highest-leverage quality improvement (per SEARCH_QUALITY_PLAN.md task 4).
- **DeepSeek API as the model provider** (OpenAI-compatible endpoint). API key lives in `deepseek.txt` at repo root (not committed) or `DEEPSEEK_API_KEY` env var. All agents (supervisor + 3 researchers) use the same model (`deepseek-v4-pro`).
- **Chinese-language context.** Prompts and skills are written in Chinese (matching the user's language). The HuggingFace endpoint is automatically set to `https://hf-mirror.com` for faster model downloads in China. `run_test.py` fixes Windows stdout encoding.
- **Report generation uses python-docx, not pandoc.** `report.py` parses Markdown line-by-line with regex, builds a `python-docx` Document. Handles headings, bold/italic/links, code blocks, lists, and task lists. Falls back gracefully if `python-docx` is not installed.

## File responsibility map (where to change what)

| Concern | File(s) | Notes |
|---------|---------|-------|
| Agent behavior (supervisor) | `prompts.py` → `SUPERVISOR_PROMPT` | 80% of behavior lives here |
| Agent behavior (researcher) | `prompts.py` → `RESEARCHER_PROMPT` | Query narrowing, search cap, return format |
| Search quality | `tools.py`, `rerank.py`, `config.py` | DDGS params, rerank model, top-k |
| Sub-agent count/model | `subagents.py` | Currently 3 identical researchers |
| Model/provider/limits | `config.py` | `AGENT_MODEL`, `RECURSION_LIMIT`, timeouts |
| Report structure rules | `skills/academic-report/SKILL.md` | Progressive disclosure — loaded on demand |
| Source credibility rules | `skills/source-quality/SKILL.md` | Loaded when researcher evaluates results |
| Output format (.docx) | `report.py` | Deterministic, outside agent loop |
| Workspace lifecycle | `agent.py` → `_prepare_workspace()` | Wipes `workspace/` on each run, copies skills in |
| History archiving | `run_test.py` → `_archive_to_history()` | Saves `research_summary.txt` to `history-database/<category>/` |

## Key architectural rules

- **Supervisor can't search.** `web_search` / `web_fetch` live only on researcher sub-agents. The supervisor orchestrates, never searches directly.
- **Context isolation via delegation.** Each researcher has its own context window via `task()`. Raw search output stays in the researcher; only the structured summary returns to the supervisor.
- **Skills are progressive disclosure.** YAML frontmatter (name + description) is always visible to the agent; the body loads only when the task matches. This keeps the system prompt lean.
- **Deterministic plumbing stays out of the agent.** `.docx` formatting happens in Python, not in the agent loop. The agent owns research and prose; code owns presentation.
- **Recursion limit is the safety valve.** `config.py` → `RECURSION_LIMIT = 250`. Every model turn and tool call is one step. Too low = mid-research halt; too high = runaway loop burn.
- **All tunables in config.py.** No hardcoded values in tools, prompts, or agent assembly. This includes model name, search params, rerank settings, timeouts, and concurrency.

## SEARCH_QUALITY_PLAN.md status

This file is an implementation spec that was largely completed. What's done:
- ✅ Task 2: Query narrowing in RESEARCHER_PROMPT
- ✅ Task 3: `skills/source-quality/SKILL.md` created
- ✅ Task 4: Rerank pipeline (`rerank.py` + integration in `tools.py`)

What's NOT done (and why):
- ❌ Task 1 (Tavily domain filtering): Not applicable — project uses DuckDuckGo which doesn't support `include_domains`/`exclude_domains`/`score` filtering
- ❌ Task 5 (academic search source): Not yet implemented — would add `search_papers` tool calling arXiv API alongside the existing `web_search`

## What NOT to do

- Don't switch search backends without understanding the tradeoffs (Tavily needs an API key but has better filtering; DuckDuckGo is free but noisier)
- Don't add tools to the supervisor — it should only orchestrate via `task`, `write_todos`, `write_file`, `read_file`
- Don't hardcode paths or values that belong in `config.py`
- Don't change the researcher return format (inline findings in message) without testing — this was a hard-won workaround for the deepagents `task()` result plumbing
- Don't remove the `write_todos`-first instruction from the supervisor prompt — it's the anchor that prevents the agent from winging it

## Reference projects (for ideas, not copy-paste)

- `langchain-ai/deep_research_from_scratch` — notebook-by-notebook construction
- `langchain-ai/open_deep_research` — production-grade supervisor/researcher
- `deepagents` docs: https://docs.langchain.com/oss/python/deepagents/overview
- `deepagents` API reference: https://reference.langchain.com/python/deepagents/

## Extension points (from BUILD_GUIDE step 8)

- LangGraph `Store` for cross-run memory (briefs and reports persist across threads)
- Context summarization for very long runs
- Human-in-the-loop plan gating (interrupt after `write_todos`)
- Parallel delegation (fire multiple `task` calls before collecting)
- Reflection/critique loop (critique sub-agent reads report against skill checklist)
- Academic search source (`search_papers` via arXiv/Semantic Scholar API)
