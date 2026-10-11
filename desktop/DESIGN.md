# 幻影工坊：桌面图片创作工作台

用户路径：两张图 → 原有 Rust CLI → 黑白真实对比 → 透明 PNG / ZIP，不需要命令行。桌面应用直接处理本机图片，不提供公共云解析服务或凭据接口。

复用已验收素材工坊 `lilyco-42/lilyco@81b5d52fd04f3029b01251ee04d18d0760fde0bb` 的独立 Jobs、受限 Workspaces、WebView2 生命周期、NSIS 文件白名单卸载和官方 shadcn 源组件。此提交是 public/main80e7e03 合并的 head。原 MIT 来源许可完整保存在 SHARED-SOURCE-LICENSE；这不是引用 Spine/AIC 引擎，也不提供复制的图像算法。

React 19 + Vite 静态构建，Tailwind 4 语义 OKLCH 色彩，官方 shadcn Base UI primitives 源文件不改，高级感来自留白、字体层级、有限的颜色和成果预览。FastAPI 管文件和任务，MirageAdapter 仅组装固定 CLI 参数；Rust 原 combine_images 是唯一合成实现，Android JNI 不变。

Windows 使用本机 WebView2，Linux 使用默认浏览器。FastAPI 随机 loopback 端口、HttpOnly/SameSiteStrict 临时会话、Origin/Host 检查；无任意 shell、远程地址抓取或上传脚本执行。未选择两张图不得生成，参数变化清除旧结果，生成失败保留输入供重试。取消/删除清理任务和临时文件。

图像像素/文件限制和错误回执由 CLI 验证，HTTP 再限制输入体积。渲染仅显示引擎输出，不用伪造的预览。黑白背景色是算法输出的展示条件，固定为真正黑/白；其余颜色全部语义 token。320/390/768/1440 尺寸、浅/深色、导出和原生安装/正常关闭在 Actions 真实验收。

后续再考虑将多个工具共用运行时正式抽成版本化 SDK；首批不另造插件协议。每个产品继续固定引擎、可核对来源和独立验收，不把只有 README 的仓库当成熟 CLI。
