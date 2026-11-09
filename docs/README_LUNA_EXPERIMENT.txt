GameTextReader V1.9 实验版：按 LunaTranslator 的原始自然语音流程

1. Windows 游戏 OCR 只保留 PP-OCRv6 Small 检测/识别，F8、鼠标指向朗读、绿色框等行为保持。
2. 这次独立语音模式直接读取原作者的完整 config..json 文件：
   - reader.windowstts.use = true
   - reader.windowstts.voice = [1, "本机 MicrosoftWindows.Voice.zh-CN.Yunxi... 完整路径"]
   - MicrosoftWindows.Voice.License （原封不动、不截断、不删空格）
   - MicrosoftWindows.Speech.License （保留读取，不误当 Voice.License）
3. 操作：可把原作者的 config..json 放在 GameTextReader.exe 所在文件夹内；或启动程序，点击「导入原作者 config..json」，选择你已有的文件。无需手工修改原内容。文件仅从本机读取，不复制进程序内置设置、不上传。
4. 选中「微软自然语音 · 云希（原作者 JSON 配置）」后按「试听」。独立工作进程读取原文件，以 model path 配置微软官方 Embedded Speech SDK，把原始 MicrosoftWindows.Voice.License 传给模型初始化属性 SpeechServiceConnection_SynthModelKey，按照 Luna 的结构用 SSML 合成 WAV 并通过 Windows 播放。
5. 如果当前机器没有语音包、Tokens.xml 或微软 SDK 不接受模型/授权，可能无法合成。不会回退成其他音色假装成功。
6. 这只是实验版，不是已经解决的云希/晓晓：GitHub Windows CI 可以验证配置字段原样进入 SDK 调用和独立工作进程，但云端没有用户的语音包，不能证明用户的云希/晓晓实际发声。
7. 本版本没有将任何微软自然语音包、原作者嵌入式语音默认密钥、用户原始配置、许可证文本复制进代码仓库或分发包。微软模型是否可由第三方应用使用取决于适用授权。
8. 系统 Windows SAPI、WinRT 和原先独立广荣入口仍保留，但本次测试自然语音时选择的是真正 Luna 原配置模式，不使用其他引擎冒充。
9. 使用全新文件夹解压，不覆盖 V1.8 原文件。若没有云希/晓晓实际 WAV，请保留 V1.8 并停止重复安装无意义测试版。
