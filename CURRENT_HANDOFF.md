# Windows 游戏文字助手｜当前交接（2026-11-09 · V2.0 原版 Luna）

**当前仅重点开发 Windows 11 游戏 OCR + 鼠标指向文字朗读；安卓「蓝星向导」暂时搁置，旧安卓离线 OCR/CRAFT 已放弃。** 本仓库 https://github.com/vobichngan285-collab/- 。新对话先读本文件即可，历史在 `RELEASE_STATUS.md`，不必重复旧实验。

## 最新：V2.0 原版 LunaTranslator 语音引擎和原始配置（2026-11-09）

- **用户最终明确要求：** 不再写自己的自然语音 SDK 适配器；必须直接采用 B 站作者开源 LunaTranslator 原版引擎且不修改其代码，用户上传的 `config..json` 也**逐字节保持原样**。只允许重写 GameTextReader 与原引擎之间的接口。保留原 Small OCR、F8、鼠标指向朗读。尽量云端验证，用户不愿反复测试无效包。
- **Windows 实际成果：** 实验分支 `exp/luna-verbatim-upstream-20261109` HEAD `aff85bb6f0877b125a074eb38321ce97c265c626`，Actions [42616893234](https://github.com/vobichngan285-collab/-/actions/runs/42616893234) **completed/success**，38项源码单元测试、冻结 EXE、Small OCR、语音 worker、原引擎哈希、GPT 工具链及无障碍等通过，30个步骤成功。
- **原作者文件原封不动：** 官方 `HIllya51/LunaTranslator` 版本 `v12.1.3.9`，原发布 ZIP SHA256 `c0248288c12de19e9e1f953922355aaa123699820fce26e4e84329be2666d62f`；从其 `files/LunaSubprocess64.exe` 获取**原版 EXE 不重编译不打补丁**，398144字节，SHA256 `886892cd78cdd8bbd029a3f4977853cc1ddce1c9723e656986fa8b5a79e6a974`。源码对应官方 tag commit `84677faeaa1e61bd7dd00b820090e9d2fe6c5142`，源文件 `windowstts.py`、`LunaSubProcess.py`、`basettsclass.py`、`msnaturalvoice.cpp`、`pipehost.hpp`、GPLv3 LICENSE 均从官方同版本复制后逐文件哈希核验；完整官方源码 ZIP 随程序提供。
- **唯一必要的新代码：** `game_reader/upstream_luna_pipe.py` 通过原生 Win32 named pipe、event 和 32MB shared map 调用作者**未修改**的 `LunaSubprocess64.exe msnaturalvoice <pipe> <event> <map> <path> <sdk dir> <exact Voice.License>`；`game_reader/luna_voice_worker.py` 不再调用自己写的 Embedded SDK（该实现已从 `luna_natural_voice.py` 删除），而是仅读取原 JSON、按原作者 SSML 公式发给原 exe，拿 WAV 回 GameTextReader 播放。GUI 在 EXE 同目录有 `config..json` 时优先选原版 Luna 音色，不会退回旧设置。无权限错误不冒称成功。
- **交付公开与私有的区别：** 不包含用户配置的可公开 GitHub CI 文件：[GameTextReader V2.0 artifact 13672424251](https://github.com/vobichngan285-collab/-/actions/runs/42616893234/artifacts/13672424251)，内层 `GameTextReader_V2.0_OriginalUnmodifiedLuna_Windows_x64_Portable.zip`。**用户原始 `config..json` 没有公开上传到 GitHub**；此次在 ChatGPT 容器内将上传的原字节加入已成功构建的 ZIP 并独立校验。用户私人整合 ZIP `GameTextReader_V2.0_Original_Luna_Exact_Config_Windows_x64.zip`，130403883字节，SHA256 `e4cb1330738a79c3064b69fd1532d88da5d3005617c71b84a542a3f70c880cf6`，ZIP CRC通过，1200文件条目；原 Config 字节不变、上游执行文件哈希不变，仅有2个 Small ONNX，用户可以在本次会话沙盒下载，不要把此私人 ZIP 上传公共仓库。
- **不可夸大：** GitHub Windows 2025 没有云希、晓晓模型，所以**目标自然语音尚未真实出声验收**；CI 证明原执行文件、IPC 命令和原始配置连接就绪，不证明微软模型适用授权或扬声器实际出声。上游 GPLv3 分发须保留完整源码，微软模型独立使用遵守其自身许可。不要重新用 SAPI、WinRT、广荣替代原引擎。
- **旧 V1.8 和 V1.9 未覆盖。** V2.0 在独立实验分支；后续如用户报告错误，按作者原代码/调用接口排查，先证实 WindowsApps 包存在、运行时组件与本地进程状态，不得更改用户配置内容。

## 当前完成版本

- **V1.8 Small 单模型 + 保益语音调查 V2：** GitHub 实验分支 `feat/windows-v18-small-only-baoyi-voice-probe-20261109`；构建源码 HEAD `ea6988ac0e8fa45340e9bed62098f05350d0e19d`；GitHub Actions [42595587940](https://github.com/vobichngan285-collab/-/actions/runs/42595587940)，**第二次运行 completed/success**，28个CI步骤成功（第一次运行未执行，任务被取消）。
- **Windows 游戏助手下载：** [V1.8 Small + TTSProbe 产物](https://github.com/vobichngan285-collab/-/actions/runs/42595587940/artifacts/13667257789)。GitHub Actions 外层ZIP内含 `GameTextReader_V1.8_Small_TTSProbe_Windows_x64_Portable.zip`，126,636,816字节、SHA256 `0aa81272efc8a82fe63ab2eb7529b98995fd483116c3011aa65a8bb46d53cc38`。已真实下载，内外ZIP CRC通过，包含 `GameTextReader.exe`、`GuangrongHost.exe`、`BaoYiVoiceInspector_V2.exe`，OCR权重恰好只有 Small DET/REC 两个。
- **独立只读语音调查工具下载：** [BaoYiVoiceInspector V2](https://github.com/vobichngan285-collab/-/actions/runs/42595587940/artifacts/13667013340)。内层 `BaoYiVoiceInspector_V2_ReadOnly.zip`，14,150字节、SHA256 `b0c8589469705e93aa88a916c631609029742bc9c9dcf83831ee13166e6057fe`，内外 ZIP CRC 通过，内含 EXE+README。该工具也已包含在 V1.8 主包中，**用户无需重复下载两次**。Actions artifact 可能约 30 天过期，GitHub 下载通常需登录。
- **OCR 最新决定：** 用户的真实 V1.7 Medium 日志记录 48 行耗时约34.3秒、79行约53.6秒，单次 Medium REC 约占推理98%；确定不再继续优化此模型。V1.8 已删除 Medium 选项、调用和权重，只保留 PP-OCRv6 Small DET+REC；旧配置 `tier=medium` 自动迁移为 `small`。F8 单键自定义、鼠标指向朗读、绿色文字框、60秒过期、原系统SAPI/WinRT和广荣入口保持。
- **自动测试边界：** Windows 2025 CI 已通过 27项 Python 测试、官方 Small ONNX 的英文/中文合成图 OCR、冻结 EXE 启动、SAPI/WinRT 合成、模拟广荣宿主 IPC PCM、UIA、两个 Small 权重包检验、V2 进程调查模拟（模拟 BoySpeechSlave 进程、32/64位判断、过滤调查工具自身、路径脱敏）。CI没有真实保益音色，不能宣称云希/晓晓已经成功。
- **之前的下载和改动：** V1.7 实验在 `exp/windows-medium-latency-v17-20261109`，成功 Actions 42583872881；V1.6 旧版亦保留。不要覆盖原版本目录。

## 当前待查：独立微软广荣语音

- **用户真实保益悦听 12.10 只读 V1 报告（2026-11-09 16:53）**：安装在 `C:\Program Files (x86)\BoyPcReader\`，找到目录中的 `BoySpeechSlave.exe`、`BoyTTS.dll`，但没有发现明确广荣 DLL 的内存加载记录；扫描误把调查工具自身识别成保益窗口，遗漏语音辅助进程名字，未标明进程位数。
- **V2 修复调查盲点：** 显式监测 `BoySpeechSlave`、`BoyVoiceInput`、`BoyTTS.dll`，报告候选进程32/64位，排除调查工具自身；不联网、不发送语音、不注入、不改保益、不读取配置/许可证。让用户在保益正朗读云希/晓晓时点击 V2「开始只读扫描」，复制报告；按真实证据判断语音链路。
- **独立广荣现实状态：** 官方 `grtts_x64.dll` 在干净 Windows CI 加载返回 Windows ERROR1114；模拟 DLL PCM 成功不等于官方引擎或用户扬声器成功。V1.8 **没有修复**独立云希/晓晓发声。不要重做已失败无环境 DLL 试验、绕开许可证或冒称已修复。

## 2026-11-09 云端微软自然语音可行性实验（无需用户下载）

- 用户提供 LunaTranslator 的 `config..json`，包含 `reader.windowstts.voice=[1, "C:\\Program Files\\WindowsApps\\MicrosoftWindows.Voice.zh-CN.Yunxi..."]` 及微软 Speech/Voice 许可**声明文本**，并亲身验证另一软件可以用云希/晓晓。**不要复制整份用户配置、许可声明或密钥到 GitHub**，也不要把声明当作第三方 SDK 使用授权。
- 已核查官方 LunaTranslator [Python WindowsTTS 适配器](https://github.com/HIllya51/LunaTranslator/blob/main/src/LunaTranslator/tts/windowstts.py) 与 [C++ natural voice subprocess](https://github.com/HIllya51/LunaTranslator/blob/main/src/NativeImpl/LunaSubprocess/msnaturalvoice.cpp)：`voice[0]=1` 是其自然语音模式，通过微软 Embedded Speech SDK、模型路径、扩展运行时与模型授权参数，而非标准 SAPI/WinRT 和广荣 DLL。项目 GPLv3，研究架构不等于可无条件复制源码。
- **已真实执行 Windows 云端实验：** 分支 `exp/cloud-natural-voice-interface-20261109`，Commit `417585abb65b69627742daf8896ec34767abd241`，Windows 2025 Actions [42609120899](https://github.com/vobichngan285-collab/-/actions/runs/42609120899) **completed/success**，JSON 报告 artifact [13668444274](https://github.com/vobichngan285-collab/-/actions/runs/42609120899/artifacts/13668444274)。脚本 `tools/cloud_voice_feasibility.py`：真正合成并验证 SAPI WAV 170876 bytes/85415帧/22050Hz/456ms；真正合成并验证 WinRT WAV 流 115886 bytes/181ms。云端 SAPI David/Zira，WinRT David/Zira/Mark；自然语音云希/晓晓 Appx 包未安装、普通 WinRT 不枚举；Windows 嵌入式语音运行组件存在但未尝试未经授权的 Embedded SDK 模型加载。
- **结论边界：** 云端完成真实合法 Windows TTS 合成，证明程序调用路径可用；云端构建机不是用户 Windows 11，**没有安装云希/晓晓、没有相关模型合法授权**，无法声称这两种目标音色已合成或 V1.8 独立云希发声已修好。微软 Embedded Speech SDK 属受限访问（见官方 Microsoft Learn）；不应通过复制许可声明/提取系统密钥/绕过加密来部署。
- 用户明确不愿为每轮研究下载实验包。**后续尽量先做云端验证**，只有云端无法获得真实设备条件时才明确说明不可覆盖的差异；不用再给用户无意义的调查包。

## 2026-11-09 按 LunaTranslator 自然语音架构的云端实验

- 用户再次强调**直接按作者实际源码的实现路线研究，禁止无谓地换 SAPI/WinRT、要求每轮本地下载**。已核查原项目 [windowstts.py](https://github.com/HIllya51/LunaTranslator/blob/main/src/LunaTranslator/tts/windowstts.py)、[LunaSubProcess.py](https://github.com/HIllya51/LunaTranslator/blob/main/src/LunaTranslator/LunaSubProcess.py)、[msnaturalvoice.cpp](https://github.com/HIllya51/LunaTranslator/blob/main/src/NativeImpl/LunaSubprocess/msnaturalvoice.cpp)：发现 `MicrosoftWindows.Voice.*` 包、`Tokens.xml` 名称/许可版本、查找微软嵌入式运行组件，64位独立进程调用 `EmbeddedSpeechConfig::FromPath`/SSML，透过 IPC 返回 WAV。其原生 C++ 还包含硬编码默认模型密钥，另一条路径把 `MicrosoftWindows.Voice.License` 配置值作为模型密钥，**不能将内置或第三方未经授权密钥复制进 GameTextReader**。
- **直接按上述结构创建了实验实现，而不是普通语音接口替代品：** `exp/cloud-natural-voice-interface-20261109`；新增 `tools/luna_natural_architecture.py`（包发现、`Tokens.xml` 元数据、嵌入式 Runtime 定位、独立 Python 进程、微软 Embedded Speech SDK 受授权模型合成函数），独立 [Actions 42610010494](https://github.com/vobichngan285-collab/-/actions/runs/42610010494) Commit `9fd0ce8e987398bde1aab0cb98e29afc546a3f73` **completed/success**。云端安装了真实官方 `azure-cognitiveservices-speech-embedded` SDK，确认 `EmbeddedSpeechConfig` API 可导入；读取模拟 `Tokens.xml` 元数据、独立进程通信与无授权情况下拒绝合成测试成功。工件 [13669373825](https://github.com/vobichngan285-collab/-/actions/runs/42610010494/artifacts/13669373825)。
- **结果边界：** GitHub Windows CI 没有云希/晓晓 Appx 模型和合法 Embedded Speech 模型授权，所以**没有真实合成云希/晓晓音频**，不能宣称最终解决。该实验只在独立分支提交，**尚未合入 V1.8 游戏应用**，也没有打出无意义的用户测试包。官方 [Embedded Speech 文档](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/embedded-speech) 要求受限访问与已授权模型。下一步若有适用的合法模型及许可，可继续用该同构结构完成真实合成；不要要求用户重复下载与云端无本质差异的工具。

## 2026-11-09 V1.9 实验：原始 Luna 配置已实际接入游戏助手（重要新进展）

- **用户明确要求直接使用上传的 B站作者原始 \`config..json\`，不再反复改用 SAPI/WinRT、广荣 DLL。** 用户上传的是有效JSON（约55KB、91个顶层键），关键字段 \`reader.windowstts.voice=[1,"C:\\Program Files\\WindowsApps\\MicrosoftWindows.Voice.zh-CN.Yunxi.1_1.0.5.0_x64__cw5n1h2txyewy"]\`；\`MicrosoftWindows.Voice.License\` 与 \`MicrosoftWindows.Speech.License\` 各721字符，均从**用户上传的原文件**读取和核实。**这两段原始全文不曾提交 GitHub，也不得写进日志或分发包。**
- **真正做出的改动**位于新实验分支 \`exp/luna-original-config-embedded-tts-20261109\`（从已成功的 V1.8 分支起步，V1.8/旧包不覆盖），V1.9 GUI 支持导入原作者未修改的 \`config..json\` 或直接将文件放在EXE同目录；选中 \`luna:original\` 原配置自然语音，实际在独立进程读取用户原配置的 \`voice\` 包路径和 \`MicrosoftWindows.Voice.License\` **不截断、无空格或换行变更**，通过 \`EmbeddedSpeechConfig.from_path\` 与 \`PropertyId.SpeechServiceConnection_SynthModelKey\` 传给正版微软 Embedded Speech SDK，采用与 LunaTranslator 一致的 SSML，合成 WAV 才用 winsound 播放。源码：\`game_reader/luna_natural_voice.py\`、\`luna_voice_worker.py\`、\`luna_bridge.py\`，并修改 \`speech.py\`、\`app.py\`、\`main.py\`。没有在源码或安装包中嵌入作者默认的模型key、用户原始许可文本或语音模型。
- **Windows 真云端构建成功**：Actions [42612283597](https://github.com/vobichngan285-collab/-/actions/runs/42612283597) **completed/success**，构建 Commit \`a23bbfe03d85747cfbbe10ffeb8a2439e6cf5c7f\`。34项Python单元测试通过，重点测试**从原样 JSON 中提取模型路径与许可字符串、原样传入模拟 SDK 相同属性**，以及本机 WAV/独立子进程/隐私、V1.8 Small OCR、Windows 打包冻结 EXE 及 GUI 启动等。冻结 EXE 的 \`--self-test-luna\` 通过：真官方 SDK 可导入、模拟原始JSON的值原样送到属性、打包 EXE 的独立语音子进程会响应，**但因缺真实云希模型而没有生成目标自然语音 WAV**。
- **下载仅作为可选交付，不要求用户反复试验**：[V1.9 实验包 artifact 13671406354](https://github.com/vobichngan285-collab/-/actions/runs/42612283597/artifacts/13671406354)；内层 \`GameTextReader_V1.9_Luna_OriginalConfig_Windows_x64_Experimental.zip\` 大小138982217字节，SHA256 \`ddda7226833ac3c2b6fdc84b22393388370ff3daba98b5d624d1dba551269b40\`；下载后人工验证外/内两层ZIP CRC均完好，包含 GameTextReader.exe、Luna README、官方 Embedded SDK的9个 DLL、Small DET和REC恰好两个ONNX，**不含用户 config..json 或 Windows 自然语音模型**。
- **额外真实官方 SDK 属性测试**：Actions [42612988482](https://github.com/vobichngan285-collab/-/actions/runs/42612988482)，实验脚本 \`tools/cloud_luna_sdk_real_property.py\` 使用**实际的** \`azure-cognitiveservices-speech-embedded\` SDK、伪造模型目录及测试字符串，\`SynthModelKey\` 属性成功设置并读回同一值，\`actual_embedded_property_set=true\`，不使用用户许可字段、不生成云希真实 WAV。
- **最关键的边界**：没有证据云端干净机器安装了云希/晓晓模型；用户原始许可文字被原样读取并连到正确接口，不等于微软SDK在用户电脑肯定接受或授权该模型。V1.9 是“真正使用原配置的可执行实验版”，但**云希/晓晓真实发声尚未确认**。不要把此前虚拟模型+假的sdk测试称为真的自然音色合成。不要绕过微软模型许可证或复制原作者程序中的默认密钥。

## 下一步

- 用户把 V1.8 ZIP 解压到新目录，确认 Small F8 识别与原声音回归正常；重点运行 `BaoYiVoiceInspector_V2.exe` 并把复制的只读报告发来。不要把工具的「查到文件名」误当成「成功合成」。
- 修改前读取当前分支 HEAD/Actions/交接；未经授权不改、不构建。每次重要进展在此更新短交接、在 `main:RELEASE_STATUS.md` 追加历史并回读核实；不重建安卓项目。


## 2026-11-09 · 已讨论待开发需求 + V1.2→V1.3 OCR 回退排查（尚未实施）

**状态：用户只授权记录和只读核查；没有授权修改软件代码、GitHub Actions 构建或发布版本。V2.0 Luna 原版引擎 + 原始 config..json 尚未在用户 Windows 11 实际测试；云希／晓晓是否真实发声仍未验收，CI success 不能代表真实语音成功。**

### 下一轮鼠标 OCR 交互需求（讨论确认）
- **全屏截图 OCR** 与 **鼠标模式切换** 必须是**两个不同的自定义单键快捷键**，示例为 F8 和 F9；前者只重新截图识别全屏，后者每按一次就在“原有鼠标指向已识别文字框即朗读”和“新鼠标悬停识别指针附近游戏弹窗并朗读”两套互斥鼠标逻辑间循环切换。保留原有 OCR 模式与文字框。
- 悬停 OCR 仅需 **(a) 自行输入毫秒数的周期局部截图 OCR** 和 **(b) 另一个可自定义单键快捷键手动触发局部 OCR** 两种入口；不做画面变化检测。局部手动键与全屏键、模式键不得冲突。区域内弹窗不需要鼠标移到弹窗文本上就能自动朗读；相同文字防反复朗读、上一轮 OCR 未完成跳过本轮而非排队。这些最小防重复机制不额外增加复杂设置。
- 设置中的“选择鼠标 OCR 区域”参考 LunaTranslator：全屏变暗但仍可辨游戏，中央十字准星，按住拖拉矩形，松开确认、Esc 取消。保存区域宽高和相对于鼠标的偏移，**运行时区域跟着鼠标移动**而非固定在屏幕，自动限制到屏幕边缘。用户不想大量调参，可通过直观框选调整大小/位置。
- 这是**未来功能清单，不是现有 V2.0 已有功能**，不因此重写 PP-OCRv6、语音引擎或已完成的鼠标指向朗读。

### 用户新反馈：V1.2 默认 Small 识别最好，V1.3 起便开始漏读（重要校正）
- 用户明确：**V1.2 用的也是第一个默认 Small 模型，而非后来删除的 Medium**；V1.2 是实际最好，**V1.3 已经漏掉游戏屏幕左侧中间的图标/文字**，之后实验包继续漏字。不能再把这次回退归因于 Medium 被移除，也不能把 V1.4 才做的缩放更改说成 V1.3 漏检的根因。
- **只读代码比对分支**：V1.2 `game-text-reader-v12-20261109` HEAD `3f04365ab0ff8c31df9ad23d5a9ea869635f13f5`；V1.3 `game-text-reader-v13-audio-speed-20261109` HEAD `91ef787cc1aacd0820be7b113234dac6dc293c51`；V1.4 `game-text-reader-v14-20261109` HEAD `c4688a9c9215f95f9bcd35c2532cc53b5eb20f05`；V2.0 `exp/luna-verbatim-upstream-20261109` HEAD `aff85bb6f0877b125a074eb38321ce97c265c626`。
- **V1.2 → V1.3 的真正变化**：`game_reader/ocr_backend.py` 将模型懒加载改为启动后台预热+锁+按阶段计时，**Small DET/REC 型号、权重文件路径、RapidOCR 显式 OCR 参数、`use_cls=False`、解析 confidence 0.42 均未改变**；`np.asarray(image.convert('RGB'))` 改为 `np.asarray(image if RGB else convert('RGB'))`，逻辑颜色像素应保持一致；`game_reader/win_screen.py` 仍抓光标所在整个屏幕。V1.3 移除画面自动变化清理；应用从前台最小化后开始截图的延迟 **250ms → 100ms**（`capture_from_button`，只有软件窗口在前台需要先最小化的路径受影响），这可能影响截到的实际游戏画面，**但还没有真实图像和证据证实**。增加了日志、语音提示音事件/预热；原 `core.py` 和 `overlay.py` 字节哈希未变。
- **V1.4 后续独立变化**：V1.2/V1.3 使用 RapidOCR 默认 DET resize（`min/736`）；V1.4 起强制最长边 `max/1280`（某些 Medium 1152），V1.8/V2.0 沿用。它可能加剧游戏小字漏检，但**不可能解释 V1.3 就开始退步的时间线**。V1.8 删除 Medium 也不是 V1.2 默认 Small vs V1.3 Small 退步的解释。
- **目前只查出代码差异，未证明实际漏读因果**。优先保留 V1.2 作为准确率回归基准，下一轮若授权只用同一真实游戏截图做 V1.2 与 V1.3 Small 引擎、检测框数量和左中区域逐项 A/B，必要时区分“截图当时没抓到文字”“OCR 没检出框”“框有但鼠标命中/语音没读”；不得把 CI 简单英文图片 PASS 当真实游戏准确率验证，也不得为了提速降低文字检测质量。


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
