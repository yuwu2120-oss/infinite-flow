import streamlit as st
from openai import OpenAI
import json

# --- 1. 配置 ---
st.set_page_config(page_title="凡人世界 Pro", page_icon="⚔️", layout="wide")

try:
    API_KEY = st.secrets["API_KEY"]
    BASE_URL = st.secrets["BASE_URL"]
except Exception:
    st.error("❌ 还没有配置 Secrets！")
    st.stop()

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# --- CSS 风格：清爽小说风 ---
st.markdown("""
<style>
    .stApp { background-color: #f9f9f9; color: #333333; }
    section[data-testid="stSidebar"] { background-color: #f0f2f6; border-right: 1px solid #e5e5e5; }
    .inventory-item {
        background-color: #ffffff;
        color: #444 !important;
        padding: 8px 12px;
        border-radius: 6px;
        margin-bottom: 8px;
        border-left: 4px solid #3b82f6;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        font-weight: 500;
    }
    p, h1, h2, h3, .stMarkdown { color: #1a1a1a !important; }
</style>
""", unsafe_allow_html=True)

# --- 初始化 ---
if "history" not in st.session_state: st.session_state.history = []
if "turn" not in st.session_state: st.session_state.turn = 1
if "bond" not in st.session_state: st.session_state.bond = 50
if "hp" not in st.session_state: st.session_state.hp = 100
if "inventory" not in st.session_state: st.session_state.inventory = []
if "game_over" not in st.session_state: st.session_state.game_over = False

# --- 侧边栏 ---
with st.sidebar:
    st.title("⚔️ 凡人世界 Pro")
    st.write(f"🩸 **主角生命值: {st.session_state.hp}/100**")
    st.progress(min(100, max(0, st.session_state.hp)) / 100)
    st.write(f"❤️ **双人羁绊值: {st.session_state.bond}**")
    st.progress(min(100, max(0, st.session_state.bond)) / 100)
    
    st.divider()
    st.write("🎒 **物品栏**")
    if st.session_state.inventory:
        for item in st.session_state.inventory:
            st.markdown(f"<div class='inventory-item'>📦 {item}</div>", unsafe_allow_html=True)
    else:
        st.caption("空空如也...")

    st.divider()
    is_started = len(st.session_state.history) > 0
    player_a = st.text_input("主角名", value="叶凡", disabled=is_started)
    player_b = st.text_input("同伴名", value="Eve", disabled=is_started)
    scenario = st.selectbox("选择副本", ["丧尸围城的超市", "午夜的泰坦尼克号", "修仙界的兽潮", "赛博朋克不夜城"], disabled=is_started)
    
    if st.button("🔄 重置世界"):
        st.session_state.clear()
        st.rerun()

# --- 主界面 ---
st.header(f"当前副本：{scenario}")

for chat in st.session_state.history:
    avatar = "⚡️" if chat["role"] == "user" else "🤖"
    with st.chat_message(chat["role"], avatar=avatar):
        st.markdown(chat["content"])
        # 如果历史记录里有图片，就显示出来
        if "image_url" in chat:
            st.image(chat["image_url"], use_container_width=True)

# --- 游戏逻辑 ---
if st.session_state.hp <= 0:
    st.error(f"💀 **BAD END：{player_a} 牺牲了...**")
    st.session_state.game_over = True

if not st.session_state.game_over:
    st.markdown("---")
    with st.form(key="game_form", clear_on_submit=True):
        col1, col2 = st.columns([4, 1])
        with col1:
            god_command = st.text_input("⚡️ 降下神谕", placeholder="输入行动...")
        with col2:
            submit_btn = st.form_submit_button(f"🎬 第 {st.session_state.turn} 回合")
    
    if submit_btn:
        memory_text = "\n".join([f"{'【主神】' if c['role']=='user' else '【剧情】'}: {c['content']}" for c in st.session_state.history[-4:]])
        instruction = f"【主神指令】：{god_command}" if god_command else "继续剧情，制造危机。"
        
        if god_command:
            st.session_state.history.append({"role": "user", "content": f"**神谕：** {god_command}"})

        with st.spinner("剧情生成中..."):
            # 1. 写故事
            story_prompt = f"""
            你是一个无限流游戏DM。副本：{scenario}。
            主角：{player_a} (HP:{st.session_state.hp})。同伴：{player_b}。
            背包：{st.session_state.inventory}。
            
            【前情】：{memory_text}
            【指令】：{instruction}
            
            要求：200字内。剧情紧凑，画面感强。
            """
            
            try:
                story_res = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": story_prompt}],
                    stream=False
                )
                story_content = story_res.choices[0].message.content
                
                # 2. 算数值 + 生成画图指令 (关键升级)
                logic_prompt = f"""
                阅读剧情：'''{story_content}'''
                
                请完成两件事：
                1. 分析数值变化 (HP, 羁绊, 物品)。
                2. 将这段剧情概括为一句【英文绘画提示词】(image_prompt)，用于生成插图。描述要具体，包含风格（如 cinematic, dark, fantasy）。
                
                严格输出 JSON 格式：
                {{
                    "hp_change": 0,
                    "bond_change": 0,
                    "new_item": null,
                    "image_prompt": "A cinematic shot of a zombie standing in dark supermarket aisle, holding an axe, 8k resolution"
                }}
                """
                
                logic_res = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": logic_prompt}],
                    stream=False
                )
                
                # 清洗并解析 JSON
                clean_json = logic_res.choices[0].message.content.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_json)
                
                # 更新数值
                hp_delta = data.get("hp_change", 0)
                if hp_delta != 0: st.session_state.hp += hp_delta
                
                bond_delta = data.get("bond_change", 0)
                if bond_delta != 0: st.session_state.bond = max(0, min(100, st.session_state.bond + bond_delta))
                
                new_item = data.get("new_item")
                if new_item: st.session_state.inventory.append(new_item)

                # --- 3. 生成图片 (魔法时刻) ---
                image_prompt = data.get("image_prompt", f"{scenario} scene, cinematic")
                # 对 Prompt 进行 URL 编码
                import urllib.parse
                encoded_prompt = urllib.parse.quote(image_prompt)
                image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=512&nologo=true"

                # 保存到历史记录
                st.session_state.history.append({
                    "role": "assistant", 
                    "content": story_content,
                    "image_url": image_url  # 把图片地址存进去
                })
                
                st.session_state.turn += 1
                st.rerun()
                
            except Exception as e:
                st.error(f"Error: {e}")
