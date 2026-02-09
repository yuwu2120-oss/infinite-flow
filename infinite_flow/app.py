import streamlit as st
from openai import OpenAI
import re

# --- 云端配置 (关键修改) ---
# 以前我们是直接写 API_KEY = "sk-..."
# 现在我们告诉代码：去服务器的保险柜(Secrets)里找 Key
try:
    API_KEY = st.secrets["API_KEY"]
    BASE_URL = st.secrets["BASE_URL"]
except FileNotFoundError:
    st.error("❌ 还没有配置 Secrets！请在 Streamlit 后台填入 API Key。")
    st.stop()

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

st.set_page_config(page_title="凡人世界", page_icon="💀", layout="wide")

# --- CSS美化 ---
st.markdown("""
<style>
    .report-card {padding: 20px; border-radius: 10px; background-color: #f0f2f6; border-left: 5px solid #ff4b4b; margin-top: 20px;}
</style>
""", unsafe_allow_html=True)

# --- 初始化 ---
if "history" not in st.session_state: st.session_state.history = []
if "turn" not in st.session_state: st.session_state.turn = 1
if "bond" not in st.session_state: st.session_state.bond = 50
if "game_over" not in st.session_state: st.session_state.game_over = False
if "final_report" not in st.session_state: st.session_state.final_report = ""

# --- 侧边栏 ---
with st.sidebar:
    st.title("💀 凡人世界 v1.0")
    # 动态颜色
    st.markdown(f"### ❤️ 灵魂羁绊值: {st.session_state.bond}")
    st.progress(st.session_state.bond / 100)
    
    st.divider()
    is_started = len(st.session_state.history) > 0
    player_a = st.text_input("玩家A", value="叶凡（腹黑，修仙）", disabled=is_started)
    player_b = st.text_input("玩家B", value="Eve（傲娇，大小姐）", disabled=is_started)
    scenario = st.selectbox("副本", ["丧尸围城的超市", "午夜的泰坦尼克号", "西方魔法世界", "修仙界的兽潮"], disabled=is_started)
    
    if st.button("🔄 重置世界"):
        st.session_state.clear()
        st.rerun()

# --- 主界面 ---
st.header(f"当前副本：{scenario}")

for chat in st.session_state.history:
    avatar = "⚡️" if chat["role"] == "user" else "🤖"
    with st.chat_message(chat["role"], avatar=avatar):
        st.markdown(chat["content"])

# --- 游戏逻辑 ---
if st.session_state.game_over:
    st.markdown("---")
    if st.session_state.bond <= 0:
        st.error("💔 **BAD END：决裂**")
    elif st.session_state.bond >= 100:
        st.success("🎉 **HAPPY END：羁绊**")
    else:
        st.warning("⏳ **NORMAL END**")
    
    if st.session_state.final_report:
        st.markdown(f"<div class='report-card'><h3>📜 观察报告</h3>{st.session_state.final_report}</div>", unsafe_allow_html=True)

else:
    st.markdown("---")
    with st.form(key="game_form", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            god_command = st.text_input("⚡️ 降下神谕", placeholder="例如：叶凡为Eve挡了一刀...")
        with col2:
            submit_btn = st.form_submit_button(f"🎬 第 {st.session_state.turn} 回合")
    
    if submit_btn:
        if st.session_state.bond <= 0 or st.session_state.bond >= 100:
            st.session_state.game_over = True
            st.rerun()

        memory_text = "\n".join([f"{'【主神】' if c['role']=='user' else '【剧情】'}: {c['content']}" for c in st.session_state.history])
        instruction = f"【主神神谕】：{god_command}" if god_command else "继续推演剧情，制造波澜。"
        if god_command:
            st.session_state.history.append({"role": "user", "content": f"**神谕：** {god_command}"})

        # --- 作家 AI ---
        writer_prompt = f"""
        你是一个无限流小说家。副本：{scenario}。
        A：{player_a}。B：{player_b}。
        当前羁绊：{st.session_state.bond}。
        【前情】：{memory_text}
        【指令】：{instruction}
        【要求】：写300字以内的精彩剧情。
        """

        with st.spinner("命运计算中..."):
            try:
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": writer_prompt}],
                    stream=False
                )
                story_content = response.choices[0].message.content
                
                # --- 会计 AI ---
                scorer_prompt = f"""
                阅读剧情：'''{story_content}'''
                分析【{player_a}】和【{player_b}】的关系变化。
                请直接输出一个数字（范围 -20 到 +20），不要输出任何其他文字！
                """
                score_res = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": scorer_prompt}],
                    stream=False
                )
                score_text = score_res.choices[0].message.content
                match = re.search(r'([+-]?\d+)', score_text)
                if match:
                    change = int(match.group(1))
                    st.session_state.bond = max(0, min(100, st.session_state.bond + change))
                    if change > 0: st.toast(f"❤️ 羁绊上升 {change} 点", icon="🔥")
                    elif change < 0: st.toast(f"💔 羁绊下降 {abs(change)} 点", icon="❄️")

                st.session_state.history.append({"role": "assistant", "content": story_content})
                st.session_state.turn += 1
                
                if st.session_state.turn > 10 or st.session_state.bond <= 0 or st.session_state.bond >= 100:
                    st.session_state.game_over = True
                    report_res = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role": "user", "content": memory_text}, {"role": "user", "content": "用心理医生口吻给这两人关系写100字诊断书。"}]
                    )
                    st.session_state.final_report = report_res.choices[0].message.content
                
                st.rerun()
            except Exception as e:

                st.error(f"Error: {e}")


