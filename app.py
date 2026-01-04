from flask import Flask, render_template, request, jsonify
import requests
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import io

app = Flask(__name__)

# --- [환경 변수] Render에서 설정 필수 ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')
GUILD_ID = os.environ.get('GUILD_ID')
PUBLIC_WEBHOOK = os.environ.get('PUBLIC_WEBHOOK')
ADMIN_WEBHOOK = os.environ.get('ADMIN_WEBHOOK')

def get_discord_members():
    if not BOT_TOKEN or not GUILD_ID: return []
    url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/members?limit=1000"
    headers = {"Authorization": f"Bot {BOT_TOKEN}"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            members = response.json()
            member_list = [{"id": m['user']['id'], "name": m['nick'] or m['user']['username']} for m in members if not m['user'].get('bot')]
            return sorted(member_list, key=lambda x: x['name'])
        return []
    except: return []

def create_card_image(receiver_name, message_text):
    try:
        bg_path = 'background.png'   # 1200x800 크리스마스 이미지
        font_path = 'Myfont.ttf'     # 업로드하신 폰트 파일명
        
        if not os.path.exists(bg_path) or not os.path.exists(font_path):
            return None

        img = Image.open(bg_path).convert("RGBA")
        draw = ImageDraw.Draw(img)
        
        # --- [설정: 16PT 느낌 및 중앙 정렬] ---
        to_font = ImageFont.truetype(font_path, 30)   # TO. 이름
        msg_font = ImageFont.truetype(font_path, 22)  # 본문 (16PT 느낌)
        text_color = (40, 20, 20) # 진한 밤색
        
        top_limit = 200    # 상단 여백
        side_margin = 180  # 좌우 여백
        bottom_limit = img.height - 230 # 펭귄 보호 구역
        
        # 1. TO. [이름] 중앙 정렬
        to_text = f"TO. {receiver_name}"
        to_w = draw.textbbox((0, 0), to_text, font=to_font)[2] - draw.textbbox((0, 0), to_text, font=to_font)[0]
        draw.text(((img.width - to_w) / 2, top_limit), to_text, font=to_font, fill=text_color)
        
        # 2. 본문 줄바꿈 및 중앙 정렬
        content_max_width = img.width - (side_margin * 2)
        y_cursor = top_limit + 70 
        
        lines = []
        current_line = ""
        for char in message_text:
            test_line = current_line + char
            w = draw.textbbox((0, 0), test_line, font=msg_font)[2]
            if w <= content_max_width:
                current_line = test_line
            else:
                lines.append(current_line.strip())
                current_line = char
        lines.append(current_line.strip())

        line_height = 38 
        for line in lines:
            if y_cursor > bottom_limit: break
            line_w = draw.textbbox((0, 0), line, font=msg_font)[2] - draw.textbbox((0, 0), line, font=msg_font)[0]
            draw.text(((img.width - line_w) / 2, y_cursor), line, font=msg_font, fill=text_color)
            y_cursor += line_height

        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        return img_io
    except Exception as e:
        print(f"이미지 생성 에러: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html', members=get_discord_members())

@app.route('/send', methods=['POST'])
def send_message():
    data = request.json
    u_id, u_name, msg = data.get('userId'), data.get('userName'), data.get('message')
    s_name = data.get('senderName')
    u_ip = request.headers.get('X-Forwarded-For', request.remote_addr)

    card_img = create_card_image(u_name, msg)

    if PUBLIC_WEBHOOK:
        if card_img:
            files = {'file': ('card.png', card_img, 'image/png')}
            payload = {"content": f"💌 <@{u_id}>님께 익명의 크리스마스 편지가 도착했어요!"}
            requests.post(PUBLIC_WEBHOOK, data=payload, files=files)
        else:
            requests.post(PUBLIC_WEBHOOK, json={"content": f"💌 <@{u_id}>: {msg}"})

    if ADMIN_WEBHOOK:
        requests.post(ADMIN_WEBHOOK, json={"content": f"🔍 [로그] {s_name}({u_ip}) -> {u_name}: {msg}"})

    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
