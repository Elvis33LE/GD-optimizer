import streamlit as st
import json
import base64
import os
import textwrap
from itertools import combinations

# --- 1. SETUP & CONFIGURATION ---
st.set_page_config(page_title="Vanguard 2.0: Strategy Engine", layout="wide")

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
    st.session_state.active_waves = [
        pool[0] if len(pool) > 0 else list(enemies_db.keys())[0],
        pool[1] if len(pool) > 1 else list(enemies_db.keys())[0],
        pool[2] if len(pool) > 2 else list(enemies_db.keys())[0]
    ]


# --- 4. SCORING LOGIC ENGINE ---
def calculate_single_score(enemy_id, tower_id):
    """Calculates score for ONE tower against ONE enemy."""
    enemy = enemies_db[enemy_id]
    tower = towers_db[tower_id]

    score = 50
    notes = []

    # 1. Weakness Match
    if tower['type'] in enemy.get('weakness_types', []):
        score += 25
        notes.append(f"⚡ Weak to {tower['type']}")

    for tag in tower.get('damage_tags', []):
        if tag in enemy.get('weakness_types', []):
            score += 15
            notes.append(f"🎯 {tag} Weakness")

    # 2. Resistance Penalty
    if tower['type'] in enemy.get('resistance_types', []):
        score -= 30
        notes.append(f"🛡️ Resists {tower['type']}")

    for tag in tower.get('damage_tags', []):
        if tag in enemy.get('resistance_types', []):
            score -= 20
            notes.append(f"🚫 Resists {tag}")

    # 3. Tactical Tags & Immunities
    enemy_tags = enemy.get('tags', [])
    enemy_immunities = enemy.get('immunities', [])

    # Stealth
    if "Invisible" in enemy_tags or "Stealth" in enemy_tags:
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
    if "Swarm" in enemy_tags or "Splitter" in enemy_tags:
        if "Area" in tower.get('damage_tags', []) or "Chain" in tower.get('role', ''):
            score += 20
            notes.append("🌊 Anti-Swarm")
        elif "Single Target" in tower.get('role', ''):
            score -= 10
            notes.append("⚠️ Poor vs Swarm")

    # Immunities
    if "Paralysis" in enemy_immunities and "Paralyze" in tower.get('damage_tags', []):
        score -= 50
        notes.append("⛔ Immune to Paralysis")

    if "Slow" in enemy_immunities and "Slow" in tower.get('damage_tags', []):
        score -= 30
        notes.append("⛔ Immune to Slow")

    if "Projectile Block" in enemy_tags:
        if "Projectile" in tower.get('damage_tags', []):
            score -= 100
            notes.append("❌ BLOCKED")
        elif "Beam" in tower.get('damage_tags', []) or "Lightning" in tower.get('damage_tags', []):
            score += 20
            notes.append("✨ Bypasses Block")

    return score, ", ".join(notes)


def solve_optimal_loadout(wave_enemies, inventory_towers):
    """
    Finds the BEST distribution of 9 unique towers (3 per wave).
    """
    if len(inventory_towers) < 9:
        return None, "Error: You need at least 9 towers in inventory to fill 3 waves!"

    # Step A: Pre-calculate scores matrix
    # scores[wave_index][tower_id] = score
    scores_matrix = []
    for enemy_id in wave_enemies:
        wave_scores = {}
        for t_id in inventory_towers:
            s, _ = calculate_single_score(enemy_id, t_id)
            wave_scores[t_id] = s
        scores_matrix.append(wave_scores)

    # Step B: Select the Top 9 Contenders
    # To save calculation time, we don't permute 20 towers. We pick the 9 most useful ones.
    # Utility = Sum of scores across all 3 waves (how generally good is this tower?)
    tower_utility = {}
    for t_id in inventory_towers:
        # Sum of scores across all 3 waves
        tower_utility[t_id] = sum(scores_matrix[w][t_id] for w in range(3))

    # Sort and take top 9
    top_9_towers = sorted(tower_utility.keys(), key=lambda x: tower_utility[x], reverse=True)[:9]

    # Step C: Combinatorial Optimization
    # We need to split these 9 towers into 3 groups of 3.
    # Total combinations = (9 choose 3) * (6 choose 3) * (3 choose 3) = 84 * 20 * 1 = 1680 checks. Very fast.

    best_total_score = -float('inf')
    best_allocation = None

    # Pick 3 for Wave 1
    for w1_set in combinations(top_9_towers, 3):
        remaining_6 = [x for x in top_9_towers if x not in w1_set]

        # Pick 3 for Wave 2
        for w2_set in combinations(remaining_6, 3):
            # Remaining 3 go to Wave 3
            w3_set = [x for x in remaining_6 if x not in w2_set]

            # Calculate Total Score for this permutation
            s1 = sum(scores_matrix[0][t] for t in w1_set)
            s2 = sum(scores_matrix[1][t] for t in w2_set)
            s3 = sum(scores_matrix[2][t] for t in w3_set)

            total = s1 + s2 + s3

            if total > best_total_score:
                best_total_score = total
                best_allocation = [w1_set, w2_set, w3_set]

    return best_allocation, None


# --- 5. PAGE: SETUP ---
if st.session_state.page == 'setup':
    st.title("⚙️ Vanguard Mission Control")
    st.caption(f"Configuring: {defaults.get('weekly_mode_name', 'Custom Week')}")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. Weekly Inventory")
        st.info("Select at least 9 towers.")
        all_tower_ids = list(towers_db.keys())
        format_tower = lambda x: f"{towers_db[x]['name']} ({towers_db[x]['type']})"

        selected_towers = st.multiselect(
            "Available Towers",
            options=all_tower_ids,
            default=st.session_state.user_towers,
            format_func=format_tower
        )

        # Validation
        if len(selected_towers) < 9:
            st.error(f"❌ You have selected {len(selected_towers)}/9 required towers.")
        else:
            st.success(f"✅ {len(selected_towers)} Towers ready.")
            st.session_state.user_towers = selected_towers

    with col2:
        st.subheader("2. Weekly Threats")
        all_enemy_ids = list(enemies_db.keys())
        format_enemy = lambda x: f"{'👑 ' if enemies_db[x]['type'] == 'Boss' else '👾 '}{enemies_db[x]['name']}"

        selected_pool = st.multiselect(
            "Enemy Pool",
            options=all_enemy_ids,
            default=st.session_state.weekly_enemy_pool,
            format_func=format_enemy
        )
        st.session_state.weekly_enemy_pool = selected_pool

    st.markdown("---")
    _, c_btn, _ = st.columns([1, 2, 1])
    with c_btn:
        disabled = len(st.session_state.user_towers) < 9
        if st.button("🚀 Enter Combat Calculator", type="primary", use_container_width=True, disabled=disabled):
            st.session_state.page = 'main'
            st.rerun()

# --- 6. PAGE: MAIN CALCULATOR ---
elif st.session_state.page == 'main':
    with st.sidebar:
        st.header("Settings")
        if st.button("⚙️ Edit Weekly Setup", use_container_width=True):
            st.session_state.page = 'setup'
            st.rerun()

        st.divider()
        st.subheader("Current Inventory")
        for t_id in st.session_state.user_towers:
            t = towers_db[t_id]
            st.markdown(f"<span style='color:{TYPE_COLORS.get(t['type'], '#fff')}'>●</span> {t['name']}",
                        unsafe_allow_html=True)

    st.title("🛡️ Vanguard Strategy Engine")

    pool_options = st.session_state.weekly_enemy_pool

    if not pool_options:
        st.error("No enemies defined! Please go to Setup.")
    else:
        # Wave Selection
        cols = st.columns(3)
        enemy_fmt = lambda x: f"{'👑' if enemies_db[x]['type'] == 'Boss' else '👾'} {enemies_db[x]['name']}"

        for i, col in enumerate(cols):
            with col:
                current_val = st.session_state.active_waves[i]
                try:
                    idx = pool_options.index(current_val)
                except ValueError:
                    idx = 0
                sel = st.selectbox(f"Wave {i + 1}", options=pool_options, index=idx, format_func=enemy_fmt, key=f"w{i}")
                st.session_state.active_waves[i] = sel

        st.divider()

        # --- OPTIMIZATION ENGINE ---
        with st.spinner("Calculating optimal unique loadouts..."):
            best_loadout, error = solve_optimal_loadout(
                st.session_state.active_waves,
                st.session_state.user_towers
            )

        if error:
            st.error(error)
        else:
            # --- MISSION BRIEFING ---
            st.subheader("📋 Optimal Squad Assignment")

            for i, wave_towers in enumerate(best_loadout):
                enemy = enemies_db[st.session_state.active_waves[i]]
                names = [towers_db[tid]['name'] for tid in wave_towers]
                st.markdown(f"**Wave {i + 1}:** " + " + ".join(names))

            st.markdown("<br>", unsafe_allow_html=True)

            # --- DETAILED CARDS (Option 2: Native Containers) ---
            for i, enemy_id in enumerate(st.session_state.active_waves):
                enemy = enemies_db[enemy_id]
                wave_towers = best_loadout[i]

                # Header
                st.markdown(f"### Wave {i + 1}: **{enemy['name']}**")

                # Enemy Stats
                tags = [f"`{t}`" for t in enemy.get('tags', [])]
                weak = [f"**{w}**" for w in enemy.get('weakness_types', [])]
                res = [f"~~{r}~~" for r in enemy.get('resistance_types', [])]
                immu = [f"🚫 {im}" for im in enemy.get('immunities', [])]

                info = f"{enemy['faction']}"
                if tags: info += f" | {' '.join(tags)}"
                if weak: info += f" | Weak: {' '.join(weak)}"
                if res: info += f" | Resist: {' '.join(res)}"
                if immu: info += f" | Immunities: {' '.join(immu)}"
                st.caption(info)

                # Render 3 Cards for this wave
                cols = st.columns(3)

                # Sort the 3 chosen towers by their specific score for this enemy
                # So the best of the 3 appears first
                sorted_wave_towers = sorted(
                    wave_towers,
                    key=lambda tid: calculate_single_score(enemy_id, tid)[0],
                    reverse=True
                )

                for idx, t_id in enumerate(sorted_wave_towers):
                    with cols[idx]:
                        t_data = towers_db[t_id]
                        score, note = calculate_single_score(enemy_id, t_id)

                        # Border Color logic
                        if score >= 80:
                            b_color = "green"
                        elif score <= 40:
                            b_color = "red"
                        else:
                            b_color = "orange"  # default grey/orange

                        # Native Streamlit Container
                        with st.container(border=True):
                            c1, c2 = st.columns([3, 1])
                            with c1:
                                st.markdown(f"**{t_data['name']}**")
                                st.caption(f"{t_data['type']} • {t_data['role']}")
                            with c2:
                                st.markdown(f"**{score}**")

                            # Divider line visually
                            st.markdown("---")

                            # Note coloring
                            if score >= 80:
                                st.markdown(f":green[{note}]")
                            elif score <= 40:
                                st.markdown(f":red[{note}]")
                            else:
                                st.markdown(f"{note}")

                st.markdown("<br>", unsafe_allow_html=True)