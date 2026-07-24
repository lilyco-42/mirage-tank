package com.lilyco.timi

import android.content.ContentValues
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Rect
import android.net.Uri
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import com.lilyco.timi.ui.theme.TimiTheme
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.window.Dialog
import androidx.core.graphics.createBitmap

class MainActivity : ComponentActivity() {

    companion object {
        init {
            System.loadLibrary("demo")
        }
    }

    private external fun combineImages(
        hidden: IntArray,
        surface: IntArray,
        width: Int,
        height: Int,
        hiddenMax: Float,
        surfaceMin: Float,
    ): IntArray

    private external fun encodePng(
        pixels: IntArray,
        width: Int,
        height: Int,
    ): ByteArray

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            TimiTheme {
                Scaffold(modifier = Modifier.fillMaxSize()) { innerPadding ->
                    MainScreen(modifier = Modifier.padding(innerPadding))
                }
            }
        }
    }

    data class SynthesisResult(
        val previewBitmap: Bitmap,
        val rawPixels: IntArray,
        val width: Int,
        val height: Int
    )

    @OptIn(ExperimentalMaterial3Api::class)
    @Composable
    fun MainScreen(modifier: Modifier = Modifier) {
        val context = androidx.compose.ui.platform.LocalContext.current
        var hiddenUri by remember { mutableStateOf<Uri?>(null) }
        var surfaceUri by remember { mutableStateOf<Uri?>(null) }
        var hiddenMax by remember { mutableFloatStateOf(80f) }
        var surfaceMin by remember { mutableFloatStateOf(150f) }
        var synthesisResult by remember { mutableStateOf<SynthesisResult?>(null) }
        var previewBgColor by remember { mutableIntStateOf(Color.WHITE) }
        var status by remember { mutableStateOf("请选择两张图片进行合成") }
        var showSponsorDialog by remember { mutableStateOf(false) }
        val scope = rememberCoroutineScope()
        val drawerState = rememberDrawerState(initialValue = DrawerValue.Closed)

        val hiddenPicker = rememberLauncherForActivityResult(
            contract = ActivityResultContracts.PickVisualMedia(),
        ) { uri -> hiddenUri = uri }

        val surfacePicker = rememberLauncherForActivityResult(
            contract = ActivityResultContracts.PickVisualMedia(),
        ) { uri -> surfaceUri = uri }

        // 实时预览逻辑
        LaunchedEffect(hiddenUri, surfaceUri, hiddenMax, surfaceMin) {
            if ((hiddenUri != null) && (surfaceUri != null)) {
                val result = processImages(hiddenUri!!, surfaceUri!!, hiddenMax, surfaceMin)
                if (result != null) {
                    synthesisResult?.previewBitmap?.recycle() // 回收旧预览图
                    synthesisResult = result
                    status = "合成成功！"
                }
            }
        }

        if (showSponsorDialog) {
            SponsorDialog(onDismiss = { showSponsorDialog = false })
        }

        ModalNavigationDrawer(
            drawerState = drawerState,
            drawerContent = {
                ModalDrawerSheet {
                    Spacer(Modifier.height(12.dp))
                    Text(
                        "Timi 幻影坦克",
                        modifier = Modifier.padding(16.dp),
                        style = MaterialTheme.typography.titleLarge
                    )
                    Divider(Modifier.padding(vertical = 8.dp))
                    NavigationDrawerItem(
                        label = { Text("赞助作者") },
                        selected = false,
                        icon = { Icon(Icons.Default.Favorite, contentDescription = null, tint = Color.Red) },
                        onClick = {
                            scope.launch { drawerState.close() }
                            showSponsorDialog = true
                        },
                        modifier = Modifier.padding(NavigationDrawerItemDefaults.ItemPadding)
                    )
                }
            }
        ) {
            Scaffold(
                topBar = {
                    TopAppBar(
                        title = { Text("Timi") },
                        navigationIcon = {
                            IconButton(onClick = { scope.launch { drawerState.open() } }) {
                                Icon(Icons.Default.Menu, contentDescription = "菜单")
                            }
                        }
                    )
                },
                modifier = Modifier.fillMaxSize()
            ) { innerPadding ->
                Column(
                    modifier = Modifier
                        .padding(innerPadding)
                        .fillMaxSize()
                        .padding(16.dp)
                        .verticalScroll(rememberScrollState()),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Top
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceEvenly
                    ) {
                        ImageSelector(
                            uri = hiddenUri,
                            label = "底图 (Hidden)",
                            onClick = {
                                hiddenPicker.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
                            }
                        )
                        ImageSelector(
                            uri = surfaceUri,
                            label = "表图 (Surface)",
                            onClick = {
                                surfacePicker.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
                            }
                        )
                    }

                    Spacer(modifier = Modifier.height(24.dp))

                    // 高级设置区域
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)),
                    ) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Text("高级设置 (遮挡程度)", style = MaterialTheme.typography.titleSmall)
                            
                            Text("底图强度 (Hidden Max): ${hiddenMax.toInt()}", style = MaterialTheme.typography.labelSmall)
                            Slider(value = hiddenMax, onValueChange = { hiddenMax = it }, valueRange = 0f..255f)
                            
                            Text("表图亮度 (Surface Min): ${surfaceMin.toInt()}", style = MaterialTheme.typography.labelSmall)
                            Slider(value = surfaceMin, onValueChange = { surfaceMin = it }, valueRange = 0f..255f)
                        }
                    }

                    Spacer(modifier = Modifier.height(20.dp))
                    Text(text = status, style = MaterialTheme.typography.bodyMedium)
                    Spacer(modifier = Modifier.height(20.dp))

                    synthesisResult?.let { result ->
                        Text("预览模式 (点击色块切换背景):", style = MaterialTheme.typography.labelSmall)
                        Row(modifier = Modifier.padding(8.dp)) {
                            Box(modifier = Modifier.size(30.dp).clip(CircleShape).background(androidx.compose.ui.graphics.Color.White).clickable { previewBgColor = Color.WHITE })
                            Spacer(modifier = Modifier.width(16.dp))
                            Box(modifier = Modifier.size(30.dp).clip(CircleShape).background(androidx.compose.ui.graphics.Color.Black).clickable { previewBgColor = Color.BLACK })
                        }
                        
                        Card(
                            elevation = CardDefaults.cardElevation(defaultElevation = 4.dp),
                            colors = CardDefaults.cardColors(containerColor = androidx.compose.ui.graphics.Color(previewBgColor))
                        ) {
                            Image(
                                bitmap = result.previewBitmap.asImageBitmap(),
                                contentDescription = "合成结果",
                                modifier = Modifier.size(300.dp)
                            )
                        }
                        Spacer(modifier = Modifier.height(16.dp))
                        Button(
                            onClick = {
                                scope.launch {
                                    val success = saveImageToGallery(result.rawPixels, result.width, result.height)
                                    if (success) {
                                        Toast.makeText(context, "图片已保存至相册", Toast.LENGTH_SHORT).show()
                                    } else {
                                        Toast.makeText(context, "保存失败", Toast.LENGTH_SHORT).show()
                                    }
                                }
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary)
                        ) {
                            Text("保存图片到相册")
                        }
                    }
                }
            }
        }
    }

    @Composable
    fun SponsorDialog(onDismiss: () -> Unit) {
        Dialog(onDismissRequest = onDismiss) {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                shape = MaterialTheme.shapes.extraLarge,
            ) {
                Column(
                    modifier = Modifier.padding(24.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text("赞助支持", style = MaterialTheme.typography.headlineSmall)
                    Spacer(Modifier.height(8.dp))
                    Text("如果觉得好用，可以请作者喝杯咖啡哦~", style = MaterialTheme.typography.bodyMedium)
                    Spacer(Modifier.height(24.dp))
                    
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Image(
                                painter = painterResource(id = R.drawable.alipay),
                                contentDescription = "支付宝",
                                modifier = Modifier.size(120.dp).clip(MaterialTheme.shapes.medium)
                            )
                            Spacer(Modifier.height(8.dp))
                            Text("支付宝", style = MaterialTheme.typography.labelSmall)
                        }
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Image(
                                painter = painterResource(id = R.drawable.wechatpay),
                                contentDescription = "微信支付",
                                modifier = Modifier.size(120.dp).clip(MaterialTheme.shapes.medium)
                            )
                            Spacer(Modifier.height(8.dp))
                            Text("微信支付", style = MaterialTheme.typography.labelSmall)
                        }
                    }
                    
                    Spacer(Modifier.height(24.dp))
                    TextButton(onClick = onDismiss) {
                        Text("关闭")
                    }
                }
            }
        }
    }

    private suspend fun saveImageToGallery(pixels: IntArray, width: Int, height: Int): Boolean = withContext(Dispatchers.IO) {
        try {
            // 调用 Rust 侧的 PNG 编码器，避开 Android Bitmap 的预乘 Alpha 处理
            val pngBytes = encodePng(pixels, width, height)
            if (pngBytes.isEmpty()) return@withContext false

            val filename = "Timi_${System.currentTimeMillis()}.png"
            val contentValues = ContentValues().apply {
                put(MediaStore.MediaColumns.DISPLAY_NAME, filename)
                put(MediaStore.MediaColumns.MIME_TYPE, "image/png")
                put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/Timi")
            }

            val uri = contentResolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, contentValues)
            val success = uri?.let {
                contentResolver.openOutputStream(it)?.use { outputStream ->
                    outputStream.write(pngBytes)
                }
                true
            } ?: false
            success
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }

    @Composable
    fun ImageSelector(uri: Uri?, label: String, onClick: () -> Unit) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(text = label, style = MaterialTheme.typography.labelMedium)
            Spacer(modifier = Modifier.height(8.dp))
            OutlinedButton(
                onClick = onClick,
                modifier = Modifier.size(120.dp),
                shape = MaterialTheme.shapes.medium,
                contentPadding = PaddingValues(0.dp)
            ) {
                if (uri != null) {
                    val bitmap = remember(uri) {
                        val inputStream = contentResolver.openInputStream(uri)
                        BitmapFactory.decodeStream(inputStream)
                    }
                    bitmap?.let {
                        Image(
                            bitmap = it.asImageBitmap(),
                            contentDescription = null,
                            modifier = Modifier.fillMaxSize(),
                            contentScale = ContentScale.Crop
                        )
                    }
                } else {
                    Text("选择图片", style = MaterialTheme.typography.bodySmall)
                }
            }
        }
    }

    private suspend fun processImages(
        hiddenUri: Uri,
        surfaceUri: Uri,
        hiddenMax: Float,
        surfaceMin: Float
    ): SynthesisResult? = withContext(Dispatchers.IO) {
        try {
            val maxSide = 800 // 进一步缩小尺寸以节省内存
            val hiddenBmp = decodeUriWithLimit(hiddenUri, maxSide) ?: return@withContext null
            val surfaceBmp = decodeUriWithLimit(surfaceUri, maxSide) ?: return@withContext null

            val targetWidth = maxOf(hiddenBmp.width, surfaceBmp.width)
            val targetHeight = maxOf(hiddenBmp.height, surfaceBmp.height)

            fun getCenterCroppedBitmap(src: Bitmap, width: Int, height: Int): Bitmap {
                val dstBmp = createBitmap(width, height, Bitmap.Config.ARGB_8888)
                val canvas = Canvas(dstBmp)
                val srcWidth = src.width
                val srcHeight = src.height
                val srcRatio = srcWidth.toFloat() / srcHeight
                val dstRatio = width.toFloat() / height
                val srcRect = if (srcRatio > dstRatio) {
                    val newSrcWidth = (srcHeight * dstRatio).toInt()
                    val offset = (srcWidth - newSrcWidth) / 2
                    Rect(offset, 0, offset + newSrcWidth, srcHeight)
                } else {
                    val newSrcHeight = (srcWidth / dstRatio).toInt()
                    val offset = (srcHeight - newSrcHeight) / 2
                    Rect(0, offset, srcWidth, offset + newSrcHeight)
                }
                canvas.drawBitmap(src, srcRect, Rect(0, 0, width, height), null)
                return dstBmp
            }

            val finalHidden = getCenterCroppedBitmap(hiddenBmp, targetWidth, targetHeight)
            val finalSurface = getCenterCroppedBitmap(surfaceBmp, targetWidth, targetHeight)

            val len = targetWidth * targetHeight
            val hiddenPixels = IntArray(len)
            val surfacePixels = IntArray(len)

            finalHidden.getPixels(hiddenPixels, 0, targetWidth, 0, 0, targetWidth, targetHeight)
            finalSurface.getPixels(surfacePixels, 0, targetWidth, 0, 0, targetWidth, targetHeight)

            val resultPixels = combineImages(hiddenPixels, surfacePixels, targetWidth, targetHeight, hiddenMax, surfaceMin)

            // 及时回收不再使用的位图
            if (finalHidden != hiddenBmp) finalHidden.recycle()
            if (finalSurface != surfaceBmp) finalSurface.recycle()
            hiddenBmp.recycle()
            surfaceBmp.recycle()

            if (resultPixels.isNotEmpty()) {
                val previewBmp = createBitmap(targetWidth, targetHeight)
                // 默认 isPremultiplied = true，UI 绘制必须使用预乘位图
                previewBmp.setPixels(resultPixels, 0, targetWidth, 0, 0, targetWidth, targetHeight)
                SynthesisResult(previewBmp, resultPixels, targetWidth, targetHeight)
            } else null
        } catch (e: OutOfMemoryError) {
            e.printStackTrace()
            null
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    private fun decodeUriWithLimit(uri: Uri, maxSide: Int): Bitmap? {
        return try {
            val options = BitmapFactory.Options().apply {
                inJustDecodeBounds = true
            }
            contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, options) }

            val width = options.outWidth
            val height = options.outHeight
            if (width <= 0 || height <= 0) return null

            var inSampleSize = 1
            while (width / inSampleSize > maxSide || height / inSampleSize > maxSide) {
                inSampleSize *= 2
            }

            val finalOptions = BitmapFactory.Options().apply {
                this.inSampleSize = inSampleSize
                inPreferredConfig = Bitmap.Config.ARGB_8888
            }
            contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, finalOptions) }
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }
}
