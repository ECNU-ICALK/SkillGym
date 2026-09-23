# Review Scope

Topic: inference-time reasoning methods for text-only language models.

Inclusion rules:
- The paper's main contribution changes reasoning behavior at inference time.
- The paper studies a text-only language model or a text-only prompting workflow.
- The paper may use prompting, sampling, decomposition, search, or program-based execution.

Exclusion rules:
- `outside_scope_modality`: the paper is centered on multimodal or vision-language settings.
- `requires_parameter_update`: the paper's main contribution depends on weight updates, fine-tuning, self-training, or other parameter updates.
- `tool_or_agent_orchestration`: the paper's main contribution is external tool use or agent orchestration during inference.
- `diagnostic_only`: the paper mainly analyzes behavior and does not propose a new inference method.
- `outside_topic`: the paper is outside the reasoning-method comparison task.

Normalized reasoning families:
- `cot`
- `zero_shot_cot`
- `self_consistency`
- `decomposition`
- `automatic_demonstration`
- `program_of_thought`
- `tree_search`
- `graph_search`

Prompting modes:
- `few_shot`
- `zero_shot`
- `mixed`
- Use `mixed` when the bundled paper text describes a method that combines multiple prompting styles or uses both prompt elicitation and demonstration-oriented construction within the same method description.

Evidence notes:
- Use the bundled abstract snapshot as the source of scope evidence and supporting snippets.
- `screening_decisions.tsv` must contain a short `scope_anchor` for every paper.
- `citation_source` should identify the XML metadata source for that paper as `arxiv_id_feed.xml::<paper_id>`.
- Use the paper ID as the primary join key across files.
- `legacy_screening_notes.tsv` is a draft worksheet and may contain mistakes; verify against the bundled paper text before using it.
