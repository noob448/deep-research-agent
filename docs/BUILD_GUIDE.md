# BUILD GUIDE — reconstruct this agent yourself

This project exists so you can **learn the deep-agent pattern by building it**, not by
running someone else's finished app. Below is the order to (re)write the files in, the
concept to internalize at each step, and small experiments to make the ideas stick.

Work top-to-bottom. Each step depends only on the ones before it.

---

## Step 0 — Mental model first (no code)

Before writing anything, get the core idea straight:

> A long research task fails on a plain agent because (a) it can't plan, (b) its
> context fills with raw search dumps, and (c) it has no way to go deep on one thread
> without losing the others. The **deep-agent harness** solves these with four
> built-in primitives: **planning** (`write_todos`), **context offloading**
> (a virtual filesystem), **delegation** (`task` → sub-agents), and **memory**.

Your supervisor will *orchestrate*; your researcher sub-agents will *search*. The
contract between them — researchers write notes to files, the supervisor reads files,
raw search output never travels back up — is the whole reason this scales. Keep that
sentence in mind through every step.

Read the `deepagents` overview docs once:
https://docs.langchain.com/oss/python/deepagents/overview

---

## Step 1 — `config.py` — name your knobs

**Write it.** Centralize: models, search depth, **recursion limit**, workspace path,
skills path.

**Concept: the recursion limit is your safety valve.** Every model turn and tool call
is one step in the LangGraph loop. An autonomous multi-sub-agent run can take many
steps; too low and it halts mid-research, too high and a misbehaving loop burns money.
Start at ~250 and watch how close real runs get.

**Experiment:** after everything works, set `recursion_limit = 15` and run a real
topic. Watch it stop partway. That failure teaches you what the limit actually governs.

---

## Step 2 — `tools.py` — give researchers eyes

**Write it.** Two LangChain `@tool`s: `web_search` (snippets) and `web_fetch` (full
page, truncated).

**Concept: tool docstrings are prompt.** The model decides when to call a tool purely
from its name + docstring. Notice how each docstring tells the agent *when* to reach
for it and — critically — to `write_file` anything worth keeping instead of holding it
in context. You're teaching context hygiene through the tool description itself.

**Experiment:** temporarily shorten `fetch_char_limit` to 500 and observe the agent
fetching, losing detail, and re-searching. Then restore it. This shows why offloading
to files beats stuffing the window.

---

## Step 3 — `prompts.py` — encode the workflow

**Write it.** Two prompts: `SUPERVISOR_PROMPT` (scope → plan → delegate → collect →
synthesize) and `RESEARCHER_PROMPT` (search → distill → write note → return summary).

**Concept: the harness prompt + your prompt compose.** `deepagents` already injects a
base prompt teaching the model how to use `write_todos`, the filesystem, and `task`.
Your `system_prompt` sits on top and supplies *mission and procedure*. You don't
re-explain the tools; you explain the job.

**This is the highest-leverage file.** 80% of agent behavior is here. Re-read the
context-isolation paragraph in each prompt — that's the load-bearing instruction.

**Experiment:** delete the "write findings to a note file, return only a short
confirmation" instruction from the researcher prompt. Re-run. Watch researchers dump
whole pages back to the supervisor and the supervisor's context balloon. Then put it
back. You'll never forget why delegation needs a file boundary.

---

## Step 4 — `subagents.py` — declare a worker

**Write it.** One function returning the researcher `SubAgent` dict:
`name`, `description`, `system_prompt`, `tools`, `model`.

**Concept: a sub-agent is a full deep agent.** When the supervisor calls
`task(description=..., subagent_type="researcher")`, the harness spins up a complete
agent loop with its *own* context window. That isolation is why ten parallel
sub-questions don't pollute each other or the supervisor. Note that `web_search` /
`web_fetch` live **only** here — the supervisor can't search, by design.

**Experiment:** give the researcher a cheaper/faster model than the supervisor (e.g. a
mini model). Quality of the final report barely moves, cost drops a lot. This is the
real-world reason delegation matters beyond context: you match model strength to task.

---

## Step 5 — `agent.py` — assemble the supervisor ★

**Write it.** One `create_deep_agent(...)` call wiring: `model`, `system_prompt`,
`subagents=[researcher]`, a filesystem `backend`, and `skills`.

**Concept: "batteries included."** You never pass `write_todos`, `read_file`,
`write_file`, or `task` — the harness adds them. You only supply what's *yours*: the
mission, the workers, the storage, the domain skill.

**Concept: backends decide where files live.**
- In-memory (default): files live in LangGraph state — perfect for tests, vanishes
  after the run.
- Local disk (what we use): files map to `./workspace` so you can **open them while
  the agent runs** and watch `/notes/*.md` appear one by one. Seeing that is the
  single best way to understand context offloading.
- Later: a sandbox backend (Modal/Daytona/Deno) if you want the agent to execute code.

The file guards optional params (`backend`, `skills`) behind a signature check so the
project survives `deepagents` API drift. When you're learning, you can delete the
guards and pass them directly — just pin your installed version first and check its
reference: https://reference.langchain.com/python/deepagents/

**Experiment:** swap to the in-memory backend (drop the `backend` kwarg). The agent
still works, but `workspace/` stays empty. Compare the two runs to feel what a backend
actually does.

---

## Step 6 — `skills/academic-report/SKILL.md` — teach the writer

**Write it.** A `SKILL.md` with YAML frontmatter (`name`, `description`) and the body:
required report structure, citation rules, quality checklist.

**Concept: skills are just-in-time expertise.** A skill is a folder with a `SKILL.md`.
The harness makes its `description` visible to the agent; when the task matches (here,
"synthesize the final report"), the agent pulls in the body for detailed instructions.
This keeps the system prompt lean — you don't carry report-writing rules in context
during the whole research phase, only when you actually write the report.

**This is the "skills底层原理" you wanted to see:** progressive disclosure. Metadata is
always cheap and visible; the heavy instructions load only on demand. That's the same
mechanism Claude Code-style agents use to scale to hundreds of skills without bloating
context.

**Experiment:** add a second skill, `skills/lit-review/SKILL.md`, with a different
structure, and tell the supervisor to choose between report styles based on the topic.
Watch it select. Now you understand skill routing.

---

## Step 7 — `report.py` + `examples/run.py` — close the loop

**Write them.** `report.py` converts `/report.md` → `.docx` (pandoc, with a
python-docx fallback). `run.py` builds the agent, **streams** the run, and renders the
doc.

**Concept: keep deterministic plumbing out of the agent.** Formatting a Word file is
not a reasoning task; doing it in Python (not in the agent loop) saves steps and is
more reliable. The agent owns research and prose; code owns presentation.

**Concept: streaming is your debugger.** `agent.stream(..., stream_mode="values")`
lets you watch every step — plan updates, `task` calls, file writes. Run it once and
just *read* the trace. The deep-agent loop stops being abstract.

---

## Step 8 — Where to go next (long-horizon & memory)

Once the core runs, extend toward the "autonomous, long-running, independent" goal:

- **Long-term memory across runs.** Add a LangGraph `Store` so briefs and finished
  reports persist across threads; have the supervisor check memory for prior work on a
  topic before researching. This is the `memory底层原理` piece — durable key-value
  state outside any single conversation.
- **Auto-summarization for very long runs.** Enable the harness's context summarization
  so old messages compact when the window grows. Combined with file offloading, this
  is what lets a run go for *hours* without falling over.
- **Human-in-the-loop.** Gate the plan: after `write_todos`, interrupt for your
  approval before the agent spends tokens on research.
- **Parallel delegation.** Have the supervisor fire multiple `task` calls before
  collecting, so researchers run concurrently. Measure the wall-clock win.
- **Reflection loop.** After the first `/report.md`, add a "critique" sub-agent that
  reads it against the skill checklist and sends gaps back for a second pass.

Each of these maps to a real capability in `deepagents` — add them one at a time and
keep the streaming trace open so you see exactly what each one changes.

---

## Reference projects to borrow from (not copy wholesale)

- `langchain-ai/deep_research_from_scratch` — notebook-by-notebook construction of the
  same scoping → research → synthesis flow. Closest to this guide's spirit.
- `langchain-ai/open_deep_research` — a fuller supervisor/researcher implementation;
  good for seeing production-grade prompts and parallelization.
- `deepagents` docs & API reference — the source of truth for current parameter names.

Read them for *ideas and prompt phrasing*. Then write your own version here — that's
where the learning is.
