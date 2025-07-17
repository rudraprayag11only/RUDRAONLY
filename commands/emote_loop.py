from highrise import BaseBot, User, Position, AnchorPosition, SessionMetadata
import asyncio
import json
import os
from pathlib import Path
from typing import Dict, Set, Optional, Any

class EmoteLoop:
    def __init__(self, bot):
        self.bot = bot
        self.loops: Dict[str, asyncio.Task] = {}  # user_id -> task
        self.user_emotes: Dict[str, str] = {}  # user_id -> emote_id
        self.emote_list = self._get_emote_list()
        
    def _get_emote_list(self) -> Dict[str, str]:
        """Load and return a dictionary of emote names to emote IDs from the JSON file."""
        try:
            # Get the directory of the current file
            current_dir = Path(__file__).parent.parent
            emotes_path = current_dir / 'data' / 'emotes.json'
            
            self.bot.safe_print(f"[DEBUG] Loading emotes from: {emotes_path}")
            
            with open(emotes_path, 'r', encoding='utf-8') as f:
                emotes_data = json.load(f)
            
            # Create a dictionary mapping emote names to their IDs (with and without spaces)
            emote_map = {}
            for emote in emotes_data.get('emotes', []):
                original_name = emote['name']
                emote_id = emote['id']
                
                # Generate all possible variations of the emote name
                name_variations = set()
                
                # Original name (with original case)
                name_variations.add(original_name)
                
                # Lowercase version
                name_lower = original_name.lower()
                name_variations.add(name_lower)
                
                # No spaces
                no_spaces = name_lower.replace(' ', '')
                if no_spaces != name_lower:
                    name_variations.add(no_spaces)
                
                # With hyphens
                with_hyphens = name_lower.replace(' ', '-')
                if with_hyphens != name_lower:
                    name_variations.add(with_hyphens)
                
                # With underscores
                with_underscores = name_lower.replace(' ', '_')
                if with_underscores != name_lower:
                    name_variations.add(with_underscores)
                
                # Add common prefixes
                if not name_lower.startswith('emote-'):
                    name_variations.add(f'emote-{name_lower}')
                    name_variations.add(f'emote-{no_spaces}')
                    name_variations.add(f'emote-{with_hyphens}')
                
                if not name_lower.startswith('dance-'):
                    name_variations.add(f'dance-{name_lower}')
                    name_variations.add(f'dance-{no_spaces}')
                    name_variations.add(f'dance-{with_hyphens}')
                
                # Add all variations to the map
                for variation in name_variations:
                    if variation and variation not in emote_map:  # Don't overwrite existing entries
                        emote_map[variation] = emote_id
                
                self.bot.safe_print(f"[DEBUG] Mapped emote '{original_name}' ({emote_id}) to variations: {name_variations}")
            
            self.bot.safe_print(f"[DEBUG] Loaded {len(emote_map)} emote mappings")
            return emote_map
            
        except Exception as e:
            self.bot.safe_print(f"Error loading emotes from JSON: {e}")
            import traceback
            self.bot.safe_print(traceback.format_exc())
            # Return an empty dict if there's an error
            return {}
    
    def _handle_loop_error(self, task: asyncio.Task, user_id: str) -> None:
        """Handle errors that occur in the emote loop."""
        try:
            # Get the exception if one was raised
            exception = task.exception()
            if exception:
                self.bot.safe_print(f"Error in emote loop for user {user_id}: {exception}")
                import traceback
                self.bot.safe_print(''.join(traceback.format_exception(type(exception), exception, exception.__traceback__)))
        except asyncio.CancelledError:
            # Task was cancelled, which is expected when stopping a loop
            self.bot.safe_print(f"Emote loop for user {user_id} was cancelled")
        except Exception as e:
            self.bot.safe_print(f"Error in handle_loop_error for user {user_id}: {e}")
            import traceback
            self.bot.safe_print(traceback.format_exc())
        finally:
            # Clean up
            if user_id in self.loops:
                self.bot.safe_print(f"Cleaning up emote loop for user {user_id} in handle_loop_error")
                del self.loops[user_id]
                if user_id in self.user_emotes:
                    del self.user_emotes[user_id]
    
    async def start_loop(self, user: User, emote_name: str) -> None:
        try:
            user_id = user.id
            self.bot.safe_print(f"Starting emote loop for @{user.username} with emote: {emote_name}")
            
            # Check if the message is in format 'emotename to stop'
            if emote_name.lower().endswith(' to stop'):
                # Extract the emote name and stop the loop
                emote_to_stop = emote_name[:-8].strip()  # Remove ' to stop' from the end
                self.bot.safe_print(f"Stopping emote loop for @{user.username} with emote: {emote_to_stop}")
                await self.stop_loop(user_id)
                return
            
            # Check if it's a stop command
            if emote_name.lower() == 'stop':
                self.bot.safe_print(f"Stop command detected for user @{user.username}")
                await self.stop_loop(user_id)
                # Send whisper for stopping emote loop
                await self.bot.whisper(user, f"⏹️ Stopped emote loop")
                return
            
            # Map emoji to their corresponding emote names
            emoji_map = {
                '😹': 'laugh',
                '😂': 'laugh',
                '😆': 'laugh',
                '😊': 'happy',
                '😍': 'heart',
                '😎': 'cool',
                '🤔': 'think',
                '😴': 'sleepy',
                '😡': 'angry',
                '😭': 'sob',
                '👋': 'wave',
                '🤗': 'hug',
                '💃': 'dance',
                '🕺': 'dance',
                '🤣': 'laugh',
                '🙄': 'eyeroll',
                '😏': 'smirk',
                '🥺': 'pouty',
                '😱': 'scream',
                '😨': 'scared',
                '😵': 'dizzy',
                '🤯': 'mindblown',
                '🤪': 'silly',
                '😜': 'wink',
                '😇': 'angel',
                '😈': 'devil',
                '👻': 'ghost',
                '💀': 'skull',
                '👀': 'look',
                '❤️': 'heart',
                '🔥': 'fire',
                '💯': '100',
                '👍': 'thumbsup',
                '👎': 'thumbsdown',
                '👏': 'clap',
                '🙌': 'hooray',
                '🙏': 'pray',
                '🤞': 'fingerscrossed',
                '✌️': 'peace',
                '🤙': 'hangloose',
                '🤘': 'rockon',
                '🤟': 'iloveyou',
                '👊': 'fistbump',
                '👌': 'ok',
                '👉': 'pointright',
                '👈': 'pointleft',
                '👆': 'pointup',
                '👇': 'pointdown',
                '🤚': 'stophand',
                '✋': 'highfive'
            }
            
            # Check if the input is an emoji and map it to an emote name
            if len(emote_name) == 1 and ord(emote_name) > 0xFFFF:  # Check if it's an emoji
                self.bot.safe_print(f"Emoji detected: {emote_name}")
                emote_name = emoji_map.get(emote_name, emote_name)
                self.bot.safe_print(f"Mapped to emote: {emote_name}")
            
            self.bot.safe_print(f"Looking for emote: {emote_name} in emote list")
            # Find the emote ID (exact match only, case-insensitive)
            emote_id = None
            emote_name_lower = emote_name.lower().strip()
            
            # First try direct match
            self.bot.safe_print(f"[DEBUG] Checking for direct match in {len(self.emote_list)} emotes")
            if emote_name_lower in self.emote_list:
                emote_id = self.emote_list[emote_name_lower]
                self.bot.safe_print(f"[DEBUG] Found direct match: '{emote_name_lower}' with ID: {emote_id}")
            else:
                self.bot.safe_print(f"[DEBUG] No direct match found for '{emote_name_lower}'")
            
            # If no direct match, try matching against display names and variations
            if not emote_id:
                # Try different variations of the input name
                possible_inputs = [
                    emote_name_lower,  # original
                    emote_name_lower.replace(' ', ''),  # remove spaces
                    emote_name_lower.replace(' ', '-'),  # replace spaces with hyphens
                    emote_name_lower.replace(' ', '_'),  # replace spaces with underscores
                    'emote-' + emote_name_lower,  # add emote- prefix
                    'emote-' + emote_name_lower.replace(' ', '-'),
                    'dance-' + emote_name_lower,  # add dance- prefix
                    'dance-' + emote_name_lower.replace(' ', '-')
                ]
                self.bot.safe_print(f"[DEBUG] Trying variations: {possible_inputs}")
                
                # Check all possible name variations
                for name, eid in self.emote_list.items():
                    name_lower = name.lower()
                    # Remove common prefixes for matching
                    base_name = name_lower.replace('emote-', '').replace('dance-', '')
                    
                    # Check against all variations
                    if (name_lower in possible_inputs or 
                        base_name in possible_inputs or
                        any(variation == base_name for variation in possible_inputs) or
                        any(variation in base_name for variation in possible_inputs) or
                        any(base_name in variation for variation in possible_inputs)):
                        emote_id = eid
                        self.bot.safe_print(f"[DEBUG] Found match: {name} with ID: {eid}")
                        break
            
            if not emote_id:
                # Try to find a similar emote name
                similar_emotes = [name for name in self.emote_list.keys() 
                               if emote_name_lower.replace(' ', '') in name.replace(' ', '')]
                
                error_msg = f"Emote '{emote_name}' not found."
                if similar_emotes:
                    error_msg += f" Did you mean: {', '.join(similar_emotes[:3])}?"
                
                self.bot.safe_print(f"[ERROR] {error_msg}")
                self.bot.safe_print(f"[DEBUG] Available emotes: {list(self.emote_list.keys())}")
                await self.bot.highrise.chat(error_msg)
                return
            
            # Stop any existing loop for this user
            self.bot.safe_print(f"[DEBUG] Stopping any existing loop for user {user_id}")
            await self.stop_loop(user_id)
            
            # Start the new loop
            self.bot.safe_print(f"[DEBUG] Creating new emote loop task for user {user_id}")
            loop_task = asyncio.create_task(self._emote_loop(user_id, emote_id))
            self.loops[user_id] = loop_task
            self.user_emotes[user_id] = emote_id
            
            # Add error handling for the task
            loop_task.add_done_callback(lambda t, uid=user_id: self._handle_loop_error(t, uid))
            
            # Send whisper for starting emote loop
            success_msg = f"🔄 Now looping: {emote_name}"
            self.bot.safe_print(f"[DEBUG] @[Bot] {user.username} {success_msg}")
            await self.bot.whisper(user, success_msg)
            
        except Exception as e:
            error_msg = f"Error in start_loop: {str(e)}"
            self.bot.safe_print(error_msg)
            import traceback
            self.bot.safe_print(traceback.format_exc())
            try:
                await self.bot.highrise.chat("❌ An error occurred while starting the emote loop.")
            except:
                pass
            
        except Exception as e:
            error_msg = f"Error in start_loop: {str(e)}"
            self.bot.safe_print(error_msg)
            import traceback
            self.bot.safe_print(traceback.format_exc())
            try:
                await self.bot.highrise.chat("❌ An error occurred while starting the emote loop.")
            except:
                pass
    
    async def on_chat(self, user: User, message: str) -> None:
        """Handle chat messages for emote commands."""
        try:
            self.bot.safe_print(f"[EMOTE_LOOP] Processing message from @{user.username}: {message}")
            
            # Skip messages that start with 'h ' (hearts command)
            if message.lower().startswith('h '):
                self.bot.safe_print("[EMOTE_LOOP] Ignoring hearts command")
                return
            
            # Handle stop command
            if message.lower() == 'stop' or message.lower().startswith('e stop'):
                self.bot.safe_print(f"[EMOTE_LOOP] Processing stop command for @{user.username}")
                await self.stop_loop(user.id)
                await self.bot.whisper(user, "⏹️ Stopped emote loop")
                return
                
            # Check if this is an emote name directly
            emote_name = message.strip().lower()
            if emote_name in self.emote_list:
                self.bot.safe_print(f"[EMOTE_LOOP] Starting emote loop with direct emote name: {emote_name}")
                await self.start_loop(user, emote_name)
                return
                
            # Handle emote commands with 'e ' prefix
            if message.lower().startswith('e '):
                emote_name = message[2:].strip().lower()
                if emote_name in self.emote_list:
                    await self.start_loop(user, emote_name)
                    return
                
            # Handle emote list command
            if message.lower() in ['emotes', 'emote list', 'list'] or message.lower().startswith('e '):
                emote_cmd = message.lower().replace('e ', '').strip()
                if emote_cmd in ['emotes', 'emote list', 'list', '']:
                    self.bot.safe_print(f"[EMOTE_LOOP] Processing emote list request from @{user.username}")
                    emote_list = ", ".join(sorted(set(
                        # Get original names (without the no-space versions we added)
                        name for name in self.emote_list.keys() 
                        if ' ' in name or not any(
                            other_name != name and other_name.replace(' ', '') == name 
                            for other_name in self.emote_list.keys()
                        )
                    )))
                    # Send emote list in whisper
                    await self.bot.whisper(user, f"Available emotes: {emote_list}")
                    return
            
            # If we get here, it's not a recognized emote name or command
            return
                
        except Exception as e:
            error_msg = f"[EMOTE_LOOP] Error in on_chat: {str(e)}"
            self.bot.safe_print(error_msg)
            import traceback
            self.bot.safe_print(traceback.format_exc())
            try:
                # Send error in whisper
                await self.bot.whisper(user, "❌ An error occurred while processing your request.")
            except:
                pass
    
    async def stop_loop(self, user_id: str) -> bool:
        """Stop the emote loop for a user."""
        if user_id in self.loops:
            self.bot.safe_print(f"[EMOTE_LOOP] Stopping loop for user {user_id}")
            task = self.loops[user_id]
            task.cancel()
            try:
                # Wait a short time for the task to cancel
                await asyncio.wait_for(task, timeout=1.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except Exception as e:
                self.bot.safe_print(f"Error while stopping loop for user {user_id}: {e}")
            
            # Clean up regardless of whether the task completed cleanly
            was_running = user_id in self.loops
            if was_running:
                del self.loops[user_id]
                if user_id in self.user_emotes:
                    del self.user_emotes[user_id]
                return True
        return False
    
    async def _emote_loop(self, user_id: str, emote_id: str) -> None:
        """The actual emote loop coroutine."""
        try:
            self.bot.safe_print(f"[DEBUG] Starting emote loop for user {user_id} with emote ID: {emote_id}")
            
            # Get emote duration from the emote list
            emote_duration = 3.0  # Default duration in seconds if not found
            for name, eid in self.emote_list.items():
                if eid == emote_id:
                    # Try to get duration from the emote data
                    emote_data = next((e for e in self._get_emote_data() if e['id'] == emote_id), None)
                    if emote_data and 'duration' in emote_data:
                        emote_duration = float(emote_data['duration'])
                    break
            
            self.bot.safe_print(f"Using emote duration: {emote_duration} seconds")
            
            while True:
                try:
                    # Check if the loop was cancelled
                    if user_id not in self.loops:
                        self.bot.safe_print(f"Loop for user {user_id} was cancelled, exiting")
                        break
                    
                    # Check if user is still in the room
                    room_users = await self.bot.highrise.get_room_users()
                    user_in_room = any(str(user.id) == user_id for user, _ in room_users.content)
                    
                    if not user_in_room:
                        self.bot.safe_print(f"User {user_id} is no longer in the room, stopping emote loop")
                        if user_id in self.loops:
                            del self.loops[user_id]
                        if user_id in self.user_emotes:
                            del self.user_emotes[user_id]
                        break
                        
                    self.bot.safe_print(f"Sending emote {emote_id} to user {user_id}")
                    
                    try:
                        # Send the emote to the specific user
                        await self.bot.highrise.send_emote(emote_id, user_id)
                        
                        # Wait for the emote to complete plus a small buffer
                        wait_time = max(emote_duration, 1.0)  # Ensure minimum 1 second
                        self.bot.safe_print(f"Waiting {wait_time} seconds before next emote")
                        await asyncio.sleep(wait_time)
                        
                    except Exception as e:
                        if "Target user not in room" in str(e):
                            self.bot.safe_print(f"User {user_id} left the room, stopping emote loop")
                            if user_id in self.loops:
                                del self.loops[user_id]
                            if user_id in self.user_emotes:
                                del self.user_emotes[user_id]
                            break
                        raise
                    
                except asyncio.CancelledError:
                    self.bot.safe_print(f"Emote loop for user {user_id} was cancelled")
                    break
                    
                except Exception as e:
                    error_msg = f"Error in emote loop for user {user_id}: {str(e)}"
                    self.bot.safe_print(error_msg)
                    import traceback
                    self.bot.safe_print(traceback.format_exc())
                    # Wait a bit before retrying
                    await asyncio.sleep(5)
                    
        except Exception as e:
            error_msg = f"Unexpected error in emote loop for user {user_id}: {str(e)}"
            self.bot.safe_print(error_msg)
            import traceback
            self.bot.safe_print(traceback.format_exc())
            
        finally:
            # Clean up if the loop ends unexpectedly
            if user_id in self.loops:
                self.bot.safe_print(f"Cleaning up emote loop for user {user_id}")
                del self.loops[user_id]
                if user_id in self.user_emotes:
                    del self.user_emotes[user_id]
    
    def _get_emote_data(self) -> list:
        """Return the raw emote data from the JSON file."""
        try:
            current_dir = Path(__file__).parent.parent
            emotes_path = current_dir / 'data' / 'emotes.json'
            with open(emotes_path, 'r', encoding='utf-8') as f:
                emotes_data = json.load(f)
            return emotes_data.get('emotes', [])
        except Exception as e:
            self.bot.safe_print(f"Error loading emote data: {e}")
            return []

def setup(bot):
    # Create and store the emote_loop instance on the bot
    bot.emote_loop = EmoteLoop(bot)
    emote_loop = bot.emote_loop
    
    async def handle_user_leave(user: User) -> None:
        """Handle user leaving the room."""
        await emote_loop.stop_loop(user.id)
    
    async def handle_chat(user: User, message: str) -> None:
        """Handle chat messages for emote loop commands."""
        try:
            # Only handle messages that start with -
            if not message.startswith('-'):
                return False
                
            # Get the command part (after the -)
            command = message[1:].strip().lower()
            bot.safe_print(f"[EMOTE_LOOP] Processing command: {command}")
            
            # Handle stop command
            if command == 'stop':
                user_id = str(user.id)
                bot.safe_print(f"[EMOTE_LOOP] Processing stop command for {user.username} ({user_id})")
                
                # Check if user has an active loop first
                if user_id in emote_loop.loops:
                    bot.safe_print(f"[EMOTE_LOOP] Found active loop for user {user.username}")
                    was_stopped = await emote_loop.stop_loop(user_id)
                    bot.safe_print(f"[EMOTE_LOOP] Stop command result: {was_stopped}")
                    
                    if was_stopped:
                        try:
                            await bot.highrise.chat(f"⏹️ Stopped emote loop for @{user.username}")
                            bot.safe_print(f"[EMOTE_LOOP] Sent stop confirmation for {user.username}")
                        except Exception as e:
                            bot.safe_print(f"[EMOTE_LOOP] Error sending stop confirmation: {e}")
                    else:
                        await bot.highrise.whisper(user.id, "❌ Failed to stop emote loop. Please try again.")
                else:
                    bot.safe_print(f"[EMOTE_LOOP] No active loop found for {user.username}")
                    await bot.highrise.whisper(user.id, "❌ You don't have an active emote loop to stop.")
                return True
                
            # Skip if it's a command (starts with a letter)
            if command and command[0].isalpha():
                bot.safe_print(f"[EMOTE_LOOP] Skipping command: {command}")
                return False
                
            # Try to start an emote loop with the given emote name
            emote_name = command.strip()
            if emote_name:
                bot.safe_print(f"[EMOTE_LOOP] Starting emote loop with: {emote_name}")
                await emote_loop.start_loop(user, emote_name)
                return True
                
            return False
                
        except Exception as e:
            bot.safe_print(f"Error in emote loop chat handler: {e}")
            import traceback
            bot.safe_print(traceback.format_exc())
    
    # Register event handlers
    bot.event_handlers.setdefault('on_user_leave', []).append(handle_user_leave)
    bot.event_handlers.setdefault('on_chat', []).append(handle_chat)
    
    bot.safe_print("[EMOTE_LOOP] Emote loop system initialized and handlers registered")
