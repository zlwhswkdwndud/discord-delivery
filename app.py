from flask import Flask, render_template, request, jsonify
import requests
import os  # 환경 변수를 읽기 위해 필요
from datetime import datetime

app = Flask(__name__)

# --- [보안 적용] Render 설정(Environment Variables)에서 읽어옵니다 ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')
GUILD_ID = os.environ.get('GUILD_ID')
PUBLIC_WEBHOOK = os.environ.get('PUBLIC_WEBHOOK')
ADMIN_WEBHOOK = os.environ.get('ADMIN_WEBHOOK')

def get_discord_members():
    """서버 멤버 목록을 가져와서 이름순으로 정렬"""
    if not BOT_TOKEN or not GUILD_ID:
        return []
        
    url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/members?limit=1000"
    headers = {"Authorization": f"Bot {BOT_TOKEN}"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            members = response.json()
            # 봇은 제외하고 닉네임 또는 유저네임 추출
            member_list = [
                {"id": m['user']['id'], "name": m['nick'] or m['user']['username']} 
                for m in members if not m['user'].get('bot')
            ]
            return sorted(member_list, key=lambda x: x['name'])
        return []
    except Exception as e:
        print(f"멤버 로드 에러: {e}")
        return []

@app.route('/')
def index():
    members = get_discord_members()
    return render_template('index.html', members=members)

@app.route('/send', methods=['POST'])
def send_message():
    data = request.json
    u_id = data.get('userId')
    u_name = data.get('userName')
    s_name = data.get('senderName')  # 보낸 사람 실명
    msg = data.get('message')
    u_ip = request.headers.get('X-Forwarded-For', request.remote_addr) # Render 환경에서 IP 가져오기

    # 1. 일반 서버 전송 (익명 처리)
    if PUBLIC_WEBHOOK:
        requests.post(PUBLIC_WEBHOOK, json={
            "content": f"🔔 <@{u_id}>님, 익명 메시지가 도착했습니다!",
            "embeds": [{
                "description": msg,
                "color": 5814783,
                "footer": {"text": "작성자는 익명으로 보호됩니다."}
            }]
        })

    # 2. 관리자 전용 개인 서버 전송 (누가 보냈는지 기록)
    if ADMIN_WEBHOOK:
        requests.post(ADMIN_WEBHOOK, json={
            "embeds": [{
                "title": "🕵️ 실시간 전송 기록 (관리자 전용)",
                "color": 15548997,
                "fields": [
                    {"name": "작성자 (기입된 이름)", "value": f"**{s_name}**", "inline": True},
                    {"name": "수신 대상", "value": u_name, "inline": True},
                    {"name": "작성자 IP", "value": u_ip, "inline": True},
                    {"name": "메시지 내용", "value": msg}
                ],
                "timestamp": datetime.now().isoformat()
            }]
        })
    
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    # Render 환경에서는 포트 10000번을 주로 사용합니다.
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)