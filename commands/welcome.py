from highrise import User, Position, AnchorPosition
import asyncio
import traceback

class WelcomeSystem:
    def __init__(self, bot):
        self.bot = bot
        self.active_users = set()  # Track users currently in the room
        self.bot.safe_print("[WelcomeSystem] Initialized - Welcome and Leave messages enabled")
        
    async def on_user_join(self, user: User, position: Position | AnchorPosition = None) -> None:
        """Handle when a user joins the room."""
        try:
            # Only send welcome if user wasn't already in the room
            if user.id not in self.active_users:
                self.bot.safe_print(f"[WelcomeSystem] Sending welcome to @{user.username}")
                
                # Send welcome message
                welcome_message = f"✨ @{user.username} Welcome! Great to have you here. ✨"
                await self.bot.highrise.chat(welcome_message)
                
                # Send heart reaction
                await self.bot.highrise.react("heart", user.id)
                
                # Mark as active
                self.active_users.add(user.id)
                
        except Exception as e:
            self.bot.safe_print(f"[WelcomeSystem] Error in welcome: {e}")
            self.bot.safe_print(traceback.format_exc())
    
    async def on_user_leave(self, user: User) -> None:
        """Handle when a user leaves the room."""
        try:
            # Only send leave message if they were actually in the room
            if user.id in self.active_users:
                self.bot.safe_print(f"[WelcomeSystem] Sending goodbye to @{user.username}")
                
                # Send leave message
                leave_message = f"👋 @{user.username} Thanks for stopping by—see you soon! 👋"
                await self.bot.highrise.chat(leave_message)
                
                # Remove from active users
                self.active_users.discard(user.id)
                
        except Exception as e:
            self.bot.safe_print(f"[WelcomeSystem] Error in leave message: {e}")
            self.bot.safe_print(traceback.format_exc())

def setup(bot):
    try:
        # Check if welcome system is already initialized
        if hasattr(bot, '_welcome_system'):
            bot.safe_print("[WelcomeSystem] Welcome system already initialized")
            return bot._welcome_system
            
        bot.safe_print("[WelcomeSystem] Starting welcome system setup...")
        welcome_system = WelcomeSystem(bot)
        
        # Store the welcome system instance
        bot._welcome_system = welcome_system
        
        # Replace the bot's methods with our handlers
        bot.on_user_join = welcome_system.on_user_join
        bot.on_user_leave = welcome_system.on_user_leave
        
        bot.safe_print("[WelcomeSystem] Successfully initialized welcome system")
        return welcome_system
        
    except Exception as e:
        bot.safe_print(f"[WelcomeSystem] Error during setup: {e}")
        bot.safe_print(traceback.format_exc())
        return None
