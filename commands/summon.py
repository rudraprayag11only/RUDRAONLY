import asyncio
import logging
from typing import List, Optional, Tuple
from highrise import User, Position, BaseBot

async def find_user_in_room(bot, username: str) -> Optional[Tuple[User, Position]]:
    """Find a user in the room by username (case-insensitive)."""
    try:
        room_users = (await bot.highrise.get_room_users()).content
        username = username.lower().lstrip('@')
        
        for room_user, pos in room_users:
            if room_user.username.lower() == username:
                return (room_user, pos)
        
        # Debug: List all users in the room
        bot.safe_print("Users in room:")
        for room_user, _ in room_users:
            bot.safe_print(f"- {room_user.username} (ID: {room_user.id})")
            
    except Exception as e:
        bot.safe_print(f"Error finding user in room: {e}")
    
    return None

async def find_bot_user(bot) -> Optional[User]:
    """Find the bot's user object in the room."""
    try:
        room_users = (await bot.highrise.get_room_users()).content
        
        # Debug: Print all room users
        bot.safe_print("\n=== DEBUG: All users in room ===")
        for ru, pos in room_users:
            bot.safe_print(f"- {ru.username} (ID: {ru.id}) at {pos}")
        bot.safe_print("==============================\n")
        
        # Try to get bot's user ID from different possible locations
        possible_bot_ids = []
        
        # 1. Check highrise.bot_id
        if hasattr(bot.highrise, 'bot_id'):
            possible_bot_ids.append(str(bot.highrise.bot_id))
            
        # 2. Check bot.session_metadata
        if hasattr(bot, 'session_metadata') and hasattr(bot.session_metadata, 'user_id'):
            possible_bot_ids.append(str(bot.session_metadata.user_id))
            
        # 3. Check bot's username from session metadata
        bot_username = None
        if hasattr(bot, 'session_metadata') and hasattr(bot.session_metadata, 'username'):
            bot_username = bot.session_metadata.username.lower()
            
        bot.safe_print(f"Looking for bot with IDs: {possible_bot_ids} or username: {bot_username}")
        
        # Search for bot in room users
        for room_user, _ in room_users:
            # Check by ID
            if str(room_user.id) in possible_bot_ids:
                bot.safe_print(f"Found bot by ID: {room_user.username} (ID: {room_user.id})")
                return room_user
                
            # Check by username if we have it
            if bot_username and room_user.username.lower() == bot_username:
                bot.safe_print(f"Found bot by username: {room_user.username} (ID: {room_user.id})")
                return room_user
                
        # If we still haven't found the bot, try to find any user that looks like a bot
        for room_user, _ in room_users:
            if 'bot' in room_user.username.lower():
                bot.safe_print(f"Potential bot found by name pattern: {room_user.username}")
                return room_user
                
    except Exception as e:
        import traceback
        bot.safe_print(f"Error in find_bot_user: {e}")
        bot.safe_print(traceback.format_exc())
    
    bot.safe_print("Could not identify the bot in the room.")
    return None

async def handle_summon(bot: BaseBot, user: User, args: List[str]) -> None:
    """Teleport the mentioned user to your location.
    
    Usage:
        !summon @username    - Teleport the user to your location
        !summon -t @username - Same as above (alternative syntax)
    """
    try:
        # Parse arguments
        target_username = None
        
        # Handle -t flag
        if args and args[0].lower() == '-t' and len(args) > 1:
            target_username = args[1].lstrip('@')
        elif args:
            target_username = args[0].lstrip('@')
        
        # Check if we have a valid username
        if not target_username:
            await bot.highrise.send_whisper(user.id, 
                "❌ Please specify a user to summon.\n"
                "Usage: !summon @username\n"
                "   or: !summon -t @username"
            )
            return
            
        bot.safe_print(f"Looking for user: {target_username}")
        
        # Find the target user
        target = await find_user_in_room(bot, target_username)
        if not target:
            await bot.highrise.send_whisper(user.id, f"❌ Couldn't find user @{target_username} in the room.")
            return
            
        target_user, _ = target
        
        # Get the command user's (your) position
        command_user_pos = None
        room_users = (await bot.highrise.get_room_users()).content
        for room_user, pos in room_users:
            if room_user.id == user.id:
                command_user_pos = pos
                break
                
        if not command_user_pos:
            await bot.highrise.send_whisper(user.id, "❌ Couldn't determine your position in the room.")
            return
            
        bot.safe_print(f"Found target: @{target_user.username}")
        bot.safe_print(f"Command user position: {command_user_pos}")
        
        # Create position next to the command user (slightly offset to avoid overlap)
        offset_x = 1.0  # 1 meter to the right
        new_pos = Position(
            command_user_pos.x + offset_x,
            command_user_pos.y,
            command_user_pos.z,
            command_user_pos.facing
        )
        
        bot.safe_print(f"Attempting to teleport @{target_user.username} to: {new_pos}")
        
        # Teleport the target user to the command user
        try:
            await bot.highrise.teleport(target_user.id, new_pos)
            # Public chat message
            await bot.highrise.chat(f"✨ Poof! @{target_user.username} has been summoned by @{user.username}!")            
            # Private message to command user
            await bot.highrise.send_whisper(user.id, f"✅ Successfully summoned @{target_user.username} to your location!")
        except Exception as e:
            error_msg = f"Error in teleport: {str(e)}"
            bot.safe_print(error_msg)
            await bot.highrise.chat("❌ Oops! I couldn't teleport there.")
            
    except Exception as e:
        bot.safe_print(f"Error in summon command: {e}")
        import traceback
        bot.safe_print(traceback.format_exc())
        await bot.highrise.chat("❌ An error occurred while trying to summon the bot.")

def setup(bot):
    @bot.command('summon')
    async def summon(user: User, args: List[str]):
        """Summon the bot to your location. Usage: !summon @username"""
        await handle_summon(bot, user, args)
