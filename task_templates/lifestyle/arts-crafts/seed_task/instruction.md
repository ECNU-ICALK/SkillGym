你在为一个社区纤维手作工作坊整理 3D 打印工具包。相关资料和交付约束已整理在工作区，现在需要一套可直接交给打印供应商的模型包与登记材料。

输入数据在：

- `/root/environment/data/brief/`：工作坊用途、槽位说明、尺寸与交付约束
- `/root/environment/data/catalog/`：候选模型清单、查询提示和模型资料摘要
- `/root/environment/data/policy/`：许可规则、热度门槛、槽位覆盖要求和命名约束

你的任务

1、从候选模型中选出 3 个模型，分别覆盖 `yarn-management`、`stitch-marker`、`tool-storage` 这 3 个槽位，并满足题面给出的筛选与许可要求。  
2、为每个入选模型准备完整的交付目录，保留模型文件、来源信息、作者信息、许可信息和文件校验信息，确保打印供应商能够直接接收。  
3、输出一份 bundle 级汇总，说明每个槽位的选型结果、规则核对情况，以及本轮仍需人工确认的事项。

输出：

如 `/root/answer` 不存在，请先创建该目录。所有交付物都写入 `/root/answer/`，且仅保留以下结果：

- `/root/answer/models/`
  - 必须包含且只包含这 3 个槽位目录：`yarn-management`、`stitch-marker`、`tool-storage`
  - 每个槽位目录下必须包含 `source_bundle.zip`、`source_manifest.json`、`files/` 和 1 个 `model_record.json`
  - `source_bundle.zip` 需要保留原始来源文件包
  - `source_manifest.json` 需要保留来源页、作者、许可和来源文件记录
  - `files/` 目录下只放该模型展开后的可打印文件
  - 每个 `model_record.json` 至少需要包含这些顶层键：`model_id`、`model_name`、`author`、`source_url`、`license_id`、`files`
  - `files` 数组中的每个对象至少需要包含：`path`、`sha256`

- `/root/answer/bundle_manifest.json`
  - 必须包含顶层键：`bundle_name`、`slot_order`、`selections`、`policy_summary`、`manual_checks`
  - `slot_order` 必须固定为 `["yarn-management", "stitch-marker", "tool-storage"]`
  - `selections` 必须覆盖 3 个槽位；每个对象至少包含：`slot_id`、`model_id`、`model_name`、`author`、`source_url`、`license_id`、`local_dir`、`policy_checks`
  - `policy_checks` 至少包含：`slot_match`、`license_allowed`、`popularity_ok`、`files_present`

- `/root/answer/selection_audit.json`
  - 必须包含顶层键：`source_endpoint`、`source_checked`、`model_ids_checked`、`records_prepared`、`notes`
  - `source_checked` 只能为 `true` 或 `false`；正式结果必须为 `true`

- `/root/answer/selection_report.md`
  - 第一行写 1 句本次 bundle 建议
  - 之后必须按槽位写 3 个二级标题：`## yarn-management`、`## stitch-marker`、`## tool-storage`
  - 每个槽位小节都要写入选模型名、入选理由、许可与交付注意点

说明：

- 请仅依据任务提供的资料完成本次整理。
- 本地来源服务可补充模型信息并提供文件获取入口。
- 入选模型的来源、作者、许可、热度和交付文件需要保持可复核。
- 请保持任务提供资料与环境内容完整，不要改动非交付结果文件。
- 交付内容需完整、可核对，并与所选模型一致。
- 不要更换槽位集合，不要把多个槽位合并到同一个目录，也不要把同一模型重复用于多个槽位。
- 最终交付物只保留 `/root/answer/` 下要求的文件和目录。
