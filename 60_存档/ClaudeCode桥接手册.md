# Claude Code 桥接手册（WorkBuddy → Claude Code CLI）

> 适用：在 WorkBuddy 对话里，直接调用本机 Claude Code 干活，结果回传。
> 验证状态：2026-08-29 已跑通（英文 + 中文 prompt 均正常）。

---

## 一句话原理

WorkBuddy 的 Bash 调本机 `claude` CLI，用 `-p`（print 模式，非交互、跑完即退出），输出回传对话。
**WorkBuddy 当壳，Claude Code 当执行器。**

---

## 一、必须先注入环境变量（关键，否则报 Not logged in）

**原因**：你的 Claude Code 走自建网关，凭证写在 `~/.claude/settings.json` 的 `env` 段
（`ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN`）。CLI 在 WorkBuddy 的 Shell 下**不自动加载**这个 env 段，
所以直接跑会报 `Not logged in · Please run /login`。

**一键注入片段（复制即用，凭证值不打印、不落盘）**：

```bash
eval "$("C:/Users/BEER/.workbuddy/binaries/python/versions/3.13.12/python.exe" -c "
import json,shlex
d=json.load(open(r'C:/Users/BEER/.claude/settings.json',encoding='utf-8'))
for k in ['ANTHROPIC_BASE_URL','ANTHROPIC_AUTH_TOKEN','ANTHROPIC_MODEL']:
    v=d.get('env',{}).get(k)
    if v: print('export '+k+'='+shlex.quote(str(v)))
")"
```

注入后自检（只显示 yes/no，不暴露值）：

```bash
echo "BASE_URL=${ANTHROPIC_BASE_URL:+yes} TOKEN=${ANTHROPIC_AUTH_TOKEN:+yes} MODEL=${ANTHROPIC_MODEL:-未设}"
```

---

## 二、三种调用模式

### 模式 1：只读分析（默认推荐，零副作用）

```bash
cd "/d/你的项目目录"
claude -p "审查 src/ 下这段代码的性能问题，只报告不建议" --restricted --output-format text
```

`--restricted`：移除 Bash / Edit 等"能执行命令和改代码"的工具，**保证不改任何文件**。
适合：代码审查、方案分析、生成报告。

### 模式 2：允许改文件（需明确目标目录）

```bash
cd "/d/你的具体项目"
claude -p "把 utils.py 里的 xxx 函数重构为异步版本" --permission-mode acceptEdits
```

`--permission-mode` 可选值：`acceptEdits` / `auto` / `plan` / `manual` / `dontAsk` / `bypassPermissions`。

### 模式 3：机器可读输出（便于后续处理）

```bash
claude -p "列出所有 TODO 注释" --restricted --output-format json
```

`--output-format`：`text`（默认）/ `json`（单结果）/ `stream-json`（实时流）。

---

## 三、安全红线（必须遵守）

| 红线 | 说明 |
|---|---|
| **必须用 `-p`** | 交互模式在 WorkBuddy 的 Bash 里会卡住等输入 |
| **显式 `cd` 到具体项目** | 禁止在 `D:\`、`C:\Users\BEER` 这类根目录跑，避免大范围扫描 / 误改 |
| **默认 `--restricted`** | 不确定就先只读，确认要改再开 `acceptEdits` |
| **不用 `bypassPermissions`** | 除非你完全清楚后果，否则禁止 |
| **长任务放后台** | 超过 2 分钟的任务用 `run_in_background: true` + 输出重定向到日志文件 |
| **每次确认 cwd** | 命令前先 `pwd` 确认当前目录是你要改的那个 |

---

## 四、已知警告与消除

调用时会出现：

```
"DeepSeek-V4-pro" is not a model this version of Claude Code recognizes ...
```

**含义**：你网关后端实际模型是 `DeepSeek-V4-pro`，Claude Code 不认识这个名字，
因此按 200k token 保守估算上下文窗口。**不影响功能**。

**消除方法（三选一）**：

```bash
# 方案 1：恢复"等 API 返回"的旧行为（最简单）
export CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT=1

# 方案 2：申明真实上下文窗口
export CLAUDE_CODE_MAX_CONTEXT_TOKENS=200000

# 方案 3：在 settings.json 里用 modelOverrides 映射模型名
```

---

## 五、重要事实（影响你的判断）

**你的 Claude Code 后端不是 Anthropic Claude 官方模型，而是 `DeepSeek-V4-pro`（经自建网关中转）。**

含义：
- 你用的一直是 Claude Code 这个**壳/工作流**（它的 agent 能力、工具调用、项目上下文管理），
  底层推理模型是 DeepSeek。
- 评估"Claude Code 能力强弱"时，要区分是**壳的能力**还是**模型的输出质量**。
- 换模型只需改 `settings.json` 里的 `ANTHROPIC_MODEL`，壳的体验不变。

---

## 六、成本与额度

- 每次 `claude -p` 都真实调用网关 → 消耗你的网关额度。
- 大项目全量分析会读大量文件进上下文，额度消耗显著上升。
- 建议：先用 `--restricted` 只读试一次，确认任务范围可控，再放开写权限。

---

## 七、快速参考：完整可用模板

```bash
# 1. 注入环境
eval "$("C:/Users/BEER/.workbuddy/binaries/python/versions/3.13.12/python.exe" -c "
import json,shlex
d=json.load(open(r'C:/Users/BEER/.claude/settings.json',encoding='utf-8'))
for k in ['ANTHROPIC_BASE_URL','ANTHROPIC_AUTH_TOKEN','ANTHROPIC_MODEL']:
    v=d.get('env',{}).get(k)
    if v: print('export '+k+'='+shlex.quote(str(v)))
")"
export CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT=1

# 2. 确认目录
cd "/d/你的项目目录" && pwd

# 3. 只读调用（改文件时才把 --restricted 换成 --permission-mode acceptEdits）
claude -p "你的任务描述" --restricted --output-format text
```
