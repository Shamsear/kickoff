"""
Context processors to inject global data into all templates
"""
from flask import session, request
from routes.auth import get_current_user
from database import db
from datetime import datetime, timedelta
import uuid

def navigation_context():
    """Inject navigation-related context into all templates"""
    context = {
        'nav_user': None,
        'nav_notifications': [],
        'nav_recent_tournaments': [],
        'nav_unread_count': 0,
        'nav_current_path': request.endpoint or '',
    }
    
    # Get current user data if logged in
    if session.get('user_id'):
        try:
            user = get_current_user()
            if user:
                context['nav_user'] = user
                
                # Get user's recent tournaments (last 5)
                tournaments = db.get_tournaments_by_user(session['user_id'])
                recent_tournaments = []
                
                for tournament in tournaments[:5]:  # Limit to 5 most recent
                    recent_tournaments.append({
                        'id': tournament.get('id'),
                        'name': tournament.get('name'),
                        'status': tournament.get('status', 'draft'),
                        'created_at': tournament.get('created_at')
                    })
                
                context['nav_recent_tournaments'] = recent_tournaments
                
                # Get real notifications (you can expand this based on your notification system)
                notifications = get_user_notifications(session['user_id'])
                context['nav_notifications'] = notifications
                context['nav_unread_count'] = len([n for n in notifications if n.get('unread', False)])
                
        except Exception as e:
            print(f"Error loading navigation context: {e}")
    
    return context

def get_user_notifications(user_id):
    """Get real notifications for a user"""
    try:
        # For now, we'll create some sample notifications based on real user data
        # In a real app, you'd query a notifications table
        notifications = []
        
        # Get user's tournaments to generate relevant notifications
        tournaments = db.get_tournaments_by_user(user_id)
        
        if tournaments:
            # Create notifications based on tournament activity
            for tournament in tournaments[:3]:  # Limit to avoid too many notifications
                status = tournament.get('status', 'draft')
                
                if status == 'registration_open':
                    notifications.append({
                        'id': f"notif_{tournament.get('id', '')}_reg",
                        'title': 'Registration Active',
                        'message': f"Players are registering for '{tournament.get('name', 'Tournament')}'",
                        'time': get_time_ago(tournament.get('updated_at', tournament.get('created_at'))),
                        'unread': True,
                        'type': 'tournament',
                        'tournament_id': tournament.get('id')
                    })
                    
                elif status == 'in_progress':
                    notifications.append({
                        'id': f"notif_{tournament.get('id', '')}_progress",
                        'title': 'Tournament Active',
                        'message': f"'{tournament.get('name', 'Tournament')}' is currently in progress",
                        'time': get_time_ago(tournament.get('updated_at', tournament.get('created_at'))),
                        'unread': False,
                        'type': 'tournament',
                        'tournament_id': tournament.get('id')
                    })
                    
                elif status == 'completed':
                    notifications.append({
                        'id': f"notif_{tournament.get('id', '')}_complete",
                        'title': 'Tournament Completed',
                        'message': f"'{tournament.get('name', 'Tournament')}' has finished",
                        'time': get_time_ago(tournament.get('updated_at', tournament.get('created_at'))),
                        'unread': False,
                        'type': 'tournament',
                        'tournament_id': tournament.get('id')
                    })
        
        # Add some system notifications if no tournaments
        if not notifications:
            notifications = [
                {
                    'id': 'welcome_' + str(uuid.uuid4())[:8],
                    'title': 'Welcome to TournamentPro',
                    'message': 'Create your first tournament to get started',
                    'time': '1 hour ago',
                    'unread': True,
                    'type': 'system'
                }
            ]
            
        # Sort by unread first, then by time (most recent first)
        notifications.sort(key=lambda x: (not x.get('unread', False), x.get('time', '')))
        
        return notifications[:10]  # Limit to 10 notifications
        
    except Exception as e:
        print(f"Error getting notifications: {e}")
        return []

def get_time_ago(timestamp_str):
    """Convert timestamp to human-readable time ago format"""
    try:
        if not timestamp_str:
            return "Just now"
            
        # Parse the timestamp
        if 'T' in timestamp_str:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            dt = datetime.fromisoformat(timestamp_str)
            
        # Remove timezone info for comparison if present
        if dt.tzinfo:
            dt = dt.replace(tzinfo=None)
            
        now = datetime.now()
        diff = now - dt
        
        if diff.days > 7:
            return f"{diff.days // 7} week{'s' if diff.days // 7 > 1 else ''} ago"
        elif diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"
            
    except Exception as e:
        print(f"Error parsing timestamp {timestamp_str}: {e}")
        return "Recently"

def search_context():
    """Inject search-related context"""
    return {
        'search_query': request.args.get('q', ''),
    }

def breadcrumb_helpers():
    """Helper functions for breadcrumbs"""
    return {
        'get_breadcrumbs': get_breadcrumbs_for_route
    }

def get_breadcrumbs_for_route():
    """Generate breadcrumbs based on current route"""
    breadcrumbs = []
    endpoint = request.endpoint
    
    if not endpoint:
        return breadcrumbs
    
    # Define breadcrumb patterns
    if endpoint.startswith('main.dashboard'):
        breadcrumbs = [{'name': 'Dashboard'}]
        
    elif endpoint.startswith('tournament.'):
        breadcrumbs.append({'name': 'Tournaments', 'url': '/explore'})
        
        if 'create' in endpoint:
            breadcrumbs.append({'name': 'Create Tournament'})
        elif 'edit' in endpoint:
            breadcrumbs.append({'name': 'Edit Tournament'})
        elif 'view' in endpoint:
            # You might want to get the actual tournament name here
            tournament_id = request.view_args.get('tournament_id')
            if tournament_id:
                tournament = db.get_tournament_by_id(tournament_id)
                if tournament:
                    breadcrumbs.append({
                        'name': tournament.get('name', 'Tournament Details'),
                        'url': f'/tournament/{tournament_id}'
                    })
                    
                    # Add specific pages
                    if 'participants' in endpoint:
                        breadcrumbs.append({'name': 'Participants'})
                    elif 'matches' in endpoint:
                        breadcrumbs.append({'name': 'Matches'})
                    elif 'standings' in endpoint:
                        breadcrumbs.append({'name': 'Standings'})
                        
    elif endpoint.startswith('auth.'):
        if 'profile' in endpoint:
            breadcrumbs = [{'name': 'Profile'}]
        elif 'login' in endpoint:
            breadcrumbs = [{'name': 'Sign In'}]
        elif 'register' in endpoint:
            breadcrumbs = [{'name': 'Sign Up'}]
            
    elif endpoint.startswith('main.explore'):
        breadcrumbs = [{'name': 'Explore Tournaments'}]
        
    elif endpoint.startswith('main.features'):
        breadcrumbs = [{'name': 'Features'}]
        
    elif endpoint.startswith('main.about'):
        breadcrumbs = [{'name': 'About'}]
        
    elif endpoint.startswith('main.contact'):
        breadcrumbs = [{'name': 'Contact'}]
    
    return breadcrumbs
