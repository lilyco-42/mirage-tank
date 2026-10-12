<p align="center">
  <img src="https://raw.githubusercontent.com/lilyco-42/mirage-tank/master/docs/logo.png" alt="mirage-tank" width="200">
</p>

<div align="center">
  <img src="docs/banner.svg" width="720" alt="banner">
</div>

# Mirage Tank (幻影坦克)

Create illusion images that show different content on different backgrounds — one image visible on dark backgrounds, another on light backgrounds.

## Desktop studio · 无需命令行

`desktop/` 新增无需命令行的 Lain42 幻影工坊：两图选择、强度滑块、真实黑白背景对比、透明 PNG / ZIP 导出、取消和工作区删除。Windows WebView2 安装 EXE / 便携 ZIP，Linux 本机浏览器 ZIP。原 Android 应用和 Rust 核心算法保持不变。

[下载 Windows 安装 EXE / ZIP 或 Linux ZIP](https://github.com/lilyco-42/mirage-tank/releases/tag/mirage-studio-v0.1.1-1950c4205118)。完整包免费，解压后双击使用。Windows 需要 WebView2，安装器暂未签名；Linux 使用 Ubuntu 24.04+ x64 本机浏览器。所有编译、构建、测试及安装验收只在 [GitHub Actions](https://github.com/lilyco-42/mirage-tank/actions/runs/38277715186) 运行；不要求用户在本机编译。0.1.1 补齐独立 Windows SDK 的完整许可及官方文件核对。交付限制和运行说明见 [桌面说明](desktop/README.md)。

## How It Works

The algorithm uses alpha blending to encode a "hidden" image and a "surface" image into a single PNG with transparency. On a **black background**, the hidden image is revealed; on a **white background**, the surface image appears.

```
result = foreground * alpha + background * (1 - alpha)
       ↳ hidden  image visible on dark  bg (alpha → 1)
       ↳ surface image visible on light bg (alpha → 0)
```

## Project Structure

```
demo/                 # Rust library + actual demo-cli binary
├── src/lib.rs        # Original core algorithm + Android JNI
├── src/main.rs       # demo-cli; PNG/JPEG inputs, optional intensity
└── Cargo.toml
desktop/              # FastAPI + WebView2 + shadcn workspace
├── studio/           # Local API and fixed CLI adapter
├── ui/               # React / shadcn interface
├── packaging/        # GitHub Actions-only EXE / ZIP packaging
└── tests/            # Real engine, preview, install/uninstall evidence
app/                  # Original Android app (Jetpack Compose)
.github/workflows/desktop.yml
```

## Usage

### CLI

```bash
# The surface image is resized to the hidden image dimensions.
# Run the prebuilt binary; source builds are handled by GitHub Actions.
demo-cli hidden.jpg surface.jpg output.png
# Optional intensity values; the legacy 3-path invocation keeps its defaults.
demo-cli hidden.jpg surface.jpg output.png 100 128
```

### Android App

The original `app/` Android project remains independent of the desktop release. Its interface provides:
- Image picker for hidden & surface images
- Real-time preview with black/white background toggle
- Adjustable intensity sliders
- Save result to gallery (PNG encoded via Rust native library)

### Library

```rust
use demo::combine_images;

let result = combine_images(&hidden_gray_img, &surface_gray_img);
result.save("output.png").unwrap();
```

### Local desktop API

The desktop app starts FastAPI only on a random `127.0.0.1` port. Its temporary HttpOnly session protects file and task routes. No arbitrary shell endpoint or public file server is exposed. It uses the original `demo-cli` binary to generate the PNG.

## Building for Android

Requires [cargo-ndk](https://github.com/bbqsrc/cargo-ndk) and Android NDK.

```bash
cargo install cargo-ndk
# Set ANDROID_NDK_HOME or configure ndk.dir in local.properties
```

The Gradle build automatically triggers `cargo ndk` to compile the Rust library into `app/src/main/jniLibs/`.

## License

MIT
