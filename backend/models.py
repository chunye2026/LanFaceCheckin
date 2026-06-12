"""
数据模型 - 人脸识别考勤系统
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import bcrypt
from flask import request, g

db = SQLAlchemy()


def write_operation_log(action, target_type='', target_id=0, target_name='', detail=''):
    """统一写操作日志"""
    try:
        log = OperationLog(
            admin_id=getattr(g, 'admin_id', None),
            admin_name=getattr(g, 'admin_name', ''),
            action=action, target_type=target_type, target_id=target_id,
            target_name=target_name, detail=detail,
            ip_address=request.remote_addr or ''
        )
        db.session.add(log)
        db.session.flush()
    except Exception:
        import logging
        logging.getLogger('app').exception('write_operation_log failed')


class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    must_change_password = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(
            password.encode('utf-8'), self.password_hash.encode('utf-8')
        )


class Member(db.Model):
    __tablename__ = 'members'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(100), default='')
    employee_id = db.Column(db.String(50), unique=True, nullable=False)
    phone = db.Column(db.String(20), default='')
    email = db.Column(db.String(100), default='')
    active = db.Column(db.Boolean, default=True)
    last_check_time = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    face_samples = db.relationship('FaceSample', backref='member', cascade='all, delete-orphan', lazy='dynamic')
    face_embeddings = db.relationship('FaceEmbedding', backref='member', cascade='all, delete-orphan', lazy='dynamic')

    @property
    def sample_count(self):
        return self.face_samples.count()

    @property
    def can_participate(self):
        from config import MIN_FACE_SAMPLES
        return self.active and self.sample_count >= MIN_FACE_SAMPLES

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'department': self.department,
            'employee_id': self.employee_id,
            'phone': self.phone,
            'email': self.email,
            'active': self.active,
            'sample_count': self.sample_count,
            'can_participate': self.can_participate,
            'last_check_time': self.last_check_time.isoformat() if self.last_check_time else '',
            'created_at': self.created_at.isoformat() if self.created_at else '',
            'updated_at': self.updated_at.isoformat() if self.updated_at else '',
        }


class FaceSample(db.Model):
    __tablename__ = 'face_samples'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    image_path = db.Column(db.String(255), default='')
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'member_id': self.member_id,
            'image_path': self.image_path,
            'created_at': self.created_at.isoformat() if self.created_at else '',
        }


class FaceEmbedding(db.Model):
    __tablename__ = 'face_embeddings'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    face_sample_id = db.Column(db.Integer, db.ForeignKey('face_samples.id'), nullable=True)
    embedding_json = db.Column(db.Text, nullable=False)  # JSON: 512-D float list
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'member_id': self.member_id,
            'face_sample_id': self.face_sample_id,
            'created_at': self.created_at.isoformat() if self.created_at else '',
        }


class CameraDevice(db.Model):
    __tablename__ = 'camera_devices'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), default='Default Camera')
    device_index = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='stopped')  # running / stopped / error
    last_frame_time = db.Column(db.DateTime, nullable=True)
    last_error = db.Column(db.Text, default='')
    fps = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'device_index': self.device_index,
            'status': self.status,
            'last_frame_time': self.last_frame_time.isoformat() if self.last_frame_time else '',
            'last_error': self.last_error,
            'fps': self.fps,
        }


class RecognitionEvent(db.Model):
    __tablename__ = 'recognition_events'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    camera_id = db.Column(db.Integer, default=0)
    matched = db.Column(db.Boolean, default=False)
    member_id = db.Column(db.Integer, nullable=True)
    member_name = db.Column(db.String(50), default='')
    confidence = db.Column(db.Float, default=0.0)
    distance = db.Column(db.Float, default=0.0)
    bbox = db.Column(db.String(100), default='')
    liveness_passed = db.Column(db.Boolean, nullable=True)
    liveness_score = db.Column(db.Float, default=0.0)
    liveness_reason = db.Column(db.String(200), default='')
    checkin_created = db.Column(db.Boolean, default=False)
    failure_reason = db.Column(db.String(200), default='')
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'camera_id': self.camera_id,
            'matched': self.matched,
            'member_id': self.member_id,
            'member_name': self.member_name,
            'confidence': self.confidence,
            'distance': self.distance,
            'bbox': self.bbox,
            'liveness_passed': self.liveness_passed,
            'liveness_score': self.liveness_score,
            'liveness_reason': self.liveness_reason,
            'checkin_created': self.checkin_created,
            'failure_reason': self.failure_reason,
            'created_at': self.created_at.isoformat() if self.created_at else '',
        }


class CheckinRecord(db.Model):
    __tablename__ = 'checkin_records'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    member_name = db.Column(db.String(50), nullable=False)
    employee_id = db.Column(db.String(50), nullable=False)
    check_type = db.Column(db.String(10), nullable=False)  # in / out
    check_time = db.Column(db.DateTime, default=datetime.now)
    confidence = db.Column(db.Float, default=0.0)
    camera_id = db.Column(db.Integer, default=0)
    source = db.Column(db.String(20), default='auto')  # auto / manual_admin
    recognition_event_id = db.Column(db.Integer, nullable=True)
    image_snapshot_path = db.Column(db.String(255), default='')
    created_at = db.Column(db.DateTime, default=datetime.now)

    member = db.relationship('Member', backref='records')

    __table_args__ = (
        db.Index('ix_checkin_member_time', 'member_id', 'check_time'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'member_id': self.member_id,
            'member_name': self.member_name,
            'employee_id': self.employee_id,
            'check_type': self.check_type,
            'check_time': self.check_time.isoformat() if self.check_time else '',
            'confidence': round(self.confidence, 4),
            'camera_id': self.camera_id,
            'source': self.source,
            'recognition_event_id': self.recognition_event_id,
            'created_at': self.created_at.isoformat() if self.created_at else '',
        }


class OperationLog(db.Model):
    __tablename__ = 'operation_logs'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    admin_id = db.Column(db.Integer, nullable=True)
    admin_name = db.Column(db.String(50), default='')
    action = db.Column(db.String(50), nullable=False)
    target_type = db.Column(db.String(50), default='')
    target_id = db.Column(db.Integer, default=0)
    target_name = db.Column(db.String(100), default='')
    detail = db.Column(db.Text, default='')
    ip_address = db.Column(db.String(50), default='')
    created_at = db.Column(db.DateTime, default=datetime.now)

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
