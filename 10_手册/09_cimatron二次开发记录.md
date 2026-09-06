# Cimatron 二次开发记录（淬锋应用外挂）

> 项目：Cimatron CE2024 二次开发外挂「淬锋应用」（C# / .NET Framework 4.8 / ClassLibrary1）
> 功能：统一面板整合多个功能 —— 一键出程式单、NC 参数批量编辑器、中文帮助、环境检查
> 归档日期：2026-08-29（含 8/27 至 8/29 全部工作进程与沉底经验）
> 产品化目标（8/29 定）：做成可打包安装、跨 Cimatron 版本兼容、对外销售需授权的外挂产品

---

## 1. 项目概述

- **定位**：从「一键出程式单」升级为「淬锋应用」外挂——参考「口口外挂」的垂直面板 + 可折叠工具箱样式，把多个功能集中到一个入口。
- **功能模块**：① 程式单（读 NC 程序 → 分组 → 截视图 → 导出 Excel）② NC 参数批量编辑器（表格化批量改工序加工参数，改即写回）③ 中文帮助（开 CHM）④ 环境检查（DLL 目录/CHM/版本探测自检）。
- **技术栈**：C# 插件（.NET Framework 4.8），通过 interop.CimatronE / interop.CimNcAPI API；手写 OOXML（零第三方依赖）打包 .xlsx；System.Drawing 做图像后处理；WinForm 手工构建 UI（无 Designer）。
- **输出**：`程式单_<NC名>.xlsx`，结构 = 元信息 → 零件视图（4 张，第一角投影布局）→ 程序表（11 列）。

## 2. 开发环境与铁律（用户决策，勿违反）

| 铁律 | 说明 |
|---|---|
| **编译只能靠用户 VS F6** | 平台下拉必须 `x64`，否则编到 bin\Debug\ 而 CE 加载 bin\x64\Debug\ 那份。AI 代编、命令行脚本、双击 .cmd/.bat 全被判死（多次尝试均失败，见 §6.1）|
| 固定验证节奏 | 改代码 → 用户关 CE → F6 → 开 CE 跑命令 → 发回 xlsx 验证 |
| **重注册边界** | **改命令名/类名/分类名(GetCategoryName)都要重注册**；只有"类名+命令名+分类名都不变、只改内部逻辑"才免注册。分类名属注册元数据，F6 不够（8/29 实测：改 GetCategoryName 后 CE 仍显示旧分类名，必须重跑 Register_API_Commands.exe）|
| **新建 .cs 必加 csproj** | Write 新建的 .cs 不会自动进 `<Compile Include>`，必须手动编辑 .csproj 加进去，否则 F6 编不出 → 命令"不存在"（8/28 实测）|
| 用户偏好 | 先对齐再动手；改完给"重点验证清单"；定量分析优先于猜 |

## 3. 代码结构与文件职责

代码目录：`D:\repos\My project workspace\产品开发\淬锋应用\dev\Cimatron-API-C---Example\ClassLibrary1\`

| 文件 | 职责 |
|---|---|
| `ExportProgramSheetCommand.cs` | 命令「程式单」：导出 XML → 分组 → 弹窗 → 截视图 → 写 Excel。含 `CaptureViews`（切视图+截图+后处理）、`RemoveGreenBackground`（去绿底+去灰条）、`CropToModelBBox`（裁模型包围盒）、`PngSize`（读 PNG 尺寸）|
| `XlsxWriter.cs` | 手写 OOXML 生成 .xlsx：单元格/合并/列宽/行高/样式/图片。含 `AddPictureAt`（绝对 EMU 定位）、`BuildDrawing`（图片锚点 XML）、**坐标分解**（DecomposeCol/DecomposeRow，WPS 兼容关键）|
| `ViewSelectForm.cs` | 视图勾选表单：4 个复选框（主/俯/左/轴测）+ 2×2 缩略图预览，默认全选 |
| `NcParamBatchEditorCommand.cs` | 命令「NC参数批量编辑器」：导出 PM XML → `ParseXml`（数据驱动取参数 ID）→ 弹表格编辑器 |
| `NcParamEditorForm.cs` | 参数编辑器主窗体：TP 分组折叠、状态列着色、批量应用/缩放、7 种写回策略链、诊断写回按钮（详见 §9）|
| `CuiFengAppCommand.cs` | 命令「淬锋应用」入口：定义面板 section/按钮，`Execute` 弹 `CuiFengPanelForm`；含 `RunEnvCheck`（环境检查）|
| `CuiFengPanelForm.cs` | 淬锋应用统一面板：可折叠工具箱 + 图标按钮（System.Drawing 现画）|
| `HelpCommand.cs` | 命令「中文帮助」：打开随外挂分发的 CHM |
| `CimatronVersionDetector.cs` | 版本探测：扫安装目录+注册表找 Cimatron 版本（产品化 M1 基础）|
| `LicenseChecker.cs` | 授权校验骨架：机器指纹(MachineGuid) + RSA 验签（产品化 M2 基础）|
| ~~`CimInfoCommand.cs`~~ | 已删除（8/29，流程验证功能下线）|
| ~~`Class1.cs`(OpenWindowsForm)~~ | 已删除（8/29，空模板命令）|

> 独立工具（不在 csproj 内，`淬锋应用\CimatronProbe\`）：`version_probe.py`（pythonnet 反射验证跨版本接口，免编译）、`CimatronProbe.cs`（同功能 C# 版，需 VS 编译）

## 4. 功能开发历程（时间线）

### 4.1 v1 最小闭环（8/27 – 8/28 早）
- 程式单 Excel 生成跑通：按 TP/刀具分组，元信息 + 程序表 + 视图截图（最初俯视+轴测 2 张）。
- 视图命令 ID（来自 Program\Command list.xml，均带自动缩放、NC 环境可用）：
  - **Front 主视 = 34186**（XZ 平面，正对 Y 看）
  - **Top 俯视 = 34064**（XY 平面，正对 Z 看）
  - **Left 左视 = 34070**（YZ 平面，正对 X 看）
  - **Isometric 轴测 = 34063**（立体）
- 截图流程：`pool.GetCommandById(id).Execute()` 切视图 → `Thread.Sleep(1000)`（等渲染，原 400ms 会截到旧视角）→ `cimDoc.SavePicture(png)`。

### 4.2 三点改进：视图上移 + 工程图样式（10:50）
- 视图从表格底部移到**元信息之后、程序表头之前**（先看模型后看程序）。
- 视图加工程图式外观：图框边框（`<a:ln w="12700">`）+ 视图名（图上方）+ 比例标注（图下方，后被去掉）。
- `Sleep(400)→1000` 根治"截到旧视角"。

### 4.3 视图+背景：4 张视图 + 去绿底（12:36 – 12:50）
- `ViewPlan` 扩到 4 项（俯+主+左+轴测）。用户确认：俯视只能看外形+孔位，看不到厚度/侧壁/沉孔 → 必须多视图。
- 新增 `RemoveGreenBackground`：NC 默认背景是亮草绿，遍历像素判定绿色 → 换白。
- **算法迭代**（第一次实测漏判浅绿）：旧判定 `G>R+20 && G>B+20 && G>100` 太严 → 新判定：①灰阶（max-min<10）跳过 ②绿色主导（max==G 且 G-min>8）换白。

### 4.4 询问式视图勾选 + 预览（13:05 – 13:29）
- 用户要求"视图由我主导"：XZ=主视、XY=俯视、YZ=左视（第一角投影），按需勾选输出。
- 新建 `ViewSelectForm.cs`：4 复选框 + 2×2 缩略图预览（先截 4 张候选并处理后弹窗），勾几个出几个，取消/空勾选 = 全选兜底。
- `CaptureViews` 重构为返回 `Dictionary<int,(Label,Path)>`，永远先抓 4 张候选；Execute 里弹窗选、组装、写 Excel。
- **C# 7.3 注意**：不能用 tuple pattern（`is (int,string)` 是 C# 8），Collect 用 if 逐个读 CheckBox。

### 4.5 投影布局 + 去比例字样 + 左视图确认（14:09）
- 用户更正：左视图投影**正确**（之前误判），34070 不动。
- 去掉"比例 1:1"字样（用户觉得多余）：`AddPicture` 加 `showScale` 参数。

### 4.6 布局重构：绝对 EMU 定位（14:47）
- 旧布局靠"行数估算(×18)"摆图 → 间距不精确、松散。
- 重构：所有图锚定同一单元格，用 **EMU 精确偏移**摆放；视图名改文本框（sp，透明无边框）贴图上方；间距精确 10mm；程序清单精确位于视图块下方 10mm。
- 底部灰条去除：NC 窗口底部状态栏被 SavePicture 截入（中性灰），从底向上扫连续中性灰行（占比>50%、max-min<18、均值100~178）整行换白，仅扫底部 80px。
- ⚠️ **此步引入 WPS 叠图隐患**（见 4.9），也是"底部显示不全"怀疑源头（见 §7）。

### 4.7 修复 drawing XML 畸形（15:05）
- 用户反馈"视图被遮挡" → 4 张 PNG 完整无遮挡，根因是 `BuildDrawing` 生成文本框时**漏了 `</xdr:sp>` 闭合标签**，Excel/WPS 修复时锚点错乱相互压盖。
- 修复：补 `</xdr:sp>`。**经验：手写 XML 必须做栈扫描验证标签平衡**（Python 栈式扫描定位）。

### 4.8 显示不全 + 比例失真（18:42）
- 用户反馈：俯视/轴测显示不全 + 三视图大小不一致（不符合"长对正/高平齐/宽相等"）。
- **数据诊断**（Python+PIL+zipfile 定量分析，不靠看图）：
  - "显示不全"根因：视图块总宽 **200.5mm > A4 可打印 174mm**，右列整列掉到页面外。
  - "比例失真"根因：每个视图独立 fit（NC fit-to-window），模型在画布中占比不同 → 长对正差 47%、宽相等差 51%。
  - 推论：主视=左视完全相同 → 零件 X=Y（正方形俯视），Z=X/4.37。
- 用户决策：A4 纵向·单图 **80mm**；**排除蓝色刀轨/UCS 算尺寸**（只按零件本体）。
- 改动：新增 `CropToModelBBox`（检测模型包围盒，排除蓝色主导像素，加 5% 边距，裁剪输出 `*_crop.png`）；`DISP_W` 360→302px（80mm）。

### 4.9 WPS 打开叠图 → 列分解（19:10 – 19:54）★最难的坑
- 现象：**WPS 桌面版打开叠图**；右侧栏预览（WorkBuddy 内核）正常。
- 尝试链：`oneCellAnchor`+大 colOff → 叠 → `twoCellAnchor` → 仍叠 + 比例乱 → **列分解 → 成功**。
- **根因**：`colOff/rowOff` **超过单列宽/单行高的大偏移**，WPS 解析器会丢弃（忽略偏移 → 所有图从同一锚点开始 → 叠在一起）。Excel/WorkBuddy 内核能正确跨列解析，所以只有 WPS 崩。与锚点类型（one/twoCellAnchor）无关。
- **最终修复**：坐标分解——把绝对 EMU 位置拆成「整数 col/row + 单元格内小偏移」，保证 colOff < 列宽、rowOff < 行高。新增 `DecomposeCol/DecomposeRow/RowTopEmu/ColWidthEmu/RowHeightEmu`。
- **用户确认：WPS 不再重叠 ✓**

### 4.10 NC 参数批量编辑器（8/28 下午 – 8/29）★第二个大功能
- 诉求：像 NC 程序管理器一样，表格化批量修改工序加工参数，改即写回。
- 数据源：`INcModel.GetProcessManagerAsXML` 导出 PM XML，**参数 ID 自描述**（XML 里 `<名称 Value="..." ID="数字"/>`，ID 即 iParamId），做批量编辑器**零硬编码 ID、数据驱动**。
- 写回：`INcModel.SetProcedureParameter(uid, paramId, value)` + `Regenerate()` 重算。
- **「非空闲模式」报错真根因（定论）**：不是"工序没进编辑模式"（`ProcedureInEditMode=1` 无效），而是**整个 Cimatron 不空闲**——编辑器用 `ShowDialog()` 模态阻塞在 `Execute()` 内，命令不结束 → 全程"命令执行中" → 写 API 被拒（读不受影响）。**对策：改无模式 `Show()`，`Execute()` 立即返回。**
- 写回策略链（7 种，`STRATEGY_ORDER={0,1,5,6,2,3,4}`）：0 直接写 / 1 ProcedureInEditMode / 5 RevokeActive / 6 关程序管理器（这四条不动 NC 状态，排前）；2/3/4 走 OpenProcedureForEdit/EnterEditMode（会弹 CE 工序编辑面板，排后）。策略 2/4 必须 `try{Set}finally{CloseProcedure(uid,1)}`。
- 无模式窗口三要素：**绑 Owner=CE 主窗句柄**（`Process.GetCurrentProcess().MainWindowHandle` 包 IWin32Window）+ **单例** + 每次写回后 `BringToFront()`。
- TP 分组折叠：分组行 `▾/▸ TP名（N 工序，M 需重算）`，批量只作用于「可见+选中」行；DataGridView 隐藏当前行会抛异常，先 `EndEdit()`+清 `CurrentCell`。
- 状态列：`程序状态`(ID 30009) 在 PM XML 里**真实工序无 ID 属性**，需第二遍 `.//*[@Value and not(@ID)]` 收进只读字典；着色 绿=完成/橙红=需重算。
- 刀号列转只读：刀号归刀具定义所有，工序层改无效（interop 无"按 ID 改刀具定义"接口）。

### 4.11 淬锋应用整合 + 命令体系重构（8/29）
- 定位：参考「口口外挂」，把所有功能集中到一个垂直面板（可折叠工具箱 + 图标按钮）。
- 命令体系：分类名 **BeerTools → 淬锋应用**；命令「一键出程式单(MVP)」改名「程式单」；**删除**「流程验证」(CimInfoCommand)、「OpenForm」(OpenWindowsForm/Class1 空模板)。
- 现有 4 命令：淬锋应用 / 程式单 / NC参数批量编辑器 / 中文帮助。
- **图标**：外部命令图标**不是散文件**，而是嵌在 `Resource\English\CimExternalRc.dll` 的 PE 资源里（RT_ICON/RT_GROUP_ICON，语言 ID 2052）。改 `Images\Commands` 目录 + ini `@ID` **无效（已证伪）**，只能用 `Register_API_Commands.exe` GUI「命令图表」字段贴（.NET 代码侧无 GetBitmap，`ICreateCommand` 无此方法）。

### 4.12 命令注册/布局机制反推（8/29）★重要技术结论
- **命令登记表 = `C:\ProgramData\Cimatron\Cimatron\2024.0\Data\ExternalCommands.ini`**（Program Files 下 `SourceData\` 那份是空模板，别被误导）。格式 `命令名=命令名@图标ID`，`@0`=无图标。
- **UI 布局缓存 = 同目录 `CommandsLayout.xml`**（工具栏/菜单栏分组）。改代码分类名后旧菜单/工具栏名仍残留于此，**必须 CE 关闭时直接改 XML 才能彻底删**（Customize 里删不掉空壳）。
- **外部命令按钮用「动态命令 ID（50xxx 区间）」引用**，不是命令名/类名（grep 命令名 0 命中）。删命令要删「代码+ini」，别去 XML 里按 ID 删按钮（ID 每次重注册会变，删错误伤）。
- **改分类名也要重注册**（见 §2 铁律），F6 不够。

### 4.13 产品化 M1/M2 启动（8/29）
- 明确最终目的：做成**可打包安装、跨版本兼容、对外销售需授权**的产品。
- **纠正**：程式单**不依赖 Excel**（XlsxWriter 用 System.IO.Compression 手写 OOXML，生成 xlsx 不碰 Excel），删掉 csproj 里两个死引用 Interop.Excel/Office.Core。
- M1 落地：`CimatronVersionDetector.cs`（版本探测）+ `version_probe.py`/`CimatronProbe.cs`（跨版本兼容验证，反射检查关键接口）。
- M2 落地：`LicenseChecker.cs` 授权骨架（机器指纹 + RSA 验签，公钥占位）。

## 5. 技术实现要点（现状代码怎么工作的）

### 5.1 视图截图链路
```
Execute → CaptureViews(app, cimDoc)
  → foreach ViewPlan(4 张)：GetCommandById(id).Execute() → Sleep(1000) → SavePicture(png)
  → RemoveGreenBackground(png)（去绿底+去底部灰条）
  → CropToModelBBox(png)（按模型包围盒裁剪，排除蓝色刀轨/UCS，+5% 边距）
→ ViewSelectForm（预览+勾选）→ 按勾选组装 views → WriteExcel
```

### 5.2 图像后处理三件套
- **去绿底**：绿色主导判定（max==G && G-min>8，灰阶跳过）。
- **去底部灰条**：从底向上扫连续中性灰行（占比>50%）整行换白，仅扫底部 80px。
- **裁模型包围盒**：排除灰阶/绿底/蓝色主导（B=max 且 B-min>20 且 B>100），加 5% 边距，`Bitmap.Clone` + MemoryStream 中转输出 `*_crop.png`。
- ⚠️ 三者都要经 **MemoryStream 中转**写文件（GDI+ 句柄冲突，见 §6.2）。

### 5.3 Excel 图片布局（列分解版）
- 布局坐标：图片用绝对 EMU（x=ColOff、y=锚定行顶+RowOff），锚定行行高设 0，间距 10mm（1mm=36000 EMU）。
- 统一单图宽 80mm（302px @96dpi），高度按 crop 后 PNG 真实比例算 → 三视图天然满足长对正/高平齐/宽相等。
- 写 XML 时：`absX/absY → DecomposeCol/DecomposeRow → (col,colOff)/(row,rowOff) → twoCellAnchor(from+to)`。
- 列宽字符→EMU 官方公式：`px=Truncate(((256*w+Truncate(128/7))/256)*7)`，默认列宽 8.43 字符、默认行高 15pt。

## 6. 沉底经验（踩坑记录，避免重复踩）

### 6.1 编译（此项目唯一解 = VS F6）
- 沙箱内 AI 代编全死：MSBuild.exe 在 Git Bash 段错误(exit 139)；dotnet build 报 MSB4803（.NET Core MSBuild 不支持 UnregisterAssembly）；devenv /build exit 1 无输出；cmd/powershell 被禁。
- 用户本机双击 .cmd 也失败：缺 VS 环境变量崩溃 + 文件关联被抢 + 中文路径编码乱。
- **结论：编译只能 VS F6（x64）**，别再折腾命令行，已被打回两次。

### 6.2 System.Drawing 图像处理（必踩）
- `new Bitmap(文件路径)` 会让 GDI+ 长期持有原 PNG 句柄 → **写回同路径静默失败**。
- 正确模式：`File.ReadAllBytes → MemoryStream → Bitmap → 处理 → bmp.Save(MemoryStream) → File.WriteAllBytes(原路径)`。写到新路径则更安全。
- **静默 `catch { }` 是最危险的失败模式**——故障无痕迹、排障无方向。失败必须写 `.err.log`。

### 6.3 手写 OOXML（零依赖生成 xlsx）
- 必须有 `cellStyleXfs` + `cellStyles` 配对，否则 Excel 报"已修复"。
- **标签必须闭合**：漏 `</xdr:sp>` 会让 Excel/WPS 修复时锚点错乱（看起来像图被遮挡）。生成后做栈扫描验证。
- **图片定位 WPS 铁律**：`colOff/rowOff` 绝不可超过单列宽/单行高（WPS 会叠图）；跨列跨行必须用「整数 col/row 递增 + 单元格内小偏移」表达。
- WPS 保存文件会重写：media 路径（WPS 用 `xl/drawings/media/` 而非标准 `xl/media/`）、重排 drawing id——这些是保存副作用，不是 bug 根因，别被误导。

### 6.4 调试方法（AI 看不到图怎么办）
- 多模态看图有时返回 `[Image from unknown]`，拿不到像素。
- **定量分析代替看图**：Python + PIL + zipfile → 解 PNG、检测包围盒、边缘触边密度（判断是否被裁）、主色统计、解析 drawing1.xml 还原图片矩形、判断重叠/超宽。这套脚本可反复用。

### 6.5 其他
- 加工时间 `TOTAL_TIME` 拿不到：PM 树 XML 无时间字段、CimNcAPI 无该接口，只在 CE 计算日志 UI / 内置 NC 报告变量体系。别再去 XML 里找。
- 去 NC 绿底阈值：若 NC 背景色或渐变变化，需重调判定。

### 6.6 接口归属（pythonnet 反射确认，写代码/写反射脚本别调错）
- 命令类实现**两个接口**：`Enable`/`Execute` 在 **`ICimCommand`**；`ICreateCommand` 是 10 个名字/菜单方法（GetCategoryName/GetCommandName/GetMenuPath/GetToolbarName/GetPrompt/GetTooltip/GetDescription/IsBelongToDoc/ShowInMenu/ShowInToolbar），**没有** Enable/Execute、也**没有 GetBitmap**。
- `GetProcedureById` 在 **`IModel`**（返回 Object 转 IMdProcedure）；`SetProcedureParameter`/`OpenProcedureForEdit`/`CloseProcedure`/`IsNcProcessManagerOpen`/`NcProcessManagerVisibility`/`Regenerate`/`CheckExecutionStatus`/`IsDialogOpen`/`IsProcInExecute`/`GetIdOfEditedNcItem` 全在 **`INcModel`**；`IMdProcedure.EnterEditMode`/`FinishEdit` 存在。
- **`IModel.ProcedureInEditMode` 是属性不是方法**（反射查它用 `GetProperties`，`GetMethods` 查不到）。
- 探查 API 正确姿势：用 pythonnet 反射 `Program\interop.CimNcAPI.dll` 拿精确签名最稳；PowerShell 的 `Assembly.LoadFile` 被安全策略拦（等同 Add-Type）；NC_中文帮助.chm 在沙箱解不开。

## 7. 已知遗留问题（用户明确暂缓，以后再修）

- **俯视图和轴测图「底部显示不全」**：WPS 与右侧栏预览**同时出现**（非 WPS 特有问题），主视/左视正常。
- **怀疑方向（未验证，下次从这里查起）**：`RemoveGreenBackground` 的"去底部灰条"逻辑从底向上扫"连续中性灰行"整行换白，**若模型底部本身是中性灰会被一起抹掉**；随后 `CropToModelBBox` 按包围盒裁剪把缺失永久固化。
  - 佐证：主视图上下留白 215/260、俯视上下 62/72 明显不对称，暗示底部有内容被处理过。
  - 排查入口：dump 处理前后 PNG 对比；或临时令 `grayRun=0` 关闭灰条处理验证。

- **工具栏名 `My Toolbadsar` 未改**（早期模板乱码名）：它是所有按钮的"家"，改名极易让已拖好的按钮全丢，需单独做并接受重拖代价。待办，非遗漏。
- **外部命令图标需 GUI 贴**：`ExternalCommands.ini` 里 5 命令仍 `@0`（X 图标占位），要用 Register_API_Commands.exe「命令图表」字段逐个贴 ICO（`淬锋应用\cuifeng_icons\`），且必须在注册那一步一起贴。
- **跨版本兼容待验证（产品化 M1 核心）**：本外挂按 Cimatron 2024.0 开发，尚未在 2025/2026 实测。拿到别的版本机器后跑 `CimatronProbe\version_probe.py` 验证关键接口是否齐全。
- **LicenseChecker 公钥占位**（产品化 M2）：`PublicKeyXml` 还是占位符，正式发布前需生成 RSA 密钥对（私钥留开发者、公钥填代码），并补一个签发工具。

## 8. 常用路径与验证流程

| 项 | 路径/说明 |
|---|---|
| 当前程式单（默认读这份）| `E:\GZ目录\CE2024\beer\CE2024\科硕机加\程式单_盖板工装 - 五轴_NC.xlsx` |
| 旧测试文件 | `程式单_BBBB_NC.xlsx`（更早期，一般不再用）|
| 当前 NC 源 | `E:\GZ目录\CE2024\beer\CE2024\科硕机加\盖板工装 - 五轴_NC.elt` |
| 参考程式单 | `DZ_NCSetup15.xlsx`（含加工时间 TOTAL_TIME 等，借鉴排版）|
| 代码目录 | `D:\repos\My project workspace\产品开发\淬锋应用\dev\Cimatron-API-C---Example\ClassLibrary1\` |
| CE 原始 XML | `%TEMP%\CimatronNcProcMgr_*.xml`（命令跑完生成，排查字段用）|
| 命令登记表 | `C:\ProgramData\Cimatron\Cimatron\2024.0\Data\ExternalCommands.ini`（真正的命令表，Program Files 下 SourceData\ 那份是空模板）|
| UI 布局缓存 | `C:\ProgramData\Cimatron\Cimatron\2024.0\Data\CommandsLayout.xml`（工具栏/菜单栏分组，删残留壳要 CE 关闭时改这里）|
| 兼容验证工具 | `D:\repos\My project workspace\产品开发\淬锋应用\CimatronProbe\`（version_probe.py 免编译 / CimatronProbe.cs 需 VS 编译）|
| 命令图标 | `D:\repos\My project workspace\产品开发\淬锋应用\cuifeng_icons\`（ICO，注册工具 GUI 贴）|

**验证流程**：关 CE → VS 平台下拉 `x64` → F6 → 确认 `bin\x64\Debug\ClassLibrary1.dll` 时间戳变今天 → 开 CE 跑命令 → 弹窗分组/勾视图 → 发回 xlsx → 定量分析验证（结构/图片/坐标/比例）。

**8/28 成果链**：白底去绿底 → 询问式视图勾选+预览 → 投影布局 → 去"比例1:1" → 底部灰条处理 → 放大1.2+10mm间距 → 修 drawing XML 缺闭合标签 → 裁模型包围盒+统一80mm宽度（满足投影原则）→ **列分解（修 WPS 叠图，已确认）**。

**8/29 成果链**：NC 参数批量编辑器（写回策略链/TP 分组/状态列/刀号只读）→ 淬锋应用整合（BeerTools→淬锋应用、删流程验证/OpenForm）→ 命令注册/布局机制反推（ExternalCommands.ini + CommandsLayout.xml + 动态按钮 ID）→ 图标机制定论（只能用 GUI 贴）→ 产品化 M1（版本探测 + 兼容验证脚本）+ M2（LicenseChecker 骨架）→ 纠正"程式单零 Excel 依赖"。

## 9. 关联

> 分工：本手册是**开发侧**（用 C# 做外挂）；CAM 操作与编程工艺知识在数控库那边。

- CAM 操作与编程 → [[Cimatron与机床操作]]（刀轴定向 / 四轴 / 五轴 / 毛坯 / 最小刀长 / 五轴连接）
- 机床设备总表 → [[机床索引]]
- 编程模板与规范 → [[模板索引]]（后处理走 Cimatron 路线，UG/Mastercam 空壳已删）
- 编程全流程 → [[数控编程流程]]
- 代码与工具 → `D:\repos\My project workspace\产品开发\淬锋应用\`（执行文件在外置仓库，vault 只存 md）
