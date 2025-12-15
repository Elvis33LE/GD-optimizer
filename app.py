import streamlit as st
import json
import os
import textwrap
from itertools import combinations
import base64

# --- 1. SETUP & CONFIGURATION ---
st.set_page_config(page_title="Vanguard 2.0: Strategy Engine", layout="wide")

# Paths
DATA_DIR = "data"
DEFAULTS_FILE = os.path.join(DATA_DIR, "defaults.json")
TOWERS_FILE = os.path.join(DATA_DIR, "towers.json")
ENEMIES_FILE = os.path.join(DATA_DIR, "enemies.json")
CARDS_FILE = os.path.join(DATA_DIR, "cards.json")

# Color Mapping for UI
TYPE_COLORS = {
    "Physical": "#95a5a6",
    "Fire": "#e67e22",
    "Electric": "#9b59b6",
    "Energy": "#2ecc71",
    "Force-field": "#3498db"
}


# --- 2. DATA LOADING ---
@st.cache_data
def load_data():
    with open(TOWERS_FILE, 'r') as f:
        towers = json.load(f)
    with open(ENEMIES_FILE, 'r') as f:
        enemies = json.load(f)
    with open(CARDS_FILE, 'r') as f:
        cards = json.load(f)

    enemies_dict = {e['id']: e for e in enemies}

    # Process Synergies from Cards
    synergy_map = {}
    for c in cards:
        if c.get('type') == 'Combo' and 'combo_partner' in c:
            pair_key = frozenset({c['tower_id'], c['combo_partner']})
            if pair_key not in synergy_map:
                synergy_map[pair_key] = []
            synergy_map[pair_key].append(c)

    return towers, enemies_dict, synergy_map


def load_defaults():
    if os.path.exists(DEFAULTS_FILE):
        with open(DEFAULTS_FILE, 'r') as f: return json.load(f)
    return {}


towers_db, enemies_db, synergy_db = load_data()
defaults = load_defaults()

# --- 3. SESSION STATE ---
if 'page' not in st.session_state:
    st.session_state.page = 'setup'

if 'user_towers' not in st.session_state:
    default_ids = defaults.get("available_towers", list(towers_db.keys())[:9])
    valid_ids = [tid for tid in default_ids if tid in towers_db]
    st.session_state.user_towers = valid_ids

if 'weekly_enemy_pool' not in st.session_state:
    default_pool = defaults.get("weekly_enemy_pool", list(enemies_db.keys())[:8])
    valid_pool = [eid for eid in default_pool if eid in enemies_db]
    st.session_state.weekly_enemy_pool = valid_pool

if 'active_waves' not in st.session_state:
    pool = st.session_state.weekly_enemy_pool
    waves = []
    if pool:
        waves = [pool[0]] * 3
        for i in range(min(len(pool), 3)):
            waves[i] = pool[i]
    st.session_state.active_waves = waves


# --- 4. SCORING ENGINE ---
def calculate_single_score(enemy_id, tower_id):
    """Calculates Base Effectiveness (Level 1 Multipliers)."""
    enemy = enemies_db[enemy_id]
    tower = towers_db[tower_id]

    score = 100.0
    notes = []

    # A. Hard Counters (Immunities)
    enemy_immunities = enemy.get('immunities', [])
    enemy_tags = enemy.get('tags', [])
    tower_tags = tower.get('damage_tags', [])

    if "Paralysis" in enemy_immunities and "Paralyze" in tower_tags:
        score *= 0.1
        notes.append("⛔ Immune: Paralysis")

    if "Slow" in enemy_immunities and "Slow" in tower_tags:
        score *= 0.5
        notes.append("⛔ Immune: Slow")

    if "Projectile Block" in enemy_tags:
        if "Projectile" in tower_tags:
            score *= 0.0
            notes.append("❌ BLOCKED")
        elif "Beam" in tower_tags or "Lightning" in tower_tags:
            score *= 1.2
            notes.append("✨ Bypasses Block")

    # B. Weakness & Resistance
    is_weak = False
    if tower['type'] in enemy.get('weakness_types', []): is_weak = True
    for tag in tower_tags:
        if tag in enemy.get('weakness_types', []): is_weak = True

    if is_weak:
        score *= 1.5
        notes.append("⚡ Weakness (+50%)")

    is_resist = False
    if tower['type'] in enemy.get('resistance_types', []): is_resist = True
    for tag in tower_tags:
        if tag in enemy.get('resistance_types', []): is_resist = True

    if is_resist:
        score *= 0.5
        notes.append("🛡️ Resist (-50%)")

    # C. Tactical Tags
    if "Invisible" in enemy_tags or "Stealth" in enemy_tags:
        if "Stealth Reveal" in tower_tags:
            score *= 1.5
            notes.append("👁️ Reveals Stealth")
        elif "Area" in tower_tags:
            score *= 1.1
            notes.append("💥 AoE Hit")
        else:
            score *= 0.6
            notes.append("⚠️ Can't see")

    if "Swarm" in enemy_tags or "Splitter" in enemy_tags:
        if "Area" in tower_tags or "Chain" in tower.get('role', ''):
            score *= 1.3
            notes.append("🌊 Anti-Swarm")
        elif "Single Target" in tower.get('role', ''):
            score *= 0.8
            notes.append("⚠️ Overwhelmed")

    return int(score), ", ".join(notes)


def solve_optimal_loadout(wave_enemies, inventory_towers):
    if len(inventory_towers) < 9:
        return None, "Error: You need at least 9 towers in inventory to fill 3 waves!"

    scores_matrix = []
    for enemy_id in wave_enemies:
        wave_scores = {}
        for t_id in inventory_towers:
            s, _ = calculate_single_score(enemy_id, t_id)
            wave_scores[t_id] = s
        scores_matrix.append(wave_scores)

    tower_utility = {}
    for t_id in inventory_towers:
        tower_utility[t_id] = sum(scores_matrix[w][t_id] for w in range(3))

    top_9 = sorted(tower_utility.keys(), key=lambda x: tower_utility[x], reverse=True)[:9]

    best_total = -float('inf')
    best_allocation = None

    for w1_set in combinations(top_9, 3):
        remaining_6 = [x for x in top_9 if x not in w1_set]

        for w2_set in combinations(remaining_6, 3):
            w3_set = [x for x in remaining_6 if x not in w2_set]

            current_sets = [w1_set, w2_set, w3_set]
            current_score = 0

            for wave_idx, tower_set in enumerate(current_sets):
                wave_raw_score = sum(scores_matrix[wave_idx][t] for t in tower_set)
                multiplier = 1.0

                for pair in combinations(tower_set, 2):
                    key = frozenset(pair)
                    if key in synergy_db:
                        for card in synergy_db[key]:
                            rating = card.get('score', 5)
                            bonus = rating * 0.025
                            multiplier += bonus

                current_score += (wave_raw_score * multiplier)

            if current_score > best_total:
                best_total = current_score
                best_allocation = current_sets

    return best_allocation, None


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

    with col1:
        st.subheader("1. Weekly Inventory")
        st.info("Select at least 9 towers.")
        all_tower_ids = list(towers_db.keys())
        format_tower = lambda x: f"{towers_db[x]['name']} ({towers_db[x]['type']})"

        selected_towers = st.multiselect("Available Towers", options=all_tower_ids,
                                         default=st.session_state.user_towers, format_func=format_tower)

        if len(selected_towers) < 9:
            st.error(f"❌ Selected {len(selected_towers)}/9 required.")
        else:
            st.success(f"✅ {len(selected_towers)} Towers ready.")
            st.session_state.user_towers = selected_towers

    with col2:
        st.subheader("2. Weekly Threats")
        all_enemy_ids = list(enemies_db.keys())
        format_enemy = lambda x: f"{'👑 ' if enemies_db[x]['type'] == 'Boss' else '👾 '}{enemies_db[x]['name']}"
        selected_pool = st.multiselect("Enemy Pool", options=all_enemy_ids, default=st.session_state.weekly_enemy_pool,
                                       format_func=format_enemy)
        st.session_state.weekly_enemy_pool = selected_pool

    st.markdown("---")
    _, c_btn, _ = st.columns([1, 2, 1])
    with c_btn:
        disabled = len(st.session_state.user_towers) < 9
        if st.button("🚀 Enter Combat Calculator", type="primary", use_container_width=True, disabled=disabled):
            st.session_state.page = 'main'
            st.rerun()

# --- 7. PAGE: MAIN ---
elif st.session_state.page == 'main':
    with st.sidebar:
        st.header("Settings")
        if st.button("⚙️ Edit Weekly Setup", use_container_width=True):
            st.session_state.page = 'setup'
            st.rerun()
        st.divider()
        st.subheader("Active Inventory")
        for t_id in st.session_state.user_towers:
            t = towers_db[t_id]
            st.markdown(f"<span style='color:{TYPE_COLORS.get(t['type'], '#fff')}'>●</span> {t['name']}",
                        unsafe_allow_html=True)

    st.title("🛡️ Vanguard Strategy Engine")

    pool_options = st.session_state.weekly_enemy_pool

    if not pool_options:
        st.error("No enemies defined! Please go to Setup.")
    else:
        cols = st.columns(3)
        enemy_fmt = lambda x: f"{'👑' if enemies_db[x]['type'] == 'Boss' else '👾'} {enemies_db[x]['name']}"

        for i, col in enumerate(cols):
            with col:
                current_val = st.session_state.active_waves[i]
                try:
                    idx = pool_options.index(current_val)
                except:
                    idx = 0
                sel = st.selectbox(f"Wave {i + 1}", options=pool_options, index=idx, format_func=enemy_fmt, key=f"w{i}")
                st.session_state.active_waves[i] = sel

        st.divider()

        with st.spinner("Analyzing enemy data & synergy matrices..."):
            best_loadout, error = solve_optimal_loadout(st.session_state.active_waves, st.session_state.user_towers)

        if error:
            st.error(error)
        else:
            # --- QUICK LINEUP SUMMARY (Restored!) ---
            st.subheader("📋 Mission Briefing")

            # Build the 3 lines separately
            line1 = f"**Wave 1:** {' - '.join([towers_db[tid]['name'] for tid in best_loadout[0]])}"
            line2 = f"**Wave 2:** {' - '.join([towers_db[tid]['name'] for tid in best_loadout[1]])}"
            line3 = f"**Wave 3:** {' - '.join([towers_db[tid]['name'] for tid in best_loadout[2]])}"

            # Use double newlines (\n\n) to force distinct lines in Markdown
            st.info(f"💡 **Quick Lineup:**\n\n{line1}\n\n{line2}\n\n{line3}")

            st.divider()

            # --- DETAILED RESULTS ---
            for i, enemy_id in enumerate(st.session_state.active_waves):
                enemy = enemies_db[enemy_id]
                wave_towers = best_loadout[i]

                with st.container(border=True):
                    c_head, c_tags = st.columns([1, 2])
                    with c_head:
                        st.markdown(f"#### Wave {i + 1}: {enemy['name']}")
                        st.caption(f"Faction: {enemy['faction']}")
                    with c_tags:
                        tags = [f"`{t}`" for t in enemy.get('tags', [])]
                        if tags: st.markdown(" ".join(tags))

                        weak = enemy.get('weakness_types', [])
                        if weak: st.markdown(f"⚡ **Weak:** {', '.join(weak)}")

                        res = enemy.get('resistance_types', [])
                        if res: st.markdown(f"🛡️ **Resist:** {', '.join(res)}")

                    st.divider()

                    active_combos = []
                    for pair in combinations(wave_towers, 2):
                        key = frozenset(pair)
                        if key in synergy_db:
                            for c in synergy_db[key]:
                                active_combos.append(c)

                    if active_combos:
                        st.markdown("**🔗 Active Synergies:**")
                        for c in active_combos:
                            score = c.get('score', 5)
                            color = "green" if score >= 8 else "orange"
                            st.markdown(f"- :{color}[**{c['name']}**] (Rating: {score}/10): {c['description']}")
                        st.markdown("")

                    t_cols = st.columns(3)
                    sorted_towers = sorted(wave_towers, key=lambda tid: calculate_single_score(enemy_id, tid)[0],
                                           reverse=True)

                    for idx, t_id in enumerate(sorted_towers):
                        with t_cols[idx]:
                            t_data = towers_db[t_id]
                            score, note = calculate_single_score(enemy_id, t_id)
                            color = TYPE_COLORS.get(t_data['type'], "#fff")
                            icon_svg = get_svg(t_data.get('icon', 'beam'), color)
                            b64_svg = base64.b64encode(icon_svg.encode('utf-8')).decode("utf-8")

                            html_code = textwrap.dedent(f"""
                            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 10px; display: flex; align-items: center; gap: 10px;">
                                <img src="data:image/svg+xml;base64,{b64_svg}" style="width:40px; height:40px;">
                                <div>
                                    <div style="font-weight:bold; color:#fff; font-size:0.95em;">{t_data['name']}</div>
                                    <div style="font-size:0.75em; color:{color};">{t_data['type']}</div>
                                </div>
                                <div style="margin-left:auto; text-align:right;">
                                    <div style="font-weight:bold; font-size:1.1em; color:#ddd;">{score}</div>
                                </div>
                            </div>
                            <div style="font-size:0.7em; color:#aaa; margin-top:4px; padding-left:4px;">
                                {note}
                            </div>
                            """)
                            st.markdown(html_code, unsafe_allow_html=True)

            st.markdown("<br><br>", unsafe_allow_html=True)
