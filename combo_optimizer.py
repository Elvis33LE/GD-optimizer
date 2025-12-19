import json
from itertools import combinations
from typing import Dict, List, Tuple, Set
import streamlit as st

class ComboOptimizer:
    def __init__(self, towers_db, enemies_db, synergy_db, cards_db):
        self.towers_db = towers_db
        self.enemies_db = enemies_db
        self.synergy_db = synergy_db
        self.cards_db = cards_db

        # Pre-compute tower combos and their scores
        self._build_combo_cache()

    def _build_combo_cache(self):
        """Cache all possible tower combinations and their synergy scores"""
        self.combo_cache = {}

        for tower_ids in combinations(self.towers_db.keys(), 2):
            # Check for combo cards between these towers
            combo_score = 0
            combo_cards = []

            # Get cards for first tower
            for card1 in self._get_all_tower_cards(tower_ids[0]):
                if card1.get('type') == 'Combo' and card1.get('combo_partner') == tower_ids[1]:
                    combo_score += card1.get('score', 0) * 2  # Weight combos higher
                    combo_cards.append(card1)

            # Get cards for second tower
            for card2 in self._get_all_tower_cards(tower_ids[1]):
                if card2.get('type') == 'Combo' and card2.get('combo_partner') == tower_ids[0]:
                    combo_score += card2.get('score', 0) * 2
                    combo_cards.append(card2)

            # Check for chain compatibility
            chain_score = self._calculate_chain_compatibility(tower_ids)

            # Calculate damage type diversity
            diversity_score = self._calculate_damage_diversity(tower_ids)

            total_score = combo_score + chain_score + diversity_score

            self.combo_cache[tower_ids] = {
                'total_score': total_score,
                'combo_score': combo_score,
                'chain_score': chain_score,
                'diversity_score': diversity_score,
                'combo_cards': combo_cards,
                'chain_groups': self._get_common_chain_groups(tower_ids)
            }

    def _get_all_tower_cards(self, tower_id):
        """Get all cards for a tower across all tiers"""
        cards = []
        if tower_id in self.cards_db:
            for tier in [1, 2, 3]:
                cards.extend(self.cards_db[tower_id].get(tier, []))
        return cards

    def _calculate_chain_compatibility(self, tower_ids):
        """Calculate how well towers' chain cards work together"""
        chain_groups = self._get_common_chain_groups(tower_ids)

        # Score based on number of shared chain groups and max chain steps
        chain_score = 0
        for group_name in chain_groups:
            max_steps = 0
            for tower_id in tower_ids:
                for card in self._get_all_tower_cards(tower_id):
                    if (card.get('type') == 'Chain' and
                        card.get('chain_group') == group_name):
                        max_steps = max(max_steps, card.get('chain_step', 0))
            chain_score += max_steps * 3  # Chain completion is valuable

        return chain_score

    def _get_common_chain_groups(self, tower_ids):
        """Get chain groups that both towers can participate in"""
        chain_groups = set()

        for tower_id in tower_ids:
            tower_chains = set()
            for card in self._get_all_tower_cards(tower_id):
                if card.get('type') == 'Chain':
                    tower_chains.add(card.get('chain_group'))

            if not chain_groups:
                chain_groups = tower_chains
            else:
                chain_groups &= tower_chains

        return chain_groups

    def _calculate_damage_diversity(self, tower_ids):
        """Calculate diversity score based on damage types"""
        damage_types = set()
        for tower_id in tower_ids:
            if tower_id in self.towers_db:
                damage_types.update(self.towers_db[tower_id].get('damage_tags', []))

        # Reward having multiple damage types
        return len(damage_types) * 2

    def get_best_combinations(self, enemy_type=None, damage_preference=None, top_n=10):
        """Get the best tower combinations for normal mode (Guardian + 4 towers)"""
        results = []

        # Generate all combinations of 4 towers (excluding Guardian as it's fixed)
        other_towers = [tid for tid in self.towers_db.keys() if tid != 'guardian']

        for tower_combo in combinations(other_towers, 4):
            total_score = 0
            combo_info = {
                'towers': ['guardian'] + list(tower_combo),
                'score_breakdown': {},
                'combos': [],
                'chains': []
            }

            # Calculate scores for all tower pairs in the combo
            for pair in combinations(combo_info['towers'], 2):
                if pair in self.combo_cache:
                    cache_data = self.combo_cache[pair]
                    total_score += cache_data['total_score']

                    # Store combo info for display
                    if cache_data['combo_cards']:
                        combo_info['combos'].extend([
                            f"{c['name']} ({self.towers_db[c['tower_id']]['name']} + {self.towers_db[c['combo_partner']]['name']})"
                            for c in cache_data['combo_cards']
                        ])

                    if cache_data['chain_groups']:
                        combo_info['chains'].extend(list(cache_data['chain_groups']))

                    # Update score breakdown
                    for score_type in ['combo_score', 'chain_score', 'diversity_score']:
                        if score_type not in combo_info['score_breakdown']:
                            combo_info['score_breakdown'][score_type] = 0
                        combo_info['score_breakdown'][score_type] += cache_data[score_type]

            # Apply enemy type bonuses
            if enemy_type:
                enemy_bonus = self._calculate_enemy_effectiveness(combo_info['towers'], enemy_type)
                total_score += enemy_bonus
                combo_info['score_breakdown']['enemy_bonus'] = enemy_bonus

            # Apply damage type preferences
            if damage_preference:
                pref_bonus = self._calculate_damage_preference(combo_info['towers'], damage_preference)
                total_score += pref_bonus
                combo_info['score_breakdown']['preference_bonus'] = pref_bonus

            combo_info['total_score'] = total_score
            results.append(combo_info)

        # Sort by total score and return top N
        results.sort(key=lambda x: x['total_score'], reverse=True)
        return results[:top_n]

    def _calculate_enemy_effectiveness(self, tower_ids, enemy_type):
        """Calculate bonus score based on effectiveness against enemy type"""
        # This would need enemy data with resistances/weaknesses
        # For now, implement basic damage type matching
        bonus = 0

        # Example: Fire damage is strong against Insect enemies
        if enemy_type.lower() == 'insect':
            for tower_id in tower_ids:
                if self.towers_db[tower_id].get('type') == 'Fire':
                    bonus += 10

        # Example: Electric damage is strong against Aquatic enemies
        if enemy_type.lower() == 'aquatic':
            for tower_id in tower_ids:
                if self.towers_db[tower_id].get('type') == 'Electric':
                    bonus += 10

        return bonus

    def _calculate_damage_preference(self, tower_ids, preferred_damage):
        """Calculate bonus for preferred damage types"""
        bonus = 0
        for tower_id in tower_ids:
            if self.towers_db[tower_id].get('type') == preferred_damage:
                bonus += 5
        return bonus

def display_combo_optimizer():
    """Display the combo optimizer section in Streamlit"""
    st.header("🎯 Combo Optimizer")
    st.markdown("Find the best tower combinations for normal mode (Guardian + 4 towers)")

    # Load data (assuming it's loaded globally or passed in)
    towers_db, enemies_db, synergy_db, cards_db = st.session_state.get('game_data', (
        st.session_state.get('towers_db', {}),
        st.session_state.get('enemies_db', {}),
        st.session_state.get('synergy_db', {}),
        st.session_state.get('cards_db', {})
    ))

    if not all([towers_db, enemies_db, synergy_db, cards_db]):
        st.error("Game data not loaded. Please check data files.")
        return

    # Initialize optimizer
    if 'combo_optimizer' not in st.session_state:
        st.session_state.combo_optimizer = ComboOptimizer(towers_db, enemies_db, synergy_db, cards_db)

    optimizer = st.session_state.combo_optimizer

    # User inputs
    col1, col2 = st.columns([1, 1])

    with col1:
        enemy_type = st.selectbox(
            "Target Enemy Type",
            options=["Any"] + list(set(e.get('faction', 'Unknown') for e in enemies_db.values())),
            index=0,
            help="Optimize towers against specific enemy factions"
        )

    with col2:
        damage_preference = st.selectbox(
            "Preferred Damage Type",
            options=["Any"] + list(set(t.get('type', 'Unknown') for t in towers_db.values())),
            index=0,
            help="Prefer towers with specific damage type"
        )

    # Optimization button
    if st.button("🔍 Find Best Combinations", type="primary"):
        with st.spinner("Analyzing tower combinations..."):
            results = optimizer.get_best_combinations(
                enemy_type=enemy_type if enemy_type != "Any" else None,
                damage_preference=damage_preference if damage_preference != "Any" else None,
                top_n=10
            )

        # Display results
        st.success(f"Found {len(results)} optimal combinations!")

        for i, combo in enumerate(results, 1):
            with st.expander(f"#{i} - Score: {combo['total_score']:.0f}", expanded=i <= 3):
                # Tower selection
                st.subheader("Tower Combination")
                tower_cols = st.columns(4)
                for j, tower_id in enumerate(combo['towers']):
                    with tower_cols[j]:
                        tower = towers_db[tower_id]
                        st.markdown(f"**{tower['name']}**")
                        st.markdown(f"Type: {tower.get('type', 'N/A')}")
                        st.markdown(f"Role: {tower.get('role', 'N/A')}")

                # Score breakdown
                st.subheader("Score Breakdown")
                score_data = combo['score_breakdown']
                if score_data:
                    for score_type, score in score_data.items():
                        if score > 0:
                            friendly_name = score_type.replace('_', ' ').title()
                            st.metric(friendly_name, f"{score:.0f}")

                # Combo cards
                if combo['combos']:
                    st.subheader("🔗 Key Combos")
                    for combo_card in combo['combos']:
                        st.markdown(f"• {combo_card}")

                # Chain sequences
                if combo['chains']:
                    st.subheader("⚡ Chain Potential")
                    for chain in combo['chains']:
                        st.markdown(f"• {chain}")

                # Damage type breakdown
                st.subheader("Damage Types")
                damage_types = {}
                for tower_id in combo['towers']:
                    for tag in towers_db[tower_id].get('damage_tags', []):
                        damage_types[tag] = damage_types.get(tag, 0) + 1

                for damage_type, count in damage_types.items():
                    st.markdown(f"• {damage_type}: {count} tower(s)")

if __name__ == "__main__":
    # Test the optimizer
    display_combo_optimizer()