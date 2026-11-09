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

## 下一步

- 用户把 V1.8 ZIP 解压到新目录，确认 Small F8 识别与原声音回归正常；重点运行 `BaoYiVoiceInspector_V2.exe` 并把复制的只读报告发来。不要把工具的「查到文件名」误当成「成功合成」。
- 修改前读取当前分支 HEAD/Actions/交接；未经授权不改、不构建。每次重要进展在此更新短交接、在 `main:RELEASE_STATUS.md` 追加历史并回读核实；不重建安卓项目。
