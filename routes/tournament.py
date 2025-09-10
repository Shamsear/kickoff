from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from routes.auth import login_required, get_current_user
from database import db
from datetime import datetime, timedelta
import uuid
import random
from tournament_generator import TournamentGenerator

tournament_bp = Blueprint('tournament', __name__)

def generate_solo_matches(tournament, participants):
    """Generate matches for solo tournament based on format"""
    matches = []
    format_type = tournament.get('format', 'single_elimination')
    
    if format_type in ['single_elimination', 'double_elimination']:
        # For elimination formats, generate bracket-style matches
        # Start with first round pairings
        shuffled_participants = participants.copy()
        random.shuffle(shuffled_participants)
        
        round_number = 1
        current_participants = shuffled_participants
        
        while len(current_participants) > 1:
            round_matches = []
            
            # Pair up participants for this round
            for i in range(0, len(current_participants) - 1, 2):
                participant1 = current_participants[i]
                participant2 = current_participants[i + 1]
                
                match_data = {
                    'tournament_id': tournament['id'],
                    'participant1_id': participant1['id'],
                    'participant2_id': participant2['id'],
                    'round_name': f'Round {round_number}'
                }
                matches.append(match_data)
                round_matches.append(match_data)
            
            # For next round, we'll have half the participants
            # This is simplified - in real implementation you'd track winners
            current_participants = current_participants[:len(current_participants)//2]
            round_number += 1
    
    elif format_type == 'round_robin':
        # Generate all possible pairings for round robin
        for i in range(len(participants)):
            for j in range(i + 1, len(participants)):
                match_data = {
                    'tournament_id': tournament['id'],
                    'participant1_id': participants[i]['id'],
                    'participant2_id': participants[j]['id'],
                    'round_name': 'Round Robin'
                }
                matches.append(match_data)
    
    elif format_type == 'league':
        # Similar to round robin, but may have multiple rounds
        # For now, treat same as round robin
        for i in range(len(participants)):
            for j in range(i + 1, len(participants)):
                match_data = {
                    'tournament_id': tournament['id'],
                    'participant1_id': participants[i]['id'],
                    'participant2_id': participants[j]['id'],
                    'round_name': 'League Play'
                }
                matches.append(match_data)
    
    return matches

@tournament_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new tournament"""
    if request.method == 'POST':
        try:
            # Get form data with proper date handling
            tournament_type = request.form.get('tournament_type')  # 'solo' or 'team'
            
            tournament_data = {
                'name': request.form.get('name', '').strip(),
                'description': request.form.get('description', '').strip(),
                'sport': request.form.get('sport'),
                'format': request.form.get('format'),
                'type': tournament_type,
                'start_date': request.form.get('start_date') or None,
                'end_date': request.form.get('end_date') or None,
                'registration_deadline': request.form.get('registration_deadline') or None,
                'entry_fee': float(request.form.get('entry_fee', 0)),
                'prize_pool': float(request.form.get('prize_pool', 0)),
                'location': request.form.get('location', '').strip(),
                'rules': request.form.get('rules', '').strip(),
                'is_public': request.form.get('is_public') == 'on',
                'organizer_id': session['user_id'],
                'status': 'draft'
            }
            
            # Add scoring system for team tournaments
            if tournament_type == 'team':
                scoring_system = request.form.get('scoring_system', 'win_based')
                tournament_data['scoring_system'] = scoring_system
            
            # Handle different limits for Solo vs Team tournaments
            if tournament_type == 'solo':
                tournament_data['max_participants'] = int(request.form.get('max_participants', 32))
                tournament_data['max_teams'] = None
                tournament_data['max_players_per_team'] = None
            elif tournament_type == 'team':
                tournament_data['max_teams'] = int(request.form.get('max_teams', 16))
                tournament_data['max_players_per_team'] = int(request.form.get('max_players_per_team', 5))
                tournament_data['max_participants'] = None
            else:
                # Default to team for backward compatibility
                tournament_data['max_teams'] = int(request.form.get('max_teams', 16))
                tournament_data['max_players_per_team'] = int(request.form.get('max_players_per_team', 5))
                tournament_data['max_participants'] = None
            
            # Validate required fields
            errors = []
            if not tournament_data['name']:
                errors.append("Tournament name is required")
            if not tournament_data['sport']:
                errors.append("Game selection is required")
            if not tournament_data['format']:
                errors.append("Tournament format is required")
            if not tournament_type:
                errors.append("Tournament type (Solo or Team) is required")
            elif tournament_type not in ['solo', 'team']:
                errors.append("Invalid tournament type selected")
            
            # Validate dates
            if tournament_data['start_date']:
                try:
                    start_date = datetime.strptime(tournament_data['start_date'], '%Y-%m-%d').date()
                    if start_date < datetime.now().date():
                        errors.append("Start date cannot be in the past")
                except ValueError:
                    errors.append("Invalid start date format")
            
            if tournament_data['end_date'] and tournament_data['start_date']:
                try:
                    end_date = datetime.strptime(tournament_data['end_date'], '%Y-%m-%d').date()
                    start_date = datetime.strptime(tournament_data['start_date'], '%Y-%m-%d').date()
                    if end_date < start_date:
                        errors.append("End date cannot be before start date")
                except ValueError:
                    errors.append("Invalid date format")
            
            if errors:
                for error in errors:
                    flash(error, 'error')
                return render_template('tournament/create.html')
            
            # Create tournament
            result = db.create_tournament(tournament_data)
            
            if result['success']:
                flash('Tournament created successfully!', 'success')
                return redirect(url_for('tournament.view', tournament_id=result['tournament']['id']))
            else:
                error_msg = result.get('error', 'Unknown error')
                flash(f'Failed to create tournament: {error_msg}', 'error')
                
        except Exception as e:
            flash(f'Error creating tournament: {str(e)}', 'error')
    
    return render_template('tournament/create.html')

@tournament_bp.route('/<tournament_id>')
def view(tournament_id):
    """View tournament details"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        flash('Tournament not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get tournament data based on type
    teams = []
    participants = []
    
    if tournament.get('type') == 'solo':
        participants = db.get_participants_by_tournament(tournament_id)
        matches = db.get_solo_matches_by_tournament(tournament_id)
    else:
        teams = db.get_teams_by_tournament(tournament_id)
        matches = db.get_matches_by_tournament(tournament_id)
    
    # Check if user is organizer
    is_organizer = session.get('user_id') == tournament.get('organizer_id')
    
    # Calculate tournament stats based on type
    if tournament.get('type') == 'solo':
        stats = {
            'total_participants': len(participants),
            'total_matches': len(matches),
            'completed_matches': len([m for m in matches if m.get('status') == 'completed']),
            'upcoming_matches': len([m for m in matches if m.get('status') == 'scheduled'])
        }
    else:
        stats = {
            'total_teams': len(teams),
            'total_matches': len(matches),
            'completed_matches': len([m for m in matches if m.get('status') == 'completed']),
            'upcoming_matches': len([m for m in matches if m.get('status') == 'scheduled'])
        }
    
    return render_template('tournament/view.html', 
                         tournament=tournament,
                         teams=teams,
                         participants=participants,
                         matches=matches,
                         stats=stats,
                         is_organizer=is_organizer)

@tournament_bp.route('/<tournament_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(tournament_id):
    """Edit tournament"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        flash('Tournament not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Check if user is organizer (with development mode support)
    current_user_id = session.get('user_id')
    tournament_organizer_id = tournament.get('organizer_id')
    is_development = not db.client
    is_mock_tournament = tournament_organizer_id == 'mock-organizer-123'
    
    if not is_development and not is_mock_tournament and current_user_id != tournament_organizer_id:
        flash('You do not have permission to edit this tournament', 'error')
        return redirect(url_for('tournament.view', tournament_id=tournament_id))
    
    if request.method == 'POST':
        try:
            # Get tournament type to handle different field sets
            tournament_type = request.form.get('tournament_type')
            
            # Get and validate status
            status = request.form.get('status')
            valid_statuses = ['draft', 'registration_open', 'upcoming', 'in_progress', 'completed']
            if status not in valid_statuses:
                status = tournament.get('status', 'draft')
            
            # Handle registration deadline - only set if registration is open
            registration_deadline = None
            if status == 'registration_open':
                registration_deadline = request.form.get('registration_deadline') or None
            
            # Update tournament data with all fields
            update_data = {
                'name': request.form.get('name', '').strip(),
                'description': request.form.get('description', '').strip(),
                'location': request.form.get('location', '').strip(),
                'rules': request.form.get('rules', '').strip(),
                'sport': request.form.get('sport'),
                'format': request.form.get('format'),
                'type': tournament_type,
                'status': status,
                'start_date': request.form.get('start_date') or None,
                'end_date': request.form.get('end_date') or None,
                'registration_deadline': registration_deadline,
                'entry_fee': float(request.form.get('entry_fee', 0)),
                'prize_pool': float(request.form.get('prize_pool', 0)),
                'is_public': request.form.get('is_public') == 'on'
            }
            
            # Add scoring system for team tournaments
            if tournament_type == 'team':
                scoring_system = request.form.get('scoring_system', 'win_based')
                update_data['scoring_system'] = scoring_system
            
            # Handle capacity settings based on tournament type
            if tournament_type == 'solo':
                update_data['max_participants'] = int(request.form.get('max_participants', 32))
                update_data['max_teams'] = None
                update_data['max_players_per_team'] = None
            elif tournament_type == 'team':
                update_data['max_teams'] = int(request.form.get('max_teams', 16))
                update_data['max_players_per_team'] = int(request.form.get('max_players_per_team', 5))
                update_data['max_participants'] = None
            
            # Validate required fields
            errors = []
            if not update_data['name']:
                errors.append("Tournament name is required")
            if not update_data['sport']:
                errors.append("Game selection is required")
            if not update_data['format']:
                errors.append("Tournament format is required")
            if not tournament_type:
                errors.append("Tournament type is required")
            elif tournament_type not in ['solo', 'team']:
                errors.append("Invalid tournament type selected")
            
            # Validate dates
            if update_data['start_date']:
                try:
                    start_date = datetime.strptime(update_data['start_date'], '%Y-%m-%d').date()
                    if start_date < datetime.now().date():
                        errors.append("Start date cannot be in the past")
                except ValueError:
                    errors.append("Invalid start date format")
            
            if update_data['end_date'] and update_data['start_date']:
                try:
                    end_date = datetime.strptime(update_data['end_date'], '%Y-%m-%d').date()
                    start_date = datetime.strptime(update_data['start_date'], '%Y-%m-%d').date()
                    if end_date < start_date:
                        errors.append("End date cannot be before start date")
                except ValueError:
                    errors.append("Invalid date format")
            
            if errors:
                for error in errors:
                    flash(error, 'error')
                return render_template('tournament/edit.html', tournament=tournament)
                
        except ValueError as e:
            flash(f'Invalid input: {str(e)}', 'error')
            return render_template('tournament/edit.html', tournament=tournament)
        except Exception as e:
            flash(f'Error processing form: {str(e)}', 'error')
            return render_template('tournament/edit.html', tournament=tournament)
        
        result = db.update_tournament(tournament_id, update_data)
        if result['success']:
            flash('Tournament updated successfully!', 'success')
            return redirect(url_for('tournament.view', tournament_id=tournament_id))
        else:
            flash('Failed to update tournament', 'error')
    
    return render_template('tournament/edit.html', tournament=tournament)

@tournament_bp.route('/<tournament_id>/teams')
@login_required
def teams(tournament_id):
    """Manage tournament teams"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        flash('Tournament not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    teams = db.get_teams_by_tournament(tournament_id)
    is_organizer = session.get('user_id') == tournament.get('organizer_id')
    
    return render_template('tournament/teams.html', 
                         tournament=tournament,
                         teams=teams,
                         is_organizer=is_organizer)

@tournament_bp.route('/<tournament_id>/team/add', methods=['GET', 'POST'])
@login_required
def add_team_form(tournament_id):
    """Add team form page and handler"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        flash('Tournament not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Check if user is organizer
    is_organizer = session.get('user_id') == tournament.get('organizer_id')
    if not is_organizer:
        flash('You do not have permission to add teams to this tournament', 'error')
        return redirect(url_for('tournament.teams', tournament_id=tournament_id))
    
    if request.method == 'POST':
        try:
            team_data = {
                'tournament_id': tournament_id,
                'name': request.form.get('name', '').strip(),
                'short_name': request.form.get('short_name', '').strip(),
                'captain_name': request.form.get('captain_name', '').strip(),
                'captain_email': request.form.get('captain_email', '').strip(),
                'captain_phone': request.form.get('captain_phone', '').strip(),
                'description': request.form.get('description', '').strip(),
                'founded_year': int(request.form.get('founded_year', 0)) if request.form.get('founded_year') else None,
                'captain_position': request.form.get('captain_position', '').strip(),
                'preferred_formation': request.form.get('preferred_formation', '').strip(),
                'team_colors': request.form.get('team_colors', '').strip(),
                'notes': request.form.get('notes', '').strip(),
                'is_approved': request.form.get('is_approved') == 'on' if is_organizer else True
            }
            
            # Validate required fields
            if not team_data['name']:
                flash('Team name is required', 'error')
                teams = db.get_teams_by_tournament(tournament_id)
                teams_count = len(teams)
                return render_template('tournament/team_form.html', tournament=tournament, is_organizer=is_organizer, teams_count=teams_count)
            
            result = db.create_team(team_data)
            if result['success']:
                flash('Team added successfully!', 'success')
                return redirect(url_for('tournament.teams', tournament_id=tournament_id))
            else:
                flash('Failed to add team: ' + result.get('error', 'Unknown error'), 'error')
                
        except Exception as e:
            flash(f'Error adding team: {str(e)}', 'error')
    
    # Get teams count for the stats
    teams = db.get_teams_by_tournament(tournament_id)
    teams_count = len(teams)
    
    return render_template('tournament/team_form.html', tournament=tournament, is_organizer=is_organizer, teams_count=teams_count)

@tournament_bp.route('/<tournament_id>/team/<team_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_team_form(tournament_id, team_id):
    """Edit team form page and handler"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        flash('Tournament not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    team = db.get_team_by_id(team_id)
    if not team:
        flash('Team not found', 'error')
        return redirect(url_for('tournament.teams', tournament_id=tournament_id))
    
    # Check if user is organizer
    is_organizer = session.get('user_id') == tournament.get('organizer_id')
    if not is_organizer:
        flash('You do not have permission to edit teams in this tournament', 'error')
        return redirect(url_for('tournament.teams', tournament_id=tournament_id))
    
    if request.method == 'POST':
        try:
            team_data = {
                'name': request.form.get('name', '').strip(),
                'short_name': request.form.get('short_name', '').strip(),
                'captain_name': request.form.get('captain_name', '').strip(),
                'captain_email': request.form.get('captain_email', '').strip(),
                'captain_phone': request.form.get('captain_phone', '').strip(),
                'description': request.form.get('description', '').strip(),
                'founded_year': int(request.form.get('founded_year', 0)) if request.form.get('founded_year') else None,
                'captain_position': request.form.get('captain_position', '').strip(),
                'preferred_formation': request.form.get('preferred_formation', '').strip(),
                'team_colors': request.form.get('team_colors', '').strip(),
                'notes': request.form.get('notes', '').strip(),
                'is_approved': request.form.get('is_approved') == 'on' if is_organizer else team.get('is_approved', True)
            }
            
            # Validate required fields
            if not team_data['name']:
                flash('Team name is required', 'error')
                teams = db.get_teams_by_tournament(tournament_id)
                teams_count = len(teams)
                return render_template('tournament/team_form.html', tournament=tournament, team=team, is_organizer=is_organizer, teams_count=teams_count)
            
            result = db.update_team(team_id, team_data)
            if result['success']:
                flash('Team updated successfully!', 'success')
                return redirect(url_for('tournament.teams', tournament_id=tournament_id))
            else:
                flash('Failed to update team: ' + result.get('error', 'Unknown error'), 'error')
                
        except Exception as e:
            flash(f'Error updating team: {str(e)}', 'error')
    
    # Get teams count for the stats
    teams = db.get_teams_by_tournament(tournament_id)
    teams_count = len(teams)
    
    return render_template('tournament/team_form.html', tournament=tournament, team=team, is_organizer=is_organizer, teams_count=teams_count)

@tournament_bp.route('/<tournament_id>/add-team', methods=['POST'])
@login_required
def add_team(tournament_id):
    """Add a team to tournament (API endpoint for backwards compatibility)"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        return jsonify({'success': False, 'error': 'Tournament not found'})
    
    # Check if user is organizer
    if session.get('user_id') != tournament.get('organizer_id'):
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    team_data = {
        'tournament_id': tournament_id,
        'name': request.form.get('name', '').strip(),
        'short_name': request.form.get('short_name', '').strip(),
        'captain_name': request.form.get('captain_name', '').strip(),
        'captain_email': request.form.get('captain_email', '').strip(),
        'captain_phone': request.form.get('captain_phone', '').strip(),
        'is_approved': True  # Auto-approve when added by organizer
    }
    
    if not team_data['name']:
        return jsonify({'success': False, 'error': 'Team name is required'})
    
    result = db.create_team(team_data)
    if result['success']:
        return jsonify({'success': True, 'team': result['team']})
    else:
        return jsonify({'success': False, 'error': 'Failed to add team'})

@tournament_bp.route('/<tournament_id>/edit-team/<team_id>', methods=['POST'])
@login_required
def edit_team(tournament_id, team_id):
    """Edit a team in tournament"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        return jsonify({'success': False, 'error': 'Tournament not found'})
    
    # Check if user is organizer
    if session.get('user_id') != tournament.get('organizer_id'):
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    team_data = {
        'name': request.form.get('name', '').strip(),
        'short_name': request.form.get('short_name', '').strip(),
        'captain_name': request.form.get('captain_name', '').strip(),
        'captain_email': request.form.get('captain_email', '').strip(),
        'captain_phone': request.form.get('captain_phone', '').strip(),
    }
    
    if not team_data['name']:
        return jsonify({'success': False, 'error': 'Team name is required'})
    
    result = db.update_team(team_id, team_data)
    if result['success']:
        return jsonify({'success': True, 'team': result['team']})
    else:
        return jsonify({'success': False, 'error': 'Failed to update team'})

@tournament_bp.route('/<tournament_id>/delete-team/<team_id>', methods=['DELETE'])
@login_required
def delete_team(tournament_id, team_id):
    """Delete a team from tournament"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        return jsonify({'success': False, 'error': 'Tournament not found'})
    
    # Check if user is organizer
    if session.get('user_id') != tournament.get('organizer_id'):
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    result = db.delete_team(team_id)
    if result['success']:
        return jsonify({'success': True, 'message': 'Team deleted successfully'})
    else:
        return jsonify({'success': False, 'error': 'Failed to delete team'})

@tournament_bp.route('/<tournament_id>/approve-team/<team_id>', methods=['POST'])
@login_required
def approve_team(tournament_id, team_id):
    """Approve a team in tournament"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        return jsonify({'success': False, 'error': 'Tournament not found'})
    
    # Check if user is organizer
    if session.get('user_id') != tournament.get('organizer_id'):
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    result = db.update_team(team_id, {'is_approved': True})
    if result['success']:
        return jsonify({'success': True, 'team': result['team']})
    else:
        return jsonify({'success': False, 'error': 'Failed to approve team'})

@tournament_bp.route('/<tournament_id>/get-team/<team_id>', methods=['GET'])
@login_required
def get_team(tournament_id, team_id):
    """Get team details for editing"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        return jsonify({'success': False, 'error': 'Tournament not found'})
    
    # Check if user is organizer
    if session.get('user_id') != tournament.get('organizer_id'):
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    team = db.get_team_by_id(team_id)
    if team:
        return jsonify({'success': True, 'team': team})
    else:
        return jsonify({'success': False, 'error': 'Team not found'})

@tournament_bp.route('/<tournament_id>/generate-fixtures', methods=['POST'])
@login_required
def generate_fixtures(tournament_id):
    """Generate tournament fixtures"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        return jsonify({'success': False, 'error': 'Tournament not found'})
    
    # Check if user is organizer (more flexible for development mode)
    current_user_id = session.get('user_id')
    tournament_organizer_id = tournament.get('organizer_id')
    
    # In development mode (no Supabase), allow if user is logged in or if it's a mock tournament
    is_development = not db.client
    is_mock_tournament = tournament_organizer_id == 'mock-organizer-123'
    
    if not is_development and not is_mock_tournament and current_user_id != tournament_organizer_id:
        return jsonify({'success': False, 'error': 'Permission denied'})
    elif not current_user_id and not is_development:
        return jsonify({'success': False, 'error': 'Authentication required'})
    
    # Handle solo vs team tournaments differently
    if tournament.get('type') == 'solo':
        participants = db.get_participants_by_tournament(tournament_id)
        existing_matches = db.get_solo_matches_by_tournament(tournament_id)
        
        if len(participants) < 2:
            return jsonify({
                'success': False, 
                'error': f'At least 2 participants required to generate fixtures. Currently have {len(participants)} participants.'
            })
        
        # Generate solo matches (participant vs participant)
        matches = generate_solo_matches(tournament, participants)
        
        # Debug info
        debug_info = {
            'participants_count': len(participants),
            'existing_matches_count': len(existing_matches),
            'generated_matches_count': len(matches),
            'tournament_format': tournament.get('format')
        }
        
        # Save solo matches to database
        created_matches = []
        failed_matches = []
        
        for match_data in matches:
            result = db.create_solo_match(match_data)
            if result['success']:
                created_matches.append(result['match'])
            else:
                failed_matches.append({
                    'match_data': match_data,
                    'error': result.get('error', 'Unknown error')
                })
        
        return jsonify({
            'success': True, 
            'matches_created': len(created_matches),
            'matches_failed': len(failed_matches),
            'matches': created_matches,
            'debug_info': debug_info,
            'failed_matches': failed_matches if failed_matches else None
        })
    
    else:
        teams = db.get_teams_by_tournament(tournament_id)
        if len(teams) < 2:
            return jsonify({'success': False, 'error': 'At least 2 teams required to generate fixtures'})
        
        # Generate team fixtures based on tournament format
        generator = TournamentGenerator(tournament, teams)
        matches = generator.generate_matches()
        
        # Save matches to database
        created_matches = []
        for match_data in matches:
            result = db.create_match(match_data)
            if result['success']:
                created_matches.append(result['match'])
        
        return jsonify({
            'success': True, 
            'matches_created': len(created_matches),
            'matches': created_matches
        })

@tournament_bp.route('/<tournament_id>/standings')
def standings(tournament_id):
    """View tournament standings"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        flash('Tournament not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Handle solo vs team tournaments differently
    if tournament.get('type') == 'solo':
        participants = db.get_participants_by_tournament(tournament_id)
        matches = db.get_solo_matches_by_tournament(tournament_id)
        print(f"Solo Tournament Debug: {len(participants)} participants, {len(matches)} matches")
        
        # Debug completed matches
        completed_matches = [m for m in matches if m.get('status') == 'completed']
        print(f"Completed solo matches: {len(completed_matches)}")
        for i, match in enumerate(completed_matches[:3]):  # Show first 3 matches
            print(f"Match {i+1}: P1 score={match.get('participant1_score')}, P2 score={match.get('participant2_score')}, Status={match.get('status')}")
        
        # Calculate participant standings
        standings_data = calculate_participant_standings(participants, matches)
    else:
        teams = db.get_teams_by_tournament(tournament_id)
        matches = db.get_matches_by_tournament(tournament_id)
        print(f"Team Tournament Debug: {len(teams)} teams, {len(matches)} matches")
        
        # Debug completed matches
        completed_matches = [m for m in matches if m.get('status') == 'completed']
        print(f"Completed team matches: {len(completed_matches)}")
        for i, match in enumerate(completed_matches[:3]):  # Show first 3 matches
            print(f"Match {i+1}: T1 score={match.get('team1_score')}, T2 score={match.get('team2_score')}, Status={match.get('status')}")
        
        # Calculate team standings
        standings_data = calculate_standings(teams, matches, tournament)
    
    # Debug calculated standings
    print(f"Calculated standings data: {len(standings_data)} entries")
    for i, standing in enumerate(standings_data[:3]):  # Show first 3 standings
        print(f"Standing {i+1}: GF={standing.get('goals_for', 0)}, GA={standing.get('goals_against', 0)}, GD={standing.get('goal_difference', 0)}, Points={standing.get('points', 0)}")
    
    # Calculate additional statistics for the header cards
    completed_matches = [m for m in matches if m.get('status') == 'completed']
    total_matches = len(completed_matches)
    
    # Calculate total goals from completed matches
    total_goals = 0
    for match in completed_matches:
        if tournament.get('type') == 'solo':
            score1 = match.get('participant1_score', 0) or 0
            score2 = match.get('participant2_score', 0) or 0
        else:
            score1 = match.get('team1_score', 0) or 0
            score2 = match.get('team2_score', 0) or 0
        total_goals += score1 + score2
    
    # Calculate average goals per match
    average_goals = round(total_goals / total_matches, 1) if total_matches > 0 else 0.0
    
    return render_template('tournament/standings.html', 
                         tournament=tournament,
                         standings=standings_data,
                         total_matches=total_matches,
                         total_goals=total_goals,
                         average_goals=average_goals)

@tournament_bp.route('/<tournament_id>/statistics')
def statistics(tournament_id):
    """View detailed tournament statistics"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        flash('Tournament not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get data based on tournament type
    if tournament.get('type') == 'solo':
        participants = db.get_participants_by_tournament(tournament_id)
        matches = db.get_solo_matches_by_tournament(tournament_id)
        standings_data = calculate_participant_standings(participants, matches)
    else:
        teams = db.get_teams_by_tournament(tournament_id)
        matches = db.get_matches_by_tournament(tournament_id)
        standings_data = calculate_standings(teams, matches, tournament)
    
    # Calculate comprehensive statistics
    stats = calculate_tournament_statistics(tournament, standings_data, matches)
    
    return render_template('tournament/statistics.html',
                         tournament=tournament,
                         standings=standings_data,
                         stats=stats)

@tournament_bp.route('/<tournament_id>/matches')
def matches(tournament_id):
    """View team tournament matches (teams only)"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        flash('Tournament not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    if tournament.get('type') == 'solo':
        # Redirect solo tournaments to the solo fixtures page
        return redirect(url_for('tournament.solo_fixtures', tournament_id=tournament_id))
    
    is_organizer = session.get('user_id') == tournament.get('organizer_id')

    matches = db.get_matches_by_tournament(tournament_id)
    teams = db.get_teams_by_tournament(tournament_id)
    
    # Create team lookup dictionary
    team_lookup = {team['id']: team for team in teams}
    
    # Add team names to matches and calculate statistics
    total_goals = 0
    for match in matches:
        team1_id = match.get('team1_id')
        team2_id = match.get('team2_id')
        match['team1_name'] = team_lookup.get(team1_id, {}).get('name', 'TBD')
        match['team2_name'] = team_lookup.get(team2_id, {}).get('name', 'TBD')
        match['team1'] = team_lookup.get(team1_id, {})
        match['team2'] = team_lookup.get(team2_id, {})
        
        # Calculate total goals for statistics
        team1_score = match.get('team1_score', 0) or 0
        team2_score = match.get('team2_score', 0) or 0
        total_goals += team1_score + team2_score
    
    # Group matches by round/status
    grouped_matches = {}
    for match in matches:
        round_name = match.get('round_name', 'Round 1')
        if round_name not in grouped_matches:
            grouped_matches[round_name] = []
        grouped_matches[round_name].append(match)
    
    # Calculate statistics for header
    total_matches = len(matches)
    completed_matches = [m for m in matches if m.get('status') == 'completed']
    scheduled_matches = [m for m in matches if m.get('status') == 'scheduled']
    live_matches = [m for m in matches if m.get('status') == 'live']
    
    return render_template('tournament/matches.html', 
                         tournament=tournament,
                         grouped_matches=grouped_matches,
                         is_organizer=is_organizer,
                         total_matches=total_matches,
                         completed_count=len(completed_matches),
                         scheduled_count=len(scheduled_matches),
                         live_count=len(live_matches),
                         total_goals=total_goals)

@tournament_bp.route('/<tournament_id>/solo-matches')
def solo_fixtures(tournament_id):
    """View solo tournament matches (participants only)"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        flash('Tournament not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    if tournament.get('type') != 'solo':
        # Redirect team tournaments to the team fixtures page
        return redirect(url_for('tournament.matches', tournament_id=tournament_id))
    
    is_organizer = session.get('user_id') == tournament.get('organizer_id')
    
    matches = db.get_solo_matches_by_tournament(tournament_id)
    participants = db.get_participants_by_tournament(tournament_id)
    
    # Create participant lookup dictionary
    participant_lookup = {participant['id']: participant for participant in participants}
    
    # Add participant names to matches
    for match in matches:
        p1_id = match.get('participant1_id')
        p2_id = match.get('participant2_id')
        match['participant1_name'] = participant_lookup.get(p1_id, {}).get('name', 'TBD')
        match['participant2_name'] = participant_lookup.get(p2_id, {}).get('name', 'TBD')
        match['participant1'] = participant_lookup.get(p1_id, {})
        match['participant2'] = participant_lookup.get(p2_id, {})
    
    completed_matches = [m for m in matches if m.get('status') == 'completed']
    upcoming_matches = [m for m in matches if m.get('status') == 'scheduled']
    
    return render_template('tournament/solo_fixtures.html', 
                         tournament=tournament,
                         matches=matches,
                         participants=participants,
                         completed_matches=len(completed_matches),
                         upcoming_matches=len(upcoming_matches),
                         is_organizer=is_organizer)

@tournament_bp.route('/<tournament_id>/generate-solo-fixtures', methods=['POST'])
@login_required
def generate_solo_fixtures(tournament_id):
    """Generate fixtures for solo tournaments only (separate endpoint)"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        return jsonify({'success': False, 'error': 'Tournament not found'})
    
    if tournament.get('type') != 'solo':
        return jsonify({'success': False, 'error': 'This endpoint is only for solo tournaments'})

    # Organizer check (reuse logic from main generator)
    current_user_id = session.get('user_id')
    tournament_organizer_id = tournament.get('organizer_id')
    is_development = not db.client
    is_mock_tournament = tournament_organizer_id == 'mock-organizer-123'
    if not is_development and not is_mock_tournament and current_user_id != tournament_organizer_id:
        return jsonify({'success': False, 'error': 'Permission denied'})

    participants = db.get_participants_by_tournament(tournament_id)
    if len(participants) < 2:
        return jsonify({'success': False, 'error': 'At least 2 participants required to generate fixtures'})

    matches = generate_solo_matches(tournament, participants)

    created_matches = []
    for match_data in matches:
        result = db.create_solo_match(match_data)
        if result['success']:
            created_matches.append(result['match'])

    return jsonify({
        'success': True,
        'matches_created': len(created_matches),
        'matches': created_matches
    })

@tournament_bp.route('/<tournament_id>/solo-matches/<match_id>', methods=['GET'])
@login_required  
def get_solo_match(tournament_id, match_id):
    """Get solo match details for editing"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        return jsonify({'success': False, 'error': 'Tournament not found'})
    
    if tournament.get('type') != 'solo':
        return jsonify({'success': False, 'error': 'This endpoint is only for solo tournaments'})
    
    # Check if user is organizer
    current_user_id = session.get('user_id')
    tournament_organizer_id = tournament.get('organizer_id')
    is_development = not db.client
    is_mock_tournament = tournament_organizer_id == 'mock-organizer-123'
    if not is_development and not is_mock_tournament and current_user_id != tournament_organizer_id:
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    # Get match details
    match = db.get_solo_match_by_id(match_id)
    if not match:
        return jsonify({'success': False, 'error': 'Match not found'})
        
    # Get participant names
    participants = db.get_participants_by_tournament(tournament_id)
    participant_lookup = {p['id']: p for p in participants}
    
    match['participant1_name'] = participant_lookup.get(match.get('participant1_id'), {}).get('name', 'TBD')
    match['participant2_name'] = participant_lookup.get(match.get('participant2_id'), {}).get('name', 'TBD')
    match['participant1'] = participant_lookup.get(match.get('participant1_id'), {})
    match['participant2'] = participant_lookup.get(match.get('participant2_id'), {})
    
    return jsonify({'success': True, 'match': match})

@tournament_bp.route('/<tournament_id>/solo-matches/<match_id>', methods=['POST'])
@login_required
def update_solo_match(tournament_id, match_id):
    """Update solo match details"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        return jsonify({'success': False, 'error': 'Tournament not found'})
    
    if tournament.get('type') != 'solo':
        return jsonify({'success': False, 'error': 'This endpoint is only for solo tournaments'})
    
    # Check if user is organizer
    current_user_id = session.get('user_id')
    tournament_organizer_id = tournament.get('organizer_id')
    is_development = not db.client
    is_mock_tournament = tournament_organizer_id == 'mock-organizer-123'
    if not is_development and not is_mock_tournament and current_user_id != tournament_organizer_id:
        return jsonify({'success': False, 'error': 'Permission denied'})
        
    # Get form data
    try:
        data = request.get_json() if request.is_json else {
            'participant1_score': request.form.get('participant1_score'),
            'participant2_score': request.form.get('participant2_score'),
            'status': request.form.get('status', 'scheduled'),
            'scheduled_date': request.form.get('match_date')  # Frontend still uses 'match_date'
        }
        
        update_data = {
            'status': data.get('status', 'scheduled')
        }
        
        # Only include scheduled_date if provided
        if data.get('scheduled_date'):
            update_data['scheduled_date'] = data.get('scheduled_date')
        
        # Handle scores
        if data.get('participant1_score') is not None:
            update_data['participant1_score'] = int(data['participant1_score'])
        if data.get('participant2_score') is not None:
            update_data['participant2_score'] = int(data['participant2_score'])
        
        # Determine winner if both scores are provided and status is completed
        if (update_data.get('participant1_score') is not None and 
            update_data.get('participant2_score') is not None and 
            update_data.get('status') == 'completed'):
            
            match = db.get_solo_match_by_id(match_id)
            if match:
                if update_data['participant1_score'] > update_data['participant2_score']:
                    update_data['winner_id'] = match.get('participant1_id')
                elif update_data['participant2_score'] > update_data['participant1_score']:
                    update_data['winner_id'] = match.get('participant2_id')
                # If scores are equal, no winner (draw)
        
        result = db.update_solo_match(match_id, update_data)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Match updated successfully',
                'match': result.get('match', {})
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to update match')
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@tournament_bp.route('/<tournament_id>/solo-matches/<match_id>/reset', methods=['POST'])
@login_required
def reset_solo_match(tournament_id, match_id):
    """Reset solo match to scheduled status"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        return jsonify({'success': False, 'error': 'Tournament not found'})
    
    if tournament.get('type') != 'solo':
        return jsonify({'success': False, 'error': 'This endpoint is only for solo tournaments'})
    
    # Check if user is organizer
    current_user_id = session.get('user_id')
    tournament_organizer_id = tournament.get('organizer_id')
    is_development = not db.client
    is_mock_tournament = tournament_organizer_id == 'mock-organizer-123'
    if not is_development and not is_mock_tournament and current_user_id != tournament_organizer_id:
        return jsonify({'success': False, 'error': 'Permission denied'})
        
    # Reset match data
    reset_data = {
        'participant1_score': 0,  # Reset to 0 instead of None
        'participant2_score': 0,  # Reset to 0 instead of None
        'winner_id': None,
        'status': 'scheduled',
        'scheduled_date': None
    }
    
    result = db.update_solo_match(match_id, reset_data)
    
    if result['success']:
        return jsonify({
            'success': True,
            'message': 'Match reset successfully'
        })
    else:
        return jsonify({
            'success': False,
            'error': result.get('error', 'Failed to reset match')
        })

@tournament_bp.route('/<tournament_id>/solo-matches/<match_id>/delete', methods=['DELETE'])
@login_required
def delete_solo_match(tournament_id, match_id):
    """Delete a solo match"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        return jsonify({'success': False, 'error': 'Tournament not found'})
    
    if tournament.get('type') != 'solo':
        return jsonify({'success': False, 'error': 'This endpoint is only for solo tournaments'})
    
    # Check if user is organizer
    current_user_id = session.get('user_id')
    tournament_organizer_id = tournament.get('organizer_id')
    is_development = not db.client
    is_mock_tournament = tournament_organizer_id == 'mock-organizer-123'
    if not is_development and not is_mock_tournament and current_user_id != tournament_organizer_id:
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    # Delete the match
    result = db.delete_solo_match(match_id)
    
    if result['success']:
        return jsonify({
            'success': True,
            'message': 'Match deleted successfully'
        })
    else:
        return jsonify({
            'success': False,
            'error': result.get('error', 'Failed to delete match')
        })

@tournament_bp.route('/<tournament_id>/team/<team_id>/players')
@login_required
def team_players(tournament_id, team_id):
    """Manage players for a team"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        flash('Tournament not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    team = db.get_team_by_id(team_id)
    if not team:
        flash('Team not found', 'error')
        return redirect(url_for('tournament.teams', tournament_id=tournament_id))
    
    players = db.get_players_by_team(team_id)
    is_organizer = session.get('user_id') == tournament.get('organizer_id')
    
    return render_template('tournament/team_players.html', 
                         tournament=tournament,
                         team=team,
                         players=players,
                         is_organizer=is_organizer)

@tournament_bp.route('/<tournament_id>/team/<team_id>/add-player', methods=['POST'])
@login_required
def add_player(tournament_id, team_id):
    """Add a player to team"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        return jsonify({'success': False, 'error': 'Tournament not found'})
    
    # Check if user is organizer
    if session.get('user_id') != tournament.get('organizer_id'):
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    player_data = {
        'team_id': team_id,
        'tournament_id': tournament_id,
        'name': request.form.get('name', '').strip(),
        'jersey_number': int(request.form.get('jersey_number', 0)) if request.form.get('jersey_number') else None,
        'position': request.form.get('position', '').strip(),
        'email': request.form.get('email', '').strip(),
        'phone': request.form.get('phone', '').strip(),
        'date_of_birth': request.form.get('date_of_birth') or None
    }
    
    if not player_data['name']:
        return jsonify({'success': False, 'error': 'Player name is required'})
    
    # Check for duplicate jersey numbers within the team
    if player_data['jersey_number']:
        existing_players = db.get_players_by_team(team_id)
        for player in existing_players:
            if player.get('jersey_number') == player_data['jersey_number']:
                return jsonify({'success': False, 'error': 'Jersey number already taken'})
    
    result = db.create_player(player_data)
    if result['success']:
        return jsonify({'success': True, 'player': result['player']})
    else:
        return jsonify({'success': False, 'error': 'Failed to add player'})

@tournament_bp.route('/<tournament_id>/team/<team_id>/edit-player/<player_id>', methods=['POST'])
@login_required
def edit_player(tournament_id, team_id, player_id):
    """Edit a player in team"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        return jsonify({'success': False, 'error': 'Tournament not found'})
    
    # Check if user is organizer
    if session.get('user_id') != tournament.get('organizer_id'):
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    player_data = {
        'name': request.form.get('name', '').strip(),
        'jersey_number': int(request.form.get('jersey_number', 0)) if request.form.get('jersey_number') else None,
        'position': request.form.get('position', '').strip()
    }
    
    if not player_data['name']:
        return jsonify({'success': False, 'error': 'Player name is required'})
    
    # Check for duplicate jersey numbers within the team (excluding current player)
    if player_data['jersey_number']:
        existing_players = db.get_players_by_team(team_id)
        for player in existing_players:
            if player.get('jersey_number') == player_data['jersey_number'] and player['id'] != player_id:
                return jsonify({'success': False, 'error': 'Jersey number already taken'})
    
    result = db.update_player(player_id, player_data)
    if result['success']:
        return jsonify({'success': True, 'player': result['player']})
    else:
        return jsonify({'success': False, 'error': 'Failed to update player'})

@tournament_bp.route('/<tournament_id>/team/<team_id>/delete-player/<player_id>', methods=['DELETE'])
@login_required
def delete_player(tournament_id, team_id, player_id):
    """Delete a player from team"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        return jsonify({'success': False, 'error': 'Tournament not found'})
    
    # Check if user is organizer
    if session.get('user_id') != tournament.get('organizer_id'):
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    result = db.delete_player(player_id)
    if result['success']:
        return jsonify({'success': True, 'message': 'Player deleted successfully'})
    else:
        return jsonify({'success': False, 'error': 'Failed to delete player'})

@tournament_bp.route('/<tournament_id>/team/<team_id>/player/add', methods=['GET', 'POST'])
@login_required
def add_player_form(tournament_id, team_id):
    """Add player form page and handler"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        flash('Tournament not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    team = db.get_team_by_id(team_id)
    if not team:
        flash('Team not found', 'error')
        return redirect(url_for('tournament.teams', tournament_id=tournament_id))
    
    # Check if user is organizer
    is_organizer = session.get('user_id') == tournament.get('organizer_id')
    if not is_organizer:
        flash('You do not have permission to add players to this team', 'error')
        return redirect(url_for('tournament.team_players', tournament_id=tournament_id, team_id=team_id))
    
    if request.method == 'POST':
        try:
            player_data = {
                'team_id': team_id,
                'tournament_id': tournament_id,
                'name': request.form.get('name', '').strip(),
                'jersey_number': int(request.form.get('jersey_number', 0)) if request.form.get('jersey_number') else None,
                'position': request.form.get('position', '').strip()
            }
            
            # Validate required fields
            if not player_data['name']:
                flash('Player name is required', 'error')
                players = db.get_players_by_team(team_id)
                players_count = len(players)
                return render_template('tournament/player_form.html', tournament=tournament, team=team, players_count=players_count)
            
            # Check for duplicate jersey numbers within the team
            if player_data['jersey_number']:
                existing_players = db.get_players_by_team(team_id)
                for player in existing_players:
                    if player.get('jersey_number') == player_data['jersey_number']:
                        flash('Jersey number already taken by another player', 'error')
                        players = db.get_players_by_team(team_id)
                        players_count = len(players)
                        return render_template('tournament/player_form.html', tournament=tournament, team=team, players_count=players_count)
            
            result = db.create_player(player_data)
            if result['success']:
                flash('Player added successfully!', 'success')
                return redirect(url_for('tournament.team_players', tournament_id=tournament_id, team_id=team_id))
            else:
                flash('Failed to add player: ' + result.get('error', 'Unknown error'), 'error')
                
        except Exception as e:
            flash(f'Error adding player: {str(e)}', 'error')
    
    # Get players count for the stats
    players = db.get_players_by_team(team_id)
    players_count = len(players)
    
    return render_template('tournament/player_form.html', tournament=tournament, team=team, players_count=players_count)

@tournament_bp.route('/<tournament_id>/team/<team_id>/player/<player_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_player_form(tournament_id, team_id, player_id):
    """Edit player form page and handler"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        flash('Tournament not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    team = db.get_team_by_id(team_id)
    if not team:
        flash('Team not found', 'error')
        return redirect(url_for('tournament.teams', tournament_id=tournament_id))
    
    player = db.get_player_by_id(player_id)
    if not player:
        flash('Player not found', 'error')
        return redirect(url_for('tournament.team_players', tournament_id=tournament_id, team_id=team_id))
    
    # Check if user is organizer
    is_organizer = session.get('user_id') == tournament.get('organizer_id')
    if not is_organizer:
        flash('You do not have permission to edit players in this team', 'error')
        return redirect(url_for('tournament.team_players', tournament_id=tournament_id, team_id=team_id))
    
    if request.method == 'POST':
        try:
            player_data = {
                'name': request.form.get('name', '').strip(),
                'jersey_number': int(request.form.get('jersey_number', 0)) if request.form.get('jersey_number') else None,
                'position': request.form.get('position', '').strip()
            }
            
            # Validate required fields
            if not player_data['name']:
                flash('Player name is required', 'error')
                players = db.get_players_by_team(team_id)
                players_count = len(players)
                return render_template('tournament/player_form.html', tournament=tournament, team=team, player=player, players_count=players_count)
            
            # Check for duplicate jersey numbers within the team (excluding current player)
            if player_data['jersey_number']:
                existing_players = db.get_players_by_team(team_id)
                for existing_player in existing_players:
                    if existing_player.get('jersey_number') == player_data['jersey_number'] and existing_player['id'] != player_id:
                        flash('Jersey number already taken by another player', 'error')
                        players = db.get_players_by_team(team_id)
                        players_count = len(players)
                        return render_template('tournament/player_form.html', tournament=tournament, team=team, player=player, players_count=players_count)
            
            result = db.update_player(player_id, player_data)
            if result['success']:
                flash('Player updated successfully!', 'success')
                return redirect(url_for('tournament.team_players', tournament_id=tournament_id, team_id=team_id))
            else:
                flash('Failed to update player: ' + result.get('error', 'Unknown error'), 'error')
                
        except Exception as e:
            flash(f'Error updating player: {str(e)}', 'error')
    
    # Get players count for the stats
    players = db.get_players_by_team(team_id)
    players_count = len(players)
    
    return render_template('tournament/player_form.html', tournament=tournament, team=team, player=player, players_count=players_count)

@tournament_bp.route('/<tournament_id>/team/<team_id>/get-player/<player_id>', methods=['GET'])
@login_required
def get_player(tournament_id, team_id, player_id):
    """Get player details for editing"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        return jsonify({'success': False, 'error': 'Tournament not found'})
    
    # Check if user is organizer
    if session.get('user_id') != tournament.get('organizer_id'):
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    player = db.get_player_by_id(player_id)
    if player:
        return jsonify({'success': True, 'player': player})
    else:
        return jsonify({'success': False, 'error': 'Player not found'})

@tournament_bp.route('/<tournament_id>/start-match/<match_id>', methods=['POST'])
@login_required
def start_match(tournament_id, match_id):
    """Start a match"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        return jsonify({'success': False, 'error': 'Tournament not found'})
    
    # Check if user is organizer
    if session.get('user_id') != tournament.get('organizer_id'):
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    # Update match status to live
    result = db.update_match_score(match_id, {'status': 'live'})
    if result['success']:
        return jsonify({'success': True, 'message': 'Match started successfully'})
    else:
        return jsonify({'success': False, 'error': 'Failed to start match'})

@tournament_bp.route('/<tournament_id>/end-match/<match_id>', methods=['POST'])
@login_required
def end_match(tournament_id, match_id):
    """End a match with scores"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        return jsonify({'success': False, 'error': 'Tournament not found'})
    
    # Check if user is organizer
    if session.get('user_id') != tournament.get('organizer_id'):
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    try:
        team1_score = int(request.form.get('team1_score', 0))
        team2_score = int(request.form.get('team2_score', 0))
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Invalid score values'})
    
    # Determine winner
    winner_id = None
    if team1_score > team2_score:
        # Get match details to find team1_id
        matches = db.get_matches_by_tournament(tournament_id)
        current_match = next((m for m in matches if m['id'] == match_id), None)
        if current_match:
            winner_id = current_match.get('team1_id')
    elif team2_score > team1_score:
        matches = db.get_matches_by_tournament(tournament_id)
        current_match = next((m for m in matches if m['id'] == match_id), None)
        if current_match:
            winner_id = current_match.get('team2_id')
    
    # Update match with final scores
    match_data = {
        'team1_score': team1_score,
        'team2_score': team2_score,
        'winner_id': winner_id,
        'status': 'completed'
    }
    
    result = db.update_match_score(match_id, match_data)
    if result['success']:
        return jsonify({'success': True, 'message': 'Match ended successfully', 'match': result['match']})
    else:
        return jsonify({'success': False, 'error': 'Failed to end match'})

@tournament_bp.route('/<tournament_id>/edit-match/<match_id>', methods=['GET', 'POST'])
@login_required
def edit_match(tournament_id, match_id):
    """Edit match details"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        return jsonify({'success': False, 'error': 'Tournament not found'})
    
    # Check if user is organizer
    if session.get('user_id') != tournament.get('organizer_id'):
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    if request.method == 'GET':
        # Get match details
        match = db.get_match_by_id(match_id)
        if match:
            return jsonify({'success': True, 'match': match})
        else:
            return jsonify({'success': False, 'error': 'Match not found'})
    
    elif request.method == 'POST':
        # Update match details
        match_data = {
            'scheduled_date': request.form.get('scheduled_date'),
            'venue': request.form.get('venue', '').strip(),
            'notes': request.form.get('notes', '').strip(),
            'referee': request.form.get('referee', '').strip()
        }
        
        # Remove empty values
        match_data = {k: v for k, v in match_data.items() if v}
        
        result = db.update_match_score(match_id, match_data)
        if result['success']:
            return jsonify({'success': True, 'message': 'Match updated successfully', 'match': result['match']})
        else:
            return jsonify({'success': False, 'error': 'Failed to update match'})

@tournament_bp.route('/<tournament_id>/matches/<match_id>/result')
@login_required
def match_result(tournament_id, match_id):
    """eFootball result entry page"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        flash('Tournament not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Check if user is organizer
    if session.get('user_id') != tournament.get('organizer_id'):
        flash('You do not have permission to manage this tournament', 'error')
        return redirect(url_for('tournament.matches', tournament_id=tournament_id))
    
    match = db.get_match_by_id(match_id)
    if not match:
        flash('Match not found', 'error')
        return redirect(url_for('tournament.matches', tournament_id=tournament_id))
    
    # Get team details
    teams = db.get_teams_by_tournament(tournament_id)
    team_lookup = {team['id']: team for team in teams}
    
    team1 = team_lookup.get(match.get('team1_id'), {})
    team2 = team_lookup.get(match.get('team2_id'), {})
    
    # Get players for each team
    team1_players = []
    team2_players = []
    
    if team1.get('id'):
        team1_players = db.get_players_by_team(team1['id'])
    if team2.get('id'):
        team2_players = db.get_players_by_team(team2['id'])
    
    # Get existing sub-matches if this is a team tournament and match is completed
    existing_sub_matches = []
    if tournament.get('type') == 'team' and match.get('status') == 'completed':
        existing_sub_matches = db.get_sub_matches_by_parent_match(match_id)
        print(f"Found {len(existing_sub_matches)} existing sub-matches for match {match_id}")
        if existing_sub_matches:
            for i, sub_match in enumerate(existing_sub_matches):
                print(f"  Sub-match {i+1}: {sub_match.get('team1_player_id')} vs {sub_match.get('team2_player_id')} ({sub_match.get('team1_player_goals', 0)}-{sub_match.get('team2_player_goals', 0)})")
    
    return render_template('tournament/match_result.html',
                         tournament=tournament,
                         match=match,
                         team1=team1,
                         team2=team2,
                         team1_players=team1_players,
                         team2_players=team2_players,
                         existing_sub_matches=existing_sub_matches)

@tournament_bp.route('/<tournament_id>/matches/<match_id>/save-result', methods=['POST'])
@login_required
def save_match_result(tournament_id, match_id):
    """Save eFootball match result with multi-match support and tiebreaker handling"""
    print(f"\n=== SAVING MATCH RESULT ===")
    print(f"Tournament ID: {tournament_id}")
    print(f"Match ID: {match_id}")
    print(f"Form data: {dict(request.form)}")
    
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        print("ERROR: Tournament not found")
        return jsonify({'success': False, 'error': 'Tournament not found'})
    
    print(f"Tournament: {tournament}")
    
    # Check if user is organizer
    if session.get('user_id') != tournament.get('organizer_id'):
        print(f"ERROR: Permission denied. User: {session.get('user_id')}, Organizer: {tournament.get('organizer_id')}")
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    try:
        # Basic match data
        notes = request.form.get('notes', '').strip()
        
        # Handle scoring based on tournament type
        if tournament.get('type') == 'team':
            print("Processing team tournament")
            # Check if using multi-match system
            has_sub_matches = request.form.get('has_sub_matches') == 'true'
            print(f"Has sub-matches: {has_sub_matches}")
            
            if has_sub_matches:
                # Process sub-matches and save them
                sub_matches_data = []
                match_data = db.get_match_by_id(match_id)
                
                # Parse sub-match data from form
                counter = 1
                while True:
                    team1_player = request.form.get(f'sub_match_{counter}_team1_player')
                    team2_player = request.form.get(f'sub_match_{counter}_team2_player')
                    
                    if not team1_player or not team2_player:
                        break
                    
                    team1_goals = int(request.form.get(f'sub_match_{counter}_team1_goals', 0))
                    team2_goals = int(request.form.get(f'sub_match_{counter}_team2_goals', 0))
                    
                    if team1_goals < 0 or team2_goals < 0:
                        return jsonify({'success': False, 'error': 'Goals cannot be negative'})
                    
                    # Determine winner of sub-match
                    winner_player_id = None
                    if team1_goals > team2_goals:
                        winner_player_id = team1_player
                    elif team2_goals > team1_goals:
                        winner_player_id = team2_player
                    
                    sub_match = {
                        'parent_match_id': match_id,
                        'tournament_id': tournament_id,
                        'team1_id': match_data.get('team1_id'),
                        'team2_id': match_data.get('team2_id'),
                        'team1_player_id': team1_player,
                        'team2_player_id': team2_player,
                        'team1_player_goals': team1_goals,
                        'team2_player_goals': team2_goals,
                        'winner_id': winner_player_id,
                        'match_order': counter,
                        'status': 'completed'
                    }
                    
                    sub_matches_data.append(sub_match)
                    counter += 1
                
                print(f"Collected {len(sub_matches_data)} sub-matches: {sub_matches_data}")
                
                if not sub_matches_data:
                    print("ERROR: No sub-matches provided")
                    return jsonify({'success': False, 'error': 'No sub-matches provided'})
                
                print("Calculating team scores from sub-matches")
                # Calculate team scores from sub-matches
                team1_wins = sum(1 for sm in sub_matches_data if sm['team1_player_goals'] > sm['team2_player_goals'])
                team2_wins = sum(1 for sm in sub_matches_data if sm['team2_player_goals'] > sm['team1_player_goals'])
                draws = sum(1 for sm in sub_matches_data if sm['team1_player_goals'] == sm['team2_player_goals'])
                
                team1_total_goals = sum(sm['team1_player_goals'] for sm in sub_matches_data)
                team2_total_goals = sum(sm['team2_player_goals'] for sm in sub_matches_data)
                
                # Calculate team scores based on scoring system
                scoring_system = tournament.get('scoring_system', 'win_based')
                if scoring_system == 'goal_based':
                    team1_score = team1_total_goals
                    team2_score = team2_total_goals
                else:
                    # Win-based: 3 points per win, 1 point per draw
                    team1_score = (team1_wins * 3) + draws
                    team2_score = (team2_wins * 3) + draws
                
                # Check if this match already has sub-matches (editing mode)
                print("Checking for existing sub-matches...")
                existing_sub_matches = db.get_sub_matches_by_parent_match(match_id)
                if existing_sub_matches:
                    print(f"Found {len(existing_sub_matches)} existing sub-matches. Clearing them first.")
                    # Delete existing sub-matches and their participants
                    print("Deleting existing sub-matches...")
                    delete_result = db.delete_sub_matches_by_parent_match(match_id)
                    if not delete_result.get('success'):
                        return jsonify({'success': False, 'error': f'Failed to clear existing sub-matches: {delete_result.get("error", "Unknown error")}'})
                    
                    # Delete existing match participants
                    print("Deleting existing match participants...")
                    participants_result = db.delete_match_participants_by_match(match_id)
                    if not participants_result.get('success'):
                        print(f"Warning: Failed to clear existing participants: {participants_result.get('error', 'Unknown error')}")
                else:
                    print("No existing sub-matches found.")
                
                # Save sub-matches to database using batch operation
                print(f"Saving {len(sub_matches_data)} sub-matches in batch...")
                batch_result = db.create_sub_matches_batch(sub_matches_data)
                if not batch_result.get('success'):
                    return jsonify({'success': False, 'error': f'Failed to save sub-matches: {batch_result.get("error", "Unknown error")}'})
                
                print(f"Successfully saved {batch_result.get('count', 0)} sub-matches.")
                
            else:
                # Legacy single-match system
                team1_player_goals = int(request.form.get('team1_player_goals', 0))
                team2_player_goals = int(request.form.get('team2_player_goals', 0))
                
                if team1_player_goals < 0 or team2_player_goals < 0:
                    return jsonify({'success': False, 'error': 'Player goals cannot be negative'})
                
                # Calculate team scores based on scoring system
                scoring_system = tournament.get('scoring_system', 'win_based')
                if scoring_system == 'goal_based':
                    team1_score = team1_player_goals
                    team2_score = team2_player_goals
                else:
                    # Win-based scoring
                    if team1_player_goals > team2_player_goals:
                        team1_score = 3
                        team2_score = 0
                    elif team2_player_goals > team1_player_goals:
                        team1_score = 0
                        team2_score = 3
                    else:
                        team1_score = 1
                        team2_score = 1
        else:
            # For solo tournaments, get scores directly
            team1_score = int(request.form.get('team1_score', 0))
            team2_score = int(request.form.get('team2_score', 0))
            
            if team1_score < 0 or team2_score < 0:
                return jsonify({'success': False, 'error': 'Scores cannot be negative'})
                
    except (ValueError, TypeError) as e:
        return jsonify({'success': False, 'error': f'Invalid score values: {str(e)}'})
    
    # Determine winner
    winner_id = None
    match_data = db.get_match_by_id(match_id)
    if team1_score > team2_score:
        winner_id = match_data.get('team1_id')
    elif team2_score > team1_score:
        winner_id = match_data.get('team2_id')
    
    # Check for knockout draw and tiebreaker
    tiebreaker_type = request.form.get('tiebreaker_type')
    is_draw = team1_score == team2_score and team1_score > 0
    is_knockout = tournament.get('format_type') == 'knockout'
    
    # Prepare match result data
    result_data = {
        'team1_score': team1_score,
        'team2_score': team2_score,
        'winner_id': winner_id,
        'status': 'completed',
        'notes': notes
    }
    
    if tournament.get('type') == 'team':
        result_data['has_sub_matches'] = request.form.get('has_sub_matches') == 'true'
    
    # Save main match result
    print(f"Saving main match result: {result_data}")
    result = db.update_match_score(match_id, result_data)
    print(f"Match save result: {result}")
    if not result['success']:
        print("ERROR: Failed to save match result")
        return jsonify({'success': False, 'error': 'Failed to save match result'})
    
    # Handle tiebreaker creation for knockout draws
    tiebreaker_matches = []
    if is_draw and is_knockout and tiebreaker_type:
        try:
            tiebreaker_matches = create_tiebreaker_matches(
                tournament_id, match_id, match_data, tiebreaker_type
            )
        except Exception as e:
            # Don't fail the main save, but log the error
            print(f"Failed to create tiebreaker matches: {str(e)}")
    
    response_data = {
        'success': True, 
        'message': 'Match result saved successfully', 
        'match': result['match']
    }
    
    if tiebreaker_matches:
        response_data['tiebreaker_matches'] = tiebreaker_matches
        response_data['message'] += f' {len(tiebreaker_matches)} tiebreaker matches created.'
    
    return jsonify(response_data)

def create_tiebreaker_matches(tournament_id, parent_match_id, parent_match_data, tiebreaker_type):
    """Create tiebreaker matches for knockout draws"""
    tiebreaker_matches = []
    
    # Determine number of matches to create
    num_matches = 1 if tiebreaker_type == 'best_of_1' else 3  # best_of_3
    
    for i in range(num_matches):
        match_data = {
            'tournament_id': tournament_id,
            'team1_id': parent_match_data['team1_id'],
            'team2_id': parent_match_data['team2_id'],
            'round_name': f"{parent_match_data.get('round_name', 'Match')} - Tiebreaker {i+1}",
            'status': 'scheduled',
            'is_tiebreaker': True,
            'tiebreaker_type': tiebreaker_type,
            'parent_tiebreaker_match_id': parent_match_id,
            'scheduled_date': parent_match_data.get('scheduled_date'),
            'venue': parent_match_data.get('venue')
        }
        
        result = db.create_match(match_data)
        if result['success']:
            tiebreaker_matches.append(result['match'])
    
    return tiebreaker_matches

@tournament_bp.route('/<tournament_id>/matches/<match_id>/reset', methods=['POST'])
@login_required
def reset_match(tournament_id, match_id):
    """Reset match to pending status"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        return jsonify({'success': False, 'error': 'Tournament not found'})
    
    # Check if user is organizer
    if session.get('user_id') != tournament.get('organizer_id'):
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    # Reset match data
    reset_data = {
        'team1_score': None,
        'team2_score': None,
        'winner_id': None,
        'status': 'scheduled',
        'notes': '',
        'statistics': None
    }
    
    result = db.update_match_score(match_id, reset_data)
    if result['success']:
        return jsonify({'success': True, 'message': 'Match reset successfully'})
    else:
        return jsonify({'success': False, 'error': 'Failed to reset match'})

@tournament_bp.route('/<tournament_id>/matches/<match_id>/details')
def match_details(tournament_id, match_id):
    """View detailed match information"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        flash('Tournament not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    match = db.get_match_by_id(match_id)
    if not match:
        flash('Match not found', 'error')
        return redirect(url_for('tournament.matches', tournament_id=tournament_id))
    
    # Get team details
    teams = db.get_teams_by_tournament(tournament_id)
    team_lookup = {team['id']: team for team in teams}
    
    team1 = team_lookup.get(match.get('team1_id'), {})
    team2 = team_lookup.get(match.get('team2_id'), {})
    
    # Get sub-matches for team tournaments
    sub_matches = []
    if tournament.get('type') == 'team':
        print(f"\n=== FETCHING SUB-MATCHES FOR MATCH {match_id} ===")
        
        # Use the enhanced method that includes player names
        sub_matches = db.get_sub_matches_with_player_names(match_id)
        print(f"Found {len(sub_matches)} sub-matches with names: {sub_matches}")
        
        # Normalize the data for template consistency
        for i, sub_match in enumerate(sub_matches):
            # Map database fields to template-friendly names
            sub_match['player1_name'] = sub_match.get('team1_player_name', 'Unknown Player')
            sub_match['player2_name'] = sub_match.get('team2_player_name', 'Unknown Player')
            sub_match['player1_id'] = sub_match.get('team1_player_id')
            sub_match['player2_id'] = sub_match.get('team2_player_id')
            sub_match['player1_score'] = sub_match.get('team1_player_goals', 0) or 0
            sub_match['player2_score'] = sub_match.get('team2_player_goals', 0) or 0
            
            # Set status and winner info
            sub_match['status'] = 'completed' if sub_match.get('team1_player_goals') is not None else 'pending'
            sub_match['is_draw'] = (sub_match.get('team1_player_goals', 0) == sub_match.get('team2_player_goals', 0) and 
                                   sub_match.get('team1_player_goals', 0) > 0)
            
            print(f"Sub-match {i+1}: {sub_match['player1_name']} vs {sub_match['player2_name']} ({sub_match['player1_score']}-{sub_match['player2_score']})")
        
        print(f"Final processed sub_matches: {len(sub_matches)} matches")
                
    
    is_organizer = session.get('user_id') == tournament.get('organizer_id')
    
    return render_template('tournament/match_details.html',
                         tournament=tournament,
                         match=match,
                         team1=team1,
                         team2=team2,
                         sub_matches=sub_matches,
                         is_organizer=is_organizer)

# Participant Management Routes for Solo Tournaments
@tournament_bp.route('/<tournament_id>/participants')
def participants(tournament_id):
    """View tournament participants page"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        flash('Tournament not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get participants for this tournament
    tournament_participants = db.get_participants_by_tournament(tournament_id)
    
    # Calculate stats
    matches_played = 0
    for participant in tournament_participants:
        # Add participant stats (wins, losses, etc.)
        participant['stats'] = {
            'wins': 0,
            'losses': 0,
            'matches_played': 0,
            'win_rate': 0
        }
    
    # Check if user is organizer
    is_organizer = session.get('user_id') == tournament.get('organizer_id')
    
    return render_template('tournament/participants.html',
                         tournament=tournament,
                         participants=tournament_participants,
                         matches_played=matches_played,
                         is_organizer=is_organizer)

@tournament_bp.route('/<tournament_id>/participants/add', methods=['GET', 'POST'])
@login_required
def add_participant(tournament_id):
    """Add a new participant to the tournament"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        if request.method == 'GET':
            flash('Tournament not found', 'error')
            return redirect(url_for('main.dashboard'))
        return jsonify({'success': False, 'error': 'Tournament not found'})
    
    # Check if user is organizer
    if session.get('user_id') != tournament.get('organizer_id'):
        if request.method == 'GET':
            flash('Permission denied', 'error')
            return redirect(url_for('tournament.participants', tournament_id=tournament_id))
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    if request.method == 'GET':
        # Get current participants count
        participants = db.get_participants_by_tournament(tournament_id)
        participants_count = len(participants)
        
        return render_template('tournament/add_participant.html', 
                             tournament=tournament,
                             participants_count=participants_count)
    
    try:
        # Get form data
        name = request.form.get('name', '').strip()
        gamer_tag = request.form.get('gamer_tag', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        platform = request.form.get('platform', '').strip()
        
        if not name:
            return jsonify({'success': False, 'error': 'Player name is required'})
        
        # Get is_approved from checkbox (it will be 'on' if checked, None if not)
        is_approved = request.form.get('is_approved') == 'on'
        
        # Create participant data
        participant_data = {
            'tournament_id': tournament_id,
            'name': name,
            'gamer_tag': gamer_tag,
            'email': email,
            'phone': phone,
            'platform': platform,
            'is_approved': is_approved
        }
        
        # Create participant using database
        result = db.create_participant(participant_data)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Player added successfully',
                'participant': result['participant']
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to add participant')
            })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@tournament_bp.route('/<tournament_id>/participants/<participant_id>/approve', methods=['POST'])
@login_required
def approve_participant(tournament_id, participant_id):
    """Approve a participant for the tournament"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        return jsonify({'success': False, 'error': 'Tournament not found'})
    
    # Check if user is organizer
    if session.get('user_id') != tournament.get('organizer_id'):
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    # Update participant approval status
    result = db.update_participant(participant_id, {'is_approved': True})
    
    if result['success']:
        return jsonify({
            'success': True,
            'message': 'Player approved successfully'
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to approve participant'
        })

@tournament_bp.route('/<tournament_id>/participants/<participant_id>/edit')
@login_required
def edit_participant(tournament_id, participant_id):
    """Edit participant page"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        flash('Tournament not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Check if user is organizer
    if session.get('user_id') != tournament.get('organizer_id'):
        flash('Permission denied', 'error')
        return redirect(url_for('tournament.participants', tournament_id=tournament_id))
    
    # Get participant from database
    participant = db.get_participant_by_id(participant_id)
    if not participant:
        flash('Participant not found', 'error')
        return redirect(url_for('tournament.participants', tournament_id=tournament_id))
    
    return render_template('tournament/edit_participant.html',
                         tournament=tournament,
                         participant=participant)

@tournament_bp.route('/<tournament_id>/participants/<participant_id>/update', methods=['POST'])
@login_required
def update_participant(tournament_id, participant_id):
    """Update a participant in the tournament"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        return jsonify({'success': False, 'error': 'Tournament not found'})
    
    # Check if user is organizer
    if session.get('user_id') != tournament.get('organizer_id'):
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    try:
        # Get form data
        name = request.form.get('name', '').strip()
        gamer_tag = request.form.get('gamer_tag', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        platform = request.form.get('platform', '').strip()
        is_approved = 'is_approved' in request.form
        
        if not name:
            return jsonify({'success': False, 'error': 'Player name is required'})
        
        # Update participant data
        participant_data = {
            'name': name,
            'gamer_tag': gamer_tag,
            'email': email,
            'phone': phone,
            'platform': platform,
            'is_approved': is_approved
        }
        
        # Update participant in database
        result = db.update_participant(participant_id, participant_data)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Player updated successfully',
                'participant': result['participant']
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to update participant')
            })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@tournament_bp.route('/<tournament_id>/participants/<participant_id>/remove', methods=['DELETE'])
@login_required
def remove_participant(tournament_id, participant_id):
    """Remove a participant from the tournament"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        return jsonify({'success': False, 'error': 'Tournament not found'})
    
    # Check if user is organizer
    if session.get('user_id') != tournament.get('organizer_id'):
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    # Remove participant from database
    result = db.delete_participant(participant_id)
    
    if result['success']:
        return jsonify({
            'success': True,
            'message': 'Player removed successfully'
        })
    else:
        return jsonify({
            'success': False,
            'error': result.get('error', 'Failed to remove participant')
        })


def _safe_int(value, default=0):
    """Coerce possibly None or non-numeric values to an int.
    Returns `default` (0) if value is None or not castable to int.
    """
    try:
        if value is None:
            return default
        return int(value)
    except (ValueError, TypeError):
        return default


def calculate_standings(teams, matches, tournament=None):
    """Calculate tournament standings based on scoring system"""
    standings = {}
    scoring_system = tournament.get('scoring_system', 'win_based') if tournament else 'win_based'
    
    # Initialize standings for each team
    for team in teams:
        standings[team['id']] = {
            'team': team,
            'points': 0,
            'matches_played': 0,
            'wins': 0,
            'draws': 0,
            'losses': 0,
            'goals_for': 0,
            'goals_against': 0,
            'goal_difference': 0,
            'clean_sheets': 0,
            'form_guide': []
        }
    
    # Calculate stats from completed matches (exclude tiebreaker matches from regular standings)
    for match in matches:
        if match.get('status') == 'completed' and not match.get('is_tiebreaker', False):
            team1_id = match['team1_id']
            team2_id = match['team2_id']
            team1_score = _safe_int(match.get('team1_score', 0))
            team2_score = _safe_int(match.get('team2_score', 0))
            
            if team1_id in standings and team2_id in standings:
                # Update matches played
                standings[team1_id]['matches_played'] += 1
                standings[team2_id]['matches_played'] += 1
                
                # For team tournaments, the match scores represent the actual goals scored
                # In both win-based and goal-based systems, team1_score/team2_score are the actual goals
                team1_goals = team1_score  # These are the actual goals scored by team1 players
                team2_goals = team2_score  # These are the actual goals scored by team2 players
                
                # Accumulate goals for/against statistics
                standings[team1_id]['goals_for'] += team1_goals
                standings[team1_id]['goals_against'] += team2_goals
                standings[team2_id]['goals_for'] += team2_goals
                standings[team2_id]['goals_against'] += team1_goals
                
                # Update clean sheets based on actual goals
                if team2_goals == 0:
                    standings[team1_id]['clean_sheets'] += 1
                if team1_goals == 0:
                    standings[team2_id]['clean_sheets'] += 1
                
                # Update wins/draws/losses and points based on scoring system
                if scoring_system == 'goal_based':
                    # Goal-based scoring: points = goals scored by team's players
                    standings[team1_id]['points'] += team1_goals
                    standings[team2_id]['points'] += team2_goals
                    
                    # Track wins/draws/losses based on match outcome
                    if team1_goals > team2_goals:
                        standings[team1_id]['wins'] += 1
                        standings[team1_id]['form_guide'].append('W')
                        standings[team2_id]['losses'] += 1
                        standings[team2_id]['form_guide'].append('L')
                    elif team1_goals < team2_goals:
                        standings[team2_id]['wins'] += 1
                        standings[team2_id]['form_guide'].append('W')
                        standings[team1_id]['losses'] += 1
                        standings[team1_id]['form_guide'].append('L')
                    else:
                        standings[team1_id]['draws'] += 1
                        standings[team1_id]['form_guide'].append('D')
                        standings[team2_id]['draws'] += 1
                        standings[team2_id]['form_guide'].append('D')
                else:
                    # Win-based scoring: 3 points for win, 1 for draw
                    # Match outcome determined by total goals scored by each team's players
                    if team1_goals > team2_goals:
                        standings[team1_id]['wins'] += 1
                        standings[team1_id]['points'] += 3
                        standings[team1_id]['form_guide'].append('W')
                        standings[team2_id]['losses'] += 1
                        standings[team2_id]['form_guide'].append('L')
                    elif team1_goals < team2_goals:
                        standings[team2_id]['wins'] += 1
                        standings[team2_id]['points'] += 3
                        standings[team2_id]['form_guide'].append('W')
                        standings[team1_id]['losses'] += 1
                        standings[team1_id]['form_guide'].append('L')
                    else:
                        standings[team1_id]['draws'] += 1
                        standings[team1_id]['points'] += 1
                        standings[team1_id]['form_guide'].append('D')
                        standings[team2_id]['draws'] += 1
                        standings[team2_id]['points'] += 1
                        standings[team2_id]['form_guide'].append('D')
    
    # Calculate goal difference
    for team_id in standings:
        standings[team_id]['goal_difference'] = standings[team_id]['goals_for'] - standings[team_id]['goals_against']
    
    # Sort based on scoring system
    if scoring_system == 'goal_based':
        # Goal-based: sort by total points (goals), then goal difference, then goals for
        sorted_standings = sorted(standings.values(), 
                                key=lambda x: (-x['points'], -x['goal_difference'], -x['goals_for']))
    else:
        # Win-based: sort by match points, then goal difference, then goals for
        sorted_standings = sorted(standings.values(), 
                                key=lambda x: (-x['points'], -x['goal_difference'], -x['goals_for']))
    
    # Add position
    for i, standing in enumerate(sorted_standings):
        standing['position'] = i + 1
    
    return sorted_standings

def calculate_participant_standings(participants, matches):
    """Calculate solo tournament participant standings"""
    standings = {}
    
    # Initialize standings for each participant
    for participant in participants:
        standings[participant['id']] = {
            'participant': participant,
            'position': 0,
            'points': 0,
            'matches_played': 0,
            'wins': 0,
            'draws': 0,
            'losses': 0,
            'goals_for': 0,
            'goals_against': 0,
            'goal_difference': 0,
            'clean_sheets': 0,
            'form_guide': []
        }
    
    # Calculate stats from completed solo matches
    for match in matches:
        if match.get('status') == 'completed':
            p1_id = match['participant1_id']
            p2_id = match['participant2_id']
            p1_score = _safe_int(match.get('participant1_score', 0))
            p2_score = _safe_int(match.get('participant2_score', 0))
            
            if p1_id in standings and p2_id in standings:
                # Update matches played
                standings[p1_id]['matches_played'] += 1
                standings[p2_id]['matches_played'] += 1
                
                # Update goals
                standings[p1_id]['goals_for'] += p1_score
                standings[p1_id]['goals_against'] += p2_score
                standings[p2_id]['goals_for'] += p2_score
                standings[p2_id]['goals_against'] += p1_score
                
                # Update clean sheets
                if p2_score == 0:
                    standings[p1_id]['clean_sheets'] += 1
                if p1_score == 0:
                    standings[p2_id]['clean_sheets'] += 1
                
                # Update wins/draws/losses and points, form
                if p1_score > p2_score:
                    standings[p1_id]['wins'] += 1
                    standings[p1_id]['points'] += 3
                    standings[p1_id]['form_guide'].append('W')
                    standings[p2_id]['losses'] += 1
                    standings[p2_id]['form_guide'].append('L')
                elif p1_score < p2_score:
                    standings[p2_id]['wins'] += 1
                    standings[p2_id]['points'] += 3
                    standings[p2_id]['form_guide'].append('W')
                    standings[p1_id]['losses'] += 1
                    standings[p1_id]['form_guide'].append('L')
                else:
                    standings[p1_id]['draws'] += 1
                    standings[p1_id]['points'] += 1
                    standings[p1_id]['form_guide'].append('D')
                    standings[p2_id]['draws'] += 1
                    standings[p2_id]['points'] += 1
                    standings[p2_id]['form_guide'].append('D')
    
    # Calculate goal difference
    for participant_id in standings:
        standings[participant_id]['goal_difference'] = standings[participant_id]['goals_for'] - standings[participant_id]['goals_against']
    
    # Sort by points, then goal difference, then goals for
    sorted_standings = sorted(standings.values(), 
                            key=lambda x: (-x['points'], -x['goal_difference'], -x['goals_for']))
    
    # Add position
    for i, standing in enumerate(sorted_standings):
        standing['position'] = i + 1
    
    return sorted_standings

def calculate_tournament_statistics(tournament, standings, matches):
    """Calculate comprehensive tournament statistics"""
    stats = {
        'total_matches': len([m for m in matches if m.get('status') == 'completed']),
        'total_goals': 0,
        'avg_goals_per_match': 0,
        'clean_sheets': 0,
        'completion_percentage': 0,
        'win_percentage': 0,
        'draw_percentage': 0,
        'decisive_percentage': 0,
        'total_clean_sheets': 0,
        'avg_match_duration': 90,
        'completed_matches': len([m for m in matches if m.get('status') == 'completed'])
    }
    
    completed_matches = [m for m in matches if m.get('status') == 'completed']
    
    if completed_matches:
        total_goals = 0
        total_draws = 0
        total_clean_sheets = 0
        
        for match in completed_matches:
            if tournament.get('type') == 'solo':
                score1 = match.get('participant1_score', 0)
                score2 = match.get('participant2_score', 0)
            else:
                score1 = match.get('team1_score', 0)
                score2 = match.get('team2_score', 0)
            
            total_goals += score1 + score2
            
            if score1 == score2:
                total_draws += 1
            
            if score1 == 0 or score2 == 0:
                total_clean_sheets += 1
        
        stats['total_goals'] = total_goals
        stats['avg_goals_per_match'] = total_goals / len(completed_matches)
        stats['total_clean_sheets'] = total_clean_sheets
        stats['draw_percentage'] = (total_draws / len(completed_matches)) * 100
        stats['decisive_percentage'] = ((len(completed_matches) - total_draws) / len(completed_matches)) * 100
    
    # Calculate top performers based on tournament type
    if tournament.get('type') == 'solo' and standings:
        # Sort by goals for top scorer
        top_scorer = max(standings, key=lambda x: x['goals_for'], default=None)
        if top_scorer and top_scorer['goals_for'] > 0:
            stats['top_scorer'] = {
                'name': top_scorer['participant']['name'],
                'goals': top_scorer['goals_for'],
                'matches_played': top_scorer['matches_played']
            }
        
        # Best defense (least goals conceded)
        best_defense = min([s for s in standings if s['matches_played'] > 0], 
                          key=lambda x: x['goals_against'], default=None)
        if best_defense:
            stats['best_defense'] = {
                'name': best_defense['participant']['name'],
                'goals_conceded': best_defense['goals_against'],
                'clean_sheets': best_defense['clean_sheets']
            }
        
        # Most wins
        most_wins = max(standings, key=lambda x: x['wins'], default=None)
        if most_wins and most_wins['wins'] > 0:
            win_percentage = (most_wins['wins'] / most_wins['matches_played'] * 100) if most_wins['matches_played'] > 0 else 0
            stats['most_wins'] = {
                'name': most_wins['participant']['name'],
                'wins': most_wins['wins'],
                'win_percentage': win_percentage
            }
    
    elif tournament.get('type') == 'team' and standings:
        # Top scoring team
        top_scoring_team = max(standings, key=lambda x: x['goals_for'], default=None)
        if top_scoring_team and top_scoring_team['goals_for'] > 0:
            goals_per_match = top_scoring_team['goals_for'] / top_scoring_team['matches_played'] if top_scoring_team['matches_played'] > 0 else 0
            stats['top_scoring_team'] = {
                'name': top_scoring_team['team']['name'],
                'goals_for': top_scoring_team['goals_for'],
                'goals_per_match': goals_per_match
            }
        
        # Best defense team
        best_defense_team = min([s for s in standings if s['matches_played'] > 0], 
                               key=lambda x: x['goals_against'], default=None)
        if best_defense_team:
            stats['best_defense_team'] = {
                'name': best_defense_team['team']['name'],
                'goals_against': best_defense_team['goals_against'],
                'clean_sheets': best_defense_team.get('clean_sheets', 0)
            }
        
        # Most successful team
        most_successful_team = max(standings, key=lambda x: x['wins'], default=None)
        if most_successful_team and most_successful_team['wins'] > 0:
            win_percentage = (most_successful_team['wins'] / most_successful_team['matches_played'] * 100) if most_successful_team['matches_played'] > 0 else 0
            stats['most_successful_team'] = {
                'name': most_successful_team['team']['name'],
                'wins': most_successful_team['wins'],
                'win_percentage': win_percentage
            }
    
    # Tournament records
    if completed_matches:
        # Highest scoring match
        highest_scoring = max(completed_matches, 
                            key=lambda x: (x.get('participant1_score', 0) + x.get('participant2_score', 0)) if tournament.get('type') == 'solo' 
                            else (x.get('team1_score', 0) + x.get('team2_score', 0)), default=None)
        if highest_scoring:
            if tournament.get('type') == 'solo':
                total_goals = highest_scoring.get('participant1_score', 0) + highest_scoring.get('participant2_score', 0)
            else:
                total_goals = highest_scoring.get('team1_score', 0) + highest_scoring.get('team2_score', 0)
            stats['highest_scoring_match'] = {'total_goals': total_goals}
        
        # Biggest victory margin
        biggest_victory = max(completed_matches, 
                            key=lambda x: abs((x.get('participant1_score', 0) - x.get('participant2_score', 0))) if tournament.get('type') == 'solo' 
                            else abs((x.get('team1_score', 0) - x.get('team2_score', 0))), default=None)
        if biggest_victory:
            if tournament.get('type') == 'solo':
                margin = abs(biggest_victory.get('participant1_score', 0) - biggest_victory.get('participant2_score', 0))
            else:
                margin = abs(biggest_victory.get('team1_score', 0) - biggest_victory.get('team2_score', 0))
            stats['biggest_victory'] = {'margin': margin}
    
    return stats
