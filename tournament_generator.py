import random
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any

class TournamentGenerator:
    """Generate tournament fixtures for different formats"""
    
    def __init__(self, tournament: Dict, teams: List[Dict]):
        self.tournament = tournament
        self.teams = teams
        self.format = tournament.get('format', 'round_robin')
        
    def generate_matches(self) -> List[Dict]:
        """Generate matches based on tournament format"""
        if self.format == 'round_robin':
            return self._generate_round_robin()
        elif self.format == 'knockout':
            return self._generate_knockout()
        elif self.format == 'single_elimination':
            return self._generate_single_elimination()
        elif self.format == 'double_elimination':
            return self._generate_double_elimination()
        elif self.format == 'group_stage':
            return self._generate_group_stage()
        elif self.format == 'swiss':
            return self._generate_swiss_system()
        else:
            # Default to round robin
            return self._generate_round_robin()
    
    def _generate_round_robin(self) -> List[Dict]:
        """Generate round robin matches (everyone plays everyone)"""
        matches = []
        match_number = 1
        
        for i in range(len(self.teams)):
            for j in range(i + 1, len(self.teams)):
                match_data = {
                    'tournament_id': self.tournament['id'],
                    'round_name': 'Round Robin',
                    'match_number': match_number,
                    'team1_id': self.teams[i]['id'],
                    'team2_id': self.teams[j]['id'],
                    'scheduled_date': self._get_match_date(match_number),
                    'venue': self.tournament.get('location', ''),
                    'status': 'scheduled'
                }
                matches.append(match_data)
                match_number += 1
        
        return matches
    
    def _generate_knockout(self) -> List[Dict]:
        """Generate knockout/elimination matches"""
        return self._generate_single_elimination()
    
    def _generate_single_elimination(self) -> List[Dict]:
        """Generate single elimination tournament"""
        matches = []
        teams = self.teams.copy()
        random.shuffle(teams)  # Randomize initial seeding
        
        # Ensure we have a power of 2 teams for proper bracket
        num_teams = len(teams)
        if num_teams < 2:
            return matches
        
        # Calculate number of rounds needed
        total_rounds = math.ceil(math.log2(num_teams))
        
        # Generate first round matches
        round_num = 1
        match_number = 1
        current_teams = teams
        
        while len(current_teams) > 1:
            round_name = self._get_round_name(round_num, total_rounds)
            next_round_teams = []
            
            # Pair up teams for matches
            for i in range(0, len(current_teams), 2):
                if i + 1 < len(current_teams):
                    # Regular match
                    match_data = {
                        'tournament_id': self.tournament['id'],
                        'round_name': round_name,
                        'match_number': match_number,
                        'team1_id': current_teams[i]['id'],
                        'team2_id': current_teams[i + 1]['id'],
                        'scheduled_date': self._get_match_date(match_number),
                        'venue': self.tournament.get('location', ''),
                        'status': 'scheduled'
                    }
                    matches.append(match_data)
                    
                    # For demo, randomly pick winner (in real app, this would be determined by match results)
                    winner = random.choice([current_teams[i], current_teams[i + 1]])
                    next_round_teams.append(winner)
                    
                    match_number += 1
                else:
                    # Bye (team advances automatically)
                    next_round_teams.append(current_teams[i])
            
            current_teams = next_round_teams
            round_num += 1
        
        return matches
    
    def _generate_double_elimination(self) -> List[Dict]:
        """Generate double elimination tournament (winners and losers bracket)"""
        matches = []
        # This is a simplified version - full double elimination is quite complex
        
        # Generate winners bracket (same as single elimination)
        winners_matches = self._generate_single_elimination()
        
        # Add round prefix
        for match in winners_matches:
            match['round_name'] = f"Winners {match['round_name']}"
        
        matches.extend(winners_matches)
        
        # Generate losers bracket matches (simplified)
        # In a real implementation, this would be much more complex
        
        return matches
    
    def _generate_group_stage(self) -> List[Dict]:
        """Generate group stage matches"""
        matches = []
        teams = self.teams.copy()
        random.shuffle(teams)
        
        # Divide teams into groups of 4 (or as close as possible)
        group_size = 4
        num_groups = math.ceil(len(teams) / group_size)
        
        match_number = 1
        
        for group_num in range(num_groups):
            start_idx = group_num * group_size
            end_idx = min(start_idx + group_size, len(teams))
            group_teams = teams[start_idx:end_idx]
            
            # Generate round robin for each group
            group_name = f"Group {chr(65 + group_num)}"  # Group A, B, C, etc.
            
            for i in range(len(group_teams)):
                for j in range(i + 1, len(group_teams)):
                    match_data = {
                        'tournament_id': self.tournament['id'],
                        'round_name': group_name,
                        'match_number': match_number,
                        'team1_id': group_teams[i]['id'],
                        'team2_id': group_teams[j]['id'],
                        'scheduled_date': self._get_match_date(match_number),
                        'venue': self.tournament.get('location', ''),
                        'status': 'scheduled'
                    }
                    matches.append(match_data)
                    match_number += 1
        
        return matches
    
    def _generate_swiss_system(self) -> List[Dict]:
        """Generate Swiss system tournament (first round only)"""
        matches = []
        teams = self.teams.copy()
        random.shuffle(teams)
        
        match_number = 1
        
        # Generate first round by pairing teams randomly
        for i in range(0, len(teams), 2):
            if i + 1 < len(teams):
                match_data = {
                    'tournament_id': self.tournament['id'],
                    'round_name': 'Round 1',
                    'match_number': match_number,
                    'team1_id': teams[i]['id'],
                    'team2_id': teams[i + 1]['id'],
                    'scheduled_date': self._get_match_date(match_number),
                    'venue': self.tournament.get('location', ''),
                    'status': 'scheduled'
                }
                matches.append(match_data)
                match_number += 1
        
        # Note: Swiss system requires subsequent rounds to be generated
        # based on results from previous rounds
        
        return matches
    
    def _get_round_name(self, round_num: int, total_rounds: int) -> str:
        """Get appropriate name for tournament round"""
        if total_rounds <= 1:
            return "Final"
        elif round_num == total_rounds:
            return "Final"
        elif round_num == total_rounds - 1:
            return "Semi-Final"
        elif round_num == total_rounds - 2:
            return "Quarter-Final"
        elif round_num == 1:
            return "First Round"
        else:
            return f"Round {round_num}"
    
    def _get_match_date(self, match_number: int) -> str:
        """Calculate match date based on tournament start date and match number"""
        start_date = self.tournament.get('start_date')
        if not start_date:
            # Default to tomorrow if no start date
            start_date = (datetime.now() + timedelta(days=1)).date()
        else:
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        
        # Schedule matches every few days
        match_date = start_date + timedelta(days=(match_number - 1) * 2)
        
        # Add some time variation
        match_datetime = datetime.combine(match_date, datetime.min.time().replace(hour=14 + (match_number % 6)))
        
        return match_datetime.isoformat()

class StandingsCalculator:
    """Calculate and update tournament standings"""
    
    @staticmethod
    def calculate_team_stats(team_id: str, matches: List[Dict]) -> Dict:
        """Calculate stats for a specific team"""
        stats = {
            'matches_played': 0,
            'wins': 0,
            'draws': 0,
            'losses': 0,
            'goals_for': 0,
            'goals_against': 0,
            'points': 0
        }
        
        for match in matches:
            if match.get('status') != 'completed':
                continue
                
            team1_id = match.get('team1_id')
            team2_id = match.get('team2_id')
            
            if team_id not in [team1_id, team2_id]:
                continue
                
            stats['matches_played'] += 1
            
            team1_score = match.get('team1_score', 0)
            team2_score = match.get('team2_score', 0)
            
            if team_id == team1_id:
                # Team is team1
                stats['goals_for'] += team1_score
                stats['goals_against'] += team2_score
                
                if team1_score > team2_score:
                    stats['wins'] += 1
                    stats['points'] += 3
                elif team1_score == team2_score:
                    stats['draws'] += 1
                    stats['points'] += 1
                else:
                    stats['losses'] += 1
                    
            else:
                # Team is team2
                stats['goals_for'] += team2_score
                stats['goals_against'] += team1_score
                
                if team2_score > team1_score:
                    stats['wins'] += 1
                    stats['points'] += 3
                elif team2_score == team1_score:
                    stats['draws'] += 1
                    stats['points'] += 1
                else:
                    stats['losses'] += 1
        
        stats['goal_difference'] = stats['goals_for'] - stats['goals_against']
        
        return stats
