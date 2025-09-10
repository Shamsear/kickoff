from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_socketio import emit
from routes.auth import login_required, get_current_user
from database import db
from datetime import datetime

match_bp = Blueprint('match', __name__)

@match_bp.route('/<match_id>')
def view(match_id):
    """View match details"""
    match = get_match_with_details(match_id)
    if not match:
        flash('Match not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    tournament = db.get_tournament_by_id(match['tournament_id'])
    is_organizer = session.get('user_id') == tournament.get('organizer_id') if tournament else False
    
    return render_template('match/view.html', 
                         match=match,
                         tournament=tournament,
                         is_organizer=is_organizer)

@match_bp.route('/<match_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(match_id):
    """Edit match details"""
    match = get_match_with_details(match_id)
    if not match:
        flash('Match not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    tournament = db.get_tournament_by_id(match['tournament_id'])
    if not tournament or session.get('user_id') != tournament.get('organizer_id'):
        flash('Permission denied', 'error')
        return redirect(url_for('match.view', match_id=match_id))
    
    if request.method == 'POST':
        update_data = {
            'scheduled_date': request.form.get('scheduled_date'),
            'venue': request.form.get('venue', '').strip(),
            'referee': request.form.get('referee', '').strip(),
            'notes': request.form.get('notes', '').strip()
        }
        
        result = db.update_match_score(match_id, update_data)
        if result['success']:
            flash('Match updated successfully!', 'success')
            return redirect(url_for('match.view', match_id=match_id))
        else:
            flash('Failed to update match', 'error')
    
    return render_template('match/edit.html', match=match, tournament=tournament)

@match_bp.route('/<match_id>/score', methods=['POST'])
@login_required
def update_score(match_id):
    """Update match score"""
    match = get_match_with_details(match_id)
    if not match:
        return jsonify({'success': False, 'error': 'Match not found'})
    
    tournament = db.get_tournament_by_id(match['tournament_id'])
    if not tournament or session.get('user_id') != tournament.get('organizer_id'):
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    try:
        team1_score = int(request.form.get('team1_score', 0))
        team2_score = int(request.form.get('team2_score', 0))
        team1_penalties = int(request.form.get('team1_penalties', 0))
        team2_penalties = int(request.form.get('team2_penalties', 0))
        
        # Determine winner
        winner_id = None
        if team1_score > team2_score:
            winner_id = match['team1_id']
        elif team2_score > team1_score:
            winner_id = match['team2_id']
        elif team1_penalties > team2_penalties:
            winner_id = match['team1_id']
        elif team2_penalties > team1_penalties:
            winner_id = match['team2_id']
        
        score_data = {
            'team1_score': team1_score,
            'team2_score': team2_score,
            'team1_penalties': team1_penalties,
            'team2_penalties': team2_penalties,
            'winner_id': winner_id,
            'status': 'completed'
        }
        
        result = db.update_match_score(match_id, score_data)
        if result['success']:
            # Emit real-time update
            from app import create_app
            app, socketio = create_app()
            with app.app_context():
                socketio.emit('match_score_update', {
                    'match_id': match_id,
                    'tournament_id': match['tournament_id'],
                    'team1_score': team1_score,
                    'team2_score': team2_score,
                    'status': 'completed'
                }, room=f"tournament_{match['tournament_id']}")
            
            return jsonify({'success': True, 'match': result['match']})
        else:
            return jsonify({'success': False, 'error': 'Failed to update score'})
            
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid score values'})

@match_bp.route('/<match_id>/live', methods=['GET', 'POST'])
@login_required
def live_scoring(match_id):
    """Live match scoring interface"""
    match = get_match_with_details(match_id)
    if not match:
        flash('Match not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    tournament = db.get_tournament_by_id(match['tournament_id'])
    if not tournament or session.get('user_id') != tournament.get('organizer_id'):
        flash('Permission denied', 'error')
        return redirect(url_for('match.view', match_id=match_id))
    
    # Get match events (goals, cards, etc.)
    match_events = get_match_events(match_id)
    
    return render_template('match/live_scoring.html', 
                         match=match,
                         tournament=tournament,
                         match_events=match_events)

@match_bp.route('/<match_id>/event', methods=['POST'])
@login_required
def add_event(match_id):
    """Add match event (goal, card, substitution)"""
    match = get_match_with_details(match_id)
    if not match:
        return jsonify({'success': False, 'error': 'Match not found'})
    
    tournament = db.get_tournament_by_id(match['tournament_id'])
    if not tournament or session.get('user_id') != tournament.get('organizer_id'):
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    event_data = {
        'match_id': match_id,
        'player_id': request.form.get('player_id'),
        'event_type': request.form.get('event_type'),
        'event_minute': int(request.form.get('event_minute', 0)),
        'description': request.form.get('description', '').strip()
    }
    
    # Add event to database (mock for now)
    event_data['id'] = f"event_{datetime.now().timestamp()}"
    event_data['created_at'] = datetime.now().isoformat()
    
    # Emit real-time event update
    from app import create_app
    app, socketio = create_app()
    with app.app_context():
        socketio.emit('match_event', {
            'match_id': match_id,
            'tournament_id': match['tournament_id'],
            'event': event_data
        }, room=f"tournament_{match['tournament_id']}")
    
    return jsonify({'success': True, 'event': event_data})

@match_bp.route('/<match_id>/start', methods=['POST'])
@login_required
def start_match(match_id):
    """Start a match"""
    match = get_match_with_details(match_id)
    if not match:
        return jsonify({'success': False, 'error': 'Match not found'})
    
    tournament = db.get_tournament_by_id(match['tournament_id'])
    if not tournament or session.get('user_id') != tournament.get('organizer_id'):
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    update_data = {
        'status': 'in_progress',
        'updated_at': datetime.now().isoformat()
    }
    
    result = db.update_match_score(match_id, update_data)
    if result['success']:
        # Emit real-time update
        from app import create_app
        app, socketio = create_app()
        with app.app_context():
            socketio.emit('match_started', {
                'match_id': match_id,
                'tournament_id': match['tournament_id']
            }, room=f"tournament_{match['tournament_id']}")
        
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Failed to start match'})

@match_bp.route('/<match_id>/statistics')
def statistics(match_id):
    """View detailed match statistics"""
    match = get_match_with_details(match_id)
    if not match:
        flash('Match not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get detailed statistics
    stats = calculate_match_statistics(match)
    match_events = get_match_events(match_id)
    
    return render_template('match/statistics.html', 
                         match=match,
                         stats=stats,
                         match_events=match_events)

@match_bp.route('/<match_id>/report')
@login_required
def generate_report(match_id):
    """Generate printable match report"""
    match = get_match_with_details(match_id)
    if not match:
        flash('Match not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    tournament = db.get_tournament_by_id(match['tournament_id'])
    match_events = get_match_events(match_id)
    stats = calculate_match_statistics(match)
    
    return render_template('match/report.html', 
                         match=match,
                         tournament=tournament,
                         match_events=match_events,
                         stats=stats,
                         print_mode=True)

# Helper functions
def get_match_with_details(match_id):
    """Get match with team details"""
    # In a real implementation, this would join with teams table
    match = db.get_matches_by_tournament("dummy")[0] if True else None  # Mock for now
    
    # Mock match data
    return {
        'id': match_id,
        'tournament_id': 'tournament_123',
        'round_name': 'Semi-Final',
        'match_number': 1,
        'team1_id': 'team_1',
        'team2_id': 'team_2',
        'team1_name': 'Team Alpha',
        'team2_name': 'Team Beta',
        'team1_score': 2,
        'team2_score': 1,
        'scheduled_date': datetime.now().isoformat(),
        'venue': 'Stadium A',
        'status': 'completed',
        'referee': 'John Smith',
        'notes': 'Great match!',
        'created_at': datetime.now().isoformat()
    }

def get_match_events(match_id):
    """Get match events (goals, cards, etc.)"""
    # Mock events data
    return [
        {
            'id': 'event_1',
            'event_type': 'goal',
            'event_minute': 23,
            'player_name': 'Player A',
            'team_name': 'Team Alpha',
            'description': 'Great shot from outside the box'
        },
        {
            'id': 'event_2',
            'event_type': 'yellow_card',
            'event_minute': 45,
            'player_name': 'Player B',
            'team_name': 'Team Beta',
            'description': 'Unsporting behavior'
        }
    ]

def calculate_match_statistics(match):
    """Calculate detailed match statistics"""
    return {
        'possession': {'team1': 55, 'team2': 45},
        'shots_on_target': {'team1': 8, 'team2': 4},
        'total_shots': {'team1': 15, 'team2': 9},
        'corners': {'team1': 7, 'team2': 3},
        'fouls': {'team1': 12, 'team2': 18},
        'yellow_cards': {'team1': 2, 'team2': 3},
        'red_cards': {'team1': 0, 'team2': 1}
    }
