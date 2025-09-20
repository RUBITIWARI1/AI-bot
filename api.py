"""
FastAPI REST API for Hospitality Booking Bot
Provides endpoints for frontend integration
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from typing import Dict, Any
import uuid
from datetime import datetime

from config import Config
from monitoring import MonitoringManager
from booking_manager import BookingManager
from ai_service import AIService
from api_models import (
    ChatRequest, ChatResponse, BookingRequest, BookingResponse,
    BookingListResponse, SearchRequest, StatsResponse, HealthResponse,
    BookingDetails
)

# Initialize FastAPI app
app = FastAPI(
    title="Hospitality Booking Bot API",
    description="AI-powered booking system for hospitality businesses",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global bot instance
bot_instance = None
sessions = {}  # Simple session storage (use Redis in production)


def get_bot():
    """Dependency to get bot instance"""
    global bot_instance
    if bot_instance is None:
        try:
            config = Config()
            monitoring = MonitoringManager()
            bot_instance = {
                'config': config,
                'monitoring': monitoring,
                'booking_manager': BookingManager(monitoring),
                'ai_service': AIService(config, monitoring)
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to initialize bot: {str(e)}")
    return bot_instance


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint with basic info"""
    return HealthResponse(
        status="healthy",
        services={
            "api": "running",
            "bot": "initialized" if bot_instance else "not_initialized"
        }
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        bot = get_bot()
        return HealthResponse(
            status="healthy",
            services={
                "api": "running",
                "bot": "initialized",
                "openai": "connected" if bot['ai_service'].openai_config['api_key'] else "not_configured",
                "monitoring": "enabled" if bot['monitoring'] else "disabled"
            }
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            services={
                "api": "running",
                "bot": "error",
                "error": str(e)
            }
        )


@app.post("/chat", response_model=ChatResponse)
async def chat_with_bot(request: ChatRequest, bot: Dict[str, Any] = Depends(get_bot)):
    """Main chat endpoint for frontend integration"""
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Track the chat request
        bot['monitoring'].track_event('ChatRequest', {
            'session_id': session_id,
            'message_length': len(request.message),
            'has_user_id': bool(request.user_id)
        })
        
        # Process the user input
        response_text = bot['booking_manager'].process_user_input(request.message)
        
        # Store session info
        if session_id not in sessions:
            sessions[session_id] = {
                'created_at': datetime.now(),
                'message_count': 0
            }
        sessions[session_id]['message_count'] += 1
        sessions[session_id]['last_activity'] = datetime.now()
        
        return ChatResponse(
            response=response_text,
            session_id=session_id,
            success=True
        )
        
    except Exception as e:
        bot['monitoring'].track_error(e, {
            'operation': 'chat',
            'session_id': request.session_id,
            'user_id': request.user_id
        })
        return ChatResponse(
            response="I'm sorry, I encountered an error processing your request. Please try again.",
            session_id=request.session_id,
            success=False,
            error=str(e)
        )


@app.post("/bookings", response_model=BookingResponse)
async def create_booking(request: BookingRequest, bot: Dict[str, Any] = Depends(get_bot)):
    """Create a new booking directly"""
    try:
        # Convert request to booking data
        booking_data = {
            'name': request.name,
            'contact': request.contact,
            'date': request.date,
            'time': request.time,
            'guests': str(request.guests),
            'special_requirements': request.special_requirements or ''
        }
        
        # Create the booking
        result = bot['booking_manager'].create_booking(booking_data)
        
        # Extract booking ID from result if successful
        booking_id = None
        if "Booking created successfully" in result:
            # Find the booking ID in the response
            import re
            match = re.search(r'BK\d{4}', result)
            if match:
                booking_id = match.group()
        
        return BookingResponse(
            booking_id=booking_id,
            success="Booking created successfully" in result,
            message=result,
            booking_data=bot['booking_manager'].bookings.get(booking_id) if booking_id else None
        )
        
    except Exception as e:
        bot['monitoring'].track_error(e, {
            'operation': 'create_booking',
            'booking_data': request.dict()
        })
        return BookingResponse(
            success=False,
            message=f"Error creating booking: {str(e)}",
            error=str(e)
        )


@app.get("/bookings", response_model=BookingListResponse)
async def list_bookings(
    status: str = None,
    date: str = None,
    bot: Dict[str, Any] = Depends(get_bot)
):
    """List all bookings with optional filtering"""
    try:
        # Get bookings from manager
        bookings_dict = bot['booking_manager'].bookings
        
        # Convert to response format
        bookings = []
        for booking_id, details in bookings_dict.items():
            # Apply filters
            if status and details.get('status', '').lower() != status.lower():
                continue
            if date and details.get('date', '') != date:
                continue
                
            bookings.append(BookingDetails(
                booking_id=booking_id,
                name=details.get('name', ''),
                contact=details.get('contact', ''),
                date=details.get('date', ''),
                time=details.get('time', ''),
                guests=details.get('guests', 0),
                special_requirements=details.get('special_requirements', ''),
                status=details.get('status', ''),
                created_at=details.get('created_at', ''),
                modified_at=details.get('modified_at'),
                cancelled_at=details.get('cancelled_at')
            ))
        
        return BookingListResponse(
            bookings=bookings,
            total_count=len(bookings)
        )
        
    except Exception as e:
        bot['monitoring'].track_error(e, {
            'operation': 'list_bookings'
        })
        return BookingListResponse(
            bookings=[],
            total_count=0,
            success=False,
            error=str(e)
        )


@app.get("/bookings/{booking_id}", response_model=BookingResponse)
async def get_booking(booking_id: str, bot: Dict[str, Any] = Depends(get_bot)):
    """Get details of a specific booking"""
    try:
        if booking_id not in bot['booking_manager'].bookings:
            return BookingResponse(
                success=False,
                message=f"Booking {booking_id} not found",
                error="Booking not found"
            )
        
        details = bot['booking_manager'].bookings[booking_id]
        return BookingResponse(
            booking_id=booking_id,
            success=True,
            message="Booking details retrieved successfully",
            booking_data=details
        )
        
    except Exception as e:
        bot['monitoring'].track_error(e, {
            'operation': 'get_booking',
            'booking_id': booking_id
        })
        return BookingResponse(
            success=False,
            message=f"Error retrieving booking: {str(e)}",
            error=str(e)
        )


@app.delete("/bookings/{booking_id}", response_model=BookingResponse)
async def cancel_booking(booking_id: str, bot: Dict[str, Any] = Depends(get_bot)):
    """Cancel a booking"""
    try:
        result = bot['booking_manager'].cancel_booking(booking_id)
        return BookingResponse(
            booking_id=booking_id,
            success="cancelled successfully" in result.lower(),
            message=result
        )
        
    except Exception as e:
        bot['monitoring'].track_error(e, {
            'operation': 'cancel_booking',
            'booking_id': booking_id
        })
        return BookingResponse(
            success=False,
            message=f"Error cancelling booking: {str(e)}",
            error=str(e)
        )


@app.post("/bookings/search", response_model=BookingListResponse)
async def search_bookings(request: SearchRequest, bot: Dict[str, Any] = Depends(get_bot)):
    """Search bookings by query"""
    try:
        result = bot['booking_manager'].search_bookings(request.query)
        
        # Parse the search result to extract bookings
        bookings = []
        if "Search Results" in result:
            lines = result.split('\n')[1:]  # Skip header
            for line in lines:
                if line.strip() and ':' in line:
                    # Extract booking ID from line
                    booking_id = line.split(':')[0].split()[-1]
                    if booking_id in bot['booking_manager'].bookings:
                        details = bot['booking_manager'].bookings[booking_id]
                        bookings.append(BookingDetails(
                            booking_id=booking_id,
                            name=details.get('name', ''),
                            contact=details.get('contact', ''),
                            date=details.get('date', ''),
                            time=details.get('time', ''),
                            guests=details.get('guests', 0),
                            special_requirements=details.get('special_requirements', ''),
                            status=details.get('status', ''),
                            created_at=details.get('created_at', ''),
                            modified_at=details.get('modified_at'),
                            cancelled_at=details.get('cancelled_at')
                        ))
        
        return BookingListResponse(
            bookings=bookings,
            total_count=len(bookings)
        )
        
    except Exception as e:
        bot['monitoring'].track_error(e, {
            'operation': 'search_bookings',
            'query': request.query
        })
        return BookingListResponse(
            bookings=[],
            total_count=0,
            success=False,
            error=str(e)
        )


@app.get("/stats", response_model=StatsResponse)
async def get_stats(bot: Dict[str, Any] = Depends(get_bot)):
    """Get booking statistics"""
    try:
        result = bot['booking_manager'].get_booking_stats()
        
        # Parse stats from the result string
        stats = {
            'total_bookings': 0,
            'confirmed_bookings': 0,
            'cancelled_bookings': 0,
            'total_guests': 0,
            'today_bookings': 0,
            'success_rate': 0.0
        }
        
        if "Booking Statistics" in result:
            lines = result.split('\n')[1:]  # Skip header
            for line in lines:
                if 'Total Bookings:' in line:
                    stats['total_bookings'] = int(line.split(':')[1].strip())
                elif 'Confirmed:' in line:
                    stats['confirmed_bookings'] = int(line.split(':')[1].split()[0])
                elif 'Cancelled:' in line:
                    stats['cancelled_bookings'] = int(line.split(':')[1].split()[0])
                elif 'Total Guests' in line:
                    stats['total_guests'] = int(line.split(':')[1].strip())
                elif "Today's Bookings:" in line:
                    stats['today_bookings'] = int(line.split(':')[1].strip())
                elif 'Success Rate:' in line:
                    stats['success_rate'] = float(line.split(':')[1].strip().replace('%', ''))
        
        return StatsResponse(**stats)
        
    except Exception as e:
        bot['monitoring'].track_error(e, {
            'operation': 'get_stats'
        })
        return StatsResponse(
            total_bookings=0,
            confirmed_bookings=0,
            cancelled_bookings=0,
            total_guests=0,
            today_bookings=0,
            success_rate=0.0,
            success=False,
            error=str(e)
        )


if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
