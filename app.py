import streamlit as st
import itertools
import base64

# --- 1. CONFIGURATION: DATA & ASSETS ---

TURRET_DATA = {
    "Guardian (Mecha)":   {"type": "🦾 Phys", "card": "Splitting Bullet", "color": "#00d2d3", "icon": "guardian"},
    "Teslacoil":          {"type": "⚡ Elec", "card": "Chain Surge (No Stun)", "color": "#a55eea", "icon": "tesla"},
    "Thunderbolt":        {"type": "⚡ Elec", "card": "Paralysis", "color": "#a55eea", "icon": "thunderbolt"},
    "Firewheel":          {"type": "🔥 Fire", "card": "Mini Drones", "color": "#0fbcf9", "icon": "firewheel"},
    "Sky Guard":          {"type": "🦾 Phys", "card": "Impact Multiplier", "color": "#0fbcf9", "icon": "skyguard"},
    "Aeroblast":          {"type": "🦾 Phys", "card": "Floating Mine", "color": "#00d2d3", "icon": "aeroblast"},
    "Gravity Vortex":     {"type": "🌌 Force", "card": "Small Black Hole", "color": "#2ecc71", "icon": "vortex"},
    "Disruption Drone":   {"type": "❄️ Force", "card": "Disruption Force", "color": "#2ecc71", "icon": "disruption"},
    "Beam Turret":        {"type": "🔋 Energy", "card": "Beam Penetration", "color": "#2ecc71", "icon": "beam"}
}

TURRETS = list(TURRET_DATA.keys())

ENEMIES = [
    "Pristine Starcore (Healer)",
    "Alien Scout Drone (Invisible)",
    "Stellar Crown Guard (Sniper)",
    "Meteorite (Swarm)",
    "Cosmic Cube (Tank)",
    "Rock Walker (Runner)",
    "Elite Rift Colossus (Shield Boss)",
    "Elite Alien Golem (Split Boss)"
]

# Known Synergies (Check for these pairs in a wave)
COMBOS = [
    {"pair": {"Sky Guard", "Gravity Vortex"}, "name": "Collapse"},
    {"pair": {"Aeroblast", "Firewheel"}, "name": "Drone Summon"},
    {"pair": {"Disruption Drone", "Thunderbolt"}, "name": "Mag. Storm"},
    {"pair": {"Railgun", "Gravity Vortex"}, "name": "Vacuum Shot"},
]

SCORES = {
    # --- STARCORE (Heals on Debuff) ---
    ("Pristine Starcore (Healer)", "Guardian (Mecha)"): 100,
    ("Pristine Starcore (Healer)", "Teslacoil"): 95,
    ("Pristine Starcore (Healer)", "Sky Guard"): 90,
    ("Pristine Starcore (Healer)", "Firewheel"): 80,
    ("Pristine Starcore (Healer)", "Aeroblast"): 75,
    ("Pristine Starcore (Healer)", "Thunderbolt"): -100,
    ("Pristine Starcore (Healer)", "Disruption Drone"): -100,
    ("Pristine Starcore (Healer)", "Beam Turret"): -100,
    ("Pristine Starcore (Healer)", "Gravity Vortex"): -50,

    # --- SCOUT DRONE (Invisible) ---
    ("Alien Scout Drone (Invisible)", "Firewheel"): 100,
    ("Alien Scout Drone (Invisible)", "Aeroblast"): 95,
    ("Alien Scout Drone (Invisible)", "Guardian (Mecha)"): 85,
    ("Alien Scout Drone (Invisible)", "Beam Turret"): 80,

    # --- CROWN GUARD (Sniper) ---
    ("Stellar Crown Guard (Sniper)", "Sky Guard"): 100,
    ("Stellar Crown Guard (Sniper)", "Guardian (Mecha)"): 90,
    ("Stellar Crown Guard (Sniper)", "Disruption Drone"): 85,

    # --- METEORITE (Swarm) ---
    ("Meteorite (Swarm)", "Firewheel"): 100,
    ("Meteorite (Swarm)", "Aeroblast"): 95,
    ("Meteorite (Swarm)", "Thunderbolt"): 90,

    # --- COSMIC CUBE (Tank) ---
    ("Cosmic Cube (Tank)", "Guardian (Mecha)"): 100,
    ("Cosmic Cube (Tank)", "Gravity Vortex"): 100,
    ("Cosmic Cube (Tank)", "Sky Guard"): 95,
    ("Cosmic Cube (Tank)", "Beam Turret"): 10,
    ("Cosmic Cube (Tank)", "Teslacoil"): 10,

    # --- ROCK WALKER (Runner) ---
    ("Rock Walker (Runner)", "Gravity Vortex"): 100,
    ("Rock Walker (Runner)", "Teslacoil"): 100,
    ("Rock Walker (Runner)", "Thunderbolt"): 90,

    # --- BOSS: COLOSSUS (Shield) ---
    ("Elite Rift Colossus (Shield Boss)", "Guardian (Mecha)"): 100,
    ("Elite Rift Colossus (Shield Boss)", "Beam Turret"): 95,
    ("Elite Rift Colossus (Shield Boss)", "Sky Guard"): 85,
    ("Elite Rift Colossus (Shield Boss)", "Disruption Drone"): 30,

    # --- BOSS: GOLEM (Splitter) ---
    ("Elite Alien Golem (Split Boss)", "Aeroblast"): 100,
    ("Elite Alien Golem (Split Boss)", "Guardian (Mecha)"): 90,
    ("Elite Alien Golem (Split Boss)", "Beam Turret"): 85,
    ("Elite Alien Golem (Split Boss)", "Gravity Vortex"): 80,
    ("Elite Alien Golem (Split Boss)", "Teslacoil"): 10,
}

# --- 2. REFINED SVG ICONS (High Detail) ---
def get_svg_content(icon_name, color):
    paths = {
        "tesla": f'<circle cx="50" cy="85" r="15" fill="{color}" opacity="0.3"/><path d="M50,70 L30,30 M50,70 L70,30" stroke="{color}" stroke-width="4"/><circle cx="50" cy="25" r="8" fill="#fff" filter="drop-shadow(0 0 4px {color})"/>',
        "skyguard": f'<rect x="30" y="40" width="15" height="30" fill="{color}" rx="2"/><rect x="55" y="40" width="15" height="30" fill="{color}" rx="2"/><path d="M20,70 L80,70 L70,90 L30,90 Z" fill="{color}" opacity="0.5"/>',
        "disruption": f'<circle cx="50" cy="50" r="40" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="4,4"/><circle cx="30" cy="50" r="8" fill="{color}"/><circle cx="70" cy="50" r="8" fill="{color}"/><path d="M30,50 L70,50" stroke="#fff" stroke-width="2"/>',
        "guardian": f'<path d="M50,20 L30,50 L30,80 L70,80 L70,50 Z" fill="{color}" opacity="0.8"/><circle cx="50" cy="40" r="6" fill="#fff"/><rect x="45" y="60" width="10" height="20" fill="#222"/>',
        "thunderbolt": f'<circle cx="50" cy="50" r="25" fill="none" stroke="{color}" stroke-width="3"/><path d="M50,20 L55,45 L40,45 L50,80 L45,55 L60,55 Z" fill="#fff"/>',
        "beam": f'<path d="M45,40 L55,40 L60,90 L40,90 Z" fill="{color}"/><circle cx="50" cy="30" r="8" fill="#fff"/><line x1="50" y1="30" x2="50" y2="5" stroke="{color}" stroke-width="4"/>',
        "firewheel": f'<circle cx="50" cy="50" r="35" fill="none" stroke="{color}" stroke-width="5" stroke-dasharray="15,10"/><circle cx="50" cy="50" r="10" fill="#fff"/>',
        "aeroblast": f'<rect x="20" y="50" width="60" height="20" fill="{color}" rx="5"/><circle cx="50" cy="40" r="15" fill="{color}"/><circle cx="50" cy="40" r="6" fill="#fff"/>',
        "vortex": f'<circle cx="50" cy="50" r="30" fill="none" stroke="{color}" stroke-width="4"/><path d="M50,50 Q70,30 80,10" stroke="#fff" stroke-width="3" fill="none"/><circle cx="50" cy="50" r="8" fill="#000" stroke="#fff" stroke-width="2"/>'
    }
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">{paths.get(icon_name, "")}</svg>'

# --- 3. LOGIC ---
def get_score(enemy, turret):
    return SCORES.get((enemy, turret), 50)

def get_tactic_note(enemy, turret, score):
    if score == -100: return "⚠️ AVOID"
    if "Starcore" in enemy and "Guardian" in turret: return "Phys (Safe)"
    if "Invisible" in enemy and "Firewheel" in turret: return "Auto-Track"
    if "Cube" in enemy and "Vortex" in turret: return "Groups Tanks"
    if "Split Boss" in enemy and "Aeroblast" in turret: return "Mine Trap"
    if score >= 90: return "✅ Counter"
    return "Fill"

def check_combos(wave_turrets):
    combo_names = []
    combo_turrets = set()
    for c in COMBOS:
        current_simple = {t.split('(')[0].strip(): t for t in wave_turrets}
        if c["pair"].issubset(set(current_simple.keys())):
            combo_names.append(c["name"])
            for simple in c["pair"]:
                combo_turrets.add(current_simple[simple])
    return combo_names, combo_turrets

def solve_loadout(e1, e2, e3):
    best_score = -9999
    best_loadout = None
    for p in itertools.permutations(TURRETS):
        w1, w2, w3 = p[0:3], p[3:6], p[6:9]
        score = sum(get_score(e1, t) for t in w1) + sum(get_score(e2, t) for t in w2) + sum(get_score(e3, t) for t in w3)
        if score > best_score:
            best_score = score
            best_loadout = (w1, w2, w3)
    return best_loadout

# --- 4. APP LAYOUT ---
st.set_page_config(page_title="Vanguard 2.0", layout="wide")

st.markdown("""
<style>
    .main .block-container { padding-top: 1rem; padding-bottom: 2rem; }
    h1 { font-size: 1.1rem !important; color: #888; margin-bottom: 0px; text-transform: uppercase; letter-spacing: 2px;}
    
    /* Card Styles */
    .turret-card {
        background-color: #141414;
        border: 1px solid #333;
        border-radius: 6px;
        padding: 8px;
        text-align: center;
        height: 160px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        position: relative;
    }
    
    /* Combo Highlight */
    .combo-active {
        border: 1px solid #f1c40f !important;
        box-shadow: 0 0 8px rgba(241, 196, 15, 0.2);
        background: radial-gradient(circle, rgba(241,196,15,0.05) 0%, rgba(20,20,20,1) 70%);
    }
    
    .turret-icon { width: 50px; height: 50px; margin-bottom: 6px; }
    .turret-name { font-size: 0.75rem; font-weight: 700; color: #eee; line-height: 1.1; }
    .turret-meta { font-size: 0.65rem; color: #aaa; margin-bottom: 4px; }
    .turret-score { font-size: 0.7rem; font-weight: bold; }
    .tactic-note { font-size: 0.6rem; color: #aaa; font-style: italic; }
    
    /* Combo Badge */
    .combo-badge {
        position: absolute;
        top: -5px;
        right: -5px;
        background-color: #f1c40f;
        color: #000;
        font-size: 0.5rem;
        font-weight: bold;
        padding: 2px 4px;
        border-radius: 3px;
        z-index: 10;
        box-shadow: 0 2px 4px rgba(0,0,0,0.5);
    }

    .wave-header {
        font-size: 0.85rem;
        font-weight: bold;
        color: #fff;
        margin-top: 15px;
        margin-bottom: 5px;
        padding-left: 8px;
        border-left: 3px solid #555;
        display: flex;
        justify-content: space-between;
    }
    .combo-text { color: #f1c40f; font-size: 0.7rem; margin-left: 10px; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Vanguard 2.0")

# Input
c1, c2, c3 = st.columns(3)
with c1: e1 = st.selectbox("Wave 1", ENEMIES, index=2)
with c2: e2 = st.selectbox("Wave 2", ENEMIES, index=6)
with c3: e3 = st.selectbox("Wave 3", ENEMIES, index=1)

# Calculate
loadout = solve_loadout(e1, e2, e3)
waves_data = [(e1, loadout[0]), (e2, loadout[1]), (e3, loadout[2])]

st.divider()

# --- GRID RENDER ---
for i, (enemy_name, turrets) in enumerate(waves_data):
    # Check for combos in this wave
    combo_names, combo_turrets = check_combos(turrets)
    
    # Header with Combo text if active
    combo_html = f'<span class="combo-text">⚡ {", ".join(combo_names)}</span>' if combo_names else ""
    st.markdown(f'<div class="wave-header"><span>WAVE {i+1} vs {enemy_name.split("(")[0]}</span>{combo_html}</div>', unsafe_allow_html=True)
    
    cols = st.columns(3)
    for j, t_name in enumerate(turrets):
        data = TURRET_DATA[t_name]
        score = get_score(enemy_name, t_name)
        note = get_tactic_note(enemy_name, t_name, score)
        
        # SVG
        svg = get_svg_content(data['icon'], data['color'])
        b64_svg = base64.b64encode(svg.encode('utf-8')).decode("utf-8")
        
        # Styles
        score_color = "#2ecc71" if score >= 90 else "#e74c3c" if score < 0 else "#f1c40f"
        is_combo = t_name in combo_turrets
        card_class = "turret-card combo-active" if is_combo else "turret-card"
        badge_html = '<div class="combo-badge">LINK</div>' if is_combo else ""
        
        with cols[j]:
            st.markdown(f"""
            <div class="{card_class}">
                {badge_html}
                <img src="data:image/svg+xml;base64,{b64_svg}" class="turret-icon">
                <div class="turret-name">{t_name.split('(')[0]}</div>
                <div class="turret-meta">{data['type']}</div>
                <div class="turret-score" style="color:{score_color}">Score: {score}</div>
                <div class="tactic-note">{note}</div>
            </div>
            """, unsafe_allow_html=True)

# Footer Requirements
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("📝 Card Requirements", expanded=False):
    dc1, dc2, dc3 = st.columns(3)
    for i, col in enumerate([dc1, dc2, dc3]):
        with col:
            st.caption(f"Wave {i+1}")
            for t in loadout[i]:
                st.markdown(f"- `{TURRET_DATA[t]['card']}`")
            
