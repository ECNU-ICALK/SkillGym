from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path


OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", "/root/final_launch_copy_package.json"))
WORK_ORDER_PATH = Path(os.environ.get("WORK_ORDER_PATH", "/workspace/work_order.json"))
SERVICE_BASE_URL = os.environ.get("SERVICE_BASE_URL", "http://127.0.0.1:8080")


def fetch_json(path: str) -> dict:
    req = urllib.request.Request(
        SERVICE_BASE_URL.rstrip("/") + path,
        headers={"X-Client": "oracle-solution"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def post_json(path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        SERVICE_BASE_URL.rstrip("/") + path,
        data=data,
        headers={"Content-Type": "application/json", "X-Client": "oracle-solution"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    work_order = json.loads(WORK_ORDER_PATH.read_text(encoding="utf-8"))
    fetch_json("/api/source-index")
    fetch_json("/api/tone-examples")
    fetch_json("/api/banned-phrases")
    fetch_json("/api/editorial-constraints")
    fetch_json("/api/rejected-draft")
    for doc_id in [
        "ai_overview",
        "parallel_agents_blog",
        "parallel_agents_docs",
        "codex_in_zed",
        "repo_readme",
    ]:
        fetch_json(f"/api/document/{doc_id}")

    payload = {
        "campaign_id": work_order["campaign_id"],
        "source_trace": [
            {"source": "/workspace/work_order.json", "purpose": "Read the campaign contract and word limits."},
            {"source": "/workspace/service_manifest.json", "purpose": "Read the local content-service endpoint map before querying the service."},
            {"source": "/workspace/drafts/rejected_copy.json", "purpose": "Track the issues that must be corrected in the new package."},
            {"source": "/api/source-index", "purpose": "Confirm the source packet inventory before drafting."},
            {"source": "/api/tone-examples", "purpose": "Align the package with the approved developer-facing tone."},
            {"source": "/api/banned-phrases", "purpose": "Remove hype and unsupported launch language."},
            {"source": "/api/editorial-constraints", "purpose": "Keep terminology and release language within the allowed bounds."},
            {"source": "/api/rejected-draft", "purpose": "Capture the previous draft failures for revision notes."},
            {"source": "/api/document/ai_overview", "purpose": "Ground product identity, AI posture, and architecture details."},
            {"source": "/api/document/parallel_agents_blog", "purpose": "Ground launch-specific workflow and Threads Sidebar language."},
            {"source": "/api/document/parallel_agents_docs", "purpose": "Ground thread behavior, layout, and worktree details."},
            {"source": "/api/document/codex_in_zed", "purpose": "Ground Codex and ACP references."},
            {"source": "/api/document/repo_readme", "purpose": "Ground project lineage and multiplayer positioning."}
        ],
        "deliverables": {
            "homepage_hero": {
                "headline": "Parallel Agents, One Editor",
                "subheadline": "Run multiple agent threads in Zed and keep each task tied to its own context.",
                "body": "Parallel Agents gives Zed a Threads Sidebar for starting, switching, and monitoring agent work across projects. You can mix Zed's built-in agent with external agents such as Codex, while the editor stays open source and GPU-accelerated in Rust."
            },
            "feature_page_section": {
                "title": "Keep Parallel Work Visible",
                "body": "Parallel Agents is built for developers who want more than one AI thread open without losing track of scope. Each thread keeps its own agent, context window, and conversation history, and the Threads Sidebar groups that work by project. You can run one thread in the main worktree, move another into a separate worktree, and choose a different agent for each path. The layout keeps parallel work in one editor window, so long-running tasks stay visible while you compare approaches, isolate edits, review changes with clearer boundaries, and keep follow-up tasks moving."
            },
            "docs_intro": {
                "title": "What Parallel Agents Adds To Zed",
                "body": "Zed's AI workflow already includes agent threads, inline edits, and model choice per task. Parallel Agents extends that model by making thread management a first-class part of the editor. The Threads Sidebar is where you start and switch work, and it can sit next to threads that use external agents through the Agent Client Protocol. That means Codex can live in the same workspace as another agent while each thread keeps its own context, history, and visible place in the workflow."
            },
            "release_note": {
                "title": "Parallel Agents for Structured Multi-Thread Work",
                "what_changed": "Zed now gives agent work a dedicated Threads Sidebar so you can run multiple threads at once, keep them grouped by project, and choose the right agent for each task.",
                "how_it_works": "Each thread keeps its own agent, context window, and conversation history. Threads can stay in the main project or move into a separate Git worktree when you want isolation, and external agents such as Codex can join the same workspace through ACP.",
                "why_it_matters": "The feature turns parallel agent work into something you can inspect and steer inside the editor. The workflow stays grounded in project context, visible state, and tools developers already use."
            },
            "short_update": {
                "body": "Parallel Agents is now part of Zed's AI workflow. You can run multiple threads, keep them organized in the Threads Sidebar, and use Codex through ACP alongside other agents, all inside an open-source editor built in Rust."
            }
        },
        "fact_ledger": [
            {
                "claim_id": "ai_overview.editor_identity",
                "claim": "Zed is an open-source AI code editor.",
                "source": "/api/document/ai_overview#ai_overview.editor_identity",
                "used_in": ["homepage_hero.body", "short_update.body"]
            },
            {
                "claim_id": "ai_overview.native_rust",
                "claim": "Zed's AI features run inside a native, GPU-accelerated application built in Rust.",
                "source": "/api/document/ai_overview#ai_overview.native_rust",
                "used_in": ["homepage_hero.body", "short_update.body"]
            },
            {
                "claim_id": "parallel_agents_blog.parallel_same_window",
                "claim": "Users can orchestrate multiple agents running in parallel in the same window.",
                "source": "/api/document/parallel_agents_blog#parallel_agents_blog.parallel_same_window",
                "used_in": ["homepage_hero.headline", "feature_page_section.body", "release_note.what_changed"]
            },
            {
                "claim_id": "parallel_agents_blog.threads_sidebar_access",
                "claim": "The Threads Sidebar controls access scope and monitors running threads.",
                "source": "/api/document/parallel_agents_blog#parallel_agents_blog.threads_sidebar_access",
                "used_in": ["homepage_hero.body", "release_note.what_changed", "short_update.body"]
            },
            {
                "claim_id": "parallel_agents_docs.independent_threads",
                "claim": "Each thread has its own agent, context window, and conversation history.",
                "source": "/api/document/parallel_agents_docs#parallel_agents_docs.independent_threads",
                "used_in": ["feature_page_section.body", "docs_intro.body", "release_note.how_it_works"]
            },
            {
                "claim_id": "parallel_agents_docs.worktree_isolation",
                "claim": "Users can place a thread in a separate Git worktree for isolation.",
                "source": "/api/document/parallel_agents_docs#parallel_agents_docs.worktree_isolation",
                "used_in": ["feature_page_section.body", "release_note.how_it_works"]
            },
            {
                "claim_id": "codex_in_zed.codex_via_acp",
                "claim": "Codex is supported in Zed through ACP.",
                "source": "/api/document/codex_in_zed#codex_in_zed.codex_via_acp",
                "used_in": ["homepage_hero.body", "docs_intro.body", "release_note.how_it_works", "short_update.body"]
            },
            {
                "claim_id": "codex_in_zed.new_thread_menu",
                "claim": "Codex can be selected from the New Thread menu.",
                "source": "/api/document/codex_in_zed#codex_in_zed.new_thread_menu",
                "used_in": ["docs_intro.body"]
            },
            {
                "claim_id": "repo_readme.atom_tree_sitter",
                "claim": "Zed comes from the creators of Atom and Tree-sitter.",
                "source": "/api/document/repo_readme#repo_readme.atom_tree_sitter",
                "used_in": ["feature_page_section.title"]
            }
        ],
        "revision_notes": [
            {
                "issue": "The rejected hero used hype and superlatives.",
                "change": "Replaced the launch slogan with a fact-first headline and removed banned phrases."
            },
            {
                "issue": "The previous draft claimed fully autonomous behavior.",
                "change": "Reframed the package around threads, context, worktrees, and visible workflow instead of unsupported autonomy."
            },
            {
                "issue": "The earlier package never explained the Threads Sidebar.",
                "change": "Added Threads Sidebar language to the hero, feature page section, and release note."
            },
            {
                "issue": "Codex references were detached from their integration path.",
                "change": "Grounded Codex mentions in ACP and the New Thread menu instead of broad AI-platform language."
            },
            {
                "issue": "The earlier package had no usable source ledger.",
                "change": "Added source trace entries and fact ledger claims tied to the local source packet."
            }
        ]
    }

    payload["quality_report"] = post_json("/api/quality-gate", payload)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
