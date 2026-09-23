你需要接管一个未完成的 Debian Security 镜像摘要发布任务，并沿着现有运维控制台的真实链路把它发布完成。

输入数据在 `/app/data/`：
- `upstream/`：归档的 Debian Security snapshot 元数据，包括 `InRelease` 和 `Packages.xz`
- `incident/incident_notes.md`：故障说明、业务约束和交付要求
- `incident/tracked_packages.json`：最终摘要中必须覆盖的重点包列表

你的任务
1. 排查当前恢复链路为什么没有完成发布，并在不替换现有链路的前提下完成这次恢复。
2. 接管容器里已经存在的运维控制台恢复现场，完成本地摘要发布。发布完成后需要保证运行链路处于健康状态。
3. 将最终结果写入 `/app/output/recovery_report.json`，格式如下：

```json
{
  "snapshot_id": "<snapshot timestamp>",
  "suite": "bookworm-security",
  "component": "main",
  "architecture": "amd64",
  "published": true,
  "package_count": 0,
  "tracked_packages": {
    "<package-name>": "<version>"
  },
  "digest_sha256": "<sha256 of published digest>"
}
```

输出：
- 只需要提交 `/app/output/recovery_report.json`
- JSON 必须为有效 UTF-8，字段名必须与上面的合同一致
- `tracked_packages` 必须覆盖 `tracked_packages.json` 中列出的全部包名

说明：
- 必须使用容器中已经存在的真实恢复链路和运维控制台，不能用替代脚本、临时 mock、手写最终输出或跳过发布步骤。
- 不要重建一条新的恢复链路来绕开现有恢复现场。
- 明确禁止通过删除、停用、短路或改写现有功能来规避问题。
- 不要修改 `/app/data/upstream/` 中的输入数据，也不要伪造日志、校验结果或已发布产物。
- 可以读取日志、状态文件和运行时目录；除 JSON 合同外，不要求额外的输出格式。

Reference data:
- https://snapshot.debian.org/archive/debian-security/20240311T000000Z/dists/bookworm-security/InRelease
- https://snapshot.debian.org/archive/debian-security/20240311T000000Z/dists/bookworm-security/main/binary-amd64/Packages.xz
