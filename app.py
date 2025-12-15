import streamlit as st
import json
import base64
import os
import textwrap

# --- 1. SETUP & CONFIGURATION ---
st.set_page_config(page_title="Vanguard 2.0: Knowledge Base", layout="wide")

# Paths
DATA_DIR = "data"
DEFAULTS_FILE = os.path.join(DATA_DIR, "defaults.json")
TOWERS_FILE = os.path.join(DATA_DIR, "towers.json")
ENEMIES_FILE = os.path.join(DATA_DIR, "enemies.json")

# Color Mapping for UI
TYPE_COLORS = {
    "Physical": "#95a5a6",
    "Fire": "#e67e22",
    "Electric": "#9b59b6",
    "Energy": "#2ecc71",
    "Force-field": "#3498db"
}


# --- 2. DATA LOADING & CACHING ---
@st.cache_data
def load_data():
    with open(TOWERS_FILE, 'r') as f: towers = json.load(f)
    with open(ENEMIES_FILE, 'r') as f: enemies = json.load(f)
    enemies_dict = {e['id']: e for e in enemies}
    return towers, enemies_dict


def load_defaults():
    if os.path.exists(DEFAULTS_FILE):
        with open(DEFAULTS_FILE, 'r') as f: return json.load(f)
    return {}


towers_db, enemies_db = load_data()
defaults = load_defaults()

# --- 3. SESSION STATE MANAGEMENT ---
if 'page' not in st.session_state:
    st.session_state.page = 'setup'

# Initialize Available Towers (Inventory)
if 'user_towers' not in st.session_state:
    default_ids = defaults.get("available_towers", list(towers_db.keys())[:8])
    # Validate IDs exist in DB
    valid_ids = [tid for tid in default_ids if tid in towers_db]
    st.session_state.user_towers = valid_ids

# Initialize Weekly Enemy Pool (The 8 Enemies)
if 'weekly_enemy_pool' not in st.session_state:
    default_pool = defaults.get("weekly_enemy_pool", list(enemies_db.keys())[:8])
    valid_pool = [eid for eid in default_pool if eid in enemies_db]
    st.session_state.weekly_enemy_pool = valid_pool

# Initialize Active Waves (The 3 selected for calculation)
if 'active_waves' not in st.session_state:
    # Default to the first 3 of the weekly pool
    pool = st.session_state.weekly_enemy_pool
    st.session_state.active_waves = [
        pool[0] if len(pool) > 0 else list(enemies_db.keys())[0],
        pool[1] if len(pool) > 1 else list(enemies_db.keys())[0],
        pool[2] if len(pool) > 2 else list(enemies_db.keys())[0]
    ]


# --- 4. SCORING LOGIC ENGINE ---
def calculate_score(enemy_id, tower_id):
    enemy = enemies_db[enemy_id]
    tower = towers_db[tower_id]

    score = 50  # Base score
    notes = []

    # 1. Weakness Match (+25)
    if tower['type'] in enemy.get('weakness_types', []):
        score += 25
        notes.append(f"⚡ Weak to {tower['type']}")

    for tag in tower.get('damage_tags', []):
        if tag in enemy.get('weakness_types', []):
            score += 15
            notes.append(f"🎯 {tag} Weakness")

    # 2. Resistance Penalty (-30)
    if tower['type'] in enemy.get('resistance_types', []):
        score -= 30
        notes.append(f"🛡️ Resists {tower['type']}")

    for tag in tower.get('damage_tags', []):
        if tag in enemy.get('resistance_types', []):
            score -= 20
            notes.append(f"🚫 Resists {tag}")

    # 3. Tactical Tags
    # Stealth
    if "Invisible" in enemy.get('tags', []) or "Stealth" in enemy.get('tags', []):
        if "Stealth Reveal" in tower.get('damage_tags', []):
            score += 40
            notes.append("👁️ Reveals Stealth")
        elif "Area" in tower.get('damage_tags', []):
            score += 10
            notes.append("💥 AoE hits Stealth")
        else:
            score -= 20
            notes.append("⚠️ Misses Stealth")

    # Swarms
    if "Swarm" in enemy.get('tags', []) or "Splitter" in enemy.get('tags', []):
        if "Area" in tower.get('damage_tags', []) or "Chain" in tower.get('role', ''):
            score += 20
            notes.append("🌊 Anti-Swarm")
        elif "Single Target" in tower.get('role', ''):
            score -= 10
            notes.append("⚠️ Poor vs Swarm")

    # Shields / Projectile Blockers
    if "Projectile Block" in enemy.get('tags', []):
        if "Projectile" in tower.get('damage_tags', []):
            score -= 100  # Hard Countered
            notes.append("❌ BLOCKED")
        elif "Beam" in tower.get('damage_tags', []) or "Lightning" in tower.get('damage_tags', []):
            score += 20
            notes.append("✨ Bypasses Block")

    return score, ", ".join(notes)


# --- 5. VISUAL ASSETS ---
def get_svg(icon_name, color):
    paths = {
        "tesla": f'<circle cx="50" cy="85" r="15" fill="{color}" opacity="0.3"/><path d="M50,25 L30,5 M50,25 L70,5" stroke="#fff" stroke-width="2"/><circle cx="50" cy="50" r="20" fill="none" stroke="{color}" stroke-width="4"/>',
        "skyguard": f'<rect x="30" y="40" width="15" height="30" fill="{color}"/><rect x="55" y="40" width="15" height="30" fill="{color}"/><path d="M20,80 L80,80" stroke="{color}" stroke-width="4"/>',
        "guardian": f'<rect x="40" y="20" width="20" height="20" rx="4" fill="{color}"/><path d="M30,80 L70,80 L60,30 L40,30 Z" fill="{color}" opacity="0.5"/>',
        "thunderbolt": f'<circle cx="50" cy="50" r="25" fill="{color}"/><path d="M50,15 L60,40 L40,40 L50,85" fill="#fff"/>',
        "firewheel": f'<circle cx="50" cy="50" r="30" fill="none" stroke="{color}" stroke-width="4" stroke-dasharray="10,5"/><circle cx="50" cy="50" r="15" fill="{color}"/>',
        "aeroblast": f'<circle cx="50" cy="50" r="20" fill="none" stroke="{color}" stroke-width="5"/><rect x="45" y="20" width="10" height="60" fill="{color}" transform="rotate(45 50 50)"/>',
        "vortex": f'<circle cx="50" cy="50" r="35" fill="none" stroke="{color}" stroke-width="2"/><circle cx="50" cy="50" r="10" fill="#000" stroke="#fff" stroke-width="2"/>',
        "beam": f'<path d="M20,80 L80,80 L50,20 Z" fill="none" stroke="{color}" stroke-width="3"/><line x1="50" y1="20" x2="50" y2="80" stroke="#fff" stroke-width="2"/>',
        "disruption": f'<circle cx="30" cy="50" r="10" fill="{color}"/><circle cx="70" cy="50" r="10" fill="{color}"/><path d="M30,50 L70,50" stroke="#fff" stroke-width="2"/>'
    }
    path = paths.get(icon_name, f'<circle cx="50" cy="50" r="30" fill="{color}"/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">{path}</svg>'


# --- 6. PAGE: SETUP ---
if st.session_state.page == 'setup':
    st.title("⚙️ Vanguard Mission Control")
    st.caption(f"Configuring: {defaults.get('weekly_mode_name', 'Custom Week')}")

    col1, col2 = st.columns(2)

    # 1. Tower Selection
    with col1:
        st.subheader("1. Weekly Inventory")
        st.info("Select available towers for this week.")
        all_tower_ids = list(towers_db.keys())
        format_tower = lambda x: f"{towers_db[x]['name']} ({towers_db[x]['type']})"

        selected_towers = st.multiselect(
            "Available Towers",
            options=all_tower_ids,
            default=st.session_state.user_towers,
            format_func=format_tower
        )
        st.session_state.user_towers = selected_towers

    # 2. Enemy Pool Selection
    with col2:
        st.subheader("2. Weekly Threats (8 Max)")
        st.info("Select the 6 Normal + 2 Bosses active this week.")
        all_enemy_ids = list(enemies_db.keys())
        format_enemy = lambda x: f"{'👑 ' if enemies_db[x]['type'] == 'Boss' else '👾 '}{enemies_db[x]['name']}"

        selected_pool = st.multiselect(
            "Enemy Pool",
            options=all_enemy_ids,
            default=st.session_state.weekly_enemy_pool,
            format_func=format_enemy
        )

        # Validation visual aid
        count = len(selected_pool)
        if count == 8:
            st.success(f"Perfect! {count} enemies selected.")
        else:
            st.warning(f"Selected {count} enemies. (Recommended: 8)")

        st.session_state.weekly_enemy_pool = selected_pool

    st.markdown("---")
    _, c_btn, _ = st.columns([1, 2, 1])
    with c_btn:
        if st.button("🚀 Enter Combat Calculator", type="primary", use_container_width=True):
            # Pre-fill active waves if they are invalid (not in pool)
            pool = st.session_state.weekly_enemy_pool
            if pool:
                # Ensure current selections are valid, else reset to first in pool
                for i in range(3):
                    if st.session_state.active_waves[i] not in pool:
                        st.session_state.active_waves[i] = pool[0]
            st.session_state.page = 'main'
            st.rerun()

# --- 7. PAGE: MAIN CALCULATOR ---
elif st.session_state.page == 'main':
    # Sidebar
    with st.sidebar:
        st.header("Settings")
        if st.button("⚙️ Edit Weekly Setup", use_container_width=True):
            st.session_state.page = 'setup'
            st.rerun()

        st.divider()
        st.subheader("Inventory")
        for t_id in st.session_state.user_towers:
            t = towers_db[t_id]
            st.markdown(f"<span style='color:{TYPE_COLORS.get(t['type'], '#fff')}'>●</span> {t['name']}",
                        unsafe_allow_html=True)

        st.divider()
        st.subheader("Threat Pool")
        for e_id in st.session_state.weekly_enemy_pool:
            e = enemies_db[e_id]
            icon = "👑" if e['type'] == 'Boss' else "👾"
            st.caption(f"{icon} {e['name']}")

    st.title("🛡️ Vanguard Strategy Engine")

    # Wave Selectors (Restricted to Weekly Pool)
    pool_options = st.session_state.weekly_enemy_pool

    if not pool_options:
        st.error("No enemies defined in Setup! Go back and select enemies.")
    else:
        cols = st.columns(3)
        enemy_fmt = lambda x: f"{'👑' if enemies_db[x]['type'] == 'Boss' else '👾'} {enemies_db[x]['name']}"

        for i, col in enumerate(cols):
            with col:
                # Get current selection index safely
                current_val = st.session_state.active_waves[i]
                try:
                    idx = pool_options.index(current_val)
                except ValueError:
                    idx = 0

                sel = st.selectbox(
                    f"Wave {i + 1}",
                    options=pool_options,
                    index=idx,
                    format_func=enemy_fmt,
                    key=f"wave_sel_{i}"
                )
                st.session_state.active_waves[i] = sel

        st.divider()

        # Calculation & Render
        for i, enemy_id in enumerate(st.session_state.active_waves):
            enemy = enemies_db[enemy_id]

            # Header
            st.markdown(f"### Wave {i + 1}: **{enemy['name']}**")

            # Context Tags
            tags = [f"`{t}`" for t in enemy.get('tags', [])]
            weak = [f"**{w}**" for w in enemy.get('weakness_types', [])]
            res = [f"~~{r}~~" for r in enemy.get('resistance_types', [])]

            info = f"{enemy['faction']}"
            if tags: info += f" | {' '.join(tags)}"
            if weak: info += f" | Weak: {' '.join(weak)}"
            if res: info += f" | Resist: {' '.join(res)}"
            st.caption(info)

            # Scoring
            scored_towers = []
            for t_id in st.session_state.user_towers:
                score, note = calculate_score(enemy_id, t_id)
                scored_towers.append({
                    "id": t_id,
                    "score": score,
                    "note": note,
                    "data": towers_db[t_id]
                })

            scored_towers.sort(key=lambda x: x['score'], reverse=True)
            top_picks = scored_towers[:3]

            # Cards
            c_cols = st.columns(3)
            for idx, item in enumerate(top_picks):
                t_data = item['data']
                score = item['score']
                color = TYPE_COLORS.get(t_data['type'], "#fff")
                score_color = "#2ecc71" if score >= 80 else "#f1c40f" if score >= 50 else "#e74c3c"

                icon_svg = get_svg(t_data.get('icon', 'beam'), color)
                b64_svg = base64.b64encode(icon_svg.encode('utf-8')).decode("utf-8")

                with c_cols[idx]:
                    # We use textwrap.dedent to remove the indentation so Streamlit renders it as HTML, not code.
                    html_code = textwrap.dedent(f"""
                                    <div style="
                                        background-color: #262730; 
                                        border: 1px solid #444; 
                                        border-bottom: 3px solid {score_color}; 
                                        border-radius: 8px; 
                                        padding: 10px; 
                                        text-align: center; 
                                        height: 200px;
                                        display: flex; flex-direction: column; justify-content: space-between; align-items: center;">

                                        <img src="data:image/svg+xml;base64,{b64_svg}" style="width:50px; height:50px; opacity:0.9;">

                                        <div style="margin-top:5px;">
                                            <div style="font-weight:bold; color: #fff; font-size:1.1em;">{t_data['name']}</div>
                                            <div style="font-size:0.8em; color: {color};">{t_data['type']} • {t_data['role']}</div>
                                        </div>

                                        <div style="width:100%;">
                                            <div style="font-size:1.2em; font-weight:900; color:{score_color};">{score} pts</div>
                                            <div style="font-size:0.7em; color: #aaa; line-height:1.2; min-height:30px;">{item['note']}</div>
                                        </div>
                                    </div>
                                    """)
                    st.markdown(html_code, unsafe_allow_html=True)