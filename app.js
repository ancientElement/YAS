let selectedFile;
let compressedBlob;
let compressedUrl;

function selectFile(input) {
    selectedFile = input.files[0];
    btn.disabled = !selectedFile;
    preview.style.display = 'none';
    dlGroup.style.display = 'none';

    if (selectedFile) {
        showOriginalPreview();
    }
}

function showOriginalPreview() {
    const url = URL.createObjectURL(selectedFile);
    const sizeMB = (selectedFile.size / 1024 / 1024).toFixed(2);

    preview.style.display = 'grid';
    orig.innerHTML = `<video src="${url}" controls muted></video>`;
    origInfo.textContent = `${sizeMB}MB`;
    comp.innerHTML = `<p style="color:#999;padding:60px 0">点击"开始压缩"</p>`;
    compInfo.textContent = '等待压缩...';
}

function updateProgress(type, percent, label) {
    const container = type === 'upload' ? uploadProgress : compressProgress;
    const fill = type === 'upload' ? uploadFill : compressFill;
    const percentEl = type === 'upload' ? uploadPercent : compressPercent;
    const labelEl = type === 'upload' ? uploadLabel : compressLabel;

    container.style.display = 'block';
    fill.style.width = percent + '%';
    percentEl.textContent = Math.round(percent) + '%';
    if (label) labelEl.textContent = label;
}

function hideProgress() {
    uploadProgress.style.display = 'none';
    compressProgress.style.display = 'none';
    uploadFill.style.width = '0%';
    compressFill.style.width = '0%';
}

async function compress() {
    if (!selectedFile) return;

    const quality = document.querySelector('input[name="lv"]:checked').value;

    btn.disabled = true;
    btn.textContent = '处理中...';
    hideProgress();

    try {
        // 使用 XMLHttpRequest 获取上传进度
        const compressedData = await new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();

            // 上传进度监听
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percent = (e.loaded / e.total) * 100;
                    updateProgress('upload', percent, '上传中...');
                }
            });

            xhr.upload.addEventListener('load', () => {
                updateProgress('upload', 100, '上传完成');
                // 开始模拟压缩进度
                let compressPercent = 0;
                xhr._compressInterval = setInterval(() => {
                    compressPercent += Math.random() * 8 + 2;
                    if (compressPercent >= 95) {
                        compressPercent = 95;
                        // 不在这里清除定时器，等待服务器响应
                    }
                    updateProgress('compress', compressPercent, '服务器压缩中...');
                }, 400);
            });

            xhr.addEventListener('load', () => {
                // 清除模拟进度定时器
                if (xhr._compressInterval) {
                    clearInterval(xhr._compressInterval);
                    xhr._compressInterval = null;
                }
                if (xhr.status === 200) {
                    updateProgress('compress', 100, '压缩完成 ✓');
                    setTimeout(() => resolve(xhr.response), 300);
                } else {
                    let errorMsg = '服务器错误';
                    try {
                        const err = JSON.parse(xhr.responseText);
                        errorMsg = err.error || errorMsg;
                    } catch { }
                    reject(new Error(errorMsg));
                }
            });

            xhr.addEventListener('error', () => reject(new Error('网络错误')));
            xhr.addEventListener('abort', () => reject(new Error('上传被取消')));

            xhr.open('POST', '/api/compress');
            xhr.responseType = 'blob';

            const formData = new FormData();
            formData.append('file', selectedFile);
            formData.append('quality', quality);
            xhr.send(formData);
        });

        hideProgress();

        // 使用已获取的数据
        compressedBlob = compressedData;
        const originalSize = selectedFile.size;
        const compressedSize = compressedData.size;

        // 显示结果
        compressedUrl = URL.createObjectURL(compressedBlob);
        comp.innerHTML = `<video src="${compressedUrl}" controls autoplay muted></video>`;

        const saved = ((1 - compressedSize / originalSize) * 100).toFixed(0);
        const sizeText = `${(compressedSize / 1024 / 1024).toFixed(2)}MB`;
        compInfo.textContent = saved > 0
            ? `${sizeText} (节省${saved}%)`
            : `${sizeText} (原文件已较小)`;

        dlGroup.style.display = 'block';

    } catch (err) {
        alert('压缩失败: ' + err.message);
        compInfo.textContent = '压缩失败';
        hideProgress();
    } finally {
        btn.disabled = false;
        btn.textContent = '开始压缩';
    }
}

function downloadOriginal() {
    if (!selectedFile) {
        alert('请选择文件');
        return;
    }
    const a = document.createElement('a');
    a.href = URL.createObjectURL(selectedFile);
    a.download = selectedFile.name;
    a.click();
}

function download() {
    if (!compressedBlob) return;
    const a = document.createElement('a');
    a.href = compressedUrl;
    const name = selectedFile.name.replace(/\.[^.]+$/, '');
    a.download = `compressed_${name}.mp4`;
    a.click();
}
