# V1.0 开发验证记录 — 2026-11-08

## 已实现源码

- Windows 11 x64 单键（F8 默认）状态监听，按键可以由用户在软件内重设。
- 以鼠标所在显示器截图；每监视器 DPI awareness；屏幕截图与 Windows 系统绝对鼠标位置对齐。
- 离线 PaddleOCR 3.7：PP-OCRv6 Small / Medium 两档，各自 DET + REC；OCR 结果返回文字行、矩形与置信度。
- 鼠标停留约 150ms 读取对应行；换行取消旧朗读；同一行不反复播报；人工按键刷新。
- Windows SAPI5 本地 TTS 枚举，语音选择、试听、语速、音量调节；Windows 11 自然语音是否暴露 SAPI5 依赖实际系统/适配器情况。
- 设置写入 LOCALAPPDATA，OCR 文字只存在内存，无网络请求。
- GitHub Actions Windows runner 构建 PyInstaller EXE 及 Inno Setup 安装程序的工作流脚本。

## 已执行检查

- Python 编译检查：通过（Linux）。
- 单元测试：6 项通过（Linux），包含 OCR 坐标解析、负屏幕坐标、文字置信度过滤、重叠文字框命中、鼠标悬停与防重复等。
- 代码目视审核：未发现调用 Azure / Edge 网络 TTS、微软许可证覆盖、游戏进程注入、反作弊绕过。

## 未完成、不得宣称成功

- Windows runner 实际安装依赖 / 模型下载 / PyInstaller / Inno Setup 构建：未执行。
- Windows EXE 安装包：未生成。
- Windows 11 原生 SAPI TTS 试听：未运行。
- 游戏中实际 F8 响应、截屏、分辨率坐标匹配、讲述人云希/晓晓兼容性：未真机验证。
- 官方权重二进制文件：当前源码包中未内置；工作流计划在联网 Windows runner 下载后随 EXE 打包。

## 限制和后续处理

当前会话执行容器为 Linux，未提供 Windows 执行器，无法在本机直接编译原生 Windows EXE。要生成可下载安装的 EXE，必须让工作流运行于独立的 Windows CI 环境（例如用户授权的 GitHub 仓库及 Actions），并验证实际构建结果。不可将源码压缩包冒称为安装包。


### 追加：Windows 构建成功（2026-11-08）
上述“未完成/未构建”是当时状态，保留历史。现在 Windows 构建已经完成；真实游戏验收仍未进行。

## Windows V1.0 构建结果 · 2026-11-08

- Windows Actions [42489455957](https://github.com/vobichngan285-collab/-/actions/runs/42489455957) **success**，构建源码 commit `bbe6efa70d8544f510507927defcf45401253d71`。
- Windows 安装依赖成功、6 项单元测试通过、4 个离线 PaddleOCR 模型已预装；PyInstaller、Inno Setup、上传均通过。
- 产物拆分 Actions [42490230612](https://github.com/vobichngan285-collab/-/actions/runs/42490230612) **success**。
- [Windows 安装包下载](https://github.com/vobichngan285-collab/-/actions/runs/42490230612/artifacts/13620224927)；[便携版下载](https://github.com/vobichngan285-collab/-/actions/runs/42490230612/artifacts/13621181984)。GitHub 可能要求登录。
- 安装版 `GameTextReader_1.0_Windows_x64_Setup.exe`，299,233,680 bytes，SHA256 `5b266f19886c028754903466cfad88bb6113cc20428a68150b8bdbd61bfb038d`。
- **Windows 11 实际安装、游戏截屏与鼠标位置、TTS 朗读、云希/晓晓仍未经过用户电脑测试。**


## V1.1 免安装版 · 2026-11-08（接续记录，不覆盖 V1.0）

- **用户实测 V1.0 的问题**：Windows 11 上未显示云希/晓晓自然语音；点击截图 OCR 报“识别失败”，但当时缺少具体错误堆栈。
- **主要技术调整**：不再打包 PaddlePaddle/PaddleX，改用官方 PP-OCRv6 Small / Medium 双档 ONNX 权重 + RapidOCR 3.10.0 + ONNX Runtime；维持离线、原始文字坐标及鼠标指向朗读。
- **TTS 调整**：兼容 SAPI 语音，同时尝试系统公开的 Windows Runtime 语音枚举、播放；未注入微软许可证、不破解系统保护。讲述人专用云希/晓晓是否对第三方暴露，**尚未在用户电脑验证**；SAPI 语音继续作为备用。
- **诊断**：OCR 失败记录阶段、异常类和堆栈到 LOCALAPPDATA/GameTextReader/last_ocr_error.txt，界面有“复制失败诊断”，不会记录截图或 OCR 文字。
- **体积优化**：PyInstaller 两套模型重复收集到 rapidocr/models 与独立 models，已在构建时删掉四个重复权重，再跑实际 EXE OCR 自测以确保不是误删。
- **仅交付绿色版**：不再生成安装程序。Windows Actions 成功任务 https://github.com/vobichngan285-collab/-/actions/runs/42494853633 ，构建源码 commit `114b33680bf7f5f3e6ca1471810e897c2fa959a6`。
- **真实 Windows CI 验证**：8 项基础测试、Small/Medium 模型初始化、PyInstaller Windows EXE 运行 OCR 双档实际推理、打包 WinRT/SAPI 声音枚举测试、四个本地权重存在性、ZIP 上传均成功。
- **交付文件**：GameTextReader_V1.1_Windows_x64_Portable.zip ，231816213 bytes（约 221 MiB）；SHA256: `55d3ec8989012ef9f57b32b4f9c918ae59a83c4325491e8a6dd151505b51426e`。
- **GitHub Artifact**：https://github.com/vobichngan285-collab/-/actions/runs/42494853633/artifacts/13622743874 ，2026-12-08 到期；亦有当前对话交付的直接 ZIP 文件。
- **严格区分**：CI 打包后 OCR 识别通过，不等于已通过用户真实 3A 游戏截图、鼠标坐标和云希/晓晓播放验收。用户下一步应先退出旧 V1.0，解压绿色版运行；用简单桌面文字测试，再进游戏。


## V1.1 用户真机反馈与待办记录 · 2026-11-09（仅记录，暂不实施）

用户在 Windows 11 实机运行绿色版 `游戏文字助手 V1.1` 并提供截图：

- **OCR 已能成功执行**：截图显示界面状态“识别完成：87 行，2030 毫秒”，下方已列出文字及屏幕坐标；与 V1.0 的“识别失败”不同。此处只说明该次截图识别成功；游戏内鼠标导航、阅读顺序仍未宣布验收。
- **微软自然语音问题仍在**：声音列表显示 SAPI Huihui/Zira 与 Windows Runtime Huihui、Yaoyao、Kangkang 等，但用户要求的微软 **云希（Yunxi）和晓晓（Xiaoxiao）仍不可选/无法使用**。用户此前在 LunaTranslator 中通过特定 config.json 许可配置调用过这两款音色；后续需分析实际调用方案和授权边界，不能把其他同名在线音色冒充离线。
- **修改请求 1 — 截屏完成反馈**：每次按自定义截图键（默认 F8），识别完成时只播放 **清脆、低音量、类似 Zippo 打火机的短提示音**；不要再用 TTS 朗读“识别完成、共多少行”等状态，也不要把 OCR 文字坐标当作语音提示播报。**鼠标指向文字的正常 TTS 朗读必须继续保留**。提示音需要实机试听确认音色。
- **修改请求 2 — 旧画面结果失效**：用户读完当前画面并切换游戏菜单/场景后，必须及时删除或作废上一画面的 OCR 坐标与文本，立即停止旧朗读，避免鼠标在新画面错误命中旧文字而乱读。具体画面变化判定机制待下一步指令决定，不能未经测试擅自承诺精准自动识别切屏。
- **当前明确要求**：**先记录以上问题和需求，等待用户下一条命令**。不修改应用代码，不启动构建，不发布版本，不覆盖原 V1.0/V1.1 产物。


## V1.2 汇总修复和发布验证 · 2026-11-09

**用户授权**：在此前已确认的九项任务上集中开发，Windows 11 x64 只交付免安装版；不改 Android 蓝星向导。

### 已编写代码
- 零人为停留时间：`HoverTracker(0)` 在首次进入新文字框即触发语音，鼠标保持在原框不重复；输入轮询 20ms。
- 自适应文字高亮：OCR 文字段落谨慎合并为朗读单元；用原生 Windows Topmost/Layered/Transparent/NoActivate 四段薄边窗绘制绿色区域外框。外框本身不拦截鼠标。
- 两种原创低音量声音：F8 识别完成单次极短机械金属声（不再播报识别行数），鼠标进入新区域时轻短音；声音在独立线程播放不阻塞朗读。
- 全量作废：一按 F8 就删除上一批文字/坐标/框选、取消旧朗读；新结果保存 60 秒，时间到自动彻底清除。画面检测在后台每约 0.24 秒获取缩小到 160×90 的画面（无额外 OCR），发生大变化一次或中变化连续两次后提前作废全部旧 OCR、鼠标框和音频。
- 使用 `tk-uia==0.8.0` 为 Tk/ttk 元件提供 Windows MSAA/UI Automation 控件语义，主动命名关键按钮/音色列表/滑块/状态及识别文本字段。
- TTS 保持 SAPI + WinRT 正规接口，优先实际**可调用**的中文音色，增加已安装讲述人自然语音包与 SAPI/WinRT 可调用清单的区别和“复制语音诊断”，备用传统本地语音。**云希/晓晓专属 Narrator 音色若未通过公开 API 暴露，仍未能保证在此 app 播放；没有采取密钥提取或许可证绕过。**
- UI 不再把文字坐标写入可读结果文本；失败仍有复制异常日志功能。
- 继续维持 RapidOCR + ONNX Runtime，Small/Medium 两档四个官方 v6 模型，禁止运行时联网下载模型。

### Windows 真机 CI 结果和明确边界
- 发布源码构建基准 `25901e79f5b166ee119368eef2cd51cd77ead657`；Windows Actions [42500629157](https://github.com/vobichngan285-collab/-/actions/runs/42500629157) 最终 **success**。
- Windows x64 14 项逻辑测试全部通过；PyInstaller EXE 打包后真实 Small+Medium OCR 推理均通过；声音接口与可调用系统音色枚举通过；独立 tk-uia UIA 和四段 Win32 透明高亮窗测试通过（`Strategy.PROVIDED`）；**完整 V1.2 主窗口实际实例化启动测试通过**。
- 唯一交付：`GameTextReader_V1.2_Windows_x64_Portable.zip`，232,053,692 bytes（221.3 MiB），SHA256 `0d4f9673194c6e82707204260d0bc1e0cee341a3e143a280888443411549a78b`。外层 GitHub artifact 为 [13625800422](https://github.com/vobichngan285-collab/-/actions/runs/42500629157/artifacts/13625800422)，到期 2026-12-08；用户还可使用聊天的已校验直接 ZIP。
- **未经过**用户游戏场景、保益悦听朗读、用户机器 Yunxi/Xiaoxiao、实际声效偏好、各类全屏游戏覆盖层/画面变化识别的验收。切屏识别是轻量启发式，不可能保证所有游戏的所有变化都立即识别；一分钟的强制清理是可靠兜底。
- 若用户反馈失败，优先收集“复制失败诊断”/“复制语音诊断”、游戏是否无边框窗口、当前生效音色，再针对具体结果调整；不要把 CI 成功说成最终实机通过。

### 后续处理
- 保留 V1.0/V1.1 历史和测试包。不自动新增其它功能；实机反馈后再开发。


## V1.3 · 2026-11-09 纠错和有证据的链路排查记录

**用户最新真机反馈**：V1.2 Medium 模式“没有结果/没有声音”、云希/晓晓仍无法使用、两种新增提示音没有听到、F8 至反馈声相隔数秒；明确要求**直接删除自动画面变化检测**。与此同时保益悦听现在能够操作界面，绿色文字框已经出现，必须保留。

**根因与待验证点分开记录：**
1. V1.2 用户截图确实显示“检测到游戏画面变化，旧文字和框已全部清空”；背景动画触发轻量图像差异检测，导致 OCR 结果失效，这是已确认的链路问题。完整删除 `game_reader/screen_change.py`、后台截图循环、界面触发、对应测试；保留 F8 即清和 60s TTL。转场后不按 F8 仍可短暂读取旧文字是明确的折中，不能声称自动切屏清除。
2. 两档 OCR **在 CI 可实际正常输出暗底中文游戏菜单**：“继续游戏”与“游戏设置”各两行均被成功识别。中间一次 CI 检查失败，是新增中文范围判断的错误转义导致误报，已修复并重跑通过。因此“Medium 在用户游戏截图没有结果”不能归咎于模型普遍不能识别，具体图像和 raw/effective counts 仍需用户实机验证。
3. RapidOCR 3.10 首次运行懒加载，当前 V1.2 每次模型切换后重新创建推理器、首次推理慢；完整 Medium DET 的 Windows CI 性能明显慢于 Small（测试英文图 DET 约 2.67s vs 0.68s，暗底中文图约 2.60s vs 0.62s）。V1.3 在 UI 后台对**当前选择**的模型用真实文字预热 DET+REC；没有同时长期持有两套模型，避免内存翻倍；同时减少多余 RGB 转换，GUI 最小化的等待从 250ms 降至 100ms。不能承诺真实机器从数秒降到毫秒级。
4. V1.2 提示音 WAV 振幅很小（完成音仅 75ms，悬停音 38ms），且 `CuePlayer` 没有错误回报，静音可能由音量、驱动或硬件路由造成。新版本增加时长/可听度、线程事件回报和“试听提示音”独立按钮。Windows CI 对 WAV 峰值、格式做验证，不假称实际扬声器已出声。
5. TTS 依旧是 SAPI + 正规 WinRT 两个路径。CI 以前只看 voice list，测试范围不足；本版实际使用 SAPI `SpFileStream` 生成 131862 字节 WAV、WinRT `SynthesizeTextToStreamAsync` 生成 66286 字节语音流，**无法由 CI 证实用户音频端点播放**。现在增加“复制链路日志”，记录模型阶段、命中、语音提交、WinRT 播放器状态、音效回报（仅元数据，不记录 OCR 内容），让下一轮实机精确定位。
6. 讲述人云希/晓晓语音包**系统已安装但未暴露给公开 SAPI/WinRT**，本版未实现专有 Embedded SDK 的授权桥接；音色问题仍列作未解决，不复制他人许可证/解锁密钥。
7. 用户反馈保益悦听 UIA 可访问且绿色框出现。新版本未改掉 `tk-uia`、按区域画边框、零人为鼠标停留等待这些已得到正面反馈的功能。

**发布/检验**：
- GitHub 分支 `game-text-reader-v13-audio-speed-20261109`，成功 Windows Actions [42504162008](https://github.com/vobichngan285-collab/-/actions/runs/42504162008)，源代码构建 commit `14458757b3afa3c8acd2d96ccbbaeaab3e77729d`。
- 14 个测试通过；SAPI 真语音合成 WAV、WinRT 真语音流生成通过；独立二档 OCR 中英文实图（合成暗底菜单）源运行和打包 EXE 都通过；无障碍与绿色框测试通过；完整 EXE UI 初始化测试通过。
- 只交付 `GameTextReader_V1.3_Windows_x64_Portable.zip`，232059188 bytes，SHA256 `8ddd216b4aa012630c2ed8e70776e22700738d5e46ad7a7582b3cbc8fd39b67e`，已在容器校验 ZIP 无损坏、EXE 及四个权重存在。GitHub artifact [13627010787](https://github.com/vobichngan285-collab/-/actions/runs/42504162008/artifacts/13627010787)，保留 30 天。
- 用户实机尚需逐一验收 **SAPI 试听**、**WinRT 试听**、**两种短音效**、**Small vs Medium F8 实际耗时与行数**；不要提前声称自然语音问题、Medium 游戏屏幕识别问题或硬件出声问题已彻底解决。
- 保留所有 V1.0/V1.1/V1.2 历史；Android 仓库未触碰。


## V1.4 修复版 · 2026-11-09 · 最新真实构建与待验收

**用户直接授权开发并要求先汇总再生成**。根据用户实拍 V1.3 照片：选择第二档 Medium 后界面仍显示“正在识别新画面...”且尚无结果，F8 耗时过长；完成提示音和鼠标移动/进入文字框的短声没有听到；微软云希/晓晓无法选择；保益悦听 UIA 和绿色框已成功出现，不得破坏。用户明确要额外接入沈广荣“广荣微软 TTS”；此前单纯 SAPI/WinRT 路线未解决。

### 本轮准确变更
1. 第二档不再运行慢速 Medium 文本检测模型；使用**PP-OCRv6 Small DET + Medium REC** 混合路径，Det.limit_type=max，Small 最长边1280／Medium最长边1152，并保持原屏幕坐标映射。Small 档仍为 Small DET+REC。这是优化速度与容错的技术取舍，**不是声称完整 Medium DET 仍在工作**。
2. prepare_models.py 和构建清单仅保留3个模型（Small DET、Small REC、Medium REC），减少 ZIP 大小，仍完全离线，不在用户电脑下载模型。
3. 提示音重新生成短机械声，采用独立 Windows waveOut 输出句段完成和文字切换音，与 SAPI/WinRT/广荣朗读分离，失败回退 winsound WAV 文件；新增分次试听和 Windows 标准提示音排障。
4. 解决“鼠标一离开 OCR 框，刚触发的 WinRT 语音还没出声就被 stop 取消”的链路问题。改为只有新区域发起新朗读才中断旧句；F8/清除/结果过期仍停播。绿色边框和无障碍 UIA 均保留。
5. WinRT MediaPlayer 改用多媒体音频类别，保留 SpeechSynthesisStream 直到播放结束，增加 MediaFailed 和播放状态诊断。不把“语音合成成功”误报为扬声器已经出声。
6. 新增可选第三方 **广荣 TTS**：借鉴沈广荣公开 NVDA 驱动使用的 DLL 接口（YongDe_GetVoiceCount/GetVoiceName/SetVoice/TextToAudio/StartStreamSynth 等），通过 Python multiprocessing 子进程隔离 DLL 和 GUI。可从用户已有 NVDA 插件标准目录有限发现，其他 Windows 保益悦听安装方式由用户在无障碍文件选择器选本地 grtts.dll。未内置任何第三方 DLL/微软自然语音模型/许可内容，未绕过许可；不能声称用户原版保益悦听与该 DLL ABI 完全相同；**广荣及云希/晓晓在用户机尚未实际发声验收**。
7. 原有“复制链路日志”保持，额外记录是否仍有 OCR 运行、声音请求、报错；无 OCR 原文。绝不恢复动画变化监测，只有按 F8 和60秒TTL清空。
8. 修正 Actions 中**pytest 失败却被下一条 compileall 的成功退出码掩盖**的问题，现 pytest 或 compileall 失败立即终止构建。16/17测试首次有一条旧音效时长上限不符已修订，**最终17项全部通过**。

### 真实测试和明确边界
- 最终 Windows Actions 成功：https://github.com/vobichngan285-collab/-/actions/runs/42508035692
- 完整 EXE 运行后，Small/Medium 双档 OCR 识别“CONTINUE GAME / SETTINGS”、“继续游戏 / 游戏设置”均通过；最后一轮 CI 暗底中文图：Small 推理约704ms，Medium 混合模式约1898ms（CI 上存在 CPU 负载波动；前轮 Medium 同类测试约537–635ms）。旧版完整 Medium 检测的一次对应推理超过3200ms，但不可把不同 CI 运行当精密 A/B。真实游戏速度仍需用户电脑验证。
- CI 成功 17 项单元测试；打包后实际 EXE OCR 双档、SAPI/WinRT合成流、原生边框 UIA 与完整窗口启动、可选 Guangrong 无 DLL 时优雅回退均通过。
- 发布唯一免安装 ZIP：`GameTextReader_V1.4_Windows_x64_Portable.zip`，194319209 bytes /185.3MiB；SHA256 `6bd0f223e07a6c6117bd08a752484fba8484aa641efeeaf8320df62c4a8b6ddd`；ZIP CRC pass，内含 EXE+3个官方 ONNX 模型、不含 grtts.dll／medium DET。GitHub Artifact https://github.com/vobichngan285-collab/-/actions/runs/42508035692/artifacts/13627842980；2026-12-08 到期。
- **未验证**：用户电脑真实声卡播放完成音/鼠标音、用户保益悦听已安装广荣 DLL 的独立调用、讲述人专有云希/晓晓可独立合成、真实游戏悬停顺序和性能。不得将 CI 通过冒充这些环节已经修好。
- 本仓库仅电脑游戏文字助手 `vobichngan285-collab/-`；未触碰 Android `kanzi-assistant`。


## V1.5 · 2026-11-09 · 独立广荣初步实验包与真实限制

**用户授权事项**：清理 V1.5 未完成的保益 BoyCtrl 语音通道接入；不再共用保益音量、语速、语音中断；继续广荣独立引擎的第一轮真实实验；生成可安装运行的包供用户测试。用户此前还指定取消鼠标进入文字区域的提示音，F8 识别完成只响一次清脆「叮」声，保留试听按钮。

**完成的代码与 GitHub 操作**：
- 将未完成分支 `game-text-reader-v15-baoyi-channel-20261109` 通过 force-with-lease 回退到 V1.4 main（该开发分支原未发布，未合入 main），新建 `game-text-reader-v15-guangrong-independent-20261109`；新分支**没有 BoyCtrl 适配器或对保益的调用**。
- 调查沈广荣官方下载 `https://github.com/shenguangrong/grtts_nvda_plugin/releases/tag/1.1.0`：经 GitHub Windows CI 真正下载并验证原版包 SHA256 `14ba0d4155549a1e4b76335687c960815c87e16f3e34907e1476d206c3609a77`。包中既有 32 位 `synthDrivers/grtts.dll`，又有 64 位 `synthDrivers/grtts_x64.dll`；V1.4 实验一直选择前者，64位程序会出现 `WinError 193`。V1.5 纠正为 64 位原版引擎。
- 继续独立 x64 运行测试：Windows 2025 CI 解压完整包，`Microsoft.CognitiveServices.Speech.core.dll`、`msc_x64.dll`、`SpeechSDKShim.dll` 可加载，但尝试 `ctypes.CDLL(grtts_x64.dll)` 在该环境返回 **WinError 1114**（DLL 初始化例程失败）。**这一步不是成功，不能声称独立的广荣微软音色已经工作**。原因仍待用户系统实测及进一步合法排查。相关 Windows Actions `42512423970`、`42512526713`、`42512625861`。
- 新增 `game_reader/guangrong_setup.py`：Tk 界面按钮「一键准备独立广荣 TTS」仅由用户点击后触发下载，联网仅首次获取158.9MB的作者官方原始发行包。检查固定SHA256、ZIP CRC、安全解压路径与体积限制，仅提取 `synthDrivers` 内容至 `%LOCALAPPDATA%\GameTextReader\GuangrongIndependent`，不拷贝、改动、控制保益或 NVDA 的运行时。
- 修订 `game_reader/guangrong_tts.py`：只允许 64 位 `grtts_x64.dll`，以独立子进程隔离崩溃并记录初始化报错、合成状态。应用启动时只使用**本软件目录安装**，不查找保益或 NVDA 语音目录，取消需要用户手动浏览 DLL 的 GUI 入口；并保留原有 SAPI/WinRT 正规可用本地声音作为对照。
- 改造原有「试听提示音」成只响一次较长的明亮原创金属叮声；F8 成功播放一次，鼠标悬停不再触发任何音效。OCR 小/混合 Medium、绿色框、保益可读的 Tk 无障碍界面和 60 秒 OCR 清空保持原样，绝不重新增加自动画面监测。
- 扩充测试至 **21 项全部通过**：64位DLL路径映射、官方 SHA 固定、真实一键下载-解压流程的无联网模拟、错误 SHA 拒绝、提示音格式、OCR模型分流、无障碍原逻辑。CI 中实际执行 Frozen EXE 模型中英文图测试、SAPI/WinRT 合成、UIA/绿色框测试、完整窗口启动，成功 Actions [42513309243](https://github.com/vobichngan285-collab/-/actions/runs/42513309243)。
- 交付 ZIP `GameTextReader_V1.5_Windows_x64_Portable.zip`；GitHub Actions Artifact [13630307332](https://github.com/vobichngan285-collab/-/actions/runs/42513309243/artifacts/13630307332)；194,303,280字节；SHA256 `0260fd7001c34cf5efcc7f7e129c8b5258f92c9bbf0288e5cdeca3a9c9c8060f`；本地CRC通过，独立文件中验证存在 EXE+三套官方 PP-OCRv6 模型，绝不包含供应商 grtts DLL 与保益代码。
- 真实用户尚待验证：广荣x64 DLL在安装了保益但独立运行的系统能否加载；输出默认永德或讯飞声音，是否实际出声；原版基础发行不包含按需下载安装的微软 NeuralVoices **云希/晓晓**，需后续合法独立安装或兼容验证，不可冒称已实现。若失败请复制「链路日志」和「语音诊断」，区分 `WinError1114`、语音列表为空、PCM生成失败与播放失败。
- OCR V1.4 第二模式慢、左上/左下角漏字尚在修复列表，**本次只是单独语音实验**；留待后续在同图A/B实测后处理。保留所有旧版历史；Android 仓库没动。


## V1.6 · 2026-11-09 · 广荣独立语音宿主专项修复／不宣称官方 DLL 已可用

用户明确要求不要重复发 OCR 照片或语音诊断，集中修复广荣微软 TTS；第二档 OCR 十几秒及结果不完整已知，本轮**完全不修改 OCR 模型参数与业务逻辑**。

- 从 main V1.5 `1ac65ba95d25236f58675a4f2b481644f68b4d2f` 新建 `game-text-reader-v16-guangrong-dll-fix-20261109` 分支，保留 V1.4/V1.5 全历史。
- 复验沈广荣 1.1.0 原始发行包双架构：`grtts.dll` 是 x86（PE machine 0x14c），`grtts_x64.dll` 是 x64（0x8664）。原包 SHA256 和安全路径规则依旧在 `game_reader/guangrong_setup.py` 校验。
- 原来通过 PyInstaller 的 Python 子进程调用 `ctypes` 加载外部引擎，冻结程序出现错误/超时；多轮 CI 追踪确定能进入原生 LoadLibraryExW 调用，却不能完成返回；这不是完整解决。
- 最终改用单独编译的 Windows x64 C++ 程序 `native/guangrong_host.cpp` → `GuangrongHost.exe`，与主程序通过匿名本地管道交互，支持语音枚举、切换、合成 PCM、停止、速率/音量。主程序 `game_reader/guangrong_tts.py` 不再原位加载第三方 DLL；保益悦听/NVDA 通道完全不参与。
- Windows CI 用 **CI-only 模拟 DLL** 回归：`HELLO 1`、语音枚举“Native Host Test Voice”、合成9600字节/24000Hz/16bit/单声道 PCM，代码路径贯通；打包冻结 EXE→本地宿主→模拟 DLL→PCM 也通过。这仅证明自研 IPC 和 PCM 链路实现，不证明广荣真实音库能运行。
- Windows CI [42556569339](https://github.com/vobichngan285-collab/-/actions/runs/42556569339) `success`，22项单元测试通过，EXE+Windows语音辅助宿主+原有离线OCR模型、UIA和绿色边框冒烟测试通过。免安装包 Artifact [13647478200](https://github.com/vobichngan285-collab/-/actions/runs/42556569339/artifacts/13647478200)，artifact报告字节数194022294（该数值是GitHub artifact，并非内部ZIP字节数），有效期至2026-12-09。没有验证可发布 sandbox 路径，不编造文件哈希。
- **严谨重要限制：** 额外下载并验证原版发行包，使用自研独立 `GuangrongHost.exe` 实际加载原版 `grtts_x64.dll`，Windows干净CI仍返回 `ERROR 1114`，没有 `READY` 或合成数据；[原版实测 Actions 42561840959](https://github.com/vobichngan285-collab/-/actions/runs/42561840959)。这项 workflow 的整体 success 指的是“完成了真实测试并正确识别未初始化”，**不是广荣已可用**。
- 真机测试建议：旧V1.5完全退出，V1.6解压到单独文件夹；它读取与V1.5相同的 `%LOCALAPPDATA%\GameTextReader\GuangrongIndependent` 官方安装组件，不必重新下载；先“重新扫描语音”，查看是否出现广荣音色，如有再点击“试听”。如果官方 DLL 仍报1114，不需要反复发送旧 OCR 照片，后续应走已知可独立运行的合规中文神经TTS方案或获取广荣宿主适配方案，而不是盲打包。
- 保留原单次F8清脆叮提示音，无鼠标区域音效；OCR Small/Medium 性能与边角漏字问题未改，后续单独处理。未触碰 Android kanzi-assistant 仓库。


## V1.6 · 2026-11-09 · 独立广荣原生宿主实验与未解决的官方 DLL 1114

**授权范围**：用户在看到 V1.5 现场截图中「PyInstallerImportError: Failed to load ...grtts_x64.dll」后，要求本次只修广荣微软 TTS，不再索要 Medium OCR 日志或语音诊断；明确 Medium 按 F8 等十几秒才出部分结果。V1.6 不应把 Medium 已修好写入交付。

**代码改动（分支 `game-text-reader-v16-guangrong-dll-fix-20261109`）**：
1. 创建 `native/guangrong_host.cpp`：独立编译的 Windows x64 本地语音辅助程序 `GuangrongHost.exe`，支持加载用户独立安装的原版 `grtts_x64.dll`、检查函数和音色、PCM 合成、匿名管道回传；有速率、音量、停播接口。语音子进程和保益悦听的读屏通道相互独立。不修改第三方 DLL、不内置官方声库或密钥。
2. 整体更换 `game_reader/guangrong_tts.py`，旧 PyInstaller 多进程内 `ctypes.CDLL` 加载路径被替换为 `subprocess.Popen` 调用真实原生 EXE；负责音色列表与 PCM 解析、播放和失败诊断，保留 SAPI/WinRT 备用。对外置 DLL 采用 Win32 原生加载器并明确上报 1114、193、126 等错误。
3. 修复 PyInstaller 运行环境继承 Windows DLL 搜索路径造成的原生 EXE 依赖冲突；C++ 宿主使用静态 MSVC CRT。保留游戏核心 F8、绿色框、自动 60 秒过期、用户无障碍读屏，不恢复后台画面监测、不动 Medium OCR 和 Small OCR。
4. 添加 CI 专用模拟 `native/fake_grtts.cpp` 和 `tools/test_grtts_host.py`（不随发布包分发）及冻结 EXE 级 `--self-test-guangrong-loader`：独立 C++ 引擎模拟音色列表 1 个、合成 24kHz 单声道 16位 PCM 共 9600字节，冻结 EXE 收到回传音频，并检查错误 PE 加载的真实 WinError 193。
5. 最终 Windows CI [42556569339](https://github.com/vobichngan285-collab/-/actions/runs/42556569339) **success**，22 项单元测试、模型实测、UIA/绿色框、冻结 GUI 启动和模拟原生语音 PCM 流程通过。Artifact [13647478200](https://github.com/vobichngan285-collab/-/actions/runs/42556569339/artifacts/13647478200)，名为 `GameTextReader-V1.6-Portable`，GitHub 报告 194022294 字节；内层目标文件名 `GameTextReader_V1.6_Windows_x64_Portable.zip`。当前工作容器无法做本地 ZIP 字节校验，不能声称本地 CRC 或 SHA256 已确认。
6. **最重要的负面结果**：独立取原版广荣 1.1.0 `grtts.nvda-addon`，验证已知 SHA256 `14ba0d4155549a1e4b76335687c960815c87e16f3e34907e1476d206c3609a77`；在干净 Windows 2025 CI 里，新的独立 C++ 原生宿主尝试加载真正的 64 位 `grtts_x64.dll`，仍报 `ERROR 1114 Windows DLL loader rejected the publisher engine`，未成功枚举真实语音、未得到真实 PCM。详见 [42561840959](https://github.com/vobichngan285-collab/-/actions/runs/42561840959)。与前一版 PyInstallerImportError 不同，这次证明真实原始 DLL 在该环境也不独立初始化。**不得宣称真实广荣微软语音已修复或模拟 DLL 证明实声可用**。
7. 下步只可针对真实独立 DLL 的原宿主依赖环境或选择不依赖读屏的独立离线 TTS 路线；别继续凭构建通过发「已修好」声明。用户 PC 实况可能不同，但目前只能作为兼容性实验包。其他历史全部保留；安卓仓库未改。



## 2026-11-09 · 新实验：保益悦听实际语音组件只读调查工具

**用户明确授权**：改变过去重复加载 NVDA 广荣 `grtts_x64.dll` 的路线，调查 Windows 保益悦听实际加载哪些语音驱动、TTS DLL、辅助进程与语音资源位置，以判断独立音色和独立语速的可行性。本轮要求现在开始实验；没有要求修改原有 OCR 或游戏文字助手朗读设置。

**已完成**：
- 基于 main `cb85f20b781cf529ab6247dfe210d92b78a93df5` 新建分支 `experiment-baoyi-real-tts-inspector-20261109`。
- 编写独立 WinForms 64 位只读工具 `diagnostics/BaoYiVoiceInspector.cs`，编译为 `BaoYiVoiceInspector.exe`，不是替换已有游戏助手；具备适配读屏的无障碍按钮/报告文本区：「开始只读扫描」「复制调查报告」「另存报告 TXT」。
- 只读列举保益候选进程、与保益相关的窗口 PID（**不记录标题文本**）、进程实际加载的 DLL 和有限的安装目录文件名，查找广荣 / NeuralVoice / SpeechSDK 等线索。可确认「文件在安装目录中」与「文件已被运行进程加载」的区别；**不能仅凭模块名称判断是哪一种声音**。
- 扫描 Windows 卸载程序注册表的保益 DisplayName/InstallLocation/DisplayVersion **仅作读取**，不读取语音配置文件或 license 内容，不调用朗读接口，不注入 DLL，不更改保益和系统设置，不请求管理员权限；本地运行**完全不联网**、没有自动上传，报告只在用户点选复制或另存时离开内存。用户目录用 `%USERPROFILE%`、`%APPDATA%` 等替换，仍提示分享前人工检查目录信息。
- 由于常见 Windows 浏览器标签或文件夹标题可能含「保益悦听」，已剔除浏览器/文件管理器误命中；输出模块访问受限的汇总数，并列出疑似音库子目录但不读取敏感内容。
- 新增独立 GitHub Actions `.github/workflows/build-baoyi-inspector.yml` 以及 CI 仅用的 `diagnostics/ProbeHost.cs` 伪保益进程。**正式 Windows CI [42564529268](https://github.com/vobichngan285-collab/-/actions/runs/42564529268) success**：Windows 64 位 .NET 框架编译成功；自动测试进程/语音 DLL 名称筛选、用户路径脱敏、无障碍控件名称；运行无害模拟的 `BoyPcReader_TestDummy.exe`，实际进程枚举在报告中找到它；不含厂商 DLL。
- 最终包 GitHub artifact [13650751784](https://github.com/vobichngan285-collab/-/actions/runs/42564529268/artifacts/13650751784)；在会话容器完整下载后解出内部 `BaoYiVoiceInspector_Windows_x64_ReadOnly.zip`，**13,374 字节，SHA256 `fa534fca19c0d6bf8bcd818f3e62291a580213e89ef7cd46720a284b7d54dcda`**，内外层 ZIP CRC 校验通过；内部恰有 `BaoYiVoiceInspector.exe`（22,016 字节，MZ 可执行标识）和 `README.txt`。
- **尚未验证**：用户电脑上实际保益进程及广荣语音模块、声库路径和初始化方式。CI 上没有用户的保益悦听，也不可能据此宣称已找到实际内部语音驱动。此实验必须由用户在运行保益悦听的 Windows 电脑上打开小工具并点击「复制调查报告」，回传报告后才能判断。

**使用**：打开电脑保益，维持平时的广荣音色并触发一次普通读屏朗读；新目录解压小工具，双击 `BaoYiVoiceInspector.exe` →「开始只读扫描」→「复制调查报告」→粘贴到对话。不要上传原音库、许可证或语音配置。调查工具没有依赖 BoyCtrl、不调用或打断保益语音、不会占用保益调速。正式 Windows GameTextReader V1.6、F8、绿色框、OCR 两档和音效没有修改；安卓仓库也没有修改。
