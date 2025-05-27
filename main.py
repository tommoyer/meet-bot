import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from urllib.parse import parse_qs

from flask import Flask, request, jsonify, Response
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/meet-bot/meet-bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
CONFIG = {
    'port': int(os.environ.get('PORT', 8080)),
    'host': os.environ.get('HOST', '0.0.0.0'),
    'mattermost_token': os.environ.get('MATTERMOST_TOKEN'),
    'service_account_file': os.environ.get('GOOGLE_SERVICE_ACCOUNT_FILE', '/etc/meet-bot/service-account.json'),
    'oauth_credentials_file': os.environ.get('GOOGLE_OAUTH_FILE', '/etc/meet-bot/oauth-credentials.json'),
    'debug': os.environ.get('DEBUG', 'false').lower() == 'true'
}


class GoogleMeetService:
    """Service class to handle Google Meet creation via Calendar API."""
    
    def __init__(self):
        self.credentials = None
        self.calendar_service = None
        self._initialize_credentials()
    
    def _initialize_credentials(self):
        """Initialize Google API credentials."""
        try:
            # Try service account first
            if os.path.exists(CONFIG['service_account_file']):
                logger.info("Using service account credentials")
                self.credentials = ServiceAccountCredentials.from_service_account_file(
                    CONFIG['service_account_file'],
                    scopes=[
                        'https://www.googleapis.com/auth/calendar',
                        'https://www.googleapis.com/auth/calendar.events'
                    ]
                )
            # Fall back to OAuth credentials
            elif os.path.exists(CONFIG['oauth_credentials_file']):
                logger.info("Using OAuth credentials")
                self.credentials = Credentials.from_authorized_user_file(
                    CONFIG['oauth_credentials_file']
                )
                if not self.credentials.valid:
                    if self.credentials.expired and self.credentials.refresh_token:
                        self.credentials.refresh(GoogleRequest())
            else:
                raise Exception("No valid credentials found")
            
            # Initialize the Calendar API service
            self.calendar_service = build('calendar', 'v3', credentials=self.credentials)
            logger.info("Google Calendar service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google credentials: {e}")
            raise
    
    def create_instant_meet(self, title: str = "Quick Meeting") -> Optional[str]:
        """
        Create an instant Google Meet using Calendar API.
        Creates a calendar event starting now with minimal duration.
        
        Args:
            title: Meeting title
            
        Returns:
            The Google Meet URL or None if creation fails
        """
        try:
            # Create an event starting now with 5-minute duration (minimum for Meet link generation)
            start_time = datetime.utcnow()
            end_time = start_time + timedelta(minutes=5)
            
            return self._create_calendar_event_with_meet(title, start_time, end_time)
            
        except Exception as error:
            logger.error(f"Error creating instant Meet: {error}")
            return None
    
    def create_scheduled_meet(self, title: str, duration_minutes: int = 60) -> Optional[str]:
        """
        Create a scheduled Google Meet using Calendar API.
        
        Args:
            title: Meeting title
            duration_minutes: Meeting duration in minutes
            
        Returns:
            The Google Meet URL or None if creation fails
        """
        try:
            start_time = datetime.utcnow()
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            return self._create_calendar_event_with_meet(title, start_time, end_time)
            
        except Exception as error:
            logger.error(f"Error creating scheduled Meet: {error}")
            return None
    
    def _create_calendar_event_with_meet(self, title: str, start_time: datetime, end_time: datetime) -> Optional[str]:
        """
        Create a Google Calendar event with Google Meet integration.
        
        Args:
            title: Meeting title
            start_time: Meeting start time
            end_time: Meeting end time
            
        Returns:
            The Google Meet URL or None if creation fails
        """
        try:
            # Generate a unique request ID to prevent duplicate conference creation
            request_id = f'meet-{int(start_time.timestamp())}-{int(time.time() * 1000) % 10000}'
            
            # Create calendar event with Google Meet
            event = {
                'summary': title,
                'description': f'Meeting created via Meet Bot at {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC',
                'start': {
                    'dateTime': start_time.isoformat() + 'Z',
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_time.isoformat() + 'Z',
                    'timeZone': 'UTC',
                },
                'conferenceData': {
                    'createRequest': {
                        'requestId': request_id,
                        'conferenceSolutionKey': {
                            'type': 'hangoutsMeet'
                        }
                    }
                },
                'attendees': [],  # Empty attendees list - anyone with link can join
                'guestsCanInviteOthers': True,
                'guestsCanSeeOtherGuests': True
            }
            
            logger.info(f"Creating calendar event with Meet: {title}")
            
            # Insert the event with conference data
            created_event = self.calendar_service.events().insert(
                calendarId='primary',
                body=event,
                conferenceDataVersion=1,
                sendUpdates='none'  # Don't send email notifications
            ).execute()
            
            logger.info(f"Calendar event created: {created_event.get('id')}")
            
            # Extract Google Meet link
            conference_data = created_event.get('conferenceData', {})
            entry_points = conference_data.get('entryPoints', [])
            
            for entry_point in entry_points:
                if entry_point.get('entryPointType') == 'video':
                    meet_url = entry_point.get('uri')
                    logger.info(f"Successfully created Google Meet: {meet_url}")
                    return meet_url
            
            # Fallback: look for hangoutLink in the event
            hangout_link = created_event.get('hangoutLink')
            if hangout_link:
                logger.info(f"Found hangout link: {hangout_link}")
                return hangout_link
            
            logger.error("No Google Meet link found in created event")
            return None
            
        except HttpError as error:
            logger.error(f"Google Calendar API error: {error}")
            if error.resp.status == 403:
                logger.error("Permission denied. Check that Calendar API is enabled and credentials are correct.")
            elif error.resp.status == 404:
                logger.error("Calendar not found. Make sure you're using the correct calendar ID.")
            return None
        except Exception as error:
            logger.error(f"Unexpected error creating Meet via Calendar API: {error}")
            return None


# Initialize Google Meet service
try:
    meet_service = GoogleMeetService()
except Exception as e:
    logger.error(f"Failed to initialize Google Meet service: {e}")
    meet_service = None


def verify_mattermost_token(token: str) -> bool:
    """Verify the Mattermost slash command token."""
    if not CONFIG['mattermost_token']:
        logger.warning("No Mattermost token configured - accepting all requests")
        return True
    return token == CONFIG['mattermost_token']


def parse_slash_command_args(text: str) -> Dict[str, Any]:
    """
    Parse slash command arguments.
    
    Examples:
    /meet
    /meet title="Daily Standup"
    /meet title="Team Meeting" duration=90
    /meet quick
    """
    args = {
        'title': None,
        'duration': 60,  # default duration in minutes
        'quick': False
    }
    
    if not text.strip():
        return args
    
    # Handle quick meeting shortcut
    if text.strip().lower() == 'quick':
        args['quick'] = True
        args['title'] = 'Quick Meeting'
        args['duration'] = 30
        return args
    
    # Parse key=value pairs and quoted strings
    import re
    
    # Match title="value" or title='value'
    title_match = re.search(r'title=["\']([^"\']*)["\']', text)
    if title_match:
        args['title'] = title_match.group(1)
    
    # Match duration=number
    duration_match = re.search(r'duration=(\d+)', text)
    if duration_match:
        args['duration'] = int(duration_match.group(1))
    
    # If no title specified but there's text, use it as title
    if not args['title'] and text.strip() and not duration_match:
        # Remove any duration arguments and use remaining text as title
        clean_text = re.sub(r'duration=\d+', '', text).strip()
        if clean_text:
            args['title'] = clean_text
    
    return args


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'google_meet_service': meet_service is not None,
        'version': '1.0.1'
    }
    return jsonify(status)


@app.route('/meet', methods=['POST'])
def handle_meet_command():
    """Handle Mattermost slash command for creating Google Meet links."""
    try:
        # Verify content type
        if request.content_type != 'application/x-www-form-urlencoded':
            logger.warning(f"Invalid content type: {request.content_type}")
            return jsonify({'text': 'Invalid request format'}), 400
        
        # Parse form data
        data = request.form.to_dict()
        logger.info(f"Received slash command data: {data}")
        
        # Verify Mattermost token
        token = data.get('token')
        if not verify_mattermost_token(token):
            logger.warning(f"Invalid Mattermost token received")
            return jsonify({'text': 'Unauthorized'}), 401
        
        # Check if Google Meet service is available
        if not meet_service:
            return jsonify({
                'response_type': 'ephemeral',
                'text': '❌ Google Meet service is not available. Please check the server configuration.'
            })
        
        # Parse command arguments
        command_text = data.get('text', '').strip()
        args = parse_slash_command_args(command_text)
        
        # Extract user info
        user_name = data.get('user_name', 'Unknown User')
        channel_name = data.get('channel_name', 'Direct Message')
        
        # Generate meeting title if not provided
        if not args['title']:
            if channel_name and channel_name != 'directmessage':
                args['title'] = f"{channel_name} Meeting"
            else:
                args['title'] = f"Meeting by {user_name}"
        
        # Create Google Meet link
        logger.info(f"Creating Google Meet: title='{args['title']}', duration={args['duration']}, quick={args['quick']}")
        
        if args['quick']:
            # For quick meetings, create instant meet
            meet_url = meet_service.create_instant_meet(args['title'])
        else:
            # For regular meetings, create scheduled meet
            meet_url = meet_service.create_scheduled_meet(args['title'], args['duration'])
        
        if meet_url:
            # Create success response
            response_text = f"🎥 **Google Meet Created**\n"
            response_text += f"**Meeting:** {args['title']}\n"
            response_text += f"**Link:** {meet_url}\n"
            if not args['quick']:
                response_text += f"**Duration:** {args['duration']} minutes\n"
            response_text += f"**Created by:** @{user_name}"
            
            logger.info(f"Successfully created Google Meet for user {user_name}: {meet_url}")
            
            return jsonify({
                'response_type': 'in_channel',
                'text': response_text
            })
        else:
            # Error response
            logger.error(f"Failed to create Google Meet for user {user_name}")
            return jsonify({
                'response_type': 'ephemeral',
                'text': '❌ Failed to create Google Meet link. Please check the logs or contact your administrator.'
            })
    
    except Exception as e:
        logger.error(f"Error handling meet command: {e}", exc_info=True)
        return jsonify({
            'response_type': 'ephemeral',
            'text': f'❌ An error occurred: {str(e)}'
        }), 500


@app.route('/meet-help', methods=['POST'])
def handle_help_command():
    """Handle help command for the Meet bot."""
    help_text = """
🎥 **Google Meet Bot Help**

**Commands:**
• `/meet` - Create a meeting for this channel/conversation
• `/meet quick` - Create a 30-minute quick meeting  
• `/meet title="Meeting Name"` - Create a meeting with custom title
• `/meet title="Weekly Standup" duration=90` - Create a 90-minute meeting
• `/meet-help` - Show this help message

**Examples:**
• `/meet` - Creates meeting named after current channel
• `/meet title="Daily Standup"` - Creates "Daily Standup" meeting (60 min)
• `/meet title="Client Call" duration=30` - Creates 30-minute "Client Call"
• `/meet quick` - Creates instant 30-minute meeting

**Notes:**
• All meetings are created as Google Calendar events with Meet links
• Meeting links are shared in the channel where the command was used
• Duration is in minutes (default: 60 minutes for regular, 30 for quick)
• Anyone with the link can join the meeting
"""
    
    return jsonify({
        'response_type': 'ephemeral',
        'text': help_text
    })


if __name__ == '__main__':
    logger.info(f"Starting Google Meet Bot server on {CONFIG['host']}:{CONFIG['port']}")
    logger.info(f"Debug mode: {CONFIG['debug']}")
    logger.info(f"Google Meet service available: {meet_service is not None}")
    
    app.run(
        host=CONFIG['host'],
        port=CONFIG['port'],
        debug=CONFIG['debug'],
        threaded=True
    )