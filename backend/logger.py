"""
统一日志模块
替换所有裸 except: pass，强制异常记录到日志文件
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from config import BASE_DIR

LOG_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

_formatter = logging.Formatter(
    '[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def _make_handler(filename, level=logging.DEBUG):
    path = os.path.join(LOG_DIR, filename)
    h = RotatingFileHandler(path, maxBytes=5 * 1024 * 1024, backupCount=5, encoding='utf-8')
    h.setLevel(level)
    h.setFormatter(_formatter)
    return h

def get_logger(name):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        logger.addHandler(_make_handler('app.log'))
        # 同时输出到控制台
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(_formatter)
        logger.addHandler(console)
    return logger

# 专用日志器
app_logger = get_logger('app')
recognition_logger = get_logger('recognition')
security_logger = get_logger('security')

# 为 recognition 和 security 增加专用文件
for _log, _file in [(recognition_logger, 'recognition.log'), (security_logger, 'security.log')]:
    if not any(isinstance(h, RotatingFileHandler) and _file in h.baseFilename for h in _log.handlers):
        _log.addHandler(_make_handler(_file))
