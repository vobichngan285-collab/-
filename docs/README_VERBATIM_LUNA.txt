GameTextReader · LunaTranslator 官方原版语音引擎整合实验（Windows x64）

核心事实：
- 本包的 LunaSubprocess64.exe 来自 LunaTranslator 作者官方发布版本 v12.1.3.9，
  未重新编译、未修改、未打补丁，运行时直接使用其中的 msnaturalvoice 指令。
  官方发布压缩包 SHA-256:
  c0248288c12de19e9e1f953922355aaa123699820fce26e4e84329be2666d62f
  原版 LunaSubprocess64.exe SHA-256:
  886892cd78cdd8bbd029a3f4977853cc1ddce1c9723e656986fa8b5a79e6a974

- 与原版的接口保持一致：msnaturalvoice 子命令、命名管道、事件、共享内存；
  原始窗口 TTS JSON voice[0]=1, voice[1] 是语音包路径；
  MicrosoftWindows.Voice.License 原样传入原作者语音子进程。
  与原作者相同的 SSML 速率公式、Unicode 转义和 WAV 返回格式。
- 本软件另写的仅是 GameTextReader <-> 原版子进程的 Windows IPC 连接部分，
  并没有重新编写原版微软语音核心或替换原作者的执行文件。
- upstream_luna_original 文件夹内含原作者 WindowsTTS 和 msnaturalvoice 等源文件的未修改原文。
  UPSTREAM_LUNA_GPL_SOURCE_v12.1.3.9.zip 包含上游同版本完整公开源码。
  其作者与版权均归 LunaTranslator 原项目及其贡献者，按 GPLv3 许可分发。
  原仓库：https://github.com/HIllya51/LunaTranslator
  源码版本 v12.1.3.9，commit 84677faeaa1e61bd7dd00b820090e9d2fe6c5142
  本软件新增连接代码的使用也须遵守上游 GPLv3 以及微软组件适用许可。

使用说明：
1. 默认 OCR 为 PP-OCRv6 Small，原有 F8 快捷键、屏幕文字框与鼠标指向朗读保留。
2. 将用户自己的原始 config..json 放在 GameTextReader.exe 同一文件夹内。
   也可以在程序里点击「导入原作者 config..json」并选择原文件。
   不要把原文件改成格式不同的配置，也不要将其上传到公共 GitHub。
3. 语音列表选择「微软自然语音 · 云希（原作者 JSON 配置）」。
   点击试听，确认实际能听见声音，然后再用于鼠标指向朗读。
4. 如果本机语音包版本路径不一致、微软组件不开放第三方调用或缺少适用模型
   使用权限，可能不能发声。程序不能替用户授予微软许可证，也不会修改系统模型。
5. 原始配置内容在打包时逐字节保留。请注意此文件也可能包含与其他应用有关的
   个人偏好或凭据，不要将带有配置的安装包公开传播。
6. GitHub 云端测试可确认官方原版执行文件 SHA、完整源码、Windows 管道调用、
   配置字节不变、OCR/应用启动；云端没有云希/晓晓模型，不得声称实际发声测试成功。
