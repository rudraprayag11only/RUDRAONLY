from highrise import BaseBot, User, Position, AnchorPosition, SessionMetadata
import asyncio
from typing import Dict, List, Optional

class HeartsSystem:
    def __init__(self, bot):
        self.bot = bot
        # Only use heart reaction
        self.heart_reaction = "heart"  # Built-in heart reaction

    async def send_hearts(self, user: User, target: Optional[User] = None, count: int = 3) -> None:
        """
        Send heart reactions to a specific user or all users using the built-in react method.
        
        Args:
            user: The user who sent the command
            target: The target user to send hearts to (if None, send to all)
            count: Number of reactions to send
        """
        try:
            if target:
                # Send heart reactions to specific user
                self.bot.safe_print(f"Sending {count} heart reactions to {target.username}")
                for _ in range(count):
                    await self.bot.highrise.react(self.heart_reaction, target.id)
                    await asyncio.sleep(0.5)  # Small delay between hearts
                
                # Notify the sender
                await self.bot.whisper(user, f"💖 Sent {count} reactions to @{target.username}!")
            else:
                # Send heart reactions to all users in the room except self and the bot
                room_users = (await self.bot.highrise.get_room_users()).content
                bot_id = getattr(self.bot, 'user_id', None)
                users = [u for u, _ in room_users if u.id != user.id and (not bot_id or u.id != bot_id)]  # Exclude command sender and bot
                
                self.bot.safe_print(f"Sending {count} heart reactions to {len(users)} users (excluding self and bot)")
                
                for target_user in users:
                    try:
                        for _ in range(count):
                            await self.bot.highrise.react(self.heart_reaction, target_user.id)
                            await asyncio.sleep(0.3)  # Small delay between hearts
                    except Exception as e:
                        self.bot.safe_print(f"Error sending heart to {target_user.username}: {str(e)}")
                        continue  # Continue with next user if there's an error
                
                # Notify the sender
                await self.bot.whisper(user, f"💖 Sent {count} reactions to everyone in the room!")
                
        except Exception as e:
            error_msg = f"❌ Error sending reactions: {str(e)}"
            self.bot.safe_print(error_msg)
            await self.bot.whisper(user, error_msg)

def setup(bot):
    hearts_system = HeartsSystem(bot)
    
    @bot.command('h')
    async def hearts_command(user: User, *args) -> None:
        try:
            # Get the first argument if it exists
            if not args:
                # Show help if no arguments
                await bot.whisper(user, "💖 Hearts Command:\n!h @username - Send 10 hearts to a user\n!h all - Send 3 hearts to everyone")
                return
                
            # Get the first argument and convert to string
            first_arg = args[0] if isinstance(args[0], str) else ' '.join(args[0]) if args[0] else ''
            
            # Check for 'all' command
            if first_arg.lower() == 'all':
                await hearts_system.send_hearts(user, None, 3)  # 3 hearts for all
                return
                
            # Check for username mention
            if first_arg.startswith('@'):
                target_username = first_arg[1:].strip()  # Remove @ and any extra spaces
                if not target_username:
                    await bot.whisper(user, "❌ Please specify a username after @")
                    return
                    
                room_users = await bot.highrise.get_room_users()
                for room_user, _ in room_users.content:
                    if room_user.username.lower() == target_username.lower():
                        await hearts_system.send_hearts(user, room_user, 10)  # 10 hearts for specific user
                        return
                await bot.whisper(user, f"❌ User @{target_username} not found in the room")
            else:
                await bot.whisper(user, "❌ Invalid command. Use '!h @username' or '!h all'")
        except Exception as e:
            error_msg = f"❌ Error processing hearts command: {str(e)}"
            bot.safe_print(error_msg)
            await bot.whisper(user, error_msg)
    
    return hearts_system
