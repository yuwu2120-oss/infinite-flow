import streamlit as st
from openai import OpenAI
import json
import random

# --- 1. 配置 ---
st.set_page_config(page_title="凡人世界 Pro", page_icon="⚔️", layout="wide")

try:
    API_KEY = st.secrets["API_KEY"]
    BASE_URL = st.secrets["BASE_URL"]
except Exception:
    st.error("❌ 还没有配置 Secrets！")
    st.stop()

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# --- CSS 风格 ---
st.markdown("""
<style>
    .stApp { background-color: #f9f9f9; color: #333333; }
    section[data-testid="stSidebar"] { background-color: #f0f2f6; border-right: 1px solid #e5e5e5; }
    
    /* 物品栏样式 */
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
    
    /* 结局卡片样式 */
    .ending-card {
        background-color: #fff1f2;
        border: 1px solid #fda4af;
        color: #881337 !important;
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 10px;
        font-size: 0.9em;
    }

    /* 修复字体颜色 */
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
# 新增：结局收藏夹
if "endings" not in st.session_state: st.session_state.endings = [] 

# --- 侧边栏 ---
with st.sidebar:
    st.title("⚔️ 凡人世界 Pro")
    
    # 1. 动态头像展示 (DiceBear API - 绝对稳定)
    col_a, col_b = st.columns(2)
    is_started = len(st.session_state.history) > 0
    player_a = st.text_input("主角名", value="叶凡", disabled=is_started)
    player_b = st.text_input("同伴名", value="Eve", disabled=is_started)

    with col_a:
        # 使用 adventurer 风格生成 RPG 头像
        st.image(f"https://api.dicebear.com/9.x/adventurer/svg?seed={player_a}&backgroundColor=b6e3f4", caption=player_a)
    with col_b:
        st.image(f"https://api.dicebear.com/9.x/adventurer/svg?seed={player_b}&backgroundColor=ffdfbf", caption=player_b)

    st.divider()
    
    # 2. 状态栏
    st.write(f"🩸 **生命值: {st.session_state.hp}/100**")
    st.progress(min(100, max(0, st.session_state.hp)) / 100)
    st.write(f"❤️ **羁绊值: {st.session_state.bond}**")
    st.progress(min(100, max(0, st.session_state.bond)) / 100)
    
    st.divider()
    st.write("🎒 **物品栏**")
    if st.session_state.inventory:
        for item in st.session_state.inventory:
            st.markdown(f"<div class='inventory-item'>📦 {item}</div>", unsafe_allow_html=True)
    else:
        st.caption("空空如也...")

    # 3. 结局图鉴 (新功能)
    if st.session_state.endings:
        st.divider()
        st.write("🏆 **已达成结局**")
        for end in st.session_state.endings:
            st.markdown(f"<div class='ending-card'>{end}</div>", unsafe_allow_html=True)

    st.divider()
    scenario = st.selectbox("选择副本", ["丧尸围城的超市", "午夜的泰坦尼克号", "修仙界的兽潮", "赛博朋克不夜城"], disabled=is_started)
    
    if st.button("🔄 重置世界"):
        st.session_state.history = []
        st.session_state.turn = 1
        st.session_state.bond = 50
        st.session_state.hp = 100
        st.session_state.inventory = []
        st.session_state.game_over = False
        st.rerun()

# --- 主界面 ---
st.header(f"当前副本：{scenario}")

for chat in st.session_state.history:
    avatar = "⚡️" if chat["role"] == "user" else "🤖"
    with st.chat_message(chat["role"], avatar=avatar):
        st.markdown(chat["content"])

# --- 游戏逻辑 ---
if not st.session_state.game_over:
    # 检查是否达成结局
    ending_title = ""
    if st.session_state.hp <= 0:
        ending_title = f"💀 BAD END：{player_a} 战死沙场"
        st.error(ending_title)
        st.session_state.game_over = True
    elif st.session_state.bond <= 0:
        ending_title = f"💔 BAD END：{player_a} 与 {player_b} 决裂"
        st.error(ending_title)
        st.session_state.game_over = True
    elif st.session_state.bond >= 100:
        ending_title = f"❤️ HAPPY END：灵魂伴侣"
        st.success(ending_title)
        st.session_state.game_over = True
    
    # 如果达成结局，且没保存过，就存入侧边栏
    if ending_title and ending_title not in st.session_state.endings:
        st.session_state.endings.append(ending_title)
        st.rerun() # 刷新一下显示侧边栏

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

        with st.spinner("命运计算中..."):
            # 1. Story AI
            story_prompt = f"""
            你是一个无限流游戏DM。副本：{scenario}。
            主角：{player_a} (HP:{st.session_state.hp})。同伴：{player_b}。
            背包：{st.session_state.inventory}。
            
            【前情】：{memory_text}
            【指令】：{instruction}
            
            要求：200字内。剧情紧凑。
            """
            
            try:
                story_res = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": story_prompt}],
                    stream=False
                )
                story_content = story_res.choices[0].message.content
                
                # 2. Logic AI (不再生成图片，只算数)
                logic_prompt = f"""
                阅读剧情：'''{story_content}'''
                分析数值变化。
                JSON格式：
                {{
                    "hp_change": 0,
                    "bond_change": 0,
                    "new_item": null
                }}
                """
                
                logic_res = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": logic_prompt}],
                    stream=False
                )
                
                clean_json = logic_res.choices[0].message.content.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_json)
                
                # 更新数值
                hp_delta = data.get("hp_change", 0)
                if hp_delta != 0: st.session_state.hp += hp_delta
                
                bond_delta = data.get("bond_change", 0)
                if bond_delta != 0: st.session_state.bond = max(0, min(100, st.session_state.bond + bond_delta))
                
                new_item = data.get("new_item")
                if new_item: st.session_state.inventory.append(new_item)

                st.session_state.history.append({
                    "role": "assistant", 
                    "content": story_content
                })
                
                st.session_state.turn += 1
                st.rerun()
                
            except Exception as e:
                st.error(f"Error: {e}")
