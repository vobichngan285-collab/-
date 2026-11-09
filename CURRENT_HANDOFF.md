# Windows 游戏文字助手｜当前交接（2026-11-09）

**当前唯一重点：Windows 11 电脑游戏 OCR 文字助手。** 安卓云端「蓝星向导」暂时搁置；安卓纯离线 OCR/CRAFT 已放弃。不要混淆两个 GitHub 仓库或重做安卓实验。

**GitHub 原仓库：** https://github.com/vobichngan285-collab/-  
**下次新对话先读本文件；旧版流水账仅在需要时再读 `RELEASE_STATUS.md`。** `main` 是交接和旧版本入口，当前 Windows V1.7 实验代码在独立分支，勿误从 main 重建旧包。

## 1. 当前已做完

- **Windows V1.7 Medium 延迟优化实验版：** 分支 `exp/windows-medium-latency-v17-20261109`，构建源码 Commit `1e9c216d1bf5ec7f7cb7facc239375fcff64d525`。原 V1.6 未覆盖。
- **正式 CI 通过：** https://github.com/vobichngan285-collab/-/actions/runs/42583872881 ，26 项单元测试、真实官方模型 Small/Medium 中英文 OCR、冻结 EXE、无障碍绿色框、SAPI/WinRT 合成和模拟广荣 PCM 通路回归通过（不等于用户电脑实测或真实广荣发声）。
- **V1.7 ZIP：** https://github.com/vobichngan285-collab/-/actions/runs/42583872881/artifacts/13658427538 ；内层 `GameTextReader_V1.7_Medium_CPU2_Windows_x64_Portable.zip`，194,448,729 bytes，SHA256 `df9a054ba44b041bc75b8906030bd41367d25a71dee96dcd346e54c3eef37287`；助手下载后对内外两层 ZIP 做了 CRC 校验，包含 `GameTextReader.exe` / `GuangrongHost.exe`，未捆绑第三方 DLL。此为 GitHub Actions 临时 artifact，不是永久 Release。
- **实际改动仅限 OCR：** Small 模型/配置不变；Medium 使用同一个 Small DET + Medium REC，默认 REC batch 2、ONNX CPU 线程 2。预热改为 750ms 防抖并丢弃过期任务；OCR 诊断拆成 `model_lock_wait_ms`、`model_load_ms`、`inference_ms`，保留原 `model_ms`。保留 F8 单键截图、鼠标指向文字朗读、绿色坐标框、60 秒清空等功能。
- **Windows CI 测试事实：** 最后一次固定CPU2条件下，batch6→batch2：4行 559→550ms、18行 2124.5→1909ms，文字/坐标完全相同；此前另轮测试约快5%，波动存在。CPU2 对照自动线程在前后顺序反转复测后只快约3%～4%，早期更大改善不稳定。**不要声称数倍提速**，CI 也不代替用户电脑实际 F8 等待；Medium REC 仍是主要耗时来源。

## 2. 现在仍存在的两个问题

**A. Medium OCR 慢，鼠标指向朗读可能受识别完成等待影响。** 用户亲测 Small 相对流畅；Medium 按 F8 后窗口不死机，但识别结果长时间不出现、自然无法即时指向朗读。V1.7 是已通过云端测试的保守调度实验包，**尚未在用户 Windows 11 真机验证**。下次请先在新目录解压 V1.7，拿同一游戏画面分别按 F8 测 Small/Medium；点「复制链路日志」，看截图、锁等待、加载、推理、有效文字框数量、是否能鼠标命中。不要自行假定 TTS 导致 OCR 推理慢。

**B. 广荣微软 TTS 的云希/晓晓仍未成功独立使用。** Windows 原版 `grtts_x64.dll` 在干净 CI 加载出现 ERROR 1114，真实声音与 PCM 均未证实；V1.6 的模拟本地 IPC/PCM 通过只证明自研链路。此前已制作 `BaoYiVoiceInspector.exe` 只读调查工具，Windows 测试成功但**尚无用户电脑真实报告**；如果继续查广荣，要使用真实保益悦听运行时证据，别重复做已失败的无环境 DLL 加载实验。TTS 与 OCR 优化是两件事。

## 3. 下一步与纪律

- **优先等用户真机测试 V1.7**，比较实际 F8 延迟、识别框、鼠标指向朗读；如果没有实际改善，再讨论更换推理执行后端或更激进的 Medium 优化，不能盲目反复改参数。
- **暂不碰广荣 TTS 或安卓蓝星向导**，除非用户新指令明确要求。
- 任何新开发先核对 GitHub 实际分支 HEAD、Actions、历史源码，**未经授权不改代码、不构建、不重新开仓**；重要进展更新本简短文件、在 `main:RELEASE_STATUS.md` 追加一条历史记录，提交并回读。不要夸大构建成功、合成成功与真实电脑可用的区别。
