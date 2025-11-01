# Project Quality Hub — 设计说明

该 MCP 服务将项目知识图谱、分支管理、智能增量更新与质量评分能力统一包装，并通过 stdio 与 MCP 客户端通信。核心组件如下：

## 架构
- `core`: 项目分析、记忆与监控逻辑。
- `quality`: AST 解析、静态分析和评分算法。
- `server`: MCP 服务器、工具定义、任务管理。

服务器启动后维持一个共享 `MCPServerContext`：
- 单例的 `EnhancedProjectMindInterface` 用于项目/分支分析。
- `SmartIncrementalUpdater` 与 `watchdog` 协作实现文件监控。
- `QualityAnalyzer`、`MultiLanguageStaticAnalyzer` 与 `IntelligentQualityScorer` 负责质量评分。
- `TaskRegistry` + `ThreadPoolExecutor` 负责跟踪长耗时任务。

## 工具清单
| 工具 | 功能 | 返回 |
| --- | --- | --- |
| `analyze_project` | 触发全量分析（后台任务） | `task_id` |
| `get_project_summary` | 汇总项目摘要、分支信息、监控状态 | 摘要字典 |
| `list_branches` / `analyze_branch` / `switch_branch` | 分支列表/分析/切换 | 分支状态 |
| `compare_branches` | 两分支差异 | 差异概览 |
| `start_monitoring` / `stop_monitoring` / `get_monitoring_status` | 控制或查询监控 | 状态字典 |
| `score_project` / `score_file` | 计算质量评分 | 平均分或单文件详情 |
| `get_task_result` / `list_tasks` | 查询任务状态 | 任务快照 |

## 任务管理
- 所有阻塞操作通过 `TaskRegistry` 调度至线程池。
- 每个任务都会记录状态、开始/结束时间、结果或错误信息。
- 客户端通过 `get_task_result` / `list_tasks` 轮询。

## 错误与日志
- 使用标准 `logging`，默认 INFO，可通过环境变量覆盖。
- 所有异常都会被捕获并记录，同时返回结构化错误。

## 依赖
- `mcp`：MCP 协议实现。
- `watchdog`：实时文件监控。
- `networkx`：依赖关系图谱管理。

## 推荐开发流程
1. 通过 `score_project` 和 `analyze_project` 测试一轮核心功能。
2. 在真实项目仓库上启用 `start_monitoring`，观察增量更新。
3. 根据需要扩展工具（如影响分析、改进建议）。
