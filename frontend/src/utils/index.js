/**
 * 共享工具函数
 */

export function formatTime(iso, full = false) {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = n => String(n).padStart(2, '0')
  if (full) {
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  }
  return `${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

export const REASON_LABELS = {
  cooldown_not_reached: '冷却中',
  already_checked_out: '已签退',
  confidence_too_low: '置信度不足',
  member_inactive: '成员已禁用',
  insufficient_face_samples: '人脸样本不足',
  liveness_failed: '活体检测失败',
  no_member_id: '无成员ID',
  unknown_rule: '未知规则',
  member_not_found: '成员不存在',
  invalid_check_type: '无效打卡类型',
}

export function reasonLabel(r) { return REASON_LABELS[r] || r || '-' }
