import requests
from config import Config
from models import db, Game
from datetime import datetime

class RAWGClient:
    """Client for interacting with RAWG Video Games Database API"""
    
    # Platform mapping: User selection -> RAWG platform ID
    PLATFORM_MAP = {
        'Steam': 4,  # PC
        'Xbox Series X|S': 186,  # Xbox Series X/S
        'PlayStation 5': 187,  # PlayStation 5
        'Nintendo Switch': 7  # Nintendo Switch
    }
    
    # Genre mapping: User selection -> RAWG genre slug
    GENRE_MAP = {
        'RPG': 'role-playing-games-rpg',
        'Shooter': 'shooter',
        'Platformer': 'platformer',
        'Metroidvania': 'metroidvania',
        'Action': 'action'
    }
    
    def __init__(self, api_key=None):
        self.api_key = api_key or Config.RAWG_API_KEY
        self.base_url = Config.RAWG_API_BASE_URL
    
    def _make_request(self, endpoint, params=None):
        """Make a request to the RAWG API"""
        if params is None:
            params = {}
        params['key'] = self.api_key
        
        try:
            response = requests.get(f"{self.base_url}/{endpoint}", params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return None
    
    def get_games_by_platform_and_genre(self, platform, genre, page_size=20):
        """Fetch games from RAWG API filtered by platform and genre"""
        platform_id = self.PLATFORM_MAP.get(platform)
        genre_slug = self.GENRE_MAP.get(genre)
        
        if not platform_id or not genre_slug:
            return []
        
        params = {
            'platforms': platform_id,
            'genres': genre_slug,
            'page_size': page_size,
            'ordering': '-rating'  # Sort by rating descending
        }
        
        data = self._make_request('games', params)
        if not data or 'results' not in data:
            return []
        
        games = []
        for game_data in data['results']:
            # Extract platform name from the game data
            platform_name = platform  # Use the user's selection
            
            # Extract genre from the game data
            genre_name = genre  # Use the user's selection
            
            # Get rating (RAWG uses 0-5 scale, convert to 0-100)
            rating = game_data.get('rating', 0) * 20  # Convert 0-5 to 0-100
            
            # Try to get Metacritic score if available (already 0-100)
            if game_data.get('metacritic'):
                rating = game_data.get('metacritic')
            
            game_info = {
                'rawg_id': game_data.get('id'),
                'title': game_data.get('name', 'Unknown'),
                'platform': platform_name,
                'genre': genre_name,
                'rating': rating,
                'image_url': game_data.get('background_image', ''),
                'description': game_data.get('description_raw', '')[:500]  # Limit description length
            }
            games.append(game_info)
        
        return games
    
    def cache_games_to_database(self, games):
        """Store fetched games in the database cache"""
        cached_count = 0
        for game_info in games:
            # Check if game already exists
            existing_game = Game.query.filter_by(
                rawg_id=game_info['rawg_id'],
                platform=game_info['platform'],
                genre=game_info['genre']
            ).first()
            
            if not existing_game:
                game = Game(
                    rawg_id=game_info['rawg_id'],
                    title=game_info['title'],
                    platform=game_info['platform'],
                    genre=game_info['genre'],
                    rating=game_info['rating'],
                    image_url=game_info['image_url'],
                    description=game_info.get('description', '')
                )
                db.session.add(game)
                cached_count += 1
        
        try:
            db.session.commit()
            return cached_count
        except Exception as e:
            db.session.rollback()
            print(f"Error caching games: {e}")
            return 0
    
    def get_cached_games(self, platform, genre, limit=20):
        """Retrieve games from database cache"""
        games = Game.query.filter_by(
            platform=platform,
            genre=genre
        ).order_by(Game.rating.desc()).limit(limit).all()
        
        return [{
            'rawg_id': g.rawg_id,
            'title': g.title,
            'platform': g.platform,
            'genre': g.genre,
            'rating': g.rating,
            'image_url': g.image_url,
            'description': g.description
        } for g in games]


