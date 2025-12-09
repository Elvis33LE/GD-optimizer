import streamlit as st
import itertools
import base64

# --- 1. CONFIGURATION: DATA & ASSETS ---

# Your specific cards/notes
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

# Scoring Logic (From previous interaction)
SCORES = {
    ("Pristine Starcore (Healer)", "Guardian (Mecha)"): 100,
    ("Pristine Starcore (Healer)", "Teslacoil"): 95,
    ("Pristine Starcore (Healer)", "Sky Guard"): 90,
    ("Pristine Starcore (Healer)", "Firewheel"): 80,
    ("Pristine Starcore (Healer)", "Aeroblast"): 75,
    ("Pristine Starcore (Healer)", "Thunderbolt"): -100,
    ("Pristine Starcore (Healer)", "Disruption Drone"): -100,
    ("Pristine Starcore (Healer)", "Beam Turret"): -100,
    ("Pristine Starcore (Healer)", "Gravity Vortex"): -50,
    ("Alien Scout Drone (Invisible)", "Firewheel"): 100,
    ("Alien Scout Drone (Invisible)", "Aeroblast"): 95,
    ("Alien Scout Drone (Invisible)", "Guardian (Mecha)"): 85,
    ("Alien Scout Drone (Invisible)", "Beam Turret"): 80,
    ("Stellar Crown Guard (Sniper)", "Sky Guard"): 100,
    ("Stellar Crown Guard (Sniper)", "Guardian (Mecha)"): 90,
    ("Stellar Crown Guard (Sniper)", "Disruption Drone"): 85,
    ("Meteorite (Swarm)", "Firewheel"): 100,
    ("Meteorite (Swarm)", "Aeroblast"): 95,
    ("Meteorite (Swarm)", "Thunderbolt"): 90,
    ("Cosmic Cube (Tank)", "Guardian (Mecha)"): 100,
    ("Cosmic Cube (Tank)", "Gravity Vortex"): 100,
    ("Cosmic Cube (Tank)", "Sky Guard"): 95,
    ("Cosmic Cube (Tank)", "Beam Turret"): 10,
    ("Cosmic Cube (Tank)", "Teslacoil"): 10,
    ("Rock Walker (Runner)", "Gravity Vortex"): 100,
    ("Rock Walker (Runner)", "Teslacoil"): 100,
    ("Rock Walker (Runner)", "Thunderbolt"): 90,
    ("Elite Rift Colossus (Shield Boss)", "Guardian (Mecha)"): 100,
    ("Elite Rift Colossus (Shield Boss)", "Beam Turret"): 95,
    ("Elite Rift Colossus (Shield Boss)", "Sky Guard"): 85,
    ("Elite Rift Colossus (Shield Boss)", "Disruption Drone"): 30,
    ("Elite Alien Golem (Split Boss)", "Aeroblast"): 100,
    ("Elite Alien Golem (Split Boss)", "Guardian (Mecha)"): 90,
    ("Elite Alien Golem (Split Boss)", "Beam Turret"): 85,
    ("Elite Alien Golem (Split Boss)", "Gravity Vortex"): 80,
    ("Elite Alien Golem (Split Boss)", "Teslacoil"): 10,
}

# --- 2. SVG GENERATION HELPERS ---
# We store the paths directly here to generate them on the fly
def get_svg_content(icon_name, color):
    paths = {
        "tesla": '<path d="M20,90 L80,90 L70,70 L30,70 Z" opacity="0.5"/><rect x="35" y="30" width="30" height="40" transform="rotate(-45 50 50)" rx="5" /><rect x="45" y="10" width="10" height="30" transform="rotate(-45 50 50)" /><line x1="30" y1="40" x2="60" y2="70" stroke="#000" stroke-width="2" opacity="0.3"/><line x1="35" y1="35" x2="65" y2="65" stroke="#000" stroke-width="2" opacity="0.3"/>',
        "skyguard": '<path d="M20,90 L80,90 L70,75 L30,75 Z" opacity="0.5"/><rect x="25" y="35" width="50" height="35" rx="4" transform="rotate(-15 50 60)"/><rect x="65" y="40" width="20" height="25" rx="2" transform="rotate(-15 50 60)"/><circle cx="40" cy="50" r="3" fill="#fff" />',
        "disruption": '<path d="M45,90 L55,90 L55,50 L45,50 Z" /><path d="M30,90 L70,90 L60,80 L40,80 Z" opacity="0.5"/><circle cx="30" cy="40" r="12" /><circle cx="70" cy="40" r="12" /><rect x="40" y="38" width="20" height="4" rx="2" />',
        "guardian": '<path d="M35,90 L45,60 L55,60 L65,90" stroke="currentColor" stroke-width="8" stroke-linecap="round" fill="none"/><circle cx="50" cy="30" r="10" /><rect x="30" y="40" width="40" height="25" rx="5" /><circle cx="20" cy="50" r="8" /><circle cx="80" cy="50" r="8" />',
        "thunderbolt": '<path d="M30,90 L70,90 L60,75 L40,75 Z" opacity="0.5"/><rect x="42" y="55" width="16" height="20" /><ellipse cx="50" cy="55" rx="25" ry="8" fill="none" stroke="currentColor" stroke-width="4"/><ellipse cx="50" cy="70" rx="20" ry="6" fill="none" stroke="currentColor" stroke-width="4"/><circle cx="50" cy="35" r="12" fill="#fff" opacity="0.9"/>',
        "beam": '<path d="M25,90 L75,90 L65,75 L35,75 Z" opacity="0.5"/><rect x="30" y="35" width="8" height="40" transform="rotate(-30 50 85)" /><rect x="62" y="35" width="8" height="40" transform="rotate(30 50 85)" /><rect x="46" y="25" width="8" height="50" /><circle cx="50" cy="35" r="6" fill="#fff" opacity="0.8"/>',
        "firewheel": '<path d="M30,90 L70,90 L60,75 L40,75 Z" opacity="0.5"/><path d="M50,20 Q70,45 65,60 T50,85 Q30,70 35,60 T50,20 Z" /><circle cx="50" cy="50" r="5" fill="#fff" />',
        "aeroblast": '<path d="M20,90 L80,90 L70,75 L30,75 Z" opacity="0.5"/><rect x="35" y="45" width="30" height="30" rx="4" /><rect x="38" y="15" width="8" height="40" transform="rotate(-45 50 55)" /><rect x="54" y="15" width="8" height="40" transform="rotate(-45 50 55)" /><rect x="40" y="30" width="20" height="5" transform="rotate(-45 50 55)" fill="#000" opacity="0.3"/>',
        "vortex": '<path d="M30,90 L70,90 L60,80 L40,80 Z" opacity="0.5"/><circle cx="50" cy="50" r="20" stroke="currentColor" stroke-width="6" fill="none" /><path d="M50,50 L80,20" stroke="currentColor" stroke-width="4" stroke-linecap="round" /><circle cx="50" cy="50" r="6" fill="#000" />'
    }
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" fill="{color}">{paths.get(icon_name, "")}</svg>'

# --- 3. CORE LOGIC ---
def get_score(enemy, turret):
    return SCORES.get((enemy, turret), 50)

def get_tactic_note(enemy, turret, score):
    if score == -100: return "⚠️ AVOID: Heals/Immune"
    if "Starcore" in enemy and "Guardian" in turret: return "Phys (No Debuff)"
    if "Invisible" in enemy and "Firewheel" in turret: return "Auto-Track"
    if "Cube" in enemy and "Vortex" in turret: return "Groups Tanks"
    if "Walker" in enemy and "Teslacoil" in turret: return "Chain Surge"
    if "Split Boss" in enemy and "Aeroblast" in turret: return "Spawn Camp Mines"
    if "Shield Boss" in enemy and "Beam" in turret: return "Breaks Shield"
    if score >= 90: return "✅ Counter"
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

# --- 4. APP LAYOUT ---
st.set_page_config(page_title="Vanguard 2.0", layout="wide")

# Custom CSS for the "Game Grid" look
st.markdown("""
<style>
    .main .block-container { padding-top: 2rem; }
    h1 { font-size: 1.5rem !important; color: #aaa; margin-bottom: 0px; }
    .turret-card {
        background-color: #1a1a1a;
        border: 2px solid #333;
        border-radius: 8px;
        padding: 10px;
        text-align: center;
        height: 180px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        align-items: center;
        transition: transform 0.2s;
    }
    .turret-card:hover { border-color: #555; transform: translateY(-2px); }
    .turret-icon { width: 60px; height: 60px; margin-bottom: 5px; }
    .turret-name { font-size: 0.85rem; font-weight: bold; color: #fff; line-height: 1.2; }
    .turret-meta { font-size: 0.75rem; color: #888; margin-top: 4px; }
    .wave-header { 
        background-color: #0d0d0d; 
        color: #fff; 
        padding: 5px 10px; 
        border-radius: 4px; 
        font-weight: bold; 
        margin-bottom: 10px; 
        border-left: 4px solid #00d2d3;
    }
    .tactic-note { font-size: 0.7rem; color: #ffd700; font-style: italic; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Vanguard 2.0")

# --- INPUT SECTION (3 columns side-by-side) ---
c1, c2, c3 = st.columns(3)
with c1: e1 = st.selectbox("Wave 1 Enemy", ENEMIES, index=2)
with c2: e2 = st.selectbox("Wave 2 Enemy", ENEMIES, index=6)
with c3: e3 = st.selectbox("Wave 3 Enemy", ENEMIES, index=1)

# --- AUTO CALCULATION ---
w1, w2, w3 = solve_loadout(e1, e2, e3)

st.divider()

# --- OUTPUT GRID RENDERER ---
def render_wave_column(wave_num, enemy, turrets):
    st.markdown(f'<div class="wave-header">WAVE {wave_num} <span style="font-weight:normal; opacity:0.7">vs {enemy.split("(")[0]}</span></div>', unsafe_allow_html=True)
    
    cols = st.columns(3) # 3 turrets per wave, side by side
    for i, t_name in enumerate(turrets):
        data = TURRET_DATA[t_name]
        svg = get_svg_content(data['icon'], data['color'])
        b64_svg = base64.b64encode(svg.encode('utf-8')).decode("utf-8")
        score = get_score(enemy, t_name)
        note = get_tactic_note(enemy, t_name, score)
        
        border_color = "#2ecc71" if score >= 90 else "#f1c40f" if score >= 50 else "#e74c3c"
        
        with cols[i]:
            st.markdown(f"""
            <div class="turret-card" style="border-bottom: 3px solid {border_color};">
                <img src="data:image/svg+xml;base64,{b64_svg}" class="turret-icon">
                <div class="turret-name">{t_name.split('(')[0]}</div>
                <div class="turret-meta">{data['type']}</div>
                <div class="tactic-note">{note}</div>
            </div>
            """, unsafe_allow_html=True)

# --- DISPLAY THE GRID ---
# We create 3 big columns for the 3 waves
main_cols = st.columns(3)

with main_cols[0]:
    render_wave_column(1, e1, w1)

with main_cols[1]:
    render_wave_column(2, e2, w2)

with main_cols[2]:
    render_wave_column(3, e3, w3)

# --- DETAILED DETAILS (Below Grid) ---
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("📝 Detailed Strategy & Card Requirements", expanded=True):
    dc1, dc2, dc3 = st.columns(3)
    
    def render_details(col, wave, turrets):
        with col:
            st.caption(f"**Strategy for Wave {wave}**")
            for t in turrets:
                d = TURRET_DATA[t]
                st.markdown(f"**{t}**: Requires `{d['card']}`")
    
    render_details(dc1, 1, w1)
    render_details(dc2, 2, w2)
    render_details(dc3, 3, w3)
    
