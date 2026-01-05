from flask import Flask, render_template, request, jsonify
import requests
import os
from PIL import Image, ImageDraw, ImageFont
import io

app = Flask(__name__)

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
            return sorted([{"id": m['user']['id'], "name": m['nick'] or m['user']['username']} for m in members if not m['user'].get('bot')], key=lambda x: x['name'])
        return []
    except: return []

def create_card_image(receiver_name, message_text, theme_file):
    try:
        # 사용자가 웹에서 선택한 테마 파일을 불러옴
        bg_path = theme_file
        font_path = 'Myfont.ttf'
        
        if not os.path.exists(bg_path) or not os.path.exists(font_path): return None
        
        img = Image.open(bg_path).convert("RGBA")
        draw = ImageDraw.Draw(img)
        to_font = ImageFont.truetype(font_path, 30)
        msg_font = ImageFont.truetype(font_path, 22) # 16pt 느낌
        text_color = (40, 20, 20)
        
        top_limit = 200
        side_margin = 180
        
        # 1. TO. [이름] 중앙 정렬
        to_text = f"TO. {receiver_name}"
        to_w = draw.textbbox((0, 0), to_text, font=to_font)[2] - draw.textbbox((0, 0), to_text, font=to_font)[0]
        draw.text(((img.width - to_w) / 2, top_limit), to_text, font=to_font, fill=text_color)
        
        # 2. 본문 줄바꿈 및 중앙 정렬
        y_cursor = top_limit + 70
        lines, current_line = [], ""
        for char in message_text:
            test_line = current_line + char
            if draw.textbbox((0, 0), test_line, font=msg_font)[2] <= (img.width - side_margin*2): current_line = test_line
            else: lines.append(current_line.strip()); current_line = char
        lines.append(current_line.strip())

        for line in lines:
            if y_cursor > img.height - 230: break
            line_w = draw.textbbox((0, 0), line, font=msg_font)[2] - draw.textbbox((0, 0), line, font=msg_font)[0]
            draw.text(((img.width - line_w) / 2, y_cursor), line, font=msg_font, fill=text_color)
            y_cursor += 38

        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        return img_io
    except: return None

@app.route('/')
def index(): return render_template('index.html', members=get_discord_members())

@app.route('/send', methods=['POST'])
def send_message():
    data = request.json
    # 사용자가 선택한 테마(bg1.png 또는 bg2.png)를 가져옴
    selected_theme = data.get('theme', 'bg1.png')
    
    card_img = create_card_image(data.get('userName'), data.get('message'), selected_theme)
    
    if PUBLIC_WEBHOOK and card_img:
        requests.post(PUBLIC_WEBHOOK, data={"content": f"💌 <@{data.get('userId')}>님께 익명의 편지가 왔어요!"}, files={'file': ('card.png', card_img, 'image/png')})
    
    if ADMIN_WEBHOOK:
        requests.post(ADMIN_WEBHOOK, json={"content": f"🔍 [로그] {data.get('senderName')} -> {data.get('userName')}(디자인:{selected_theme}): {data.get('message')}"})
    
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
