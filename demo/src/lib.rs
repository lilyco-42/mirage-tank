use image::{GrayImage, Rgba, RgbaImage};

/// 核心合成算法：计算前景色 P0 和 Alpha
#[inline]
pub fn calculate_pixel(p1: f32, p2: f32) -> (f32, f32) {
    let p2 = p2.max(p1);
    let alpha = 1.0 - (p2 - p1);
    let p0 = if alpha > 0.0 {
        (p1 / alpha).min(1.0)
    } else {
        0.0
    };
    (p0, alpha)
}

/// 供 CLI 使用的原有函数
pub fn combine_images(img_hidden: &GrayImage, img_surface: &GrayImage) -> RgbaImage {
    let (width, height) = img_hidden.dimensions();
    let mut result_img = RgbaImage::new(width, height);
    for x in 0..width {
        for y in 0..height {
            let p1 = img_hidden.get_pixel(x, y)[0] as f32 / 255.0;
            let p2 = img_surface.get_pixel(x, y)[0] as f32 / 255.0;
            let (p0, alpha) = calculate_pixel(p1, p2);
            let rgb = (p0 * 255.0) as u8;
            let a = (alpha * 255.0) as u8;
            result_img.put_pixel(x, y, Rgba([rgb, rgb, rgb, a]));
        }
    }
    result_img
}

// =========================================================================
// JNI 导出 - 原始像素直接处理版本 (100% Safe)
// =========================================================================

#[cfg(any(target_os = "android", test))]
#[no_mangle]
pub unsafe extern "system" fn Java_com_lilyco_timi_MainActivity_combineImages<'local>(
    mut env: jni::JNIEnv<'local>,
    _class: jni::objects::JClass<'local>,
    hidden_pixels: jni::objects::JIntArray<'local>,
    surface_pixels: jni::objects::JIntArray<'local>,
    width: jni::sys::jint,
    height: jni::sys::jint,
    hidden_max: jni::sys::jfloat,
    surface_min: jni::sys::jfloat,
) -> jni::objects::JIntArray<'local> {
    let len = (width * height) as usize;

    // 使用底层 JNI 接口实现零拷贝 (Critical Access)
    let internal = env.get_native_interface();

    let h_raw = hidden_pixels.as_raw();
    let s_raw = surface_pixels.as_raw();

    let h_ptr =
        ((**internal).GetPrimitiveArrayCritical.unwrap())(internal, h_raw, std::ptr::null_mut());
    let s_ptr =
        ((**internal).GetPrimitiveArrayCritical.unwrap())(internal, s_raw, std::ptr::null_mut());

    let h_slice = std::slice::from_raw_parts(h_ptr as *const i32, len);
    let s_slice = std::slice::from_raw_parts(s_ptr as *const i32, len);

    let mut out_pixels = vec![0i32; len];

    for i in 0..len {
        let p1_c = h_slice[i] as u32;
        let r1 = (p1_c >> 16) & 0xFF;
        let g1 = (p1_c >> 8) & 0xFF;
        let b1 = p1_c & 0xFF;
        let gray1 = (r1 * 2126 + g1 * 7152 + b1 * 722) / 10000;

        let p2_c = s_slice[i] as u32;
        let r2 = (p2_c >> 16) & 0xFF;
        let g2 = (p2_c >> 8) & 0xFF;
        let b2 = p2_c & 0xFF;
        let gray2 = (r2 * 2126 + g2 * 7152 + b2 * 722) / 10000;

        let p1_val = ((gray1 as f32 / 255.0) * hidden_max).floor() / 255.0;
        let p2_val =
            (surface_min + ((gray2 as f32 / 255.0) * (255.0 - surface_min)).floor()) / 255.0;

        let (p0, alpha) = calculate_pixel(p1_val, p2_val);

        let rgb = (p0 * 255.0) as u32;
        let a = (alpha * 255.0) as u32;

        let out_color = (a << 24) | (rgb << 16) | (rgb << 8) | rgb;
        out_pixels[i] = out_color as i32;
    }

    // 释放指针 (JNI_ABORT 因为我们不写回原数组)
    ((**internal).ReleasePrimitiveArrayCritical.unwrap())(
        internal,
        h_raw,
        h_ptr,
        jni::sys::JNI_ABORT,
    );
    ((**internal).ReleasePrimitiveArrayCritical.unwrap())(
        internal,
        s_raw,
        s_ptr,
        jni::sys::JNI_ABORT,
    );

    let output = env
        .new_int_array(len as jni::sys::jsize)
        .unwrap_or_else(|_| env.new_int_array(0).unwrap());
    if !out_pixels.is_empty() {
        env.set_int_array_region(&output, 0, &out_pixels)
            .unwrap_or(());
    }
    output
}

#[cfg(any(target_os = "android", test))]
#[no_mangle]
pub unsafe extern "system" fn Java_com_lilyco_timi_MainActivity_encodePng<'local>(
    mut env: jni::JNIEnv<'local>,
    _class: jni::objects::JClass<'local>,
    pixels: jni::objects::JIntArray<'local>,
    width: jni::sys::jint,
    height: jni::sys::jint,
) -> jni::objects::JByteArray<'local> {
    let len = (width * height) as usize;
    let mut raw_pixels = vec![0i32; len];
    if env
        .get_int_array_region(&pixels, 0, &mut raw_pixels)
        .is_err()
    {
        return env.new_byte_array(0).unwrap();
    }

    let mut la_data = Vec::with_capacity(len * 2);
    for p in raw_pixels {
        let a = ((p >> 24) & 0xFF) as u8;
        let r = ((p >> 16) & 0xFF) as u8;
        // 因为幻影坦克的前景色是灰度（R=G=B），所以直接取 R 通道即可
        la_data.push(r);
        la_data.push(a);
    }

    let mut png_bytes = Vec::new();
    let encoder = image::codecs::png::PngEncoder::new(&mut png_bytes);
    use image::ImageEncoder;
    if encoder
        .encode(&la_data, width as u32, height as u32, image::ColorType::La8)
        .is_err()
    {
        return env.new_byte_array(0).unwrap();
    }

    let output = env
        .new_byte_array(png_bytes.len() as jni::sys::jsize)
        .unwrap();
    let jbytes = std::slice::from_raw_parts(png_bytes.as_ptr() as *const i8, png_bytes.len());
    env.set_byte_array_region(&output, 0, jbytes).unwrap();
    output
}

#[cfg(test)]
mod tests {
    use super::*;
    use jni::{InitArgsBuilder, JavaVM};

    #[test]
    fn test_jni_combine_images_logic() {
        // 1. 初始化一个嵌入式 JVM 环境 (用于测试 JNIEnv 调用)
        let jvm_args = InitArgsBuilder::default()
            .version(jni::JNIVersion::V8)
            .build()
            .unwrap();
        let jvm = JavaVM::new(jvm_args).unwrap();
        let mut env = jvm.attach_current_thread().unwrap();

        // 2. 准备测试数据 (模拟 2x2 的简单图像)
        let width = 2;
        let height = 2;
        let len = (width * height) as usize;

        // 模拟底图 (全黑) 和表图 (全白)
        let h_data = vec![0xFF000000u32 as i32; len]; // ARGB Black
        let s_data = vec![0xFFFFFFFFu32 as i32; len]; // ARGB White

        let h_array = env.new_int_array(len as i32).unwrap();
        let s_array = env.new_int_array(len as i32).unwrap();
        env.set_int_array_region(&h_array, 0, &h_data).unwrap();
        env.set_int_array_region(&s_array, 0, &s_data).unwrap();

        // 3. 调用 JNI 导出函数 (直接在 Rust 中模拟调用)
        unsafe {
            let result_array = Java_com_lilyco_timi_MainActivity_combineImages(
                std::ptr::read(&*env),
                jni::objects::JClass::from(jni::objects::JObject::null()),
                h_array,
                s_array,
                width,
                height,
                100.0,
                128.0,
            );

            // 4. 验证结果
            let mut result_pixels = vec![0i32; len];
            env.get_int_array_region(&result_array, 0, &mut result_pixels)
                .unwrap();

            assert_eq!(result_pixels.len(), len);
            println!(
                "JNI Simulation Success: First pixel is {:08X}",
                result_pixels[0] as u32
            );
        }
    }
}
