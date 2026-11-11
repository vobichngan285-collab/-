LunaTranslator 完整原版 OCR 基准实验｜2026-11-12

原作者 GitHub：https://github.com/HIllya51/LunaTranslator
固定版本：v12.1.3.9
原作者源码 Commit：84677faeaa1e61bd7dd00b820090e9d2fe6c5142
许可证：GPL-3.0（完整原版源码与 LICENSE 在 UPSTREAM_FULL_SOURCE_v12.1.3.9.zip）

本包的意义
============
本包不是“我们用原作者思路仿写的 OCR”，而是直接原封不动使用
LunaTranslator 官方完整版，保留其全部 OCR 体系：
1. 原版 NativeUtils.dll / GdiCropImage 游戏/桌面截图；
2. 原版 OCR 选区管理、连续扫描线程、定时与画面分析；
3. 原版 CVUtils.dll / LocalOCR 的引擎、设备、模型和线程配置；
4. 原版识别结果处理、原文去重、文字块坐标输出；
5. 原版完整 Qt 环境、官方主程序及依赖。

所有原作者运行文件经 SHA256 逐文件校验，未被修改。
本包是用于验证“真正原作者整套程序”游戏表现的【独立基准实验】，
尚未连接到蓝星助手的鼠标朗读和快捷键，因此不能冒称“已整体替换 GameTextReader”。

如何试
======
1. 解压整个 ZIP 到全新目录，进入 LunaTranslator_CompleteOriginal 中的
   LunaTranslator_x64 目录（具体路径以程序实际文件为准）。
2. 运行 LunaTranslator.exe，按原作者程序的 OCR 设置开启自动区域 OCR。
3. 选择原版 OCR 引擎和原作者推荐的设备配置；观察所用引擎、是否启用 GPU。
4. 将扫描检查间隔设为与此前测试相同的 300ms（若原版设置项使用秒，输入 0.3）。
5. 使用《七日杀》同一个固定选区，分别记录：未启动软件的 FPS、
   只开原版 Luna OCR 的 FPS、CPU 占用和实际 OCR 结果。
6. 不要同时打开蓝星 GameTextReader 的连续区域 OCR，
   否则两套扫描叠加会影响实验真实性。

注意
====
* 与蓝星历史工作包完全隔离。不能把文件解压覆盖到旧版目录。
* 上游可能需要在程序内下载和选择 OCR 模型；模型及设备不同会影响
  CPU/GPU 占用，不能认为同为 300ms 就必然同 FPS。
* 由于上游完整程序非蓝星原版语音设置，勿复制、公开私人 voice config。
* 若你需要在蓝星原有 F8/F9/F11/F7 和云曦/晓晓语音中使用 Luna 原版，
  还需要在确认原版 CPU 表现后，通过最小输入输出适配层连接；
  直接拼装 Qt、C++ 和 Tk 是错误路径。
* 本版绝不修改昨天确认识别正常的源码、安装包和参数。
