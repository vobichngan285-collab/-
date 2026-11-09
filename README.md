# 游戏文字助手 V1.6 · 独立广荣引擎兼容性测试 · 2026-11-09

本版只针对 V1.5 的广荣 TTS 加载错误。**OCR 两档、检测范围、边角识别和语音内容均没有调整**，Medium 仍存在用户已报告的十几秒和漏识别现象。

**[下载 V1.6 Windows x64 免安装实验包](https://github.com/vobichngan285-collab/-/actions/runs/42556569339/artifacts/13647478200)**。请将新 ZIP 完整解压到一个新目录，不要覆盖 V1.5；运行 `GameTextReader/GameTextReader.exe`，同目录必须存在新的 `GuangrongHost.exe`。

V1.6 修复的是**程序架构**而非已经证明可用的广荣微软语音：不再使用 PyInstaller 的 ctypes/multiprocessing 子进程调用原版 DLL，改为独立 Windows C++ x64 原生辅助程序加载 DLL、输出 PCM，经匿名管道交回游戏助手，保益悦听不参与，原语速和音量不改。取消了鼠标进入文字框的短提示音，F8 完成只响清脆叮声，延续 V1.5。

**官方真实引擎依然存在兼容性风险：**在干净 Windows 2025 测试机器上，从广荣作者发布的原始 1.1.0 安装包提取完整 `synthDrivers`，用本版 C++ 原生辅助程序加载 `grtts_x64.dll` 时仍返回 Windows **1114**（DLL 初始化例程失败），不是语音已成功播放。真实检验：[官方原版 DLL 兼容性测试](https://github.com/vobichngan285-collab/-/actions/runs/42561840959)。因此不要宣称云希/晓晓已经修好或认为安装 ZIP 就能发声。**官方基础包也不包含云希/晓晓自然语音资源。**

CI 结果：[Windows 构建通过](https://github.com/vobichngan285-collab/-/actions/runs/42556569339)，22 项单元测试通过；独立辅助程序使用 CI 自建模拟 DLL 成功完成音色发现、合成 9600 字节 24kHz PCM、并从真正冻结打包的 EXE 接收 PCM；模拟 DLL 只用于 CI，未放入用户软件。真实广荣 DLL 通过同样的接口**没有初始化成功**。此前给用户的 PyInstallerImportError 表述不正确，V1.6 已将错误归类交给原生进程处理。

V1.6 软件内仍保留「一键准备独立广荣 TTS」，首次需要联网下载作者原版发行包到本软件独立目录，以后不需要联网；若其独立 DLL 不允许初始化，显示具体失败信息，Windows 系统语音依旧可用。请不要为此更改保益悦听设置，也不必重复提交 OCR 或语音诊断。

---

# 游戏文字助手 V1.6 · 广荣独立语音兼容性测试版（2026-11-09）

**[获取 V1.6 Windows x64 免安装包](https://github.com/vobichngan285-collab/-/actions/runs/42556569339/artifacts/13647478200)**；GitHub Actions 成功，22 项单元测试通过。GitHub 的 artifact 有时外面再包一层 ZIP；解压后运行 `GameTextReader/GameTextReader.exe`。

**本版仅修复广荣语音接入链路，不改动 OCR 档位参数。** 之前在 V1.5 中，PyInstaller 打包后的 Python 进程加载广荣 x64 DLL 会报错误或卡住。本次添加自研独立 `GuangrongHost.exe`，由其负责本地原生加载、语音枚举、PCM 合成和向主程序传输音频。原有「一键准备独立广荣 TTS」入口保留，官方资源仍需用户首次主动下载。整个链路不占用或控制保益悦听读屏通道。

**测试成功范围：** 独立 Windows C++ 程序编译成功，模拟 DLL 返回1个语音、生成9600字节24kHz PCM；冻结 EXE→原生辅助程序→模拟 DLL→PCM 的完整链路成功；Windows CI共22个单元测试、双档 OCR 冒烟测试、无障碍和 UIA 冒烟测试均通过。

**尚未成功的关键范围：** 使用广荣作者**未经修改**的真实 `grtts_x64.dll`，在干净 Windows CI 上通过原生程序依然报 `ERROR 1114`（DLL 初始化例程失败），没有实际声音输出；[真实组件验证日志](https://github.com/vobichngan285-collab/-/actions/runs/42561840959)。**因此不能说广荣微软自然语音已修复。** 用户 Windows 系统如能独立加载，可通过语音下拉框和试听验证；如果不能，当前包可能同样报告1114。真实的云希/晓晓自然语音不包含在基础发布包内。

第二档 Medium 超过10秒、边角漏字和 OCR 返回不全**不在本次修复范围内**。

---
# V1.5 独立广荣 TTS 兼容性实验版 · 2026-11-09

本项目 Windows 11 x64、完全离线 OCR，免安装 ZIP（不需要安装保益悦听、NVDA 或另外寻找 DLL）。

**[下载 V1.5 免安装 ZIP](https://github.com/vobichngan285-collab/-/actions/runs/42513309243/artifacts/13630307332)**：解压运行 `GameTextReader/GameTextReader.exe`。GitHub Actions artifact 外层可能还有一个 ZIP。用户可从聊天直接获取已校验 ZIP。

### 这次实验怎么操作
1. 完全退出旧版程序，将 V1.5 解压到新目录，运行 EXE。
2. 点击 **「一键准备独立广荣 TTS（首次需要联网）」**。本按钮自动从沈广荣 Github 官方发行版 1.1.0 下载 **158,891,643 bytes** 的 `.nvda-addon` 原版，校验 GitHub 发行资产 SHA-256 `14ba0d4155549a1e4b76335687c960815c87e16f3e34907e1476d206c3609a77`，解压里面的 `synthDrivers` 到 `%LOCALAPPDATA%\GameTextReader\GuangrongIndependent`。**只下载一次，以后在该设备离线使用**。不捆绑第三方 DLL/自然音库。
3. 等待语音列表刷新。如果出现「广荣 · ...」，选择该项并点击 **「试听」**。这是完整独立子进程，不向保益发出任何 `BoyCtrl` 调用，也不改变保益的语速/音量。
4. 点击 **「试听提示音」**，仅发一声清脆的「叮」。F8 识别完成也只发这个提示音；鼠标进入文字框不再发提示音，但仍会按原逻辑朗读文字。
5. 如果广荣没有出声、没有出现在列表或提示加载失败，点击 **「复制链路日志」** 和 **「复制语音诊断」**，回传日志文本。这次不需要查找任何 DLL。

### 验证与限制
- [Windows Actions 42513309243](https://github.com/vobichngan285-collab/-/actions/runs/42513309243) **Success**，21 项单元测试通过；源代码和打包 EXE 双档 OCR 中文/英文图片、SAPI+WinRT 合成数据、无障碍 Tk UIA、绿色文字框及完整主窗口初始化均通过。实际游戏画面、用户扬声器仍必须真机验证。
- 官方发行版中 **32 位 DLL 为 `grtts.dll`、64 位 DLL 为 `grtts_x64.dll`**，V1.4 错用了 32 位文件。新版本现在选择官方 64 位引擎。
- **兼容性风险：** 在无 NVDA 的干净 Windows 2025 CI 上，`grtts_x64.dll` 使用正确依赖和目录仍在加载阶段报 `WinError 1114`。因此本包定位为**独立广荣兼容性实验**，不声称已经实现自然语音合成。用户机器可能有不同依赖/Windows 环境，须实测。
- 广荣 1.1.0 官方基础包含永德及默认讯飞，**不包含云希、晓晓等按需下载的微软自然语音包**。这一步首先验证独立引擎，不保证这两种音色已经可用。
- **保益悦听读屏通道已彻底退出开发路线**。此前未完成的 BoyCtrl 分支已回退至旧 V1.4 main 基准，新版没有 BoyCtrl DLL/代码，保益仍可按自己的语速正常读屏。
- OCR、绿色框和无障碍依旧用 V1.4 路线。本次仅替换/修正独立 TTS 接入及音效；V1.4 Medium 速度与边角漏字仍是独立待修复事项，不能将本包表述成已经修好了这些问题。
- 最终 ZIP：`GameTextReader_V1.5_Windows_x64_Portable.zip`，**194,303,280 bytes**，SHA256 `0260fd7001c34cf5efcc7f7e129c8b5258f92c9bbf0288e5cdeca3a9c9c8060f`。已下载到独立环境，CRC 通过，含 EXE+3个官方模型且不含任何 `grtts.dll` 或 `BoyCtrl`。GitHub artifact id **13630307332**；到期 2026-12-08。
- 完整历史见下方旧版本记录，保持原有提交历史；与安卓蓝星视觉/看字助手无关，Android 仓库没有改动。

---

# 游戏文字助手 V1.4 修复测试版 · 2026-11-09

**Windows 11 x64 · 完全离线 OCR · 免安装 ZIP**。请完整退出旧版本、将 ZIP 解压到新文件夹、运行 `GameTextReader/GameTextReader.exe`。

- [V1.4 GitHub Actions Windows 成功构建、免安装 ZIP 下载](https://github.com/vobichngan285-collab/-/actions/runs/42508035692/artifacts/13627842980)。聊天还提供了经 CRC 与 SHA256 验证的直接 ZIP。GitHub Artifact 下载本身可能外套一层 ZIP。
- **第二档由“完整 Medium DET+REC”改成“Small 快速检测 + Medium 识别”**，并按最长边限制检测输入（Small 1280、Medium 1152）。不再反复让耗时的 Medium 检测器做全屏定位。**如实保留检测器区别**，模型选择文字也同步更正。
- 只内置三个 PP-OCRv6 ONNX 模型：Small DET / Small REC / Medium REC（去掉不用的 Medium DET 权重）。体积减至 **194,319,209 bytes / 185.3 MiB**，SHA256 `6bd0f223e07a6c6117bd08a752484fba8484aa641efeeaf8320df62c4a8b6ddd`。
- **短音效**采用独立 WinMM waveOut 播放句段完成／进入新文字区域的短金属声，失败回退到 Windows WAV 文件播放；“试听提示音”将音效分隔播放，另有“试听系统提示音”用来排查设备静音。用户电脑实际出声仍需要真机确认。
- **修复鼠标离开区域就立刻停止尚未起声语音的竞态**：进入新区域立即朗读/打断旧句；短暂离开区域仅隐藏绿色框，不再取消刚合成的句子。F8、清空、60 秒到期仍立即停止和删除。
- **广荣 TTS 新增实验性接入**：自动尝试发现用户 NVDA 标准安装目录的 `grtts.dll`，其他安装方式通过“选择已安装的广荣 DLL”按钮选择用户现有文件。底层通过独立子进程调用 `YongDe_*`，支持声音列表、语速/音量、停止和同步 PCM／流式合成回退；不会附带第三方 DLL、语音包、许可证，也不会修改微软许可。**保益悦听具体 DLL 兼容性、云希/晓晓的实际声音输出尚未在用户机上验证**，如果选择不到则保持 SAPI/WinRT 备用。
- WinRT 语音改为把合成流保留至 MediaEnded，加入播放失败回调与音频状态日志，使用默认多媒体输出类别。**接口成功不等于扬声器必定有声**。
- 保留已验收的保益悦听 UIA 兼容、绿色文字框、F8 手动截屏、60 秒硬过期；**绝不恢复自动画面检测**。
- [Windows CI 42508035692](https://github.com/vobichngan285-collab/-/actions/runs/42508035692) **success**：17 项单元测试强制全过，实测 Small 与 Medium 混合两档在英文与暗色中文合成游戏菜单有识别结果，冻结 EXE 双档 OCR/Windows 本地语音合成/UIA/绿色框/完整窗口均运行通过。CI 没有安装用户的真实广荣 DLL，无法代替真实游戏和真实扬声器测试。
- 实机验收建议：先选 Medium 按 F8 看识别行数、耗时和文字框；“试听提示音”检查分离播放；分别试听 SAPI、WinRT；再选择电脑已合法安装的 `grtts.dll`，在语音下拉框中选择“广荣 · ...”试听。出现任何无声/空结果，点击“复制链路日志”发文字，不包含 OCR 原文、截图或音频。

---

# V1.3 Windows 游戏文字助手 · 2026-11-09 修复与诊断版

**下载**：[Windows 11 x64 免安装 ZIP（已通过 Windows CI）](https://github.com/vobichngan285-collab/-/actions/runs/42504162008/artifacts/13627010787)，直接解压运行 `GameTextReader/GameTextReader.exe`。GitHub 下载有一层外部 artifact ZIP，聊天提供的直接文件无需重复解压外层。**用户机器实际游戏、音效、云希/晓晓尚未验收。**

- **从代码中删除了整个自动画面变化检测模块和后台截图线程**，避免游戏动画导致错清结果。现在只按 F8 立即清除上一批 OCR 文字/坐标/框/语音并刷新，或在 60 秒后自动清空。因此切屏后若没有再按 F8，旧识别结果可能在到期前继续存在。
- Small/Medium OCR 模型仍为原官方 PP-OCRv6 DET+REC，且已在 Windows CI 上对英文和暗底中文菜单分别成功识别。Medium **不是坏模型**；它的完整 DET 推理计算量更大。在该 CI 测试图中 Medium 检测约 2.60 秒、Small 检测约 0.62 秒；真实游戏延迟以新诊断数据为准。
- 软件后台预热**当前选中的一个** OCR 模型（RapidOCR 首次调用懒加载，必须有真实文字触发 REC 加载），避免平时按 F8 才开始冷启动；OCR 模型切换后再次预热。删除一次重复的 RGB 全屏复制，打开的设置窗口隐藏后从 250ms 等待缩短到 100ms。
- **新增「复制链路日志」**：区分截图、OCR 初始化/等待、推理、raw 与有效文字行数、鼠标命中、TTS 提交、WinRT 播放器状态、音效接受与错误；日志不含照片或识别文字。新增独立的「试听提示音」按钮。
- 提高两种原创金属/短嗒提示音的可辨度，并在失败时显示提示（不会阻塞 TTS）。无障碍 Tk UIA 和绿色 click-through 文字框保留。
- **用户报告无声问题尚未在用户机器定位完成**。Windows CI 本次真正用 SAPI 生成了 131862 字节 WAV，也通过 WinRT 生成了 66286 字节的语音流；这是**合成成功，不等于扬声器播放成功**。云希/晓晓 Narrator 专用自然音色若未对第三方公开 API 开放，仍不会出现在列表中。
- CI [42504162008](https://github.com/vobichngan285-collab/-/actions/runs/42504162008) 最终 **success**，14 个逻辑测试、源代码和打包 EXE 上 Small/Medium 英文与暗底中文 OCR、SAPI/WinRT 音频生成、UI 无障碍和实际 EXE 启动均通过。
- `GameTextReader_V1.3_Windows_x64_Portable.zip`：**232059188 字节（约 221.3 MiB）**，SHA256 `8ddd216b4aa012630c2ed8e70776e22700738d5e46ad7a7582b3cbc8fd39b67e`；唯一提供绿色 ZIP，不再制作安装器。

### V1.3 真人实机定位步骤

选择一款 SAPI 声音（如 Huihui Desktop）并点击「试听」；再选择 WinRT 的中文声音并点击「试听」，比较两者。单独点击「试听提示音」。进入游戏、F8 识别并鼠标指向文字后，打开主窗口点击「复制链路日志」，复制文本发送。若识别了零行，日志会明确显示是 OCR 未返回有效文字，而不是把它误报成 TTS 故障。请确保音频输出设备/音量混合器没有静音。保益悦听和绿色框在 V1.2 已由用户反馈可以正常使用，V1.3 没替换这些控件。

---

# 游戏文字助手 V1.2 · Windows 11 免安装版

**当前开发版本：V1.2（2026-11-09）。** Windows x64 单击运行，不需要安装 Python。可下载 [V1.2 Windows Actions 构建产物](https://github.com/vobichngan285-collab/-/actions/runs/42500629157/artifacts/13625800422)（GitHub 产物下载外层 ZIP 里有绿色版 ZIP）。

- 一次 F8 离线截图 OCR，PP-OCRv6 Small/Medium，两档模型都已随程序打包；不连续运行 OCR。
- **鼠标进入新文字区域立即朗读，无 150ms 人为等待**；同一区域不重复，移动到别的区域中断上一句。
- 实际朗读区域的绿色原生 Windows 透明鼠标穿透边框（短菜单单独框、明显连续长文本谨慎合并），移动时一声极短轻音。
- OCR 完成仅播放原创低音量机械式短音效；不再语音播放识别行数或坐标。
- 一次 OCR 的文字、坐标、绿色框、朗读状态在**60 秒时全部删除**；明显画面变化时提前删除，检测只比较 160×90 的缩略截图，不重复 OCR。**不是 100% 精确的切屏识别**，小画面变化可能漏检，动画可能误判；切屏后可直接按 F8 使旧结果立即失效并重识别。
- Tk 窗口集成 tk-uia（MSAA / Windows UI Automation）辅助技术适配，控件可提供无障碍名称和值；**保益悦听具体效果仍须用户电脑验收**。
- SAPI/WinRT 正规本地语音接口，增加可调用中文优先、可复制的 TTS 与系统讲述人语音包诊断。Windows 安装了 **云希/晓晓** 不等于第三方 SAPI/WinRT 可以播放；目前**未保证能调用讲述人专用自然语音**，也不包含许可证修改或保护机制绕过。
- 只有绿色 ZIP：解压整个目录，运行 `GameTextReader/GameTextReader.exe`，退出旧版后再开新版本。
- V1.2 ZIP 为 **232,053,692 bytes（约 221.3 MiB）**，SHA-256 `0d4f9673194c6e82707204260d0bc1e0cee341a3e143a280888443411549a78b`。
- Windows CI [42500629157](https://github.com/vobichngan285-collab/-/actions/runs/42500629157) **success**：14 项单元测试、Small/Medium 在打包 EXE 中实际识别、系统 TTS 接口、UI Automation 和边框构建、完整主窗口启动全部通过。不代表实际游戏及保益悦听已验收。

---



## 2026-11-08 · V1.1 免安装轻量版（当前）

**请优先下载 V1.1，不要继续用旧 V1.0 排查 OCR。** 这次把过大的 PaddlePaddle/PaddleX 推理栈替换为 RapidOCR + ONNX Runtime，保留百度飞桨 PP-OCRv6 Small/Medium 双档，重复权重已删除。只发布 ZIP 绿色版。

- [Windows V1.1 成功构建及下载](https://github.com/vobichngan285-collab/-/actions/runs/42494853633/artifacts/13622743874)（GitHub 产物含一层包装 ZIP，下载后解开即得到绿色版 ZIP）
- 原始绿色版 ZIP 大小：231816213 bytes，约 221 MiB；SHA256 `55d3ec8989012ef9f57b32b4f9c918ae59a83c4325491e8a6dd151505b51426e`。
- CI 已实际运行 Windows EXE，Small/Medium 两档 OCR 均通过；SAPI 与 WinRT 本地语音枚举及打包测试通过。
- **尚未真实验证用户机器上的云希/晓晓**。WinRT 只能调用系统开放的本地语音；用户 Windows 11 讲述人音色不保证开放给普通应用；不注入许可证或修改系统保护。
- 先退出旧 V1.0，再解压运行 `GameTextReader/GameTextReader.exe`，无需安装 Python。配置仍保存在 `%LOCALAPPDATA%/GameTextReader/settings.json`。
- 详细实测和修复记录见 `RELEASE_STATUS.md`。旧 V1.0 历史保留。

# 游戏文字助手 V1.0 — Windows 11 独立版

**状态：Windows 安装包和便携版已成功构建，等待用户真机验收。**

## 功能

- **单键触发**：默认 F8，可在软件里直接按一个按键更改；按键从松开到按下只截图一次。
- **本地截图**：以鼠标所在显示器为范围，按原始像素捕获画面，不上传截图。
- **双本地模型**：百度飞桨 PP-OCRv6 Small（默认）/ Medium 的检测 + 识别模型；坐标映射回 Windows 绝对屏幕位置。
- **鼠标指向朗读**：鼠标悬停于识别出的行矩形约 150ms 后，SAPI5 本地 TTS 朗读。重复停留不重复读；移开时中断；移到另一行读新行。
- **手动刷新**：切换游戏菜单再次按快捷键截屏识别，不在后台持续 OCR。
- **保存设置**：`%LOCALAPPDATA%\GameTextReader\settings.json`；不上传文字或配置。
- **最简设置**：单键、模型、可检测的 SAPI 本地声音、语速、停留时间。

## 已知边界

- 这是**截图阅读**，不能知道游戏菜单内部“真实选中项”。
- 部分独占全屏游戏、受保护画面、抗作弊程序可能拒绝普通桌面截图或拦截单键；应优先测试无边框窗口模式。
- 如果游戏使用自绘鼠标，窗口 API 的鼠标物理坐标可能与画面内鼠标外观不同，需实际测试。
- 只有 Windows SAPI5 正式枚举出来的声音才可在列表中选择；讲述人自然语音云希/晓晓 **不保证** 能通过 SAPI5 直接调用。**不会内置微软许可声明或绕过系统的代码。**
- 当前第一版仅 CPU OCR，第一次加载 Medium 可能较慢。
- 多显示器选择使用截图时鼠标所在显示器；Windows 缩放按每监视器 DPI aware 处理。
- 不做背包动态 OCR、实时连续识别、云端调用、注入游戏、外挂或内存读取。

## Windows 源码运行（开发者）

要求 Python 3.11 x64；安装包用户不需要此步骤。

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-win.txt
python -m pip install pytest
python prepare_models.py
python -m pytest -q tests
python main.py
```

首次制作安装包需要联网下载官方 OCR 权重，**安装后运行无需联网**。

## Windows 安装包制作

仓库内 `.github/workflows/build-windows.yml` 可在有 GitHub Actions 的独立项目仓库中生成：

- `GameTextReader_1.0_Windows_x64_Setup.exe` （Inno Setup 安装包）
- `GameTextReader_1.0_Windows_x64_Portable.zip` （无需安装的绿色版）

构建流程：Windows x64 安装 PaddlePaddle 3.2.0 + PaddleOCR 3.7.0、进行纯逻辑测试、下载四个官方模型目录、PyInstaller 打包、用 Inno Setup 制作安装程序、上传构建产物。

**注意：** 自动化脚本能否在某个 Windows runner 上成功打包，需要真实跑过 Actions 才能判定；PyInstaller 成功也不代表游戏截图、鼠标匹配和微软自然语音已经真机通过。

## 真实电脑验收顺序

1. 安装并启动；选择可试听的本地声音，按“试听”确认。
2. 在桌面打开一个含清晰中英文的窗口；最小化本软件，按 F8；等待识别结束，移动鼠标到文字上检查读音和位置。
3. 切换 Medium，重复同样场景并比较准确率。
4. 在游戏的**无边框窗口菜单**测试 F8、鼠标位置和语音中断；记录游戏名、分辨率和 DPI 缩放。
5. 关闭网络重新测试截图和语音；云希/晓晓须单独确认能否被本地 SAPI 列表发现和试听。

## 安全与许可

不修改 Windows 系统 TTS 注册表、语音许可文本、游戏数据或反作弊模块。PaddleOCR 及模型来自 PaddlePaddle 官方、Apache 2.0；分发前附加第三方依赖的许可文件与声明，并检查实际下载的模型许可证。开发工具 PyInstaller 的构建结果仍需审计全部依赖。


## Windows V1.0 构建结果 · 2026-11-08

- Windows Actions [42489455957](https://github.com/vobichngan285-collab/-/actions/runs/42489455957) **success**，构建源码 commit `bbe6efa70d8544f510507927defcf45401253d71`。
- Windows 安装依赖成功、6 项单元测试通过、4 个离线 PaddleOCR 模型已预装；PyInstaller、Inno Setup、上传均通过。
- 产物拆分 Actions [42490230612](https://github.com/vobichngan285-collab/-/actions/runs/42490230612) **success**。
- [Windows 安装包下载](https://github.com/vobichngan285-collab/-/actions/runs/42490230612/artifacts/13620224927)；[便携版下载](https://github.com/vobichngan285-collab/-/actions/runs/42490230612/artifacts/13621181984)。GitHub 可能要求登录。
- 安装版 `GameTextReader_1.0_Windows_x64_Setup.exe`，299,233,680 bytes，SHA256 `5b266f19886c028754903466cfad88bb6113cc20428a68150b8bdbd61bfb038d`。
- **Windows 11 实际安装、游戏截屏与鼠标位置、TTS 朗读、云希/晓晓仍未经过用户电脑测试。**
