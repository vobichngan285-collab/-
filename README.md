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
