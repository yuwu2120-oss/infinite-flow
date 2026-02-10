import streamlit as st
from openai import OpenAI
import json

# --- 1. 配置 ---
st.set_page_config(page_title="凡人世界：灵魂试炼", page_icon="🧬", layout="wide")

try:
    API_KEY = st.secrets["API_KEY"]
    BASE_URL = st.secrets["BASE_URL"]
except Exception:
    st.error("❌ 还没有配置 Secrets！")
    st.stop()

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# --- CSS: 极简未来风 (Social App 质感) ---
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; color: #212529; }
    section[data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #dee2e6; }
    
    /* 战报卡片样式 */
    .soul-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        margin-top: 20px;
        margin-bottom: 20px;
        text-align: center;
    }
    .soul-title { font-size: 1.5em; font-weight: bold; margin-bottom: 10px; }
    .soul-tag { 
        background-color: rgba(255,255,255,0.2); 
        padding: 5px 10px; 
        border-radius: 20px; 
        font-size: 0.9em; 
        display: inline-block;
        margin: 5px;
    }
    
    /* 聊天气泡 */
    div[data-testid="stChatMessage"] {
        background-color: white;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border: 1px solid #eee;
    }
</style>
""", unsafe_allow_html=True)

# --- 初始化 ---
if "history" not in st.session_state: st.session_state.history = []
if "turn" not in st.session_state: st.session_state.turn = 1
if "hp" not in st.session_state: st.session_state.hp = 100
if "attributes" not in st.session_state: 
    # 六维图谱 (0-100)
    st.session_state.attributes = {"勇气": 50, "智慧": 50, "冷血": 50} 
if "game_over" not in st.session_state: st.session_state.game_over = False
if "final_report" not in st.session_state: st.session_state.final_report = None

# --- 侧边栏 ---
with st.sidebar:
    st.title("🧬 凡人世界 | 灵魂试炼")
    st.caption("Alpha v2.6 - Social Edition")
    
    # 实时属性雷达 (简化版)
    st.write("📊 **当前人格倾向**")
    st.progress(st.session_state.attributes["勇气"] / 100)
    st.caption(f"🦁 勇气: {st.session_state.attributes['勇气']}")
    st.progress(st.session_state.attributes["智慧"] / 100)
    st.caption(f"🧠 智慧: {st.session_state.attributes['智慧']}")
    st.progress(st.session_state.attributes["冷血"] / 100)
    st.caption(f"❄️ 冷血: {st.session_state.attributes['冷血']}")
    
    st.divider()
    
    # 生命值
    st.write(f"🩸 **生命值: {st.session_state.hp}/100**")
    st.progress(min(100, max(0, st.session_state.hp)) / 100)
    
    st.divider()
    is_started = len(st.session_state.history) > 0
    player_name = st.text_input("你的名字", value="玩家1", disabled=is_started)
    scenario = st.selectbox("选择试炼副本", ["丧尸围城", "泰坦尼克号", "修仙界", "赛博朋克"], disabled=is_started)
    
    if st.button("🔄 重启时间线"):
        st.session_state.clear()
        st.rerun()

# --- 主界面 ---
st.header(f"当前副本：{scenario}")

# 历史记录
for chat in st.session_state.history:
    avatar = "👤" if chat["role"] == "user" else "🤖"
    with st.chat_message(chat["role"], avatar=avatar):
        st.markdown(chat["content"])

# --- 游戏逻辑 ---

# 1. 游戏结束显示战报 (核心社交功能)
if st.session_state.game_over and st.session_state.final_report:
    report = st.session_state.final_report
    
    st.markdown("---")
    st.markdown(f"""
    <div class="soul-card">
        <div class="soul-title">💀 灵魂观测报告 💀</div>
        <p>受试者：{player_name}</p>
        <p>结局：{report['ending']}</p>
        <div>
            <span class="soul-tag">🦁 勇气 {report['stats']['勇气']}</span>
            <span class="soul-tag">🧠 智慧 {report['stats']['智慧']}</span>
            <span class="soul-tag">❄️ 冷血 {report['stats']['冷血']}</span>
        </div>
        <hr style="border-color: rgba(255,255,255,0.3);">
        <p style="font-style: italic;">"{report['comment']}"</p>
        <p style="font-size: 0.8em; margin-top: 15px;">🔍 凡人世界 · Infinite Flow Social</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.info("💡 **长按截图或复制上方文字，发给朋友挑战你的生存记录！**")

# 2. 游戏进行中
elif not st.session_state.game_over:
    if st.session_state.hp <= 0:
        st.session_state.game_over = True
        st.rerun()

    st.markdown("---")
    with st.form(key="game_form", clear_on_submit=True):
        user_input = st.text_input("⚡️ 做出你的抉择...", placeholder="你打算怎么做？")
        submit_btn = st.form_submit_button(f"🎬 第 {st.session_state.turn} 回合")
    
    if submit_btn and user_input:
        # 记录
        st.session_state.history.append({"role": "user", "content": user_input})
        
        # 构建 Prompt
        memory = "\n".join([f"{c['role']}: {c['content']}" for c in st.session_state.history[-4:]])
        
        with st.spinner("命运计算中..."):
            # A. 剧情生成
            story_prompt = f"""
            你是一个无限流游戏AI。副本：{scenario}。主角：{player_name} (HP:{st.session_state.hp})。
            前情：{memory}
            玩家行动：{user_input}
            
            请输出简短精彩的剧情结果(100字内)。如果必死，直接写死。
            """
            story_res = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": story_prompt}]
            )
            story_content = story_res.choices[0].message.content
            st.session_state.history.append({"role": "assistant", "content": story_content})
            
            # B. 数值与人格分析 (Data Mining)
            logic_prompt = f"""
            阅读剧情：{story_content}
            分析主角的行为，调整属性。
            JSON格式：
            {{
                "hp_change": 0,
                "courage_change": 0, (勇气变化 -10到10)
                "wisdom_change": 0, (智慧变化 -10到10)
                "cold_change": 0 (冷血变化 -10到10)
            }}
            """
            logic_res = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": logic_prompt}]
            )
            try:
                data = json.loads(logic_res.choices[0].message.content.replace("```json", "").replace("```", ""))
                
                # 更新数值
                st.session_state.hp = max(0, min(100, st.session_state.hp + data.get("hp_change", 0)))
                st.session_state.attributes["勇气"] = max(0, min(100, st.session_state.attributes["勇气"] + data.get("courage_change", 0)))
                st.session_state.attributes["智慧"] = max(0, min(100, st.session_state.attributes["智慧"] + data.get("wisdom_change", 0)))
                st.session_state.attributes["冷血"] = max(0, min(100, st.session_state.attributes["冷血"] + data.get("cold_change", 0)))
                
                # 判定结束
                if st.session_state.hp <= 0 or st.session_state.turn >= 10: # 10回合强制结算，方便测试
                    st.session_state.game_over = True
                    # C. 生成最终战报 (The Social Asset)
                    report_prompt = f"""
                    玩家 {player_name} 结束了游戏。
                    最终属性：{st.session_state.attributes}。
                    结局剧情：{story_content}。
                    
                    请生成一个JSON战报：
                    {{
                        "ending": "给结局起个中二的标题 (如：深海的殉道者)",
                        "comment": "一句犀利的性格评价 (如：你太善良了，在这个世界活不过3分钟)",
                        "stats": {st.session_state.attributes}
                    }}
                    """
                    report_res = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role": "user", "content": report_prompt}]
                    )
                    st.session_state.final_report = json.loads(report_res.choices[0].message.content.replace("```json", "").replace("```", ""))
                
                st.session_state.turn += 1
                st.rerun()
                
            except Exception as e:
                st.error(e)
