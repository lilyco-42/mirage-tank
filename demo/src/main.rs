use demo::combine_images;
use image::{imageops::FilterType, io::Reader, DynamicImage, ImageFormat};
use std::{env, path::Path, process};

fn read_image(path: &str) -> Result<DynamicImage, String> {
    let meta = std::fs::metadata(path).map_err(|e| format!("无法读取图片: {e}"))?;
    if !meta.is_file() || meta.len() > 16 * 1024 * 1024 {
        return Err("请选择不超过 16 MB 的 PNG / JPEG 图片".into());
    }
    let (width, height) = image::image_dimensions(path).map_err(|e| format!("图片无效: {e}"))?;
    if width == 0 || height == 0 || width > 8192 || height > 8192
        || u64::from(width) * u64::from(height) > 16_000_000 {
        return Err("图片最多 1600 万像素，单边最多 8192 像素".into());
    }
    let mut reader = Reader::open(path).map_err(|e| e.to_string())?
        .with_guessed_format().map_err(|e| e.to_string())?;
    if !matches!(reader.format(), Some(ImageFormat::Png | ImageFormat::Jpeg)) {
        return Err("仅支持 PNG / JPEG 图片".into());
    }
    let mut limits = image::io::Limits::default();
    limits.max_image_width = Some(8192);
    limits.max_image_height = Some(8192);
    limits.max_alloc = Some(192 * 1024 * 1024);
    reader.limits(limits);
    reader.decode().map_err(|e| format!("图片解码失败: {e}"))
}

fn run(args: &[String]) -> Result<(), String> {
    if args.len() != 4 && args.len() != 6 {
        return Err("用法: demo-cli <隐藏图> <表面图> <输出.png> [隐藏强度1-127 白底起点128-255]".into());
    }
    let hidden_max = if args.len() == 6 { args[4].parse::<u8>().map_err(|_| "隐藏强度必须为整数")? } else { 100 };
    let surface_min = if args.len() == 6 { args[5].parse::<u8>().map_err(|_| "白底起点必须为整数")? } else { 128 };
    if !(1..=127).contains(&hidden_max) || surface_min < 128 {
        return Err("隐藏强度须为1-127，白底起点须为128-255".into());
    }
    if Path::new(&args[3]).extension().and_then(|s| s.to_str()).map(str::to_ascii_lowercase).as_deref() != Some("png") {
        return Err("请保存为 PNG，以保留透明通道".into());
    }
    let mut hidden = read_image(&args[1])?.to_luma8();
    let surface = read_image(&args[2])?.to_luma8();
    let (width, height) = hidden.dimensions();
    for pixel in hidden.pixels_mut() {
        pixel[0] = ((pixel[0] as f32 / 255.0) * f32::from(hidden_max)) as u8;
    }
    let mut surface = image::imageops::resize(&surface, width, height, FilterType::Triangle);
    for pixel in surface.pixels_mut() {
        pixel[0] = surface_min + ((pixel[0] as f32 / 255.0) * f32::from(255 - surface_min)) as u8;
    }
    // Keep the original core algorithm and Android JNI implementation intact.
    let result = combine_images(&hidden, &surface);
    result.save(&args[3]).map_err(|e| format!("保存图片失败: {e}"))?;
    println!("已生成 {width} × {height} 透明 PNG");
    Ok(())
}

fn main() {
    if let Err(error) = run(&env::args().collect::<Vec<_>>()) {
        eprintln!("{error}");
        process::exit(1);
    }
}
