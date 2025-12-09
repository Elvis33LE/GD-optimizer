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

# Scoring Logic (UPDATED: Penalizes AoE vs Single Target Bosses)
SCORES = {
    # --- STARCORE (Heals on Debuff) ---
    ("Pristine Starcore (Healer)", "Guardian (Mecha)"): 100,
    ("Pristine Starcore (Healer)", "Teslacoil"): 95,
    ("Pristine Starcore (Healer)", "Sky Guard"): 90,
    ("Pristine Starcore (Healer)", "Firewheel"): 80,
    ("Pristine Starcore (Healer)", "Aeroblast"): 75,
    ("Pristine Starcore (Healer)", "Thunderbolt"): -100, # Stun = Heal
    ("Pristine Starcore (Healer)", "Disruption Drone"): -100, # Slow = Heal
    ("Pristine Starcore (Healer)", "Beam Turret"): -100, # Vuln = Heal
    ("Pristine Starcore (Healer)", "Gravity Vortex"): -50,

    # --- SCOUT DRONE (Invisible) ---
    ("Alien Scout Drone (Invisible)", "Firewheel"): 100, # MVP
    ("Alien Scout Drone (Invisible)", "Aeroblast"): 95,
    ("Alien Scout Drone (Invisible)", "Guardian (Mecha)"): 85,
    ("Alien Scout Drone (Invisible)", "Beam Turret"): 80,

    # --- CROWN GUARD (Sniper) ---
    ("Stellar Crown Guard (Sniper)", "Sky Guard"): 100,
    ("Stellar Crown Guard (Sniper)", "Guardian (Mecha)"): 90,
    ("Stellar Crown Guard (Sniper)", "Disruption Drone"): 85,
    ("Stellar Crown Guard (Sniper)", "Beam Turret"): 70,

    # --- METEORITE (Swarm) ---
    ("Meteorite (Swarm)", "Firewheel"): 100,
    ("Meteorite (Swarm)", "Aeroblast"): 95,
    ("Meteorite (Swarm)", "Thunderbolt"): 90,
    ("Meteorite (Swarm)", "Teslacoil"): 85,
    ("Meteorite (Swarm)", "Gravity Vortex"): 80,
    ("Meteorite (Swarm)", "Guardian (Mecha)"): 70,
    ("Meteorite (Swarm)", "Sky Guard"): 40, # Bad vs Swarm (Single Target)
    ("Meteorite (Swarm)", "Beam Turret"): 40, # Bad vs Swarm

    # --- COSMIC CUBE (Tank) ---
    ("Cosmic Cube (Tank)", "Guardian (Mecha)"): 100,
    ("Cosmic Cube (Tank)", "Gravity Vortex"): 100,
    ("Cosmic Cube (Tank)", "Sky Guard"): 95,
    ("Cosmic Cube (Tank)", "Aeroblast"): 80,
    ("Cosmic Cube (Tank)", "Beam Turret"): 10, # Resisted
    ("Cosmic Cube (Tank)", "Teslacoil"): 10, # Resisted

    # --- ROCK WALKER (Runner) ---
    ("Rock Walker (Runner)", "Gravity Vortex"): 100,
    ("Rock Walker (Runner)", "Teslacoil"): 100,
    ("Rock Walker (Runner)", "Thunderbolt"): 90,
    ("Rock Walker (Runner)", "Guardian (Mecha)"): 80,

    # --- BOSS: COLOSSUS (Shield) ---
    ("Elite Rift Colossus (Shield Boss)", "Guardian (Mecha)"): 100, # Best Shield Breaker
    ("Elite Rift Colossus (Shield Boss)", "Beam Turret"): 95, # Applies Vulnerable
    ("Elite Rift Colossus (Shield Boss)", "Aeroblast"): 80, # Physical Mines (Okay)
    ("Elite Rift Colossus (Shield Boss)", "Sky Guard"): 70, # Good Impact
    ("Elite Rift Colossus (Shield Boss)", "Firewheel"): -50, # USELESS vs Shield
    ("Elite Rift Colossus (Shield Boss)", "Gravity Vortex"): -50, # USELESS vs Boss
    ("Elite Rift Colossus (Shield Boss)", "Teslacoil"): -20, # Low Single Target
    ("Elite Rift Colossus (Shield Boss)", "Disruption Drone"): 30, # Resisted

    # --- BOSS: GOLEM (Splitter) ---
    ("Elite Alien Golem (Split Boss)", "Aeroblast"): 100, # MVP: Spawn Camp
    ("Elite Alien Golem (Split Boss)", "Guardian (Mecha)"): 90,
    ("Elite Alien Golem (Split Boss)", "Beam Turret"): 85,
    ("Elite Alien Golem (Split Boss)", "Gravity Vortex"): 80, # Catch splits
    ("Elite Alien Golem (Split Boss)", "Firewheel"): -20, # Bad vs Boss
    ("Elite Alien Golem (Split Boss)", "Teslacoil"): 10, # Resisted
}

# --- 2. ASSETS ---
def get_svg_content(icon_name, color):
    paths = {
        "tesla": f'<circle cx="50" cy="85" r="15" fill="{color}" opacity="0.3"/><ellipse cx="50" cy="70" rx="25" ry="10" fill="none" stroke="{color}" stroke-width="4" opacity="0.6"/><ellipse cx="50" cy="55" rx="20" ry="8" fill="none" stroke="{color}" stroke-width="4" opacity="0.8"/><ellipse cx="50" cy="40" rx="15" ry="6" fill="none" stroke="{color}" stroke-width="4"/><circle cx="50" cy="25" r="8" fill="#fff"/><path d="M50,25 L30,5 M50,25 L70,5" stroke="#fff" stroke-width="2"/>',
        "skyguard": f'<rect x="20" y="60" width="60" height="30" rx="5" fill="{color}" opacity="0.4"/><rect x="30" y="40" width="15" height="30" fill="{color}"/><rect x="55" y="40" width="15" height="30" fill="{color}"/><path d="M37,40 L37,10 L45,20 L37,40" fill="#fff" opacity="0.9"/><path d="M62,40 L62,10 L70,20 L62,40" fill="#fff" opacity="0.9"/>',
        "disruption": f'<circle cx="50" cy="50" r="45" fill="none" stroke="{color}" stroke-width="2" opacity="0.3"/><circle cx="30" cy="50" r="10" fill="{color}" opacity="0.7"/><circle cx="70" cy="50" r="10" fill="{color}" opacity="0.7"/><path d="M30,50 Q50,20 70,50 Q50,80 30,50" fill="none" stroke="#fff" stroke-width="3" opacity="0.6"/><circle cx="30" cy="50" r="4" fill="#fff"/><circle cx="70" cy="50" r="4" fill="#fff"/>',
        "guardian": f'<path d="M30,80 L70,80 L60,30 L40,30 Z" fill="{color}" opacity="0.5"/><rect x="40" y="20" width="20" height="20" rx="4" fill="{color}"/><circle cx="50" cy="30" r="6" fill="#fff"/><rect x="25" y="35" width="10" height="25" rx="2" fill="{color}" opacity="0.8"/><rect x="65" y="35" width="10" height="25" rx="2" fill="{color}" opacity="0.8"/><circle cx="50" cy="55" r="10" fill="none" stroke="#fff" stroke-width="3"/>',
        "thunderbolt": f'<circle cx="50" cy="50" r="30" fill="{color}" opacity="0.3"/><circle cx="50" cy="50" r="15" fill="{color}"/><path d="M50,10 L55,35 L45,35 L50,10" fill="#fff"/><path d="M50,90 L45,65 L55,65 L50,90" fill="#fff"/><path d="M10,50 L35,45 L35,55 L10,50" fill="#fff"/><path d="M90,50 L65,55 L65,45 L90,50" fill="#fff"/><circle cx="50" cy="50" r="5" fill="#fff"/>',
        "beam": f'<path d="M20,80 L80,80 L70,60 L30,60 Z" fill="{color}" opacity="0.4"/><rect x="45" y="30" width="10" height="30" fill="{color}"/><path d="M45,30 L50,5 L55,30 Z" fill="#fff"/><path d="M50,5 L20,0 L50,5 L80,0" stroke="{color}" stroke-width="2" opacity="0.6"/>',
        "firewheel": f'<circle cx="50" cy="50" r="40" fill="none" stroke="{color}" stroke-width="4" opacity="0.5" stroke-dasharray="10,5"/><path d="M50,85 Q30,65 35,45 Q50,10 65,45 Q70,65 50,85 Z" fill="{color}" opacity="0.8"/><path d="M50,75 Q40,60 45,45 Q50,25 55,45 Q60,60 50,75 Z" fill="#fff" opacity="0.6"/>',
        "aeroblast": f'<rect x="25" y="65" width="50" height="20" rx="4" fill="{color}" opacity="0.4"/><rect x="35" y="35" width="30" height="35" fill="{color}"/><circle cx="50" cy="35" r="15" fill="none" stroke="{color}" stroke-width="5"/><circle cx="50" cy="35" r="5" fill="#fff"/><rect x="65" y="55" width="15" height="15" rx="8" fill="#fff" opacity="0.8"/>',
        "vortex": f'<circle cx="50" cy="50" r="45" fill="none" stroke="{color}" stroke-width="2" opacity="0.2"/><path d="M50,50 m-35,0 a35,35 0 1,0 70,0 a35,35 0 1,0 -70,0" fill="none" stroke="{color}" stroke-width="6" opacity="0.6" stroke-dasharray="60, 160"/><circle cx="50" cy="50" r="15" fill="#000" stroke="#fff" stroke-width="3"/><path d="M50,50 L85,15" stroke="#fff" stroke-width="3" stroke-linecap="round"/>'
    }
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">{paths.get(icon_name, "")}</svg>'

# --- 3. CORE LOGIC ---
def get_score(enemy, turret):
    return SCORES.get((enemy, turret), 50)

def get_tactic_note(enemy, turret, score):
    if score == -100: return "⚠️ AVOID: Heals/Immune"
    if score <= -20: return "⚠️ Weak vs this enemy"
    if "Starcore" in enemy and "Guardian" in turret: return "Phys (No Debuff)"
    if "Invisible" in enemy and "Firewheel" in turret: return "Auto-Track"
    if "Cube" in enemy and "Vortex" in turret: return "Groups Tanks"
    if "Walker" in enemy and "Teslacoil" in turret: return "Chain Surge"
    if "Split Boss" in enemy and "Aeroblast" in turret: return "Spawn Camp Mines"
    if "Shield Boss" in enemy and "Beam" in turret: return "Breaks Shield"
    if score >= 90: return "✅ Counter"
    if score <= 30: return "⚠️ Resisted"
    return "Fill"

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

# --- 4. APP LAYOUT & CSS ---
st.set_page_config(page_title="Vanguard 2.0", layout="wide")

st.markdown("""
<style>
    .main .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    h1 { font-size: 1.2rem !important; color: #888; margin-bottom: 0px; }
    /* Tighter grid layout for the cards */
    .turret-card {
        background-color: #141414; /* Darker background */
        border: 1px solid #333;
        border-radius: 6px;
        padding: 8px;
        text-align: center;
        height: 170px; /* Fixed height for alignment */
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        align-items: center;
    }
    .turret-icon { width: 55px; height: 55px; margin-bottom: 4px; filter: drop-shadow(0px 0px 3px rgba(255,255,255,0.2)); }
    .turret-name { font-size: 0.8rem; font-weight: 700; color: #eee; line-height: 1.1; margin-bottom: 2px;}
    .turret-meta { font-size: 0.7rem; color: #aaa; }
    .turret-score { font-size: 0.75rem; font-weight: bold; margin-top: 2px; }
    .tactic-note { font-size: 0.65rem; color: #ffd700; font-style: italic; margin-top: 4px; line-height: 1.1;}
    
    /* Wave headers */
    .wave-row-header {
        font-size: 0.9rem;
        font-weight: bold;
        color: #fff;
        margin-top: 15px;
        margin-bottom: 5px;
        padding-left: 10px;
        border-left: 4px solid #555;
    }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Vanguard 2.0")

# Input columns
c1, c2, c3 = st.columns(3)
with c1: e1 = st.selectbox("Wave 1", ENEMIES, index=2)
with c2: e2 = st.selectbox("Wave 2", ENEMIES, index=6)
with c3: e3 = st.selectbox("Wave 3", ENEMIES, index=1)

# Auto-Calculate
loadout = solve_loadout(e1, e2, e3)
waves_data = [(e1, loadout[0]), (e2, loadout[1]), (e3, loadout[2])]

st.divider()

# --- CARD REQUIREMENTS (Top View) ---
with st.expander("📝 Check Your Card Setup", expanded=True):
    dc1, dc2, dc3 = st.columns(3)
    for i, col in enumerate([dc1, dc2, dc3]):
        with col:
            st.caption(f"Wave {i+1}")
            for t in loadout[i]:
                st.markdown(f"- {t.split('(')[0]}: `{TURRET_DATA[t]['card']}`")

st.markdown("<br>", unsafe_allow_html=True)

# --- GRID RENDERER ---
for i, (enemy_name, turrets) in enumerate(waves_data):
    st.markdown(f'<div class="wave-row-header">Wave {i+1} vs {enemy_name.split("(")[0]}</div>', unsafe_allow_html=True)
    
    cols = st.columns(3)
    for j, t_name in enumerate(turrets):
        data = TURRET_DATA[t_name]
        score = get_score(enemy_name, t_name)
        note = get_tactic_note(enemy_name, t_name, score)
        
        svg = get_svg_content(data['icon'], data['color'])
        b64_svg = base64.b64encode(svg.encode('utf-8')).decode("utf-8")
        
        score_color = "#2ecc71" if score >= 90 else "#f1c40f" if score >= 50 else "#e74c3c"
        border_color = score_color

        with cols[j]:
            st.markdown(f"""
            <div class="turret-card" style="border-bottom: 3px solid {border_color};">
                <img src="data:image/svg+xml;base64,{b64_svg}" class="turret-icon">
                <div>
                    <div class="turret-name">{t_name.split('(')[0]}</div>
                    <div class="turret-meta">{data['type']}</div>
                </div>
                <div>
                    <div class="turret-score" style="color:{score_color}">Score: {score}</div>
                    <div class="tactic-note">{note}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
