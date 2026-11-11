# Windows 游戏文字助手｜当前交接（2026-11-10 · 区域跟踪实验版）

## 最新进展｜2026-11-10 Windows GameTextReader 最新版无法解压：原 EXE 无损双格式重新打包（已发布）

- **用户实际反馈：** 用户重新切回**电脑 Windows 11 截图 OCR + 鼠标指向朗读**工具，报告目前最新的**游戏 HWND 固定绑定版** ZIP 在用户电脑上“无法解压”，要求重新制作下载包。不可混同安卓 Blue Star Guide。原先 Release ZIP 源文件本身通过 CRC，所以原因**未定位**，不能凭此断言程序损坏；需要兼容 Windows 自带解压并提供备用格式。
- **不改代码与历史版本：** 保留原已 Windows 构建与测试通过的 EXE，固定编译源码 `44c19d3043d52d5d673b03f46f8e5e63b6e92d68`，源 Windows CI [42800465082](https://github.com/vobichngan285-collab/-/actions/runs/42800465082) **121 passed / 1 warning / 0 failed**。不修改 PP-OCRv6 Small、微软原 Luna 语音、F8、F11、F9 三模式、鼠标滚轮、HWND 绑定和 UI 无障碍，也不打包用户私人 `config..json`。源分支 `fix/windows-luna-bound-game-window-20261110` 和 Release `win-game-bound-20261110` 都不覆盖。
- **隔离打包分支：** `pack/windows-bound-zip-7z-recovery-20261110`，仅新增 `.github/workflows/repack-bound-extract-recovery.yml`，运行时**从原成功 Windows CI 下载已冻结原始 EXE artifact**（不是从 main 重新编译），校验原单层 ZIP 130294928 bytes、SHA256 `c819f19aac8e97cd52889d68a70b5e951ec37665227f2f45215f057dfa22c913`，1186文件、全部 ZIP CRC、原 exe/官方 Small 模型/原版 Luna 二进制与 GPL 源码完整，最长相对路径106字符且不含私密配置。首轮工作流 [42830848477](https://github.com/vobichngan285-collab/-/actions/runs/42830848477) 因 ubuntu-22.04 默认 Python 不支持 `hashlib.file_digest` 而失败，加入 Python 3.11后恢复，**不涉及产品 EXE 代码变动**。
- **双格式新包并逐字节验收：** 最新 GitHub Actions [42830988762](https://github.com/vobichngan285-collab/-/actions/runs/42830988762) **completed/success**，分支工作流 commit `a14d7ebd1d97d154336c5b68c2d5ea84757e3249`。新 Windows Explorer 内置可用 `ZIP_STORED` **不压缩 ZIP**，单层 `GameTextReader/` 文件夹，含简明说明，**282801938 bytes**，SHA256 `cfd2821b62fa9fe9e31f584effb3cff56804c5cf770314d3dda2959942d4e28b`。备用 **7z** `106024961 bytes`，SHA256 `311ea20cfa19ade8ae4af8870b783d74c592f39503b7e49e8a1b6de6be4da96f`，需 Windows 7-Zip。重新打包后**1187 个文件（含新增 README 解压说明）**，两种格式都成功完整解压，逐文件 SHA256 与原 EXE 源提取目录一致，所含官方 Luna GPL 源码不变。新压缩包对用户电脑是否能正常解压仍需真人测试，且网路下载中断会造成损坏。
- **公开新 Release：** https://github.com/vobichngan285-collab/-/releases/tag/win-game-bound-repack-zip7z-20261110 。ZIP 直链：https://github.com/vobichngan285-collab/-/releases/download/win-game-bound-repack-zip7z-20261110/BlueStarOCR_GameTextReader_Windows_ExtractFix_Store.zip 。7z 直链：https://github.com/vobichngan285-collab/-/releases/download/win-game-bound-repack-zip7z-20261110/BlueStarOCR_GameTextReader_Windows_ExtractFix_7Zip.7z 。另有 `SHA256SUMS.txt`。非草稿 public prerelease，三个资产均 uploaded。
- **用户安装指引：** **优先 ZIP** 用 Windows “全部解压”，建议解到短路径 `C:\BlueStarOCR\`，得到 `C:\BlueStarOCR\GameTextReader\GameTextReader.exe`。避免在压缩文件预览器里直接运行 EXE，避免覆盖旧版。若 ZIP 无法解压，再下载 7z 用 7-Zip 解压；若两种均报损坏先核对下载**实际文件大小和 SHA256**，排除下载不完整；用户不用重新填写 OCR 权重或其他新配置（私有语音配置信息不可置于公开包）。目前用户电脑是否能正常运行最新游戏菜单修复仍待实际测试。

## 最新进展｜2026-11-10 真实《七日杀》跨菜单朗读故障：固定游戏 HWND 修复实验版（已构建/发布）

- **用户发现的实际问题：** 新版在《七日杀》游戏首页「开始游戏/继续游戏/设置」可以 OCR 朗读，但点击「开始游戏」进入另一页面后，F8 有「叮」声、鼠标指向读不出当前页面文字。用户确认故障与滚轮无关，并指出游戏窗口自身未变；要求直接参照 LunaTranslator 的持久绑定游戏窗口思路，不重新设计 OCR/TTS。
- **原因与修复定位：** 上一版虽然参考了原版 `screenshot.cpp` 的 GDI/BitBlt，却缺少 `ocrtext.py` 中保存 `self.hwnd`、后续重复向 `imageCutEx(self.ref.hwnd, rect)` 提供同一窗口句柄的关键调用链；旧版仍每次捕获重新读取 GetForegroundWindow，并在前台 HWND 不同后立即清除旧 OCR。新增 `game_reader/game_window.py` 的 GameWindowBinding，首次在游戏里 OCR 时绑定外部游戏 HWND+PID；只要原 HWND 对应进程仍存在就不因为加载页/其他前台变化自动重绑；窗口关闭或 HWND 被回收时才释放与重新绑定。保留绑定窗口内不同子窗口同 PID 的活跃判断，失去游戏前台焦点时暂停鼠标朗读、保留已识别文字直至下次 OCR/TTL，而非直接清除。
- **接入范围：** `game_reader/app.py` 的 F8 全屏、F11 框选、鼠标跟随、固定区域连续识别统一传入同一绑定 HWND，实际像素每次重新截图而非缓存；`game_reader/win_screen.py` 截图函数新增可选固定 HWND；`game_reader/luna_capture.py` 沿用原 HWND 优先 GDI、失败回退 ImageGrab，并增加截图方式 `window_gdi` / `desktop` 纯元数据用于 F8 状态诊断。未改 Small OCR 权重、语音 DLL、原版微软云希/晓晓对接、滚轮键及三个模式的清除行为。
- **代码隔离：** 原 GitHub 仓库 https://github.com/vobichngan285-collab/-；新独立修复分支 `fix/windows-luna-bound-game-window-20261110`。**实际编译源码 HEAD `44c19d3043d52d5d673b03f46f8e5e63b6e92d68`**；发布脚本后续分支 Commit `08b5c97f164ce53187dceaa0fd5d243cb8fc72aa`，切勿混淆。上个版本分支不覆盖。
- **Windows CI：** [run 42800465082](https://github.com/vobichngan285-collab/-/actions/runs/42800465082) completed/success，**121 passed，1 warning，0 failed**；PyInstaller EXE 真正运行 Small OCR、语音 worker、UIA 无障碍控件、F11 三次真实 picker、应用自测等成功。之前 run 42800251220 因测试文件缺失 SimpleNamespace import，120 passed/1 failed，现已修复，不是产品故障。
- **GitHub 公开发布：** [run 42800815029](https://github.com/vobichngan285-collab/-/actions/runs/42800815029) completed/success；[Release win-game-bound-20261110](https://github.com/vobichngan285-collab/-/releases/tag/win-game-bound-20261110)，公开 prerelease、非草稿。Windows **单层** ZIP `BlueStarOCR_GameWindowBound_Windows_x64.zip`，130294928 bytes，SHA256 `c819f19aac8e97cd52889d68a70b5e951ec37665227f2f45215f057dfa22c913`，直接地址 https://github.com/vobichngan285-collab/-/releases/download/win-game-bound-20261110/BlueStarOCR_GameWindowBound_Windows_x64.zip；本项目源码 ZIP `BlueStarOCR_GameWindowBound_Source.zip` 130066 bytes，SHA256 `0fde30e7e76d112b16b5dcd0be92e22864321dde5c40d0afdbd4ba1c0297c186`，原版 Luna GPLv3 源码仍随便携包提供。ZIP CRC/EXE/源码检查通过，私人 `config..json` 不公开。
- **仍未解决/用户验收：** **不能保证《七日杀》切换页面后已经正常朗读，必须在用户 Windows 真机再试**；特别注意即使 HWND 固定，GDI 也可能在某些 DirectX/Vulkan 渲染场景返回旧帧，光标位置也可能来自游戏自绘鼠标而非系统坐标。新版 F8 诊断包含 `window_gdi` 或 `desktop`，若仍有叮声却读不到当前页面文字，下一步仅针对该截图来源问题排查，不重构已工作的语音/识别，不归咎滚轮。

## 最新进展｜2026-11-10 Windows 游戏窗口截图 + 鼠标滚轮智能清除 + 全屏计时（独立实验版构建与公开发布成功）

- **项目和隔离：** 唯一优先为 Windows 11 游戏 OCR（非安卓）。原仓库 https://github.com/vobichngan285-collab/- 。原固定区域实验版本和稳定版保留；本轮新独立分支 `feat/windows-game-capture-mouse-clear-speed-20261110`，目前发布工作流修复后的分支 HEAD `07f8e60aad103c9a0021f71fa2e47ea315a9bfdf`。**实际被 Windows runner 编译的应用源码 Commit 是 `31a92b90c43f15bfe0d817cd7d044a2344803ca4`**；后续为许可证说明和发布工作流，不能误认为另一个 EXE 编译版。
- **更新 1（鼠标）：** 新 `game_reader/mouse_input.py` 采用独立 WH_MOUSE_LL 消息线程处理滚轮方向增量，永远 CallNextHookEx 放行原鼠标滚动；鼠标中键、侧键与键盘仍使用现有 GetAsyncKeyState；快捷键绑定、名称、重复冲突检查共享原逻辑。新默认清除键为「滚轮向下」，旧 F6 默认配置升级；用户改过的其他按键原样保留。加入滚轮短时间重复抑制和细粒度 delta 累积。
- **更新 2（三模式智能清除）：** 默认模式删除旧 OCR 坐标、框、朗读；鼠标跟随模式清除后停止自动扫描，重新进入模式才恢复；固定区域模式清除 `fixed_region` 和 `fixed_monitor` 的记忆，停止扫描并使旧 job 失效、隐藏边框，需 F11 再框选。F7 只控制边框显示，不改变 OCR。区域跟踪依旧保留普通模式切换后的恢复能力，除非用户真的按清除快捷键删除。
- **更新 3（F8 诊断）：** 记录按键到 OCR 完成、截图、OCR 锁等待、图像预处理、模型推理阶段的毫秒数；避免已有 RGB 图像的重复 RGB 转换；主窗口触发的固定隐藏等待从 250ms 减少为 120ms（游戏内 F8 仍立即处理）。**没有把成功叮声提前到 OCR 完成之前**，没有调整 Small 识别模型权重，也没有声称真实提速百分比。
- **更新 4（大型游戏截图）：** 新 `game_reader/luna_capture.py` 参照原作者 HIllya51/LunaTranslator `v12.1.3.9` 的 `src/NativeImpl/NativeUtils/screenshot.cpp`：优先目标游戏 HWND 的 GetDC + BitBlt，坐标 ScreenToClient，对空白窗口截屏回退原桌面 ImageGrab；全屏、局部、框选快照和固定区域调用统一的截图接口。原版 LunaSubprocess64.exe 和所有语音适配未改动。新增 `LUNA_CAPTURE_NOTICE.md` 明确 GPLv3 来源；公共发布提供本项目源码 ZIP 和原 Luna 上游 GPL 源码包。
- **Windows CI：** [run 42787182157](https://github.com/vobichngan285-collab/-/actions/runs/42787182157) `completed/success`，**116 passed、1 warning、0 failed**；冻结 EXE、真实官方 Small ONNX OCR、原版 Luna worker、UI 自动化无障碍控件、F11 Tk 框选均通过。新测试覆盖滚轮高精度 delta、方向绑定和冲突、三模式智能清除、HWND 优先/桌面回退。
- **公开 Release：** [run 42787873992](https://github.com/vobichngan285-collab/-/actions/runs/42787873992) `completed/success`，发布 `win-gamecompat-mousewheel-vnext-20261110`，不是旧区域实验包。单层 Windows ZIP 130291497 bytes、SHA256 `c1214fc5c4f52efc936f74895e33532c3650fb1396b4132a3058a1300ca59055`；[直接下载](https://github.com/vobichngan285-collab/-/releases/download/win-gamecompat-mousewheel-vnext-20261110/BlueStarOCR_GameCompat_MouseWheel_Windows_x64.zip)。另外公开项目源码 ZIP 124186 bytes、SHA256 `dd48f6b752fa16bef96fe92bf931fa649503a217c40c3cb3f62a738c7495b806`。ZIP CRC 和内部 EXE/原 Luna 源码均验证过；私人 `config..json` 不公开也不修改。
- **边界与验收：** 这是**待用户真机测试的独立实验版**，不能宣称《荒野大镖客 2》/ Vulkan、DX12、独占全屏游戏已修复，也不能宣称鼠标滚轮钩子在所有游戏都能收到消息或云希/晓晓已听觉验收。Windows CI 无真实 3D 游戏、用户设备或微软语音授权。测试重点：F8 是否按键生效且截图来自游戏、文字框能否正确命中、滚轮是否既能清除又保留游戏滚动、模式清除后不自动重生、F8 阶段耗时。若问题复现，先取不含屏幕内容的阶段日志，不重写或替换原语音引擎。

## 最新进展｜2026-11-10 GitHub 公开 Release 直接下载补救（成功）

- **原因：** 用户反馈旧 Actions artifact 下载慢、无法解压；原 GitHub Actions 链接可能要求登录并多套一层 ZIP。不能据此断言用户本地 ZIP 实际损坏。
- **独立完整性复核：** 原外层 artifact `BlueStar-FixedRegion-Outer.zip` 为129838758字节，仅包含一个内层 ZIP，CRC 测试通过，SHA256 `de3a5f924806b5f9b9bc52cccab461078dad27ee266ed74adbb6e66719307477`；内层 `GameTextReader_FixedRegion_ThreeModes_Experimental_Windows_x64.zip` 为130279329字节，1194项 ZIP 内容 CRC 全部通过，SHA256 `e58d38a2c2948cda5c6a3d0472b6187e2d527b2c5d2ec3009b9d27e420182430`。原 EXE 未更改，不再重新构建。 
- **解决：** 在原实验分支上新增专用发布工作流 `.github/workflows/publish-region-experiment.yml`，commit `8b86a382e67cdd6cb69f31c6a37f79fe7bef7965`；使用已通过的 Windows CI artifact 解出内层 ZIP，运行 `sha256sum -c` 与 `unzip -t`，通过后用 GitHub Release 提供单层 ZIP 公开直链，不需要进入 Actions，也不需要双层解压。
- **Release 发布验证：** [run 42776413685](https://github.com/vobichngan285-collab/-/actions/runs/42776413685) `completed/success`；非 draft 的公开 prerelease [win-region-experiment-20261110](https://github.com/vobichngan285-collab/-/releases/tag/win-region-experiment-20261110)，Release asset id `730542023`，状态 `uploaded`，字节 `130279329`。
- **给用户的直接 ZIP 地址（不经 Actions 外层）：** https://github.com/vobichngan285-collab/-/releases/download/win-region-experiment-20261110/BlueStarOCR_RegionTracking_Windows_x64.zip 。用户网络经 GitHub CDN 仍可能慢，不能保证本地网络速度；提示放到浏览器下载或使用下载管理器。不要覆盖原有正常版本。
- 保持实验源码构建 Commit `a93e31e4b034df6e514bd5b314c05ee702378c16`、109 tests passed 与49 UIA 命名控件不变；私人 `config..json` 不公开。旧 artifact 和 Release 均保留，未覆盖旧包或修改安卓仓库。

## 最新进展｜2026-11-10 固定区域跟踪 OCR 第三模式实验版（Windows CI 已成功）

- **原仓库/基线/隔离：** `vobichngan285-collab/-`；从已通过的 V1.2.1 `997ade1552d097917b8a3121b963c4b45d6844fb` 新建 `exp/windows-fixed-region-tracking-20261110`。成功构建 Commit `a93e31e4b034df6e514bd5b314c05ee702378c16`。未覆盖 V1.2.1、未合入 main 应用代码，安卓 `kanzi-assistant` 未改。
- **用户确定交互已实现：** 同一模式单键（默认 F9）循环 `默认(pointer) → 鼠标跟随(hover) → 区域跟踪(region) → 默认`；区域模式 F11 暗屏左键自由拖框，松开立即按选定像素识别且开始持续跟踪；保存 `fixed_region` 绝对物理坐标与 `fixed_monitor` 原显示器边界，切走再回来自动恢复，启动程序仍默认进入普通模式，不会自行后台扫描。鼠标跟随旧 `region` 偏移独立保存，不被固定框覆盖。
- **识别策略：** `region_strategy=change` 默认每300ms仅低成本取样变化、变化时才运行 PP-OCRv6 Small；`period` 则用户手动设置 `region_period_ms` 100～60000ms，默认500ms，每次周期 OCR。每一模式同一时刻最多一个局部识别任务，三种截图共享 `_ocr_lock`；用 generation 和 job_id 丢弃模式切换/清除后的晚到结果。新文字行才朗读，重复行静音；文字消失后再出现可以重读。
- **边框：** 原生 Win32 四段点击穿透边框复用三个模式；颜色绿色/蓝色/黄色/红色/白色，粗细1～8像素；默认绿色3px。区域跟踪默认显示已框选的固定位置，可用可重绑定 F7 显示/隐藏，**仅改视觉、不触发 OCR、不打断 TTS**。F7 与原 F8/F9/F10/F11/F6 防冲突；离开区域跟踪自动隐藏，再进入按默认显示设置恢复。较粗边框使用额外外边距，确保始终在精确 OCR 截图像素外。
- **完整审核和修复：** 检查模式状态机、Windows 显示器变更/负坐标、F11 背景截图与框选恢复、OCR 单任务互斥、F6 后不把相同文字立即重新播报、旧结果丢弃、边框对截图污染、Windows UIA 焦点。首轮冻结包测试发现旧 F11 自测虚拟 App 缺少新状态字段，已修复；新增 F7 控件惰性查找，测试夹具可独立调用。最终不再有失败。
- **Windows Actions 最终证据：** [run 42762512266](https://github.com/vobichngan285-collab/-/actions/runs/42762512266) `completed/success`，**109 passed，1 warning，0 failed**；真实 Small 模型自测、冻结 EXE 启动、原版未修改 Luna 二进制与源码哈希、持续语音 worker、Win32 五种颜色原生边框、F11 picker 三次真 Tk 开关/拖选、原生 UIA `Strategy.PROVIDED` 和 **49 个命名控件**全部通过。
- **实验版工件：** [artifact 13737813672](https://github.com/vobichngan285-collab/-/actions/runs/42762512266/artifacts/13737813672)，名称 `GameTextReader-FixedRegion-ThreeModes-Experimental`，129838758 bytes，到期 `2026-12-10T05:31:57Z`。外层 GitHub Actions artifact 内含便携 `GameTextReader_FixedRegion_ThreeModes_Experimental_Windows_x64.zip`，这是 ZIP 便携 EXE，不是 MSI 安装器；解压独立新目录，不覆盖旧版。私人 `config..json`、微软模型/密钥不在公开包内。
- **真机待确认：** 游戏 《七日杀》持久跟踪实际文字变化准确率、CPU/游戏帧率、Windows 全屏截图区域与 F7 边框可见性、云希/晓晓真实播放。CI 不代表用户 PC 音频听觉和 FPS 验收。若游戏动态背景不断变化，可能频繁触发 change OCR；可切到可调周期模式降低负载。下一轮根据用户反馈定点修，不重做离线 Medium/安卓实验。

## 最新进展｜2026-11-10 V1.2.1 提示音、界面精简与鼠标语音提速（已构建）

- **主项目：** Windows Blue Star OCR 游戏文字朗读助手；安卓蓝星向导继续搁置。原仓库 `vobichngan285-collab/-`，未创建新仓库，未覆盖旧分支或旧安装包。
- **源码分支/实际构建 Commit：** `feat/windows-v121-cue-cleanui-voice-latency-20261110` / `997ade1552d097917b8a3121b963c4b45d6844fb`。从上版 `d5720f6924471200b3f2b68cc5a42a7c74f7c653` 延续。
- **用户授权修复：** 默认模式识别出过滤后可朗读文字时播放更清脆的成功叮声；从共用 winsound 改为专用 waveOut 异步后台播放，避免打断 Luna 音频；新增可读屏「试听叮声」和失败诊断；删除设置页多处重复小字说明、保留必要状态和 UIA。
- **语音低风险提速：** 鼠标跨文字区域时取消多余 stop 命令；不同短文字继续立即抢占；微软原版 Luna 不修改，增加仅 RAM 里 60 秒有效的 16 条/4MB 上限短文本合成 WAV 缓存，清除 OCR/过期会清缓存；重复短物品文字可重用音频。首次合成仍受微软引擎速度限制，尚无用户本机实测加速数据。
- **不改动：** PP-OCRv6 Small、F11 鼠标自由拖框与松手识别、F6 可自定义清除及 60 秒过期、原版 Luna 执行文件与语音配置、无障碍设置架构。不增加双击侧键（会延迟单击识别，用户明确取消）。
- **GitHub Windows CI：** [run 42754662061](https://github.com/vobichngan285-collab/-/actions/runs/42754662061) `completed/success`，**93 passed、1 warning、0 failed**；冻结 EXE、Small 模型实测、SAPI/WinRT、原版 Luna 版本/哈希、持久语音 worker、可点击穿透绿色框、3 次 F11 Tk 框选、完整应用启动、UIA Strategy.PROVIDED 与**38 个原生命名控件**全部通过。
- **下载：** [artifact 13735420785](https://github.com/vobichngan285-collab/-/actions/runs/42754662061/artifacts/13735420785)，名称 `GameTextReader-V1.2.1-Cue-CleanUI-FastVoice`，129822675 字节，2026-12-10T04:17:15Z 到期；ZIP 中为 `GameTextReader_V1.2.1_Cue_CleanUI_FastVoice_Windows_x64.zip`。仅官方公共依赖与模型，不附用户私人 `config..json`。
- **尚待真机验证：** 用户电脑能否从「试听叮声」听到音效、游戏音量混合器/输出设备、过滤英文数字设置、自然语音云希晓晓真实发声与鼠标切换实际延迟。CI 无声卡听觉验收，不应声称真实响铃或具体提速百分比。继续从本分支定点修复，不重做旧实验。

## 最新进展｜2026-11-10 Windows Blue Star OCR 清脆提示、自由框选、手动清除及速度修复（已构建）

- **当前活跃项目：** Windows 11 游戏 OCR，安卓蓝星向导继续搁置。原仓库不变：`vobichngan285-collab/-`。用户已授权本轮代码和构建。
- **新独立分支：** `feat/windows-v12-cursor-drag-clear-speed-20261110`；**Windows 实际构建 Commit：** `d5720f6924471200b3f2b68cc5a42a7c74f7c653`。从清爽蓝色大字 UI 源码 `6f1a78125c3fab9e7b0d04f7ac0180ea266a3b69` 起步；没有覆盖旧包、旧分支或 main 应用代码。
- **三项用户确认功能：** 默认模式 OCR 有**过滤后可朗读文字**才发出约145ms 清脆完成叮声，设置里可关；F11（可设其他单键）以**按快捷键时实际鼠标位置**为十字起点，鼠标左键任意方向拖动、松开即按选中矩形立即 OCR，保存相对 X/Y 偏移，淡绿框与后续局部扫描框使用同一区域；默认 F6（可自定义、冲突检查）立即清空所有旧 OCR 结果、框和语音并令进行中的旧结果失效，原 60 秒自动失效不变。
- **速度与健壮性：** 修复指向文字朗读的 `spoken` 未赋值引用风险；局部 OCR 完成后不重复等待完整扫描周期；按 generation 丢弃过时语音队列；减少局部截图的不必要 RGB 转换，三个截图路径串行共用 Small OCR 模型锁；新增截图/推理时间诊断，清除中途 OCR 时立即释放 UI busy。**没有改动 PP-OCRv6 Small 权重、原版 LunaTranslator 原生 EXE、用户私人配置或读屏控件架构**。
- **GitHub Windows CI 已确认：** [run 42684557197](https://github.com/vobichngan285-collab/-/actions/runs/42684557197) `completed/success`，`87 passed, 1 warning`（无失败）；冻结 EXE 真实 Small OCR、SAPI/WinRT 接口、原生语音 worker 常驻协议、原版 Luna 哈希和 GPL 源码、三次 Tk 框选、可点击穿透边框、完整蓝色 GUI 启动及 UIA `Strategy.PROVIDED` / **37 个命名原生控件**均 PASS；ZIP 上传成功。
- **下载**：[artifact 13704431105](https://github.com/vobichngan285-collab/-/actions/runs/42684557197/artifacts/13704431105)，名称 `GameTextReader-V12-CursorDrag-ClearKey-FastOCR`，**129817505 bytes**，过期时间 `2026-12-09T19:36:02Z`。这是 GitHub Actions 便携 ZIP，解压到**新目录**、勿覆盖既有语音可用版。公开构建不包含用户私人 `config..json`、语音模型密钥或识别文字。
- **尚需用户真机验收：** Windows 11 / 《七日杀》实际鼠标起点与任意方向拖框、松手后 OCR、扫描框边缘坐标；F6 手动清理和默认模式叮声；真实云希/晓晓发声、延迟和 NVDA 等真实读屏器控件反馈。CI 通过不等于实际游戏和真实音色必然正常，也没有可靠的加速百分比。下一步根据用户测试日志定点修正，不恢复 Medium、不重做已放弃实验。


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


## 最新接手提示：2026-11-11 Windows 游戏 OCR “简单粗暴”可见像素截图实验版

**唯一优先仍是电脑 GameTextReader；安卓蓝星向导暂停。** 用户指出真实《七日杀》主菜单可读，但进入存档菜单后最新绑定游戏 HWND/GDI 版叮声响却不读；用户纠正此前“解压失败”误解（实际解压启动没问题，是 OCR 逻辑没修好），并批准把核心链路简化、优化全屏识别→叮声→鼠标朗读的等待。

- Windows 项目原仓库 `vobichngan285-collab/-`，main 应用代码未覆盖。新独立分支 `fix/windows-simple-visible-capture-fast-20261111`，构建源码 Commit `0954e8157e851587acd5130b472dbe2ef6d2ad71`。
- **实际修改：** F8 使用锁定游戏 HWND 仅查询游戏客户端当下位置，截取当前位置可见桌面像素（原 V1.2 ImageGrab 路线）；不再经过窗口 GDI 位图。局部/固定区域仍统一真实桌面像素。保留 V1.2 Small、自然语音、滚轮、绿色框、无障碍、多模式，严禁下次随意重写。鼠标/队列轮询调至15ms，有可朗读结果则在 GUI 更新前投递叮声。不得宣传已有游戏真实速度提升数据。
- **CI:** 第一次 [42854631681](https://github.com/vobichngan285-collab/-/actions/runs/42854631681) 因旧20ms测试断言失败，后修复测试；最终 [42854889143](https://github.com/vobichngan285-collab/-/actions/runs/42854889143) Windows **success /125 passed /1 warning**，冻结 EXE OCR/语音协议/UIA/Tk picker自测成功，ZIP内1186项解压读校验成功。
- **交付直链：** https://github.com/vobichngan285-collab/-/releases/download/win-simple-visible-capture-20261111/BlueStarOCR_SimpleVisibleCapture_Fast_Windows_x64.zip ，130292246 bytes，SHA256 `f3aa38af7db2a97120612316fbb574af768c8d1441f181868cee5e3e20a5d88c`；[Release 和源码](https://github.com/vobichngan285-collab/-/releases/tag/win-simple-visible-capture-20261111) 。此前用户真实能发声的旧版和所有 ZIP/源码均保留。私人 `config..json` 不上云不随包。
- **待用户 Windows 真机验证，不能称已解决：** 《七日杀》第一主菜单 F8→叮→鼠标逐行读；点击开始进入「玩家档案/继续游戏/管理存档」新画面后再 F8→叮→逐行读；不同模式/轮盘清除可用；微软自然语音有声；具体屏幕内 F8 耗时。若依旧有叮但读旧文字，优先从新状态文字中的 `desktop_game_client`、实际识别行数、光标命中来定位，不再反复打包或胡乱改 OCR/TTS。**可见桌面抓图可能受独占全屏/遮挡影响**，不能假称已真机证实所有游戏场景。
- 详细原始历史和完整发布记录见 `main/RELEASE_STATUS.md` 最新追加章节；原 main 根目录的历史记录全部保留。


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
