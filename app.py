import streamlit as st
import itertools

# --- 1. DEFINE YOUR SPECIFIC ARSENAL ---
# Based on your screenshots, these are your 9 available cards.
TURRETS = [
    "Guardian (Mecha)",
    "Teslacoil (No Paralyze)",
    "Thunderbolt (Stun)",
    "Firewheel (Drones)",
    "Sky Guard (Sniper)",
    "Aeroblast (Mines)",
    "Gravity Vortex (Pull)",
    "Disruption Drone (Slow)",
    "Beam Turret (Vulnerable)"
]

# --- 2. DEFINE THE ENEMIES ---
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

# --- 3. THE BRAIN: SCORING MATRIX ---
# This scores how good a turret is against an enemy (0-100).
# -100 means "DO NOT USE" (e.g., Debuffs vs Starcore).
# Based on your specific Card Unlocks (e.g., Aeroblast Mines, Beam Vulnerable).

SCORES = {
    # Format: (Enemy, Turret): Score
    
    # --- ENEMY 1: PRISTINE STARCORE (Heals on Debuff) ---
    # Weak: Phys/Elec. DANGER: No Debuffs.
    ("Pristine Starcore (Healer)", "Guardian (Mecha)"): 100, # Pure Phys carry
    ("Pristine Starcore (Healer)", "Teslacoil (No Paralyze)"): 90, # Safe Elec damage
    ("Pristine Starcore (Healer)", "Sky Guard (Sniper)"): 85, # Safe Phys impact
    ("Pristine Starcore (Healer)", "Firewheel (Drones)"): 80, # Drones are safe units
    ("Pristine Starcore (Healer)", "Aeroblast (Mines)"): 75, # Mines are traps (safe)
    ("Pristine Starcore (Healer)", "Thunderbolt (Stun)"): -100, # DANGER: Stun heals it
    ("Pristine Starcore (Healer)", "Disruption Drone (Slow)"): -100, # DANGER: Slow heals it
    ("Pristine Starcore (Healer)", "Beam Turret (Vulnerable)"): -100, # DANGER: Vuln heals it
    ("Pristine Starcore (Healer)", "Gravity Vortex (Pull)"): -50, # risky/low damage

    # --- ENEMY 2: SCOUT DRONE (Invisible) ---
    # Weak: Phys. Needs Tracking/Traps.
    ("Alien Scout Drone (Invisible)", "Firewheel (Drones)"): 100, # MVP: Auto-tracking
    ("Alien Scout Drone (Invisible)", "Aeroblast (Mines)"): 95, # Mines kill invisible units
    ("Alien Scout Drone (Invisible)", "Guardian (Mecha)"): 85, # Volley hits area
    ("Alien Scout Drone (Invisible)", "Beam Turret (Vulnerable)"): 80, # Auto-lock
    
    # --- ENEMY 3: CROWN GUARD (Sniper) ---
    # Weak: Phys. Kill fast.
    ("Stellar Crown Guard (Sniper)", "Sky Guard (Sniper)"): 100, # Range counter
    ("Stellar Crown Guard (Sniper)", "Guardian (Mecha)"): 90, # Burst
    ("Stellar Crown Guard (Sniper)", "Disruption Drone (Slow)"): 85, # Keeps them away

    # --- ENEMY 4: METEORITE (Swarm) ---
    # Needs AoE.
    ("Meteorite (Swarm)", "Firewheel (Drones)"): 100,
    ("Meteorite (Swarm)", "Aeroblast (Mines)"): 95,
    ("Meteorite (Swarm)", "Thunderbolt (Stun)"): 90,

    # --- ENEMY 5: COSMIC CUBE (Tank) ---
    # Resists Energy. Needs Phys + Grouping.
    ("Cosmic Cube (Tank)", "Guardian (Mecha)"): 100, # Phys Burst
    ("Cosmic Cube (Tank)", "Gravity Vortex (Pull)"): 100, # Mandatory grouping
    ("Cosmic Cube (Tank)", "Sky Guard (Sniper)"): 95, # Phys Impact
    ("Cosmic Cube (Tank)", "Beam Turret (Vulnerable)"): 10, # Resisted
    ("Cosmic Cube (Tank)", "Teslacoil (No Paralyze)"): 10, # Weak
    
    # --- ENEMY 6: ROCK WALKER (Runner) ---
    # Immune to Slow <50%. Weak Elec.
    ("Rock Walker (Runner)", "Gravity Vortex (Pull)"): 100, # Trap them early
    ("Rock Walker (Runner)", "Teslacoil (No Paralyze)"): 100, # Chain Surge
    ("Rock Walker (Runner)", "Thunderbolt (Stun)"): 90, # Electric Weakness

    # --- BOSS 1: COLOSSUS (Shield) ---
    # Resists Force. Needs Shield Break.
    ("Elite Rift Colossus (Shield Boss)", "Guardian (Mecha)"): 100, # High DPS break
    ("Elite Rift Colossus (Shield Boss)", "Beam Turret (Vulnerable)"): 95, # Removes defense
    ("Elite Rift Colossus (Shield Boss)", "Sky Guard (Sniper)"): 85, # Impact burst
    ("Elite Rift Colossus (Shield Boss)", "Disruption Drone (Slow)"): 30, # Resisted
    
    # --- BOSS 2: GOLEM (Splitter) ---
    # Resists Energy. Splits on death.
    ("Elite Alien Golem (Split Boss)", "Aeroblast (Mines)"): 100, # MVP: Spawn camp minions
    ("Elite Alien Golem (Split Boss)", "Guardian (Mecha)"): 90, # Phys DPS
    ("Elite Alien Golem (Split Boss)", "Beam Turret (Vulnerable)"): 85, # Buffs mines
    ("Elite Alien Golem (Split Boss)", "Gravity Vortex (Pull)"): 80, # Cleanup splits
    ("Elite Alien Golem (Split Boss)", "Teslacoil (No Paralyze)"): 10, # Resisted
}

# Default score for undefined combos
def get_score(enemy, turret):
    return SCORES.get((enemy, turret), 50) 

# --- 4. THE SOLVER ALGORITHM ---
def solve_loadout(e1, e2, e3):
    best_score = -9999
    best_loadout = None
    
    # Generate all permutations of the 9 turrets
    # This checks every possible way to arrange your cards
    # Since 9! is small for a computer, this is instant.
    for p in itertools.permutations(TURRETS):
        wave1 = p[0:3]
        wave2 = p[3:6]
        wave3 = p[6:9]
        
        # Calculate Total Score
        score = 0
        score += sum([get_score(e1, t) for t in wave1])
        score += sum([get_score(e2, t) for t in wave2])
        score += sum([get_score(e3, t) for t in wave3])
        
        if score > best_score:
            best_score = score
            best_loadout = (wave1, wave2, wave3)
            
    return best_loadout

# --- 5. THE UI (STREAMLIT) ---
st.set_page_config(page_title="Vanguard Strategizer", layout="centered")

st.title("🛡️ Galaxy Defense: Vanguard Optimizer")
st.markdown("Select your enemies from the battle preview. This tool calculates the **perfect mathematical counter** using your 9 specific cards with **No Repeats**.")

col1, col2, col3 = st.columns(3)
with col1:
    e1 = st.selectbox("Wave 1 Enemy", ENEMIES, index=0)
with col2:
    e2 = st.selectbox("Wave 2 Enemy", ENEMIES, index=4) # Default to Cube
with col3:
    e3 = st.selectbox("Wave 3 Enemy", ENEMIES, index=7) # Default to Golem

if st.button("🚀 Calculate Optimal Strategy"):
    w1, w2, w3 = solve_loadout(e1, e2, e3)
    
    st.divider()
    
    # Display Wave 1
    st.subheader(f"🌊 Wave 1: vs {e1.split('(')[0]}")
    c1, c2, c3 = st.columns(3)
    c1.info(f"**{w1[0]}**")
    c2.info(f"**{w1[1]}**")
    c3.info(f"**{w1[2]}**")
    
    # Display Wave 2
    st.subheader(f"🛡️ Wave 2: vs {e2.split('(')[0]}")
    c1, c2, c3 = st.columns(3)
    c1.warning(f"**{w2[0]}**")
    c2.warning(f"**{w2[1]}**")
    c3.warning(f"**{w2[2]}**")
    
    # Display Wave 3
    st.subheader(f"☠️ Wave 3: vs {e3.split('(')[0]}")
    c1, c2, c3 = st.columns(3)
    c1.error(f"**{w3[0]}**")
    c2.error(f"**{w3[1]}**")
    c3.error(f"**{w3[2]}**")

    st.success("Strategy Generated! This creates the highest scoring combination avoiding all immunities (e.g. Healer vs Debuffs).")
