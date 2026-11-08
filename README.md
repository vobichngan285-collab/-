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
