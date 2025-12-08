import streamlit as st
import itertools

# --- 1. CONFIGURATION: TURRETS & CARDS ---
# We add metadata here: Damage Type and the Specific Card required.
TURRET_DATA = {
    "Guardian (Mecha)": {"type": "🦾 Phys", "card": "Splitting Bullet"},
    "Teslacoil":        {"type": "⚡ Elec", "card": "Chain Surge (No Stun)"},
    "Thunderbolt":      {"type": "⚡ Elec", "card": "Paralysis"},
    "Firewheel":        {"type": "🔥 Fire", "card": "Mini Drones"},
    "Sky Guard":        {"type": "🦾 Phys", "card": "Impact Multiplier"},
    "Aeroblast":        {"type": "🦾 Phys", "card": "Floating Mine"},
    "Gravity Vortex":   {"type": "🌌 Force", "card": "Small Black Hole"},
    "Disruption Drone": {"type": "❄️ Force", "card": "Disruption Force"},
    "Beam Turret":      {"type": "🔋 Energy", "card": "Beam Penetration"}
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

# --- 2. SCORING MATRIX ---
# Format: (Enemy, Turret): Score
# 100 = Perfect Counter / MVP
# 80-90 = Great Choice
# 50 = Decent / Filler
# -100 = DANGER (Do not use)

SCORES = {
    # --- STARCORE (Heals on Debuff) ---
    ("Pristine Starcore (Healer)", "Guardian (Mecha)"): 100,
    ("Pristine Starcore (Healer)", "Teslacoil"): 95, 
    ("Pristine Starcore (Healer)", "Sky Guard"): 90,
    ("Pristine Starcore (Healer)", "Firewheel"): 80,
    ("Pristine Starcore (Healer)", "Aeroblast"): 75,
    ("Pristine Starcore (Healer)", "Thunderbolt"): -100, # Stun heals it
    ("Pristine Starcore (Healer)", "Disruption Drone"): -100, # Slow heals it
    ("Pristine Starcore (Healer)", "Beam Turret"): -100, # Vuln heals it
    ("Pristine Starcore (Healer)", "Gravity Vortex"): -50,

    # --- SCOUT DRONE (Invisible) ---
    ("Alien Scout Drone (Invisible)", "Firewheel"): 100, # Auto-track
    ("Alien Scout Drone (Invisible)", "Aeroblast"): 95, # Traps
    ("Alien Scout Drone (Invisible)", "Guardian (Mecha)"): 85,
    ("Alien Scout Drone (Invisible)", "Beam Turret"): 80, # Auto-lock
    
    # --- CROWN GUARD (Sniper) ---
    ("Stellar Crown Guard (Sniper)", "Sky Guard"): 100,
    ("Stellar Crown Guard (Sniper)", "Guardian (Mecha)"): 90,
    ("Stellar Crown Guard (Sniper)", "Disruption Drone"): 85,

    # --- METEORITE (Swarm) ---
    ("Meteorite (Swarm)", "Firewheel"): 100,
    ("Meteorite (Swarm)", "Aeroblast"): 95,
    ("Meteorite (Swarm)", "Thunderbolt"): 90,

    # --- COSMIC CUBE (Tank - Resists Energy) ---
    ("Cosmic Cube (Tank)", "Guardian (Mecha)"): 100,
    ("Cosmic Cube (Tank)", "Gravity Vortex"): 100, # Mandatory grouping
    ("Cosmic Cube (Tank)", "Sky Guard"): 95, # Phys Impact
    ("Cosmic Cube (Tank)", "Beam Turret"): 10, # Resisted
    ("Cosmic Cube (Tank)", "Teslacoil"): 10, # Resisted
    
    # --- ROCK WALKER (Runner - Weak Elec) ---
    ("Rock Walker (Runner)", "Gravity Vortex"): 100, # Trap early
    ("Rock Walker (Runner)", "Teslacoil"): 100, # Chain Surge
    ("Rock Walker (Runner)", "Thunderbolt"): 90, # Elec Weakness

    # --- BOSS: COLOSSUS (Shield) ---
    ("Elite Rift Colossus (Shield Boss)", "Guardian (Mecha)"): 100,
    ("Elite Rift Colossus (Shield Boss)", "Beam Turret"): 95, # Applies Vulnerable
    ("Elite Rift Colossus (Shield Boss)", "Sky Guard"): 85,
    ("Elite Rift Colossus (Shield Boss)", "Disruption Drone"): 30, # Resisted
    
    # --- BOSS: GOLEM (Splitter - Resists Energy) ---
    ("Elite Alien Golem (Split Boss)", "Aeroblast"): 100, # MVP: Spawn camp
    ("Elite Alien Golem (Split Boss)", "Guardian (Mecha)"): 90,
    ("Elite Alien Golem (Split Boss)", "Beam Turret"): 85, # Buffs mines
    ("Elite Alien Golem (Split Boss)", "Gravity Vortex"): 80,
    ("Elite Alien Golem (Split Boss)", "Teslacoil"): 10, # Resisted
}

def get_score(enemy, turret):
    return SCORES.get((enemy, turret), 50) 

# --- 3. HELPER: TACTICAL NOTES ---
# Returns a short string explaining WHY the score is high/low
def get_tactic_note(enemy, turret, score):
    # DANGER ZONES
    if score == -100:
        return "⚠️ AVOID: Triggers Heal/Immunity"
    if score < 40:
        return "⚠️ Weak: Resisted damage"
        
    # STARCORE
    if "Starcore" in enemy:
        if "Teslacoil" in turret: return "Safe Electric (No Stun)"
        if "Guardian" in turret: return "Pure Phys (No Debuff)"
    
    # INVISIBLE
    if "Invisible" in enemy:
        if "Firewheel" in turret: return "Drones Auto-track Invisible"
        if "Aeroblast" in turret: return "Mines kill Unseen units"
        
    # CUBE
    if "Cube" in enemy:
        if "Vortex" in turret: return "Prevents growing huge"
        if "Sky Guard" in turret: return "Impact breaks Armor"
        
    # WALKER
    if "Walker" in enemy:
        if "Vortex" in turret: return "Trap before <50% HP"
        if "Teslacoil" in turret: return "Exploits +50% Weakness"
        
    # BOSSES
    if "Split Boss" in enemy:
        if "Aeroblast" in turret: return "Mines spawn-kill Minions"
        if "Beam" in turret: return "Vulnerable boosts Mines"
    if "Shield Boss" in enemy:
        if "Beam" in turret: return "Removes Shield Defense"
        
    # GENERIC HIGH SCORES
    if score == 100: return "🌟 HARD COUNTER"
    if score >= 90: return "✅ Excellent Matchup"
    
    return "Fill / Standard Damage"


# --- 4. SOLVER ---
def solve_loadout(e1, e2, e3):
    best_score = -9999
    best_loadout = None
    
    for p in itertools.permutations(TURRETS):
        wave1 = p[0:3]
        wave2 = p[3:6]
        wave3 = p[6:9]
        
        score = 0
        score += sum([get_score(e1, t) for t in wave1])
        score += sum([get_score(e2, t) for t in wave2])
        score += sum([get_score(e3, t) for t in wave3])
        
        if score > best_score:
            best_score = score
            best_loadout = (wave1, wave2, wave3)
            
    return best_loadout

# --- 5. UI DISPLAY ---
st.set_page_config(page_title="Vanguard Strategizer 2.0", layout="centered")

st.title("🛡️ Vanguard Strategizer 2.0")
st.caption("Optimized for your 9 specific card unlocks.")

col1, col2, col3 = st.columns(3)
with col1:
    e1 = st.selectbox("Wave 1", ENEMIES, index=0)
with col2:
    e2 = st.selectbox("Wave 2", ENEMIES, index=4)
with col3:
    e3 = st.selectbox("Wave 3", ENEMIES, index=7)

if st.button("🚀 Calculate Optimal Strategy", type="primary"):
    w1, w2, w3 = solve_loadout(e1, e2, e3)
    
    # Function to render a single turret card
    def render_turret(turret_name, enemy_name):
        score = get_score(enemy_name, turret_name)
        data = TURRET_DATA[turret_name]
        note = get_tactic_note(enemy_name, turret_name, score)
        
        # Color coding the score
        score_color = "green" if score >= 80 else "orange" if score >= 50 else "red"
        
        st.markdown(f"""
        <div style="background-color: #1E1E1E; padding: 10px; border-radius: 5px; margin-bottom: 10px; border-left: 5px solid {score_color};">
            <div style="font-weight: bold; font-size: 1.1em;">{turret_name}</div>
            <div style="color: #bbb; font-size: 0.9em;">{data['type']} | <span style="color:{score_color}">Score: {score}</span></div>
            <div style="color: #FFD700; font-size: 0.85em;">🃏 Card: {data['card']}</div>
            <div style="font-style: italic; font-size: 0.85em; margin-top: 5px;">"{note}"</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    
    # WAVE 1
    st.subheader(f"🌊 Wave 1 vs {e1.split('(')[0]}")
    c1, c2, c3 = st.columns(3)
    with c1: render_turret(w1[0], e1)
    with c2: render_turret(w1[1], e1)
    with c3: render_turret(w1[2], e1)

    # WAVE 2
    st.subheader(f"🛡️ Wave 2 vs {e2.split('(')[0]}")
    c1, c2, c3 = st.columns(3)
    with c1: render_turret(w2[0], e2)
    with c2: render_turret(w2[1], e2)
    with c3: render_turret(w2[2], e2)

    # WAVE 3
    st.subheader(f"☠️ Wave 3 vs {e3.split('(')[0]}")
    c1, c2, c3 = st.columns(3)
    with c1: render_turret(w3[0], e3)
    with c2: render_turret(w3[1], e3)
    with c3: render_turret(w3[2], e3)
        
