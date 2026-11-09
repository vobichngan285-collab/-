GameTextReader · V1.2 Small 底座 + 系统已安装自然语音自动发现（实验版）

核心设计：
- OCR 使用用户真机认可的 V1.2 Small DET+Small REC 原始检测参数（无 DET max/1280 缩放）。
- 不恢复后来已经删除的自动场景变化检测；不提供 Medium 模型、按钮及其权重。
- 本轮先实现语音修正；另行讨论的悬停局部 OCR/自定义模式键尚未加入本实验包。
- 不修改、不覆盖原 V1.2、V2.0 版本；请单独解压本实验包。

语音流程：
1. Windows 当前用户的已安装 MicrosoftWindows.Voice.* 语音包通过系统 Get-AppxPackage 列举。
2. 读取语音包 Tokens.xml 中可访问的名称/LicenseVersion，不直接以旧 JSON 的硬编码 WindowsApps 路径作为识别列表。
3. GUI 显示“系统自然语音 · 云希/晓晓（已安装，待试听）”；此显示不等于已能合成。
4. 用户选择自己本机的原版 config..json 或放在 EXE 同目录。程序只读取语音模型配置字段，不复制私人配置到 GitHub。
5. 在已选择的当前安装包路径上，找到系统的 Embedded Speech 运行组件，通过原作者未修改的 LunaSubprocess64.exe 按官方项目原有 SSML/命名管道协议合成音频；成功返回 WAV 后才请求本地播放。
6. 如失败，按发现/运行组件/原生进程/合成阶段给出脱敏错误分类，不再只有“RuntimeError”。诊断不输出用户私人许可证文字或完整 WindowsApps 路径。

安全与验收：
- 这份实验包不会内嵌原版 config..json、个人许可证、WindowsApps 语音模型。
- 仅可使用用户有权使用的本机配置与微软语音组件；本程序不会提取或绕过许可证。
- GitHub Windows 2025 云端没有用户的云希/晓晓自然语音包，因此 CI 只能验证扫描逻辑、官方原版可执行文件、IPC 与冷启动行为；无法证明真实云希/晓晓已发声。
- 如果用户在本机再次失败，请使用软件中的「复制语音诊断」并记录错误代码；不要公开 config..json、完整命令行或许可证值。
- 对真实发声判定：需点击“试听”并实际听到语音，不接受仅“检测到音色”或 “CI success” 作为通过标准。

原始上游 LunaTranslator： https://github.com/HIllya51/LunaTranslator ，v12.1.3.9，GPLv3。打包完整对应源码并保持原作者相关组件字节未修改；微软系统组件适用其独立的授权条件。
