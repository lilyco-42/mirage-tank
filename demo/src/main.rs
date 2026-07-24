use demo::combine_images;
use image::imageops::FilterType;
use std::env;
use std::process;

fn main() {
    let args: Vec<String> = env::args().collect();

    if args.len() < 4 {
        eprintln!("用法: cargo run --bin demo-cli -- <隐藏图> <表面图> <输出路径>");
        process::exit(1);
    }

    let hidden_path = &args[1];
    let surface_path = &args[2];
    let output_path = &args[3];

    println!("读取图片中...");

    // 1. 读取隐藏图，并【大幅调暗】（亮度范围压缩到 0.0 ~ 0.4）
    let raw_hidden = image::open(hidden_path).expect("无法打开隐藏图").to_luma8();
    let (width, height) = raw_hidden.dimensions();

    let mut img_hidden = raw_hidden.clone();
    for pixel in img_hidden.pixels_mut() {
        // 将原本 0~255 的亮度缩放到 0~100 (保证隐藏图足够暗)
        pixel[0] = ((pixel[0] as f32 / 255.0) * 100.0) as u8;
    }

    // 2. 读取表面图，并【大幅调亮】（亮度范围拉高到 0.5 ~ 1.0）
    let raw_surface = image::open(surface_path).expect("无法打开表面图");
    let resized_surface =
        image::imageops::resize(&raw_surface.to_luma8(), width, height, FilterType::Triangle);

    let mut img_surface = resized_surface;
    for pixel in img_surface.pixels_mut() {
        // 将原本 0~255 的亮度平移映射到 128~255 (保证表面图足够亮)
        pixel[0] = 128 + ((pixel[0] as f32 / 255.0) * 127.0) as u8;
    }

    println!("正在合成...");
    let result = combine_images(&img_hidden, &img_surface);

    println!("正在保存至 {}...", output_path);
    result.save(output_path).expect("保存图片失败");

    println!("完成！图片已生成。");
}
