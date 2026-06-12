import requests

# 1. Login
r = requests.post('http://127.0.0.1:5000/api/admin/login', json={'username':'admin','password':'admin123'})
d = r.json()
token = d['data']['token'] if d.get('code')==200 else None
print(f'1. Login: {r.status_code} ok={d["code"]==200}')

# 2. Dashboard
r = requests.get('http://127.0.0.1:5000/api/dashboard/status')
d = r.json()['data']
print(f'2. Dashboard: events={len(d.get("aggregated_events",[]))} records={len(d.get("recent_records",[]))}')

# 3. Members
r = requests.get('http://127.0.0.1:5000/api/admin/members', headers={'Authorization':f'Bearer {token}'})
print(f'3. Members: {len(r.json()["data"])}')

# 4. Camera
r = requests.get('http://127.0.0.1:5000/api/admin/camera/status')
print(f'4. Camera: running={r.json()["data"]["running"]}')

# 5. Events
r = requests.get('http://127.0.0.1:5000/api/admin/recognition-events?per_page=2', headers={'Authorization':f'Bearer {token}'})
print(f'5. Events: {r.json()["data"]["total"]}')

# 6. Records
r = requests.get('http://127.0.0.1:5000/api/admin/checkin-records?per_page=2', headers={'Authorization':f'Bearer {token}'})
print(f'6. Records: {r.json()["data"]["total"]}')

# 7. Logs
r = requests.get('http://127.0.0.1:5000/api/admin/operation-logs?per_page=2', headers={'Authorization':f'Bearer {token}'})
print(f'7. Logs: {r.json()["data"]["total"]}')

# 8. System
r = requests.get('http://127.0.0.1:5000/api/admin/system/status')
print(f'8. System: model={r.json()["data"]["model_available"]}')

# 9. Frontend
r = requests.get('http://127.0.0.1:5000/')
print(f'9. Frontend: html_len={len(r.text)}')

# 10. No auth
r = requests.get('http://127.0.0.1:5000/api/admin/members')
print(f'10. No auth: {r.status_code} (expect 401)')

print('\nAll checks done!')
