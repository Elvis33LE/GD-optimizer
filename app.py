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
USER_CONFIG_FILE = "user_config.json"

# Color Mapping for UI
TYPE_COLORS = {
    "Physical": "#95a5a6",
    "Fire": "#e67e22",
    "Electric": "#9b59b6",
    "Energy": "#2ecc71",
    "Force-field": "#3498db"
}


# --- 2. DATA LOADING & PERSISTENCE ---
@st.cache_data
def load_data():
    with open(TOWERS_FILE, 'r') as f:
        towers = json.load(f)
    with open(ENEMIES_FILE, 'r') as f:
        enemies = json.load(f)
    with open(CARDS_FILE, 'r') as f:
        cards = json.load(f)

    enemies_dict = {e['id']: e for e in enemies}

    # Process Synergies & Card Lookup
    synergy_map = {}
    cards_by_tower = {}

    for c in cards:
        if c.get('type') == 'Combo' and 'combo_partner' in c:
            pair_key = frozenset({c['tower_id'], c['combo_partner']})
            if pair_key not in synergy_map:
                synergy_map[pair_key] = []
            synergy_map[pair_key].append(c)

        tid = c['tower_id']
        tier = c['tier']
        if tid not in cards_by_tower: cards_by_tower[tid] = {1: [], 2: [], 3: []}
        if tier in cards_by_tower[tid]:
            cards_by_tower[tid][tier].append(c)

    return towers, enemies_dict, synergy_map, cards_by_tower


def load_defaults():
    if os.path.exists(DEFAULTS_FILE):
        with open(DEFAULTS_FILE, 'r') as f: return json.load(f)
    return {}


def load_user_config():
    if os.path.exists(USER_CONFIG_FILE):
        try:
            with open(USER_CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return None
    return None


def save_user_config():
    config_data = {
        "user_towers": st.session_state.user_towers,
        "weekly_enemy_pool": st.session_state.weekly_enemy_pool,
        "card_setup": st.session_state.card_setup
    }
    with open(USER_CONFIG_FILE, 'w') as f:
        json.dump(config_data, f, indent=4)
    st.toast("✅ Setup saved to disk! It will load next time.", icon="💾")


towers_db, enemies_db, synergy_db, cards_db = load_data()
defaults = load_defaults()
user_conf = load_user_config()

# --- 3. SESSION STATE INITIALIZATION ---
if 'page' not in st.session_state:
    st.session_state.page = 'setup'

if 'user_towers' not in st.session_state:
    if user_conf and 'user_towers' in user_conf:
        st.session_state.user_towers = user_conf['user_towers']
    else:
        default_ids = defaults.get("available_towers", list(towers_db.keys())[:9])
        st.session_state.user_towers = [tid for tid in default_ids if tid in towers_db]

if 'weekly_enemy_pool' not in st.session_state:
    if user_conf and 'weekly_enemy_pool' in user_conf:
        st.session_state.weekly_enemy_pool = user_conf['weekly_enemy_pool']
    else:
        default_pool = defaults.get("weekly_enemy_pool", list(enemies_db.keys())[:8])
        st.session_state.weekly_enemy_pool = [eid for eid in default_pool if eid in enemies_db]

if 'card_setup' not in st.session_state:
    if user_conf and 'card_setup' in user_conf:
        st.session_state.card_setup = user_conf['card_setup']
    else:
        st.session_state.card_setup = defaults.get("weekly_card_setup", {})

if 'active_waves' not in st.session_state:
    pool = st.session_state.weekly_enemy_pool
    waves = []
    if pool:
        waves = [pool[0]] * 3
        for i in range(min(len(pool), 3)):
            waves[i] = pool[i]
    st.session_state.active_waves = waves


# --- 4. SCORING & OPTIMIZATION LOGIC ---

def get_combo_tags(description, name):
    desc = description.lower() + " " + name.lower()
    tags = set()
    if any(x in desc for x in ["fire", "flame", "burn", "ignition"]): tags.add("Fire")
    if any(x in desc for x in ["lightning", "shock", "paralyze", "thunder", "electric"]): tags.add("Electric")
    if any(x in desc for x in ["laser", "beam", "energy", "refraction"]): tags.add("Energy")
    if any(x in desc for x in ["physical", "shell", "bullet", "mine", "impact"]): tags.add("Physical")
    if any(x in desc for x in ["force", "black hole", "pull", "teleport", "disruption"]): tags.add("Force-field")
    if "vulnerable" in desc: tags.add("Vulnerable")
    if "slow" in desc: tags.add("Slow")
    return tags


def analyze_user_setup(user_setup):
    active_conditions = set()
    for tower_id, config in user_setup.items():
        all_cards = config.get("tier_1", []) + config.get("tier_2", [])
        all_text = " ".join([str(c).lower() for c in all_cards if c])
        if any(x in all_text for x in ["ignition", "burn", "flame"]): active_conditions.add("Burn")
        if any(x in all_text for x in ["paraly", "shock"]): active_conditions.add("Paralyze")
        if any(x in all_text for x in ["slow", "stasis", "matrix"]): active_conditions.add("Slow")
        if any(x in all_text for x in ["vulnerable", "mark"]): active_conditions.add("Vulnerable")
    return active_conditions


def get_active_chains_text(tower_id):
    if tower_id not in st.session_state.card_setup: return ""
    setup = st.session_state.card_setup[tower_id]
    selected_names = set([c for c in (setup.get("tier_1", []) + setup.get("tier_2", [])) if c])
    chains = {}
    for tier in [1, 2]:
        for card in cards_db.get(tower_id, {}).get(tier, []):
            if card['name'] in selected_names and 'chain_group' in card:
                group = card['chain_group']
                step = card['chain_step']
                if group not in chains or step > chains[group]:
                    chains[group] = step
    if not chains: return ""
    parts = []
    for group, step in chains.items():
        roman = "I" * step if step < 4 else str(step)
        parts.append(f"{group} ({roman})")
    return "⛓️ " + ", ".join(parts)


def calculate_single_score(enemy_id, tower_id):
    enemy = enemies_db[enemy_id]
    tower = towers_db[tower_id]
    score = 100.0
    notes = []

    # 1. Chain Bonus
    active_chains_text = get_active_chains_text(tower_id)
    if active_chains_text:
        chain_count = active_chains_text.count("(")
        chain_bonus = chain_count * 15
        score += chain_bonus

        # 2. Tags Logic
    active_tags = set(tower.get('damage_tags', []))
    if tower_id in st.session_state.card_setup:
        setup = st.session_state.card_setup[tower_id]
        all_selected_card_names = setup.get("tier_1", []) + setup.get("tier_2", [])
        for card_name in all_selected_card_names:
            if not card_name: continue
            if any(x in card_name for x in ["Ignition", "Burning", "Flame"]): active_tags.add("Burn")
            if any(x in card_name for x in ["Paralysis", "Paralyze"]): active_tags.add("Paralyze")
            if any(x in card_name for x in ["Slow", "Stasis"]): active_tags.add("Slow")
            if any(x in card_name for x in ["Stealth Reveal", "Ignition"]): active_tags.add("Stealth Reveal")

    enemy_immunities = enemy.get('immunities', [])
    enemy_tags = enemy.get('tags', [])
    if "Paralysis" in enemy_immunities and "Paralyze" in active_tags:
        score *= 0.1
        notes.append("⛔ Immune: Paralysis")
    if "Slow" in enemy_immunities and "Slow" in active_tags:
        score *= 0.5
        notes.append("⛔ Immune: Slow")
    if "Projectile Block" in enemy_tags:
        if "Projectile" in active_tags:
            score *= 0.0
            notes.append("❌ BLOCKED")
        elif "Beam" in active_tags or "Lightning" in active_tags:
            score *= 1.2
            notes.append("✨ Bypasses Block")

    is_weak = False
    if tower['type'] in enemy.get('weakness_types', []): is_weak = True
    for tag in active_tags:
        if tag in enemy.get('weakness_types', []): is_weak = True
    if is_weak:
        score *= 1.5
        notes.append("⚡ Weakness")

    is_resist = False
    if tower['type'] in enemy.get('resistance_types', []): is_resist = True
    for tag in active_tags:
        if tag in enemy.get('resistance_types', []): is_resist = True
    if is_resist:
        score *= 0.5
        notes.append("🛡️ Resist")

    if "Invisible" in enemy_tags or "Stealth" in enemy_tags:
        if "Stealth Reveal" in active_tags:
            score += 40
            notes.append("👁️ Reveals")
        elif "Area" in active_tags:
            score += 10
            notes.append("💥 AoE")
        else:
            score *= 0.6
            notes.append("⚠️ Can't see")

    if "Swarm" in enemy_tags or "Splitter" in enemy_tags:
        if "Area" in active_tags or "Chain" in tower.get('role', ''):
            score *= 1.2
            notes.append("🌊 Anti-Swarm")
        elif "Single Target" in tower.get('role', ''):
            score *= 0.8
            notes.append("⚠️ Overwhelmed")

    return int(score), ", ".join(notes)


def solve_optimal_loadout(wave_enemies, inventory_towers, mode_2vs1=False):
    """
    Optimizes tower allocation.
    If mode_2vs1=True, it maximizes the sum of the best 2 waves only.
    """
    if len(inventory_towers) < 9:
        return None, None, "Error: You need at least 9 towers in inventory to fill 3 waves!"

    setup_conditions = analyze_user_setup(st.session_state.card_setup)
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
    best_wave_scores = []  # Store individual wave scores to identify sacrifice later

    for w1_set in combinations(top_9, 3):
        remaining_6 = [x for x in top_9 if x not in w1_set]
        for w2_set in combinations(remaining_6, 3):
            w3_set = [x for x in remaining_6 if x not in w2_set]
            current_sets = [w1_set, w2_set, w3_set]

            # Calculate score for each wave in this configuration
            current_wave_scores = []

            for wave_idx, tower_set in enumerate(current_sets):
                enemy = enemies_db[wave_enemies[wave_idx]]
                wave_score = sum(scores_matrix[wave_idx][t] for t in tower_set)
                synergy_bonus = 0

                for pair in combinations(tower_set, 2):
                    key = frozenset(pair)
                    if key in synergy_db:
                        for combo in synergy_db[key]:
                            rating = combo.get('score', 5)
                            combo_points = rating * 10
                            tags = get_combo_tags(combo['description'], combo['name'])

                            if any(t in enemy.get('weakness_types', []) for t in tags): combo_points *= 1.5
                            if any(t in enemy.get('resistance_types', []) for t in tags): combo_points *= 0.5

                            requires_burn = "burn" in combo['description'].lower()
                            requires_slow = "slow" in combo['description'].lower()
                            if requires_burn and "Burn" in setup_conditions: combo_points *= 1.4
                            if requires_slow and "Slow" in setup_conditions: combo_points *= 1.3
                            if "Vulnerable" in tags: wave_score *= 1.15

                            synergy_bonus += combo_points

                current_wave_scores.append(wave_score + synergy_bonus)

            # --- OPTIMIZATION STRATEGY ---
            if mode_2vs1:
                # Maximize sum of Top 2 scores (Sacrifice the lowest)
                optimization_metric = sum(sorted(current_wave_scores, reverse=True)[:2])
            else:
                # Maximize Total Score (Balanced)
                optimization_metric = sum(current_wave_scores)

            if optimization_metric > best_total:
                best_total = optimization_metric
                best_allocation = current_sets
                best_wave_scores = current_wave_scores

    return best_allocation, best_wave_scores, None


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

    c_save, c_load, _ = st.columns([1, 1, 3])
    with c_save:
        if st.button("💾 Save Setup", type="secondary", use_container_width=True):
            save_user_config()
    with c_load:
        if st.button("🔄 Load Weekly Defaults", type="primary", use_container_width=True):
            if os.path.exists(USER_CONFIG_FILE): os.remove(USER_CONFIG_FILE)
            defs = load_defaults()
            valid_towers = [t for t in defs.get("available_towers", []) if t in towers_db]
            st.session_state.user_towers = valid_towers
            st.session_state.weekly_enemy_pool = defs.get("weekly_enemy_pool", [])
            st.session_state.card_setup = defs.get("weekly_card_setup", {})
            st.toast("Reverted to Weekly Official Defaults!", icon="✅")
            st.rerun()

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

    st.divider()

    st.subheader("3. Card Loadout (Tier 1 & 2)")
    st.info("Set the 4 card slots per Tier. Duplicates allowed.")


    def get_default_slot(tower_id, tier, slot_idx):
        try:
            return st.session_state.card_setup[tower_id][f"tier_{tier}"][slot_idx]
        except:
            return None


    def get_opt_idx(options, item):
        try:
            return options.index(item)
        except:
            return 0


    for t_id in st.session_state.user_towers:
        t_data = towers_db[t_id]
        if t_id not in st.session_state.card_setup:
            st.session_state.card_setup[t_id] = {"tier_1": [], "tier_2": []}

        with st.expander(f"🃏 {t_data['name']} Configuration", expanded=False):
            t1_opts = [c['name'] for c in cards_db.get(t_id, {}).get(1, [])]
            t2_opts = [c['name'] for c in cards_db.get(t_id, {}).get(2, [])]
            all_opts = sorted(list(set(t1_opts + t2_opts)))

            st.markdown("**Tier 1 Slots**")
            cols_t1 = st.columns(4)
            current_t1 = []
            for i in range(4):
                with cols_t1[i]:
                    idx = get_opt_idx(all_opts, get_default_slot(t_id, 1, i))
                    val = st.selectbox(f"T1-{i + 1}", options=all_opts, index=idx, key=f"{t_id}_t1_{i}",
                                       label_visibility="collapsed")
                    current_t1.append(val)
            st.session_state.card_setup[t_id]["tier_1"] = current_t1

            st.markdown("**Tier 2 Slots**")
            cols_t2 = st.columns(4)
            current_t2 = []
            for i in range(4):
                with cols_t2[i]:
                    idx = get_opt_idx(all_opts, get_default_slot(t_id, 2, i))
                    val = st.selectbox(f"T2-{i + 1}", options=all_opts, index=idx, key=f"{t_id}_t2_{i}",
                                       label_visibility="collapsed")
                    current_t2.append(val)
            st.session_state.card_setup[t_id]["tier_2"] = current_t2

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

        # --- 2:1 MODE TOGGLE ---
        st.markdown("### 🏆 Strategy Mode")
        mode_2vs1 = st.checkbox("2:1 Power Mode",
                                help="Maximize chances of winning 2 rounds, ignoring the score of the weakest round.")

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

        with st.spinner("Analyzing data..."):
            best_loadout, wave_scores, error = solve_optimal_loadout(
                st.session_state.active_waves,
                st.session_state.user_towers,
                mode_2vs1=mode_2vs1
            )

        if error:
            st.error(error)
        else:
            # Determine sacrifice wave index if in 2:1 mode
            sacrifice_idx = -1
            if mode_2vs1 and wave_scores:
                sacrifice_idx = wave_scores.index(min(wave_scores))

            st.subheader("📋 Mission Briefing")
            line1 = f"**Wave 1:** {' - '.join([towers_db[tid]['name'] for tid in best_loadout[0]])}"
            line2 = f"**Wave 2:** {' - '.join([towers_db[tid]['name'] for tid in best_loadout[1]])}"
            line3 = f"**Wave 3:** {' - '.join([towers_db[tid]['name'] for tid in best_loadout[2]])}"
            st.info(f"💡 **Quick Lineup:**\n\n{line1}\n\n{line2}\n\n{line3}")

            st.divider()

            for i, enemy_id in enumerate(st.session_state.active_waves):
                enemy = enemies_db[enemy_id]
                wave_towers = best_loadout[i]

                # Check if this is the sacrifice wave
                is_sacrifice = (i == sacrifice_idx)
                border_color = "red" if is_sacrifice else "grey"

                with st.container(border=True):
                    c_head, c_tags = st.columns([1, 2])
                    with c_head:
                        header_text = f"#### Wave {i + 1}: {enemy['name']}"
                        if is_sacrifice:
                            st.markdown(f"#### 💀 Wave {i + 1}: SACRIFICIAL TEAM")
                            st.caption(f"Enemy: {enemy['name']} (Expected Loss)")
                        else:
                            st.markdown(header_text)
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
                        st.markdown("**🔗 Potential Combos:**")
                        for c in active_combos:
                            rating = c.get('score', 5)
                            desc = c['description']
                            tags = get_combo_tags(desc, c['name'])

                            badges = []
                            if any(t in enemy.get('weakness_types', []) for t in tags): badges.append(
                                "⚡ Super Effective")
                            if any(t in enemy.get('resistance_types', []) for t in tags): badges.append("🛡️ Resisted")

                            setup_conditions = analyze_user_setup(st.session_state.card_setup)
                            if "burn" in desc.lower() and "Burn" in setup_conditions: badges.append(
                                "🔥 Guaranteed Trigger")
                            if "slow" in desc.lower() and "Slow" in setup_conditions: badges.append(
                                "❄️ Guaranteed Trigger")

                            badge_str = " ".join([f"`{b}`" for b in badges])
                            color = "green" if rating >= 8 else "orange"

                            st.markdown(f"- :{color}[**{c['name']}**] ({rating}/10) {badge_str}")
                            st.caption(f"└ {desc}")
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

                            active_chains = get_active_chains_text(t_id)

                            html_code = textwrap.dedent(f"""
                            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 10px;">
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <img src="data:image/svg+xml;base64,{b64_svg}" style="width:40px; height:40px;">
                                    <div>
                                        <div style="font-weight:bold; color:#fff; font-size:0.95em;">{t_data['name']}</div>
                                        <div style="font-size:0.75em; color:{color};">{t_data['type']}</div>
                                    </div>
                                    <div style="margin-left:auto; text-align:right;">
                                        <div style="font-weight:bold; font-size:1.1em; color:#ddd;">{score}</div>
                                    </div>
                                </div>
                                <div style="margin-top:6px;">
                                    {f'<div style="font-size:0.75em; color:#4ea8de; margin-bottom:2px;">{active_chains}</div>' if active_chains else ''}
                                    <div style="font-size:0.7em; color:#aaa; line-height:1.2;">{note}</div>
                                </div>
                            </div>
                            """)
                            st.markdown(html_code, unsafe_allow_html=True)

            st.markdown("<br><br>", unsafe_allow_html=True)