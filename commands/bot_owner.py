import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from highrise.models import User

class BotOwner:
    def __init__(self, bot):
        self.bot = bot
        self.owners_file = Path("data") / "bot_owners.json"
        self._ensure_owners_file()
        
    def _ensure_owners_file(self):
        """Ensure the bot owners file exists with empty structure."""
        self.owners_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.owners_file.exists():
            # Create with empty owners list
            with open(self.owners_file, 'w') as f:
                json.dump({"owners": []}, f, indent=2)
    
    def _load_owners(self) -> List[Dict[str, str]]:
        """Load the list of bot owners from the JSON file."""
        try:
            with open(self.owners_file, 'r') as f:
                data = json.load(f)
                return data.get('owners', [])
        except Exception as e:
            self.bot.safe_print(f"Error loading bot owners: {e}")
            return []
    
    async def is_owner(self, user_id: str) -> bool:
        """Check if a user is a bot owner."""
        try:
            user_id = str(user_id)
            owners = self._load_owners()
            owner_ids = [str(owner.get('user_id')) for owner in owners]
            is_owner = user_id in owner_ids
            self.bot.safe_print(f"Bot owner check for {user_id}: {is_owner}")
            return is_owner
        except Exception as e:
            self.bot.safe_print(f"Error checking bot owner status: {e}")
            return False
    
    async def add_owner(self, user_id: str, username: str) -> bool:
        """Add a user to the bot owners list."""
        try:
            user_id = str(user_id)
            owners = self._load_owners()
            
            # Check if already an owner
            if any(str(owner.get('user_id')) == user_id for owner in owners):
                return False
                
            # Add new owner
            owners.append({
                'user_id': user_id,
                'username': username
            })
            
            # Save back to file
            with open(self.owners_file, 'w') as f:
                json.dump({"owners": owners}, f, indent=2)
                
            return True
            
        except Exception as e:
            self.bot.safe_print(f"Error adding bot owner: {e}")
            return False
    
    async def remove_owner(self, user_id: str) -> bool:
        """Remove a user from the bot owners list."""
        try:
            user_id = str(user_id)
            owners = self._load_owners()
            
            # Filter out the user
            new_owners = [o for o in owners if str(o.get('user_id')) != user_id]
            
            # If nothing changed, user wasn't an owner
            if len(new_owners) == len(owners):
                return False
                
            # Save back to file
            with open(self.owners_file, 'w') as f:
                json.dump({"owners": new_owners}, f, indent=2)
                
            return True
            
        except Exception as e:
            self.bot.safe_print(f"Error removing bot owner: {e}")
            return False

    async def list_owners(self) -> List[Dict[str, str]]:
        """List all bot owners."""
        return self._load_owners()

    async def handle_command(self, user: User, message: str) -> None:
        """Handle bot owner commands."""
        try:
            parts = message[1:].split()  # Remove the '!' prefix
            if not parts:
                return
                
            command = parts[0].lower()
            args = parts[1:]
            
            if command == "botowner":
                # List all bot owners
                owners = await self.list_owners()
                if not owners:
                    await self.bot.highrise.chat("🤖 No bot owners found.")
                    return
                
                # Get just the usernames
                usernames = [f"@{owner.get('username', 'Unknown')}" for owner in owners]
                
                # Send a single message with all usernames
                await self.bot.highrise.chat(f"🤖 Bot Owners: {', '.join(usernames)}")
                        
            elif command == "addowner" and len(args) == 1:
                # Check if user is a bot owner
                if not await self.is_owner(user.id):
                    await self.bot.highrise.chat("❌ Only bot owners can use this command.")
                    return
                    
                # Get target username
                target_username = args[0].lstrip('@')
                
                # Get room users to find the target user
                room_users = (await self.bot.highrise.get_room_users()).content
                target_user = next((u for u, _ in room_users if u.username.lower() == target_username.lower()), None)
                
                if target_user:
                    added = await self.add_owner(target_user.id, target_user.username)
                    if added:
                        await self.bot.highrise.chat(f"✅ Added @{target_user.username} to bot owners!")
                    else:
                        await self.bot.highrise.chat(f"ℹ️ @{target_user.username} is already a bot owner.")
                else:
                    # If user not in room, add with just the username
                    added = await self.add_owner(None, target_username)
                    if added:
                        await self.bot.highrise.chat(f"⚠️ Added @{target_username} to bot owners, but couldn't verify their ID. They may need to be in the room.")
                    else:
                        await self.bot.highrise.chat(f"ℹ️ @{target_username} is already a bot owner or an error occurred.")
                        
            elif command == "remowner" and len(args) == 1:
                # Check if user is a bot owner
                if not await self.is_owner(user.id):
                    await self.bot.highrise.chat("❌ Only bot owners can use this command.")
                    return
                    
                # Get target username
                target_username = args[0].lstrip('@')
                
                # Find the owner in the list
                owners = self._load_owners()
                target_owner = next((o for o in owners if o.get('username', '').lower() == target_username.lower()), None)
                
                if target_owner:
                    removed = await self.remove_owner(target_owner['user_id'])
                    if removed:
                        await self.bot.highrise.chat(f"✅ Removed @{target_owner['username']} from bot owners!")
                    else:
                        await self.bot.highrise.chat(f"❌ Failed to remove @{target_owner['username']} from bot owners.")
                else:
                    await self.bot.highrise.chat(f"❌ No bot owner found with username @{target_username}")
                    
        except Exception as e:
            self.bot.safe_print(f"Error in bot owner command: {e}")
            import traceback
            self.bot.safe_print(traceback.format_exc())

def setup(bot):
    """Setup function called by the bot to register the bot owner system."""
    bot_owner = BotOwner(bot)
    
    # Register commands
    @bot.command('botowner')
    async def botowner_cmd(user: User, args: list = None):
        await bot_owner.handle_command(user, '!botowner')
        
    @bot.command('addowner')
    async def addowner_cmd(user: User, args: list):
        if not args:
            await bot.highrise.chat("❌ Please specify a username.")
            return
        await bot_owner.handle_command(user, f'!addowner {args[0]}')
    
    @bot.command('remowner')
    async def remowner_cmd(user: User, args: list):
        if not args:
            await bot.highrise.chat("❌ Please specify a username.")
            return
        await bot_owner.handle_command(user, f'!remowner {args[0]}')
    
    return bot_owner
