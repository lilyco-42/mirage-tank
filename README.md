<p align="center">
  <img src="https://raw.githubusercontent.com/lilyco-42/mirage-tank/master/docs/logo.png" alt="mirage-tank" width="200">
</p>

<div align="center">
  <img src="docs/banner.svg" width="720" alt="banner">
</div>

# Mirage Tank (幻影坦克)

Create illusion images that show different content on different backgrounds — one image visible on dark backgrounds, another on light backgrounds.

## How It Works

The algorithm uses alpha blending to encode a "hidden" image and a "surface" image into a single PNG with transparency. On a **black background**, the hidden image is revealed; on a **white background**, the surface image appears.

```
result = foreground * alpha + background * (1 - alpha)
       ↳ hidden  image visible on dark  bg (alpha → 1)
       ↳ surface image visible on light bg (alpha → 0)
```

## Project Structure

```
rust/
├── demo/              # Rust library + CLI binary
│   ├── src/
│   │   ├── lib.rs     # Core algorithm + JNI exports for Android
│   │   ├── main.rs    # CLI entry point (old version)
│   │   └── demo-cli.rs# CLI binary "mirage-cli"
│   └── Cargo.toml
├── app/               # Android app (Jetpack Compose)
│   └── src/main/java/com/lilyco/timi/MainActivity.kt
├── build.gradle.kts   # Android Gradle build (root)
├── settings.gradle.kts
└── gradle.properties
```

## Usage

### CLI

```bash
# Two images must have the same dimensions
cargo run --bin demo-cli -- hidden.jpg surface.jpg output.png
```

### Android App

Open the `app/` directory in Android Studio, build and run. The app provides:
- Image picker for hidden & surface images
- Real-time preview with black/white background toggle
- Adjustable intensity sliders
- Save result to gallery (PNG encoded via Rust native library)

### Library

```rust
use mirage_tank::combine_images;

let result = combine_images(&hidden_gray_img, &surface_gray_img);
result.save("output.png").unwrap();
```

### HTTP Demo

```bash
cd http_demo
cargo run
# Server listens on http://0.0.0.0:8000
```

## Building for Android

Requires [cargo-ndk](https://github.com/bbqsrc/cargo-ndk) and Android NDK.

```bash
cargo install cargo-ndk
# Set ANDROID_NDK_HOME or configure ndk.dir in local.properties
```

The Gradle build automatically triggers `cargo ndk` to compile the Rust library into `app/src/main/jniLibs/`.

## License

MIT
