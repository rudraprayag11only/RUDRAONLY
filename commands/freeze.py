import asyncio
import json
import os
from pathlib import Path
from typing import Dict, Optional, Any
from highrise.models import User, Position
import os
import json
from highrise import AnchorPosition

class FreezeSystem:
    def __init__(self, bot):
        self.bot = bot
        self.frozen_positions: Dict[str, Position] = {}
        self.freeze_tasks: Dict[str, asyncio.Task] = {}
        self.stop_events: Dict[str, asyncio.Event] = {}
        # Use absolute path for the save files
        current_dir = Path(__file__).parent.parent
        self.save_file = current_dir / 'data' / 'freeze_state.json'
        self.save_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_state()
        
    async def is_owner(self, user: User) -> bool:
        """Check if a user is a bot owner."""
        if not hasattr(self.bot, 'bot_owner'):
            self.bot.safe_print("❌ Bot owner system not initialized")
            return False
            
        try:
            return await self.bot.bot_owner.is_owner(str(user.id))
        except Exception as e:
            self.bot.safe_print(f"❌ Error checking bot owner status: {e}")
            return False

    def _load_state(self) -> None:
        """Load frozen state from JSON file."""
        try:
            if self.save_file.exists():
                with open(self.save_file, 'r') as f:
                    data = json.load(f)
                    for user_id, pos_data in data.get('frozen_positions', {}).items():
                        self.frozen_positions[user_id] = Position(
                            x=pos_data['x'],
                            y=pos_data['y'],
                            z=pos_data['z']
                        )
                        # Start freeze loop for each saved position
                        if user_id not in self.freeze_tasks:
                            self.stop_events[user_id] = asyncio.Event()
                            self.freeze_tasks[user_id] = asyncio.create_task(
                                self._freeze_loop(user_id, self.frozen_positions[user_id])
                            )
        except Exception as e:
            self.bot.safe_print(f"Error loading freeze state: {e}")
    
    def _save_state(self) -> None:
        """Save frozen state to JSON file."""
        try:
            data = {
                'frozen_positions': {
                    user_id: {'x': pos.x, 'y': pos.y, 'z': pos.z}
                    for user_id, pos in self.frozen_positions.items()
                }
            }
            with open(self.save_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.bot.safe_print(f"Error saving freeze state: {e}")
    
    async def handle_freeze_command(self, user: User, args: list) -> None:
        """Handle the freeze command to freeze a user in place."""
        self.bot.safe_print(f"[DEBUG] handle_freeze_command called with args: {args}")
        
        # Check if user is an owner
        if not await self.is_owner(user):
            await self.bot.whisper(user, "❌ This command is only available to bot owners!")
            return
        
        # Check if a username was mentioned
        if not args or not args[0].startswith('@'):
            await self.bot.whisper(user, "❌ Please mention a user to freeze. Example: !freeze @username")
            return
            
        target_username = args[0][1:]  # Remove @ symbol
        self.bot.safe_print(f"[DEBUG] Attempting to freeze user: {target_username}")
        
        try:
            # Get all users in the room
            self.bot.safe_print("[DEBUG] Getting room users...")
            room_users = await self.bot.highrise.get_room_users()
            self.bot.safe_print(f"[DEBUG] Found {len(room_users.content)} users in the room")
            
            # Find the target user
            target_user = None
            target_pos = None
            for room_user, pos in room_users.content:
                self.bot.safe_print(f"[DEBUG] Checking user: {room_user.username} (ID: {room_user.id})")
                if room_user.username.lower() == target_username.lower():
                    target_user = room_user
                    target_pos = pos
                    self.bot.safe_print(f"[DEBUG] Found target user: {target_user.username} at position {target_pos}")
                    break
                    
            if not target_user:
                error_msg = f"❌ Could not find user @{target_username} in the room."
                self.bot.safe_print(f"[ERROR] {error_msg}")
                self.bot.safe_print("[DEBUG] Available users in room:" + "\n  " + "\n  ".join([f"{u[0].username} (ID: {u[0].id})" for u in room_users.content]))
                await self.bot.whisper(user, error_msg)
                return
                
            # Don't allow freezing the bot
            if hasattr(self.bot, 'bot_id') and target_user.id == self.bot.bot_id:
                await self.bot.whisper(user, "❌ I can't freeze myself!")
                return
                
            # Check if user is already frozen
            if target_user.id in self.freeze_tasks:
                await self.bot.whisper(user, f"❌ @{target_user.username} is already frozen!")
                return
                
            # Store the frozen position
            self.frozen_positions[target_user.id] = target_pos
            
            # Create stop event for this freeze session
            self.stop_events[target_user.id] = asyncio.Event()
            
            # Start the freeze loop
            self.freeze_tasks[target_user.id] = asyncio.create_task(
                self._freeze_loop(target_user.id, target_pos)
            )
            
            await self.bot.whisper(user, f"❄️ @{target_user.username} has been frozen in place!")
            await self.bot.whisper(target_user, f"❄️ You've been frozen in place by @{user.username}")
            # Removed the "Type !unfreeze to move again" part as requested
            self._save_state()  # Save state after freezing
            
        except Exception as e:
            await self.bot.whisper(user, f"❌ Error: {str(e)}")
            self.bot.safe_print(f"Error in freeze command: {e}")
            if user.id in self.freeze_tasks:
                self.freeze_tasks[user.id].cancel()
                del self.freeze_tasks[user.id]
            if user.id in self.frozen_positions:
                del self.frozen_positions[user.id]

    async def handle_unfreeze_command(self, user: User, target_username: str) -> None:
        """
        Handle the unfreeze command to stop a user from being frozen.
        
        Args:
            user: The user who sent the command
            target_username: The username to unfreeze (without @)
        """
        try:
            self.bot.safe_print(f"[UNFREEZE] Processing unfreeze for @{target_username}")
            
            # Get room users to find the target user
            room_users = await self.bot.highrise.get_room_users()
            target_user = None
            target_user_id = None
            
            # Find the target user in the room (case-insensitive match)
            target_username_lower = target_username.lower()
            for room_user, pos in room_users.content:
                if room_user.username.lower() == target_username_lower:
                    target_user = room_user
                    target_user_id = str(room_user.id)
                    self.bot.safe_print(f"[DEBUG] Found user @{room_user.username} (ID: {room_user.id})")
                    break
            
            if not target_user or not target_user_id:
                # User not found, exit silently
                return
                
            # Check if user is in frozen_positions or has an active freeze task
            is_frozen = (
                any(k.lower() == target_user_id.lower() for k in self.frozen_positions.keys()) or
                any(k.lower() == target_user_id.lower() for k in self.freeze_tasks.keys())
            )
            
            if not is_frozen:
                return
            
            # Find the actual key in the dictionaries (case-insensitive match)
            frozen_key = next((k for k in self.frozen_positions.keys() if k.lower() == target_user_id.lower()), None)
            task_key = next((k for k in self.freeze_tasks.keys() if k.lower() == target_user_id.lower()), None)
            
            # Stop the freeze task if it exists
            if task_key and task_key in self.freeze_tasks:
                task = self.freeze_tasks[task_key]
                if not task.done():
                    task.cancel()
                del self.freeze_tasks[task_key]
                self.bot.safe_print(f"[DEBUG] Removed freeze task for user ID: {task_key}")
            
            # Clear the frozen position
            if frozen_key and frozen_key in self.frozen_positions:
                del self.frozen_positions[frozen_key]
                self.bot.safe_print(f"[DEBUG] Removed frozen position for user ID: {frozen_key}")
            
            # Stop the stop event if it exists
            stop_key = next((k for k in self.stop_events.keys() if k.lower() == target_user_id.lower()), None)
            if stop_key and stop_key in self.stop_events:
                self.stop_events[stop_key].set()
                del self.stop_events[stop_key]
                self.bot.safe_print(f"[DEBUG] Stopped and removed stop event for user ID: {stop_key}")
            
            # Save the updated state
            self._save_state()
            
            # Send success message
            success_msg = f"✅ @{target_username} has been unfrozen!"
            self.bot.safe_print(f"[UNFREEZE] {success_msg}")
            await self.bot.whisper(user, success_msg)
            
            # Notify the target user if they're not the one who sent the command
            if target_user_id != str(user.id) and hasattr(target_user, 'id'):
                msg_to_target = f"✅ @{user.username} has unfrozen you!"
                await self.bot.whisper(target_user, msg_to_target)
            
        except Exception as e:
            error_msg = f"❌ Error unfreezing user: {str(e)}"
            self.bot.safe_print(f"[ERROR] {error_msg}")
            self.bot.safe_print("Traceback:", exc_info=True)
            await self.bot.whisper(user, error_msg)
            
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            self.bot.safe_print(f"[ERROR] {error_msg}")
            self.bot.safe_print("Traceback:", exc_info=True)
            await self.bot.whisper(user, error_msg)

    async def _freeze_loop(self, user_id: str, position: Position) -> None:
        """Continuously teleport a user to the frozen position."""
        self.bot.safe_print(f"[DEBUG] _freeze_loop started for user_id: {user_id}")
        stop_event = self.stop_events.get(user_id)
        if not stop_event:
            self.bot.safe_print(f"[ERROR] No stop event found for user {user_id}")
            return
            
        try:
            self.bot.safe_print(f"[DEBUG] Starting freeze loop for user {user_id} at position {position}")
            freeze_count = 0
            while not stop_event.is_set():
                try:
                    # Get current room users to find the target user's current position
                    room_users = await self.bot.highrise.get_room_users()
                    user_found = False
                    
                    # Find the target user in the room
                    for room_user, current_pos in room_users.content:
                        if str(room_user.id) == user_id:
                            user_found = True
                            freeze_count += 1
                            # Log position every 10 iterations to reduce log spam
                            if freeze_count % 10 == 0:
                                self.bot.safe_print(f"[DEBUG] User {room_user.username} current position: {current_pos}")
                            
                            # If user has moved from their frozen position, teleport them back
                            position_changed = (
                                abs(current_pos.x - position.x) > 0.1 or 
                                abs(current_pos.y - position.y) > 0.1 or 
                                abs(current_pos.z - position.z) > 0.1
                            )
                            
                            if position_changed:
                                self.bot.safe_print(f"[DEBUG] User {room_user.username} moved from {position} to {current_pos}")
                                try:
                                    await self.bot.highrise.teleport(room_user.id, position)
                                    self.bot.safe_print(f"[DEBUG] Teleported user {room_user.username} back to frozen position: {position}")
                                except Exception as e:
                                    self.bot.safe_print(f"[ERROR] Failed to teleport user: {e}")
                            break
                    
                    if not user_found:
                        self.bot.safe_print(f"[DEBUG] User {user_id} not found in room, ending freeze loop")
                        break
                        
                except Exception as e:
                    self.bot.safe_print(f"Error in freeze loop: {e}")
                
                # Small delay to prevent spamming the server
                await asyncio.sleep(0.5)
                
        except asyncio.CancelledError:
            self.bot.safe_print(f"[DEBUG] Freeze loop for user {user_id} was cancelled")
        except Exception as e:
            self.bot.safe_print(f"Error in freeze loop: {e}")
        finally:
            # Clean up
            if user_id in self.freeze_tasks:
                del self.freeze_tasks[user_id]
            if user_id in self.stop_events:
                del self.stop_events[user_id]
            if user_id in self.frozen_positions:
                del self.frozen_positions[user_id]
            self._save_state()

def setup(bot):
    # Create and store the freeze system instance
    bot.safe_print("[DEBUG] Setting up freeze system...")
    bot.freeze_system = FreezeSystem(bot)
    bot.safe_print("[DEBUG] Freeze system setup complete")
    
    # Register freeze command
    @bot.command('freeze')
    async def freeze_cmd(user: User, *args) -> None:
        """Freeze a user in place. Usage: !freeze @username"""
        try:
            # Convert args to list if it's not already
            args_list = list(args) if args else []
            bot.safe_print(f"[DEBUG] Processing freeze command from {user.username} with args: {args_list}")
            
            if not args_list or not args_list[0]:
                await bot.whisper(user, "❌ Please mention a user to freeze. Example: !freeze @username")
                return
                
            # Get the mention from args
            mention = str(args_list[0]).strip()
            if not mention.startswith('@'):
                mention = f'@{mention}'
                
            bot.safe_print(f"[DEBUG] Calling handle_freeze_command with: {user.username}, [{mention}]")
            await bot.freeze_system.handle_freeze_command(user, [mention])
            
        except Exception as e:
            error_msg = f"Error in freeze command: {e}"
            bot.safe_print(f"[ERROR] {error_msg}")
            import traceback
            bot.safe_print(traceback.format_exc())
            await bot.whisper(user, f"❌ {error_msg}")
    
    # Register new unfreeze command
    @bot.command('unfreeze')
    async def unfreeze_user(user: User, target_username: str) -> None:
        """
        Unfreeze a user
        
        Usage: !unfreeze @username
        """
        try:
            bot.safe_print(f"[UNFREEZE] {user.username} is trying to unfreeze {target_username}")
            
            # Remove @ if present
            if target_username.startswith('@'):
                target_username = target_username[1:]
            
            # Get the room users to find the target user
            room_users = await bot.highrise.get_room_users()
            target_user = None
            
            for room_user, pos in room_users.content:
                if room_user.username.lower() == target_username.lower():
                    target_user = room_user
                    break
            
            if not target_user:
                await bot.whisper(user, f"❌ User @{target_username} not found in the room")
                return
            
            # Check if user is an owner
            if not await bot.freeze_system.is_owner(user):
                await bot.whisper(user, "❌ This command is only available to bot owners!")
                return
            
            # Call the unfreeze method
            await bot.freeze_system.handle_unfreeze_command(user, target_username)
            
            # Send success message
            await bot.whisper(user, f"✅ Successfully unfroze @{target_username}")
            
        except Exception as e:
            error_msg = f"Failed to unfreeze user: {str(e)}"
            bot.safe_print(f"[ERROR] {error_msg}")
            import traceback
            bot.safe_print(traceback.format_exc())
            await bot.whisper(user, f"❌ {error_msg}")
