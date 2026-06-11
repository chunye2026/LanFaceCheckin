from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import bcrypt

db = SQLAlchemy()


class Admin(db.Model):
    """管理员表"""
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.password_hash.encode('utf-8')
        )


class Member(db.Model):
    """成员表"""
    __tablename__ = 'members'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(100), default='')
    employee_id = db.Column(db.String(50), unique=True, nullable=False)
    phone = db.Column(db.String(20), default='')
    email = db.Column(db.String(100), default='')
    face_encoding = db.Column(db.Text, default='')  # 人脸特征编码（JSON字符串）
    face_image = db.Column(db.String(255), default='')  # 人脸照片路径
    status = db.Column(db.Integer, default=1)  # 1=正常, 0=禁用
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'department': self.department,
            'employee_id': self.employee_id,
            'phone': self.phone,
            'email': self.email,
            'status': self.status,
            'has_face': bool(self.face_encoding),
            'created_at': self.created_at.isoformat() if self.created_at else '',
            'updated_at': self.updated_at.isoformat() if self.updated_at else '',
        }


class CheckRecord(db.Model):
    """打卡记录表"""
    __tablename__ = 'check_records'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    member_name = db.Column(db.String(50), nullable=False)
    employee_id = db.Column(db.String(50), nullable=False)
    check_type = db.Column(db.String(10), nullable=False)  # 'in'=签到, 'out'=签退
    check_time = db.Column(db.DateTime, default=datetime.now)
    ip_address = db.Column(db.String(50), default='')
    confidence = db.Column(db.Float, default=0.0)  # 人脸识别置信度

    member = db.relationship('Member', backref=db.backref('records', cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            'id': self.id,
            'member_id': self.member_id,
            'member_name': self.member_name,
            'employee_id': self.employee_id,
            'check_type': self.check_type,
            'check_time': self.check_time.isoformat() if self.check_time else '',
            'ip_address': self.ip_address,
            'confidence': round(self.confidence, 4),
        }


class AuditLog(db.Model):
    """操作日志表（全留痕）"""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=True)
    admin_name = db.Column(db.String(50), default='')
    action = db.Column(db.String(50), nullable=False)  # 操作类型
    target_type = db.Column(db.String(50), default='')  # 操作对象类型
    target_id = db.Column(db.Integer, default=0)
    target_name = db.Column(db.String(100), default='')  # 操作对象名称
    detail = db.Column(db.Text, default='')  # 详细信息（JSON）
    ip_address = db.Column(db.String(50), default='')
    created_at = db.Column(db.DateTime, default=datetime.now)

    admin = db.relationship('Admin', backref='logs')

    def to_dict(self):
        return {
            'id': self.id,
            'admin_id': self.admin_id,
            'admin_name': self.admin_name,
            'action': self.action,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'target_name': self.target_name,
            'detail': self.detail,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat() if self.created_at else '',
        }
