import streamlit as st
from openai import OpenAI
import json  # 新增：专门用来处理数据的库

# --- 1. 配置 ---
st.set_page_config(page_title="凡人世界 Pro", page_icon="⚔️", layout="wide")

try:
    API_KEY = st.secrets["API_KEY"]
    BASE_URL = st.secrets["BASE_URL"]
except Exception:
    st.error("❌ 还没有配置 Secrets！")
    st.stop()

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# --- CSS 修复版 (高对比度) ---
st.markdown("""
<style>
    /* 1. 全局配置 */
    .stApp {
        background-color: #0e1117; /* 深空灰背景 */
        color: #ffffff; /* 全局白字 */
    }
    
    /* 2. 暴力强制修改所有文本颜色 (解决看不清的问题) */
    p, .stMarkdown, div[data-testid="stMarkdownContainer"] {
        color: #ffffff !important;
    }

    /* 3. 聊天气泡 - 增加辨识度 */
    div[data-testid="stChatMessage"] {
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        color: #ffffff !important; /* 气泡内文字强制白 */
    }
    
    /* 主角气泡：深蓝色背景 */
    div[data-testid="stChatMessage"]:nth-child(odd) {
        background-color: #172554; 
        border: 1px solid #3b82f6;
    }
    
    /* AI气泡：深灰色背景 */
    div[data-testid="stChatMessage"]:nth-child(even) {
        background-color: #262626; 
        border: 1px solid #525252;
    }

    /* 4. 侧边栏 */
    section[data-testid="stSidebar"] {
        background-color: #1a1c24;
    }
    
    /* 5. 物品栏样式 */
    .inventory-item {
        background-color: #334155;
        color: #fbbf24 !important; /* 金色字体 */
        padding: 5px 10px;
        border-radius: 5px;
        margin-bottom: 5px;
        border: 1px solid #f59e0b;
        font-family: monospace;
    }
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
    
    # 血条
    st.write(f"🩸 **主角生命值: {st.session_state.hp}/100**")
    st.progress(min(100, max(0, st.session_state.hp)) / 100)
    
    # 羁绊
    st.write(f"❤️ **双人羁绊值: {st.session_state.bond}**")
    st.progress(min(100, max(0, st.session_state.bond)) / 100)
    
    # 背包 (修复显示问题)
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
    scenario = st.selectbox(
        "选择副本", 
        ["丧尸围城的超市", "午夜的泰坦尼克号", "修仙界的兽潮", "赛博朋克不夜城", "克苏鲁深海考察站"], 
        disabled=is_started
    )
    
    if st.button("🔄 重置世界"):
        st.session_state.clear()
        st.rerun()

# --- 主界面 ---
st.header(f"当前副本：{scenario}")

for chat in st.session_state.history:
    avatar = "⚡️" if chat["role"] == "user" else "🤖"
    with st.chat_message(chat["role"], avatar=avatar):
        st.markdown(chat["content"])

# --- 游戏结束判定 ---
if st.session_state.hp <= 0:
    st.error(f"💀 **BAD END：{player_a} 牺牲了...**")
    st.session_state.game_over = True

# --- 核心逻辑区 ---
if not st.session_state.game_over:
    st.markdown("---")
    with st.form(key="game_form", clear_on_submit=True):
        col1, col2 = st.columns([4, 1])
        with col1:
            god_command = st.text_input("⚡️ 降下神谕", placeholder="输入行动...")
        with col2:
            submit_btn = st.form_submit_button(f"🎬 第 {st.session_state.turn} 回合")
    
    if submit_btn:
        # 1. 记录输入
        memory_text = "\n".join([f"{'【主神】' if c['role']=='user' else '【剧情】'}: {c['content']}" for c in st.session_state.history[-4:]]) # 只读最近4条，省钱且快
        instruction = f"【主神指令】：{god_command}" if god_command else "继续剧情，制造危机。"
        
        if god_command:
            st.session_state.history.append({"role": "user", "content": f"**神谕：** {god_command}"})

        # 2. Story AI (负责写文)
        with st.spinner("命运计算中..."):
            story_prompt = f"""
            你是一个无限流游戏DM。副本：{scenario}。
            主角：{player_a} (HP:{st.session_state.hp})。同伴：{player_b}。
            背包：{st.session_state.inventory}。
            
            【前情】：{memory_text}
            【指令】：{instruction}
            
            要求：200字内。如果HP低，描述受伤。如果获得物品，明确描述发现过程。
            """
            
            try:
                story_res = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": story_prompt}],
                    stream=False
                )
                story_content = story_res.choices[0].message.content
                st.session_state.history.append({"role": "assistant", "content": story_content})
                
                # 3. Logic AI (数学脑 - 强力升级版)
                # 这里我们强制 AI 输出 JSON 格式，机器读 JSON 是 100% 准确的
                logic_prompt = f"""
                阅读剧情：'''{story_content}'''
                
                请分析主角的状态变化，并必须以严格的 JSON 格式输出。
                
                格式模板：
                {{
                    "hp_change": -10,  (整数：扣血为负，回血为正，无变化为0)
                    "bond_change": 5,  (整数：关系变好正，变坏负，无变化0)
                    "new_item": "医疗包" (字符串：如果没有获得新物品，必须填 null)
                }}
                
                注意：只输出 JSON，不要包含任何 markdown 标记（如 ```json）。
                """
                
                logic_res = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": logic_prompt}],
                    stream=False
                )
                logic_text = logic_res.choices[0].message.content
                
                # 清洗数据（防止 AI 加了 ```json 前缀）
                clean_json = logic_text.replace("```json", "").replace("```", "").strip()
                
                # 4. 解析数据并更新 (最关键的一步)
                data = json.loads(clean_json)
                
                # 更新血量
                hp_delta = data.get("hp_change", 0)
                if hp_delta != 0:
                    st.session_state.hp += hp_delta
                    if hp_delta < 0: st.toast(f"🩸 受到伤害 {hp_delta}", icon="🤕")
                    else: st.toast(f"💚 恢复生命 +{hp_delta}", icon="💊")
                
                # 更新羁绊
                bond_delta = data.get("bond_change", 0)
                if bond_delta != 0:
                    st.session_state.bond = max(0, min(100, st.session_state.bond + bond_delta))
                    st.toast(f"❤️ 羁绊变化 {bond_delta}", icon="💞")
                
                # 更新背包
                new_item = data.get("new_item")
                if new_item:
                    st.session_state.inventory.append(new_item)
                    st.toast(f"🎒 获得物品：{new_item}", icon="🎁")

                st.session_state.turn += 1
                # 我删除了“if turn > 15”的代码，现在游戏无限进行了！
                
                st.rerun()
                
            except Exception as e:
                # 如果 AI 偶尔发疯，我们不仅报错，还打印出来方便调试
                print(f"Logic Error: {e}")
                st.rerun()


