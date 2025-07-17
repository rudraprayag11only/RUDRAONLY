from highrise import BaseBot, User, Position, AnchorPosition
from typing import List, Optional, Dict, Set
import asyncio
from dataclasses import dataclass

@dataclass
class UserMovement:
    username: str
    user_id: str
    last_position: Position
    last_update: float
    is_moving: bool = False

class MovementTracker:
    def __init__(self, bot):
        self.bot = bot
        self.tracked_users: Dict[str, UserMovement] = {}
        self.movement_handlers = set()
        
    async def track_user(self, user: User, position: Position) -> None:
        """Track a user's movement."""
        user_id = str(user.id)
        if user_id not in self.tracked_users:
            self.tracked_users[user_id] = UserMovement(
                username=user.username,
                user_id=user_id,
                last_position=position,
                last_update=asyncio.get_event_loop().time()
            )
        else:
            # Update existing user's position
            movement = self.tracked_users[user_id]
            movement.last_position = position
            movement.last_update = asyncio.get_event_loop().time()
            movement.is_moving = True
            
        # Notify handlers
        await self._notify_handlers(user, position)
        
    async def _notify_handlers(self, user: User, position: Position) -> None:
        """Notify all registered movement handlers."""
        for handler in self.movement_handlers:
            try:
                await handler(user, position)
            except Exception as e:
                self.bot.safe_print(f"Error in movement handler: {e}")
                import traceback
                self.bot.safe_print(traceback.format_exc())
                
    def register_handler(self, handler):
        """Register a movement handler function."""
        self.movement_handlers.add(handler)
        return handler
        
    def unregister_handler(self, handler):
        """Unregister a movement handler function."""
        if handler in self.movement_handlers:
            self.movement_handlers.remove(handler)

async def handle_move(bot: BaseBot, user: User, args: List[str]) -> None:
    """Handle the move command to move the bot to specific coordinates."""
    try:
        if len(args) < 2:
            await bot.highrise.chat("❌ Please provide x and z coordinates. Example: !move 5 10")
            return
            
        try:
            x = float(args[0])
            z = float(args[1])
            y = 0.0  # Default height, can be adjusted if needed
            
            if len(args) > 2:
                y = float(args[2])
                
            position = Position(x, y, z)
            await bot.highrise.walk_to(position)
            await bot.highrise.chat(f"🚶 Moving to position: x={x}, y={y}, z={z}")
            
        except ValueError:
            await bot.highrise.chat("❌ Invalid coordinates. Please use numbers like: !move 5 10")
            
    except Exception as e:
        bot.safe_print(f"Error in move command: {e}")
        await bot.highrise.chat("❌ An error occurred while trying to move.")

async def handle_stop(bot: BaseBot, user: User, args: List[str]) -> None:
    """Stop any ongoing movement."""
    try:
        # This is a placeholder - in a real implementation, you'd need a way to cancel movement
        await bot.highrise.chat("🛑 Movement stopped.")
    except Exception as e:
        bot.safe_print(f"Error in stop command: {e}")
        await bot.highrise.chat("❌ An error occurred while trying to stop.")

def setup(bot):
    """Set up movement-related commands and handlers."""
    # Initialize movement tracker
    movement_tracker = MovementTracker(bot)
    
    # Register movement handler
    @bot.event
    async def on_user_move(user: User, position: Position) -> None:
        await movement_tracker.track_user(user, position)
    
    # Add commands
    bot.command("move")(handle_move)
    bot.command("stop")(handle_stop)
    
    # Store the tracker on the bot instance for access in other modules
    bot.movement_tracker = movement_tracker
    
    return movement_tracker
