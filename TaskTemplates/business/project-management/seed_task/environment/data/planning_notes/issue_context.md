# Supavisor Sprint Planning Notes

本目录整理自 `supabase/supavisor` 公开 issue backlog，并补充了本次 Sprint 规划时需要关注的业务背景。

## 主题

- 本次 Sprint 聚焦连接稳定性、网络访问控制和代理链路可靠性。
- `must_ship` 项主要覆盖网络限制、连接收包错误和客户端应用名透传。
- 高优先级但未就绪或受阻的项需要在本轮计划里明确解释，不允许直接忽略。

## 归一化 issue 摘要

- `SV-236` Support network restrictions  
  来源：https://github.com/supabase/supavisor/issues/236  
  背景：租户网络访问限制是下游多个网络链路改造的前提。

- `SV-320` Handle Receive query error  
  来源：https://github.com/supabase/supavisor/issues/320  
  背景：收包错误直接影响连接稳定性，是本轮必须压住的故障类问题。

- `SV-343` Prepend application_name from client to application_name set by DbHandler only in session mode  
  来源：https://github.com/supabase/supavisor/issues/343  
  背景：需要保留客户端应用名，便于排查和链路审计。

- `SV-204` Add PROXY protocol support  
  来源：https://github.com/supabase/supavisor/issues/204  
  背景：需要在网络限制工作完成后接入真实客户端来源信息。

- `SV-349` Naive proxy from client to owner node  
  来源：https://github.com/supabase/supavisor/issues/349  
  背景：与代理链路演进相关，但依赖上游代理协议支持。

- `SV-331` Supabase IP Ban Issue with Connection Pooling  
  来源：https://github.com/supabase/supavisor/issues/331  
  背景：用户侧反馈强烈，但可以作为次于 must-ship 工作的插入项。

- `SV-314` Failed to connect using interval private network Postgres  
  来源：https://github.com/supabase/supavisor/issues/314  
  背景：与网络访问控制主题相关，但 QA 成本偏高。

- `SV-221` Don't start all pool connections immediately  
  来源：https://github.com/supabase/supavisor/issues/221  
  背景：仍缺少必要的测试结论，当前不适合承诺。

- `SV-209` Option to set a log level on a client connection  
  来源：https://github.com/supabase/supavisor/issues/209  
  背景：运维可观测性改进，价值明确但优先级低于当前稳定性主题。

- `SV-163` Read replica support  
  来源：https://github.com/supabase/supavisor/issues/163  
  背景：范围较大，本轮如果进入承诺会明显挤压稳定性 workstream。

- `SV-319` Supavisor brings down infrastructure after role modification  
  来源：https://github.com/supabase/supavisor/issues/319  
  背景：严重度高，但当前存在未解除 blocker。

- `SV-830` Supavisor memory usage gradually reaches 100%  
  来源：https://github.com/supabase/supavisor/issues/830  
  背景：已关闭，不应再进入当前 Sprint 承诺。

- `SV-854` Fails to connect when a startup parameter has an empty value  
  来源：https://github.com/supabase/supavisor/issues/854  
  背景：已关闭，不应再进入当前 Sprint 承诺。
