import path from "node:path";
import { getVisibleSkills, type GenerationUnit, type PublishedTaskInfo, type SkillInfo } from "./discovery.js";
import type { DerivedTaskPlan } from "./schema.js";
import { dedent } from "./utils.js";

function renderSkills(skills: SkillInfo[]): string {
  if (skills.length === 0) {
    return "- 无 skills";
  }
  return skills.map((skill) => `- ${skill.name} (${skill.dirName})`).join("\n");
}

function renderScopeBrief(unit: GenerationUnit): string {
  if (unit.skillMode === "all") {
    return dedent(`
      当前模式: all
      当前 task 必须保留全部输入 skills 的关键能力点和实际解题收益。
      当前 scope 固定为 all-skills。
    `);
  }

  return dedent(`
    当前模式: per-skill
    当前目标 skill: ${unit.targetSkill?.name ?? "unknown"} (${unit.targetSkill?.dirName ?? "unknown"})
    这是严格单技能构造模式：
    - 当前 task 只允许围绕这个目标 skill 设计。
    - 当前 task 中只能注入这一个 shipped skill。
  `);
}

function renderPublishedTaskEntry(task: PublishedTaskInfo): string {
  return dedent(`
    - ${task.derivedTaskId}
      acceptance kind: ${task.acceptanceKind ?? "unknown"}
      task dir: ${task.taskDir}
      read first: ${task.planPath}
      then read: ${task.instructionPath}
      then read: ${task.taskTomlPath}
      optional: ${task.testOutputsPath}
      optional assets dir: ${task.environmentDir}
  `);
}

function renderPublishedTaskReference(unit: GenerationUnit): string {
  if (unit.publishedTasks.length === 0) {
    return dedent(`
      已发布 Harbor family 目录: ${unit.finalFamilyDir || "unknown"}
      当前还没有已发布任务；如果该目录之后出现内容，也要把它当成历史已发布任务直接读取。
    `);
  }

  return dedent(`
    已发布 Harbor family 目录: ${unit.finalFamilyDir}
    这些任务已经发布到 final-root。planner、writer、reviewer、repair 都必须直接读取这些绝对路径：
    ${unit.publishedTasks.map((task) => renderPublishedTaskEntry(task)).join("\n")}
  `);
}

function renderTemplateReferenceRules(assetTargetDir: string): string {
  return dedent(`
    模板参考规则:
    - template_source/ 是参考模板，不是让你机械复写的最终任务。
    - template_source/environment/skills/ 里的内容只作为模板上下文参考，不代表最终 shipped skills。
    - input_skills/ 才是本轮真正要注入最终任务的 shipped skills 来源。
    - 你可以复用、裁剪、重命名 template_source/environment/ 中的输入资产，也可以在 ${assetTargetDir} 下新建全新的输入资产；如果任务需要真实世界背景、数据、规则或样例，必须通过 web search 获取真实数据来源并体现在输入资产中。输入资产需要包含执行任务所需的前置输入，不能包含Harbor任务格式下的solution和tests。
    - 派生任务不要求保留模板任务的原始素材、文件名或目录结构；只要任务目标、验证方式合理即可。
  `);
}

function renderInputSkillRules(
  unit: GenerationUnit,
  options: {
    draftSkillDirLabel?: string;
  } = {},
): string {
  const visibleSkills = getVisibleSkills(unit);
  const draftSkillDir = options.draftSkillDirLabel ?? "draft/environment/skills/";
  return dedent(`
    输入 skill 规则:
    - ${draftSkillDir} 已由系统从 input_skills/ 预先注入。
    - 这些 injected skills 是只读 payload；不要修改、删除、重命名、增补或重排其中任何文件。
    - 最终 shipped skills 只由 input_skills/ 决定，不由 template_source/environment/skills/ 决定。
    - 当前可见 input skills:
    ${renderSkills(visibleSkills)}
  `);
}

function renderHarborOracleBaseline(): string {
  return dedent(`
    Harbor verifier 契约:
    - Harbor 会执行 /tests/test.sh 作为 verifier 入口。
    - Harbor 只识别 /logs/verifier/reward.txt 和 /logs/verifier/reward.json；写到其他位置不会被识别。所以要稳定在这两个路径下写reward，方便后续判断任务是否通过。
    - tests/test.sh 不得在未写出 reward 的情况下直接结束；无论测试通过还是失败，都必须稳定写出 reward。
    - tests/test.sh 在写入 verifier 日志、CTRF 或 reward 前，必须先执行 mkdir -p /logs/verifier。
  `);
}

function renderTaskArtifactContracts(): string {
  return dedent(`
    关键文件契约:
    - solution/solve.sh 必须像真实 solver 一样，基于输入资产、任务规则和公开依赖推导可通过测试的结果。
    - solution/solve.sh、tests/test.sh、tests/test_outputs.py 不得直接依赖 skill 安装路径或 skill 文件内容。
    - instruction.md 不要直接要求做题者使用 input skills，也不要暴露内部实现、oracle、verifier 或可直接照搬的答案捷径。
    - tests/test_outputs.py 只检查 instruction.md 已说明或可直接推出的、与题目问题本身和目标 skill 关键能力直接相关的核心输出契约，尽量面向结果语义；不要把 instruction.md 章节结构、task.toml 元数据字段、英文要求、source_template_id、Harbor 包装层要求写成主测试点。
    - 防作弊测试只拦截明显 shortcut，不要新增主任务契约之外的核心要求。
    - 在验证agent是否成功通过任务的时候，tests/test_outputs.py 不得依赖固定关键词、固定短语、固定同义词集合或唯一措辞，除非 instruction.md 明确说明要输出固定关键词、固定短语、固定同义词集合或唯一措辞。
    - 如果测试要求字段、端点、文件路径、状态码、schema 名称或输出结构，instruction.md 必须明确说明。
  `);
}

function renderInstructionWritingRules(): string {
  return dedent(`
    instruction.md 写作契约:
    - instruction.md 必须使用英文，简洁、用户可读。
    - instruction.md 必须严格使用这些章节：Brief opening, Input data, Your task, Output, Notes。
    - 写题前先阅读目标 skill，理解它的适用场景、核心工作流和输出判断方式；任务设计应考验 solver 是否能自然识别并执行这种工作流，但 instruction.md 不要明说“使用某个 skill”。
    - 题面只保留用户可见的交付合同：输入位置、输入资产含义、要完成的任务、输出文件、必要格式和边界条件。
    - 弱化或移走本应由 skill 提供的诊断细节、推理步骤和专家判断框架。
    - instruction.md 不得提及 verifier、tests、solution、task.toml、plan.json、/logs、shipped skill payload、installed skill path 等内部实现细节。
  `);
}

function renderVerifierDesignPrinciples(): string {
  return dedent(`
    verifier(目标是验收agent是否成功通过任务) 设计原则:
    - verifier 设计必须明确分为主测试和防作弊测试两部分。
    - 主测试负责验证题目要求的核心输出、结果语义、状态变化和主要成功路径。
    - 防作弊测试负责验证做题者没有通过篡改输入资产、直接搬运现成答案、绕过关键步骤、伪造输出或其他 shortcut 取巧过关。
    - tests/test.sh 与 tests/test_outputs.py 的实现应让这两类检查边界清晰、职责明确，避免混成一个含糊的大一统测试。
    - verifier 主测试只能断言 instruction.md 明确写出的用户可见契约。
    - 防作弊测试只能检测硬编码、fixture 过拟合或 shortcut 行为。
  `);
}

function renderHarborTaskFormatSummary(): string {
  return dedent(`
    Harbor 任务格式摘要:
    - Harbor task 是一个自包含目录，包含面向用户的题面、容器化运行环境、oracle 解法和 verifier。
    - 标准任务结构通常包括：
      - instruction.md：用户可见的任务说明与约束
      - task.toml：任务元数据与运行配置
      - environment/：容器环境与输入资产
      - solution/solve.sh：用于证明任务可行性的 oracle 解法
      - tests/test.sh：verifier 入口
    - Harbor 会先在容器化环境中运行 agent，再执行 /tests/test.sh 来判定 reward。
    - solution/solve.sh 的作用是证明任务可做，它属于内部 oracle 产物，不应在面向用户的 instruction.md 中暴露。
    - tests/test.sh 是 verifier 入口；它的验收应基于可观察输出和状态来验证任务契约，而不是依赖私有实现细节。
    - 常见的Harbor运行时路径，例如/logs/、/oracle/、/tests/ 这类 Harbor 运行时路径属于任务运行环境的一部分，但除非任务通过 instruction.md 明确暴露这些路径，否则它们不会自动对用户可见。
  `);
}

function renderSkillEffectDesignRules(unit: GenerationUnit): string {
  const modeSpecificRule =
    unit.skillMode === "all"
      ? "- all 模式下，多个 shipped skills 都必须对完成任务产生实质影响；任务不能退化为不依赖这些 skills 也能稳定完成。"
      : `- per-skill 模式下，目标 skill ${unit.targetSkill?.name ?? "unknown"} (${unit.targetSkill?.dirName ?? "unknown"}) 必须是关键瓶颈；任务不能退化为不依赖该 skill 也能稳定完成。`;

  return dedent(`
    skill effect 契约:
    - 相关 shipped skill 必须对任务成败产生实质影响；没有这些 skill 时，通用 agent 很难完成任务。
    - 任务难点必须主要来自相关 skill 支撑的关键判断、工作流或领域操作，不得主要来自重型环境搭建、长时间预热、运行时噪声或纯体力编码。
    - 任务不得向 agent 暴露可直接读取并足以通过 verifier 的完整答案、可直接搬运的产物，或其他能绕过关键 skill 的显著 shortcut。
    - 如果不依赖相关 skill，仅凭通用命令行/脚本能力和少量试错就能稳定完成任务，则该任务不构成 skill bottleneck。
    ${modeSpecificRule}
  `);
}

function renderEnvironmentResourceRules(): string {
  return dedent(`
    task.toml 环境与超时契约:
    - task.toml 必须包含 [environment]。
    - [environment].cpus 必须为 2。
    - [environment].memory_mb 必须为 2048。
    - [environment].storage_mb 必须为 5120。
    - [environment].gpus 必须为 0。
    - [environment].build_timeout_sec 必须显式写出，值必须是合理的秒数，足以完成当前 environment/Dockerfile build。
    - task.toml 必须包含 [agent]。
    - [agent].timeout_sec 必须显式写出，值必须是合理的秒数，足以完成当前任务，不要省略。
    - task.toml 必须包含 [verifier]。
    - [verifier].timeout_sec 必须显式写出，值必须是合理的秒数，足以运行 tests/test.sh 和 tests/test_outputs.py。
    - timeout 秒数可以参考 template_source/task.toml，但不要机械照抄；应根据当前任务复杂度、依赖安装、测试耗时和 agent 解题负担合理设置。
  `);
}

function renderDockerfileRules(): string {
  return dedent(`
    Dockerfile 契约:
    - environment/Dockerfile 必须显式声明 WORKDIR。
    - 如果 WORKDIR 不是 /root，solution/solve.sh、tests/test.sh、tests/test_outputs.py 与 Dockerfile 的路径契约仍必须保持一致。
    - agent 解题需要读取、编辑、分析的非 skill 输入资产，应优先 COPY 到 WORKDIR 或其子目录；不要把题目输入散落在默认工作目录外。
    - 纯可执行工具可以放在 /usr/local/bin；后台服务内部实现可以放在其他系统路径，但如果题面要求 agent 直接阅读或修改，应放进 WORKDIR。
    - 这样可以保证 Codex 进入默认工作目录时自然发现任务资产，减少“资产存在但 agent 没看到”的失败。
    - environment/Dockerfile 不得把 skills 复制到普通运行时路径，如 /root/environment/skills、/app/skills、/workspace/skills。
    - environment/Dockerfile 中与 skill 安装相关的唯一允许语句是 COPY skills /root/.codex/skills。
    - 不要再添加任何把 skills/ 或 /root/.codex/skills 复制、移动、同步、软链接到其他目录的 COPY、RUN cp、ln -s、rsync 或等价逻辑。
    - environment/Dockerfile 不得使用 COPY . /root、COPY . /root/、COPY ./ /root、ADD . /root 或带 flag 的等价宽泛复制写法。
  `);
}

export function buildTaskDisplayName(plan: Pick<DerivedTaskPlan, "taskOrdinal">): string {
  return `Task ${plan.taskOrdinal}`;
}

export function buildTaskAttemptBrief(
  unit: GenerationUnit,
  plan: Pick<DerivedTaskPlan, "derivedTaskId" | "taskOrdinal">,
  options: {
    attemptIndex: number;
    draftDirLabel?: string;
    artifactsDirLabel?: string;
  },
): string {
  const template = unit.template;
  const visibleSkills = getVisibleSkills(unit);
  const draftDirLabel = options.draftDirLabel ?? "draft/";
  const artifactsDirLabel = options.artifactsDirLabel ?? "artifacts/";
  const taskDisplayName = buildTaskDisplayName(plan);
  return dedent(`
    # Codex Task Builder Brief

    你现在位于 Harbor task builder 的单题 attempt workspace 中。

    当前 task: ${plan.derivedTaskId} (${taskDisplayName})
    当前 attempt: attempt-${options.attemptIndex}
    当前 attempt 工作目录: task_attempts/${plan.derivedTaskId}/attempt-${options.attemptIndex}/
    当前唯一允许修改的任务目录: ${draftDirLabel}
    NOTE : 
    - 不能主动终止造任务的进程，造任务的进程会自动终止
    - 所有的修改只能在当前 attempt 工作目录下面进行
    当前证据目录: ${artifactsDirLabel}

    模板 ID: ${template.templateId}
    模板相对路径: ${template.templateRelativePath}
    模板目录: template_source/
    输入 skills 目录: input_skills/

    当前 shipped skills:
    ${renderSkills(visibleSkills)}

    ${renderScopeBrief(unit)}
    ${renderPublishedTaskReference(unit)}

    当前工作语义:
    1. 从 template_source/ 读取完整上下文，包括 task.toml、instruction.md、environment/、environment/skills/、solution/、tests；同时阅读 input_skills/ 里的真实 shipped skills。
    2. 如 final-root 中已有同 family 的已发布任务，必须直接读取这些任务目录，避免和它们撞题。
    3. 当前只处理这个 task 的当前 attempt。
    4. 历史 attempt 和其他 task 的未发布草稿都不属于当前上下文，不要把它们当成正式历史任务或去重基准。
    5. 正式历史任务只看 final-root 下已发布的 *__with_skill 任务；不要把 *__no_skill 对照副本当成正式历史任务。
    6. 派生任务只写到 ${draftDirLabel}，不要直接写入最终发布目录。
    7. 每个完整任务至少包含:
       - task.toml
       - instruction.md
       - environment/Dockerfile
       - environment/skills/**
       - solution/solve.sh
       - tests/test.sh
       - tests/test_outputs.py
       - plan.json
    8. plan.json 是 planner 产物，后续 materialize/publish 也要保留，不要删除。
    9. environment/Dockerfile 必须遵守下方 Dockerfile 约束。
    10. 最终 Harbor 任务面向用户可见的文本必须使用英文，至少包括 instruction.md、task.toml 的 metadata.name 和 metadata.description。
    11. ${draftDirLabel}environment/skills/ 由系统从 input_skills/ 预注入，视为只读 payload；不要修改这些 skill 内容。
    ${renderHarborTaskFormatSummary()}
    ${renderTemplateReferenceRules(`${draftDirLabel}environment/`)}
    ${renderInputSkillRules(unit, { draftSkillDirLabel: `${draftDirLabel}environment/skills/` })}
    ${renderSkillEffectDesignRules(unit)}
    ${renderDockerfileRules()}
    ${renderTaskArtifactContracts()}
    ${renderVerifierDesignPrinciples()}
    ${renderEnvironmentResourceRules()}
    ${renderHarborOracleBaseline()}
  `);
}

export function buildSingleTaskPlannerPrompt(
  unit: GenerationUnit,
  plan: Pick<DerivedTaskPlan, "derivedTaskId" | "taskOrdinal">,
): string {
  const template = unit.template;
  const visibleSkills = getVisibleSkills(unit);
  const taskDisplayName = buildTaskDisplayName(plan);
  const slotName = plan.derivedTaskId;

  return dedent(`
    先阅读 TASK_BUILDER_BRIEF.md，然后完整检查 template_source/ 和 input_skills/；如果 final-root 已有同 family 的已发布 *__with_skill 任务，也必须直接读取这些已发布任务目录。

    当前只规划一个任务的当前 attempt，不要写任何文件。
    你只需要为当前槽位返回一个单题 blueprint。

    当前槽位:
    - derivedTaskId: ${plan.derivedTaskId}
    - taskOrdinal: ${plan.taskOrdinal}
    - display name: ${taskDisplayName}

    模板摘要:
    - templateId: ${template.templateId}
    - templateRelativePath: ${template.templateRelativePath}
    - difficulty: ${template.metadata.difficulty ?? "unknown"}
    - category: ${template.metadata.category ?? "unknown"}
    - tags: ${(template.metadata.tags ?? []).join(", ") || "none"}
    - input skills:
    ${renderSkills(visibleSkills)}
    已发布 Harbor family 目录: ${unit.finalFamilyDir || "unknown"}
    当前已发布任务: ${unit.publishedTasks.length === 0 ? "none" : unit.publishedTasks.map((task) => task.derivedTaskId).join(", ")}

    规划要求:
    - 规划前必须完整检查当前相关输入 shipped skills 的目录，至少阅读各自的 SKILL.md 以及其中直接引用的脚本、模板和资源文件；不要只根据 skill 名字猜用途。
    - 规划前必须优先使用 web search 查找真实世界资料、官方文档、公开标准、权威数据库、真实项目文档或公开业务资料。
    - 不要凭空编造关键背景、数据、规则或标准；如果某个关键设定来自真实资料，必须在 referenceData 中记录来源。
    - 应尽可能的规划出一个没有skill连gpt5.4都无法做出来的任务，且失败的细节必须是偏行动级别的失败、一些格式问题可以放宽松，但是有了skill以后，gpt5.4就可以稳定做出来。
    - 必须基于 shipped skill 目录内容提炼关键能力点，并明确说明没有这些能力点时通用 agent 会卡在哪里。
    - 输出的 title、realWorldContext、taskGoal、inputAssets、requiredOutputs、verifierFocus、skillBenefitRationale、difficulty、category 必须用中文；referenceData 可以保留来源标题原文。
    - 当前只规划一个任务 ${slotName}；只返回 schema 要求的 10 个字段：title、realWorldContext、referenceData、taskGoal、inputAssets、requiredOutputs、verifierFocus、skillBenefitRationale、difficulty、category。
    - title: 短标题。
    - realWorldContext: 基于真实资料的现实业务/工作背景。
    - referenceData: planner web search 得到的实际参考来源列表，使用纯文本格式，例如：
      Reference data:

      - Source title: https://example.com/page
      - Source title: https://example.com/another-page
    - taskGoal: agent 最终要完成的任务目标。
    - inputAssets: writer 应该构造哪些输入资产。
    - requiredOutputs: agent 必须产出的文件、字段、报告或状态变化。
    - verifierFocus: verifier 应重点检查的行为、语义和输出契约。
    - skillBenefitRationale: 1.解释目标 skill 为什么与任务关键能力相关。2.解释为什么agent在执行任务的时候为什么有skill会比无skill更容易通过任务
    - difficulty: 难度。
    - category: 类别。
    - derivedTaskId、taskOrdinal、templateId、skillMode、targetSkillDirName、targetSkillName 由程序补齐，不属于 planner 输出。
    - 当前工作上下文只代表这个 task 的当前 attempt；历史 attempt 和其他未发布草稿都不是正式去重基准。
    - input_skills/ 才是最终 shipped skill 来源；不要把 template_source/environment/skills/ 误当成 shipped skills。
    - 如果 final-root 已有同 family 的已发布 *__with_skill 任务，必须先直接读取它们，并主动避免与这些历史任务在任务场景、输入资产、输出语义和测试判定方式上过于接近。
    - 不要把 *__no_skill 对照副本视为正式历史任务。
    ${renderSkillEffectDesignRules(unit)}

    返回严格符合 schema 的 JSON，不要输出额外解释。
  `);
}

export function buildTaskWriterPrompt(
  unit: GenerationUnit,
  plan: DerivedTaskPlan,
  options: {
    draftDirLabel?: string;
  } = {},
): string {
  const taskDisplayName = buildTaskDisplayName(plan);
  const draftDirLabel = options.draftDirLabel ?? "draft/";
  const skillConstraint =
    unit.skillMode === "per-skill"
      ? dedent(`
        - ${draftDirLabel}environment/skills/ 中只能保留一个 shipped skill：${unit.targetSkill?.name ?? "unknown"} (${unit.targetSkill?.dirName ?? "unknown"})。
        - 你必须保持只有这一个 shipped skill，不要复制、引用或假设其他 skills 存在。
        - 这个任务必须在只提供该 skill 的前提下成立。
      `)
      : dedent(`
        - ${draftDirLabel}environment/skills/ 已预先从 input_skills/ 复制当前全部 shipped skills。
      `);

  return dedent(`
    先阅读 TASK_BUILDER_BRIEF.md，然后阅读 template_source/、input_skills/、当前 task 的 plan.json blueprint，以及 final-root 下已发布的 *__with_skill 同 family 任务。

    当前 task blueprint:
    ${JSON.stringify(plan, null, 2)}

    造任务时必须完整使用 plan.json blueprint，尤其要围绕 realWorldContext、referenceData、taskGoal、inputAssets、requiredOutputs、verifierFocus 来设计输入资产、题面、输出契约和 verifier。
    应尽可能的造出一个没有skill连gpt5.4都无法做出来的任务，且失败的细节必须是偏行动级别的失败、一些格式问题可以放宽松，但是有了skill以后，gpt5.4就可以稳定做出来。
    现在只生成一个完整派生任务，写入:
    - ${draftDirLabel}

    写作前先确认：
    - ${draftDirLabel} 是当前任务目录。
    - 当前只允许修改 ${draftDirLabel} 内的文件；不要修改历史 attempt 或其他 task 的未发布草稿。
    - 历史 attempt 或其他未发布草稿都不是当前任务必须参考的去重对象。
    - 当前任务的 sibling / 历史去重，只以 final-root 下已经发布的 *__with_skill 同 family 任务为准。
    - 不要把 *__no_skill 对照副本当成历史任务。
    - 还必须检查 final-root 中已经发布的 *__with_skill 同 family 任务；优先阅读：
      - <published_task>/plan.json
      - <published_task>/instruction.md
      - <published_task>/task.toml
    - 如有必要，再补充检查：
      - <published_task>/tests/test_outputs.py
      - <published_task>/environment/
    - 主动避免与已发布任务在任务场景、输入资产、输出物语义和测试判定方式上过于接近。
    - 已发布 Harbor family 目录: ${unit.finalFamilyDir || "unknown"}
    - 已发布任务列表:
    ${unit.publishedTasks.length === 0 ? "- none" : unit.publishedTasks.map((task) => renderPublishedTaskEntry(task)).join("\n")}
    - 你不能修改 blueprint 中已经固定的核心约束：derivedTaskId、taskOrdinal、templateId、skillMode、targetSkillDirName、targetSkillName。

    已知约束:
    ${skillConstraint}
    ${renderTemplateReferenceRules(`${draftDirLabel}environment/`)}
    ${renderInputSkillRules(unit, { draftSkillDirLabel: `${draftDirLabel}environment/skills/` })}
    ${renderSkillEffectDesignRules(unit)}
    - 未修改的初始 environment 必须无法通过 verifier；任务必须要求 solver 基于题面和输入资产产生实际修改或输出。
    ${renderTaskArtifactContracts()}
    ${renderInstructionWritingRules()}
    ${renderVerifierDesignPrinciples()}
    - task.toml 中 metadata.id 必须等于 "${plan.derivedTaskId}"。
    - task.toml 中 metadata.name 必须显式包含 "${taskDisplayName}"。
    - instruction.md 必须使用英文描述。
    - task.toml 中 metadata.name 和 metadata.description 必须使用英文描述。
    - task.toml 中 metadata.source_template_id 必须等于 "${plan.templateId}"。
    - task.toml 中如保留 metadata.task_role，只能写成 "task"，不得再写 similar 或 transfer。
    - task.toml 的 [metadata] 至少必须包含:
      - id
      - name
      - description
      - author_name
      - author_email
      - difficulty
      - category
      - tags
      - source_template_id
    - task.toml 必须包含 [environment]，并固定写为:
      - cpus = 2
      - memory_mb = 2048
      - storage_mb = 5120
      - gpus = 0
    - task.toml 还必须显式包含 [environment].build_timeout_sec、[agent].timeout_sec、[verifier].timeout_sec。
    - 这些 timeout 字段必须是数值秒数；不要省略，不要依赖 Harbor 默认值。
    - timeout 秒数由你根据 template_source/task.toml 和当前任务复杂度自行设置。
    - 必须保留 plan.json，不要删除或改名；如需更新，只能与当前 blueprint 保持一致。
    ${renderDockerfileRules()}
    - 不要把当前任务实现成比 blueprint 更轻的版本；尤其不要通过教程式 instruction、暴露关键步骤、放置一眼可见答案或单命令捷径，把它稀释成 easy/普通 medium 小题。
    - 不得对已发布 sibling 任务做简单领域换皮；必须在任务场景、输入资产、输出语义和 verifier 判定方式上形成实质差异。
    - instruction.md 和 environment 输入资产都不得暴露 solution/tests/task.toml/plan.json/logs 等任务内部实现细节。
    ${renderHarborOracleBaseline()}

    你需要创建或更新这些文件:
    - plan.json
    - task.toml
    - instruction.md
    - environment/Dockerfile
    - environment/ 下必要输入资产
    - solution/solve.sh
    - tests/test.sh
    - tests/test_outputs.py

    写完文件后，返回严格符合 schema 的 JSON，总结你写入了哪些文件。
  `);
}

export function buildBlockingReviewerPrompt(
  unit: GenerationUnit,
  plan: DerivedTaskPlan,
  options: {
    draftDirLabel?: string;
  } = {},
): string {
  const draftDirLabel = options.draftDirLabel ?? "draft/";

  return dedent(`
    不要修改任何文件。你现在只负责单题 blocking 审查。

    先阅读:
    - TASK_BUILDER_BRIEF.md
    - template_source/
    - input_skills/
    - ${draftDirLabel}
    - final-root 下同 family 已发布 *__with_skill 任务

    当前 task:
    - ${plan.derivedTaskId} (${buildTaskDisplayName(plan)}) -> ${draftDirLabel}
    - 当前只审这个 task 的当前 attempt；历史 attempt 和其他未发布草稿都不属于当前上下文。

    历史任务去重主要由 planner/writer 负责；reviewer 不需要逐项复审已发布任务。
    只有当前 draft 明显复制已发布 *__with_skill 任务的场景、输入资产、输出契约和 verifier 策略时，才作为 blocking 问题指出。
    不要把历史 attempt、未发布草稿或 *__no_skill 对照副本作为正式去重基准。

    审查目标:
    - 只判断当前 task 是否存在 blocking 问题；下面任一项不满足，都必须判定 blockingPass=false：
      - 英文与内部实现: instruction.md、task.toml 的 metadata.name 和 metadata.description 必须全英文；instruction.md 不得暴露内部实现、oracle、verifier 或可直接照搬的答案捷径。
      - injected skills: ${draftDirLabel}environment/skills/ 必须与 input_skills/ 一致；writer 不应改写 injected skill payload，不得修改、删除、重排或增补。
      - task.toml: 必须显式包含 [environment].build_timeout_sec、[agent].timeout_sec、[verifier].timeout_sec。
      - verifier reward: tests/test.sh 必须先 mkdir -p /logs/verifier，并在所有通过/失败/异常路径稳定写出 /logs/verifier/reward.txt 或 reward.json；不得因 set -e/pipefail、裸跑测试或提前退出导致 reward 缺失。
      - solver 与 skill 解耦: solution/solve.sh 是否像真实 solver 一样基于输入资产、任务规则和公开依赖推导答案；solution/solve.sh、tests/test.sh、tests/test_outputs.py 不得硬依赖 environment/skills/**、/root/.codex/skills/**、/app/skills/** 或其他 skill 安装路径。
      - 未修改的初始 environment 如果可以通过 verifier，直接判定为 blocking 问题；任务必须要求 solver 产生实际修改或输出。
      - verifier 契约: verifier 必须清晰区分主测试和防作弊测试；只能检查 instruction.md 明确说明或可直接推出的结果语义，不得测试未承诺实现细节、固定措辞/关键词/同义词集合，除非题面明确要求；防作弊测试只能拦截 shortcut，不得新增 hidden requirement。
      - 路径与写入目录: solution/solve.sh、tests/test.sh、tests/test_outputs.py、environment/Dockerfile 的路径契约必须一致；运行时写入目录必须显式创建。
      - Dockerfile: 必须显式声明 WORKDIR；若 WORKDIR 不是 /root，脚本路径仍须一致；FROM 不得使用私有/本地或未允许 registry；不得使用 COPY . /root、ADD . /root 或同类宽泛复制；不得把 skills 复制到 /root/environment/skills、/app/skills、/workspace/skills 等普通运行时路径。

    返回格式要求:
    - taskResults 中只返回当前这个任务
    - taskResults[].blockingPass=false 表示该任务存在 blocking 问题
    - blockingIssues 写出你审查以后发现的具体问题

    返回严格符合 schema 的 JSON，不要输出额外解释。
  `);
}

export function buildRepairPrompt(args: {
  unit: GenerationUnit;
  plan: DerivedTaskPlan;
  draftDirLabel?: string;
  blockingIssues: string[];
  staticIssues: string[];
  runtimeIssues: string[];
  skillEffectIssues: string[];
  runtimeDir?: string;
  runtimeLogRoot?: string;
  runtimeLogIndexPath?: string;
  runtimeLogPath?: string;
  runtimeResultPath?: string;
  jobLogPath?: string;
  trialLogPath?: string;
  verifierStdoutPath?: string;
  rewardPath?: string;
  artifactManifestPath?: string;
  skillEffectEvidenceRoot?: string;
  skillEffectResultPath?: string;
  skillEffectBucket?: string;
}): string {
  const draftDirLabel = args.draftDirLabel ?? "draft/";
  const blockingBlock =
    args.blockingIssues.length > 0
      ? args.blockingIssues.map((issue) => `- ${issue}`).join("\n")
      : "- 无 blocking reviewer 问题";
  const staticBlock =
    args.staticIssues.length > 0
      ? args.staticIssues.map((issue) => `- ${issue}`).join("\n")
      : "- 无 static 问题";
  const runtimeBlock =
    args.runtimeIssues.length > 0
      ? args.runtimeIssues.map((issue) => `- ${issue}`).join("\n")
      : "- 无 runtime 问题";
  const skillEffectBlock =
    args.skillEffectIssues.length > 0
      ? args.skillEffectIssues.map((issue) => `- ${issue}`).join("\n")
      : "- 无 skill-effect 问题";

  return dedent(`
    你正在修复一个 Harbor task 草稿。

    当前只允许修改本 attempt 的 ${draftDirLabel} 内的文件，不要修改 template_source/、input_skills/、artifacts/、family workspace 根目录、历史 attempt、Harbor 仓库代码，也不要修改 environment/skills/ 下 injected skill 的内容。

    当前 task blueprint:
    ${JSON.stringify(args.plan, null, 2)}

    当前问题:
    blocking reviewer:
    ${blockingBlock}

    static:
    ${staticBlock}

    runtime:
    ${runtimeBlock}

    skill-effect:
    ${skillEffectBlock}

    你还可以读取这些本 attempt 的运行证据:
    - Oracle runtime evidence root: ${args.runtimeLogRoot ?? args.runtimeDir ?? "当前没有 Oracle runtime evidence root"}
    - 日志索引: ${args.runtimeLogIndexPath ?? "当前没有 log-index.json"}
    - Oracle 日志: ${args.runtimeLogPath ?? "当前没有 runtime log"}
    - Oracle 结果 JSON: ${args.runtimeResultPath ?? "当前没有 result.json"}
    - Harbor job 日志: ${args.jobLogPath ?? "当前没有 job.log"}
    - trial 日志: ${args.trialLogPath ?? "当前没有 trial.log"}
    - verifier 输出: ${args.verifierStdoutPath ?? "当前没有 verifier/test-stdout.txt"}
    - reward 文件: ${args.rewardPath ?? "当前没有 reward.txt/reward.json"}
    - artifacts manifest: ${args.artifactManifestPath ?? "当前没有 artifacts/manifest.json"}
    - Skill-effect evidence root: ${args.skillEffectEvidenceRoot ?? "当前没有 skill-effect evidence root"}
    - skill-effect 总结 JSON: ${args.skillEffectResultPath ?? "当前没有 skill-effect result json"}
    - skill-effect bucket: ${args.skillEffectBucket ?? "当前没有 skill-effect bucket"}

    修复要求:
    - 必须保留 plan.json，不要删除。
    - instruction.md、task.toml 的 metadata.name、metadata.description 必须保持英文，不要写中文任务描述。
    - 如果 task.toml 缺少 [environment].build_timeout_sec、[agent].timeout_sec 或 [verifier].timeout_sec，必须补齐；秒数根据 template_source/task.toml、当前任务复杂度和测试耗时合理设置，不要依赖 Harbor 默认值。
    - 不要修改 environment/skills/ 下 injected skill payload；如果需要调整 skill 使用方式，应通过题目本身、输入资产、tests 修正，而不是改 skill 内容。
    - 如果 solution/solve.sh 或 tests/** 直接调用 skill 模块，必须去耦：把最小必需逻辑搬到任务自身代码里；最终参考解与 verifier 在有 skill / 无 skill 两种评测设置都要能运行。
    - 修复 solution/solve.sh 时，必须像真实 solver 一样，基于输入资产、任务规则和公开依赖推导可通过测试的结果。
    - 未修改的初始 workspace 必须仍然不能通过 verifier；不要通过降低 verifier 或预置答案让空跑通过。
    - 修复 instruction.md 时必须保持简洁的用户题面结构：Brief opening, Input data, Your task, Output, Notes；不要改成教程式解法，也不要暴露 verifier/test/solution/task.toml/logs、shipped skill payload、installed skill path 或内部 task package 细节。
    - 如果问题是已发布 *__with_skill sibling / 历史任务过近，必须实质调整任务场景、输入资产、输出语义或 verifier 判定方式，不要只换领域名词。
    - verifier 必须继续保持主测试和防作弊测试两部分的清晰分工；修复时不要把它们重新混成一个难以解释的大测试。
    - 修复 verifier 主测试时，只能断言 instruction.md 明确写出的用户可见契约；字段、端点、文件路径、状态码、schema 名称和输出结构如果被测试要求，必须已在 instruction.md 中说明。
    - 修复防作弊测试时，只能检测硬编码、fixture 过拟合或 shortcut 行为，不得引入主任务契约之外的新功能要求。
    - 如果当前任务的主输出是自由文本，而 tests/test_outputs.py 依赖固定关键词、固定短语、固定同义词集合或唯一措辞，只有 instruction.md 已明确要输出固定关键词、固定短语、固定同义词集合或唯一措辞，才允许保留这种检查。
    - 如果需要修改 environment/Dockerfile，请继续满足下面这些 Dockerfile 契约：
    ${renderDockerfileRules()}
    - 如果需要修改 environment/Dockerfile，FROM 不得使用私有/本地 registry，或未允许的 registry。
    - 你应把完整日志目录或阶段 evidence root 当作主入口，自由递归读取相关证据，而不是只盯住某一个摘要文件。需要具体 result、reward 或 trajectory 时，从对应 evidence root 下递归查找 log-index.json、result.json、with_skill/、no_skill/ 和 variants/。
    - skill-effect 修复必须先按 bucket 分类：
      1. with_skill pass / no_skill pass：优先判断任务是否太简单、verifier 是否没有检查 skill 关键工作流、no_skill 是否仍有 shortcut 或残留 skill 线索。
      2. with_skill fail / no_skill pass：这是反向劣势，优先检查 skill 工作流是否被题面/输入/测试误导，verifier 是否过拟合 no-skill 输出，或 with_skill 是否遇到 runtime/budget/path 问题。
      3. with_skill fail / no_skill fail：优先按任务不可用处理，检查 runtime、verifier、题面可执行性、输入资产完整性。
      4. with_skill pass / no_skill invalid fail：不要直接接受，优先检查 no_skill 变体构造、runtime、verifier 稳定性，确保 no_skill 是有效 reward 失败而不是无效失败。
    - 不要为了保留过窄测试而把 hidden requirement 硬塞进 instruction.md；优先让 verifier 回到 instruction.md 已承诺的用户可见契约。只有确实属于必要用户契约时，才同步修改 instruction.md 和 verifier。
    - 返回 JSON 时，summary 只简短说明你修了什么，不要复述原因。
    - 返回 JSON 时，repairReason 要详细说明为什么这轮需要修，必须基于当前问题和你读到的证据来写，不能空泛。
    - repairReason 必须写出本轮最关键的问题，以及为什么本轮改动是在针对这个根因。

    完成修改后，返回严格 JSON:
    {
      "summary": "简短说明你修了什么",
      "repairReason": "详细说明为什么这轮需要修、看到了什么证据、为什么决定这样改",
      "changedFiles": ["相对路径1", "相对路径2"]
    }
  `);
}

export function relativeDraftPath(derivedTaskId: string): string {
  return path.posix.join("drafts", derivedTaskId);
}
