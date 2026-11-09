# Windows 游戏文字助手｜当前交接（2026-11-09 · V1.8）

**当前仅重点开发 Windows 11 游戏 OCR + 鼠标指向文字朗读；安卓「蓝星向导」暂时搁置，旧安卓离线 OCR/CRAFT 已放弃。** 本仓库 https://github.com/vobichngan285-collab/- 。新对话先读本文件即可，历史在 `RELEASE_STATUS.md`，不必重复旧实验。

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
