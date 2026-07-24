use mirage_tank::combine_images;
use std::env;
use std::process;

fn main() {
    let args: Vec<String> = env::args().collect();

    if args.len() < 4 {
        eprintln!(
            "用法: mirage-cli <隐藏图路径(黑背景下显示)> <表面图路径(白背景下显示)> <输出PNG路径>"
        );
        eprintln!("示例: mirage-cli hidden.jpg surface.jpg output.png");
        process::exit(1);
    }

    let hidden_path = &args[1];
    let surface_path = &args[2];
    let output_path = &args[3];

    println!("读取图片中...");
    let img_hidden = image::open(hidden_path).expect("无法打开隐藏图").to_luma8();

    let img_surface = image::open(surface_path)
        .expect("无法打开表面图")
        .to_luma8();

    if img_hidden.dimensions() != img_surface.dimensions() {
        eprintln!("错误: 两张图片的尺寸必须一致！");
        process::exit(1);
    }

    println!("正在合成幻影坦克图片...");
    let result = combine_images(&img_hidden, &img_surface);

    println!("正在保存至 {} ...", output_path);
    result.save(output_path).expect("保存图片失败");

    println!("合成完成！");
}
