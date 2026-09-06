---
tags: [工具配置, 同步, Obsidian, Syncthing]
created: 2026-08-30
---

# Syncthing 同步 Obsidian 库（电脑 ↔ 手机）

## 它解决什么

让手机和电脑的 Obsidian 库**双向实时同步**，数据只在自己设备之间直连传输，不经任何云服务器。手机上随手记的，回电脑能接着写；电脑上整理的，出门在手机上看。

## 当前配置快照

| 项 | 值 |
|---|---|
| Syncthing 版本 | v2.1.3 "Hafnium Hornet"（go1.26.5） |
| 电脑设备名 / ID | BKUHR / `QL3ZMJG-HNMZUAT-AQM3L7F-SGZNUCX-R3U3G36-K5K4Z2E-ENXQ3KY-WDL2SA6` |
| 手机设备名 | PLR110（Syncthing-Fork） |
| 文件夹 ID | `obsidian`（**两端必须完全一致**） |
| 电脑路径 | `D:\My knowledge vault` |
| 手机路径 | `/storage/emulated/0/Documents/Obsidian` |
| 同步规模 | 244 文件 / 115 MiB |
| 管理界面 | `https://127.0.0.1:8384`（自签证书，浏览器报不安全点继续） |

## 文件位置

| 用途 | 路径 |
|---|---|
| 主程序 | `D:\syncthing\syncthing.exe` |
| 配置与数据库 | `D:\syncthing-data` |
| 启动脚本（源） | `D:\tools\syncthing-start.vbs` |
| 桌面图标 | `C:\Users\BEER\Desktop\Syncthing.vbs` |
| 忽略规则 | `D:\My knowledge vault\.stignore` |

**双击桌面图标即可启动**：后台静默运行（无黑窗口），5 秒后自动打开管理页；若已在运行则只打开管理页。

## 换机器 / 重装时照做

1. 下载 Syncthing 官方便携版（zip），解压到**非系统盘**（如 `D:\syncthing`）
2. 建配置目录（如 `D:\syncthing-data`）
3. 建启动脚本（内容见下）→ 放桌面
4. 手机装 **Syncthing-Fork**（官方 Android 版已停止维护，别装错）
5. 两端建**同一个文件夹 ID**，互相添加对方设备
6. 手机端：关电池优化 + 设仅 WiFi 同步
7. 手机 Obsidian：**以文件夹形式打开仓库**，选同步目录

启动脚本 `syncthing-start.vbs`（静默启动 + 自动开管理页）：

```vbs
Set ws  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
home = "D:\syncthing-data"
prog = "D:\syncthing\syncthing.exe"

If Not fso.FolderExists(home) Then fso.CreateFolder(home)

running = False
Set exec = ws.Exec("tasklist /FI ""IMAGENAME eq syncthing.exe""")
out = exec.StdOut.ReadAll()
If InStr(1, out, "syncthing.exe", 1) > 0 Then running = True

If Not running Then
    ws.CurrentDirectory = "D:\syncthing"
    ws.Run """" & prog & """ serve --home=" & home, 0, False
    WScript.Sleep 5000
End If

ws.Run "https://127.0.0.1:8384", 1, False
```

## .stignore 规则（`D:\My knowledge vault\.stignore`）

| 规则 | 为什么 |
|---|---|
| `.git` `.gitignore` | **423 MB**，占库总量 80%，同步到手机毫无意义 |
| `.workbuddy` `.claude` `.claudian` `.agents` `.playwright-mcp` `.mcp.json` | AI 工具数据，频繁变动且机器专属，同步必然冲突 |
| `.obsidian/workspace*` `.obsidian/appearance.json` | 工作区状态与外观配置，两端必然不同，**主要冲突源** |
| `.stignore.bak` `*.sync-conflict-*` | 临时文件与冲突残留，不该同步 |
| `.DS_Store` `Thumbs.db` `desktop.ini` | 系统垃圾 |

**效果**：915 文件 / 531 MB → **244 文件 / 115 MiB**，手机毫无压力。

## 踩过的坑

1. **v2.x 参数结构变了**：老教程的单横线 `-home=` 会报 `unknown flag`。v2 用**双横线 + 子命令**——`syncthing.exe serve --home=D:\path`
2. **路径必须 Windows 原生格式**：`--home=/d/xxx` 会被解析成 `d:\d\xxx`（MSYS 路径转换坑）。必须写 `D:/syncthing-data`
3. **不带 `--home` 启动会落 C 盘** `AppData\Local\Syncthing`。**启动入口必须统一**，否则形成两个不同设备 ID 的实例，同步关系全乱
4. **手机端文件夹 ID 必须与电脑端一致**（`obsidian`）。用了自动生成的随机 ID，电脑会当成"另一个新文件夹"
5. **手机端建完文件夹还要打开电脑设备开关**（共享），否则只是本地文件夹，根本不同步
6. **手机必须关电池优化**（设置 → 应用 → Syncthing-Fork → 电池 → 无限制），否则 Android 杀后台，同步时断时续
7. **首次同步必冲突**：`.obsidian/appearance.json` 两端各自生成。已加进忽略规则，之后两端各保留自己的主题字号（合理，屏幕尺寸本就不同）
8. **改 `.stignore` 前先停服务**，否则文件被进程锁住写不了（EPERM）
9. **用 CLI 建文件夹会多出一个空条目**（id 为空），GUI 会一直报错，需手动清理

## 日常使用

- **启动**：双击桌面 `Syncthing.vbs`
- **别两端同时编辑同一篇笔记**。真撞车会生成 `xxx.sync-conflict-日期.md`，手动合并后删除
- **手机改完，等同步状态变"最新"再动电脑端**

## 故障排查

| 现象 | 原因 / 处理 |
|---|---|
| 管理页打不开 | 服务没启动 → 双击桌面图标 |
| 一直不同步 | 手机电池优化没关 / 不在 WiFi 下 |
| 手机看不到文件 | Obsidian 要用"**以文件夹形式打开仓库**"，不是"创建新仓库" |
| 出现 `.sync-conflict-` 文件 | 两端同时改了同一文件 → 合并后删除 |
| 手机 Obsidian 报错或卡住 | 某个桌面插件手机不支持 → 删手机端 `.obsidian/plugins/<插件名>` |
| 文件夹显示"非共享" | 手机端没把该文件夹共享给电脑设备（打开开关） |

## 相关

- 桌面快捷方式无法由脚本自动创建（系统安全策略拦截 COM），故用 `.vbs` 脚本代替——代价是图标为脚本默认图标，好处是**无黑窗口**且自动开管理页

- 备份与仓库策略总览 → [[05_备份与仓库管理方案]]（Git 那半边的备份策略）
- 工具矩阵 → [[03_工具速查]] ｜ 系统架构 → [[00_系统全景]]
