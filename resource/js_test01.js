/**
 * utils.js
 * 常用工具函数示例
 */

// 格式化当前时间
function formatTime(date = new Date()) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  const h = String(date.getHours()).padStart(2, '0');
  const min = String(date.getMinutes()).padStart(2, '0');
  const s = String(date.getSeconds()).padStart(2, '0');
  return `${y}-${m}-${d} ${h}:${min}:${s}`;
}

// 数组去重
function uniqueArray(arr) {
  return [...new Set(arr)];
}

// 随机字符串
function randomString(length = 8) {
  const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let result = '';
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

// 导出（Node.js）
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    formatTime,
    uniqueArray,
    randomString
  };
}