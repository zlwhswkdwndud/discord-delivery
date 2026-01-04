from flask import Flask, render_template, request, jsonify
import requests
import os
from datetime import datetime

app = Flask(__name__)

# --- [환경 변수 설정] Render 관리자 페이지(Environment)에서 입력하세요 ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')
GUILD_ID = os.environ.get('GUILD_ID')
PUBLIC_WEBHOOK = os.environ.get('PUBLIC_WEBHOOK')
ADMIN_WEBHOOK = os.environ.get('ADMIN_WEBHOOK')

def get_discord_members():
    """서버의 멤버 목록을 가져와서 정렬합니다."""
    if not BOT_TOKEN or not GUILD_ID:
        return []
        
    url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/members?limit=1000"
    headers = {"Authorization": f"Bot {BOT_TOKEN}"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            members = response.json()
            # 봇 제외, 닉네임 우선 추출
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
    s_name = data.get('senderName')
    msg = data.get('message')
    
    # Render에서 실제 사용자 IP를 가져오는 방식
    u_ip = request.headers.get('X-Forwarded-For', request.remote_addr)

    # 1. 일반 서버 전송 (디자인 강화 버전)
    if PUBLIC_WEBHOOK:
        payload = {
            "content": f"### 📬 <@{u_id}>님을 위한 비밀 편지가 도착했어요!",
            "embeds": [{
                "description": f"\n**“ {msg} ”**\n\n",
                "color": 0xFFD1DC,  # 화사한 벚꽃 핑크색
                "author": {
                    "name": "익명 마음 전달소",
                    "icon_url": "https://cdn-icons-png.flaticon.com/512/2190/2190552.png"
                },
                "footer": {
                    "text": "누군가 당신을 생각하며 보낸 따뜻한 메시지입니다.",
                    "icon_url": "https://cdn-icons-png.flaticon.com/512/1077/1077035.png"
                }
            }]
        }
        requests.post(PUBLIC_WEBHOOK, json=payload)

    # 2. 관리자 전용 기록 (누가 보냈는지 상세 리포트)
    if ADMIN_WEBHOOK:
        admin_payload = {
            "embeds": [{
                "title": "📑 실시간 전송 로그 (관리자 전용)",
                "color": 0x2b2d31,  # 디스코드 다크 모드 배경색
                "fields": [
                    {"name": "👤 작성자(기입명)", "value": f"**{s_name}**", "inline": True},
                    {"name": "🎯 수신 대상", "value": f"{u_name} (<@{u_id}>)", "inline": True},
                    {"name": "📝 내용", "value": f"``` {msg} ```"},
                    {"name": "🌐 접속 정보(IP)", "value": f"`{u_ip}`"}
                ],
                "timestamp": datetime.now().isoformat()
            }]
        }
        requests.post(ADMIN_WEBHOOK, json=admin_payload)
    
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    # Render 환경에서 자동으로 포트를 할당받습니다.
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
