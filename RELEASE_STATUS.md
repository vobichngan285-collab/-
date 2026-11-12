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


## 2026-11-09 · Windows V1.7 Medium 性能/预热调度实验（云端成功，电脑待验收）

- **当前开发重点：** Windows 游戏截图 OCR + 鼠标指向朗读；安卓云端蓝星向导暂时搁置，安卓旧离线 OCR/CRAFT 已放弃。下一次优先阅读根目录短交接 `CURRENT_HANDOFF.md`，不必全文浏览本历史。
- **代码来源与隔离：** 从 V1.6 源码分支 `game-text-reader-v16-guangrong-dll-fix-20261109` 的 `cb85f20b781cf529ab6247dfe210d92b78a93df5` 创建 `exp/windows-medium-latency-v17-20261109`。V1.7 实际构建 Commit `1e9c216d1bf5ec7f7cb7facc239375fcff64d525`，没有覆盖原稳定分支或安卓仓库。
- **改动：** 保留 Small 参数与绿色坐标框、F8、60秒失效、Windows 与独立广荣语音模块；仅 Medium REC 使用 batch2 与 ONNX CPU 2线程（Small DET仍负责两档定位）；延迟/取消过期后台预热任务，新增锁等待、模型加载与推理分段计时。没有修改广荣 DLL/声音逻辑。
- **事实测试：** Windows 2025 Runner 的 4行/18行合成菜单中，Medium batch6→2 的一轮约5%改善且文字与坐标一致；固定CPU2与自动线程反转顺序重测仅约3～4%改善（之前某单轮24～29%不稳定）。两轮绝对耗时波动较大，不能跨轮声称数倍提升或替代用户电脑实测。认定瓶颈仍主要是 Medium REC。测试报告见本实验 [Actions 42583872881](https://github.com/vobichngan285-collab/-/actions/runs/42583872881) 的两个性能报告 artifact。
- **最终CI：** [42583872881](https://github.com/vobichngan285-collab/-/actions/runs/42583872881) **completed/success**，26项源码测试、Small/Medium真实权重OCR、冻结 EXE、无障碍绿框、系统语音合成与模拟 GuangrongHost PCM 通过；不能据此声称真人扬声器或官方广荣 DLL 可发声。
- **实际交付：** [V1.7 Windows x64 ZIP 工件](https://github.com/vobichngan285-collab/-/actions/runs/42583872881/artifacts/13658427538)（30天保留）；内层 `GameTextReader_V1.7_Medium_CPU2_Windows_x64_Portable.zip`，194,448,729 bytes，SHA256 `df9a054ba44b041bc75b8906030bd41367d25a71dee96dcd346e54c3eef37287`。本轮已实际下载验证外层+内层 ZIP CRC、EXE、广荣宿主、OCR 模型和无第三方 grtts DLL。
- **未完成 / 下一步：** 用户 Windows11 电脑安装同图对比 Small 与 Medium 的真实 F8 耗时、文字命中和朗读；若速度仍不能接受，再考虑其它 Medium 识别执行方案。广荣 `grtts_x64.dll` 官方独立加载 ERROR1114 问题**本轮没有修复**，可参考已完成只读 BaoYi 调查工具，等待真实电脑调查证据。不要再次重复旧模拟 PCM 或 Android CRAFT 实验。

## 2026-11-09 · V1.8 Small-only + BaoYi Voice Inspector V2（CI 已通过，用户电脑待验收）

- 用户真机 V1.7 Medium 日志：`2560x1440`，79框总53.587s、48框总34.298s，模型加载/锁等待0ms，Small DET约0.5–0.6s，Medium REC约33.7–52.9s。用户决定后续版本移除 Medium，转而集中解决广荣微软语音。
- V1.8 分支 `feat/windows-v18-small-only-baoyi-voice-probe-20261109`，Build Commit `ea6988ac0e8fa45340e9bed62098f05350d0e19d`。删 Medium UI/识别调用/权重，旧 `tier=medium` 自动迁移 Small，只保留官方 PP-OCRv6 Small DET+REC 及原快识配置；F8、绿色文字框、60秒过期、原 SAPI/WinRT 及广荣实验入口保持。
- 用户保益悦听 12.10 真机只读 V1 报告（2026-11-09 16:53）表明存在 `BoySpeechSlave.exe`、`BoyTTS.dll` 安装文件，未直接发现已加载的 `grtts_x64.dll`；旧扫描器遗漏了进程名筛选、把自己当成保益相关进程。V2 新增明确语音辅助进程识别、候选进程架构、`BoyTTS.dll` 加载观察、自身排除、只读脱敏，**并未解决独立广荣发声**。需用户在保益正常朗读时回传 V2 报告；官方 DLL 单独加载 ERROR1114 仍待证实实际环境关系。
- GitHub Windows Actions [42595587940](https://github.com/vobichngan285-collab/-/actions/runs/42595587940)：首次排队后取消（completed/failure），明确重新运行第二次 **completed/success**；27个 Python 单元测试、真实 Small OCR 中英文本图、冻结EXE、SAPI/WinRT、模拟独立广荣PCM、UIA、V2 调查工具真实模拟进程、两个Small权重验证成功。模拟语音不证明云希/晓晓实际发声。
- 主程序 artifact [13667257789](https://github.com/vobichngan285-collab/-/actions/runs/42595587940/artifacts/13667257789)，内层 `GameTextReader_V1.8_Small_TTSProbe_Windows_x64_Portable.zip`，126636816 bytes，SHA256 `0aa81272efc8a82fe63ab2eb7529b98995fd483116c3011aa65a8bb46d53cc38`。独立 V2 工具 artifact [13667013340](https://github.com/vobichngan285-collab/-/actions/runs/42595587940/artifacts/13667013340)，内层 `BaoYiVoiceInspector_V2_ReadOnly.zip`，14150 bytes，SHA256 `b0c8589469705e93aa88a916c631609029742bc9c9dcf83831ee13166e6057fe`。两套内外层 ZIP CRC 实际校验通过，游戏包仅两个 Small ONNX，包含调查工具，无需重复下载。产物为限期 Actions artifact。
- 下次新对话优先读简短入口 `CURRENT_HANDOFF.md`，回传 V2 真机报告、核查 Small 和朗读回归；不要重新折腾 Medium 或旧安卓离线 OCR；不得声称调查成功等于广荣成功。

## 2026-11-09 · Windows 云端微软自然语音可行性验证（真实合成，目标音色条件不具备）

- 用户提供 LunaTranslator 配置 `config..json`，有 `reader.windowstts.voice` 自然语音 Yunxi WindowsApps 包路径和 MicrosoftWindows.Voice.License 字段，称该软件用云希/晓晓成功。追到原 [windowstts.py](https://github.com/HIllya51/LunaTranslator/blob/main/src/LunaTranslator/tts/windowstts.py) 与 [msnaturalvoice.cpp](https://github.com/HIllya51/LunaTranslator/blob/main/src/NativeImpl/LunaSubprocess/msnaturalvoice.cpp)，确认其类型1经微软 Embedded Speech SDK 独立进程合成，配置许可声明不等于任意新软件的使用授权。不能通过复制用户许可证文字或绕过模型加密实现移植；不要将整份私有配置提交 GitHub。
- 用户要求尽量云端先实验而非每次下载。已从 V1.8 源码分支派生 `exp/cloud-natural-voice-interface-20261109`，在 Windows-2025 Actions [42609120899](https://github.com/vobichngan285-collab/-/actions/runs/42609120899) Commit `417585abb65b69627742daf8896ec34767abd241` **completed/success**。实际执行 `tools/cloud_voice_feasibility.py`：SAPI 写出真实 WAV 170876 bytes/456ms、WinRT 生成真实 WAV 流115886 bytes/181ms，非模拟；报告 [artifact 13668444274](https://github.com/vobichngan285-collab/-/actions/runs/42609120899/artifacts/13668444274)。
- 云端没有云希/晓晓 Appx 包：SAPI 只 David/Zira，WinRT David/Zira/Mark；嵌入式语音运行时组件存在，但缺目标模型/授权，未测试云希/晓晓真实合成，也未改 V1.8。微软 Embedded Speech 是 limited-access 功能。下一步先区分普通 WinRT 与已获合法 Embedded SDK 授权，明确云端不能模拟用户已有自然语音包，不再要求反复下载无意义实验包。

## 2026-11-09 · 直接复现 LunaTranslator 自然语音架构的 Windows 云端实验

- 用户坚持按 B 站作者的成功做法和实际实现路线研究，不再反复用普通 SAPI/WinRT 代替云希/晓晓，尽量全云端完成。
- 仔细回读 [`windowstts.py`](https://github.com/HIllya51/LunaTranslator/blob/main/src/LunaTranslator/tts/windowstts.py)、[`LunaSubProcess.py`](https://github.com/HIllya51/LunaTranslator/blob/main/src/LunaTranslator/LunaSubProcess.py)、[`msnaturalvoice.cpp`](https://github.com/HIllya51/LunaTranslator/blob/main/src/NativeImpl/LunaSubprocess/msnaturalvoice.cpp) 和 `pipehost.hpp`：音色 type=1 使用 MicrosoftWindows.Voice 包、Tokens.xml 元数据、微软 SDK 独立 64 位进程，进程间传 SSML、返回 WAV。原代码还提供硬编码模型初始化密钥和用户配置的 Voice.License 字符串密钥，不等于可供本项目复用的合法模型授权；不得复制第三方密钥/规避加密。
- 在 `exp/cloud-natural-voice-interface-20261109` 新增同构隔离实验 `tools/luna_natural_architecture.py` + `.github/workflows/verify-luna-natural.yml`，Commit `9fd0ce8e987398bde1aab0cb98e29afc546a3f73`。Windows [Actions 42610010494](https://github.com/vobichngan285-collab/-/actions/runs/42610010494) **completed/success**，从 pip 安装正版 Embedded SDK，`EmbeddedSpeechConfig` API 导入成功、模拟 `Tokens.xml` 解析成功、独立子进程 JSON 通信成功、无合法模型授权拒绝语音合成成功。结果 artifact [13669373825](https://github.com/vobichngan285-collab/-/actions/runs/42610010494/artifacts/13669373825)。
- **明确未实现：** 云端没有真实云希/晓晓模型与使用授权，因而云希/晓晓实际声音合成**未测试、未通过**；V1.8 稳定版源码/语音设置未修改，未发让用户反复下载的包。后续要沿此同构方案完成真正合成，需要适用的获授权模型条件，禁止宣称与模拟进程测试等价。

## 2026-11-09 · V1.9 真实接入用户 Luna 原始 JSON 到微软 Embedded Speech（实机语音尚未验收）

- 用户反复强调不要换实现路线，需**像 LunaTranslator 一样实际用原始代码/配置**。上传 \`config..json\` 是完整有效JSON，实际含 \`reader.windowstts.voice=[1, "C:\\Program Files\\WindowsApps\\MicrosoftWindows.Voice.zh-CN.Yunxi.1_1.0.5.0_x64__cw5n1h2txyewy"]\`，\`MicrosoftWindows.Voice.License\`/ \`MicrosoftWindows.Speech.License\` 皆721字符。用户说 B站软件原配置粘贴后云希/晓晓可朗读。已确认公开源 \`windowstts.py\`、\`msnaturalvoice.cpp\` 的实际调用链是离线 Embedded SDK及模型KEY属性，而不是 SAPI/WinRT。完整许可文本/原始配置绝不能上传到公共GitHub。
- 原 V1.8 成功稳定版留存不改，建独立实验 \`exp/luna-original-config-embedded-tts-20261109\`，提供读取用户未改动JSON并取得自然语音包路径+全文 \`Voice.License\`，独立语音进程使用正版 \`EmbeddedSpeechConfig.from_path\`、\`SpeechServiceConnection_SynthModelKey\` 并传入相同字符串，SSML WAV 再交 Windows 播放；GameTextReader V1.9 GUI可导入该JSON或EXE目录直接放 \`config..json\`；录制到的日志只显示布尔状态和代号，不含许可字段/识别文字。主要源码 \`game_reader/luna_natural_voice.py\`、\`luna_voice_worker.py\`、\`luna_bridge.py\`、\`app.py\`、\`speech.py\`、\`main.py\`。
- Windows构建 [42612283597](https://github.com/vobichngan285-collab/-/actions/runs/42612283597) Build Commit \`a23bbfe03d85747cfbbe10ffeb8a2439e6cf5c7f\` **completed/success**，34项单元测试、原始 JSON→属性调用不修改字符串（用云端模拟SDK和虚拟包测试）、官方 Embedded SDK 导入、独立冻结EXE工作进程、Small OCR、中英文真实OCR、Windows系统语音、UI自动化、旧广荣模拟组件通过。主包 artifact [13671406354](https://github.com/vobichngan285-collab/-/actions/runs/42612283597/artifacts/13671406354)，内层 \`GameTextReader_V1.9_Luna_OriginalConfig_Windows_x64_Experimental.zip\`，138,982,217 bytes，SHA256 \`ddda7226833ac3c2b6fdc84b22393388370ff3daba98b5d624d1dba551269b40\`；外层内层 ZIP CRC 已独立下载验证、1215项、仅两个 Small ONNX、含微软 Embedded SDK 实际 DLL，不含用户原JSON或模型。
- 额外真实官方SDK测试 [42612988482](https://github.com/vobichngan285-collab/-/actions/runs/42612988482)，脚本 \`tools/cloud_luna_sdk_real_property.py\` 用正版 \`azure-cognitiveservices-speech-embedded\` 和假模型目录+假字符串验证 \`SynthModelKey\` 真实set_property/get_property返回值一致。**这证明属性可设置，不证明用户云希/晓晓自然语音曾在云端真正合成 WAV**；官方 Windows CI 不具目标模型或真实授权，因此无法保证用户电脑SDK接受该模型。不要直接复制第三方默认key作为授权。
- 选择这条实现路线后不要再做重复广荣 DLL 或 SAPI 假替代；尊重用户不想多次下载实验包，能在云端的实验优先做；未到真实音频测试的步骤必须坦诚。

## 2026-11-09 · V2.0 原封不动使用 LunaTranslator 原版二进制（核心未改，配置未改）

- 用户最终要求：**不使用改写的微软语音 SDK，不修改 B 站作者原版语音核心，不删改用户上传的 `config..json`，直接将原作者的成功实现接入 GameTextReader。** 本次执行中保留 V1.8/V1.9 原实验包和各分支，另建 `exp/luna-verbatim-upstream-20261109`，Build HEAD `aff85bb6f0877b125a074eb38321ce97c265c626`。
- 源：[LunaTranslator 官方 v12.1.3.9 Windows x64 发布版](https://github.com/HIllya51/LunaTranslator/releases/tag/v12.1.3.9) SHA256 `c0248288c12de19e9e1f953922355aaa123699820fce26e4e84329be2666d62f`；内含 `files/LunaSubprocess64.exe` 398144 bytes、SHA256 `886892cd78cdd8bbd029a3f4977853cc1ddce1c9723e656986fa8b5a79e6a974`。从官方 ZIP 原样复制此 EXE、校验实际哈希，不重新编译；官方源 tag `84677faeaa1e61bd7dd00b820090e9d2fe6c5142`。随最终包提供作者原样 `windowstts.py`/`LunaSubProcess.py`/`basettsclass.py`/`msnaturalvoice.cpp`/`pipehost.hpp`/GPLv3 LICENSE 及完整官方源压缩包。
- 本项目只添加 Windows IPC 连接模块 `game_reader/upstream_luna_pipe.py`（原版 msnaturalvoice 命令、named pipe、event 和32MB共享内存协议），`luna_voice_worker.py` 直接启动**原作者未修改的** `LunaSubprocess64.exe`，从用户原始 JSON 读取完整 `MicrosoftWindows.Voice.License`、mode=1和语音包路径传入原 EXE，SSML 按原公式传入，取得 WAV 后 Windows 播放；旧自研微软 Embedded SDK 合成代码已从生产适配器中删去。EXE 同目录若有 `config..json`，优先它且自动选原版语音，不被旧设置覆盖。
- 云端 Build [Actions 42616893234](https://github.com/vobichngan285-collab/-/actions/runs/42616893234) **completed/success**：38项 Python 测试、Windows 官方 Small OCR、冻结EXE GUI/UIA/语音 worker/原版文件哈希与源码复本检查、ZIP 完整性通过。公开无配置的 GitHub artifact [13672424251](https://github.com/vobichngan285-collab/-/actions/runs/42616893234/artifacts/13672424251)。
- 用户上传的 **完整 `config..json` 55251字节原始内容未修改**；此次仅在私有 ChatGPT 容器中把源文件字节加入 CI 通过的原版整合 ZIP，验证源和包内 SHA256 一致、上游 EXE 与官方 SHA256 一致、ZIP 全部 CRC 通过，最终私人文件 `GameTextReader_V2.0_Original_Luna_Exact_Config_Windows_x64.zip` 130403883字节，SHA256 `e4cb1330738a79c3064b69fd1532d88da5d3005617c71b84a542a3f70c880cf6`。**私人配置没有提交 GitHub，禁止把私人 ZIP 再公开上传；私人会话 sandbox 文件不等于 GitHub artifact。**
- **未验证的关键点：** CI Windows 2025 没有云希/晓晓自然语音包，无法实录目标音色；因此不能宣称已经成功朗读，只能证明原程序字节原封不动、用户 JSON 字节原封不动、完整集成打包成功。实际出声和微软模型许可依赖最终用户的 Windows 环境，不能从 CI 推断。保留上游 GPLv3 源码和第三方授权边界。


## 2026-11-09 · 已讨论的下一轮鼠标悬停 OCR 与 V1.2→V1.3 漏读回归（仅记录）

- **未授权软件开发、未运行构建、未发布新包**。下一轮需求：全屏截图 OCR（示例 F8）与鼠标朗读模式切换（示例 F9）使用两个不同、均可自定义为单个按键的热键。模式键每按一次循环“原有指向已截图文字框朗读”↔“局部鼠标悬停 OCR 新弹窗朗读”；局部 OCR 只需直接填写毫秒周期刷新与另一个自定义单键手动触发，不加入复杂的画面变化识别。框选区域参考 LunaTranslator：暗屏、中央十字准星、拖动矩形、松开确认/Esc取消；记住相对鼠标的框大小及位置，识别区域跟随鼠标。后台同一内容避免周期性重读，跳过 OCR 在途期间的新周期，避免任务堆积。原 F8 全屏 OCR / Small / 鼠标命中文字框逻辑均保留。
- **用户明确补充并校正：V1.2 采用的就是默认 Small（第一个档），V1.3 开始就出现屏幕左中区域有图标文字却漏读；V1.2 真机效果最好。** 这不是因为后来删 Medium，不能将 V1.4 才引入的 DET max/1280 缩放视为 V1.3 首次回退的原因。
- 只读核对 GitHub 源码 V1.2 HEAD `3f04365ab0ff8c31df9ad23d5a9ea869635f13f5` 与 V1.3 HEAD `91ef787cc1aacd0820be7b113234dac6dc293c51`：两个版本 Small 模型对、显式 RapidOCR 引擎参数、默认检测尺寸、阈值0.42、文本框映射、截图全屏范围一致。V1.3 新增后台 OCR 预热与计时/锁、移除画面变化检测、前台窗口先最小化后截图的延迟由 250ms 缩短至100ms、RGB 重复转换优化与音效日志；目前只有**可能影响截图时机**的候选差异，没有真正同画面 A/B 证据，不能宣称已找到根因。V1.4起 DET max/1280 可能进一步恶化小字漏检，但非最早的起点。下轮最先恢复/对照 V1.2 默认 Small 准确性，不要更改语音核心或重新做旧 Medium 实验。
- **V2.0 真实云希/晓晓仍未测试**：用户尚未在自己 Windows11 运行验收。原作者二进制 + 原始私人 `config..json` 集成仅在 CI 成功，**不是语音包已修好**。本记录只保存讨论结果，下一轮开发需再次征得用户指令，并先回读交接、分支、HEAD、Actions。


## 2026-11-09 · 用户最终澄清：只借 V1.2 OCR 底子，不回滚已经删除的功能（未来开发原则）

**仅记录未来开发决策，本次不改任何应用源代码、不运行构建、不发布新包。** 用户明确说“删除的东西不变，第2个识别模型本身就用不了，直接删除。我们只是用1.2的底子”。

- **以 V1.2 的默认第一档 PP-OCRv6 Small 为 OCR 底座**：参考 `game-text-reader-v12-20261109` commit `3f04365ab0ff8c31df9ad23d5a9ea869635f13f5` 中真实验证过的 Small DET + Small REC、图像捕获/模型参数/识别框映射/原鼠标命中朗读等相关实现，优先保持 V1.2 的游戏文字检出能力。
- **不要把完整 V1.2 原样恢复成新软件**：后续版本已经删除、且用户不要求恢复的旧功能继续维持删除状态（特别是 V1.2 的自动画面变化检测不因复用底子而重新引入）；**第二档 Medium（含 Medium DET/REC、切换 UI 和模型权重）继续彻底移除，不做第二档实验**。只有 Small 单模型。
- 新版本以原仓库内 V1.2 旧代码为**参考/起步基础**，对照后续版本只引入用户批准且仍然需要的功能，例如已讨论的独立全屏截图键、鼠标模式切换键、悬停局部 OCR + 毫秒周期/手动键、暗屏十字框选。不要重新采用导致识别效果倒退的性能改写；每个新功能不应降低 V1.2 Small 的游戏 OCR 准确性。
- **V2.0 原版 Luna 语音尚未经过用户真机发声验证**，不能因为决定以 V1.2 为底子就宣称语音已修好。语音集成的保留/移植必须以验证为依据，不影响 OCR 底座。
- 这是设计与后续开发约束记录；实际修改仍需用户另行明确授权。尊重原来的 V1.2、V2.0 和实验记录，不覆盖代码或现有包。


## 2026-11-09 · V2.0 用户首次 Windows 真机测试失败：原版 Luna 自然语音没有发声（新事实，需优先处理）

- 用户在 Windows 11 启动了此前交付的 V2.0 私有整合包，界面显示「微软自然语音·云希（原作者 JSON 配置）」；点击试听后界面明确报 **「TTS 出错：Luna 自然语音：RuntimeError（请检查原配置、语音包和 SDK 兼容性）」**，**未成功发声**。此前“未真机测试”状态已经被本次失败证据替代：**V2.0 自然语音真机失败，不能继续声称待测或者已可用**。截图仅证明上层通用 RuntimeError，不代表知道底层 SDK 错误码。
- 用户指出：其从 B 站得到的配置在**原作者软件**中的作用是让原软件检测/选择到 Windows 已安装的微软自然语音；不等于在 GameTextReader 中同样配置就自动具备发声功能。应正视此区分，避免以“识别到音色”代替“真正合成 WAV 并播放”。
- **只读检查原作者 v12.1.3.9 源码**：`src/LunaTranslator/tts/windowstts.py` 经 `NativeUtils.FindPackages("MicrosoftWindows.Voice.")` 自动枚举语音包、从 `Tokens.xml` 读取名称和 LicenseVersion、提供音色列表；`checkifnatural()` 才启动 `LunaSubProcess.msnaturalvoice(path,dllp,license)`，`speak()` 经 SSML/IPC 合成。原程序不是只有扫描，亦包含完整工作流。**GameTextReader V2.0** 的 `game_reader/luna_natural_voice.py` 直接读取原 JSON 的固定 `reader.windowstts.voice[1]` 路径，未等价复现动态枚举/选择；`upstream_luna_pipe.py` 启动原版二进制，但由自行编写的连接层负责 IPC、运行组件定位，且与原主程序环境可能不同。不能把原版二进制哈希一致误认为全流程兼容。
- **找到确定的诊断盲点**：`luna_voice_worker.py` 在失败时返回安全抽象 `error` 及 `error_type`，`luna_bridge.py` 无论 worker 报哪种非 ok 状态，都先抛 `RuntimeError`，随后向用户只报这个新异常的类名，没有显示可区分的**无敏感信息错误分类**。因此截图中 RuntimeError 无法判断是 JSON路径过期、语音包不存在、系统运行时缺失、语音子进程 IPC 失败，还是实际 SDK 合成失败。不能无证据归因于许可证、微软系统、原作者引擎或用户设备。
- **下一步只读调查**：优先让用户在当前包点击「复制链路日志」，检查 `Luna 原始配置状态` 中的 `config_valid`、`selected_package_exists` 等无敏感状态，以及最后 TTS 错误和事件；不要索要原始许可证、完整私有配置或全硬盘路径，也不要让用户无意义重复下载新包。之后若获开发授权，才可完善脱敏分阶段诊断，重做以原版音色发现和真实音频合成为验收的 Windows 真机方案。**当前不修改源代码、不构建**。


## 2026-11-09 · Windows 语音改造实验：V1.2 Small 底座 + 自动发现已安装微软自然语音（CI 通过；用户电脑真实发声待验）

- **为什么做**：用户已在自己的 Windows 11 启动 V2.0，选择云希试听出现 `TTS 出错：Luna 自然语音：RuntimeError`，没有实际发声。重新读 B 站作者 LunaTranslator v12.1.3.9 `windowstts.py`、`LunaSubProcess.py` 与 `msnaturalvoice.cpp`，确认正确链路是 **查找 MicrosoftWindows.Voice.* 安装包 → 读取 Tokens.xml 元数据 → 选音色 → 加载微软本机运行组件和用户适用的本机 Voice.License → 通过作者原版 LunaSubprocess64.exe 合成 SSML 音频 → WAV 播放**；“检测到音色”绝不意味着“已经能发声”。
- **实验仓库/分支**：仍为原 Windows 仓库 `vobichngan285-collab/-`，新建独立 `exp/v12-small-system-voice-discovery-20261109`，从用户验证准确率最好的 **V1.2** commit `3f04365ab0ff8c31df9ad23d5a9ea869635f13f5` 开始。未覆盖 V1.2、V2.0 的原分支。
- **V1.2 OCR 底子严格保留**：`core.py`、`overlay.py`、`win_screen.py`、`cues.py` 的 Git blob SHA 与 V1.2 **相同**；`ocr_backend.py` 沿用 V1.2 的 Small DET/REC、原始 RapidOCR 默认 DET 尺寸参数与截图像素转换，不引入后续的 `max/1280` 限制；删除第二档 Medium 模型选择/权重；已从新分支移除之前删掉的自动画面变化检测模块及相关旧测试。
- **重做语音扫描与调用**：新 `game_reader/ms_voice_discovery.py` 通过 Windows `Get-AppxPackage -Name 'MicrosoftWindows.Voice.*'` 查询当前用户已安装语音包、可访问时解析 `Tokens.xml` 的 Name / LicenseVersion；每个自然音色在界面显示“已安装，待试听”。不再直接用 JSON 中写死的旧 WindowsApps 版本路径作为音色列表。只使用用户电脑私有的 `config..json` 读取现有 Voice.License（可导入或放在 EXE 同目录），**不将密钥/配置上传 GitHub**。由上游未经修改的 `LunaSubprocess64.exe` 合成，新增扩展的系统运行组件目录查找和错误阶段分类（扫描/运行组件/引擎/IPC/SDK合成），不再只显示 `RuntimeError`。不存在许可证绕过措施，微软组件与上游 GPLv3 授权需遵守。
- **真实 Windows 云端构建结果**：构建源代码 commit **`bd72deecf7457899e0751bc97a5cc93ac12362dc`**，Actions [42633429036](https://github.com/vobichngan285-collab/-/actions/runs/42633429036) **completed/success**。全部 Python 单元测试（含 Windows 包发现虚拟测试、V1.2 DET 无缩放断言）、Small OCR 官方模型自测、PyInstaller EXE、小模型恰好两个、上游原版 DLL/EXE 文件 SHA 和完整 GPL 源代码、SAPI/WinRT、**冻结 EXE 的独立语音 worker IPC 错误分类测试**、UIA及完整窗口启动、ZIP 打包和 artifact 上传都通过。**CI 没有安装云希/晓晓，也没有实际合成目标语音**。自动化证明结构、扫描逻辑和包装完好，**不证明现在已经解决发声**。
- **公开下载实验包（无用户私有 config）**：[Actions artifact 13680739016](https://github.com/vobichngan285-collab/-/actions/runs/42633429036/artifacts/13680739016)；名称 `GameTextReader-V12Base-SystemVoice-Discovery-Experimental`；约129,755,090字节；2026-12-09 过期。将实验包解压到独立目录，再在程序中选择**本机**此前原作者 `config..json`（不要公开该文件），点击「重新扫描语音」选系统自然音色、试听。失败时只需告知脱敏 stage/code 或截图，绝不要求私密许可文本。
- **唯一未解决的验收项**：用户的 Windows11 上云希/晓晓是否真正出声。用户已经明确 V2.0 真机失败，所以**新实验包仍处于待真机发声验收**。如果不行，按本版的具体失败阶段解决，不再无目标轮换 SAPI/WinRT/广荣或反复让用户下载无意义包。
- **下一阶段悬停 OCR**：之前讨论的全屏快捷键与模式键分离、鼠标附近暗屏框选及周期扫描仍只是**待开发**，本次**未添加**，不要声称已有。先保证语音链路的实际运行结果，再按用户指令进行下一轮功能开发。


## 2026-11-09 · 用户本机新实验包真实失败：扫描成功但语音子进程报告缺配置（重要）

- 用户已运行新实验包（Actions 42633429036 / artifact 13680739016）。屏幕出现系统已发现 **3 个自然语音包**，下拉显示 Microsoft Yunxi (Natural)，但点击试听无声音，底部完整错误：`TTS 出错：系统自然语音合成失败：stage=discovery_or_setup; code=local_voice_license_missing`。
- **原代码经过回读确认**：`game_reader/luna_voice_worker.py` 的 `local_voice_license_missing` 仅在 worker 执行 `load_user_config(config_path)` 后无法得到本机 JSON 的 `MicrosoftWindows.Voice.License` 时抛出；这是**合成前**的失败，不可断言微软 SDK 不兼容或无许可。
- **值得注意的界面与 worker 状态不一致**：用户截图上方提示近似“已发现 3 个系统自然语音包，请试听确认真实发声”；在本版 `game_reader/app.py` 中，只有 GUI 线程检查 `has_config=True` 才显示“请试听确认真实发声”，否则提示“请先选择本机原版语音配置，再试听”。因此**不能武断认为用户没选配置/原文件缺字段**；更可能是 GUI 与独立语音工作进程的配置路径/初始化状态不同步，或文件在子进程内不可读取。`ms_voice_discovery.py` GUI 和 worker 都使用同一个 `load_user_config` 函数，需重点查完整配置路径在 `app`→`SpeechWorker.set_luna_config`→`LunaNaturalBridge.config_path`→JSON stdin→`luna_voice_worker` 之间是否变成空/过期，以及选择配置后的重建时序。
- **最小无需重下包的排查**：让用户通过当前版本按钮“选择本机原版语音配置”选择原始 `config..json`，等待扫描完成再点试听；不需要上传/展示任何私有许可证文本。若相同错误继续出现，应修复程序内部主/子进程配置状态传递并提升非敏感诊断，不要重复要求用户导入或盲目换引擎。
- **状态**：扫描包发现已在用户本机成功；自然语音**尚未合成成功/尚未发声**；此前“构建成功”绝不代表通过实际声音验收。本条仅记录 bug，没有修改现有实验版代码、没有重新构建。


## 2026-11-09 · V1.2 Small 自然语音配置链修复：发现 Windows 中文路径编码问题，构建通过（真机发声待验）

- **本轮用户授权**：“开始”，针对其 Windows 11 截图中的“检测到 3 个微软自然语音包且能选 Yunxi，试听却报 `stage=discovery_or_setup; code=local_voice_license_missing`”修复。用户已多次选择本机原版 `config.json`，不再要求反复扫描或反复提供私人配置。
- **已找到更具体且可自动复现的错误**：旧版本主 GUI 自检能看到本机配置中的 `MicrosoftWindows.Voice.License` 字段，但独立语音子进程报告缺失。新增 Windows 冻结 EXE 回归测试：生成*虚构测试值*的 JSON 配置，路径含中文与空格，通过 UTF-8 的子进程输入发送给 PyInstaller 打包的 `--luna-worker`；修复前 worker 错误报告 `local_voice_config_file_missing`（测试文件实际存在），表明中文路径在主进程→子进程传递中变形。确认旧 `luna_voice_worker.py` 使用 `sys.stdin.readline()`，Windows worker 默认文本代码页可能是 cp1252；而 `luna_bridge.py` 发出的是 UTF-8。**本轮改为 `sys.stdin.buffer.readline(...).decode('utf-8-sig')`，修复后的真实冻结 EXE 中文路径探针通过。** 上述是配置读取链修复，不证明模型授权有效/合成成功。
- **双保险：消除旧状态不一致**：`ReaderApp.speak_selected()` 在每次“试听”或“鼠标指向朗读”时从当前 GUI 实际选中音色以及最新 `settings['luna_config']` 取值，作为同一个 `natural_speak` 队列消息传给 `SpeechWorker`；worker 按需重建语音桥，避免先前扫描/导入产生的旧路径缓存。此更新不影响 SAPI/WinRT 普通朗读路径。
- **细分且脱敏错误**：`inspect_local_voice_config()` 分类配置未选择、路径文件不存在、无法读取、JSON损坏、Voice.License 字段缺失、字段存在。worker 支持 `check_config` 自检命令，只回传 `stage/code`，绝不回传原始许可证内容、完整配置路径；许可证不放 GitHub，不嵌入包。前台导入时的配置检查同步使用新分类。
- **原仓库独立实验分支**：`exp/v12-small-voice-config-route-fix-20261109`，基于之前已构建实验分支 `exp/v12-small-system-voice-discovery-20261109`（原先 V1.2 Small OCR 底子），**最终 HEAD `e000570123a8a5ac591a2e28c958fe2ac66eb940`**。V1.2 原版 `core.py`、`overlay.py`、`win_screen.py`、`cues.py` 的 Git blob SHA 再次核对与 V1.2 原样一致，Small OCR 仍使用 V1.2 检测尺寸参数，无 V1.4 的 max/1280；Medium 模型及已删除的自动场景变化检测仍不恢复；旧 V1.2/V2.0 和 main 源码没有覆盖。
- **CI 测试/构建（真正 Windows runner）**：最终 GitHub Actions **run `42640318964` completed/success**，包含所有 Python 单元测试、特别是模拟 cp1252 的二进制 UTF-8 输入测试、配置状态分类测试；V1.2 Small PP-OCRv6 DET+REC 两模型与冻结 EXE 实际 OCR、系统语音API、官方原版 Luna 二进制+GPL源码、**冻结 EXE 的带中文与空格路径 JSON 文件端到端读取自测**、UIA与主界面启动、ZIP 打包/Artifact 上传全部通过。早期 CI run 42639636517 对已存在中文文件误报不存在，促成确认编码错误和修复；只有最后新 run 标记为合格。
- **新下载包**：`GameTextReader-V12Base-NaturalVoice-ConfigRouteFix-Experimental`，GitHub Actions artifact id **13684269589**，下载页 https://github.com/vobichngan285-collab/-/actions/runs/42640318964/artifacts/13684269589；约 129,757,494 字节；截止 2026-12-09 的临时 artifact。下载是**公开无私人配置的包**；用户应另行在本机使用自己现有的原版 config.json，只选择本地文件，不上传密钥/内容。建议解压到独立目录，直接选已安装 Yunxi 试听；如果仍报错，截图错误代码即可。
- **重要验收边界**：**尚未在用户 Windows 11 真机确认云希/晓晓发声。** CI 证明 Windows 路径编码与跨进程文件读取正常，无法代替真实 Windows 语音模型与微软 SDK 授权/合成验证。如果后续错误推进到 `embedded_sdk_rejected_synthesis`、native runtime、IPC 等阶段，按该新码针对性处理；不得宣称“一切语音已修好”。截图出现自然音色仍只是“已安装、待试听”。
- **用户下一轮鼠标悬停 OCR、暗屏框选、独立模式切换等**仍只是待开发；本轮没有动这些功能。



## 2026-11-09 · GameTextReader 下一版完整鼠标 OCR 实验包（Windows CI 通过，鼠标侧键/游戏弹窗待真机验收）

- **用户授权**：明确“可以做实验包，把这些功能全部都加进去，写好代码之后逐行检查，没有逻辑漏洞就生成安装包”。实验使用**原仓库** `vobichngan285-collab/-`，从此前已构建且**用户实机确认云希/晓晓真正有声**的 `exp/v12-small-voice-config-route-fix-20261109` commit `e000570123a8a5ac591a2e28c958fe2ac66eb940` 新建独立分支 `exp/v12-small-hover-ocr-mouse-hotkeys-20261109`；保留 main、V1.2、V2.0 及原实验历史，不覆盖原代码。
- **需求已实现**：默认快捷键 F8 仅重截屏、F9 只在两种鼠标模式间循环（按用户原顺序首次按 F9 确认默认指向朗读，第二次切到悬停 OCR，第三次默认，以后循环；开机默认指向模式也保持 V1.2 兼容）、F10 在悬停模式手动立即局部识别；三键可分别自定义为**单个键盘键或标准鼠标 XBUTTON1/2**，不能占用相同按键；不使用 Ctrl/Alt 组合。由于 Tk `<KeyPress>` 不会收到鼠标侧键，录制侧键用原 Windows `GetAsyncKeyState(0x05/0x06)` 20ms 轮询和按下沿去抖，执行阶段也按虚拟键码读取。若鼠标驱动将侧键映射为键盘宏则按驱动映射效果行事，不能承诺系统完全屏蔽游戏原本侧键行为。
- **两套逻辑独立**：默认模式使用既有 F8 全屏 OCR 文字框和原点击即读/四边绿色框处理，保留 60 秒有效期；悬停模式按用户指定毫秒间隔（100～60000，输入保存，默认500ms）截图**鼠标周围局部区域**并使用同一个 V1.2 Small 检测器识别当前提示弹窗，不要求指针移动到文字框上。支持专用手动局部 OCR 键强制重新朗读。没有加入用户拒绝的画面变化识别逻辑；当 OCR 尚未完成，下一周期直接跳过不排队；F8 全屏请求至多留一个待处理，局部 OCR 与全屏 OCR 不并发访问同一引擎。归一化同文周期不重复朗读，新内容才触发语音；切换模式使用 generation 丢弃旧局部结果并停止旧朗读。
- **暗屏框选**：新增设置按钮，隐藏主窗口、当前显示器半透明变暗、屏幕中央十字准星代表未来鼠标位置，左键拖出任意矩形、松开保存、Esc 取消；保存宽、高及相对中心准星偏移，游戏运行时通过实际鼠标物理坐标计算并随鼠标移动，靠显示器边缘平移/裁剪；支持负显示器坐标。框选时停用 OCR 防止识别软件遮罩。
- **严格保护**：重新读取 Git tree，`core.py`、`win_screen.py`、`overlay.py`、`cues.py`、`ocr_backend.py` 与用户实机成功的上一基础分支 **blob SHA 完全一致**；`speech.py`、`luna_bridge.py`、`luna_voice_worker.py`、`ms_voice_discovery.py`、`luna_natural_voice.py`、`upstream_luna_pipe.py` **同样逐一 SHA 相同**，没有重动真正已经成功的自然语音链路。唯一 OCR 模型仍是 V1.2 默认 Small DET+REC，保持原始默认检测图像尺寸参数；Medium 和旧场景变化检测保持删除。新模块 `game_reader/hover_modes.py`、`game_reader/region_picker.py`，仅改 `game_reader/app.py` 和隔离实验工作流/测试。
- **CI/自动化检查**：最终实验 commit **`b391d3a87b5e7284aacc0c379fbcca0f86a7d470`**，GitHub Actions **run `42649078052` completed/success**，**50 passed, 1 warning**；其中 Windows 实际 Tk 暗屏区域选择和取消、快捷键冲突和鼠标侧键边沿状态、F9 首次/第二次模式序列、剪裁坐标含多屏负坐标、毫秒非法值、纯 OCR 去重、旧任务丢弃、原 V1.2 Small OCR 配置回归均有测试。冻结 EXE 的 Small OCR、SAPI/WinRT 可导入与语音子进程 IPC / 中文路径自测、应用 UIA/启动、原版 Luna 模块 + GPL 许可来源及哈希、完整 ZIP 上传全部通过。唯一 warning 是未改动的上游适配器文档字符串转义提示（不影响构建）。
- **下载**：公开无用户私有许可的 GitHub Actions artifact **13687659996**，名称 `GameTextReader-V12Base-MouseHover-SideHotkeys-Experimental`，浏览器下载链接 https://github.com/vobichngan285-collab/-/actions/runs/42649078052/artifacts/13687659996 ；GitHub 返回 artifact ZIP 大小 **129,776,746 bytes**，保留至 2026-12-09 UTC。内部为 `GameTextReader_V12Base_MouseHover_SideHotkeys_Experimental_x64.zip`，再解压可得 `GameTextReader/GameTextReader.exe` 与依赖。
- **验收边界**：CI windows-2025 云端不能模拟用户电脑上真实游戏/真实鼠标侧键/独占全屏兼容，也不能证明新包云希及晓晓在用户 Windows11 依然确实发声；之前同一语音链路**由用户在上一实验包亲自证实能播放**，本次没有改代码。应让用户先单独解压，不覆盖已成功的语音版，确认快捷键、暗屏选区、不同游戏弹窗自动朗读，以及云希晓晓真机语音回归。若有异常需截图/诊断再精修，不要宣称全部硬件真机验收通过。
- **隐私/许可证**：原始 `config.json` 只在用户自己的 Windows 电脑上，构建包与 GitHub 仓库不含私有 License；云端使用虚拟字符串，绝不能公开泄露用户文件。


## 2026-11-10 · Windows 游戏 OCR 关键修复：全局框选、指针错位、微软自然语音启动延迟（CI 已通过，游戏真机待验收）

- **用户实机失败反馈**：上一鼠标 OCR 实验包 (Actions 42649078052) 的暗屏选区只成功一次，随后“按住画框快捷键无反应”；鼠标已移动到屏幕左侧约三分之一，程序仍朗读桌面的“此电脑”“回收站”等错位文字。后续用户明确追加“把之前讨论的微软自然语音变慢一并解决”。上一版的“50 passed”仅说明构建测试，不是实机通过。不要再次推荐那个旧实验包当成正常版。
- **只读核对后定位的缺陷**：旧版没有**独立全局框选键**，只有主 UI 按钮；根窗口 `withdraw()` 后生成 Tk 子 Toplevel，重开/游戏覆盖时可能不可见；旧悬停识别把鼠标周围整个裁剪区域的所有文字都朗读，并没有检查识别完成时鼠标是否已离开截图位置；默认指向模式允许继续引用更换游戏/应用窗口前的 OCR 坐标；启动默认已是指向模式但旧 F9 第一次竟然只“确认默认模式”，必须再按第二次才进入悬停模式。自然语音每句话重启一层 Python 子进程和一层原作者 Luna 原生语音进程，造成不必要的启动延迟。**这些是源代码可确认的逻辑问题**；不代表已量化用户设备的具体耗时或游戏窗口合成行为。
- **原仓库和独立实验分支**：`vobichngan285-collab/-`，从 `exp/v12-small-hover-ocr-mouse-hotkeys-20261109` 的 `b391d3a87b5e7284aacc0c379fbcca0f86a7d470` 分出 `exp/v12-small-hover-ocr-picker-pointer-fix-20261110`。最终提交/CI HEAD **`bb70f140e7b416434de12d1cf29f79336b579ca6`**。未覆盖之前工作版本、其它分支或 main 的应用源码。
- **F11 全局截图式框选（也能录成鼠标侧键）**：新增独立的 `pick_vk` 默认 F11/可自定义键盘单键或 XBUTTON1/XBUTTON2；通过与 F8/F9/F10 相同的 Windows 异步虚拟键轮询，从游戏、桌面、其它页面均可触发。框选前将 Tk 主窗口保持“映射但完全透明”（避免 `withdraw`/最小化父窗口导致子 Toplevel 不出现），获取当前显示器**内存截图**并压暗显示为框选背景，十字点和拖动矩形可见；Esc 取消、按下拖动松开确认、保存相对鼠标坐标、最后恢复原主窗口状态。截图未保存到磁盘或提交云端。截图失败可退回半透明遮罩。每次进入框选递增 generation 并停止旧语音，丢弃旧 OCR 结果。
- **F9 循环错误修复**：开机默认保留 V1.2 指向朗读，但**第一次**按 F9 即刻进入悬停 OCR；第二次返回指向，第三次再进悬停。之前用户看到“没反应/还在读旧区域”，此错误会明显恶化体验。
- **鼠标位置和朗读关联修复**：局部 OCR 结果携带截图时物理鼠标坐标与前台窗口 class，识别结束后如果鼠标已移动约 45px 之外或者焦点换窗，立即丢弃过期结果；已经开始合成/朗读的内容在鼠标远离原截图位置后立即停止；桌面/Explorer 前台不再把“此电脑”“回收站”等当成游戏弹窗周期 OCR。普通指向模式在 Windows 前台 HWND 换窗后自动销毁旧截图的 OCR 坐标（*不是*用户反对的逐帧场景变化检测），且指向 A→B 不仅 A→空白都会停止旧语音。仍需要使用 F8 更新对应当前窗口的全屏 OCR 坐标。
- **微软自然语音低延迟方案**：保留用户已实际验证发声的私有本地原版 config、未修改的原作者 LunaSubprocess64.exe 和 SDK/音色发现/许可处理；新增 `natural_voice_session.py`，通过持续存在的 `--luna-worker` UTF-8 JSON-lines 进程缓存原作者 native engine，**同一音色连续朗读不再重复扫描包、装载 DLL、启动两级进程**，仅切换音色/配置或发生故障时重建。选择自然音色后支持异步预热。`luna_bridge.py` 用单后台工作线程加至多一条“最新待读文字”取代每句话独立 Python 子进程，并以 generation 防止迟到的 WAV 重新播放旧文本，stop 只停止 WAV 不杀掉已预热的原生引擎；准备/请求到播放启动耗时以不含密钥的诊断事件回传。原版 SAPI/WinRT 继续可用。**尚未经过用户电脑真实云希/晓晓低延迟验收，不能保证固定缩短多少毫秒**。
- **保护及兼容**：与已在用户电脑成功发声的 `e000570123a8a5ac591a2e28c958fe2ac66eb940` 基础版对比，`game_reader/core.py`、`overlay.py`、`win_screen.py`、`cues.py`、`ocr_backend.py`、`prepare_models.py`、`luna_natural_voice.py`、`upstream_luna_pipe.py`、`ms_voice_discovery.py` Git blob SHA **均不变**；唯一模型仍 V1.2 默认 Small DET+REC，无 Medium、无旧场景变化检测。自然语音的 Windows bridge/worker 新增重用管理，但未改原版原生合成 EXE。
- **CI 真实结果**：最终 GitHub Actions **run 42658651753 completed/success**；源码 **58 passed, 1 skipped, 1 warning**（hosted Python 单独 Tk 运行时缺 Tcl auto.tcl，改用冻结 EXE 强制实际检查）；打包后的真正 Windows GUI EXE **连续三次暗屏框选开关/拖选/原窗口状态恢复**全部 PASS，V1.2 Small 模型实际 OCR、SAPI/WinRT、**冻结 EXE 持续两次请求的同一语音工作进程**、中文配置路径、UI Automation、完整应用启动和 ZIP Artifact 上传全部 success。保留原版 Luna 子程序校验哈希和对应 GPLv3 源码。不内嵌用户的配置密钥。
- **用户下载链接**：GitHub Actions [run 42658651753](https://github.com/vobichngan285-collab/-/actions/runs/42658651753)，Artifact **13693462858**，地址 https://github.com/vobichngan285-collab/-/actions/runs/42658651753/artifacts/13693462858，名称 `GameTextReader-V12-PickerPointerFastVoice-Experimental`、约 **129,795,378 字节**；2026-12-09 过期。需解压两层 ZIP 到单独目录，不覆盖用户已成功使用的云希/晓晓旧版。
- **真机待验收**：需用户在自己的 Windows11、实际游戏、自己的鼠标侧键上确认 F11（可自定义）是否从任何页面立即打开暗屏截图式选择、能反复成功退出和重开；F9 第一按切换；F8 旧坐标更新；按鼠标位置局部识别不再报旧桌面文本；连续多段云希/晓晓语音是否实际降低等待时间、没出现声音消失。CI 的 Windows 桌面并不等同于全屏独占游戏/鼠标驱动、实际微软自然语音许可环境；不可宣称所有游戏已经真机通过。如果仍不准确，先让用户提供具体模式和位置再处理，拒绝盲目叠补丁。


## 2026-11-10 · 鼠标居中就近朗读实验包（用户已授权，Windows CI 完成，真机待测试）

- **用户明确反馈及批准**：在前一版实测 Windows 桌面，鼠标指向下方 DLSS 图标，却朗读上方“7 Days to Die / 七日杀”；用户确认当时是在“鼠标悬停 OCR”模式，并要求直接简化为**以鼠标为中心定期扫描附近文本、找到就近文字立即朗读**，不再对整块截图的全部文字拼接发声；“可以，那你先把实验版搞出来，我先测试一下”。本轮无需再询问模式。
- **独立分支及可回滚基础**：`exp/v12-small-pointer-centered-nearest-ocr-20261110` 基于上一修复并完成构建的 commit `bb70f140e7b416434de12d1cf29f79336b579ca6`；最终 Windows 构建 HEAD **`316c1998e451d1664fa442eeeb2f63acec701a1d`**。旧版、主分支应用源码、此前能用的语音包均没有被覆盖。没有创建新仓库。
- **确切代码变更**：新增纯策略 `game_reader/hover_target.py`，`centered_region()` 保留旧 F11 框选的宽高，**忽略之前保存的 x/y 偏移**，始终计算鼠标为中心的截图 bbox（屏幕边缘仍平移夹紧）；`nearest_readable_text()` 以 OCR 原始物理屏幕坐标计算鼠标到各文字框的实际欧氏距离，**仅选一个最近阅读区域**（沿用原 V1.2 的长段落换行合并），没有距离在 155px 内的文字便返回 None、不朗读无关远处文字。原先 `_handle_hover_result` 的 `"\\n".join(region.text for region in regions)` 整框朗读已替换为最近区域选取；保留跨帧相同文字去重、OCR 工作串行、离开截图位置 45px / 换窗丢弃旧结果与停止旧语音。新的 F11 框选只决定扫描宽高（显示提示也已说明），避免老选区偏移继续影响鼠标中心。
- **纠正额外的直接冲突**：移除 `start_hover_ocr` 中禁止 Windows 桌面/Explorer 前台进行扫描的条件。用户明确需要在任意页面使用鼠标局部文字朗读，桌面 DLSS、7 Days 等标签亦应可被识别；不增加新的场景变化模型或视觉大模型。
- **保护原有 OCR 与语音**：对照旧基线与最终 Windows 打包 commit 的 Git tree SHA，`game_reader/core.py`、`ocr_backend.py`（原 Small DET+REC）、`win_screen.py`、`overlay.py`、`cues.py`、`speech.py`、`luna_bridge.py`、`luna_voice_worker.py`、`natural_voice_session.py`、`upstream_luna_pipe.py`、`ms_voice_discovery.py`、`foreground.py`、`main.py` **全部逐项 blob SHA 相同**。先前做好的系统云希/晓晓授权读取、低延迟预热/原版 Luna 引擎复用、全局 F11 屏幕快照暗屏框选、F8/F9/F10 和鼠标侧键等均保持未修改。
- **关键回归测试**：新增 `tests/test_hover_target_nearest.py`，用用户同样的“7 Days 在鼠标上方、DLSS 在鼠标下方”真实几何布局做模拟，必须只返回 DLSS；包括距离外无字不说、技能提示长段落原有合并、多个同名标签、负坐标显示器、边缘裁剪、旧偏移改为鼠标居中、Progman 桌面前台允许 OCR 截图、截图尺寸/模型与坐标对齐等。调整了此前假定“区域全部文字一起读”的旧测试，保留模式切换、键盘/侧键热键及延迟 TTS 测试。
- **构建与 Artifact（已经验真）**：GitHub Actions Windows run **`42664550473` completed / success**，**67 passed, 1 warning**，无失败。打包冻结 Windows EXE 原生 PP-OCRv6 Small 识别、SAPI/WinRT 依赖、语音 worker 同进程多请求与中文路径、Windows 真 Tk F11 三次打开/取消/拖框、完整 App 启动、自检、公开无私有 License ZIP 上传均成功。Artifact **`13695738684`**，名称 `GameTextReader-V12-MouseCenteredNearestOCR-Experimental`，大小 **129,797,452 bytes**；用户直接下载 https://github.com/vobichngan285-collab/-/actions/runs/42664550473/artifacts/13695738684 ，有效至 `2026-12-09T17:27:54Z`（UTC）。
- **真机验收边界**：CI 只证明 Windows 实验包构建和模拟 DLSS/7 Days 几何测例/EXE 自检成功。实际 Windows11 游戏鼠标指向 DLSS、7 Days、图标外空白时是否读对，微软云希/晓晓是否有声和速度，窗口独占全屏截图是否成功，仍以用户下载后实机验证为准。无法保证 PP-OCRv6 Small 必然识别被图标遮挡的文字；OCR 距离阈值固定 155px，真机可按实际截图再校准。让用户单独解压，不要覆盖已能发声的上一版，也不要公开上传本地配置许可证。


## 2026-11-10 · 用户定稿清爽蓝色大字 UI + 无障碍 + 鼠标局部 OCR/过滤/提示（Windows 构建成功，待实机读屏和游戏验收）

- **用户明确授权**：“可以就用这个，然后你结合我们上面说的所有的更新条件，现在就可以生成安装包了”，并追加硬要求：“记住别搞了新配色之后无障碍这一块就不读了这一块一定要注意”。用户最终选择的是**第二张清爽蓝色界面**，拒绝首版拥挤的霓虹堆叠式设计。此轮无需再问设计方向。
- **原仓库分支/基线**：`vobichngan285-collab/-`，独立实验分支 **`exp/v12-clean-blue-a11y-filtered-mouse-20261110`** 从用户上次可下载的就近文字实验 `316c1998e451d1664fa442eeeb2f63acec701a1d` 创建；最终 Build HEAD **`6f1a78125c3fab9e7b0d04f7ac0180ea266a3b69`**。保留历史 V1.2 / 自然语音可发声版 / 前几次实验版。不覆盖 main 应用代码。
- **本版 UI**：`game_reader/ui_theme.py` 深蓝底、浅白高对比文字、13–22pt 大字号、干净左侧导航 6 页（OCR与鼠标、语音设置、全屏OCR、内容过滤、通用设置、关于软件），右侧清晰卡片化设置；鼠标模式和默认模式有独立按键；提供“恢复默认”和“应用设置”按钮；原版微软云希/晓晓自然语音扫描、导入本机 config.json、试听、音量/语速、F8–F11 全部保留。
- **无障碍硬性保护**：所有导航按钮、模式选择按钮、4 个快捷键按钮、Checkbutton 三个过滤开关、文本阈值 Spinbox、语音 Combobox、音量/语速滑杆、诊断/状态与原始 OCR Text 均是**原生 ttk/tk 控件**，未使用画布模拟按钮，仍通过 `tk_uia.enable` 与 `tk_uia.set_acc_name` 设置控件名称。隐藏的分页使用真正的 `grid_remove`，防止读屏/Tab 走进被遮住的设置页。源码 `main.py` 新增**强制打包后自检**，验证控件实际存在、原生 Win Tk 类型、6 页切换时只有当前页面映射、UI Automation 启用，并在日志回传状态。**真实 Windows frozen EXE 测试结果**：`UIA: Strategy.PROVIDED`、`Named native controls: 35`、`Tested pages: 6`，全部 PASS。此为 Windows UI Automation 自检，**不是**已在用户真实 NVDA/讲述人等读屏工具中逐项听过；必须区分。
- **鼠标扫描框**：基于原版四条原生 Win32 `WS_EX_TRANSPARENT | WS_EX_NOACTIVATE` 小窗口，为鼠标 ROI 增添独立**淡绿色半透明 2px** 外框，真实位置使用 `capture_box(centered_region(...), mouse, monitor)` 与截图一致，在鼠标跟随模式展示；默认模式/按 F11 暗屏框选/设置关闭时隐藏。原旧高亮 `ClickThroughOutline()` 的默认 alpha、padding、thickness 均保留向后兼容；新增可选 alpha=92/padding=3/thickness=2。没有带交互焦点的画布遮挡游戏。
- **鼠标模式语音提示**：F9 或对应鼠标侧键每次切换，都先停止旧语音，再通过当前选中的语音播报准确短语“鼠标模式”或“默认模式”，不通过英文/数字/符号过滤；为避免 OCR 抢断提示，切换后短暂推迟局部 OCR 调度。可以在设置里关掉语音提示。
- **用户明确纠正后的 OCR 处理**：**不再使用上一版的“最近文字距离”算法**，也不搞图像变化模型或物品图标分类。鼠标只决定截图中心与框的宽高，周期（默认保存 500ms、按钮恢复默认 400ms）截取一小块画面，用**原版 V1.2 Small DET+REC、原版 `build_reading_regions` 排列规则**按行生成局部文本，先过滤、再比较重复，发现新文字就朗读全部局部文本。F10 手动刷新/可强制重新朗读，F11 可调整扫描宽高。原始 OCR 文本在界面里仍完整保存显示，过滤只影响语音。
- **朗读过滤与相似阈值**：新增 `game_reader/text_filters.py`，三个独立开关默认全部**开启**：过滤 Latin 英文字母、Unicode 数字、标点/特殊符号；能独立关闭；同时对过滤后的文本进行前后比对与**有界编辑距离**重复抑制，默认阈值2、可设0–8，短文字长度不超过4采用完全相同才跳过，确保“碎布→石斧”仍朗读，而“碎布18→碎布19”在数字过滤打开时不重复读。给游戏物品栏多行名称与18/173数量编了回归测试。
- **保持不动的根基**：基线和最终 Git tree SHA 逐文件核对，`game_reader/core.py`、`ocr_backend.py`、`win_screen.py`、`cues.py`、`speech.py`、`luna_bridge.py`、`luna_voice_worker.py`、`natural_voice_session.py`、`ms_voice_discovery.py`、`upstream_luna_pipe.py`、`region_picker.py`、`hover_modes.py` 均不变；PP-OCRv6 Small 是唯一模型，不恢复 Medium 或旧场景变化检测；保留已经由用户在旧包实测成功的微软语音及持续进程低延迟调用链。原始许可 config.json 只在用户电脑上，不打入公开 ZIP。
- **真实 CI 状态**：最后 GitHub Actions run **`42674922910` completed/success**；**78 passed, 1 skipped, 1 warning**（skip 是 hosted source Python 的 Tcl 运行时，冻结 EXE 真正运行 3 次 F11 Tk picker 测试 PASS）；Windows 实测 frozen EXE 通过 V1.2 Small OCR、SAPI/WinRT 模块、云希/晓晓worker无密钥协议与中文路径/复用、点击穿透框自检、全应用 GUI 启动与 UIA (35命名原生控件 + 六页)、ZIP 文件生成及上传。早期 run `42673587752` 的测试脚本自身误判文档中的 Canvas 用词，随后修复；run `42674652065` 因新增诊断日志行的 Python 转义符错误在 compileall 被挡住，已修复；另几次 run 0 jobs 的调度失败不代表通过。只有最后绿色完整 run 为验收结果。
- **下载地址**：GitHub Actions Artifact **`13698963874`**，名称 `GameTextReader-V12-CleanBlue-AccessibleFilterOCR-Experimental`，大小 **129,812,722 bytes**，临时保留至 `2026-12-09T18:34:10Z`，公开可验证链接 https://github.com/vobichngan285-collab/-/actions/runs/42674922910/artifacts/13698963874 。Windows x64 便携双层 ZIP，用户要逐层解压，在单独目录启动 `GameTextReader.exe`，不覆盖旧版本。软件截图和语音许可不上传。
- **尚未完成的实机部分**：用户 Windows11 实际游戏《七日杀》中鼠标跟随绿色框的穿透和坐标、短名称“碎布”、朗读节奏、三类过滤是否符合个人偏好、真实云希/晓晓实际声音，以及用户使用的**真实无障碍读屏器是否逐个读出新 UI 控件**都需用户亲机测试。**不能将 Windows UI Automation 的 provider 通过宣传为实际辅助读屏器实测已过**。如果用户在读屏器里遇到不朗读，下一轮优先修复该问题，不改变旧成功的 V1.2 OCR 和语音链。

## 2026-11-10 Windows Blue Star OCR V1.2 清爽蓝色 UI 功能微调／性能优化实验（通过 Windows CI）

- **代码分支**：`feat/windows-v12-cursor-drag-clear-speed-20261110`；**Build SHA**：`d5720f6924471200b3f2b68cc5a42a7c74f7c653`；基于 `6f1a78125c3fab9e7b0d04f7ac0180ea266a3b69`，没有覆盖原版蓝 UI。
- **功能**：默认模式识别成功且有可朗读内容播放短促叮声（可关闭）；F11 光标起点四方向拖动松开立即 OCR，绿色框跟随保存 X/Y 偏移；新增可自定义 F6 立即清除 OCR 与朗读、取消过期结果，原 60 秒自动清空保留。修复 `spoken` 未初始化、延迟调度及旧语音队列，局部截图减少重复颜色转换、OCR 串行锁、截图与推理分段耗时记录。
- **验证**：GitHub Actions [42684557197](https://github.com/vobichngan285-collab/-/actions/runs/42684557197) `completed/success`；87 passed / 1 warning，冻结 Windows EXE Small OCR、UI Automation 37 个原生命名控件、F11 Tk 重复拖框、常驻自然语音 worker 协议、原版 Luna 哈希与 GPL 源码等检查均成功。
- **交付**：GitHub Actions [artifact 13704431105](https://github.com/vobichngan285-collab/-/actions/runs/42684557197/artifacts/13704431105) (129817505 bytes, 至 2026-12-09T19:36:02Z)，便携 ZIP，**不含私人语音配置**。下一步 Windows11 游戏场景、自然语音真实出声/提速、真实读屏器真机验收，不保证任何未经测试的速度改善百分比。

## 2026-11-10 · 固定区域跟踪第三模式实验版

- 原仓库 `vobichngan285-collab/-`；开发分支 `exp/windows-fixed-region-tracking-20261110`，构建源码 `a93e31e4b034df6e514bd5b314c05ee702378c16`，基线 V1.2.1 `997ade1552d097917b8a3121b963c4b45d6844fb`。
- F9 循环默认/鼠标跟随/固定区域跟踪；区域跟踪 F11 暗屏自由框选、松手启动；保存绝对屏幕区域与显示器几何，切回自动恢复。区域两种策略：画面变化才 OCR（约300ms 低成本差分）／自定义100至60000ms周期 OCR。
- 固定区域只朗读新行，相同文字不重复；文字消失后再出现可重读。OCR 模型全局锁、模式 generation 和任务 job_id 防旧结果串模式；F6 清空保留当前固定区域去重状态，防下轮把相同文字重新朗读。
- 边框统一五色、1～8像素，可默认显示；F7 自定义快捷键即时显示/隐藏固定框、完全不触发识别或 TTS；边框保持 Win32 原生点击穿透且在 OCR 采样边界外。
- 用户要求的逐项逻辑审核：修复旧冻结 F11 自测缺少状态字段导致的显示失败，解决新 F7 单控件测试夹具访问无关控件的问题；旧 F8/F11、语音、模型、不改用户私人配置。未合并 main 应用代码、未覆盖旧包。
- **最终 Windows Actions** [42762512266](https://github.com/vobichngan285-collab/-/actions/runs/42762512266) 已完成成功，**109 测试通过，1 warning，0 失败**，真实冻结 EXE/Small OCR/未修改原版 Luna/持续语音IPC/UIA 49命名原生控件/F11 三次 Tk picker/五色8px native outline 通过。
- **便携安装实验包** [artifact 13737813672](https://github.com/vobichngan285-collab/-/actions/runs/42762512266/artifacts/13737813672) 129838758 bytes，有效期 2026-12-10T05:31:57Z，内层 `GameTextReader_FixedRegion_ThreeModes_Experimental_Windows_x64.zip`，不含私有 `config..json`。下载后解压新目录运行 GameTextReader.exe，非 MSI，不覆盖旧版。
- 用户电脑 Windows 11 / 《七日杀》真实 OCR变化检测、持续 CPU 开销和游戏 FPS、显示器边缘、音频输出仍待确认，不冒称已经真机验收。

## 2026-11-10 · 区域跟踪实验包公开直链发布

- 用户反馈 GitHub Actions artifact 速度慢、无法解压；原 artifact 129838758 bytes 含内层单 ZIP，外层 SHA256 `de3a5f924806b5f9b9bc52cccab461078dad27ee266ed74adbb6e66719307477`。复核内层 130279329 bytes / 1194项，ZIP CRC 测试 0错误，SHA256 `e58d38a2c2948cda5c6a3d0472b6187e2d527b2c5d2ec3009b9d27e420182430`。
- 新独立 release workflow `.github/workflows/publish-region-experiment.yml` commit `8b86a382e67cdd6cb69f31c6a37f79fe7bef7965`，Actions [42776413685](https://github.com/vobichngan285-collab/-/actions/runs/42776413685) completed/success；从先前成功 Windows 构建直接取内层原字节，SHA256/ZIP 测试通过。未重新编译也未改 app。
- GitHub 公开 prerelease [win-region-experiment-20261110](https://github.com/vobichngan285-collab/-/releases/tag/win-region-experiment-20261110)，非草稿，asset 730542023，已 uploaded，大小 130279329 bytes：
  https://github.com/vobichngan285-collab/-/releases/download/win-region-experiment-20261110/BlueStarOCR_RegionTracking_Windows_x64.zip
- 单层 ZIP，用户直接下载解压后进入 GameTextReader 运行 EXE；无需进入 Actions 页面。GitHub CDN 速度取决于用户实际网络，仍需用户验证。


## 最新进展｜2026-11-10 Windows 游戏窗口截图 + 鼠标滚轮智能清除 + 全屏计时（独立实验版构建与公开发布成功）

- **项目和隔离：** 唯一优先为 Windows 11 游戏 OCR（非安卓）。原仓库 https://github.com/vobichngan285-collab/- 。原固定区域实验版本和稳定版保留；本轮新独立分支 `feat/windows-game-capture-mouse-clear-speed-20261110`，目前发布工作流修复后的分支 HEAD `07f8e60aad103c9a0021f71fa2e47ea315a9bfdf`。**实际被 Windows runner 编译的应用源码 Commit 是 `31a92b90c43f15bfe0d817cd7d044a2344803ca4`**；后续为许可证说明和发布工作流，不能误认为另一个 EXE 编译版。
- **更新 1（鼠标）：** 新 `game_reader/mouse_input.py` 采用独立 WH_MOUSE_LL 消息线程处理滚轮方向增量，永远 CallNextHookEx 放行原鼠标滚动；鼠标中键、侧键与键盘仍使用现有 GetAsyncKeyState；快捷键绑定、名称、重复冲突检查共享原逻辑。新默认清除键为「滚轮向下」，旧 F6 默认配置升级；用户改过的其他按键原样保留。加入滚轮短时间重复抑制和细粒度 delta 累积。
- **更新 2（三模式智能清除）：** 默认模式删除旧 OCR 坐标、框、朗读；鼠标跟随模式清除后停止自动扫描，重新进入模式才恢复；固定区域模式清除 `fixed_region` 和 `fixed_monitor` 的记忆，停止扫描并使旧 job 失效、隐藏边框，需 F11 再框选。F7 只控制边框显示，不改变 OCR。区域跟踪依旧保留普通模式切换后的恢复能力，除非用户真的按清除快捷键删除。
- **更新 3（F8 诊断）：** 记录按键到 OCR 完成、截图、OCR 锁等待、图像预处理、模型推理阶段的毫秒数；避免已有 RGB 图像的重复 RGB 转换；主窗口触发的固定隐藏等待从 250ms 减少为 120ms（游戏内 F8 仍立即处理）。**没有把成功叮声提前到 OCR 完成之前**，没有调整 Small 识别模型权重，也没有声称真实提速百分比。
- **更新 4（大型游戏截图）：** 新 `game_reader/luna_capture.py` 参照原作者 HIllya51/LunaTranslator `v12.1.3.9` 的 `src/NativeImpl/NativeUtils/screenshot.cpp`：优先目标游戏 HWND 的 GetDC + BitBlt，坐标 ScreenToClient，对空白窗口截屏回退原桌面 ImageGrab；全屏、局部、框选快照和固定区域调用统一的截图接口。原版 LunaSubprocess64.exe 和所有语音适配未改动。新增 `LUNA_CAPTURE_NOTICE.md` 明确 GPLv3 来源；公共发布提供本项目源码 ZIP 和原 Luna 上游 GPL 源码包。
- **Windows CI：** [run 42787182157](https://github.com/vobichngan285-collab/-/actions/runs/42787182157) `completed/success`，**116 passed、1 warning、0 failed**；冻结 EXE、真实官方 Small ONNX OCR、原版 Luna worker、UI 自动化无障碍控件、F11 Tk 框选均通过。新测试覆盖滚轮高精度 delta、方向绑定和冲突、三模式智能清除、HWND 优先/桌面回退。
- **公开 Release：** [run 42787873992](https://github.com/vobichngan285-collab/-/actions/runs/42787873992) `completed/success`，发布 `win-gamecompat-mousewheel-vnext-20261110`，不是旧区域实验包。单层 Windows ZIP 130291497 bytes、SHA256 `c1214fc5c4f52efc936f74895e33532c3650fb1396b4132a3058a1300ca59055`；[直接下载](https://github.com/vobichngan285-collab/-/releases/download/win-gamecompat-mousewheel-vnext-20261110/BlueStarOCR_GameCompat_MouseWheel_Windows_x64.zip)。另外公开项目源码 ZIP 124186 bytes、SHA256 `dd48f6b752fa16bef96fe92bf931fa649503a217c40c3cb3f62a738c7495b806`。ZIP CRC 和内部 EXE/原 Luna 源码均验证过；私人 `config..json` 不公开也不修改。
- **边界与验收：** 这是**待用户真机测试的独立实验版**，不能宣称《荒野大镖客 2》/ Vulkan、DX12、独占全屏游戏已修复，也不能宣称鼠标滚轮钩子在所有游戏都能收到消息或云希/晓晓已听觉验收。Windows CI 无真实 3D 游戏、用户设备或微软语音授权。测试重点：F8 是否按键生效且截图来自游戏、文字框能否正确命中、滚轮是否既能清除又保留游戏滚动、模式清除后不自动重生、F8 阶段耗时。若问题复现，先取不含屏幕内容的阶段日志，不重写或替换原语音引擎。


## 最新进展｜2026-11-10 真实《七日杀》跨菜单朗读故障：固定游戏 HWND 修复实验版（已构建/发布）

- **用户发现的实际问题：** 新版在《七日杀》游戏首页「开始游戏/继续游戏/设置」可以 OCR 朗读，但点击「开始游戏」进入另一页面后，F8 有「叮」声、鼠标指向读不出当前页面文字。用户确认故障与滚轮无关，并指出游戏窗口自身未变；要求直接参照 LunaTranslator 的持久绑定游戏窗口思路，不重新设计 OCR/TTS。
- **原因与修复定位：** 上一版虽然参考了原版 `screenshot.cpp` 的 GDI/BitBlt，却缺少 `ocrtext.py` 中保存 `self.hwnd`、后续重复向 `imageCutEx(self.ref.hwnd, rect)` 提供同一窗口句柄的关键调用链；旧版仍每次捕获重新读取 GetForegroundWindow，并在前台 HWND 不同后立即清除旧 OCR。新增 `game_reader/game_window.py` 的 GameWindowBinding，首次在游戏里 OCR 时绑定外部游戏 HWND+PID；只要原 HWND 对应进程仍存在就不因为加载页/其他前台变化自动重绑；窗口关闭或 HWND 被回收时才释放与重新绑定。保留绑定窗口内不同子窗口同 PID 的活跃判断，失去游戏前台焦点时暂停鼠标朗读、保留已识别文字直至下次 OCR/TTL，而非直接清除。
- **接入范围：** `game_reader/app.py` 的 F8 全屏、F11 框选、鼠标跟随、固定区域连续识别统一传入同一绑定 HWND，实际像素每次重新截图而非缓存；`game_reader/win_screen.py` 截图函数新增可选固定 HWND；`game_reader/luna_capture.py` 沿用原 HWND 优先 GDI、失败回退 ImageGrab，并增加截图方式 `window_gdi` / `desktop` 纯元数据用于 F8 状态诊断。未改 Small OCR 权重、语音 DLL、原版微软云希/晓晓对接、滚轮键及三个模式的清除行为。
- **代码隔离：** 原 GitHub 仓库 https://github.com/vobichngan285-collab/-；新独立修复分支 `fix/windows-luna-bound-game-window-20261110`。**实际编译源码 HEAD `44c19d3043d52d5d673b03f46f8e5e63b6e92d68`**；发布脚本后续分支 Commit `08b5c97f164ce53187dceaa0fd5d243cb8fc72aa`，切勿混淆。上个版本分支不覆盖。
- **Windows CI：** [run 42800465082](https://github.com/vobichngan285-collab/-/actions/runs/42800465082) completed/success，**121 passed，1 warning，0 failed**；PyInstaller EXE 真正运行 Small OCR、语音 worker、UIA 无障碍控件、F11 三次真实 picker、应用自测等成功。之前 run 42800251220 因测试文件缺失 SimpleNamespace import，120 passed/1 failed，现已修复，不是产品故障。
- **GitHub 公开发布：** [run 42800815029](https://github.com/vobichngan285-collab/-/actions/runs/42800815029) completed/success；[Release win-game-bound-20261110](https://github.com/vobichngan285-collab/-/releases/tag/win-game-bound-20261110)，公开 prerelease、非草稿。Windows **单层** ZIP `BlueStarOCR_GameWindowBound_Windows_x64.zip`，130294928 bytes，SHA256 `c819f19aac8e97cd52889d68a70b5e951ec37665227f2f45215f057dfa22c913`，直接地址 https://github.com/vobichngan285-collab/-/releases/download/win-game-bound-20261110/BlueStarOCR_GameWindowBound_Windows_x64.zip；本项目源码 ZIP `BlueStarOCR_GameWindowBound_Source.zip` 130066 bytes，SHA256 `0fde30e7e76d112b16b5dcd0be92e22864321dde5c40d0afdbd4ba1c0297c186`，原版 Luna GPLv3 源码仍随便携包提供。ZIP CRC/EXE/源码检查通过，私人 `config..json` 不公开。
- **仍未解决/用户验收：** **不能保证《七日杀》切换页面后已经正常朗读，必须在用户 Windows 真机再试**；特别注意即使 HWND 固定，GDI 也可能在某些 DirectX/Vulkan 渲染场景返回旧帧，光标位置也可能来自游戏自绘鼠标而非系统坐标。新版 F8 诊断包含 `window_gdi` 或 `desktop`，若仍有叮声却读不到当前页面文字，下一步仅针对该截图来源问题排查，不重构已工作的语音/识别，不归咎滚轮。



## Windows GameTextReader 最新游戏窗口绑定版重新打包发布｜2026-11-10

- **用户反馈：** 最近版本在其 Windows 11 电脑“无法解压”，可能与不完整下载或解压程序有关；当前没有原错误信息，不能断言原 ZIP 损坏。
- **采取措施：** 在原仓库新隔离分支 `pack/windows-bound-zip-7z-recovery-20261110` **仅重打包，不重新编译或修改 EXE**。从原 Windows 121项通过的 CI run 42800465082 获取原冻结构建（实际应用源码 `44c19d3043d52d5d673b03f46f8e5e63b6e92d68`），先核验原始 ZIP 130294928 字节 SHA256 `c819f19aac8e97cd52889d68a70b5e951ec37665227f2f45215f057dfa22c913`，1186源文件CRC全通过，模型与原Luna源码及 EXE 均在。
- **新压缩格式：** 重新逐文件压缩并加入一次解压说明后为1187文件。Windows Explorer **ZIP_STORED 原生ZIP** `BlueStarOCR_GameTextReader_Windows_ExtractFix_Store.zip`：**282801938字节** SHA256 `cfd2821b62fa9fe9e31f584effb3cff56804c5cf770314d3dda2959942d4e28b`；**7-Zip备用包** `BlueStarOCR_GameTextReader_Windows_ExtractFix_7Zip.7z`：**106024961字节** SHA256 `311ea20cfa19ade8ae4af8870b783d74c592f39503b7e49e8a1b6de6be4da96f`。两个新包都CRC/测试通过、实际完整解压通过，**全部1187文件逐文件SHA256一致**；没有中等模型、私有用户配置。
- **构建与发布：** GitHub Actions run [42830988762](https://github.com/vobichngan285-collab/-/actions/runs/42830988762) completed/success，workflow SHA `a14d7ebd1d97d154336c5b68c2d5ea84757e3249`。新公开Release [win-game-bound-repack-zip7z-20261110](https://github.com/vobichngan285-collab/-/releases/tag/win-game-bound-repack-zip7z-20261110)，ZIP直链 https://github.com/vobichngan285-collab/-/releases/download/win-game-bound-repack-zip7z-20261110/BlueStarOCR_GameTextReader_Windows_ExtractFix_Store.zip ；7z直链 https://github.com/vobichngan285-collab/-/releases/download/win-game-bound-repack-zip7z-20261110/BlueStarOCR_GameTextReader_Windows_ExtractFix_7Zip.7z 。旧Release/源码不动；不动安卓仓库。
- **Windows用户解压：** ZIP推荐Windows“全部解压”到 `C:\BlueStarOCR\`，运行解压后的 `GameTextReader\GameTextReader.exe`，不要在 ZIP内运行EXE。若ZIP解压失败用7z+7-Zip；若两种都失败先检验下载大小和SHA256，排除下载被中断。真实游戏跨页识别、微软音色/鼠标快捷键表现仍需用户实机验证。


## 最新实验版｜2026-11-11 Windows《七日杀》跨菜单截图回归 + 全屏响应简化（构建及公开 Release 成功）

- **用户实际故障与授权：** 用户指出前一个绑定窗口版在《七日杀》主菜单 F8 OCR、鼠标朗读正常；点击「开始游戏」进入玩家档案/存档选择页面后，按 F8 听到叮声但无法正常朗读新页面文字。用户明确要求“简单粗暴，去掉一切不必要环节”，批准现在修改，目标同时减少 F8→提示音和鼠标指向→朗读的额外等待。之前“无法解压”反馈经用户纠正是**能解压并启动，但仍不读**；重新压缩不是解决办法。
- **原仓库、分支和可回滚：** `vobichngan285-collab/-`。新独立实验分支 `fix/windows-simple-visible-capture-fast-20261111` 从上一个游戏窗口修复分支 `08b5c97f164ce53187dceaa0fd5d243cb8fc72aa` 创建；**实际 Windows 构建源码 Commit `0954e8157e851587acd5130b472dbe2ef6d2ad71`**。不覆盖旧 ZIP、Release、V1.2/语音可用版，不改安卓项目，不合并到 main 应用代码。
- **根本设计改变：** `game_reader/win_screen.py` 中所有 OCR 图像路径走 `ImageGrab.grab(bbox,all_screens=True)`，取得此刻真正可见的桌面像素；不再向截图代码传递 HWND 以进行 GDI `GetDC+BitBlt`。F8 只用锁定游戏 HWND 通过 `GetClientRect + ClientToScreen` 找**当前客户区的物理屏幕矩形**，与光标所在显示器求交集，直接截图并返回正确原点。无游戏 HWND 时保留 V1.2 原整显示器截图。鼠标局部、F11、固定区域复用同一个可见像素来源；旧 `luna_capture.py` 仅保留源码/历史测试，不再从 win_screen 的实际截屏入口调用。窗口无效、最小化或不在对应显示器时**报错**，不盲目用旧图冒充成功。
- **响应精简：** `game_reader/app.py` 的全屏截图入口去掉多余条件分支；输入轮询从20/25ms收敛为15ms、OCR结果事件轮询从40ms改15ms，OCR确实产生过滤后非空文字时，**完成音立即入独立音效队列**，先于 Tk 文字及状态控件刷新；若无可朗读内容，不播放成功叮。详细诊断记录行数、朗读区域数、截图方式、截图/预处理/模型/锁等待时间。**不改 PP-OCRv6 Small/Medium 设置、自然语音 DLL/原 Luna worker/微软云希晓晓、鼠标滚轮、原有多模式/绿色框/无障碍**。模型仅 Small；软件只保留已做过的本地语音链。
- **专门回归测试：** `tests/test_pinned_game_window.py` 增加相同 HWND 模拟从主菜单跳存档菜单、两次捕获必须读到两帧不同桌面像素、窗口裁剪/坐标偏移、跨屏、最小化错误、F8 无绑定回退 V1.2 整屏、固定区域不调用 GDI；更新20→15ms的鼠标轮询断言。第一次 CI run [42854631681](https://github.com/vobichngan285-collab/-/actions/runs/42854631681) 为**124 passed / 1 failed**（断言还要求20ms）；更新断言重测通过。保留失败历史，不能当成功结果。
- **最终 Windows CI：** [run 42854889143](https://github.com/vobichngan285-collab/-/actions/runs/42854889143) **completed/success，125 passed、1 warning、0 failed**；PyInstaller真实 EXE 生成、Small OCR 实际模型推理、SAPI/WinRT、自然语音 worker 协议/中文路径、UIA/绿色框、自检主窗口、F11 真 Tk 框选均通过。逐文件流式读取 ZIP **1186 项通过**。注意这不是用户机上《七日杀》实际游戏测试，未测得真实 F8 速度提升幅度。
- **公开直链（单层 ZIP）：** [Release win-simple-visible-capture-20261111](https://github.com/vobichngan285-collab/-/releases/tag/win-simple-visible-capture-20261111)；`BlueStarOCR_SimpleVisibleCapture_Fast_Windows_x64.zip` **130292246 bytes**，SHA256 `f3aa38af7db2a97120612316fbb574af768c8d1441f181868cee5e3e20a5d88c`，直接 URL https://github.com/vobichngan285-collab/-/releases/download/win-simple-visible-capture-20261111/BlueStarOCR_SimpleVisibleCapture_Fast_Windows_x64.zip 。项目源码 ZIP 同一 Release：`BlueStarOCR_SimpleVisibleCapture_Source.zip`，135699 bytes，SHA256 `dbbe3d383458bd0436218fc14bbb9ab7e3352559931c5c72588f45d92023a9ef`。旧原版 Luna GPLv3 全部原始源包仍随 EXE 发布，无用户私有 config/License。
- **实际验收要点：** 新目录解压 ZIP，运行 `GameTextReader/GameTextReader.exe`，先在《七日杀》主菜单 F8、鼠标指向，再在存档选择界面 F8 指「玩家档案、继续游戏、管理存档」；核实**新菜单**文字/框与朗读是否一致；记录 F8 最后状态“截图方式 desktop_game_client / 检测文字行 / 截图与模型耗时”，对比上一版。游戏需要无遮挡的可见窗口；若独占全屏屏幕抓图不可用或有覆盖层，需要用用户机的实际截图/日志诊断，不能假称已全游戏解决。不得为小提速降低小字准确率。


## 追加｜2026-11-12 Windows 区域跟踪首次立即 OCR、模式彻底清理、F7 边框记忆（已构建／待真机验收）

- **用户明确授权修改：** 区域跟踪 F7 隐藏后切到别的模式再回来，绿色框自动重新显示；从默认模式切到区域跟踪，开始十几秒有字却不朗读；连续区域 OCR 玩游戏感到卡顿。用户明确表示 **300ms 变化检查已经自行验证，不认为它是卡顿原因，严禁凭猜测拉长扫描间隔**。同意“切换即旧任务失效、读完删除临时图片，仅保留必要去重、保持简单粗暴”并于本轮明确说“可以现在开始”。
- **原仓库与隔离：** 仍为 https://github.com/vobichngan285-collab/- ，本轮**不覆盖 main 应用代码或旧可用 ZIP**。从已发布、用户实测《七日杀》正常的可见桌面捕获源码 commit `0954e8157e851587acd5130b472dbe2ef6d2ad71` 创建独立分支 `fix/windows-region-instant-clean-20261112`；最终 CI 源码 HEAD `21bfe93b39ff3cd28cb7a3555fc5872a2fbf5c57`。
- **F7 边框：** 进入区域跟踪或 F11 重新框选时不再覆盖 `_region_border_visible` 的手动状态，初始化仍尊重设置中的 `show_scan_frame`；F7 只改变显示，不改变识别和语音。
- **模式切换瞬时清理：** `ReaderApp._switch_mouse_mode` 立即递增 capture/mode/region job ID，取消待处理全屏优先请求，将原模式 busy 标志、旧显示文本、旧朗读区域、过期计时归零，停止旧 TTS、隐藏旧框；旧 hover/region worker 在截图或获得 OCR 锁后先检查代号，过期即丢弃；旧 hover 事件不得误清新模式 busy 标志。**安全边界：已经进入 ONNX Runtime 的底层识别不能被强制中断**，它会安全结束且不得提供旧朗读，新任务仍可能等待共享 OCR 锁。
- **区域首次扫描：** 改为进入区域模式就立刻安排一次强制 OCR，不等待 180ms/250ms 的模式状态门槛；常规变化检查默认仍为每 `300ms`，未改 OCR 输入分辨率、官方 PP-OCRv6 Small 权重、游戏截图源和 F8 模式。
- **模型与内存：** `LocalOCR.prepare("small")` 在 app 启动后后台初始化一次，使用同一 OCR 锁并复用 ONNX 模型，避免切模式时不必要的冷加载；图片只在当前扫描 worker 局部变量中短暂存在，不进入任务队列，画面变化门限缓存改为 `128×72` 的 **9216 字节**缩略灰度特征 bytes（不是图片对象）；识别出来的原文不再常驻区域模式 UI 输出，只保留最小的最近文字去重状态。自然语音引擎的必要请求生命周期没有粗暴砍断，旧版语音路径不改。
- **自动化测试：** 首次 CI [43055164326](https://github.com/vobichngan285-collab/-/actions/runs/43055164326) 为 **125 passed／3 failed**：两个旧模拟环境缺少 `capture_id`，一个旧断言假设 Small 初始化必须在 `recognize` 方法内；随后兼容模拟对象并更新断言来验证 `prepare+recognize`。最终 Windows CI [43055498020](https://github.com/vobichngan285-collab/-/actions/runs/43055498020) **completed/success，128 passed、1 skipped、1 warning**；Windows EXE 真实执行 OCR/SAPI/WinRT/natural voice worker/UI Automation/原生框/F11 三次真实选区/主窗口启动自检成功；ZIP **1186 项完整读取通过**。
- **独立发布：** [win-region-instant-clean-20261112](https://github.com/vobichngan285-collab/-/releases/tag/win-region-instant-clean-20261112) （public prerelease，非草稿）。Windows x64 ZIP 直链：https://github.com/vobichngan285-collab/-/releases/download/win-region-instant-clean-20261112/BlueStarOCR_RegionInstantClean_Windows_x64.zip ；**130293625 bytes，SHA256 `f09523dd3565d41fd386d2f7c5607bf87c6ea1609dca7a59ec44c198e9497ddd`**。源码 ZIP：https://github.com/vobichngan285-collab/-/releases/download/win-region-instant-clean-20261112/BlueStarOCR_RegionInstantClean_Source.zip ，138249 bytes，SHA256 `6dfebde714399182b11bb621a932c5d2f31d78f6a6d84cdf01c6959943fc923f`。原作者 Luna 原始 DLL/源码和用户私有配置隔离不变。
- **真实游戏仍待验证：** 下载到新的目录，不覆盖旧版；在《七日杀》或用户实际游戏确认：F7 隐藏区域框→切到鼠标跟随→回区域后仍隐藏；进入区域首次有字的实际声音延迟；连续玩游戏是否还卡；F8 原全屏 OCR 和云曦/晓晓仍正常。**CI 不能证明实际游戏 FPS 或十几秒延迟已经消失**，不应声称已彻底修复。若有问题回退原始 [win-simple-visible-capture-20261111](https://github.com/vobichngan285-collab/-/releases/tag/win-simple-visible-capture-20261111) 的 ZIP。


## 追加｜2026-11-12 Windows GameTextReader：正式调用 LunaTranslator 原版 NativeUtils.dll 截图与 getresauto 调度（已构建／用户真机 CPU 待验收）

- **授权和背景：** 用户确认电脑 OCR 区域连续跟踪 CPU 占用明显高于其实际用过的 B 站开源工具，同为约 300ms，要求直接按 **HIllya51/LunaTranslator 官方源码**移植，而不是再次自己模拟，且明确批准开始。上一轮 `win-region-instant-clean-20261112` 因用户实测 OCR 漏读显著增加，被认定失败版本，严禁作为基线。使用此前用户认为识别正常的 `win-simple-visible-capture-20261111` 源码 commit `0954e8157e851587acd5130b472dbe2ef6d2ad71`，叠加已隔离验证的 F7 单行修复分支 `fix/windows-f7-border-only-20261112` commit `235ec1d016aeaa58413434f430ba34d7466d1ca6`，从此创建 **独立分支** `feat/windows-luna-original-native-region-20261112`，不覆盖任何旧代码、APK、ZIP 或 Release。
- **上游精确来源：** https://github.com/HIllya51/LunaTranslator ，固定 tag `v12.1.3.9` / upstream commit `84677faeaa1e61bd7dd00b820090e9d2fe6c5142`。官方 `LunaTranslator_x64.zip` 发布包 SHA256 `c0248288c12de19e9e1f953922355aaa123699820fce26e4e84329be2666d62f`。**原封不动复制官方 NativeUtils.dll**，由 `files/DLL64/NativeUtils.dll` 原字节复制到 GameTextReader 便携根目录，SHA256 **`0d1fed0e062a9cb0418214bca22da95f900c630c0378d0d4c2914ab22093d996`**。运行时 `game_reader/luna_native_region.py` 用 `ctypes.CDLL` + `CFUNCTYPE` 调用 **原版 C++ `GdiCropImage(NULL,x1,y1,x2,y2,cb,curr=1)`**；不再自行重写 C++ BitBlt 算法，且 `curr=1` **只读桌面可见图像**，不调用曾在《七日杀》出现跨菜单旧画面的游戏 HWND 视图。若原版返回空白/尺寸异常/加载失败，才恢复 11 月 11 日原来可用的 Pillow ImageGrab；图片处理完即释放局部内存。原版 `screenshot.cpp`、`bmpx.hpp`、`ocrtext.py`、`NativeUtils.py` 逐字节随包提供；**完整原作者 GPLv3 源码**随 EXE ZIP 打包，避免侵犯许可。
- **移植原版完成时间门槛：** 对照 `ocrtext.py` `rangemanger.getresauto` 的 `lastocrtime` 完成后定时判断，把我们固定区域 **完整 OCR** 的下一次触发条件调整为上一轮 OCR 结束起不少于 300ms（`region_strategy="period"` 仍服从用户原先保存的周期）；保留原先帧变化检测、`128×72` 缩略图判断、OCR 的去重和语言过滤、小模型和推理参数，**没有复用识别率下降的 11 月 12 日重构版**。同一 OCR 引擎仍有线程互斥锁。注意本次并非整套 Qt 主程序替换，而是 **调用上游未修改的原生库及移植 getresauto 的时间门槛**，Python 适配层仅负责 DLL 调用、BMP 解码和失败回退；不要声称原封不动复制完整 Luna UI/OCR 模块。
- **F7：** 保留从原版修补的切回固定区域不重置边框 `_region_border_visible`，未改快捷键或其他模式的既有功能。F8 全屏和鼠标跟随继续调用 11 月 11 日可见桌面截图方案，原 V1.2 PP-OCRv6 Small 及 Luna/WinRT/SAPI TTS 未改。
- **代码隔离：** 分支最终用于构建的 HEAD `155789273074c30cf90cb0b15f9f25130a64be6e`。相对 F7-only 基线仅新增 `game_reader/luna_native_region.py`、`tests/test_luna_original_native_region.py`，更新 `game_reader/app.py`（原版 DLL 调用及完成时间门槛）、`tests/test_fixed_region_tracking.py`（改为 mock 新原版截屏入口）和专用 Windows workflow；未改 `ocr_backend.py`、`fixed_region.py`、`win_screen.py`、`speech.py`、模型文件。老版分支和 Release 都保留。
- **测试结果：** GitHub Actions Windows runner [43063357637](https://github.com/vobichngan285-collab/-/actions/runs/43063357637) **completed / success；131 passed / 1 warning / 0 failed**，Windows EXE OCR Small、SAPI/WinRT/natural voice、UIA、框选3次、主窗口启动都通过。工作流真实加载原作者 NativeUtils.dll 并调用原版 C++ GdiCropImage，在 Windows runner 成功得到 128×96 图像。ZIP 完整读 **1191 项**通过；DLL SHA 和官方包 SHA 核对通过。注意 Windows runner 与真实游戏 GPU 渲染场景不等价。
- **新独立公开预发布：** [win-luna-original-native-region-20261112](https://github.com/vobichngan285-collab/-/releases/tag/win-luna-original-native-region-20261112)，非草稿 prerelease。Windows ZIP **130805164 bytes**，SHA256 `70872a626c5e9a81374e381669653ce9a4c7b2c180cc163f81fb2d114271da48`；浏览器直链 https://github.com/vobichngan285-collab/-/releases/download/win-luna-original-native-region-20261112/BlueStarOCR_LunaOriginalNative_Windows_x64.zip 。项目源码 ZIP **141431 bytes**，SHA256 `b1cfc827a35a9a83311d3eaff2da79ae8afb5f23df890d3b93c564704dc0d63e`，直链 https://github.com/vobichngan285-collab/-/releases/download/win-luna-original-native-region-20261112/BlueStarOCR_LunaOriginalNative_Source.zip 。用户私人 `config..json` 不打包、不公开。
- **真实游戏验收限制：** 用户必须在 Windows 11 的《七日杀》同一选区对照当前与昨日前版本的 CPU 占用、首次朗读、文字识别完整度、跨菜单画面新鲜度和 F7 保持；只有用户实测才能宣称明显降低 CPU 或解决卡顿。原生桌面 GDI 在部分 DirectX 独占全屏可能截不到内容，会回退 Pillow，可能没有 CPU 提升。尤其不能误将自动化 131 测试通过当作已实测游戏帧率。若出现明显漏识别，立刻切回 https://github.com/vobichngan285-collab/-/releases/tag/win-simple-visible-capture-20261111 。本轮未改安卓 Blue Star Guide。


## 追加｜2026-11-12 Windows 完整 LunaTranslator 原版 OCR 接管蓝星：Qt 实际联通验证通过／帧率待用户验收

- **用户明确授权：** 放弃先前 11 月 12 日部分截图 DLL 和部分 OCR 调度的拼接做法，要求将 B 站大佬 LunaTranslator 相关 **整套 OCR 运行逻辑与代码尽可能直接原版移植**，由蓝星原界面、快捷键和 TTS 承接文字/坐标，严禁助手自行重写识别算法。用户报告此前部分移植导致《七日杀》约 **100 FPS → 30–40 FPS**，且某实验版文字识别率明显下降；这是严重回归，旧失败版不可当作稳定基线。
- **保守起点与隔离：** 源码从 11 月 11 日用户认为识别正常的 `0954e8157e851587acd5130b472dbe2ef6d2ad71` + 独立 F7 边框保持修复 `235ec1d016aeaa58413434f430ba34d7466d1ca6` 出发。全新分支 `feat/windows-original-luna-ocr-bridge-20261112`，此次最终成功构建 HEAD **`a518a4bccc5804f5f3d2a4acb2c783ea79faa765`**。没有覆盖/合并旧 Windows 应用或 Android 项目。
- **完整上游原版固定：** [HIllya51/LunaTranslator](https://github.com/HIllya51/LunaTranslator) 固定 tag `v12.1.3.9`，上游源码 commit `84677faeaa1e61bd7dd00b820090e9d2fe6c5142`，原作者发行 `LunaTranslator_x64.zip` SHA256 `c0248288c12de19e9e1f953922355aaa123699820fce26e4e84329be2666d62f`。实际在 ZIP 中携带 **586 个原作者完整程序运行文件**，逐个 SHA256 对官方包核实 **全部字节一致**；还携带原作者 `git archive` 全部 **1485 个源码文件**（含 GPLv3 许可证）。**原版 NativeUtils、CVUtils、Qt、`ocrtext.py`、`imageCutEx()`、`ocr_run()`、官方 `det.onnx/rec.onnx`、MS-SSIM、原版文本后处理及线程调度均不改。**
- **两段接入但不重新做 OCR：** 原作者完整版作为 **独立本机进程**位于绿色包 `GameTextReader/LunaOriginal/LunaTranslator_x64/`；仅额外添加 `LunaTranslator/textio/textoutput/bluestar.py` 进程间通信插件，走原版 `BASEOBJECT.startoutputer` 机制，把原文通过本机 `127.0.0.1:29381` 发往蓝星；本机 `127.0.0.1:29380` 接收操作指令，在原作者 GUI Qt 线程上调用其 **原版** `ocrtext.clearrange/newrangeadjustor/setrect/showhiderangeui/pause_recognition/resume_recognition`、`imageCutEx()`、`ocr_run()`，从原版 `OCRResultParsed.json` 获得文本及四角坐标。蓝星 `game_reader/luna_original_bridge.py` 仅启动原程序、IPC 与文本框坐标转换；`game_reader/app.py` F8、F11、悬停和原版连续区域路径改用原版 OCR：**蓝星区域模式不再启动自身截图/128×72 变化识别/自写 OCR 推理调度**。蓝星保留 F7 隐藏边框、模式切换、鼠标指向朗读、过滤、用户原本微软语音和无障碍。旧 `ocr_backend.py`／模型文件仍作为独立老版自检与回退遗留，但生产 OCR 路径未调用，并不代表两套 OCR 同时执行。
- **新建独立全原版参考包：** 分支 `exp/windows-luna-complete-original-20261112` 打包 **原封不动完整作者 x64 runtime + 全部原版源码** 的独立基准 ZIP（不是蓝星整合版），GitHub release `win-luna-complete-original-experiment-20261112`：https://github.com/vobichngan285-collab/-/releases/download/win-luna-complete-original-experiment-20261112/BlueStar_Luna_CompleteOriginal_OCR_Experiment.zip ，SHA256 `d338a826784746876c006dd93b9788199be293b2b800541b6bf99f6814a37828`，73,261,468 bytes。该基准包原作者 586 个运行文件逐个校验通过、源文件 1485 个完整，原作者程序真正可运行。
- **重要真实故障及最终修复：** 首次蓝星整合构建虽然跑通 **131 测试 + 原版进程 ping**，正式在 Windows runner 操作 `pause/region` 时却发生 **`TimeoutError: Luna original Qt UI did not answer`**。重复等待 14s+3 次操作仍失败，说明仅 ping 的绿灯不充分；旧预发布 `win-full-original-luna-integrated-20261112` 因此被认定**真实区域控制不可用，明确要求用户不要使用**，不能作为新版本。查明 Qt 接入 QObject 的跨线程槽注册问题：改为来自 PyQt5/6 的 **`@pyqtSlot(object)` 原生槽**，将 Qt Dispatcher 移入原版 QApplication GUI 线程之后再以 `QueuedConnection` 连接；这是 IPC 适配器层修复，**没有重写原作者 OCR 任一模块**。更改了 Windows workflow，要求直接在真实 Windows Qt GUI 上逐项调用 `pause → region → border → clear → OCR` 全部成功才允许发布，防止再次出现只测 ping 的伪成功。
- **最终确认成功：** [GitHub Windows Actions #43076172749](https://github.com/vobichngan285-collab/-/actions/runs/43076172749) **completed/success**；**131 passed、1 warning、0 failed**；精确原版 586 个 runtime SHA256 全通过；Qt GUI 原版接口实际调用 `pause`、`region`、`border`、`clear` 均 **PASS**；`imageCutEx + CVUtils ONNX` 实际在 Windows runner 通过 IPC 识别出 **1 个 OCR 条目**，而不是只建立进程 ping；旧 F8 OCR 自检、语音 SAPI/WinRT/natural voice worker、UIA/native 框和 Tk 拖动3次、Frozen APP 启动都过；最终 ZIP **1922 项全部压缩数据可读取**。不能把 CI 当作《七日杀》GPU 游戏帧率实测，也不能保证文本准确度匹配旧 PP-OCRv6 Small。
- **最终新隔离公开预发布（仅使用这个整合版）：** `win-full-original-luna-qtfix-20261112` [发布页](https://github.com/vobichngan285-collab/-/releases/tag/win-full-original-luna-qtfix-20261112)；Windows 11 x64 无安装 ZIP [BlueStarOCR_LunaFullOriginalQtFix_Windows_x64.zip](https://github.com/vobichngan285-collab/-/releases/download/win-full-original-luna-qtfix-20261112/BlueStarOCR_LunaFullOriginalQtFix_Windows_x64.zip)；**205,048,787 bytes**，SHA256 **`e99a52a69ee0cf079a5a7be58946df99a0af62933c6d548ffcf2b24475ff31a6`**。配套项目源码 ZIP https://github.com/vobichngan285-collab/-/releases/download/win-full-original-luna-qtfix-20261112/BlueStarOCR_LunaFullOriginalQtFix_Source.zip ，**156,522 bytes**，SHA256 `00eb92b5ee1e9147605c386ddab86d999b850fbc6a4e1431b107bbe105dc028e`。旧版全部原样保留；用户应独立目录解压并运行 `GameTextReader/GameTextReader.exe`，出现原版 LunaTranslator 窗口需保持运行、按原版设置模型/推理设备、用 F9 进入区域模式 F11 选区，避免同时启动其他旧版扫描。回退旧稳定原版 https://github.com/vobichngan285-collab/-/releases/tag/win-simple-visible-capture-20261111 ，保留 F7 的旧原版 https://github.com/vobichngan285-collab/-/releases/tag/win-f7-border-only-20261112 。
- **最重要的限制 / 下一步：** 只有用户真实在 Windows 11 《七日杀》**相同游戏画面**实测可判断 FPS 从原 100 到现在多少、CPU 占用、OCR 漏读率和 F7 显示。之前失败版本 30–40 FPS 是实际反馈，不能声称本次已解决。若 FPS 再暴跌，立刻退出新版（确保原版 Luna 子进程不遗留）并退回 11 月 11 日正常版。未经用户下一步指令不得基于本版再次大改或覆盖历史文件。


## 追加｜2026-11-12 Windows 原版 Luna OCR：300ms 周期、隐藏原版粉色 HUD／重复区域框，单独实验版

- **用户真机反馈（图片及文字）：** 整合 `win-full-original-luna-qtfix-20261112` 在《七日杀》能朗读，但 CPU 负担仍大；屏幕出现 LunaTranslator **粉色悬浮翻译工具栏及译文条**，和游戏字幕重复。用户批准马上按方案调整。核查原本 build workflow 的 `$defaults['ocr_auto_method_v2']='analysis'`，而 Luna v12.1.3.9 上游 `ocrtext.gettextthread` 自动扫描每循环 `time.sleep(0.1)`；`getresauto` 在其分析模式每轮截图 + MSSIM，导致即使此前宣传 300ms，其模式也不是 **按 OCR 完成时间判定的周期模式**。不再继续乱动原作者 OCR 算法。
- **独立分支：** `fix/windows-luna-hidden-300ms-20261112`，严格从原版整体移植版已测试成功 commit `a518a4bccc5804f5f3d2a4acb2c783ea79faa765` 创建，**没有改动或覆盖任何旧 release**。可发布应用代码+workflow commit `ca667e74fbb6d1fdb69fc61c4410b913daec9f51`；随后额外增加一项测试 commit `08861f6fc4f7d1f1f024086ad3a3c25435188112`，**功能代码与已发布 binary 未发生变动**。
- **精确改动仅限接入层：** `experiments/luna_original_full/bluestar_outputer.py` 使用原作者 Qt UI 的 `translation_ui.hide_()` 隐藏 pink toolbar/text 界面；在调用原作者原版 `ocrtext.clearrange/newrangeadjustor/setrect` 后，原作者自身区域框调用 `source.showhiderangeui(False)` 隐藏，但 `ocrtext.ranges` 保持 **1 个有效扫描区域**，蓝星 F7 控制的**唯一绿色边框**原样工作；F7 的 `request_border` 即使请求显示也不重新显示原版多余边框。适配器增加只读 `status` 本机命令返回 Luna 原版实时策略、间隔、原窗口可见性、范围框可见性和数量，供测试验证。
- **构建隔离配置：** `$defaults['startupautohide']=$true`（原作者 `LunaTranslator.py` 存在官方判断）、`showintab=false`、`ocr_translation_overlay=false`、`ocr_auto_method_v2='period'`、`ocr_interval=0.3`。**原作者完整 586 个运行文件、OCR 图像捕获、C++/Qt、ONNX、MSSIM、线程模型等均未修改**，仍带 GPLv3 原版全部 1485 个源码文件。绝不冒称 300ms 是截图周期：源码 `ocrtext.gettextthread` **每次完整 OCR 循环完休眠 100ms**，`getresauto` 会先截图再做 0.3s 完整 OCR 门槛检查。因此性能改善是待验证的目标，绝非已经确认。
- **双并发构建状态：** 首次成功 GitHub Actions Windows [#43082564906](https://github.com/vobichngan285-collab/-/actions/runs/43082564906) **completed/success**，130 passed、1 skipped、1 warning、0 failed；原版真实 GUI+IPC 在 Windows Runner 返回 `{'strategy':'period','interval_s':0.3,'main_window_hidden':True,'source':'ocrtext',...}`，设选区后 `original_region_count=1, original_regions_hidden=True`；原版暂停/设区/隐藏重复边框/清空均过，隐藏 UI 后原版截图+ONNX OCR 返回 **1 个 OCR 条目**。586 原版 DLL/runtime 逐文件 SHA 校验通过，205MB 压缩包共 1922 文件完整读取过。第二次并发构建 [#43082629574](https://github.com/vobichngan285-collab/-/actions/runs/43082629574) **132 passed, 1 warning**，真实 Qt/OCR 等步骤通过，**只有最后的重复发布步骤失败**，原因 GitHub 明确报 `a release with the same tag name already exists`；不要把它误认为 OCR 构建/测试失败。两次功能代码一致，第二次只多了静态测试。
- **已发布独立实验 ZIP（只用此版）：** [win-luna-300ms-hidden-ui-20261112](https://github.com/vobichngan285-collab/-/releases/tag/win-luna-300ms-hidden-ui-20261112)。Windows x64 ZIP [BlueStarOCR_Luna300msHiddenUI_Windows_x64.zip](https://github.com/vobichngan285-collab/-/releases/download/win-luna-300ms-hidden-ui-20261112/BlueStarOCR_Luna300msHiddenUI_Windows_x64.zip)，**205047834 bytes**，官方发布文件 SHA256 `3e4bd6bf525202871e5790d0ccb5bcfdf5c328e152df6f9c54f7ec8a6a5918bf`；源码 ZIP `BlueStarOCR_Luna300msHiddenUI_Source.zip`，**157652 bytes**，SHA256 `e834954771695925e14dca9d0021a3e91631cdb98fb4b8112f107260959bd88e`。必须独立文件夹解压，不覆盖之前工作版本；用户关闭所有旧版本及其 Luna 子进程后只启动新版 `GameTextReader/GameTextReader.exe`，用 F9/F11/F7 测，在相同游戏选区观察 CPU、FPS、首次朗读、字幕变化、跨菜单正常。可回退 11 月 11 日 [原正常版](https://github.com/vobichngan285-collab/-/releases/tag/win-simple-visible-capture-20261111)。
- **下一步需用户真机确认：** 是否不再看到原作者粉色主界面、F7 蓝星区域框是否正常、识别漏字是否增加、开启跟踪后的 FPS/CPU 是否改善。隐藏 UI 并不保证 GPU/GDI 截图不阻塞游戏；如仍严重掉帧，应独立测量截图开销，不要再为减少 CPU 无依据地切换或重写原作者模型。未动安卓 Blue Star Guide。


## 追加｜2026-11-12 Windows Luna 原版 OCR：按用户实际配置 PP-OCRv6_small / 4 线程 / GPU=true / 400ms 实验

- **用户指令：** 上传其原作者 LunaTranslator 的 `config..json` 和 `ocrsetting..json`，批准开始重新按其实际低占用配置构建，而不是由助手猜测参数。只提取公开无敏感的 OCR 五字段和扫描/去重设置；绝不提交用户完整 JSON、私人密钥、许可证或 TTS 声音安装路径。
- **用户实际已核实配置：** `ocrsetting.local.args={model:"PP-OCRv6_small",thread:4,gpu:true,luid:0,device_type:"CPU"}`；`config.json` 的 `ocr_auto_method_v2="period"`、`ocr_interval=0.4` 秒、`multiregion=true`、`ocr_text_diff=5`。**GPU=true 是用户请求，不代表实际硬件 DML 推理成功；device_type="CPU" 与 gpu=true 同时存在是原作者程序允许的设置，不能擅改。** 官方 Luna v12.1.3.9 完整包仅自带 PP-OCRv5_mobile，与用户 PP-OCRv6_small 不同。官方指南明确 v6 small 需另行下载，大小约25.2MB；仅复制模型名称可能静默回退 v5。
- **安全分支：** `fix/windows-luna-user-v6small-gpu-400ms-20261112` 基于上个成功构建隐藏粉色窗口实验版 `fix/windows-luna-hidden-300ms-20261112` 的 commit `08861f6fc4f7d1f1f024086ad3a3c25435188112` 新建，**不覆盖任何旧分支/Release**。当前 HEAD `2260fc94b66f1504eb8a652184527c607399ea6d`。与基线对比新增 `experiments/luna_original_full/install_official_v6small.py`（仅负责取原版模型安装 ZIP，不包含新 OCR 算法），调整 `.github/workflows/build-windows-luna-original.yml`（官方 v6 Small 模型及原始 OCR 配置、400ms、构建/真启动检查、独立命名），适配层 `bluestar_outputer.py` 添加只读运行配置诊断（含 DML provider 是否可用），及一个测试文件；**没修改官方 Luna OCR、CVUtils、NativeUtils、截图、调度算法及主应用 OCR 链路**。
- **原版模型一致性（必须核验才能发布）：** 构建脚本通过原作者 `myutils/ocrengines/local.py` 采用的官方 `https://lunatranslator.org/Resource/ocr_models` manifest 读取 `PP-OCRv6_small` 元数据和下载 URL；下载原 ZIP，验证含配套 `det.onnx`、`rec.onnx`、`dict.txt`，带原作者 `info.json`，放在原版可扫描的 `cache/ocrmodel/bluestar_official_<sha>`。缺包、名字错误、ZIP 结构异常、内容不完整直接**失败，不发布**。未用 RapidOCR v6 的未知字典冒充原作者完整模型。用户机器开启 GPU 需保留其原有设置；CI Windows runner 不保证真实物理 GPU，应分别汇报 DML provider 是否可用，不得将 GPU 请求标志等同于已硬件加速。
- **保留隐藏界面：** `startupautohide=true`；原作者粉色翻译 HUD、原作者重复区域框隐藏，蓝星 F7 自己管理边框；仍采用原版 `period` 而不是重新实现算法；从 300ms 改为用户真实 400ms，用户 `multiregion=true` 与 `ocr_text_diff=5`。
- **构建验收：** 新分支 push 自动触发 GitHub Windows Actions [#43137641631](https://github.com/vobichngan285-collab/-/actions/runs/43137641631) 和更新测试版 [#43137664283](https://github.com/vobichngan285-collab/-/actions/runs/43137664283)，目前 **queued 未确认完成，不得声称生成了新版 ZIP 或提供猜测下载直链**。流程须运行完整测试、模型真实安装、原版 Qt loaded runtime 值校验和单次 OCR（机器无真实 DML GPU 时须明确不能认证 GPU）、压缩包和单独新 release `win-luna-user-v6small-gpu-400ms-20261112`。如 CI 失败，读 job logs 精确修复并独立版本处理，拒绝仅凭 tests passed 宣布性能成功。不要重复发布相同 tag 造成历史中的 422 并发错误。
- **下一步用户真机：** 即便成功构建，也仍须对照原版同样《七日杀》选区，分别观察 FPS、CPU、GPU，确认实际启用 DML 和识别率，不能保证 100 FPS 或最低 CPU。出现卡顿或识别率下降立即回退 11 月 11 日用户认可的 `win-simple-visible-capture-20261111`。


## 续记｜2026-11-12 用户真实 Luna PP-OCRv6 Small / GPU / 400ms 已构建、真实运行及 ZIP 交付；GitHub Release API 权限受限

- **已完成的确凿结果：** 原分支 `fix/windows-luna-user-v6small-gpu-400ms-20261112`，成功构建的功能源码 commit `3f8f576fc42439f0f3571f98c6506830ce059e7a`，GitHub Actions [#43138145108](https://github.com/vobichngan285-collab/-/actions/runs/43138145108)。Windows runner 检查通过：原作者上游官方 manifest `https://lunatranslator.org/Resource/ocr_models` 的 `PP-OCRv6_small` 模型 ZIP 下载成功（实链 `https://lunatranslator.org/r2/luna/ocr_models_v6/v6small.zip`，SHA256 `515b940376c7bfc4acc5221349528f446c83981dfda7e07d74aa099522327840`），装入官方 `cache/ocrmodel/bluestar_official_515b940376c7`，`det.onnx/rec.onnx/dict.txt/info.json` 全部核实。原版 LunaTranslator Qt 进程实时回读 `strategy=period,interval_s=0.4,model=PP-OCRv6_small,threads=4,gpu_requested=true,gpu_luid=0,device_type=CPU,dml_provider_available=true,multiregion=true,ocr_text_diff=5,main_window_hidden=true`；区框 1 个但原版 GUI 重复边框隐藏；`pause/region/border/clear` 全成功；**原版 OCR 用用户 GPU=true 配置实测识别返回 1 个条目**。注意 Windows runner dml_available 和 OCR 成功，不代表用户电脑 GPU 型号/实际负载/FPS 已认证。
- **完整 Windows 可执行绿色版已打包、存放：** Actions #43138145108 自检、UIA、鼠标框和 voice checks 通过，最终 `release/GameTextReader_FixedRegion_ThreeModes_Experimental_Windows_x64.zip` 实际 **231,615,519 bytes**，SHA256 **`2a585adcdfdf94b25a04c123a3fe5dcc0d520adddca2d320df307de3f9473795`**，1927 个文件项压缩流均成功读取。上传 GitHub Actions artifact **ID `13907684622`**，名称 `GameTextReader-FixedRegion-ThreeModes-Experimental`，页面 [#43138145108](https://github.com/vobichngan285-collab/-/actions/runs/43138145108)，expires 2026-12-12。此 artifact ZIP 被真实下载到当前对话文件容器，解出**内层单独安装包** `/mnt/data/BlueStarOCR_LunaV6SmallGPU400ms_Windows_x64.zip`，二次 SHA256 对照完全一致；程序 `GameTextReader/GameTextReader.exe` 和 `userconfig_bluestar/{config.json,ocrsetting.json}`、模型 det/rec/dict/info 均在 ZIP，实际解包读取复核 `0.4/period/multiregion=true/ocr_text_diff=5` 与用户 OCR `4/gpu=true/luid0/device_typeCPU` **全部一致**。当前回复通过 sandbox link 直接交付用户，不依赖 Release API。
- **必须区分两个 GitHub Actions 失败：** #43138145108 **仅最后 GH Release 发布失败**，原因 GitHub token 对仓库 `POST /releases` 返回 **403 Resource not accessible by integration**；OCR 测试、官方模型、完整 ZIP 和上传 Artifact 均成功。#43138283725 则是额外 CPU fallback 的 **CI 测试脚本字符串引号 SyntaxError**（不是上游模型或 Windows GUI 的错误），用户 gpu=true 的真实原版 OCR 已经成功。最新功能等效分支 `c4e5f46ed5640f2a5581b28a48557e9c93c0d76a` 修复测试字符串，并为无 Release 权限仓库新增**专用命名 Windows ZIP 和源码 ZIP 的 Actions artifacts**，自动发布 Release 失败不再误判有效构建失败；工作流 [#43138869829](https://github.com/vobichngan285-collab/-/actions/runs/43138869829) 截止记录时尚待运行完成。用户可以先用上面已核验的真实安装包。
- **未改变核心 OCR：** 这次只调整上游完整 Luna 的**安装模型及配置**、添加适配器只读状态诊断；不是再次重写自己的截图、模型和调度。旧版正式/实验 ZIP、上游所有原版文件、安卓蓝星向导全部保留。
- **用户真机未测：** 必须同一选区观察《七日杀》是否保持 FPS、CPU 是否较前版降低、GPU 利用率、OCR 准确率和首次朗读。6000 次断言/编译不会模拟游戏独占全屏渲染；**切勿许诺 100FPS**。如严重卡顿即回退 `win-simple-visible-capture-20261111`。GitHub Repo workflow 权限要由用户管理员启用 Actions Read and write permissions 才能让 `gh release create` 有机会成功，不能在现有 API 连接内绕过权限。


## 追加｜2026-11-12 Windows Luna 原版 OCR 精简：仅保留 OCR 功能和蓝星既有语音/无障碍，旧引擎已物理排除

- **本轮明确授权：** 用户要求“大刀阔斧精简”最新 GameTextReader，不用 LunaTranslator 原版的网页翻译、词典、Hook、Magpie、多余 TTS，只保留其**原版 OCR**截图/区域/调度/本地模型及蓝星自己的 F7/F8/F9/F11、鼠标朗读、云曦/晓晓等用户功能。用户未经同意不得覆盖早期任何工作版本。
- **独立分支：** `refactor/windows-luna-ocr-only-slim-20261112` 从用户 CPU 改善的 `fix/windows-luna-user-v6small-gpu-400ms-20261112` HEAD `c4e5f46ed5640f2a5581b28a48557e9c93c0d76a` 分离，原版上游仍固定 HIllya51/LunaTranslator `v12.1.3.9`。
- **第一阶段真正在 Windows 上完成并可测试：** [Actions #43146112683](https://github.com/vobichngan285-collab/-/actions/runs/43146112683) **completed/success**，功能代码 commit `a24701d4cbddfd5991c1f5fc457b9848d6ba57f1`；从 BlueStar 生产应用删除旧 `main.py --self-test-ocr` 引用，PyInstaller **不再打包 RapidOCR/onnxruntime/OpenCV/NumPy/旧 DET/REC**；原有本地 RapidOCR 测试和源码仅作为历史保存在仓库独立 `requirements-legacy-tests.txt` 中，不进入 EXE。部署的 Luna 原版 `ocr_auto_method_v2=period`、400ms、PP-OCRv6_small、4线程、GPU true、LUID 0、device_type CPU 等用户实测配置**仍原样保留**。此外，原版 `fanyi`、`cishu`、`reader`、其他 OCR 引擎、text hook、元数据自动更新、所有后处理模块均在隔离 `userconfig_bluestar` 设为不启用，只有 `ocr.local` 和 `textoutputer.bluestar` 在用；但这个第一阶段包**没有物理删除原版 GUI/翻译源文件**，不可声称全部原作者非OCR文件已经去掉。GitHub Actions artifact ID `13911841559`，名称 `BlueStarOCR-Luna-OCR-ONLY-SLIM-Windows`，外层包内有内层 `BlueStarOCR_LunaOCROnly_Slim_Windows_x64.zip` 大小 **129138303 bytes** ≈**123 MiB**，SHA256 `738074e89b56d38e0deaceafc8fc469e57c62f8fc30e59f679592bc064cc7c82`；此前上一版 231615519 bytes ≈221 MiB，新包减少约 44%，`_internal` 无 rapidocr/onnxruntime/cv2/numpy/models。已从 GitHub artifact 下载、解包内层并二次验 SHA、验证 userconfig 和正式运行文件路径：`/mnt/data/BlueStarOCR_Stage1_LunaOCR_FrontendSlim_Windows_x64.zip`（仅当前会话的本地 artifact，不代表长期公开 URL）。保留完整原版 GPL 源文件 ZIP。
- **第二阶段进一步物理剔除的实验：** 在上述分支新增 `experiments/luna_original_full/prune_original_luna.py`，拟删除原版不使用的翻译 provider、词典、原版 TTS provider、其他 OCR backend、Magpie、LunaHook、旧 PP-OCRv5 模型、重复 GPL 源副本等；从 Windows CI stage 真删 **248 files / 45,603,456 raw bytes**，但首次实际原版 Qt OCR 进程在删除后**不能正常提供本机 IPC**，所以强制 BLOCK 发布。检查官方 `myutils.config.checkintegrity()` 发现它 **无条件要求存在 Magpie.Core.exe、LunaHook 和 LunaSubProcess 等非 OCR 文件**；精简脚本只调整原版 **非 OCR 启动校验**，保留 CVUtils、NativeUtils、onnxruntime、DirectML 等 OCR DLL 检查。后续检查仍阻塞启动，所以脚本另跳过原作者 `LunaTranslator.py` 的非 OCR 初始化方法（metadata/translator/dictionaries/original TTS/LLM service/update等），**原作者核心 `ocrtext.py`、`ocrengines/local.py`、CVUtils/NativeUtils/Qt OCR 区域管理全部不改**。原作者完整 GPL 源码仍随包提供；精简改动脚本在 GitHub 保留便于审计。第二阶段最终源码 commit `0ecdbfc56487f56f00bf35cdba9a537cfbff2437`，待验证 [Actions #43148397909](https://github.com/vobichngan285-collab/-/actions/runs/43148397909) 在记录时为 **queued**；**不能声称已经构建成功或发布完整物理删减版**。
- **严格测试要求：** CI 不得仅看源码/模型名；必须真实启动裁剪后的原版 Luna Qt process，经 127.0.0.1 本机接口验证 `status`、`pause`、`region`、`border`、`ocr` 和 `clear`，并检查没有旧 OCR 重复打包。只要 Windows 原版截图/识别失败就拒绝发布。不能为减体积删除可访问性 UI、用户原来微软自然语音/本地授权文件加载、原版 PP-OCRv6_small、GPU 配置或旧工作版 GitHub 记录。用户此前反馈 CPU 已接近 B 站原版但识别漏字；本次精简**不修复原版 OCR 行坐标丢失/画面遮挡问题**，需后续独立核查，绝不声称精简等于识别率改善。
