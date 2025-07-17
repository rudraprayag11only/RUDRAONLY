import asyncio
from typing import Optional
from highrise import BaseBot, User, Position, AnchorPosition

class GotoSystem:
    def __init__(self, bot):
        self.bot = bot
        self.bot.safe_print("[GotoSystem] Initializing goto system...")
        
    async def _is_owner(self, user_id: str) -> bool:
        """Check if user is a bot owner using the BotOwner system."""
        try:
            if hasattr(self.bot, 'bot_owner') and self.bot.bot_owner:
                return await self.bot.bot_owner.is_owner(user_id)
            return False
        except Exception as e:
            self.bot.safe_print(f"[GotoSystem] Error checking bot owner permissions: {e}")
            return False
    
    async def _find_user_in_room(self, username: str) -> Optional[User]:
        """Find a user in the room by username."""
        try:
            # Remove @ if present
            username = username.lstrip('@').lower()
            
            # Get all users in the room
            room_users = (await self.bot.highrise.get_room_users()).content
            
            # Find the user
            for room_user, _ in room_users:
                if room_user.username.lower() == username:
                    return room_user
            return None
        except Exception as e:
            self.bot.safe_print(f"[GotoSystem] Error finding user: {e}")
            return None
    
    async def _get_user_position(self, user_id: str) -> Optional[Position]:
        """Get the position of a user in the room."""
        try:
            room_users = (await self.bot.highrise.get_room_users()).content
            
            for room_user, position in room_users:
                if room_user.id == user_id:
                    return position
            return None
        except Exception as e:
            self.bot.safe_print(f"[GotoSystem] Error getting user position: {e}")
            return None
    
    async def handle_goto_command(self, user: User, args: list) -> None:
        """Handle the !goto command."""
        try:
            # Check if user is an owner
            if not await self._is_owner(user.id):
                await self.bot.highrise.send_whisper(user.id, "❌ Only bot owners can use this command.")
                return
            
            # Validate arguments
            if len(args) == 0:
                await self.bot.highrise.send_whisper(user.id, "❌ Usage: !goto @username (teleports you to that user) or !goto @user1 @user2 (teleports user1 to user2)")
                return
            elif len(args) == 1:
                # Single argument: teleport the command issuer to the target
                user_to_teleport = user
                target_user_name = args[0]
            elif len(args) == 2:
                # Two arguments: teleport first user to second user
                user_to_teleport_name = args[0]
                target_user_name = args[1]
                # Find the user to teleport
                user_to_teleport = await self._find_user_in_room(user_to_teleport_name)
                if not user_to_teleport:
                    await self.bot.highrise.send_whisper(user.id, f"❌ User '{user_to_teleport_name}' not found in the room.")
                    return
            else:
                await self.bot.highrise.send_whisper(user.id, "❌ Too many arguments. Usage: !goto @username or !goto @user1 @user2")
                return
            
            # Find target user
            target_user = await self._find_user_in_room(target_user_name)
            
            if not target_user:
                await self.bot.highrise.send_whisper(user.id, f"❌ Target user '{target_user_name}' not found in the room.")
                return
            
            # Get target user's position
            target_position = await self._get_user_position(target_user.id)
            if not target_position:
                await self.bot.highrise.send_whisper(user.id, f"❌ Could not get position of target user '{target_user_name}'.")
                return
            
            # Handle different position types
            if isinstance(target_position, AnchorPosition):
                # If target is on an anchor, teleport to the anchor
                try:
                    await self.bot.highrise.teleport(user_to_teleport.id, target_position)
                    await self.bot.highrise.send_whisper(user.id, f"✅ Teleported @{user_to_teleport.username} to @{target_user.username}'s anchor position!")
                except Exception as e:
                    self.bot.safe_print(f"[GotoSystem] Error teleporting to anchor: {e}")
                    await self.bot.highrise.send_whisper(user.id, "❌ You can only teleport to users who are on a seat or standing on the ground.")
            elif isinstance(target_position, Position):
                # If target is on a regular position, teleport nearby
                try:
                    # Create a position slightly offset from the target to avoid overlapping
                    offset_position = Position(
                        x=target_position.x + 0.5,
                        y=target_position.y,
                        z=target_position.z + 0.5,
                        facing=target_position.facing
                    )
                    
                    await self.bot.highrise.teleport(user_to_teleport.id, offset_position)
                    await self.bot.highrise.send_whisper(user.id, f"✅ Teleported @{user_to_teleport.username} to @{target_user.username}'s position!")
                except Exception as e:
                    self.bot.safe_print(f"[GotoSystem] Error teleporting to position: {e}")
                    # Try teleporting to exact position if offset fails
                    try:
                        await self.bot.highrise.teleport(user_to_teleport.id, target_position)
                        await self.bot.highrise.send_whisper(user.id, f"✅ Teleported @{user_to_teleport.username} to @{target_user.username}'s exact position!")
                    except Exception as e2:
                        self.bot.safe_print(f"[GotoSystem] Error teleporting to exact position: {e2}")
                        await self.bot.highrise.send_whisper(user.id, f"❌ Failed to teleport: {str(e2)}")
            else:
                await self.bot.highrise.send_whisper(user.id, f"❌ Unknown position type for target user '{target_user_name}'.")
            
        except Exception as e:
            error_msg = f"❌ Error in goto command: {str(e)}"
            self.bot.safe_print(f"[GotoSystem] {error_msg}")
            import traceback
            self.bot.safe_print(traceback.format_exc())
            await self.bot.highrise.send_whisper(user.id, "❌ An error occurred while processing the goto command.")

def setup(bot):
    """Setup function called by the bot to register the goto command."""
    goto_system = GotoSystem(bot)
    
    # Register the goto command
    @bot.command('goto')
    async def goto_command(user: User, *args):
        await goto_system.handle_goto_command(user, list(args))
    
    bot.safe_print("[GotoSystem] Goto command registered successfully!")
    return goto_system
