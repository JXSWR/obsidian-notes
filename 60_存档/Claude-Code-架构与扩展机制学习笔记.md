# Claude Code 架构与扩展机制学习笔记

> 来源：Anthropic 官方文档（`code.claude.com/docs`、`anthropic.com/engineering/claude-code-best-practices`）
> 整理时间：2026-07-21
> 定位：从「会用 Claude Code」到「理解架构 + 能扩展」的系统性学习笔记

---

## 目录

- [一、核心架构](#一核心架构)
  - [1.1 代理循环（Agentic Loop）](#11-代理循环agentic-loop)
  - [1.2 模型 + 工具](#12-模型--工具)
  - [1.3 Claude 可以访问什么](#13-claude-可以访问什么)
  - [1.4 执行环境与界面](#14-执行环境与界面)
  - [1.5 会话机制](#15-会话机制)
  - [1.6 上下文窗口管理](#16-上下文窗口管理)
  - [1.7 检查点与权限](#17-检查点与权限)
- [二、五种扩展机制](#二五种扩展机制)
  - [2.1 Skills（技能）](#21-skills技能)
  - [2.2 Subagents（子代理）](#22-subagents子代理)
  - [2.3 Hooks（钩子）](#23-hooks钩子)
  - [2.4 MCP（模型上下文协议）](#24-mcp模型上下文协议)
  - [2.5 Plugins（插件）](#25-plugins插件)
  - [2.6 五种机制对比与选择指南](#26-五种机制对比与选择指南)
- [三、最佳实践](#三最佳实践)
  - [3.1 给 Claude 验证工作的方式](#31-给-claude-验证工作的方式)
  - [3.2 先探索，再计划，再编码](#32-先探索再计划再编码)
  - [3.3 在提示中提供具体上下文](#33-在提示中提供具体上下文)
  - [3.4 配置你的环境](#34-配置你的环境)
  - [3.5 有效沟通](#35-有效沟通)
  - [3.6 管理你的会话](#36-管理你的会话)
  - [3.7 自动化和扩展](#37-自动化和扩展)
  - [3.8 避免常见失败模式](#38-避免常见失败模式)
- [四、核心架构图](#四核心架构图)
- [五、官方资源索引](#五官方资源索引)

---

## 一、核心架构

### 1.1 代理循环（Agentic Loop）

当 Claude 接到任务时，会经历三个阶段：

1. **收集上下文（Gather Context）**
2. **采取行动（Take Action）**
3. **验证结果（Verify Results）**

这三个阶段是**融合**的，不是线性的。Claude 始终在用工具——搜文件、改代码、跑测试都是工具调用。

**循环的自适应性：**
- 关于代码库的问题 → 可能只需要「收集上下文」
- 修 bug → 三阶段循环多次
- 重构 → 大量「验证结果」

Claude 会根据上一步学到的内容决定下一步做什么，把数十个操作串起来，沿途纠错。

**用户的参与：**
- 任何时刻都可中断、引导、提供额外上下文
- Claude 自主工作，但对你的输入保持响应

**驱动组件：**
- **模型**：负责推理
- **工具**：负责行动
- Claude Code 本身是「代理框架（Agent Harness）」——提供工具、上下文管理和执行环境，把语言模型变成能干活的代理

---

### 1.2 模型 + 工具

#### 模型

| 模型 | 适用场景 |
|------|---------|
| **Sonnet** | 大多数编码任务 |
| **Opus** | 复杂架构决策，更强的推理能力 |

切换：会话中用 `/model`，启动时用 `claude --model <name>`

> 文档说「Claude 选择 / 决定」时，指的就是模型在推理。

#### 工具

工具是让 Claude 成为「代理」的关键。**没有工具，Claude 只能回文本；有了工具，Claude 能采取行动。** 每次工具调用都会返回信息，反馈进循环，决定下一步。

#### 内置工具五大类别

| 类别 | 能做什么 |
|------|---------|
| **文件操作** | 读取、编辑、创建、重命名、重组文件 |
| **搜索** | 按模式找文件、正则搜索内容、探索代码库 |
| **执行** | 跑 shell 命令、启动服务器、跑测试、用 git |
| **网络** | 搜索网络、抓文档、查错误信息 |
| **代码智能** | 编辑后看类型错误/警告、跳定义、查引用（需插件） |

**工具选择示例——「修一个失败的测试」：**
1. 跑测试套件 → 看哪些挂了
2. 读错误输出
3. 搜相关源文件
4. 读文件理解代码
5. 改文件修复
6. 再跑测试验证

每一步都给 Claude 新信息，决定下一步——这就是代理循环在运作。

---

### 1.3 Claude 可以访问什么

在目录里跑 `claude` 后，Claude Code 可以访问：

- **你的项目**：目录和子目录下的所有文件
- **你的终端**：任何你能跑的命令（构建、git、包管理器、脚本）
- **你的 git 状态**：当前分支、未提交变更、提交历史
- **你的 CLAUDE.md**：项目特定的指令、约定、上下文
- **自动内存（Auto Memory）**：Claude 自动保存的学习内容。`MEMORY.md` 前 200 行或 25KB（先到者为准）每次会话开头加载
- **你配置的扩展**：MCP servers、Skills、Subagents、Claude in Chrome

> 因为 Claude 看到整个项目，它可以**跨文件工作**——搜索 → 读取多个文件 → 跨文件协调编辑 → 跑测试验证 → 提交。这跟只看当前文件的内联补全完全不同。

---

### 1.4 执行环境与界面

#### 三种执行环境

| 环境 | 代码运行位置 | 用例 |
|------|------------|------|
| **本地（Local）** | 你的机器 | 默认。完全访问文件、工具、环境 |
| **云（Cloud）** | Anthropic 管理的 VM | 卸载任务、处理本地没有的仓库 |
| **远程控制（Remote Control）** | 你的机器，浏览器控制 | 用 Web UI，但一切仍在本地 |

#### 多种界面

终端、桌面应用、IDE 扩展（VS Code / JetBrains）、`claude.ai/code`、远程控制、Slack、CI/CD 管道。

> **关键认知**：界面只决定你怎么交互，底层的代理循环在所有界面都是同一套。

---

### 1.5 会话机制

#### 会话存储

- 对话保存在本地 `~/.claude/projects/` 下的纯文本 JSONL 文件
- 每条消息、每次工具调用、每个结果都记录在案
- 支持回退、恢复、分叉会话
- Claude 在改代码前会先对受影响文件**快照**

#### 会话独立性

- 每个新会话从新的上下文窗口开始，**没有之前的对话历史**
- 跨会话的「记忆」靠：自动内存 + CLAUDE.md
- 可以在 CLAUDE.md 里加持久规则

#### 跨分支工作

- 每个对话绑定当前目录
- 切分支时：Claude 看到新分支的文件，但对话历史保持不变
- 用 `git worktrees` 可以跑多个并行 Claude 会话，互不干扰

#### 恢复与分叉

| 操作 | 命令 | 行为 |
|------|------|------|
| **恢复** | `claude --continue` 或 `claude --resume` | 同一会话 ID 继续，新消息追加 |
| **分叉** | `--fork-session` 或 `/branch` | 复制历史到新会话 ID，原会话不变 |

> 多个终端恢复同一会话：消息会交错写入，对话变乱。并行工作请用 `--fork-session` 给每个终端独立会话。

---

### 1.6 上下文窗口管理

**这是 Claude Code 最重要的资源。** 大多数最佳实践都围绕这个约束展开。

#### 上下文窗口装着什么

对话历史、文件内容、命令输出、CLAUDE.md、自动内存、加载的 skills、系统说明。

#### 当上下文填满时

Claude Code 会自动管理：
1. 先清除较旧的工具输出
2. 必要时总结对话
3. 请求和关键代码片段被保留；早期详细指令可能丢失

#### 管理策略

- **持久规则放 CLAUDE.md**，不要依赖对话历史
- 在 CLAUDE.md 里加「Compact Instructions」部分
- 用 `/compact <focus>` 精准压缩，如 `/compact focus on the API changes`
- 用 `/context` 看什么在占空间
- 用 `/mcp` 查每个 MCP server 的上下文成本

**抖动保护**：如果单个文件或工具输出太大，导致每次总结后上下文立即重新填满，Claude Code 会在几次尝试后停止自动压缩并报错。

#### 用 Skills 和 Subagents 管理上下文

| 机制 | 如何省上下文 |
|------|------------|
| **Skills** | 按需加载。会话开始只看到描述，完整内容仅在使用时加载。`disable-model-invocation: true` 可让描述都不进上下文 |
| **Subagents** | 在独立新上下文里跑，工作不污染主对话，完成后只返回摘要。这是长会话的关键武器 |

---

### 1.7 检查点与权限

#### 检查点（Checkpoints）—— 撤销文件变更

- **每个文件编辑都可逆**
- Claude 编辑前会快照当前内容
- 按两次 `Esc` 回退，或让 Claude 撤销
- 检查点独立于 git，恢复会话时仍可用
- **只覆盖文件变更**；影响远程系统的操作（数据库、API、部署）无法 checkpoint——所以 Claude 在跑有外部副作用的命令前会问你

#### 权限模式（`Shift+Tab` 循环切换）

| 模式 | 行为 |
|------|------|
| **Manual** | 文件编辑和 shell 命令前都问 |
| **Accept Edits** | 自动编辑文件 + 常见文件系统命令（mkdir、mv），其他命令仍问 |
| **Plan** | 只读工具，提出计划不修改源文件 |
| **Auto** | 后台安全检查评估所有操作 |

也可以在 `.claude/settings.json` 里把特定命令（如 `npm test`、`git status`）加白名单，免每次询问。

---

## 二、五种扩展机制

Claude Code 的扩展性来自五个积木：**Skills、Subagents、Hooks、MCP、Plugins**。

### 2.1 Skills（技能）

#### 定义

通过创建 `SKILL.md` 文件扩展 Claude 的功能。文件包含 YAML frontmatter（元数据）+ Markdown 正文（指令说明）。Claude 在相关时自动用，或通过 `/skill-name` 直接调。

#### 核心特性

| 特性 | 说明 |
|------|------|
| **按需加载** | 正文仅在使用时加载，平时几乎不占上下文 |
| **调用控制** | `disable-model-invocation: true` 仅用户调；`user-invocable: false` 仅 Claude 调 |
| **工具预批准** | `allowed-tools` 在 skill 活动时免批准 |
| **工具限制** | `disallowed-tools` 在 skill 活动时移除特定工具 |
| **动态上下文注入** | `` !`command` `` 语法在发送前执行 shell，输出替换占位符 |
| **Subagent 执行** | `context: fork` 在隔离上下文跑，无法访问对话历史 |
| **参数传递** | `$ARGUMENTS`、`$N`、命名参数 |
| **实时变更** | 编辑 skill 文件在当前会话即时生效 |
| **支持文件** | 目录里可放模板、示例、脚本 |

#### 存储位置与作用范围

| 级别 | 路径 | 适用范围 |
|------|------|---------|
| 企业 | 托管设置 | 组织所有用户 |
| 个人 | `~/.claude/skills/<name>/SKILL.md` | 你的所有项目 |
| 项目 | `.claude/skills/<name>/SKILL.md` | 仅此项目 |
| 插件 | `<plugin>/skills/<name>/SKILL.md` | 启用插件处 |

优先级：企业 > 个人 > 项目 > 捆绑 skill。

#### 适用场景

- 反复粘贴相同的指令/检查清单/多步骤程序
- CLAUDE.md 的一部分演变成「程序」而非「事实」时，抽出来做 skill
- 按需加载的参考文档（API 规范、领域知识）
- 特定操作的分步指令（部署、提交、代码生成）
- 生成视觉输出（HTML 报告、依赖图）

#### 示例

```markdown
---
name: fix-issue
description: Fix a GitHub issue
disable-model-invocation: true
---
Analyze and fix the GitHub issue: $ARGUMENTS.

1. Use `gh issue view` to get the issue details
2. Understand the problem
3. Search the codebase for relevant files
4. Implement changes
5. Write and run tests
6. Ensure linting and type checking pass
7. Create a descriptive commit message
8. Push and create a PR
```

调用：`/fix-issue 1234`

---

### 2.2 Subagents（子代理）

#### 定义

在隔离上下文中执行任务的专门代理。Skills 通过 `context: fork` 可以在 subagent 中跑，此时 skill 内容变成驱动 subagent 的提示。

#### 内置代理类型

| 类型 | 特点 |
|------|------|
| **Explore** | 跳过 CLAUDE.md 和 git 状态，优化代码库探索，只读工具 |
| **Plan** | 跳过 CLAUDE.md 和 git 状态，保持上下文小 |
| **general-purpose** | 默认代理类型 |

#### 自定义子代理

在 `.claude/agents/` 下定义专门的助手，每个有自己的工具集和模型：

```markdown
---
name: security-reviewer
description: Reviews code for security vulnerabilities
tools: Read, Grep, Glob, Bash
model: opus
---
You are a senior security engineer. Review code for:
- Injection vulnerabilities (SQL, XSS, command injection)
- Authentication and authorization flaws
- Secrets or credentials in code
- Insecure data handling

Provide specific line references and suggested fixes.
```

调用：明确告诉 Claude「Use a subagent to review this code for security issues.」

#### 适用场景

- 需要隔离运行的研究任务（深度代码库探索）
- 需要特定执行环境（模型、工具、权限）
- 需要保持主对话上下文小

---

### 2.3 Hooks（钩子）

#### 定义

围绕工具事件自动化的工作流机制。在特定工具事件发生时自动执行脚本。

#### 与 Skills 的关键区别

| 维度 | Skills | Hooks |
|------|--------|-------|
| **本质** | 提示式指导（模型选择遵循） | 事件驱动确定性执行 |
| **保证** | 不一定每次都遵循 | 100% 发生 |
| **用途** | 工作流封装 | 强制行为（零例外） |

#### 适用场景

- skill 在第一个响应后停止影响行为时，用 hooks 强制
- 必须每次都发生的操作（格式化、lint、阻止写某些目录）
- 自动化测试、验证流程

#### 配置

在 `.claude/settings.json` 中配置，或让 Claude 帮你写：

```
Write a hook that runs eslint after every file edit
Write a hook that blocks writes to the migrations folder.
```

用 `/hooks` 浏览已配置的钩子。

---

### 2.4 MCP（模型上下文协议）

#### 定义

连接外部工具和数据源的协议。通过 MCP server，Claude 可以访问 Notion、Figma、数据库、GitHub、Slack 等。

#### 作用

- 提供外部工具和数据源连接
- 通过 `.mcp.json` 配置，可与 skill 捆绑
- 作为插件的一部分分发

#### 添加 MCP server

```bash
claude mcp add <server-name>
```

#### 适用场景

- 从 issue 跟踪器实现功能
- 查询数据库
- 分析监控数据
- 集成 Figma 设计
- 自动化工作流

#### 注意

- MCP 工具定义默认延迟加载，通过 tool search 按需载入
- 只有工具名占用上下文，直到 Claude 实际用某个工具
- 用 `/mcp` 检查每个 server 的成本

---

### 2.5 Plugins（插件）

#### 定义

打包和分发 skills + 其他扩展（agents、hooks、MCP、output-styles）的容器。在 skill 文件夹加 `.claude-plugin/plugin.json` 即可作为插件加载。

#### 核心特点

- **捆绑多种扩展**为一体
- 通过市场发现和安装预构建插件
- 使用命名空间 `plugin-name:skill-name` 避免冲突

#### 与 Skills 的区别

| 方面 | Skills | Plugins |
|------|--------|---------|
| **本质** | 单个功能扩展 | 扩展的打包容器 |
| **命名空间** | 可能冲突 | `plugin-name:skill-name`，不冲突 |
| **包含** | 指令 + 支持文件 | skills + agents + hooks + MCP + output-styles |
| **管理** | 文件系统或 `skillOverrides` | `/plugin` 命令 |
| **分发** | 手动 | 市场 |

#### 官方市场分类

| 类别 | 代表插件 |
|------|---------|
| **代码智能** | 各语言 LSP（Python、TypeScript、Rust、Go、Java 等） |
| **外部集成** | github、gitlab、jira、notion、figma、slack、sentry |
| **安全审查** | security-guidance |
| **开发工作流** | commit-commands、pr-review-toolkit、plugin-dev |
| **输出样式** | explanatory-output-style、learning-output-style |

#### 安装

```bash
/plugin install <name>@<marketplace>
# 例如
/plugin install github@claude-plugins-official
```

---

### 2.6 五种机制对比与选择指南

#### 核心对比表

| 机制 | 本质 | 触发方式 | 隔离性 | 主要用途 |
|------|------|---------|--------|---------|
| **Skills** | 提示式指令 | 自动或 `/name` | 默认内联，可 `fork` | 封装可复用工作流和知识 |
| **Subagents** | 隔离执行环境 | Skills 或 Claude 委派 | 完全隔离 | 独立上下文中执行任务 |
| **Hooks** | 事件驱动自动化 | 工具事件触发 | 依附 skill 生命周期 | 确定性强制行为 |
| **MCP** | 外部工具连接 | 工具调用 | N/A | 连接外部服务和数据源 |
| **Plugins** | 分发容器 | 安装后激活 | N/A | 打包和分发多种扩展 |

#### 按场景选择

| 场景 | 选什么 |
|------|-------|
| 封装可复用工作流 | **Skills** |
| 工作流需隔离运行，不污染主对话 | **Skills + Subagents**（`context: fork`） |
| 提示式指导不足以保证行为一致 | **Hooks** |
| 需连接外部服务/数据源 | **MCP** |
| 需将多种扩展一起分发 | **Plugins** |
| 组织范围内统一部署 | 企业级 Skills 或 Plugins |

#### 组合使用模式

```
Plugin（分发容器）
  ├── Skills（核心指令）
  │     ├── SKILL.md（主说明）
  │     ├── context: fork → Subagent（隔离执行）
  │     ├── hooks（确定性强制行为）
  │     ├── allowed-tools（工具预批准）
  │     └── .mcp.json（外部工具连接）
  ├── agents/（自定义子代理）
  ├── hooks/（全局钩子）
  └── output-styles/（输出样式）
```

#### 关键区别速记

1. **Skills vs CLAUDE.md**：Skills 按需加载，CLAUDE.md 始终在上下文。CLAUDE.md 演变成「程序」时就该抽成 skill。
2. **Skills vs Hooks**：Skills 是建议（模型选择遵循），Hooks 是强制（事件驱动确定性执行）。
3. **Skills vs Subagents**：Skills 默认内联（共享上下文），Subagents 隔离运行（无法访问对话历史）。
4. **Skills vs Plugins**：Skills 是单一功能，Plugins 是打包容器。
5. **Skills vs MCP**：Skills 提供指令和工作流，MCP 提供外部工具连接。
6. **自定义命令 vs Skills**：自定义命令（`.claude/commands/`）已合并到 skills。建议直接用 skills。

---

## 三、最佳实践

> **核心约束**：Claude 的上下文窗口会快速填满，性能随填充而下降。大多数最佳实践都围绕这个约束展开。

### 3.1 给 Claude 验证工作的方式

**给 Claude 一个可运行的检查：测试、构建、截图对比。这是「你能旁观的会话」和「你能放心离开的会话」之间的区别。**

Claude 在工作「看起来完成」时停止。没有可运行检查，你就是验证循环——每个错误都要等你发现。给一个能产生通过/失败信号的东西，循环就自动闭合了。

#### 检查可以是

- 测试套件
- 构建退出码
- Linter
- 将输出与基准文件对比的脚本
- 与设计稿对比的浏览器截图

#### 策略对比

| 场景 | ❌ 不推荐 | ✅ 推荐 |
|------|----------|---------|
| 提供验证标准 | "implement a function that validates email addresses" | "write a validateEmail function. test cases: user@example.com → true, invalid → false, user@.com → false. run the tests after implementing" |
| 可视化验证 UI | "make the dashboard look better" | "[粘贴截图] implement this design. take a screenshot, compare to original, list differences and fix them" |
| 解决根因 | "the build is failing" | "the build fails with: [错误]. fix it and verify build succeeds. address root cause, don't suppress" |

#### 检查作为停止门控的四种方式

1. **单提示内**：同一消息里运行检查并迭代
2. **跨会话**：设为 `/goal` 条件，独立评估器每轮重检
3. **确定性门控**：Stop hook 跑检查脚本，阻止轮次结束直到通过（连续 8 次阻止后 Claude 会覆盖 hook）
4. **第二意见**：验证子代理或动态工作流，让新模型尝试反驳结果

> **让 Claude 展示证据而非断言成功**：测试输出、命令结果、截图。审查证据比重新验证更快。

---

### 3.2 先探索，再计划，再编码

将研究、规划和实现分开，避免解决错误的问题。

#### 四阶段工作流

**1. 探索（Explore）**——进入 Plan Mode，Claude 只读不写

```
read /src/auth and understand how we handle sessions and login.
also look at how we manage environment variables for secrets.
```

**2. 计划（Plan）**

```
I want to add Google OAuth. What files need to change?
What's the session flow? Create a plan.
```

按 `Ctrl+G` 在文本编辑器里打开计划，直接编辑后再让 Claude 继续。

**3. 实现（Implement）**——退出 Plan Mode

```
implement the OAuth flow from your plan. write tests for the
callback handler, run the test suite and fix any failures.
```

**4. 提交（Commit）**

```
commit with a descriptive message and open a PR
```

#### 何时用 Plan Mode

- **直接跳过**：范围明确、修复很小（拼写、加日志、重命名）
- **最有用**：方法不确定、跨多文件改动、对代码不熟
- **判断标准**：能用一句话描述 diff，就跳过计划

---

### 3.3 在提示中提供具体上下文

指令越精确，需要的修正越少。Claude 能推断意图，但不能读心。

#### 策略对比

| 场景 | ❌ 不推荐 | ✅ 推荐 |
|------|----------|---------|
| 界定范围 | "add tests for foo.py" | "write a test for foo.py covering the edge case where user is logged out. avoid mocks." |
| 指向信息源 | "why does ExecutionFactory have such a weird api?" | "look through ExecutionFactory's git history and summarize how its api came to be" |
| 引用现有模式 | "add a calendar widget" | "look at how existing widgets are implemented. HotDogWidget.php is a good example. follow the pattern to implement a new calendar widget..." |
| 描述症状 | "fix the login bug" | "users report login fails after session timeout. check src/auth/, especially token refresh. write a failing test, then fix it" |

#### 提供丰富内容的方式

- **用 `@` 引用文件**：Claude 在响应前读取
- **直接粘贴图片**：复制/粘贴或拖放
- **提供 URL**：文档和 API 参考
- **管道输入**：`cat error.log | claude`
- **让 Claude 自己拉**：让它用 Bash、MCP、读文件自行获取

> 模糊提示在探索时有用（如 "what would you improve in this file?"），能浮现你没想到的问题。

---

### 3.4 配置你的环境

#### 3.4.1 编写有效的 CLAUDE.md

运行 `/init` 基于项目结构生成起始 CLAUDE.md，然后优化。

**核心原则：保持简短、人类可读、无情修剪。** 对每一行问："删除这行会导致 Claude 犯错吗？" 不会就删。**臃肿的 CLAUDE.md 会让 Claude 忽略你的实际指令！**

| ✅ 包含 | ❌ 排除 |
|---------|---------|
| Claude 无法猜的 Bash 命令 | 读代码就能搞清楚的 |
| 与默认不同的代码风格 | 标准语言约定 |
| 测试指令和首选运行器 | 详细 API 文档（改为链接） |
| 仓库规范（分支命名、PR 约定） | 频繁变化的信息 |
| 项目特定的架构决策 | 长篇解释或教程 |
| 开发环境怪癖（必需环境变量） | 逐文件描述 |
| 常见陷阱 | 不言而喻的做法 |

**故障排查**：
- Claude 有规则还做错事 → 文件太长，规则被淹没
- Claude 问的问题 CLAUDE.md 有答案 → 措辞有歧义
- 加强调（"IMPORTANT"、"YOU MUST"）可提高遵守度
- **像对待代码一样对待 CLAUDE.md**：审查、修剪、测试

**CLAUDE.md 文件位置**：

| 位置 | 作用 |
|------|------|
| `~/.claude/CLAUDE.md` | 所有会话 |
| `./CLAUDE.md` | 项目根，检入 git 共享 |
| `./CLAUDE.local.md` | 个人项目笔记，加 `.gitignore` |
| 父目录 | monorepo，自动拉入 |
| 子目录 | 按需拉入 |

**导入语法**：

```markdown
See @README.md for project overview.
- Git workflow: @docs/git-instructions.md
- Personal overrides: @~/.claude/my-project-instructions.md
```

#### 3.4.2 配置权限

减少中断的三种方式：

1. **Auto 模式**：分类器模型审查命令，只阻止有风险的
2. **权限白名单**：允许已知安全的命令（`npm run lint`、`git commit`）
3. **沙箱**：OS 级隔离，限制文件系统和网络访问

#### 3.4.3 使用 CLI 工具

告诉 Claude 用 `gh`、`aws`、`gcloud`、`sentry-cli` 等 CLI 工具——这是与外部服务交互最具上下文效率的方式。

- 装了 `gh`，Claude 知道怎么创建 issue、开 PR、读评论
- 没装 `gh`，Claude 仍可用 GitHub API，但未认证请求常遇速率限制
- Claude 也擅长学新工具：`Use 'foo-cli-tool --help' to learn about foo tool, then use it to solve A, B, C.`

#### 3.4.4 连接 MCP 服务器

```bash
claude mcp add <server-name>
```

让 Claude 从 issue 跟踪器实现功能、查数据库、分析监控、集成 Figma、自动化工作流。

#### 3.4.5 设置 Hooks

对**必须每次都发生、零例外**的操作用 hooks。与建议性的 CLAUDE.md 不同，hooks 是确定性的。

让 Claude 帮你写：
- "Write a hook that runs eslint after every file edit"
- "Write a hook that blocks writes to the migrations folder."

#### 3.4.6 创建 Skills

在 `.claude/skills/` 中加 `SKILL.md`，提供领域知识和可复用工作流。详见 [2.1 Skills](#21-skills技能)。

#### 3.4.7 创建自定义子代理

在 `.claude/agents/` 中定义专门助手，每个有自己的工具集和模型。详见 [2.2 Subagents](#22-subagents子代理)。

#### 3.4.8 安装插件

```bash
/plugin
```

插件无需配置即可添加 skills、工具和集成。如果用类型化语言，装代码智能插件——为 Claude 提供精确的符号导航和编辑后自动错误检测。

---

### 3.5 有效沟通

#### 询问代码库问题

像问高级工程师一样问：
- How does logging work?
- How do I make a new API endpoint?
- What edge cases does `CustomerOnboardingFlowImpl` handle?
- Why does this code call `foo()` instead of `bar()` on line 333?

#### 让 Claude 采访你

对较大功能，先让 Claude 采访你：

```
I want to build [brief description]. Interview me in detail using the AskUserQuestion tool.

Ask about technical implementation, UI/UX, edge cases, concerns, and tradeoffs.
Don't ask obvious questions, dig into the hard parts I might not have considered.

Keep interviewing until we've covered everything, then write a complete spec to SPEC.md.
```

**规格完成后，启动新会话执行**——新会话有干净上下文专注实现，你有书面规格可参考。

---

### 3.6 管理你的会话

#### 尽早且经常纠正方向

- **`Esc`**：中途停止 Claude，上下文保留
- **`Esc + Esc` 或 `/rewind`**：打开回退菜单，恢复先前对话和代码状态
- **`"Undo that"`**：让 Claude 撤销
- **`/clear`**：不相关任务间重置上下文

> **关键规则**：如果同一问题纠正 Claude 超过两次，上下文已被失败方法污染。`/clear` 重来，写一个包含所学内容的更具体提示。**干净会话 + 更好提示 > 长会话 + 累积修正。**

#### 积极管理上下文

- 任务之间频繁 `/clear`
- 自动压缩触发时，Claude 总结重要内容
- 用 `/compact <instructions>` 精准压缩
- 用 `Esc + Esc` 或 `/rewind` 选择消息检查点，选「Summarize from here」或「Summarize up to here」
- 在 CLAUDE.md 里加压缩指令，如 `"When compacting, always preserve the full list of modified files and any test commands"`
- 用 `/btw` 问快速问题，答案不进对话历史

#### 用子代理做调查

```
Use subagents to investigate how our authentication system handles token
refresh, and whether we have any existing OAuth utilities I should reuse.
```

子代理在独立上下文探索、读文件、汇报总结，不污染主对话。也可用于验证：

```
use a subagent to review this code for edge cases
```

#### 用检查点回退

每个提示都创建检查点。可以恢复对话、代码或两者。不必仔细规划每一步——告诉 Claude 尝试有风险的东西，不行就回退。

> 检查点只跟踪通过 Claude 编辑工具的更改。Bash 命令或外部进程的更改不被捕获。**这不是 git 的替代品。**

#### 恢复对话

`/rename` 给会话起名（如 `oauth-migration`），像分支一样对待它们。`claude --continue` 继续最近会话，`claude --resume` 从列表选。

---

### 3.7 自动化和扩展

#### 7.1 无头模式（非交互）

```bash
# 一次性查询
claude -p "Explain what this project does"

# 结构化输出
claude -p "List all API endpoints" --output-format json

# 流式输出
claude -p "Analyze this log file" --output-format stream-json --verbose
```

#### 7.2 多 Claude 会话并行

| 方法 | 适用场景 |
|------|---------|
| **Worktrees** | 在隔离 git 检出中跑独立 CLI 会话，编辑不冲突 |
| **桌面应用** | 可视化管理多个本地会话 |
| **Claude Code on the web** | 在 Anthropic 云 VM 中跑 |
| **Agent teams** | 多会话自动协调，共享任务、消息传递、团队负责人 |

**Writer/Reviewer 模式**：

| Session A (Writer) | Session B (Reviewer) |
|--------------------|----------------------|
| `Implement a rate limiter for our API endpoints` | `Review the rate limiter in @src/middleware/rateLimiter.ts. Look for edge cases, race conditions, and consistency with existing patterns.` |
| `Here's the review feedback: [Session B output]. Address these issues.` | |

#### 7.3 跨文件扇出

```bash
for file in $(cat files.txt); do
  claude -p "Migrate $file from React to Vue. Return OK or FAIL." \
    --allowedTools "Edit,Bash(git commit *)"
done
```

先在 2-3 个文件上测试，优化提示，再大规模跑。

#### 7.4 Auto 模式自主运行

```bash
claude --permission-mode auto -p "fix all lint errors"
```

分类器模型在命令运行前审查，阻止范围升级、未知基础设施、恶意内容驱动的操作。

#### 7.5 对抗性审查步骤

无人值守工作越长，独立检查越重要。让子代理在新鲜上下文中审查 diff：

```
Use a subagent to review the rate limiter diff against PLAN.md. Check that
every requirement is implemented, the listed edge cases have tests, and
nothing outside the task's scope changed. Report gaps, not style preferences.
```

> 被提示找差距的审查者通常会报告一些，即使工作是可靠的。追逐每个发现会导致过度工程。告诉审查者只标记影响正确性或所述要求的差距。

---

### 3.8 避免常见失败模式

| 失败模式 | 症状 | 修复 |
|---------|------|------|
| **大杂烩会话** | 一个任务跳到不相关的事，再回来，上下文充满无关信息 | 不相关任务间 `/clear` |
| **反复纠正** | Claude 做错，纠正，还错，再纠正，上下文被失败方法污染 | 两次纠正失败后 `/clear`，写更好的初始提示 |
| **过度指定的 CLAUDE.md** | 文件太长，Claude 忽略一半，重要规则在噪音中丢失 | 无情修剪。Claude 已正确做的事删掉或转成 hook |
| **信任然后验证差距** | Claude 产生看似合理但未处理边缘情况的实现 | 始终提供验证（测试、脚本、截图），无法验证就不发布 |
| **无限探索** | 让 Claude「调查」某事不界定范围，读数百个文件填满上下文 | 狭窄界定范围或用子代理 |

---

## 四、核心架构图

```
用户提示
  ↓
┌─────────────────────────────────────────┐
│         代理循环（Agentic Loop）          │
│  收集上下文 → 采取行动 → 验证结果         │
│  （可循环多次，用户可随时中断）            │
└─────────────────────────────────────────┘
  ↓                    ↓
模型（推理）          工具（行动）
  ↓                    ↓
Sonnet/Opus      文件操作 / 搜索 / 执行 / 网络 / 代码智能
                         ↓
              ┌──────────────────────────┐
              │  扩展层                   │
              │  Skills / MCP /          │
              │  Hooks / Subagents /     │
              │  Plugins                 │
              └──────────────────────────┘
                         ↓
              ┌──────────────────────────┐
              │  持久化层                 │
              │  CLAUDE.md / Auto Memory │
              │  / 检查点 / 会话历史      │
              └──────────────────────────┘
```

---

## 五、官方资源索引

| 资源 | 链接 | 用途 |
|------|------|------|
| **Claude Code 官方文档** | `code.claude.com/docs` | 完整文档，有中文版 |
| **How Claude Code works** | `code.claude.com/docs/zh-CN/how-claude-code-works` | 核心架构详解 |
| **Skills 文档** | `code.claude.com/docs/zh-CN/skills` | Skills 完整规范 |
| **Plugins 文档** | `code.claude.com/docs/zh-CN/discover-plugins` | 插件市场 |
| **Best Practices** | `anthropic.com/engineering/claude-code-best-practices` | Anthropic 工程团队实战指南 |
| **Build with Claude** | `anthropic.com/learn/build-with-claude` | 官方课程（含 Claude Code、subagents、MCP） |
| **帮助中心** | `support.anthropic.com` | FAQ 和故障排查 |
| **插件目录** | `claude.com/plugins` | 浏览官方插件 |

---

## 学习路径建议

1. **第一遍快读**：通读「核心架构」部分，建立整体认知
2. **动手实验**：用 `/init` 生成 CLAUDE.md，按 [3.4.1](#341-编写有效的-claudemd) 优化
3. **试 Skills**：把一个你反复粘贴的工作流封装成 skill
4. **试 Subagents**：用 `context: fork` 跑一个隔离的研究任务
5. **试 Hooks**：给一个必须每次发生的操作加 hook
6. **深入 Best Practices**：每条对照自己的使用习惯，找出差距
7. **看官方课程**：`anthropic.com/learn/build-with-claude` 的 Claude Code 课程

---

_本笔记基于 Anthropic 官方文档整理，内容以官方为准。_
