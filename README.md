# Windows 游戏文字助手｜GameTextReader

**当前主要开发：Windows 11 的离线游戏 OCR + 鼠标指向文字朗读。** 安卓云端「蓝星向导」暂时搁置；安卓旧离线 OCR/CRAFT 已放弃。

**新对话只需先读：** [CURRENT_HANDOFF.md](CURRENT_HANDOFF.md)。它包含当前版本、真实进度、两大未解决问题、实验分支与下一步计划。旧开发史仅在 [RELEASE_STATUS.md](RELEASE_STATUS.md) 存档，不要从 V1.0 重新阅读或重复旧实验。

## 当前 Windows 测试版

- **V1.7 Medium 延迟实验：** `exp/windows-medium-latency-v17-20261109`；[成功 Windows CI](https://github.com/vobichngan285-collab/-/actions/runs/42583872881)；[免安装 ZIP 工件](https://github.com/vobichngan285-collab/-/actions/runs/42583872881/artifacts/13658427538)。
- **改动范围：** Small OCR 原样保留；Medium 默认使用 batch2、CPU2；避免过期预热任务争用，记录锁等待与模型推理耗时。
- **测试边界：** 26 项自动测试与真实模型的 Windows CI 通过；改善幅度在稳定复测中不大（几百分点），**尚未通过用户 Windows 电脑实际游戏验收**。请不要将临时实验包装成已解决速度问题的正式版本。
- **广荣微软 TTS：** 用户目标为云希／晓晓，官方 DLL 在独立实验环境加载仍有 ERROR1114；本次 V1.7 **没有修复广荣发声问题**。先分开调查 OCR 与语音。
- **原 V1.6：** [旧版 Windows CI](https://github.com/vobichngan285-collab/-/actions/runs/42556569339)，可以独立保留作 A/B 回退，不要覆盖旧解压目录。

## 交接与工作纪律

每次开发前核查原分支、实际 Commit、CI 与版本。只在用户明确授权时改代码、测试或构建；不要重建已完成的模块。成果及真实局限更新 [CURRENT_HANDOFF.md](CURRENT_HANDOFF.md)，历史只在 [RELEASE_STATUS.md](RELEASE_STATUS.md) 追加摘要。原长 README 可在[历史提交](https://github.com/vobichngan285-collab/-/blob/48dacf9b53287fe3c9cd7f3db1b6d423665dd01f/README.md) 找回。
