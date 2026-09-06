# GitHub SSH 连接配置指南

## 适用场景

通过 SSH 方式连接 GitHub，无需每次输入密码即可完成 `git clone`、`git push`、`git pull` 等操作。

> **本文档针对操作系统：Windows 11**

---

## 1. 生成 SSH 密钥

打开终端（Git Bash / PowerShell / CMD），执行：

```bash
# 创建 .ssh 目录（如已存在则跳过）
mkdir -p ~/.ssh && chmod 700 ~/.ssh

# 生成 Ed25519 密钥（推荐，更安全更快）
ssh-keygen -t ed25519 -C "your-email@example.com" -f ~/.ssh/id_ed25519_github -N ""

# 备选：RSA 4096 密钥（兼容性更广泛）
# ssh-keygen -t rsa -b 4096 -C "your-email@example.com" -f ~/.ssh/id_rsa_github -N ""
```

| 参数 | 说明 |
|------|------|
| `-t ed25519` | 密钥类型，Ed25519（推荐） |
| `-C` | 注释，一般填邮箱 |
| `-f` | 密钥文件路径 |
| `-N ""` | 空密码（不设密码短语） |

生成后查看公钥：

```bash
cat ~/.ssh/id_ed25519_github.pub
```

---

## 2. 配置 SSH Config 文件

编辑 `~/.ssh/config`，添加以下内容：

```
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_github
    IdentitiesOnly yes
```

| 配置项 | 说明 |
|--------|------|
| `Host` | 别名，连接时使用 `ssh github.com` |
| `HostName` | 实际主机名 |
| `User` | 登录用户，GitHub 固定为 `git` |
| `IdentityFile` | 使用的私钥路径 |
| `IdentitiesOnly yes` | 仅使用指定密钥，不尝试其他密钥 |

设置文件权限（Git Bash 下执行）：

```bash
chmod 600 ~/.ssh/config
chmod 600 ~/.ssh/id_ed25519_github
chmod 644 ~/.ssh/id_ed25519_github.pub
```

---

## 3. 添加公钥到 GitHub

1. 打开 [GitHub SSH Keys 设置页](https://github.com/settings/keys)
2. 点击 **New SSH Key**
3. **Title**：填写一个辨识名称，如 `Windows PC`、`公司电脑`
4. **Key Type**：选择 **Authentication Key**（不要选 Signing Key）
5. **Key**：完整粘贴公钥内容（从 `ssh-ed25519` 开头到注释结尾）
6. 点击 **Add SSH Key** 保存

> ⚠️ 注意：公钥必须完整复制，包含开头的 `ssh-ed25519` 和结尾的注释，不能断行或遗漏。

---

## 4. 配置 Git 用户信息

```bash
git config --global user.name "你的GitHub用户名"
git config --global user.email "你的GitHub注册邮箱"
```

查看当前配置：

```bash
git config --global --list | grep user
```

---

## 5. 测试连接

```bash
ssh -T git@github.com
```

首次连接会提示确认主机指纹，输入 `yes` 回车。

成功后显示：

```
Hi <用户名>! You've successfully authenticated, but GitHub does not provide shell access.
```

> 这是正常的——GitHub 不提供 shell 访问，仅用于 Git 操作。

---

## 6. 日常使用

### 克隆仓库

```bash
# SSH 方式（推荐）
git clone git@github.com:用户名/仓库名.git

# 示例
git clone git@github.com:JXSWR/obsidian-notes.git
```

### 已有仓库切换为 SSH

```bash
# 查看当前远程地址
git remote -v

# 修改为 SSH 地址
git remote set-url origin git@github.com:用户名/仓库名.git
```

### 推送到远程

```bash
git push origin master
# 或首次推送设置上游分支
git push -u origin master
```

---

## 7. 当前设备配置信息

> 更新日期：2026-08-05

| 项目 | 值 |
|------|-----|
| 密钥路径 | `~/.ssh/id_ed25519_github` |
| 密钥类型 | Ed25519 |
| 公钥指纹 | `SHA256:7IOcpy8+TsQEZOtCinaxKnwwMvPbtvmp14e7LUQWAPI` |
| Git 用户名 | JXSWR |
| Git 邮箱 | 601024079@qq.com |
| Config 文件 | `~/.ssh/config` |

---

## 8. 常见问题

### Q: `Permission denied (publickey)`

可能原因：
- 公钥未添加到 GitHub 账户，或添加了但内容不完整
- 在 GitHub 上选错了 Key Type（应为 Authentication Key，不是 Signing Key）
- 私钥路径与 config 中的 `IdentityFile` 不一致

排查命令：
```bash
# 详细调试输出
ssh -vT git@github.com
```

### Q: `Host key verification failed`

手动添加 GitHub 主机密钥：
```bash
ssh-keyscan -t ed25519 github.com >> ~/.ssh/known_hosts
```

### Q: 每次都要输密码

如果生成密钥时没有用 `-N ""`，而是设置了密码短语，可以添加到 SSH Agent 避免重复输入：

```bash
eval $(ssh-agent -s)
ssh-add ~/.ssh/id_ed25519_github
```

### Q: 如何生成多个密钥用于不同平台

```bash
# GitHub
ssh-keygen -t ed25519 -C "github" -f ~/.ssh/id_ed25519_github

# GitLab
ssh-keygen -t ed25519 -C "gitlab" -f ~/.ssh/id_ed25519_gitlab

# Gitee
ssh-keygen -t ed25519 -C "gitee" -f ~/.ssh/id_ed25519_gitee
```

然后在 `~/.ssh/config` 中分别配置不同 Host 对应不同密钥即可。

---

*本文档基于实际操作记录，如需更新请修改后注明日期。*

---

## 相关

- 备份与仓库策略总览 → [[05_备份与仓库管理方案]]（.gitignore / LFS / 大文件处理）
- 手机同步 → [[07_Syncthing同步Obsidian配置手册]]
- 工具矩阵 → [[03_工具速查]] ｜ 术语 → [[04_术语速查]]
