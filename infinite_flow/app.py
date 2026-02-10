import streamlit as st
from openai import OpenAI
import re

# --- 1. 配置必须放在最前面 ---
st.set_page_config(page_title="凡人世界 Pro", page_icon="⚔️", layout="wide")

# --- 2. 读取密钥 ---
try:
    API_KEY = st.secrets["API_KEY"]
    BASE_URL = st.secrets["BASE_URL"]
except Exception:
    st.error("❌ 还没有配置 Secrets！")
    st.stop()

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# --- CSS美化 (血条特效) ---
st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #ff4b4b; }
    .report-card {padding: 20px; border-radius: 10px; background-color: #f0f2f6; border-left: 5px solid #ff4b4b;}
</style>
""", unsafe_allow_html=True)

# --- 初始化变量 (新增 HP 和 背包) ---
if "history" not in st.session_state: st.session_state.history = []
if "turn" not in st.session_state: st.session_state.turn = 1
if "bond" not in st.session_state: st.session_state.bond = 50
if "hp" not in st.session_state: st.session_state.hp = 100  # 新增：初始血量
if "inventory" not in st.session_state: st.session_state.inventory = [] # 新增：初始背包
if "game_over" not in st.session_state: st.session_state.game_over = False
if "final_report" not in st.session_state: st.session_state.final_report = ""

# --- 侧边栏 (显示状态) ---
with st.sidebar:
    st.title("⚔️ 凡人世界 Pro")
    
    # 1. 显示血量
    st.write(f"🩸 **主角生命值: {st.session_state.hp}/100**")
    st.progress(min(100, max(0, st.session_state.hp)) / 100)
    
    # 2. 显示羁绊
    st.write(f"❤️ **双人羁绊值: {st.session_state.bond}**")
    st.progress(min(100, max(0, st.session_state.bond)) / 100)
    
    # 3. 显示背包
    st.divider()
    st.write("🎒 **物品栏**")
    if st.session_state.inventory:
        for item in st.session_state.inventory:
            st.code(item, language=None)
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

# 渲染历史记录
for chat in st.session_state.history:
    avatar = "⚡️" if chat["role"] == "user" else "🤖"
    with st.chat_message(chat["role"], avatar=avatar):
        st.markdown(chat["content"])

# --- 游戏结束判定 ---
if st.session_state.hp <= 0:
    st.session_state.game_over = True
    st.error(f"💀 **BAD END：{player_a} 牺牲了...**")
    st.markdown("---")

elif st.session_state.game_over:
    if st.session_state.bond <= 0:
        st.error("💔 **BAD END：决裂**")
    elif st.session_state.bond >= 100:
        st.success("🎉 **HAPPY END：灵魂伴侣**")
    else:
        st.warning("⏳ **NORMAL END：生存**")

# --- 游戏输入区域 ---
if not st.session_state.game_over:
    st.markdown("---")
    with st.form(key="game_form", clear_on_submit=True):
        col1, col2 = st.columns([4, 1])
        with col1:
            god_command = st.text_input("⚡️ 降下神谕", placeholder="输入行动，例如：叶凡冲上去挡住攻击...")
        with col2:
            submit_btn = st.form_submit_button(f"🎬 第 {st.session_state.turn} 回合")
    
    if submit_btn:
        # 1. 记录玩家输入
        memory_text = "\n".join([f"{'【主神】' if c['role']=='user' else '【剧情】'}: {c['content']}" for c in st.session_state.history])
        instruction = f"【主神指令】：{god_command}" if god_command else "继续剧情，制造危机。"
        
        if god_command:
            st.session_state.history.append({"role": "user", "content": f"**神谕：** {god_command}"})

        # 2. 调用 Story AI (写故事)
        with st.spinner("命运计算中..."):
            story_prompt = f"""
            你是一个无限流游戏DM。副本：{scenario}。
            主角：{player_a} (HP:{st.session_state.hp})。同伴：{player_b}。
            背包物品：{st.session_state.inventory}。
            
            【前情】：{memory_text}
            【指令】：{instruction}
            
            请描写一段精彩剧情(200字内)。如果HP很低，描述受伤状态。如果获得物品，请描述发现过程。
            """
            try:
                story_res = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": story_prompt}],
                    stream=False
                )
                story_content = story_res.choices[0].message.content
                st.session_state.history.append({"role": "assistant", "content": story_content})
                
                # 3. 调用 Logic AI (计算数值) - 这里是核心黑科技
                logic_prompt = f"""
                阅读这段剧情：'''{story_content}'''
                请分析剧情对【{player_a}】的影响。
                必须严格按照以下格式输出 JSON 数据，不要任何多余文字：
                
                HP_CHANGE: [数字] (受伤填负数，回血填正数，无变化填0)
                BOND_CHANGE: [数字] (关系变好正数，变坏负数，无变化0)
                ITEM_GET: [物品名] (如果没有获得物品，填 None)
                """
                
                logic_res = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": logic_prompt}],
                    stream=False
                )
                logic_text = logic_res.choices[0].message.content
                
                # 4. 解析数据并更新状态
                # 提取 HP
                hp_match = re.search(r'HP_CHANGE:\s*([+-]?\d+)', logic_text)
                if hp_match:
                    hp_delta = int(hp_match.group(1))
                    st.session_state.hp += hp_delta
                    if hp_delta < 0: st.toast(f"🩸 受到伤害 {hp_delta}", icon="🤕")
                    if hp_delta > 0: st.toast(f"💚 恢复生命 {hp_delta}", icon="💊")

                # 提取 羁绊
                bond_match = re.search(r'BOND_CHANGE:\s*([+-]?\d+)', logic_text)
                if bond_match:
                    bond_delta = int(bond_match.group(1))
                    st.session_state.bond = max(0, min(100, st.session_state.bond + bond_delta))
                    if bond_delta != 0: st.toast(f"❤️ 羁绊变化 {bond_delta}", icon="💞")

                # 提取 物品
                item_match = re.search(r'ITEM_GET:\s*(.+)', logic_text)
                if item_match:
                    item_name = item_match.group(1).strip()
                    if item_name != "None":
                        st.session_state.inventory.append(item_name)
                        st.toast(f"🎒 获得物品：{item_name}", icon="🎁")

                st.session_state.turn += 1
                
                # 判定结束
                if st.session_state.turn > 15 or st.session_state.hp <= 0:
                    st.session_state.game_over = True
                
                st.rerun()
                
            except Exception as e:
                st.error(f"Error: {e}")
