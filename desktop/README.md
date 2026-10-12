# Lain42 幻影工坊

Windows 双击 `Lain42-Mirage-Studio.exe`，打开 WebView2 工作台。Linux 双击同名程序，在默认浏览器打开本机页面；保存作品后关闭启动窗口。

1. 选择隐藏图（黑底可见）和表面图（白底可见），支持 PNG / JPEG。
2. 调整强度，点击“合成并预览”，对比真实黑白背景和透明原图。
3. 保存透明 PNG，或下载包含 PNG 和处理参数的 ZIP。

所有处理在本机，不上传云端，不需要账号、模型或额外安装 Python / Rust。灰度幻影效果，表面图自动缩放到隐藏图尺寸；单张最多 16 MB、1600 万像素，单边最多 8192 像素。

必须保留透明 PNG；截图或转存 JPEG 会破坏背景切换效果。关闭窗口清理临时素材，已下载作品不删除。Linux 浏览器模式须关闭启动窗口结束服务。

首发 Windows 10/11 x64（需要 Microsoft WebView2 Runtime）和 Ubuntu 24.04+ x64。安装 EXE 尚未代码签名，可能显示未知发布者，请使用正式 Release 并核对 SHA256。不宣称支持 macOS / 手机安装包；原有 Android 项目保持独立。

所有产品构建、测试与安装验收仅在 GitHub Actions；本机不编译。包含 Rust CLI、完整界面、Python 运行时、来源版本、依赖声明与 MIT 许可。

桌面封装 0.1.1 补齐 Windows 所带 Microsoft.Web.WebView2 SDK 1.0.3856.49 的独立 BSD-3-Clause 署名。
`MICROSOFT-WEBVIEW2-LICENSE.txt` 保留官方完整文本，`webview2-sdk.json` 记录官方包和五个 SDK 文件的 SHA256；
Actions 对照官方 NuGet 包核验安装依赖与最终冻结包中的文件，再将许可纳入便携 ZIP 和安装 EXE。
SDK 与 WebView2 Runtime 是不同组件；本安装包不附带 Runtime，仍需 Microsoft 官方运行时。
官方 SDK 来源：https://www.nuget.org/packages/Microsoft.Web.WebView2/1.0.3856.49 。
