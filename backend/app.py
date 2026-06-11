"""
人脸识别考勤系统 - 后端入口
无感识别 + 管理员后台
"""
import os
import secrets
from flask import Flask, send_from_directory
from flask_cors import CORS
from models import db, Admin, CameraDevice
from config import (
    SECRET_KEY, DATABASE_URL, UPLOAD_FOLDER, CORS_ALLOWED_ORIGINS,
    FLASK_DEBUG, FLASK_HOST, FLASK_PORT, FLASK_USE_SSL,
    ADMIN_INIT_USERNAME, ADMIN_INIT_PASSWORD, BASE_DIR
)
from security import init_security, hash_password
from logger import app_logger

import camera_service as camera_service_mod



def create_app():
    app = Flask(__name__, static_folder='../frontend/dist', static_url_path='')
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    # CORS 白名单
    CORS(app, resources={r"/api/*": {"origins": CORS_ALLOWED_ORIGINS}})

    # 安全模块
    init_security(app.config)

    # 数据库
    db.init_app(app)

    # 注册路由
    from routes.admin import admin_bp
    app.register_blueprint(admin_bp)

    # 保留打卡记录公开查询（无需登录，供前端监控台使用）
    from models import CheckinRecord
    from flask import jsonify, request
    @app.route('/api/checkin/records', methods=['GET'])
    def public_records():
        today = request.args.get('today', '')
        q = CheckinRecord.query
        if today:
            q = q.filter(CheckinRecord.check_time >= f'{today} 00:00:00')
        records = q.order_by(CheckinRecord.check_time.desc()).limit(20).all()
        return jsonify({'code': 200, 'data': [r.to_dict() for r in records]})

    # 上传文件访问
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(UPLOAD_FOLDER, filename)

    # 前端 SPA
    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    @app.route('/<path:path>')
    def static_files(path):
        try:
            return app.send_static_file(path)
        except Exception:
            return app.send_static_file('index.html')

    # 初始化
    with app.app_context():
        db.create_all()
        camera_service_mod.init_app(app)
        _init_defaults()

    app_logger.info('Application created successfully')
    return app


def _init_defaults():
    """初始化默认数据（仅开发环境）"""
    if not Admin.query.filter_by(username=ADMIN_INIT_USERNAME).first():
        pw = ADMIN_INIT_PASSWORD
        if not pw:
            pw = secrets.token_urlsafe(8)
            print(f'[INIT] 管理员随机密码: {pw}')
        admin = Admin(username=ADMIN_INIT_USERNAME, must_change_password=(not ADMIN_INIT_PASSWORD))
        admin.set_password(pw)
        db.session.add(admin)
        db.session.commit()
        app_logger.info(f'Default admin created: {ADMIN_INIT_USERNAME}')

    if not CameraDevice.query.first():
        cam = CameraDevice(name='Default Camera', device_index=0)
        db.session.add(cam)
        db.session.commit()


if __name__ == '__main__':
    app = create_app()
    use_ssl = FLASK_USE_SSL
    cert_path = os.path.join(BASE_DIR, 'cert.pem')
    key_path = os.path.join(BASE_DIR, 'key.pem')
    if use_ssl and not (os.path.exists(cert_path) and os.path.exists(key_path)):
        use_ssl = False

    proto = 'https' if use_ssl else 'http'
    print('=' * 55)
    print('  人脸识别考勤系统')
    print(f'  管理员: {ADMIN_INIT_USERNAME}')
    print(f'  地址: {proto}://127.0.0.1:{FLASK_PORT}')
    print('=' * 55)

    if use_ssl:
        import ssl
        ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_ctx.load_cert_chain(cert_path, key_path)
        app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG, ssl_context=ssl_ctx)
    else:
        app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
