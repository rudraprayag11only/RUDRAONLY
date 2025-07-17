from highrise import BaseBot, User, SessionMetadata, Position, AnchorPosition, Item, EmoteEvent, ReactionEvent
import asyncio
import random
import traceback
import os
import json

class EmoteSystem:
    def __init__(self, bot):
        self.bot = bot
        self.is_emoting = False
        self.emote_task = None
        self.stop_event = asyncio.Event()
        self.emotes = self._load_emotes()
        self.bot.safe_print("[EmoteSystem] Initialized")

    def _load_emotes(self):
        """Load emote IDs from JSON file."""
        emotes_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'emotes.json')
        try:
            with open(emotes_file, 'r') as f:
                data = json.load(f)
                # Extract just the emote IDs from the JSON structure
                return [emote['id'] for emote in data.get('emotes', []) if 'id' in emote]
        except Exception as e:
            self.bot.safe_print(f"[EmoteSystem] Error loading emotes: {e}")
            # Return some default emotes if loading fails
            return ["idle-loop-happy", "idle-loop-sitfloor", "idle-lookup"]

    async def start_emote_loop(self):
        """Continuously perform random emotes until stopped."""
        self.is_emoting = True
        self.stop_event.clear()
        
        try:
            while not self.stop_event.is_set():
                # Select a random emote
                emote = random.choice(self.emotes)
                self.bot.safe_print(f"[EmoteSystem] Performing emote: {emote}")
                
                # Perform the emote
                try:
                    await self.bot.highrise.send_emote(emote)
                except Exception as e:
                    self.bot.safe_print(f"[EmoteSystem] Error performing emote {emote}: {e}")
                
                # Wait for a random time between 5-15 seconds
                wait_time = random.uniform(5.0, 15.0)
                try:
                    await asyncio.wait_for(self.stop_event.wait(), timeout=wait_time)
                    break  # Exit if stop event is set during wait
                except asyncio.TimeoutError:
                    continue  # Continue the loop if timeout occurs (normal operation)
                    
        except Exception as e:
            self.bot.safe_print(f"[EmoteSystem] Error in emote loop: {e}")
            self.bot.safe_print(traceback.format_exc())
        finally:
            self.is_emoting = False
            self.emote_task = None

    async def start_emote(self, user: User) -> None:
        """Start the random emote sequence."""
        if self.is_emoting:
            await self.bot.highrise.chat("I'm already performing random emotes!")
            return
            
        self.bot.safe_print(f"[EmoteSystem] Starting random emotes for @{user.username}")
        self.emote_task = asyncio.create_task(self.start_emote_loop())
        await self.bot.highrise.chat("🎭 Starting random emotes! Type !stopemote to stop.")

    async def stop_emote(self, user: User) -> None:
        """Stop the random emote sequence."""
        if not self.is_emoting:
            await self.bot.highrise.chat("I'm not currently performing any emotes!")
            return
            
        self.bot.safe_print(f"[EmoteSystem] Stopping random emotes for @{user.username}")
        self.stop_event.set()
        
        # Wait for the task to complete
        if self.emote_task:
            try:
                await asyncio.wait_for(self.emote_task, timeout=5.0)
            except asyncio.TimeoutError:
                self.bot.safe_print("[EmoteSystem] Warning: Emote task didn't stop cleanly")
                self.emote_task.cancel()
            
        await self.bot.highrise.chat("🎭 Stopped random emotes!")

def setup(bot):
    try:
        # Check if emote system is already initialized
        if hasattr(bot, '_emote_system'):
            bot.safe_print("[EmoteSystem] Emote system already initialized")
            return bot._emote_system
            
        bot.safe_print("[EmoteSystem] Starting emote system setup...")
        emote_system = EmoteSystem(bot)
        
        # Store the emote system instance
        bot._emote_system = emote_system
        
        # Register commands
        @bot.command('startemote')
        async def start_emote_cmd(user: User, args: list):
            await emote_system.start_emote(user)
            
        @bot.command('stopemote')
        async def stop_emote_cmd(user: User, args: list):
            await emote_system.stop_emote(user)
        
        bot.safe_print("[EmoteSystem] Successfully initialized emote system")
        return emote_system
        
    except Exception as e:
        bot.safe_print(f"[EmoteSystem] Error during setup: {e}")
        bot.safe_print(traceback.format_exc())
        return None
