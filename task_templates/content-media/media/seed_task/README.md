# Media Template

这是面向 `media` 类 skill 的模板。它综合参考 SkillsMP media 类热门 skill 的共性能力：本地视频帧抽取、短预览导出、接近像素级核对、批量交付收口、以及围绕素材一致性的结构化整理。

## 第一部分：任务设计参考

* **Skill 价值定位**：`media` 类热门 skill 的共同价值，是把本地视频、帧级定位、预览片段和交付清单串成一条可复查的生产链路。模板任务应让 skill 在素材定位、输出组织、顺序约束和交付闭环上体现价值，同时把实现细节留在环境里处理。
* **Verifier 设计重点**：Verifier 应优先验证输出是否能从输入稳定重建，而不是只检查文案或单个文件存在。重点应覆盖源视频映射、still / preview / sheet 的数量与顺序、尺寸与时间点一致性、JSON 结构闭环、输入不可变和输出清洁度。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`media__mission_pick_bundle`
- 类别：`media`
- 绑定 Skill：`video-frames`
- 输入数据参考来源：
  - `environment/mission_packet/clip_manifest.json`：任务内 clip 注册表
  - `environment/mission_packet/shot_requests.csv`：任务内 still / preview 请求表
  - `environment/mission_packet/layout_spec.json`：任务内 contact sheet 布局表
  - `environment/mission_packet/videos/launch_pad.mp4`：任务内 launch 序列源视频  
    【https://svs.gsfc.nasa.gov/13946/】
  - `environment/mission_packet/videos/landing_targeting.mp4`：任务内 tracking 序列源视频  
    【https://svs.gsfc.nasa.gov/14724/】
  - `environment/mission_packet/videos/landing_touchdown.mp4`：任务内 touchdown 序列源视频  
    【https://svs.gsfc.nasa.gov/14724/】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier 策略：

主测试

| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| 输出文件与 schema | 检查 still、preview、sheet、`frame_index.json`、`delivery_report.json` 是否齐全且可解析 | 结构化交付与清单闭环 |
| still 语义 | 逐条复算 still 截帧结果，检查尺寸与 locator 对应关系 | 帧级定位与素材核对 |
| helper 接入 | 在覆写 `MEDIA_PICK_FRAME_TOOL` 时检查 still 生成是否逐条走本地 helper | 工具接入与动作路径收敛 |
| preview 起点 | 逐条复算 preview 首帧，检查是否从指定时间点开始 | 时间点截取与导出一致性 |
| sheet 顺序 | 检查每个 sheet 的分组、顺序、画布尺寸和拼接位置 | 批量整理与版式约束 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 输入不可变 | 检查 mission packet 是否被改动 |
| 输出范围 | 检查 `/app/output` 是否只留下规定产物 |
| 占位清理 | 检查输出中是否混入 `TODO`、`TBD`、process residue 等内容 |
| 空 locator | 检查空 `still_locator` 是否仍然生成有效 still |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把本地视频帧抽取、短预览导出和 contact sheet 组装收成稳定流水线，从而降低顺序错乱、尺寸不一致和交付清单漏项的风险。without skill 更容易在 helper 对接、顺序组织和输出收口上出错；with skill 则更容易把生成结果一次性收敛到 verifier 需要的形态。

基于最近 **3** 次有效对照实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3 (0%)` | `3/3 (100%)` | without Skill 更容易卡在 helper 对接、动作顺序和输出收口；with Skill 三次都完成交付闭环。 |
| Agent 执行耗时 | `345.1s` | `253.6s` | With Skill 的平均耗时降低约 `26.5%`。 |
| Tokens | `1.12M` | `0.59M` | Without Skill 的 token 开销约为 With Skill 的 `1.88x`。 |

本示例任务的当前对照中，with_skill 试验 `task_with_skills_e2b__vXUedVH` 通过；without_skill 试验 `task_without_skills_e2b__r5rDM26` 在主测试里的 helper 接入项失败，差异集中在 helper 对接与动作选择层面。

## 📁 标准目录结构说明

```text
seed_task/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── mission_packet/
│   ├── workspace/
│   └── skills/
├── tests/
└── solution/
```
