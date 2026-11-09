// BaoYi Voice Inspector / 保益悦听语音组件只读调查工具
// Standalone WinForms .NET Framework 4.x, x64, no administrator privilege.
// No network, telemetry, OCR capture, text input, license/config reading,
// DLL injection, voice commands or process modification.
// Output only candidate process/module names and redacted installation paths.
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Windows.Forms;
using Microsoft.Win32;

namespace BaoYiVoiceInspector
{
    internal static class Program
    {
        [STAThread]
        private static void Main(string[] args)
        {
            if (args.Length > 0 && args[0] == "--self-test")
            {
                string path = Path.Combine(Path.GetTempPath(), "BaoYiVoiceInspector_test.txt");
                try
                {
                    if (!Inspector.IsProduct("BoyPcReader.exe") ||
                        !Inspector.IsProduct("保益悦听") ||
                        !Inspector.IsStrongVoiceModule("grtts_x64.dll") ||
                        !Inspector.IsStrongVoiceModule("Microsoft.CognitiveServices.Speech.core.dll") ||
                        Inspector.IsProduct("explorer.exe") ||
                        Inspector.IsStrongVoiceModule("kernel32.dll"))
                        throw new Exception("Product or voice engine matching regression");
                    string home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
                    if (home.Length > 2)
                    {
                        string sample = home + "\\Documents\\example.dll";
                        string redacted = Inspector.RedactPath(sample);
                        if (redacted.Contains(home) || !redacted.Contains("%USERPROFILE%"))
                            throw new Exception("User folder redaction regression");
                    }
                    File.WriteAllText(path, "PASS: matching, module detection, user-path redaction", Encoding.UTF8);
                    Environment.ExitCode = 0;
                }
                catch (Exception ex)
                {
                    File.WriteAllText(path, "FAIL: " + ex.ToString(), Encoding.UTF8);
                    Environment.ExitCode = 1;
                }
                return;
            }
            if (args.Length > 0 && args[0] == "--ci-scan")
            {
                string path = Path.Combine(Path.GetTempPath(), "BaoYiVoiceInspector_ci_scan.txt");
                try
                {
                    string report = Inspector.Scan();
                    if (!report.Contains("扫描进程总数") ||
                        !report.Contains("不读取朗读内容") ||
                        !report.Contains("调查结论"))
                        throw new Exception("Scan report incomplete");
                    File.WriteAllText(path, report, new UTF8Encoding(true));
                    Environment.ExitCode = 0;
                }
                catch (Exception ex)
                {
                    File.WriteAllText(path, "FAIL: " + ex.ToString(), Encoding.UTF8);
                    Environment.ExitCode = 1;
                }
                return;
            }
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new InspectorForm());
        }
    }

    internal sealed class InspectorForm : Form
    {
        private readonly Button scanButton;
        private readonly Button copyButton;
        private readonly Button saveButton;
        private readonly TextBox report;
        private readonly Label status;
        private string lastReport = "";

        public InspectorForm()
        {
            Text = "保益悦听语音组件调查工具 · 只读";
            Width = 940;
            Height = 690;
            MinimumSize = new Size(690, 480);
            Font = new Font("Microsoft YaHei UI", 10.0f);
            StartPosition = FormStartPosition.CenterScreen;
            AutoScaleMode = AutoScaleMode.Font;

            var layout = new TableLayoutPanel();
            layout.Dock = DockStyle.Fill;
            layout.Padding = new Padding(14);
            layout.ColumnCount = 1;
            layout.RowCount = 4;
            layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
            layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            Controls.Add(layout);

            var intro = new Label();
            intro.AutoSize = true;
            intro.MaximumSize = new Size(850, 0);
            intro.Text = "先正常启动保益悦听，并使用你平常的广荣微软音色。" +
                         " 然后按“开始只读扫描”。仅检查进程、已经加载的 DLL 和安装目录文件名；" +
                         "不会发出朗读指令，不修改保益、不读取配置内容或许可证，也不会上传任何信息。";
            intro.AccessibleName = "实验说明";
            layout.Controls.Add(intro, 0, 0);

            var buttons = new FlowLayoutPanel();
            buttons.AutoSize = true;
            buttons.Dock = DockStyle.Fill;
            buttons.Padding = new Padding(0, 10, 0, 10);
            scanButton = new Button();
            scanButton.AutoSize = true;
            scanButton.Text = "开始只读扫描";
            scanButton.AccessibleName = "开始只读扫描保益语音组件";
            scanButton.Click += StartScan;
            buttons.Controls.Add(scanButton);

            copyButton = new Button();
            copyButton.AutoSize = true;
            copyButton.Text = "复制调查报告";
            copyButton.Enabled = false;
            copyButton.AccessibleName = "复制调查报告到剪贴板";
            copyButton.Click += delegate
            {
                try { Clipboard.SetText(lastReport); status.Text = "报告已复制，可粘贴到聊天。"; }
                catch (Exception ex) { status.Text = "剪贴板不可用：" + ex.Message; }
            };
            buttons.Controls.Add(copyButton);

            saveButton = new Button();
            saveButton.AutoSize = true;
            saveButton.Text = "另存报告 TXT";
            saveButton.Enabled = false;
            saveButton.AccessibleName = "手动保存调查报告文本";
            saveButton.Click += SaveReport;
            buttons.Controls.Add(saveButton);
            layout.Controls.Add(buttons, 0, 1);

            report = new TextBox();
            report.Dock = DockStyle.Fill;
            report.Multiline = true;
            report.ReadOnly = true;
            report.ScrollBars = ScrollBars.Both;
            report.WordWrap = false;
            report.Font = new Font("Consolas", 10.5f);
            report.AccessibleName = "只读调查报告内容";
            report.Text = "尚未扫描。\r\n请先打开保益悦听，再点击“开始只读扫描”。";
            layout.Controls.Add(report, 0, 2);

            status = new Label();
            status.Dock = DockStyle.Fill;
            status.AutoSize = true;
            status.AccessibleName = "扫描状态";
            status.Text = "状态：就绪。无需管理员权限；发现访问受限的进程时会在报告中说明。";
            layout.Controls.Add(status, 0, 3);
            ActiveControl = scanButton;
        }

        private void StartScan(object sender, EventArgs e)
        {
            scanButton.Enabled = false;
            copyButton.Enabled = false;
            saveButton.Enabled = false;
            status.Text = "正在只读调查正在运行的进程和语音 DLL……";
            report.Text = "扫描中。程序不会向外发送任何数据。";
            ThreadPool.QueueUserWorkItem(delegate
            {
                string result;
                try { result = Inspector.Scan(); }
                catch (Exception ex)
                {
                    result = "调查发生异常：" + ex.GetType().Name + "\r\n" + ex.Message;
                }
                if (IsDisposed || !IsHandleCreated) return;
                try
                {
                    BeginInvoke((Action)delegate
                    {
                        lastReport = result;
                        report.Text = result;
                        copyButton.Enabled = true;
                        saveButton.Enabled = true;
                        scanButton.Enabled = true;
                        status.Text = "只读扫描结束。请选择“复制调查报告”，发送给我分析。";
                    });
                }
                catch (InvalidOperationException) { }
            });
        }

        private void SaveReport(object sender, EventArgs e)
        {
            using (var dialog = new SaveFileDialog())
            {
                dialog.Title = "另存保益语音调查报告";
                dialog.FileName = "BaoYi_TTS_Report.txt";
                dialog.Filter = "文本文件 (*.txt)|*.txt";
                if (dialog.ShowDialog(this) != DialogResult.OK) return;
                try
                {
                    File.WriteAllText(dialog.FileName, lastReport, new UTF8Encoding(true));
                    status.Text = "报告已保存。除你手动保存的位置外，不会写入其他诊断文件。";
                }
                catch (Exception ex) { status.Text = "保存失败：" + ex.Message; }
            }
        }
    }

    internal static class Inspector
    {
        private const int MaxModulesPerCandidate = 100;
        private const int MaxFilesPerDirectory = 100;
        private static readonly string[] VoiceTokens = {
            "grtts", "guangrong", "naturalvoice", "neuralvoice", "yongde",
            "vocalizer", "cerence", "speechsdk", "cognitiveservices.speech",
            "msc_x64", "xfyun", "ifly", "ttsengine", "synthdriver", "boyctrl"
        };
        private static readonly string[] ProductTokens = {
            "baoyi", "boypc", "boyreader", "boyctrl", "保益", "悦听",
            "boy_sr", "boysr", "boyreader", "boyscreenreader"
        };
        private static readonly string[] AssociatedSubdirs = {
            "bin", "dll", "plugins", "plugin", "tts", "voice", "voices",
            "speech", "synthDrivers", "engines", "audio", "NaturalVoiceS", "x64"
        };

        internal static bool ContainsAny(string value, string[] pieces)
        {
            if (String.IsNullOrEmpty(value)) return false;
            string v = value.ToLowerInvariant();
            foreach (string p in pieces)
                if (v.Contains(p.ToLowerInvariant())) return true;
            return false;
        }

        internal static bool IsProduct(string value)
        {
            return ContainsAny(value, ProductTokens);
        }
        internal static bool IsStrongVoiceModule(string value)
        {
            return ContainsAny(value, VoiceTokens);
        }
        private static bool IsPossibleSpeech(string value)
        {
            return IsStrongVoiceModule(value) ||
                   ContainsAny(value, new string[] { "speech", "sapi", "voice", "tts", "synth" });
        }

        internal static string RedactPath(string path)
        {
            if (String.IsNullOrEmpty(path)) return "(无)";
            string result = path;
            string home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            string[] originals = {
                Environment.GetEnvironmentVariable("LOCALAPPDATA"),
                Environment.GetEnvironmentVariable("APPDATA"),
                home, Environment.GetEnvironmentVariable("TEMP")
            };
            string[] replacements = {
                "%LOCALAPPDATA%", "%APPDATA%", "%USERPROFILE%", "%TEMP%"
            };
            // Prefer longest prefixes so C:\Users\someone\AppData is not partially stripped.
            for (int i = 0; i < originals.Length; ++i)
            {
                if (!String.IsNullOrEmpty(originals[i]))
                    result = ReplaceIgnoreCase(result, originals[i].TrimEnd('\\'), replacements[i]);
            }
            if (!String.IsNullOrEmpty(Environment.UserName))
                result = ReplaceIgnoreCase(result, Environment.UserName, "<用户>");
            return result;
        }

        private static string ReplaceIgnoreCase(string source, string search, string replacement)
        {
            if (String.IsNullOrEmpty(search)) return source;
            int i = 0;
            var output = new StringBuilder();
            while (i < source.Length)
            {
                int found = source.IndexOf(search, i, StringComparison.OrdinalIgnoreCase);
                if (found < 0) { output.Append(source.Substring(i)); break; }
                output.Append(source.Substring(i, found - i));
                output.Append(replacement);
                i = found + search.Length;
            }
            return output.ToString();
        }

        private static readonly HashSet<int> ProductWindows = new HashSet<int>();
        private delegate bool WindowEnumProc(IntPtr hwnd, IntPtr arg);
        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        private static extern bool EnumWindows(WindowEnumProc callback, IntPtr lParam);
        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        private static extern int GetWindowText(IntPtr hwnd, StringBuilder buffer, int maxCount);
        [DllImport("user32.dll")]
        private static extern int GetWindowTextLength(IntPtr hwnd);
        [DllImport("user32.dll")]
        private static extern bool IsWindowVisible(IntPtr hwnd);
        [DllImport("user32.dll")]
        private static extern int GetWindowThreadProcessId(IntPtr hwnd, out int pid);

        private static void MatchWindows()
        {
            ProductWindows.Clear();
            EnumWindows(delegate(IntPtr hwnd, IntPtr arg)
            {
                if (!IsWindowVisible(hwnd)) return true;
                int length = GetWindowTextLength(hwnd);
                if (length == 0 || length > 1024) return true;
                var buffer = new StringBuilder(length + 1);
                GetWindowText(hwnd, buffer, buffer.Capacity);
                // Window title is used ONLY to identify BaoYi process IDs.
                // NEVER print or store titles; may contain user documents.
                if (IsProduct(buffer.ToString()))
                {
                    int pid;
                    GetWindowThreadProcessId(hwnd, out pid);
                    if (pid > 0) ProductWindows.Add(pid);
                }
                return true;
            }, IntPtr.Zero);
        }

        private sealed class ProductLocation
        {
            public string Label, Directory;
            public ProductLocation(string label, string path) { Label = label; Directory = path; }
        }

        private static List<ProductLocation> GetInstallationRecords()
        {
            var items = new List<ProductLocation>();
            foreach (RegistryHive hive in new RegistryHive[] {
                RegistryHive.LocalMachine, RegistryHive.CurrentUser })
            {
                foreach (RegistryView view in new RegistryView[] {
                    RegistryView.Registry64, RegistryView.Registry32 })
                {
                    try
                    {
                        using (RegistryKey root = RegistryKey.OpenBaseKey(hive, view))
                        using (RegistryKey uninstall = root.OpenSubKey(
                           @"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", false))
                        {
                            if (uninstall == null) continue;
                            string[] names = uninstall.GetSubKeyNames();
                            for (int i = 0; i < names.Length && i < 4096; ++i)
                            {
                                try
                                {
                                    using (RegistryKey sub = uninstall.OpenSubKey(names[i], false))
                                    {
                                        if (sub == null) continue;
                                        string display = Convert.ToString(sub.GetValue("DisplayName", ""));
                                        if (!IsProduct(display)) continue;
                                        string loc = Convert.ToString(sub.GetValue("InstallLocation", ""));
                                        string icon = Convert.ToString(sub.GetValue("DisplayIcon", ""));
                                        if (String.IsNullOrEmpty(loc) && !String.IsNullOrEmpty(icon))
                                        {
                                            string p = icon.Trim().Trim('"');
                                            int comma = p.LastIndexOf(',');
                                            if (comma > 0) p = p.Substring(0, comma).Trim('"');
                                            try { loc = Path.GetDirectoryName(p); }
                                            catch (ArgumentException) { }
                                        }
                                        string version = Convert.ToString(sub.GetValue("DisplayVersion", ""));
                                        items.Add(new ProductLocation(display + " " + version, loc));
                                    }
                                }
                                catch (Exception ex) when (ex is System.Security.SecurityException ||
                                                          ex is UnauthorizedAccessException ||
                                                          ex is IOException) { }
                            }
                        }
                    }
                    catch (Exception ex) when (ex is System.Security.SecurityException ||
                                              ex is UnauthorizedAccessException ||
                                              ex is IOException) { }
                }
            }
            return items;
        }

        private static bool IsWindowsSystemModule(string file)
        {
            string windows = Environment.GetFolderPath(Environment.SpecialFolder.Windows);
            return !String.IsNullOrEmpty(windows) && file.StartsWith(
                windows + "\\", StringComparison.OrdinalIgnoreCase);
        }

        internal static string Scan()
        {
            var text = new StringBuilder();
            text.AppendLine("===== 保益悦听语音组件只读调查报告 =====");
            text.AppendLine("本报告不读取朗读内容、屏幕文字、聊天记录、配置文件内容或许可证。");
            text.AppendLine("无网络上传；不发送语音命令、不停止或改变保益悦听进程。");
            text.AppendLine("扫描时间：" + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"));
            text.AppendLine("Windows 系统：" + Environment.OSVersion.VersionString);
            text.AppendLine("诊断进程位数：" + (Environment.Is64BitProcess ? "64位" : "32位"));
            text.AppendLine();

            try { MatchWindows(); }
            catch (Exception ex) { text.AppendLine("窗口匹配不可用：" + ex.GetType().Name); }

            List<ProductLocation> installed = GetInstallationRecords();
            text.AppendLine("【1. 已安装的保益相关程序】");
            if (installed.Count == 0) text.AppendLine("未从常用 Windows 卸载注册表位置找到保益项目（不代表一定未安装）。");
            var roots = new List<ProductLocation>();
            var seenRoot = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (ProductLocation item in installed)
            {
                text.AppendLine("- " + item.Label + "；目录：" + RedactPath(item.Directory));
                if (!String.IsNullOrEmpty(item.Directory) &&
                    Directory.Exists(item.Directory) && seenRoot.Add(item.Directory))
                    roots.Add(item);
            }
            text.AppendLine();

            int inspected = 0, inaccessible = 0, candidateCount = 0;
            var loadedVoiceNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var candidates = new StringBuilder();
            Process[] processes = Process.GetProcesses();
            foreach (Process process in processes)
            {
                using (process)
                {
                    ++inspected;
                    string name = "";
                    try { name = process.ProcessName; }
                    catch { continue; }
                    bool isProduct = IsProduct(name) || ProductWindows.Contains(process.Id);
                    List<ProcessModule> modules = new List<ProcessModule>();
                    try
                    {
                        foreach (ProcessModule module in process.Modules)
                            modules.Add(module);
                    }
                    catch (Win32Exception) { ++inaccessible; }
                    catch (InvalidOperationException) { ++inaccessible; }
                    catch (System.Security.SecurityException) { ++inaccessible; }

                    var strong = new List<ProcessModule>();
                    var related = new List<ProcessModule>();
                    foreach (ProcessModule mod in modules)
                    {
                        string dll = mod.ModuleName;
                        if (IsStrongVoiceModule(dll))
                            strong.Add(mod);
                        if (isProduct &&
                            (IsPossibleSpeech(dll) || !IsWindowsSystemModule(mod.FileName)))
                            related.Add(mod);
                    }
                    if (!isProduct && strong.Count == 0) continue;
                    candidateCount++;
                    bool voicePositive = strong.Count > 0;
                    candidates.AppendLine(isProduct ? "[保益相关进程]" : "[加载了语音相关 DLL 的其他进程]");
                    candidates.AppendLine("进程：" + name + ".exe；PID：" + process.Id +
                                          "；保益窗口匹配：" + ProductWindows.Contains(process.Id));
                    if (modules.Count == 0)
                        candidates.AppendLine("  无法读取此进程的模块（权限、位数或进程已退出）。");
                    else
                    {
                        candidates.AppendLine("  已加载模块数：" + modules.Count);
                        if (voicePositive)
                            candidates.AppendLine("  ★ 已在内存中找到疑似语音引擎 DLL：");
                        foreach (ProcessModule mod in strong)
                        {
                            loadedVoiceNames.Add(mod.ModuleName);
                            candidates.AppendLine("  已加载：" + mod.ModuleName +
                                                   "；" + RedactPath(mod.FileName));
                        }
                        if (isProduct)
                        {
                            int printed = 0;
                            candidates.AppendLine("  本程序额外加载的非 Windows 系统模块／语音模块：");
                            foreach (ProcessModule mod in related)
                            {
                                if (strong.Contains(mod)) continue;
                                if (++printed > MaxModulesPerCandidate)
                                {
                                    candidates.AppendLine("  ...（余下模块省略）");
                                    break;
                                }
                                candidates.AppendLine("  模块：" + mod.ModuleName +
                                                      "；" + RedactPath(mod.FileName));
                            }
                            if (modules.Count > 0)
                            {
                                try
                                {
                                    string p = process.MainModule.FileName;
                                    string dir = Path.GetDirectoryName(p);
                                    if (!String.IsNullOrEmpty(dir) && seenRoot.Add(dir))
                                        roots.Add(new ProductLocation(name, dir));
                                    candidates.AppendLine("  运行目录：" + RedactPath(dir));
                                }
                                catch (Exception) { candidates.AppendLine("  主程序运行目录：无法读取"); }
                            }
                        }
                    }
                    candidates.AppendLine();
                }
            }
            text.AppendLine("【2. 当前运行进程与已加载的 DLL】");
            text.AppendLine("扫描进程总数：" + inspected + "；模块无法读取：" + inaccessible);
            text.AppendLine("命中的相关进程数：" + candidateCount);
            if (candidateCount == 0)
                text.AppendLine("未发现正在运行的保益候选进程或具有明显广荣标识的模块。请先启动保益再扫描。");
            text.Append(candidates);
            text.AppendLine();

            text.AppendLine("【3. 保益安装目录中可能相关的文件名】");
            int fileMatches = 0;
            foreach (ProductLocation item in roots)
            {
                if (String.IsNullOrEmpty(item.Directory)) continue;
                text.AppendLine("目录来源：" + item.Label + "；" + RedactPath(item.Directory));
                fileMatches += ScanDirectory(item.Directory, text);
                foreach (string child in AssociatedSubdirs)
                {
                    try
                    {
                        string dir = Path.Combine(item.Directory, child);
                        if (Directory.Exists(dir)) fileMatches += ScanDirectory(dir, text);
                    }
                    catch (Exception) { }
                }
            }
            if (roots.Count == 0) text.AppendLine("未定位到可读取的保益安装目录。");
            if (fileMatches == 0) text.AppendLine("上述安装目录中未发现明显名称匹配的 DLL 或语音资源。");
            text.AppendLine();

            text.AppendLine("【4. 调查结论】");
            if (loadedVoiceNames.Count > 0)
            {
                text.AppendLine("已在运行中发现疑似语音模块（这些是内存已加载证据，不只是安装文件）：");
                foreach (string name in loadedVoiceNames) text.AppendLine("- " + name);
                text.AppendLine("下一步：依据模块具体名称和路径，研究它属于哪一种语音接口；");
                text.AppendLine("但仅凭模块名称不能证明保益已经使用它合成当前正在听到的声音。");
            }
            else
            {
                text.AppendLine("尚未在可检查的运行进程中定位到明确的广荣引擎模块。");
                text.AppendLine("可能的原因：保益使用另一名称的组件、另一个独立服务、");
                text.AppendLine("系统 TTS 服务，或者当前进程模块读取受到权限限制。");
                text.AppendLine("不能据此断言保益没有使用广荣。");
            }
            text.AppendLine("仅有安装文件不能证明它正在使用；只有模块被加载才构成直接运行证据。");
            text.AppendLine("报告可能含安装目录结构和程序名；发送前可自行检查并删去不想分享的行。");
            text.AppendLine("===== 调查结束 =====");
            return text.ToString();
        }

        private static int ScanDirectory(string folder, StringBuilder text)
        {
            int seen = 0, matched = 0;
            try
            {
                foreach (string f in Directory.EnumerateFiles(folder, "*", SearchOption.TopDirectoryOnly))
                {
                    if (++seen > 1200) { text.AppendLine("  文件过多，仅扫描前 1200 个文件名"); break; }
                    string name = Path.GetFileName(f);
                    string ext = Path.GetExtension(name).ToLowerInvariant();
                    if (!IsPossibleSpeech(name) && ext != ".vl" &&
                        ext != ".onnx" && ext != ".pyd" && ext != ".voice") continue;
                    if (++matched > MaxFilesPerDirectory) { text.AppendLine("  ...（更多文件名省略）"); break; }
                    text.AppendLine("  仅存在于目录：" + name + "；" + RedactPath(folder));
                }
            }
            catch (UnauthorizedAccessException) { text.AppendLine("  当前账户无权列出目录文件名"); }
            catch (IOException) { text.AppendLine("  目录无法列出或正被其他程序占用"); }
            return matched;
        }
    }
}
