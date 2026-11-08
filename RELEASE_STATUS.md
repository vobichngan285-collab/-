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
