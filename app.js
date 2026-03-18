/**
 * iPhone 视频/照片压缩工具 - 核心逻辑
 * 作用：处理文件选择、压缩计算、预览显示和下载
 */

// ========== 全局变量 ==========
let selectedFile;      // 用户选择的原始文件
let compressedBlob;    // 压缩后的文件 Blob

/**
 * 文件选择处理函数
 * @param {HTMLInputElement} input - 文件输入框元素
 * 当用户选择文件后触发，保存文件引用并立即显示原始预览
 */
function selectFile(input) {
    selectedFile = input.files[0];
    // 有文件时启用压缩按钮
    btn.disabled = !selectedFile;
    // 隐藏之前的预览和下载按钮
    preview.style.display = 'none';
    dlGroup.style.display = 'none';
    
    // 立即显示原始文件预览
    if (selectedFile) {
        showOriginalPreview();
    }
}

/**
 * 显示原始文件预览
 * 选择文件后立即展示，无需等待压缩
 */
function showOriginalPreview() {
    const url = URL.createObjectURL(selectedFile);
    const sizeMB = (selectedFile.size / 1024 / 1024).toFixed(2);
    
    // 显示对比区域，但只显示原始文件
    preview.style.display = 'grid';
    
    if (selectedFile.type.startsWith('image/')) {
        // 显示图片预览
        orig.innerHTML = `<img src="${url}">`;
    } else {
        // 显示视频预览
        orig.innerHTML = `<video src="${url}" controls muted loop></video>`;
    }
    origInfo.textContent = `${sizeMB}MB`;
    
    // 清空压缩后的预览区域，显示提示文字
    comp.innerHTML = `<p style="color:#999;padding:80px 0">点击"开始压缩"查看结果</p>`;
    compInfo.textContent = '等待压缩...';
}

/**
 * 主压缩函数
 * 根据文件类型调用对应的压缩方法
 */
function compress() {
    // 获取选中的压缩等级（0.7=低，0.5=中，0.3=高）
    const lv = parseFloat(document.querySelector('input[name="lv"]:checked').value);
    
    // 禁用按钮并显示加载状态
    btn.disabled = true;
    btn.textContent = '压缩中...';
    
    // 根据文件类型分流处理
    if (selectedFile.type.startsWith('image/')) {
        compressImage(lv);
    } else {
        compressVideo(lv);
    }
}

/**
 * 图片压缩函数
 * @param {number} lv - 压缩比例（0-1之间）
 * 使用 Canvas 重新绘制图片实现尺寸压缩
 */
function compressImage(lv) {
    const img = new Image();
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    // 图片加载完成后执行压缩
    img.onload = () => {
        // 按比例缩小画布尺寸
        canvas.width = img.width * lv;
        canvas.height = img.height * lv;
        
        // 将图片绘制到画布上（实现缩放）
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        
        // 将画布内容导出为 JPEG Blob（质量 0.9）
        canvas.toBlob(
            blob => showResult(blob, 'image'),
            'image/jpeg',
            0.9
        );
    };
    
    // 创建临时 URL 加载图片
    img.src = URL.createObjectURL(selectedFile);
    
    // 原始预览已在 selectFile 时显示，这里只更新尺寸信息
    origInfo.textContent = `${(selectedFile.size / 1024 / 1024).toFixed(2)}MB`;
}

/**
 * 视频压缩函数
 * @param {number} lv - 压缩比例（0-1之间）
 * 使用 Canvas + MediaRecorder 重新编码视频
 */
function compressVideo(lv) {
    const video = document.createElement('video');
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    let rec;
    let chunks = [];
    let progressInterval;
    
    // 设置视频属性：静音、行内播放（移动端需要）
    video.muted = true;
    video.playsInline = true;
    
    // 错误处理
    const handleError = (msg) => {
        clearInterval(progressInterval);
        compInfo.textContent = '压缩失败: ' + msg;
        btn.disabled = false;
        btn.textContent = '开始压缩';
        video.pause();
        if (rec && rec.state !== 'inactive') {
            try { rec.stop(); } catch (e) {}
        }
    };
    
    // 视频元数据加载完成后
    video.onloadeddata = () => {
        try {
            const duration = video.duration || 5;
            // 按比例缩小画布尺寸
            const w = Math.floor(video.videoWidth * lv);
            const h = Math.floor(video.videoHeight * lv);
            
            if (w <= 0 || h <= 0) {
                handleError('视频尺寸无效');
                return;
            }
            
            canvas.width = w;
            canvas.height = h;
            
            // 创建视频流录制器，使用较低比特率提高性能
            const stream = canvas.captureStream(30); // 限制30fps
            let mimeType = 'video/webm';
            if (!MediaRecorder.isTypeSupported(mimeType)) {
                mimeType = 'video/webm;codecs=vp9';
                if (!MediaRecorder.isTypeSupported(mimeType)) {
                    mimeType = '';
                }
            }
            
            const options = mimeType ? { mimeType, videoBitsPerSecond: 2500000 } : {};
            rec = new MediaRecorder(stream, options);
            
            // 收集录制的数据块
            rec.ondataavailable = e => {
                if (e.data && e.data.size > 0) {
                    chunks.push(e.data);
                }
            };
            
            // 录制停止后合并数据
            rec.onstop = () => {
                clearInterval(progressInterval);
                if (chunks.length === 0) {
                    handleError('录制数据为空');
                    return;
                }
                compressedBlob = new Blob(chunks, { type: 'video/webm' });
                showResult(compressedBlob, 'video');
            };
            
            rec.onerror = () => {
                handleError('录制器错误');
            };
            
            // 开始播放和录制
            video.play().catch(() => handleError('视频播放失败'));
            rec.start(1000); // 每1秒收集一次数据，减少开销
            
            // 显示进度
            const startTime = Date.now();
            progressInterval = setInterval(() => {
                const elapsed = (Date.now() - startTime) / 1000;
                const progress = Math.min((elapsed / duration) * 100, 99);
                compInfo.textContent = `压缩中... ${Math.floor(progress)}%`;
            }, 500);
            
            // 逐帧绘制视频到画布，使用 setTimeout 替代 requestAnimationFrame 降低 CPU 占用
            const draw = () => {
                if (video.paused || video.ended || rec.state === 'inactive') {
                    if (rec.state !== 'inactive') {
                        try { rec.stop(); } catch (e) {}
                    }
                    return;
                }
                ctx.drawImage(video, 0, 0, w, h);
                setTimeout(draw, 33); // 约30fps
            };
            draw();
            
            // 视频时长后自动停止（加1秒缓冲）
            setTimeout(() => {
                if (!video.paused) video.pause();
            }, (duration + 1) * 1000);
            
        } catch (err) {
            handleError(err.message);
        }
    };
    
    video.onerror = () => handleError('视频加载失败');
    
    // 创建临时 URL 加载视频
    video.src = URL.createObjectURL(selectedFile);
    
    // 原始预览已在 selectFile 时显示，这里只更新尺寸信息
    origInfo.textContent = `${(selectedFile.size / 1024 / 1024).toFixed(2)}MB`;
}

/**
 * 显示压缩结果
 * @param {Blob} blob - 压缩后的文件 Blob
 * @param {string} type - 文件类型（'image' 或 'video'）
 */
function showResult(blob, type) {
    compressedBlob = blob;
    
    // 显示对比区域
    preview.style.display = 'grid';
    
    // 创建压缩后文件的预览 URL
    const url = URL.createObjectURL(blob);
    
    // 根据类型显示图片或视频
    comp.innerHTML = type === 'image'
        ? `<img src="${url}">`
        : `<video src="${url}" controls muted loop autoplay></video>`;
    
    // 计算并显示压缩信息
    const saved = ((1 - blob.size / selectedFile.size) * 100).toFixed(0);
    compInfo.textContent = `${(blob.size / 1024 / 1024).toFixed(2)}MB (节省${saved}%)`;
    
    // 恢复按钮状态，显示下载按钮组
    btn.disabled = false;
    btn.textContent = '开始压缩';
    dlGroup.style.display = 'block';
}

/**
 * 下载原视频文件
 */
function downloadOriginal() {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(selectedFile);
    a.download = selectedFile.name;
    a.click();
}

/**
 * 下载压缩后的文件
 * 创建临时链接触发浏览器下载
 */
function download() {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(compressedBlob);
    
    // 生成下载文件名：compressed_原文件名.扩展名
    const ext = compressedBlob.type.includes('image') ? '.jpg' : '.webm';
    const name = selectedFile.name.replace(/\.[^.]+$/, '');
    a.download = 'compressed_' + name + ext;
    
    a.click();
}
