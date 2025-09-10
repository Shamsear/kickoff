from flask_socketio import emit, join_room, leave_room, disconnect
from flask import session, request
from database import db
import json

def register_events(socketio):
    """Register all WebSocket events"""
    
    @socketio.on('connect')
    def on_connect(auth):
        """Handle client connection"""
        print(f'Client connected: {request.sid}')
        
        # Check if user is authenticated
        if 'user_id' not in session:
            print('Unauthenticated connection rejected')
            disconnect()
            return False
        
        # Send welcome message
        emit('connected', {'message': 'Connected to TournamentPro real-time updates'})
        return True
    
    @socketio.on('disconnect')
    def on_disconnect():
        """Handle client disconnection"""
        print(f'Client disconnected: {request.sid}')
    
    @socketio.on('join_tournament')
    def on_join_tournament(data):
        """Join tournament room for real-time updates"""
        if 'user_id' not in session:
            emit('error', {'message': 'Authentication required'})
            return
        
        tournament_id = data.get('tournament_id')
        if not tournament_id:
            emit('error', {'message': 'Tournament ID required'})
            return
        
        # Verify tournament exists
        tournament = db.get_tournament_by_id(tournament_id)
        if not tournament:
            emit('error', {'message': 'Tournament not found'})
            return
        
        # Join tournament room
        room = f'tournament_{tournament_id}'
        join_room(room)
        
        print(f'User {session["user_id"]} joined tournament room: {room}')
        emit('joined_tournament', {
            'tournament_id': tournament_id,
            'tournament_name': tournament.get('name', 'Unknown Tournament')
        })
        
        # Notify others in the room
        emit('user_joined', {
            'user_name': session.get('user_name', 'Unknown User'),
            'user_id': session['user_id']
        }, room=room, include_self=False)
    
    @socketio.on('leave_tournament')
    def on_leave_tournament(data):
        """Leave tournament room"""
        if 'user_id' not in session:
            return
        
        tournament_id = data.get('tournament_id')
        if not tournament_id:
            return
        
        room = f'tournament_{tournament_id}'
        leave_room(room)
        
        print(f'User {session["user_id"]} left tournament room: {room}')
        emit('left_tournament', {'tournament_id': tournament_id})
        
        # Notify others in the room
        emit('user_left', {
            'user_name': session.get('user_name', 'Unknown User'),
            'user_id': session['user_id']
        }, room=room)
    
    @socketio.on('update_match_score')
    def on_update_match_score(data):
        """Handle real-time match score updates"""
        if 'user_id' not in session:
            emit('error', {'message': 'Authentication required'})
            return
        
        match_id = data.get('match_id')
        tournament_id = data.get('tournament_id')
        team1_score = data.get('team1_score', 0)
        team2_score = data.get('team2_score', 0)
        
        if not match_id or not tournament_id:
            emit('error', {'message': 'Match ID and Tournament ID required'})
            return
        
        # Verify user has permission to update scores
        tournament = db.get_tournament_by_id(tournament_id)
        if not tournament or session['user_id'] != tournament.get('organizer_id'):
            emit('error', {'message': 'Permission denied'})
            return
        
        # Update match score in database
        score_data = {
            'team1_score': team1_score,
            'team2_score': team2_score,
            'status': data.get('status', 'in_progress')
        }
        
        result = db.update_match_score(match_id, score_data)
        if result['success']:
            # Broadcast update to all users in tournament room
            room = f'tournament_{tournament_id}'
            emit('match_score_updated', {
                'match_id': match_id,
                'team1_score': team1_score,
                'team2_score': team2_score,
                'status': score_data['status'],
                'updated_by': session.get('user_name', 'Unknown User')
            }, room=room)
            
            # Update tournament standings if match is completed
            if score_data['status'] == 'completed':
                emit('standings_updated', {
                    'tournament_id': tournament_id,
                    'message': 'Tournament standings have been updated'
                }, room=room)
        else:
            emit('error', {'message': 'Failed to update match score'})
    
    @socketio.on('match_event')
    def on_match_event(data):
        """Handle real-time match events (goals, cards, etc.)"""
        if 'user_id' not in session:
            emit('error', {'message': 'Authentication required'})
            return
        
        match_id = data.get('match_id')
        tournament_id = data.get('tournament_id')
        event_type = data.get('event_type')
        event_minute = data.get('event_minute', 0)
        player_name = data.get('player_name', '')
        description = data.get('description', '')
        
        if not match_id or not tournament_id or not event_type:
            emit('error', {'message': 'Match ID, Tournament ID, and event type required'})
            return
        
        # Verify user has permission
        tournament = db.get_tournament_by_id(tournament_id)
        if not tournament or session['user_id'] != tournament.get('organizer_id'):
            emit('error', {'message': 'Permission denied'})
            return
        
        # Create match event
        event_data = {
            'match_id': match_id,
            'event_type': event_type,
            'event_minute': event_minute,
            'player_name': player_name,
            'description': description,
            'created_at': data.get('created_at')
        }
        
        # Broadcast event to all users in tournament room
        room = f'tournament_{tournament_id}'
        emit('match_event_added', event_data, room=room)
        
        print(f'Match event added: {event_type} at minute {event_minute}')
    
    @socketio.on('team_registered')
    def on_team_registered(data):
        """Handle new team registration notifications"""
        if 'user_id' not in session:
            return
        
        tournament_id = data.get('tournament_id')
        team_name = data.get('team_name')
        
        if not tournament_id or not team_name:
            return
        
        # Broadcast to tournament room
        room = f'tournament_{tournament_id}'
        emit('team_registration_notification', {
            'tournament_id': tournament_id,
            'team_name': team_name,
            'message': f'New team "{team_name}" has registered for the tournament!'
        }, room=room)
        
        print(f'Team registration notification: {team_name} in tournament {tournament_id}')
    
    @socketio.on('tournament_news')
    def on_tournament_news(data):
        """Handle tournament news updates"""
        if 'user_id' not in session:
            emit('error', {'message': 'Authentication required'})
            return
        
        tournament_id = data.get('tournament_id')
        title = data.get('title')
        content = data.get('content')
        
        if not tournament_id or not title or not content:
            emit('error', {'message': 'Tournament ID, title, and content required'})
            return
        
        # Verify user has permission
        tournament = db.get_tournament_by_id(tournament_id)
        if not tournament or session['user_id'] != tournament.get('organizer_id'):
            emit('error', {'message': 'Permission denied'})
            return
        
        # Broadcast news to tournament room
        room = f'tournament_{tournament_id}'
        emit('tournament_news_published', {
            'tournament_id': tournament_id,
            'title': title,
            'content': content,
            'author': session.get('user_name', 'Tournament Organizer'),
            'published_at': data.get('published_at')
        }, room=room)
        
        print(f'Tournament news published: {title}')
    
    @socketio.on('poll_vote')
    def on_poll_vote(data):
        """Handle poll voting"""
        if 'user_id' not in session:
            emit('error', {'message': 'Authentication required'})
            return
        
        poll_id = data.get('poll_id')
        option_id = data.get('option_id')
        tournament_id = data.get('tournament_id')
        
        if not poll_id or not option_id or not tournament_id:
            emit('error', {'message': 'Poll ID, option ID, and tournament ID required'})
            return
        
        # Process vote (mock for now)
        vote_data = {
            'poll_id': poll_id,
            'option_id': option_id,
            'user_id': session['user_id']
        }
        
        # Broadcast updated poll results to tournament room
        room = f'tournament_{tournament_id}'
        emit('poll_vote_updated', {
            'poll_id': poll_id,
            'option_id': option_id,
            'vote_count': data.get('new_vote_count', 1),
            'voter_name': session.get('user_name', 'Anonymous')
        }, room=room)
        
        print(f'Poll vote cast: {poll_id} - option {option_id}')
    
    @socketio.on('typing_start')
    def on_typing_start(data):
        """Handle typing indicator start"""
        if 'user_id' not in session:
            return
        
        tournament_id = data.get('tournament_id')
        if not tournament_id:
            return
        
        room = f'tournament_{tournament_id}'
        emit('user_typing', {
            'user_name': session.get('user_name', 'Someone'),
            'user_id': session['user_id']
        }, room=room, include_self=False)
    
    @socketio.on('typing_stop')
    def on_typing_stop(data):
        """Handle typing indicator stop"""
        if 'user_id' not in session:
            return
        
        tournament_id = data.get('tournament_id')
        if not tournament_id:
            return
        
        room = f'tournament_{tournament_id}'
        emit('user_stopped_typing', {
            'user_id': session['user_id']
        }, room=room, include_self=False)
    
    @socketio.on('request_live_data')
    def on_request_live_data(data):
        """Handle requests for current live data"""
        if 'user_id' not in session:
            emit('error', {'message': 'Authentication required'})
            return
        
        tournament_id = data.get('tournament_id')
        data_type = data.get('data_type', 'all')  # all, standings, matches, scores
        
        if not tournament_id:
            emit('error', {'message': 'Tournament ID required'})
            return
        
        # Get current tournament data
        tournament = db.get_tournament_by_id(tournament_id)
        if not tournament:
            emit('error', {'message': 'Tournament not found'})
            return
        
        live_data = {'tournament_id': tournament_id}
        
        if data_type in ['all', 'matches']:
            matches = db.get_matches_by_tournament(tournament_id)
            live_data['matches'] = matches
        
        if data_type in ['all', 'teams']:
            teams = db.get_teams_by_tournament(tournament_id)
            live_data['teams'] = teams
        
        if data_type in ['all', 'standings']:
            # Calculate current standings
            from routes.tournament import calculate_standings
            teams = db.get_teams_by_tournament(tournament_id)
            matches = db.get_matches_by_tournament(tournament_id)
            standings = calculate_standings(teams, matches)
            live_data['standings'] = standings
        
        emit('live_data', live_data)
        print(f'Live data sent for tournament {tournament_id}: {data_type}')
