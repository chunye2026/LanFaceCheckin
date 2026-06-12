import requests
r = requests.get('http://127.0.0.1:5000/api/dashboard/status')
d = r.json()
s = d['data']['stats']
alerts = d['data']['alerts']
print(f"server: OK")
print(f"model_available: {s['model_available']}")
print(f"members: {s['member_total']} (eligible: {s['eligible_count']})")
print(f"today_in: {s['today_checkin']}, today_out: {s['today_checkout']}")
print(f"threshold: {s['threshold']}")
print(f"alerts: {len(alerts)}")
for a in alerts: print(f"  - {a['msg']}")
