# TournamentPro - Professional Tournament Management Platform

A comprehensive web application for creating, managing, and sharing sports and eSports tournaments. Built with Flask, Supabase, and real-time WebSocket technology.

## 🏆 Features

### Core Features
- **Multiple Tournament Formats**: Round-robin, Knockout, Single/Double elimination, Group stages, Swiss system
- **Real-time Updates**: Live score updates, instant standings, match events via WebSockets
- **Multi-sport Support**: Soccer, Basketball, Volleyball, eSports (MOBA, Battle Royale, etc.)
- **Team & Player Management**: Complete registration system with profiles and statistics
- **Media Gallery**: Upload photos, videos, and documents
- **News System**: Tournament updates and announcements
- **Responsive Design**: Works on all devices (desktop, tablet, mobile)

### Tournament Management
- Automatic fixture generation
- Live match scoring
- Real-time standings calculation
- Match statistics and reports
- Team roster management
- Player statistics tracking
- Printable match reports

### Media & Communication
- Photo and video galleries
- News updates and announcements
- Real-time notifications
- Social media sharing
- Tournament branding
- Sponsor management

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Supabase account (free tier available)
- Git

### 1. Clone the Repository
```bash
git clone <repository-url>
cd tournament-pro
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up Environment Variables
Copy `.env.example` to `.env` and configure:
```bash
cp .env.example .env
```

Edit `.env` file:
```env
# Supabase Configuration
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# Flask Configuration
FLASK_SECRET_KEY=your_very_secret_key_here
FLASK_DEBUG=True

# File Upload Settings
MAX_CONTENT_LENGTH=16777216  # 16MB
UPLOAD_FOLDER=static/uploads

# App Settings
APP_NAME=TournamentPro
APP_VERSION=1.0.0
```

### 5. Set up Supabase Database
1. Create a new project in [Supabase](https://supabase.com)
2. Go to SQL Editor in your Supabase dashboard
3. Copy and run the SQL from `database_schema.sql`
4. Update your `.env` file with the project URL and anon key

### 6. Run the Application
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## 📁 Project Structure

```
tournament-pro/
├── app.py                 # Main Flask application
├── config.py              # Application configuration
├── database.py            # Database connection and operations
├── websocket_events.py    # Real-time WebSocket handlers
├── tournament_generator.py # Tournament fixture generation
├── requirements.txt       # Python dependencies
├── database_schema.sql    # Supabase database schema
├── .env.example          # Environment variables example
├── routes/               # Flask route handlers
│   ├── auth.py          # Authentication routes
│   ├── main.py          # Main application routes
│   ├── tournament.py    # Tournament management
│   ├── match.py         # Match management
│   └── media.py         # Media and file handling
├── templates/           # Jinja2 HTML templates
│   ├── base.html       # Base template
│   ├── index.html      # Homepage
│   ├── auth/           # Authentication templates
│   ├── dashboard/      # Dashboard templates
│   ├── tournament/     # Tournament templates
│   └── ...
└── static/             # Static files
    └── uploads/        # Uploaded media files
```

## 🎮 Usage Guide

### Creating Your First Tournament

1. **Register/Login**: Create an account or log in
2. **Dashboard**: Access your tournament management dashboard
3. **Create Tournament**: Click "Create Tournament" and fill in details:
   - Basic information (name, sport, format)
   - Schedule and limits
   - Rules and settings
4. **Add Teams**: Register teams manually or allow online registration
5. **Generate Fixtures**: Automatically create match schedule
6. **Manage Matches**: Update scores and track progress
7. **Share Results**: Publish standings and match results

### Supported Tournament Formats

- **Round Robin**: Every team plays every other team
- **Single Elimination**: Knockout format, one loss eliminates
- **Double Elimination**: Teams get a second chance in losers bracket
- **Group Stage**: Teams divided into groups, top teams advance
- **Swiss System**: Teams paired based on performance
- **Mixed Format**: Combination of multiple formats

### Sports & Games Supported

#### Traditional Sports
- Soccer/Football
- Futsal
- Basketball
- Volleyball
- Handball
- Tennis
- Table Tennis

#### eSports
- MOBA (League of Legends, Dota 2)
- Battle Royale (Fortnite, PUBG)
- Shooting Games (CS:GO, Valorant)
- Sports Games (FIFA, PES)

## 🔧 Configuration

### Environment Variables
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_ANON_KEY`: Supabase anonymous key
- `FLASK_SECRET_KEY`: Flask session secret key
- `MAX_CONTENT_LENGTH`: Maximum file upload size
- `UPLOAD_FOLDER`: Directory for uploaded files

### Database Configuration
The application uses Supabase (PostgreSQL) as the database. Run the SQL schema in `database_schema.sql` to create all necessary tables.

### File Upload Configuration
- Supported image formats: PNG, JPG, JPEG, GIF, WebP
- Supported video formats: MP4, AVI, MOV, WMV, WebM
- Supported document formats: PDF, DOC, DOCX, TXT
- Maximum file size: 16MB (configurable)

## 🔄 Real-time Features

The application uses WebSocket technology for real-time updates:

- **Live Score Updates**: Scores update instantly across all connected clients
- **Match Events**: Goals, cards, substitutions appear in real-time
- **Standings Updates**: Tournament tables refresh automatically
- **Notifications**: Instant alerts for tournament updates
- **Team Registration**: Real-time notifications when teams join

## 📊 API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `GET /auth/logout` - User logout

### Tournaments
- `POST /tournament/create` - Create tournament
- `GET /tournament/<id>` - View tournament
- `POST /tournament/<id>/add-team` - Add team
- `POST /tournament/<id>/generate-fixtures` - Generate matches

### Matches
- `GET /match/<id>` - View match details
- `POST /match/<id>/score` - Update match score
- `POST /match/<id>/event` - Add match event

### Media
- `POST /media/upload/<tournament_id>` - Upload media files
- `GET /media/gallery/<tournament_id>` - View media gallery

## 🚀 Deployment

### Local Development
```bash
python app.py
```

### Production Deployment
1. Set `FLASK_DEBUG=False` in environment
2. Use a production WSGI server like Gunicorn:
```bash
pip install gunicorn
gunicorn -w 4 -k eventlet app:app
```

### Docker Deployment
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "4", "-k", "eventlet", "app:app", "--bind", "0.0.0.0:5000"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -am 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Create Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Check this README and code comments
- **Issues**: Report bugs and request features via GitHub Issues
- **Community**: Join our Discord server for discussions

## 🏗️ Development Roadmap

### Phase 1 (Current)
- ✅ Basic tournament management
- ✅ Real-time score updates
- ✅ Multi-format support
- ✅ Media gallery
- ✅ Responsive design

### Phase 2 (Planned)
- 🔄 Mobile app (React Native)
- 🔄 Advanced statistics
- 🔄 Tournament broadcasting
- 🔄 Payment integration
- 🔄 Multi-language support

### Phase 3 (Future)
- 📋 AI-powered bracket predictions
- 📋 Advanced analytics dashboard
- 📋 Tournament streaming integration
- 📋 Sponsor management system
- 📋 Mobile notifications

## 🎯 Key Features Comparison

| Feature | TournamentPro | Competitors |
|---------|---------------|-------------|
| Real-time Updates | ✅ WebSocket | ❌ Manual refresh |
| Multi-format Support | ✅ 6+ formats | ⚠️ Limited |
| eSports Support | ✅ Full support | ❌ Traditional only |
| Mobile Responsive | ✅ Fully responsive | ⚠️ Partial |
| Free Tier | ✅ Full featured | ❌ Very limited |
| Open Source | ✅ MIT License | ❌ Proprietary |

---

**Built with ❤️ for the tournament community**

For more information, visit our website or contact our support team.
