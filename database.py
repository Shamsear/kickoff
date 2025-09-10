import os
from supabase import create_client, Client
from typing import Optional, Dict, List, Any
from datetime import datetime
import uuid
from uuid import uuid4
import time
from functools import lru_cache

# Global Supabase client
supabase: Optional[Client] = None

def init_supabase():
    """Initialize Supabase client with optimized settings"""
    global supabase
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_ANON_KEY')
    
    if url and key:
        # Create client with basic optimizations
        try:
            supabase = create_client(url, key)
            print("✅ Supabase client initialized with optimizations")
        except Exception as e:
            print(f"⚠️ Failed to create Supabase client: {e}")
            supabase = None
    else:
        print("⚠️ Supabase credentials not found in environment variables")
        # For development, we'll create a mock client
        supabase = None
    
    return supabase

def get_supabase_client():
    """Get the Supabase client instance"""
    return supabase

class DatabaseManager:
    """Database operations manager for Supabase"""
    
    def __init__(self):
        self._user_cache = {}  # Simple in-memory cache
        self._cache_timeout = 300  # 5 minutes cache timeout
        self._dev_solo_matches = {}  # In-memory storage for development solo matches
    
    @property
    def client(self):
        """Dynamically get the current Supabase client"""
        return get_supabase_client()
    
    def _cache_key(self, table, identifier):
        """Generate cache key"""
        return f"{table}:{identifier}"
    
    def _get_from_cache(self, key):
        """Get item from cache if not expired"""
        if key in self._user_cache:
            data, timestamp = self._user_cache[key]
            if time.time() - timestamp < self._cache_timeout:
                return data
            else:
                del self._user_cache[key]
        return None
    
    def _set_cache(self, key, data):
        """Set item in cache"""
        self._user_cache[key] = (data, time.time())
    
    def _clear_user_cache(self, email=None):
        """Clear user cache for specific email or all"""
        if email:
            key = self._cache_key('user', email)
            if key in self._user_cache:
                del self._user_cache[key]
        else:
            self._user_cache.clear()
    
    # User operations
    def create_user(self, email: str, password: str, full_name: str) -> Dict:
        """Create a new user"""
        try:
            if not self.client:
                # Mock response for development - simulate successful creation
                print(f"Mock: Creating user with email {email}")
                user = {
                    'id': str(uuid.uuid4()),
                    'email': email,
                    'full_name': full_name,
                    'created_at': datetime.now().isoformat()
                }
                # Update cache
                self._set_cache(self._cache_key('user', email), user)
                return {
                    'success': True,
                    'user': user
                }
            
            # Insert user data (store hashed password if using auth later)
            response = self.client.table('users').insert({
                'email': email,
                'full_name': full_name,
                'created_at': datetime.now().isoformat()
            }).execute()
            user = response.data[0]
            # Update cache
            self._set_cache(self._cache_key('user', email), user)
            return {'success': True, 'user': user}
        except Exception as e:
            # Check if it's a duplicate key error
            error_msg = str(e).lower()
            if 'unique' in error_msg or 'duplicate' in error_msg:
                return {'success': False, 'error': 'An account with this email already exists'}
            return {'success': False, 'error': str(e)}
    
    def create_user_if_not_exists(self, email: str, password: str, full_name: str) -> Dict:
        """Optimized user creation that checks existence efficiently"""
        try:
            if not self.client:
                # Mock: check if user exists first
                cache_key = self._cache_key('user', email)
                if self._get_from_cache(cache_key):
                    return {'success': False, 'error': 'An account with this email already exists'}
                # Create mock user
                return self.create_user(email, password, full_name)
            
            # For Supabase, use upsert with conflict handling
            response = self.client.table('users').upsert({
                'email': email,
                'full_name': full_name,
                'created_at': datetime.now().isoformat()
            }, on_conflict='email', ignore_duplicates=False).execute()
            
            if response.data:
                user = response.data[0]
                self._set_cache(self._cache_key('user', email), user)
                return {'success': True, 'user': user}
            else:
                return {'success': False, 'error': 'Failed to create user'}
                
        except Exception as e:
            error_msg = str(e).lower()
            if 'unique' in error_msg or 'duplicate' in error_msg or 'already exists' in error_msg:
                return {'success': False, 'error': 'An account with this email already exists'}
            return {'success': False, 'error': str(e)}
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email with caching"""
        try:
            if not self.client:
                # Return None when no client available (for development)
                return None
            
            # Check cache first
            cache_key = self._cache_key('user', email)
            cached_user = self._get_from_cache(cache_key)
            if cached_user is not None:
                return cached_user
            
            # Query database with optimized select
            response = self.client.table('users').select('id,email,full_name,created_at').eq('email', email).limit(1).execute()
            user = response.data[0] if response.data else None
            
            # Cache the result (including None results to avoid repeated queries)
            self._set_cache(cache_key, user)
            return user
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        try:
            if not self.client:
                return {
                    'id': user_id,
                    'email': 'test@example.com',
                    'full_name': 'Test User',
                    'created_at': datetime.now().isoformat()
                }
            
            response = self.client.table('users').select('*').eq('id', user_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error getting user by ID: {e}")
            return None
    
    # Tournament operations
    def create_tournament(self, tournament_data: Dict) -> Dict:
        """Create a new tournament"""
        try:
            tournament_data['id'] = str(uuid.uuid4())
            tournament_data['created_at'] = datetime.now().isoformat()
            tournament_data['updated_at'] = datetime.now().isoformat()
            
            if not self.client:
                return {'success': True, 'tournament': tournament_data}
            
            response = self.client.table('tournaments').insert(tournament_data).execute()
            return {'success': True, 'tournament': response.data[0]}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_tournaments_by_user(self, user_id: str) -> List[Dict]:
        """Get all tournaments created by a user"""
        try:
            if not self.client:
                return []
            
            response = self.client.table('tournaments').select('*').eq('organizer_id', user_id).execute()
            return response.data
        except Exception as e:
            print(f"Error getting tournaments: {e}")
            return []
    
    def get_tournament_by_id(self, tournament_id: str) -> Optional[Dict]:
        """Get tournament by ID"""
        try:
            # Only return mock data if no client exists
            if not self.client:
                return {
                    'id': tournament_id,
                    'name': 'eFootball Solo Championship',
                    'description': 'A mock solo tournament for development and testing',
                    'sport': 'efootball',
                    'format': 'single_elimination',
                    'type': 'solo',
                    'status': 'registration_open',
                    'max_participants': 32,
                    'max_teams': None,
                    'max_players_per_team': None,
                    'scoring_system': None,  # Solo tournaments don't have scoring systems
                    'entry_fee': 0,
                    'prize_pool': 500,
                    'organizer_id': 'mock-organizer-123',
                    'is_public': True,
                    'location': 'Online',
                    'rules': 'Standard eFootball rules apply',
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
            
            # Always query the database if client exists
            response = self.client.table('tournaments').select('*').eq('id', tournament_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error getting tournament: {e}")
            return None
    
    def update_tournament(self, tournament_id: str, data: Dict) -> Dict:
        """Update tournament data"""
        try:
            data['updated_at'] = datetime.now().isoformat()
            
            if not self.client:
                return {'success': True, 'tournament': data}
            
            response = self.client.table('tournaments').update(data).eq('id', tournament_id).execute()
            return {'success': True, 'tournament': response.data[0]}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # Team operations
    def create_team(self, team_data: Dict) -> Dict:
        """Create a new team"""
        try:
            team_data['id'] = str(uuid.uuid4())
            team_data['created_at'] = datetime.now().isoformat()
            
            if not self.client:
                return {'success': True, 'team': team_data}
            
            response = self.client.table('teams').insert(team_data).execute()
            return {'success': True, 'team': response.data[0]}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_teams_by_tournament(self, tournament_id: str) -> List[Dict]:
        """Get all teams in a tournament"""
        try:
            if not self.client:
                return []
            
            response = self.client.table('teams').select('*').eq('tournament_id', tournament_id).execute()
            return response.data
        except Exception as e:
            print(f"Error getting teams: {e}")
            return []
    
    def get_team_by_id(self, team_id: str) -> Optional[Dict]:
        """Get team by ID"""
        try:
            if not self.client:
                return {
                    'id': team_id,
                    'name': 'Mock Team',
                    'short_name': 'MOCK',
                    'captain_name': 'Mock Captain',
                    'captain_email': 'mock@example.com',
                    'captain_phone': '123-456-7890',
                    'is_approved': True,
                    'created_at': datetime.now().isoformat()
                }
            
            response = self.client.table('teams').select('*').eq('id', team_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error getting team by ID: {e}")
            return None
    
    def update_team(self, team_id: str, team_data: Dict) -> Dict:
        """Update team data"""
        try:
            team_data['updated_at'] = datetime.now().isoformat()
            
            if not self.client:
                return {'success': True, 'team': team_data}
            
            response = self.client.table('teams').update(team_data).eq('id', team_id).execute()
            return {'success': True, 'team': response.data[0]}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def delete_team(self, team_id: str) -> Dict:
        """Delete a team"""
        try:
            if not self.client:
                return {'success': True, 'message': 'Team deleted successfully'}
            
            response = self.client.table('teams').delete().eq('id', team_id).execute()
            return {'success': True, 'message': 'Team deleted successfully'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # Player operations
    def create_player(self, player_data: Dict) -> Dict:
        """Create a new player"""
        try:
            player_data['id'] = str(uuid.uuid4())
            player_data['created_at'] = datetime.now().isoformat()
            
            if not self.client:
                return {'success': True, 'player': player_data}
            
            response = self.client.table('players').insert(player_data).execute()
            return {'success': True, 'player': response.data[0]}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_players_by_team(self, team_id: str) -> List[Dict]:
        """Get all players in a team"""
        try:
            if not self.client:
                # Return mock players for development mode
                return [
                    {
                        'id': 'mock-player-1',
                        'team_id': team_id,
                        'name': 'Alex Rodriguez',
                        'jersey_number': 10,
                        'position': 'Forward',
                        'email': 'alex@example.com'
                    },
                    {
                        'id': 'mock-player-2',
                        'team_id': team_id,
                        'name': 'Maria Santos',
                        'jersey_number': 7,
                        'position': 'Midfielder',
                        'email': 'maria@example.com'
                    },
                    {
                        'id': 'mock-player-3',
                        'team_id': team_id,
                        'name': 'David Kim',
                        'jersey_number': 9,
                        'position': 'Forward',
                        'email': 'david@example.com'
                    },
                    {
                        'id': 'mock-player-4',
                        'team_id': team_id,
                        'name': 'Sarah Johnson',
                        'jersey_number': 11,
                        'position': 'Midfielder',
                        'email': 'sarah@example.com'
                    }
                ]
            
            response = self.client.table('players').select('*').eq('team_id', team_id).execute()
            return response.data
        except Exception as e:
            print(f"Error getting players: {e}")
            return []
    
    def get_player_by_id(self, player_id: str) -> Optional[Dict]:
        """Get player by ID"""
        try:
            if not self.client:
                return {
                    'id': player_id,
                    'name': 'Mock Player',
                    'jersey_number': 1,
                    'position': 'Forward',
                    'email': 'mock@example.com',
                    'phone': '123-456-7890',
                    'created_at': datetime.now().isoformat()
                }
            
            response = self.client.table('players').select('*').eq('id', player_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error getting player by ID: {e}")
            return None
    
    def update_player(self, player_id: str, player_data: Dict) -> Dict:
        """Update player data"""
        try:
            player_data['updated_at'] = datetime.now().isoformat()
            
            if not self.client:
                return {'success': True, 'player': player_data}
            
            response = self.client.table('players').update(player_data).eq('id', player_id).execute()
            return {'success': True, 'player': response.data[0]}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def delete_player(self, player_id: str) -> Dict:
        """Delete a player"""
        try:
            if not self.client:
                return {'success': True, 'message': 'Player deleted successfully'}
            
            response = self.client.table('players').delete().eq('id', player_id).execute()
            return {'success': True, 'message': 'Player deleted successfully'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # Participant operations (for solo tournaments)
    def create_participant(self, participant_data: Dict) -> Dict:
        """Create a new participant for solo tournaments"""
        try:
            participant_data['id'] = str(uuid.uuid4())
            participant_data['created_at'] = datetime.now().isoformat()
            participant_data['status'] = 'active'
            
            if not self.client:
                return {'success': True, 'participant': participant_data}
            
            response = self.client.table('participants').insert(participant_data).execute()
            return {'success': True, 'participant': response.data[0]}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_participants_by_tournament(self, tournament_id: str) -> List[Dict]:
        """Get all participants in a tournament"""
        try:
            # Only return mock data if no client exists
            if not self.client:
                # Return mock participants for development/testing
                return [
                    {
                        'id': 'mock-participant-1',
                        'name': 'John Doe',
                        'email': 'john@example.com',
                        'gamer_tag': 'JohnGamer',
                        'tournament_id': tournament_id,
                        'status': 'active',
                        'created_at': '2024-12-09T10:00:00Z'
                    },
                    {
                        'id': 'mock-participant-2',
                        'name': 'Jane Smith', 
                        'email': 'jane@example.com',
                        'gamer_tag': 'JanePlayer',
                        'tournament_id': tournament_id,
                        'status': 'active',
                        'created_at': '2024-12-09T11:00:00Z'
                    },
                    {
                        'id': 'mock-participant-3',
                        'name': 'Mike Wilson',
                        'email': 'mike@example.com', 
                        'gamer_tag': 'MikeChamp',
                        'tournament_id': tournament_id,
                        'status': 'active',
                        'created_at': '2024-12-09T12:00:00Z'
                    }
                ]
            
            # Always query the database if client exists
            response = self.client.table('participants').select('*').eq('tournament_id', tournament_id).execute()
            return response.data
        except Exception as e:
            print(f"Error getting participants: {e}")
            return []
    
    def get_participant_by_id(self, participant_id: str) -> Optional[Dict]:
        """Get participant by ID"""
        try:
            if not self.client:
                return {
                    'id': participant_id,
                    'name': 'Mock Participant',
                    'email': 'mock@example.com',
                    'phone': '123-456-7890',
                    'gamer_tag': 'MockGamer',
                    'skill_level': 'Intermediate',
                    'status': 'active',
                    'created_at': datetime.now().isoformat()
                }
            
            response = self.client.table('participants').select('*').eq('id', participant_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error getting participant by ID: {e}")
            return None
    
    def update_participant(self, participant_id: str, participant_data: Dict) -> Dict:
        """Update participant data"""
        try:
            participant_data['updated_at'] = datetime.now().isoformat()
            
            if not self.client:
                return {'success': True, 'participant': participant_data}
            
            response = self.client.table('participants').update(participant_data).eq('id', participant_id).execute()
            return {'success': True, 'participant': response.data[0]}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def delete_participant(self, participant_id: str) -> Dict:
        """Delete a participant"""
        try:
            if not self.client:
                return {'success': True, 'message': 'Participant deleted successfully'}
            
            response = self.client.table('participants').delete().eq('id', participant_id).execute()
            return {'success': True, 'message': 'Participant deleted successfully'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_participant_by_email(self, tournament_id: str, email: str) -> Optional[Dict]:
        """Check if participant with email already exists in tournament"""
        try:
            if not self.client:
                return None
            
            response = self.client.table('participants').select('*').eq('tournament_id', tournament_id).eq('email', email).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error checking participant by email: {e}")
            return None
    
    # Match operations
    def create_match(self, match_data: Dict) -> Dict:
        """Create a new match"""
        try:
            match_data['id'] = str(uuid.uuid4())
            match_data['created_at'] = datetime.now().isoformat()
            match_data['status'] = 'scheduled'
            
            if not self.client:
                return {'success': True, 'match': match_data}
            
            response = self.client.table('matches').insert(match_data).execute()
            return {'success': True, 'match': response.data[0]}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_matches_by_tournament(self, tournament_id: str) -> List[Dict]:
        """Get all matches in a tournament"""
        try:
            if not self.client:
                return []
            
            response = self.client.table('matches').select('*').eq('tournament_id', tournament_id).execute()
            return response.data
        except Exception as e:
            print(f"Error getting matches: {e}")
            return []
    
    def get_solo_matches_by_tournament(self, tournament_id: str) -> List[Dict]:
        """Get all solo matches in a tournament"""
        try:
            # Only return mock data if no client exists at all
            if not self.client:
                # Return mock solo matches for development/testing when no database
                return [
                    {
                        'id': 'mock-solo-match-1',
                        'tournament_id': tournament_id,
                        'participant1_id': 'mock-participant-1',
                        'participant2_id': 'mock-participant-2',
                        'participant1_score': 2,
                        'participant2_score': 1,
                        'status': 'completed',
                        'winner_id': 'mock-participant-1',
                        'round': 1,
                        'created_at': '2024-12-09T14:00:00Z'
                    },
                    {
                        'id': 'mock-solo-match-2',
                        'tournament_id': tournament_id,
                        'participant1_id': 'mock-participant-3',
                        'participant2_id': 'mock-participant-1',
                        'participant1_score': None,
                        'participant2_score': None,
                        'status': 'scheduled',
                        'winner_id': None,
                        'round': 1,
                        'created_at': '2024-12-09T15:00:00Z'
                    }
                ]
            
            # Always query the database if client exists
            response = self.client.table('solo_matches').select('*').eq('tournament_id', tournament_id).execute()
            return response.data
        except Exception as e:
            print(f"Error getting solo matches: {e}")
            return []
    
    def get_match_by_id(self, match_id: str) -> Optional[Dict]:
        """Get match by ID"""
        try:
            if not self.client:
                return {
                    'id': match_id,
                    'team1_id': 'mock-team-1',
                    'team2_id': 'mock-team-2',
                    'status': 'scheduled',
                    'team1_score': 0,
                    'team2_score': 0,
                    'team1_player_goals': None,
                    'team2_player_goals': None,
                    'team1_player_id': None,
                    'team2_player_id': None,
                    'venue': '',
                    'notes': '',
                    'referee': '',
                    'created_at': datetime.now().isoformat()
                }
            
            response = self.client.table('matches').select('*').eq('id', match_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error getting match by ID: {e}")
            return None
    
    def update_match_score(self, match_id: str, score_data: Dict) -> Dict:
        """Update match score and status"""
        try:
            score_data['updated_at'] = datetime.now().isoformat()
            
            if not self.client:
                return {'success': True, 'match': score_data}
            
            response = self.client.table('matches').update(score_data).eq('id', match_id).execute()
            return {'success': True, 'match': response.data[0]}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def create_solo_match(self, match_data: Dict) -> Dict:
        """Create a new solo match"""
        try:
            match_data['id'] = str(uuid.uuid4())
            match_data['created_at'] = datetime.now().isoformat()
            if 'status' not in match_data:
                match_data['status'] = 'scheduled'
            
            # Only return mock response if no client exists at all
            if not self.client:
                return {'success': True, 'match': match_data}
            
            # Always try to save to database if client exists
            response = self.client.table('solo_matches').insert(match_data).execute()
            return {'success': True, 'match': response.data[0]}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_solo_match_by_id(self, match_id: str) -> Optional[Dict]:
        """Get solo match by ID"""
        try:
            if not self.client:
                # Return mock solo match for development
                return {
                    'id': match_id,
                    'tournament_id': 'mock-tournament-123',
                    'participant1_id': 'mock-participant-1',
                    'participant2_id': 'mock-participant-2',
                    'participant1_score': None,
                    'participant2_score': None,
                    'status': 'scheduled',
                    'winner_id': None,
                    'round': 1,
                    'match_date': None,
                    'created_at': datetime.now().isoformat()
                }
            
            response = self.client.table('solo_matches').select('*').eq('id', match_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error getting solo match by ID: {e}")
            return None
    
    def update_solo_match(self, match_id: str, match_data: Dict) -> Dict:
        """Update solo match data"""
        try:
            match_data['updated_at'] = datetime.now().isoformat()
            
            if not self.client:
                return {'success': True, 'match': match_data}
            
            response = self.client.table('solo_matches').update(match_data).eq('id', match_id).execute()
            return {'success': True, 'match': response.data[0] if response.data else match_data}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def delete_solo_match(self, match_id: str) -> Dict:
        """Delete a solo match"""
        try:
            if not self.client:
                return {'success': True, 'message': 'Solo match deleted successfully'}
            
            response = self.client.table('solo_matches').delete().eq('id', match_id).execute()
            return {'success': True, 'message': 'Solo match deleted successfully'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_all_tournaments(self, limit: int = 1000) -> List[Dict]:
        """Get all tournaments for statistics (admin/platform level)"""
        try:
            if not self.client:
                # Return mock data for development with realistic numbers
                return [
                    {
                        'id': f'mock-tournament-{i}',
                        'name': f'Tournament {i}',
                        'type': 'solo' if i % 2 == 0 else 'team',
                        'status': 'completed' if i < 800 else ('in_progress' if i < 850 else 'registration_open'),
                        'created_at': datetime.now().isoformat(),
                        'organizer_id': f'user-{i % 100}'
                    } for i in range(1, 1001)
                ]
            
            response = self.client.table('tournaments').select('*').limit(limit).execute()
            return response.data
        except Exception as e:
            print(f"Error getting all tournaments: {e}")
            return []
    
    # Public tournament access methods
    def get_public_tournaments(self, limit: int = 50) -> List[Dict]:
        """Get all public tournaments available for registration"""
        try:
            if not self.client:
                # Return mock data for development
                return [
                    {
                        'id': 'mock-tournament-1',
                        'name': 'eFootball Championship 2024',
                        'description': 'Annual eFootball tournament for all skill levels',
                        'type': 'solo',
                        'format': 'single_elimination',
                        'status': 'registration_open',
                        'max_participants': 32,
                        'registration_deadline': '2024-12-31T23:59:59',
                        'start_date': '2025-01-15T18:00:00',
                        'entry_fee': 0,
                        'prize_pool': 1000,
                        'organizer_name': 'Tournament Admin',
                        'created_at': datetime.now().isoformat(),
                        'participant_count': 12
                    },
                    {
                        'id': 'mock-tournament-2', 
                        'name': 'Team eFootball League',
                        'description': 'Professional team competition',
                        'type': 'team',
                        'format': 'round_robin',
                        'status': 'registration_open',
                        'max_teams': 16,
                        'registration_deadline': '2024-12-25T23:59:59',
                        'start_date': '2025-01-10T19:00:00',
                        'entry_fee': 50,
                        'prize_pool': 5000,
                        'organizer_name': 'Pro League',
                        'created_at': datetime.now().isoformat(),
                        'team_count': 8
                    }
                ]
            
            # Query public tournaments with participant counts
            response = self.client.table('tournaments').select(
                '*,'
                'participants(count),'
                'teams(count),'
                'users!tournaments_organizer_id_fkey(full_name)'
            ).in_('status', ['registration_open', 'in_progress', 'draft']).limit(limit).execute()
            
            tournaments = []
            for tournament in response.data:
                tournament_data = tournament.copy()
                # Add participant/team counts
                if tournament['type'] == 'solo':
                    tournament_data['participant_count'] = len(tournament.get('participants', []))
                else:
                    tournament_data['team_count'] = len(tournament.get('teams', []))
                
                # Add organizer name
                if tournament.get('users'):
                    tournament_data['organizer_name'] = tournament['users']['full_name']
                
                tournaments.append(tournament_data)
            
            return tournaments
        except Exception as e:
            print(f"Error getting public tournaments: {e}")
            return []
    
    def get_public_tournament_details(self, tournament_id: str) -> Optional[Dict]:
        """Get detailed information about a public tournament including participant info"""
        try:
            if not self.client:
                # Return mock detailed tournament
                return {
                    'id': tournament_id,
                    'name': 'eFootball Championship 2024',
                    'description': 'Annual eFootball tournament for all skill levels. Open to players of all experience levels.',
                    'type': 'solo',
                    'format': 'single_elimination',
                    'status': 'registration_open',
                    'max_participants': 32,
                    'registration_deadline': '2024-12-31T23:59:59',
                    'start_date': '2025-01-15T18:00:00',
                    'end_date': '2025-01-16T22:00:00',
                    'entry_fee': 0,
                    'prize_pool': 1000,
                    'rules': 'Standard eFootball rules apply. Best of 3 matches in elimination rounds.',
                    'organizer_name': 'Tournament Admin',
                    'organizer_email': 'admin@tournament.com',
                    'created_at': datetime.now().isoformat(),
                    'participant_count': 12,
                    'participants': []
                }
            
            # Get tournament with full details
            response = self.client.table('tournaments').select(
                '*,'
                'participants(*),'
                'teams(*),'
                'users!tournaments_organizer_id_fkey(full_name,email)'
            ).eq('id', tournament_id).execute()
            
            if not response.data:
                return None
                
            tournament = response.data[0]
            
            # Add computed fields
            if tournament['type'] == 'solo':
                tournament['participant_count'] = len(tournament.get('participants', []))
            else:
                tournament['team_count'] = len(tournament.get('teams', []))
            
            if tournament.get('users'):
                tournament['organizer_name'] = tournament['users']['full_name']
                tournament['organizer_email'] = tournament['users']['email']
            
            return tournament
        except Exception as e:
            print(f"Error getting tournament details: {e}")
            return None
    
    def register_for_tournament(self, tournament_id: str, registration_data: Dict) -> Dict:
        """Register a participant for a tournament with comprehensive validation"""
        try:
            # Get tournament first to check type and capacity
            tournament = self.get_public_tournament_details(tournament_id)
            if not tournament:
                return {'success': False, 'error': 'Tournament not found or no longer available'}
            
            if tournament['status'] != 'registration_open':
                status_messages = {
                    'draft': 'Registration has not started yet for this tournament',
                    'in_progress': 'Registration is closed - tournament has already started',
                    'completed': 'This tournament has already ended',
                    'cancelled': 'This tournament has been cancelled'
                }
                message = status_messages.get(tournament['status'], 'Registration is not currently open')
                return {'success': False, 'error': message}
            
            # Check registration deadline
            if tournament.get('registration_deadline'):
                from datetime import datetime
                deadline = datetime.fromisoformat(tournament['registration_deadline'].replace('Z', '+00:00'))
                if datetime.now() > deadline:
                    return {'success': False, 'error': 'Registration deadline has passed'}
            
            # Handle solo tournament registration
            if tournament['type'] == 'solo':
                # Check for duplicate registration
                existing = self.get_participant_by_email(tournament_id, registration_data['email'])
                if existing:
                    return {'success': False, 'error': 'This email address is already registered for this tournament'}
                
                # Check capacity with more specific message
                current_count = tournament.get('participant_count', 0)
                max_participants = tournament.get('max_participants', 0)
                if current_count >= max_participants:
                    return {'success': False, 'error': f'Tournament is full ({max_participants} participants maximum)'}
                
                # Create participant with enhanced data
                participant_data = {
                    'tournament_id': tournament_id,
                    'name': registration_data['name'],
                    'email': registration_data['email'],
                    'phone': registration_data.get('phone', ''),
                    'psn_id': registration_data.get('psn_id', ''),
                    'skill_level': registration_data.get('skill_level', 'beginner'),
                    'status': 'registered',
                    'registration_date': datetime.now().isoformat()
                }
                result = self.create_participant(participant_data)
                if result.get('success'):
                    result['message'] = f'Successfully registered! You are participant #{current_count + 1} of {max_participants}'
                return result
            
            else:  # team tournament
                # Check for duplicate team name (case-insensitive)
                existing_teams = self.get_teams_by_tournament(tournament_id)
                team_names = [team['name'].lower().strip() for team in existing_teams]
                if registration_data['team_name'].lower().strip() in team_names:
                    return {'success': False, 'error': 'A team with this name is already registered. Please choose a different team name'}
                
                # Check for duplicate captain email
                captain_emails = [team.get('captain_email', '').lower() for team in existing_teams if team.get('captain_email')]
                if registration_data['email'].lower() in captain_emails:
                    return {'success': False, 'error': 'This email address is already registered as a team captain'}
                
                # Check capacity with more specific message
                current_count = tournament.get('team_count', 0)
                max_teams = tournament.get('max_teams', 0)
                if current_count >= max_teams:
                    return {'success': False, 'error': f'Tournament is full ({max_teams} teams maximum)'}
                
                # Validate short name uniqueness
                short_names = [team.get('short_name', '').upper() for team in existing_teams]
                proposed_short_name = registration_data.get('short_name', registration_data['team_name'][:4]).upper()
                if proposed_short_name in short_names:
                    # Auto-generate unique short name
                    base_name = registration_data['team_name'][:3].upper()
                    counter = 1
                    while f"{base_name}{counter}" in short_names:
                        counter += 1
                    proposed_short_name = f"{base_name}{counter}"
                
                # Create team with enhanced data
                team_data = {
                    'tournament_id': tournament_id,
                    'name': registration_data['team_name'],
                    'short_name': proposed_short_name,
                    'captain_name': registration_data['captain_name'],
                    'captain_email': registration_data['email'],
                    'captain_phone': registration_data.get('phone', ''),
                    'is_approved': True,  # Auto-approve for public registration
                    'status': 'registered',
                    'registration_date': datetime.now().isoformat()
                }
                result = self.create_team(team_data)
                if result.get('success'):
                    result['message'] = f'Successfully registered! You are team #{current_count + 1} of {max_teams}'
                    if proposed_short_name != registration_data.get('short_name', ''):
                        result['message'] += f' (Team tag: {proposed_short_name})'
                return result
                
        except Exception as e:
            print(f"Error registering for tournament: {e}")
            return {'success': False, 'error': 'Registration failed due to a technical error. Please try again'}

    # Sub-matches operations for multi-match team tournaments
    def create_sub_match(self, sub_match_data: Dict) -> Dict:
        """Create a new sub-match"""
        try:
            sub_match_data['id'] = str(uuid.uuid4())
            sub_match_data['created_at'] = datetime.now().isoformat()
            if 'status' not in sub_match_data:
                sub_match_data['status'] = 'scheduled'
            
            if not self.client:
                return {'success': True, 'sub_match': sub_match_data}
            
            response = self.client.table('sub_matches').insert(sub_match_data).execute()
            return {'success': True, 'sub_match': response.data[0]}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def create_sub_matches_batch(self, sub_matches_data: List[Dict]) -> Dict:
        """Create multiple sub-matches in a batch operation"""
        try:
            # Add IDs and timestamps to all records
            for sub_match_data in sub_matches_data:
                sub_match_data['id'] = str(uuid.uuid4())
                sub_match_data['created_at'] = datetime.now().isoformat()
                if 'status' not in sub_match_data:
                    sub_match_data['status'] = 'scheduled'
            
            if not self.client:
                return {'success': True, 'sub_matches': sub_matches_data, 'count': len(sub_matches_data)}
            
            response = self.client.table('sub_matches').insert(sub_matches_data).execute()
            return {'success': True, 'sub_matches': response.data, 'count': len(response.data)}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_sub_matches_by_parent_match(self, parent_match_id: str) -> List[Dict]:
        """Get all sub-matches for a parent match"""
        try:
            if not self.client:
                # Return mock sub-matches for development
                return [
                    {
                        'id': 'mock-sub-match-1',
                        'parent_match_id': parent_match_id,
                        'team1_player_id': 'mock-player-1',
                        'team2_player_id': 'mock-player-2',
                        'team1_player_goals': 2,
                        'team2_player_goals': 1,
                        'match_order': 1,
                        'status': 'completed',
                        'winner_id': 'mock-player-1'
                    },
                    {
                        'id': 'mock-sub-match-2',
                        'parent_match_id': parent_match_id,
                        'team1_player_id': 'mock-player-3',
                        'team2_player_id': 'mock-player-4',
                        'team1_player_goals': 1,
                        'team2_player_goals': 3,
                        'match_order': 2,
                        'status': 'completed',
                        'winner_id': 'mock-player-4'
                    },
                    {
                        'id': 'mock-sub-match-3',
                        'parent_match_id': parent_match_id,
                        'team1_player_id': 'mock-player-1',
                        'team2_player_id': 'mock-player-4',
                        'team1_player_goals': None,
                        'team2_player_goals': None,
                        'match_order': 3,
                        'status': 'scheduled',
                        'winner_id': None
                    }
                ]
            
            response = self.client.table('sub_matches').select('*').eq('parent_match_id', parent_match_id).order('match_order').execute()
            return response.data
        except Exception as e:
            print(f"Error getting sub-matches: {e}")
            return []
    
    def get_sub_matches_with_player_names(self, parent_match_id: str) -> List[Dict]:
        """Get all sub-matches for a parent match with player names resolved"""
        try:
            # Get the basic sub-matches
            sub_matches = self.get_sub_matches_by_parent_match(parent_match_id)
            
            if not sub_matches:
                return []
            
            # For development mode, we need to manually add player names
            if not self.client:
                # Create a mapping of player IDs to names from our mock data
                player_names = {
                    'mock-player-1': 'Alex Rodriguez',
                    'mock-player-2': 'Maria Santos', 
                    'mock-player-3': 'David Kim',
                    'mock-player-4': 'Sarah Johnson'
                }
                
                # Add player names to each sub-match
                for sub_match in sub_matches:
                    team1_player_id = sub_match.get('team1_player_id')
                    team2_player_id = sub_match.get('team2_player_id')
                    
                    sub_match['team1_player_name'] = player_names.get(team1_player_id, 'Unknown Player')
                    sub_match['team2_player_name'] = player_names.get(team2_player_id, 'Unknown Player')
                
                return sub_matches
            
            # For production mode, we'd need to join with players table
            # This would be a more complex query or multiple queries
            enhanced_sub_matches = []
            for sub_match in sub_matches:
                # Get player names
                team1_player = self.get_player_by_id(sub_match.get('team1_player_id'))
                team2_player = self.get_player_by_id(sub_match.get('team2_player_id'))
                
                sub_match['team1_player_name'] = team1_player.get('name', 'Unknown Player') if team1_player else 'Unknown Player'
                sub_match['team2_player_name'] = team2_player.get('name', 'Unknown Player') if team2_player else 'Unknown Player'
                
                enhanced_sub_matches.append(sub_match)
            
            return enhanced_sub_matches
            
        except Exception as e:
            print(f"Error getting sub-matches with player names: {e}")
            return []
    
    def update_sub_match(self, sub_match_id: str, sub_match_data: Dict) -> Dict:
        """Update sub-match data"""
        try:
            sub_match_data['updated_at'] = datetime.now().isoformat()
            
            # Determine winner based on goals
            if 'team1_player_goals' in sub_match_data and 'team2_player_goals' in sub_match_data:
                goals1 = sub_match_data.get('team1_player_goals', 0)
                goals2 = sub_match_data.get('team2_player_goals', 0)
                
                if goals1 > goals2:
                    sub_match_data['winner_id'] = sub_match_data.get('team1_player_id')
                elif goals2 > goals1:
                    sub_match_data['winner_id'] = sub_match_data.get('team2_player_id')
                else:
                    sub_match_data['winner_id'] = None  # Draw
                
                if goals1 is not None and goals2 is not None:
                    sub_match_data['status'] = 'completed'
                    sub_match_data['completed_at'] = datetime.now().isoformat()
            
            if not self.client:
                return {'success': True, 'sub_match': sub_match_data}
            
            response = self.client.table('sub_matches').update(sub_match_data).eq('id', sub_match_id).execute()
            return {'success': True, 'sub_match': response.data[0] if response.data else sub_match_data}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def delete_sub_matches_by_parent_match(self, parent_match_id: str) -> Dict:
        """Delete all sub-matches for a parent match"""
        try:
            if not self.client:
                return {'success': True, 'message': 'Sub-matches deleted (offline mode)'}
            
            response = self.client.table('sub_matches').delete().eq('parent_match_id', parent_match_id).execute()
            return {'success': True, 'deleted_count': len(response.data) if response.data else 0}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def delete_match_participants_by_match(self, match_id: str) -> Dict:
        """Delete all match participants for a match"""
        try:
            if not self.client:
                return {'success': True, 'message': 'Match participants deleted (offline mode)'}
            
            response = self.client.table('match_participants').delete().eq('match_id', match_id).execute()
            return {'success': True, 'deleted_count': len(response.data) if response.data else 0}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def calculate_match_summary_from_sub_matches(self, parent_match_id: str) -> Dict:
        """Calculate team scores from sub-matches"""
        try:
            sub_matches = self.get_sub_matches_by_parent_match(parent_match_id)
            
            team1_wins = 0
            team2_wins = 0
            draws = 0
            team1_total_goals = 0
            team2_total_goals = 0
            
            for sub_match in sub_matches:
                if sub_match.get('status') == 'completed':
                    goals1 = sub_match.get('team1_player_goals', 0)
                    goals2 = sub_match.get('team2_player_goals', 0)
                    
                    team1_total_goals += goals1
                    team2_total_goals += goals2
                    
                    if goals1 > goals2:
                        team1_wins += 1
                    elif goals2 > goals1:
                        team2_wins += 1
                    else:
                        draws += 1
            
            return {
                'team1_wins': team1_wins,
                'team2_wins': team2_wins,
                'draws': draws,
                'team1_total_goals': team1_total_goals,
                'team2_total_goals': team2_total_goals,
                'completed_sub_matches': team1_wins + team2_wins + draws,
                'total_sub_matches': len(sub_matches)
            }
        except Exception as e:
            print(f"Error calculating match summary: {e}")
            return {
                'team1_wins': 0,
                'team2_wins': 0,
                'draws': 0,
                'team1_total_goals': 0,
                'team2_total_goals': 0,
                'completed_sub_matches': 0,
                'total_sub_matches': 0
            }
    
    def create_match_participant(self, participant_data: Dict) -> Dict:
        """Create a match participant record"""
        try:
            participant_data.setdefault('id', str(uuid4()))
            participant_data.setdefault('created_at', datetime.now().isoformat())
            participant_data.setdefault('updated_at', datetime.now().isoformat())
            
            if not self.client:
                return {'success': True, 'participant': participant_data}
            
            response = self.client.table('match_participants').insert(participant_data).execute()
            return {'success': True, 'participant': response.data[0] if response.data else participant_data}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_match_participants(self, match_id: str) -> List[Dict]:
        """Get all participants for a match"""
        try:
            if not self.client:
                return []
            
            response = self.client.table('match_participants').select('*').eq('match_id', match_id).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error getting match participants: {e}")
            return []
    
    def get_match_participants_by_team(self, match_id: str, team_id: str) -> List[Dict]:
        """Get participants for a specific team in a match"""
        try:
            if not self.client:
                return []
            
            response = self.client.table('match_participants').select('*').eq('match_id', match_id).eq('team_id', team_id).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error getting team participants: {e}")
            return []
    
    def search_participants_by_email(self, email: str, tournament_name: str = None) -> List[Dict]:
        """Search for solo participants by email address"""
        try:
            if not self.client:
                # Return mock data for development
                mock_participants = [
                    {
                        'id': 'mock-participant-1',
                        'tournament_id': 'mock-tournament-1',
                        'name': 'John Doe',
                        'email': email,
                        'phone': '+1234567890',
                        'skill_level': 'intermediate',
                        'created_at': datetime.now().isoformat()
                    }
                ] if email else []
                
                # Filter by tournament name if provided
                if tournament_name and mock_participants:
                    # In mock mode, just return empty if tournament name doesn't match our mock tournament
                    if 'championship' not in tournament_name.lower():
                        return []
                
                return mock_participants
            
            # Build query
            query = self.client.table('participants').select('*').eq('email', email)
            
            # Filter by tournament name if provided
            if tournament_name:
                # Get tournaments matching the name first
                tournaments_response = self.client.table('tournaments').select('id').ilike('name', f'%{tournament_name}%').execute()
                tournament_ids = [t['id'] for t in tournaments_response.data] if tournaments_response.data else []
                
                if tournament_ids:
                    query = query.in_('tournament_id', tournament_ids)
                else:
                    # No tournaments match the name, return empty
                    return []
            
            response = query.execute()
            return response.data if response.data else []
            
        except Exception as e:
            print(f"Error searching participants by email: {e}")
            return []
    
    def search_teams_by_email(self, email: str, tournament_name: str = None) -> List[Dict]:
        """Search for teams by contact email address"""
        try:
            if not self.client:
                # Return mock data for development
                mock_teams = [
                    {
                        'id': 'mock-team-1',
                        'tournament_id': 'mock-tournament-2',
                        'name': 'Dream Team',
                        'short_name': 'DT',
                        'contact_email': email,
                        'contact_phone': '+1234567890',
                        'created_at': datetime.now().isoformat()
                    }
                ] if email else []
                
                # Filter by tournament name if provided
                if tournament_name and mock_teams:
                    # In mock mode, just return empty if tournament name doesn't match our mock tournament
                    if 'league' not in tournament_name.lower():
                        return []
                
                return mock_teams
            
            # Build query - search both email and contact_email fields
            base_query = self.client.table('teams').select('*')
            
            # Create OR condition for email fields
            query1 = base_query.eq('email', email)
            query2 = base_query.eq('contact_email', email)
            
            # Execute both queries and combine results
            response1 = query1.execute()
            response2 = query2.execute()
            
            teams = []
            if response1.data:
                teams.extend(response1.data)
            if response2.data:
                # Avoid duplicates by checking IDs
                existing_ids = {team['id'] for team in teams}
                teams.extend([team for team in response2.data if team['id'] not in existing_ids])
            
            # Filter by tournament name if provided
            if tournament_name and teams:
                tournaments_response = self.client.table('tournaments').select('id').ilike('name', f'%{tournament_name}%').execute()
                tournament_ids = {t['id'] for t in tournaments_response.data} if tournaments_response.data else set()
                
                if tournament_ids:
                    teams = [team for team in teams if team['tournament_id'] in tournament_ids]
                else:
                    teams = []
            
            return teams
            
        except Exception as e:
            print(f"Error searching teams by email: {e}")
            return []

# Global database manager instance
db = DatabaseManager()
