# Hospitality Booking Bot

A smart AI-powered bot for handling hospitality bookings, cancellations, and customer inquiries using OpenAI's GPT model.

## Features

- 🤖 **AI-Powered Conversations**: Natural language processing for customer interactions
- 📅 **Booking Management**: Create, modify, and cancel reservations
- 🏨 **Hospitality Focus**: Specialized for hotels, restaurants, and events
- 💬 **Smart Responses**: Context-aware responses using OpenAI GPT-3.5-turbo
- 🔍 **Booking Lookup**: Find and view booking details by ID
- 📊 **Booking Analytics**: List and manage all bookings

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Get OpenAI API Key**:
   - Visit [OpenAI Platform](https://platform.openai.com/api-keys)
   - Create a new API key
   - Set it as an environment variable:
     ```bash
     # Windows
     set OPENAI_API_KEY=your_api_key_here
     
     # macOS/Linux
     export OPENAI_API_KEY=your_api_key_here
     ```

3. **Run the Bot**:
   ```bash
   python Index.py
   ```

## Usage Examples

### Making a Booking
```
You: I'd like to book a table for 4 people on December 25th at 7 PM
Bot: Booking created successfully! Booking ID: BK0001
```

### Cancelling a Booking
```
You: I need to cancel booking BK0001
Bot: Booking BK0001 has been cancelled successfully.
```

### Viewing Booking Details
```
You: Show me details for BK0001
Bot: Booking Details for BK0001: [detailed information]
```

### General Inquiries
```
You: What are your operating hours?
Bot: [AI-generated response about operating hours]
```

## Bot Capabilities

- **Natural Language Understanding**: Handles various ways of expressing requests
- **Booking ID Recognition**: Automatically detects booking IDs in conversations
- **Context Awareness**: Maintains conversation context for better responses
- **Error Handling**: Graceful handling of API errors and invalid requests
- **Data Extraction**: Automatically extracts booking information from natural language

## Technical Details

- **Language**: Python 3.7+
- **AI Model**: OpenAI GPT-3.5-turbo
- **Storage**: In-memory (easily replaceable with database)
- **Architecture**: Object-oriented design with modular functions

## Customization

The bot can be easily customized for different hospitality businesses:
- Modify the system prompt for specific business needs
- Add database integration for persistent storage
- Implement additional booking types (rooms, events, etc.)
- Add payment processing integration
- Connect to existing booking systems

## License

This project is licensed under the MIT License - see the LICENSE file for details.
get weather updates 
