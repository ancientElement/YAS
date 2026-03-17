/**
 * iPhone 压缩工具 - Node.js 服务器
 * 作用：提供静态文件服务，部署 WebApp
 */

// 引入内置 http 模块和文件系统模块
const http = require('http');
const fs = require('fs');
const path = require('path');

// 配置
const PORT = 3000;  // 服务器端口
const ROOT = '.';   // 静态文件根目录

// MIME 类型映射表
const MIME_TYPES = {
    '.html': 'text/html',
    '.css': 'text/css',
    '.js': 'application/javascript',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.ico': 'image/x-icon',
    '.svg': 'image/svg+xml',
    '.json': 'application/json'
};

/**
 * 创建 HTTP 服务器
 */
const server = http.createServer((req, res) => {
    // 处理 URL，默认访问 index.html
    let filePath = req.url === '/' ? '/index.html' : req.url;
    filePath = path.join(ROOT, filePath);
    
    // 获取文件扩展名
    const ext = path.extname(filePath).toLowerCase();
    const contentType = MIME_TYPES[ext] || 'application/octet-stream';
    
    // 读取文件
    fs.readFile(filePath, (err, data) => {
        if (err) {
            // 文件不存在
            if (err.code === 'ENOENT') {
                res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
                res.end('404 页面不存在');
            } else {
                // 其他错误
                res.writeHead(500, { 'Content-Type': 'text/plain; charset=utf-8' });
                res.end('500 服务器错误');
            }
            return;
        }
        
        // 成功响应
        res.writeHead(200, { 
            'Content-Type': contentType,
            'Cache-Control': 'no-cache'  // 开发时禁用缓存
        });
        res.end(data);
    });
});

// 获取本机 IP 地址
function getLocalIP() {
  const interfaces = require('os').networkInterfaces();
  for (const name of Object.keys(interfaces)) {
    for (const iface of interfaces[name]) {
      if (iface.family === 'IPv4' && !iface.internal) {
        return iface.address;
      }
    }
  }
  return 'localhost';
}
const localIP = getLocalIP();

// 启动服务器
server.listen(PORT, () => {
    console.log('========================================');
    console.log('  iPhone 压缩工具已启动！');
    console.log('========================================');
    console.log(`\n请用浏览器访问以下地址之一：`);
    console.log(`  • http://${localIP}:${PORT}  (推荐，用于局域网访问)`);
    console.log(`  • http://localhost:${PORT}`);
    console.log('========================================');
    console.log('  按 Ctrl+C 停止服务器');
    console.log('========================================');
});
