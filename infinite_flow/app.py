import streamlit as st
from openai import OpenAI
import json

# --- 1. 配置 ---
st.set_page_config(page_title="凡人世界：创世版", page_icon="🌍", layout="wide")

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
    .inventory-item {
        background-color: #ffffff; color: #444 !important; padding: 8px 12px;
        border-radius: 6px; margin-bottom: 8px; border-left: 4px solid #3b82f6;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1); font-weight: 500;
    }
    /* 创世卡片风格 */
    .creation-card {
        background-color: #e0e7ff; border: 1px dashed #4338ca; padding: 15px; border-radius: 10px; margin-bottom: 20px;
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

# --- 新增：自定义副本存储 ---
# 结构：{"副本名": "世界观描述..."}
if "custom_worlds" not in st.session_state: 
    st.session_state.custom_worlds = {} 

# --- 侧边栏 ---
with st.sidebar:
    st.title("🌍 凡人世界")
    
    # --- 1. 创世引擎 (核心新功能) ---
    with st.expander("🛠️ 创造我的副本", expanded=False):
        # 简单的商业模式逻辑
        created_count = len(st.session_state.custom_worlds)
        free_limit = 1
        
        if created_count < free_limit:
            st.caption(f"🎁 新手福利：免费创建次数 ({created_count}/{free_limit})")
            with st.form("create_world_form"):
                new_world_name = st.text_input("副本名称", placeholder="例如：赛博修仙2077")
                new_world_desc = st.text_area("世界观设定", placeholder="例如：这是一个充满霓虹灯的修仙世界，人们用芯片筑基，黑客是最高级的符咒师...")
                if st.form_submit_button("✨ 立即创造"):
                    if new_world_name and new_world_desc:
                        st.session_state.custom_worlds[new_world_name] = new_world_desc
                        st.success(f"副本【{new_world_name}】创造成功！")
                        st.rerun()
                    else:
                        st.warning("请填写完整设定！")
        else:
            # 模拟付费墙
            st.markdown(f"""
            <div class='creation-card'>
                <h4>🔒 免费次数已用完</h4>
                <p>你已创建了 {created_count} 个私有宇宙。</p>
                <p>解锁<b>无限创造权</b></p>
                <button style='background:#4338ca;color:white;border:none;padding:5px 10px;border-radius:5px;'>💎</button>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # --- 2. 状态栏 ---
    st.write(f"🩸 **HP: {st.session_state.hp}/100**")
    st.progress(min(100, max(0, st.session_state.hp)) / 100)
    st.write(f"❤️ **羁绊: {st.session_state.bond}**")
    st.progress(min(100, max(0, st.session_state.bond)) / 100)
    
    st.divider()
    st.write("🎒 **物品栏**")
    if st.session_state.inventory:
        for item in st.session_state.inventory:
            st.markdown(f"<div class='inventory-item'>📦 {item}</div>", unsafe_allow_html=True)
    else:
        st.caption("空空如也...")

    st.divider()
    
    # --- 3. 副本选择 (合并官方+自定义) ---
    is_started = len(st.session_state.history) > 0
    player_a = st.text_input("冒险者", value="叶凡(腹黑，搞笑，正义感)", disabled=is_started)
    player_b = st.text_input("伙伴", value="Eve(聪明，善良)", disabled=is_started)
    
    # 合并列表
    official_worlds = ["丧尸围城的超市", "汉朝", "西游世界", "秦始皇陵", "深海考察站"]
    my_worlds = list(st.session_state.custom_worlds.keys())
    
    # 如果有自定义副本，显示分隔符
    if my_worlds:
        all_options = official_worlds + ["--- 我的副本 ---"] + my_worlds
    else:
        all_options = official_worlds
        
    selected_option = st.selectbox("选择世界", all_options, disabled=is_started)
    
    # 处理分隔符选择
    if selected_option == "--- 我的副本 ---":
        st.error("请选择具体的副本！")
        st.stop()
        
    # 获取当前副本的详细设定
    if selected_option in st.session_state.custom_worlds:
        current_world_setting = st.session_state.custom_worlds[selected_option]
        st.info(f"正在加载自定义设定：\n{current_world_setting}")
    else:
        current_world_setting = "这是一个标准的无限流副本，请根据名字自由发挥。"
    
    if st.button("🔄 重置时间线"):
        st.session_state.clear()
        st.rerun()

# --- 主界面 ---
st.header(f"当前副本：{selected_option}")

for chat in st.session_state.history:
    avatar = "⚡️" if chat["role"] == "user" else "🤖"
    with st.chat_message(chat["role"], avatar=avatar):
        st.markdown(chat["content"])

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
        memory_text = "\n".join([f"{'【主神】' if c['role']=='user' else '【剧情】'}: {c['content']}" for c in st.session_state.history[-4:]])
        instruction = f"【主神指令】：{god_command}" if god_command else "继续剧情，制造危机。"
        
        if god_command:
            st.session_state.history.append({"role": "user", "content": f"**神谕：** {god_command}"})

        with st.spinner("命运演化中..."):
            # Story AI (注入了自定义世界观！)
            story_prompt = f"""
            你是一个无限流游戏DM。
            【当前副本】：{selected_option}
            【世界观设定】：{current_world_setting}
            
            主角：{player_a} (HP:{st.session_state.hp})。同伴：{player_b}。
            背包：{st.session_state.inventory}。
            
            【前情】：{memory_text}
            【指令】：{instruction}
            
            要求：300字内。严格遵循【世界观设定】的风格。
            """
            
            try:
                story_res = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": story_prompt}],
                    stream=False
                )
                story_content = story_res.choices[0].message.content
                st.session_state.history.append({"role": "assistant", "content": story_content})
                
                # Logic AI
                logic_prompt = f"""
                阅读剧情：'''{story_content}'''
                分析状态变化，严格JSON输出：
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
                
                hp_delta = data.get("hp_change", 0)
                if hp_delta != 0:
                    st.session_state.hp += hp_delta
                    if hp_delta < 0: st.toast(f"🩸 伤害 {hp_delta}", icon="🤕")
                    else: st.toast(f"💚 恢复 +{hp_delta}", icon="💊")
                
                bond_delta = data.get("bond_change", 0)
                if bond_delta != 0:
                    st.session_state.bond = max(0, min(100, st.session_state.bond + bond_delta))
                    st.toast(f"❤️ 羁绊 {bond_delta}", icon="💞")
                
                new_item = data.get("new_item")
                if new_item:
                    st.session_state.inventory.append(new_item)
                    st.toast(f"🎒 获得：{new_item}", icon="🎁")

                st.session_state.turn += 1
                st.rerun()
                
            except Exception as e:
                print(f"Logic Error: {e}")
                st.rerun()


