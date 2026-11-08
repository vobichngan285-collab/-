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
