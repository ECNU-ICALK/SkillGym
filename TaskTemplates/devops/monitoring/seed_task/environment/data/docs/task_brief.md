# Harbor Monitoring Bundle Brief

本次交付对象是一个 Harbor 风格服务集合的监控配置包。

交付约束：

- 交付批次为 `release-2026-05-monitoring`
- 结果必须覆盖 `harbor-core`、`harbor-jobservice`、`harbor-registry`、`harbor-exporter`
- 输出摘要必须包含请求量、错误率、p95 延迟和状态分级
- 监控配置应保持 inventory 驱动，因为同一批次下可能追加新的 inventory 文件
- 正式摘要范围除了批次标识外，还要遵守摘要合同中的范围标签；同一批次目录里可能同时存在辅助观测目标，它们可以保留在 inventory 中，但不能进入本次正式 bundle 的正式采集集合或摘要覆盖范围
- 同一个合同服务在 inventory 中可能拆成多个 target 条目，但最终摘要和服务级规则仍应按服务口径聚合
- 服务级规则与摘要复用路径需要继续保留 `bundle`、`lane`、`service` 这组范围维度，避免后续汇总时丢失正式交付范围
- inventory 条目里还带有目标级抓取传输字段；当前 bundle 与后续新增 manifest 都要继续按这些字段完成抓取，而且同一 inventory 目录后续可能出现不同受支持格式的 manifest 文件
- 输出 JSON 中的 `healthy_target_count` 按正式摘要里当前已纳入并可汇总的 distinct 服务数填写；即使某个服务拆成多个 target，也不要把它们分别累计，而且 page/ticket 状态的服务只要当前可抓取可汇总也应计入
- 结果必须通过环境中已有控制脚本产出

限制说明：

- 不要改动 `/app/data/` 下的输入文件
- 不要改成其它监控系统
- 不要用手工计算结果替代当前交付方式
- 保留现有服务名称和批次标识
