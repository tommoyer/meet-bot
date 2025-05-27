# ... (previous code above unchanged)

@app.route('/meet', methods=['POST'])
def handle_meet_command():
    """Handle Mattermost slash command for creating Google Meet links or help."""
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

        # Parse command arguments
        command_text = data.get('text', '').strip()

        # If the user types "/meet help" (case-insensitive, allow extra whitespace)
        if command_text.lower() == "help":
            help_text = """
🎥 **Google Meet Bot Help**

**Commands:**
• `/meet` - Create a meeting for this channel/conversation
• `/meet quick` - Create a 30-minute quick meeting  
• `/meet title="Meeting Name"` - Create a meeting with custom title
• `/meet title="Weekly Standup" duration=90` - Create a 90-minute meeting
• `/meet help` - Show this help message

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

        # Check if Google Meet service is available
        if not meet_service:
            return jsonify({
                'response_type': 'ephemeral',
                'text': '❌ Google Meet service is not available. Please check the server configuration.'
            })

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

# Remove the /meet-help endpoint if present