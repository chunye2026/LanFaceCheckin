"""
人脸识别局域网打卡系统 - 后端入口
"""
import os
import ssl
from flask import Flask, send_from_directory
from flask_cors import CORS
from models import db, Admin
from config import DATABASE_PATH, UPLOAD_FOLDER, DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD, SECRET_KEY, BASE_DIR
from routes.auth import auth_bp
from routes.member import member_bp
from routes.checkin import checkin_bp
from routes.log import log_bp


def create_app():
    app = Flask(__name__, static_folder='../frontend/dist', static_url_path='')

    # 配置
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_PATH}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 最大上传16MB

    # 初始化扩展
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)

    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(member_bp)
    app.register_blueprint(checkin_bp)
    app.register_blueprint(log_bp)

    # 上传文件访问
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(UPLOAD_FOLDER, filename)

    # 前端SPA路由（生产环境）
    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    @app.route('/<path:path>')
    def static_files(path):
        try:
            return app.send_static_file(path)
        except:
            return app.send_static_file('index.html')

    # 初始化数据库和默认管理员
    with app.app_context():
        db.create_all()

        # 创建默认管理员
        if not Admin.query.filter_by(username=DEFAULT_ADMIN_USERNAME).first():
            admin = Admin(username=DEFAULT_ADMIN_USERNAME)
            admin.set_password(DEFAULT_ADMIN_PASSWORD)
            db.session.add(admin)
            db.session.commit()
            print(f'[初始化] 默认管理员已创建: {DEFAULT_ADMIN_USERNAME} / {DEFAULT_ADMIN_PASSWORD}')

    return app


if __name__ == '__main__':
    app = create_app()

    # SSL 证书路径
    cert_path = os.path.join(BASE_DIR, 'cert.pem')
    key_path = os.path.join(BASE_DIR, 'key.pem')

    use_ssl = os.path.exists(cert_path) and os.path.exists(key_path)

    print('=' * 55)
    print('  人脸识别局域网打卡系统 - 后端服务')
    print(f'  默认管理员: admin / admin123')
    if use_ssl:
        print(f'  HTTPS 模式: https://127.0.0.1:5000')
        print('  提示: 自签名证书，浏览器会提示不安全，点击"继续访问"即可')
    else:
        print(f'  HTTP 模式: http://127.0.0.1:5000')
        print('  警告: 局域网IP访问时摄像头将无法使用，请用127.0.0.1访问')
    print('=' * 55)

    if use_ssl:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(cert_path, key_path)
        app.run(host='0.0.0.0', port=5000, debug=True, ssl_context=ssl_context)
    else:
        app.run(host='0.0.0.0', port=5000, debug=True)
