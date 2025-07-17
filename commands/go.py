import os
import json
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Set
from highrise import BaseBot, User, Position, AnchorPosition, SessionMetadata

class RateLimiter:
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.user_requests = {}
        
    def is_allowed(self, user_id: str) -> bool:
        current_time = time.time()
        if user_id not in self.user_requests:
            self.user_requests[user_id] = []
            
        # Remove old requests outside the time window
        self.user_requests[user_id] = [t for t in self.user_requests[user_id] 
                                     if current_time - t < self.time_window]
        
        if len(self.user_requests[user_id]) < self.max_requests:
            self.user_requests[user_id].append(current_time)
            return True
        return False

class GoSystem:
    def __init__(self, bot):
        self.bot = bot
        self.places_file = os.path.join("data", "places.json")
        self.places = {}
        self._last_places_load = 0
        self._places_lock = asyncio.Lock()
        self.cooldowns = {}  # User ID to last teleport time
        self.COOLDOWN = 5  # seconds
        self.rate_limiter = RateLimiter(max_requests=5, time_window=60)  # 5 requests per minute per user
        self._load_places()  # Initial load

    def _load_places(self) -> Dict:
        """Load places from the JSON file with caching."""
        current_time = time.time()
        if current_time - self._last_places_load < 5:  # 5 second cache
            return self.places
            
        try:
            if not os.path.exists(self.places_file):
                # Create default places if file doesn't exist
                default_places = {}
                os.makedirs(os.path.dirname(self.places_file), exist_ok=True)
                with open(self.places_file, 'w') as f:
                    json.dump(default_places, f, indent=4)
                self.places = default_places
                self._last_places_load = current_time
                return self.places
            
            with open(self.places_file, 'r') as f:
                self.places = json.load(f)
                self._last_places_load = current_time
                return self.places
                
        except json.JSONDecodeError as e:
            self.bot.safe_print(f"Error decoding places JSON: {e}")
            return {}
        except Exception as e:
            self.bot.safe_print(f"Error loading places: {e}")
            return self.places  # Return cached version if available
            
    async def _is_owner(self, user_id: str) -> bool:
        """Check if user is a bot owner."""
        if not hasattr(self.bot, 'bot_owner'):
            self.bot.safe_print("❌ Bot owner system not initialized")
            return False
            
        try:
            return await self.bot.bot_owner.is_owner(user_id)
        except Exception as e:
            self.bot.safe_print(f"❌ Error checking bot owner status: {e}")
            return False

    async def _get_user_position(self, user_id: str) -> Tuple[float, float, float, str]:
        """Get the current position and facing of a user."""
        try:
            room_users = (await self.bot.highrise.get_room_users()).content
            for room_user, pos in room_users:
                if room_user.id == user_id:
                    if isinstance(pos, Position):
                        facing = 'FrontRight'  # Default facing
                        return pos.x, pos.y, pos.z, facing
                    elif hasattr(pos, 'anchor_ix'):  # If it's an AnchorPosition
                        return pos.x, pos.y, pos.z, pos.facing
            return None
        except Exception as e:
            self.bot.safe_print(f"Error getting user position: {e}")
            return None
            
    async def add_place(self, user: User, place_name: str) -> None:
        """Add a new place at the user's current location."""
        try:
            # Check if user is an owner
            if not await self._is_owner(user.id):
                await self.bot.highrise.send_whisper(user.id, "❌ Only bot owners can add places.")
                return
                
            # Get user's current position
            pos_data = await self._get_user_position(user.id)
            if not pos_data:
                await self.bot.highrise.send_whisper(user.id, "❌ Could not determine your position.")
                return
                
            x, y, z, facing = pos_data
            
            # Add the new place
            self.places[place_name.lower()] = {
                'x': x,
                'y': y,
                'z': z,
                'facing': facing
            }
            
            # Save to file
            with open(self.places_file, 'w') as f:
                json.dump(self.places, f, indent=4)
                
            await self.bot.highrise.send_whisper(user.id, f"✅ Added new place: {place_name} at ({x}, {y}, {z}) facing {facing}")
            
        except Exception as e:
            self.bot.safe_print(f"Error adding place: {e}")
            await self.bot.highrise.send_whisper(user.id, "❌ An error occurred while adding the place.")
            
    async def remove_place(self, user: User, place_name: str) -> None:
        """Remove an existing place."""
        try:
            # Check if user is an owner
            if not await self._is_owner(user.id):
                await self.bot.highrise.send_whisper(user.id, "❌ Only bot owners can remove places.")
                return
                
            # Check if place exists
            if place_name.lower() not in self.places:
                await self.bot.highrise.send_whisper(user.id, f"❌ Place '{place_name}' does not exist.")
                return
                
            # Remove the place
            del self.places[place_name.lower()]
            
            # Save to file
            with open(self.places_file, 'w') as f:
                json.dump(self.places, f, indent=4)
                
            await self.bot.highrise.send_whisper(user.id, f"✅ Removed place: {place_name}")
            
        except Exception as e:
            self.bot.safe_print(f"Error removing place: {e}")
            await self.bot.highrise.send_whisper(user.id, "❌ An error occurred while removing the place.")

    async def teleport_to_place(self, user: User, place_name: str) -> None:
        """Teleport the user to the specified place with rate limiting and cooldown."""
        try:
            # Rate limiting check
            if not self.rate_limiter.is_allowed(user.id):
                await self.bot.highrise.send_whisper(user.id, "⚠️ Too many requests. Please wait a moment before trying again.")
                return
                
            # Check cooldown
            current_time = time.time()
            if user.id in self.cooldowns:
                time_since_last = current_time - self.cooldowns[user.id]
                if time_since_last < self.COOLDOWN:
                    remaining = int(self.COOLDOWN - time_since_last)
                    await self.bot.highrise.send_whisper(user.id, f"⏳ Please wait {remaining} seconds before teleporting again!")
                    return
            
            # Update cooldown
            self.cooldowns[user.id] = current_time
            
            # Get the place with thread-safe access
            async with self._places_lock:
                self._load_places()  # Ensure we have the latest data
                place = self.places.get(place_name.lower())
                if not place:
                    await self.bot.highrise.send_whisper(user.id, f"❌ Unknown place '{place_name}'. Use !places to see available locations.")
                    return
            
            # Create position with error checking
            try:
                x = float(place['x'])
                y = float(place['y'])
                z = float(place['z'])
                facing = place.get('facing', 'FrontRight')
                target_pos = Position(x, y, z, facing)
            except (KeyError, ValueError) as e:
                self.bot.safe_print(f"Invalid position data for {place_name}: {e}")
                await self.bot.highrise.send_whisper(user.id, "❌ Invalid teleport location. Please contact an admin.")
                return
            
            # Execute teleport with timeout
            try:
                await asyncio.wait_for(
                    self.bot.highrise.teleport(user.id, target_pos),
                    timeout=5.0
                )
                # Always use whisper for feedback
                await self.bot.highrise.send_whisper(user.id, f"✨ You've been teleported to {place_name}!")
                    
            except asyncio.TimeoutError:
                self.bot.safe_print(f"Teleport timed out for {user.username}")
                await self.bot.highrise.send_whisper(user.id, "⏳ Teleport timed out. Please try again.")
            except Exception as e:
                self.bot.safe_print(f"Error during teleport for {user.username}: {e}")
                await self.bot.highrise.send_whisper(user.id, "❌ Failed to teleport. Please try again later.")
            
        except Exception as e:
            self.bot.safe_print(f"Error teleporting user: {e}")
            await self.bot.highrise.chat(f"❌ An error occurred while teleporting to {place_name}.")
            
    async def list_places(self, user: User) -> None:
        """List all available places with pagination if needed."""
        try:
            async with self._places_lock:
                self._load_places()  # Ensure fresh data
                if not self.places:
                    await self.bot.highrise.send_whisper(user.id, "❌ No places available. Contact a moderator.")
                    return
                
                # Sort places alphabetically
                sorted_places = sorted(self.places.keys())
                
                # Always use whisper for listing places
                chunk_size = 10
                chunks = [sorted_places[i:i + chunk_size] for i in range(0, len(sorted_places), chunk_size)]
                await self.bot.highrise.send_whisper(user.id, "📍 Available places (showing 10 at a time):")
                for i, chunk in enumerate(chunks, 1):
                    places_list = ", ".join([f"!{place}" for place in chunk])
                    await self.bot.highrise.send_whisper(user.id, f"Page {i}: {places_list}")
                    
        except Exception as e:
            self.bot.safe_print(f"Error listing places: {e}")
            await self.bot.highrise.send_whisper(user.id, "❌ Failed to load places. Please try again later.")

def setup(bot):
    go_system = GoSystem(bot)
    
    @bot.command('go')
    async def go_command(user: User, args: list) -> None:
        """Teleport to a predefined location. Usage: !go [place]"""
        if not await go_system._is_owner(user.id):
            await bot.highrise.send_whisper(user.id, "❌ Only bot owners can use this command.")
            return
            
        if not args:
            await go_system.list_places(user)
            return
            
        place_name = ' '.join(args).lower()
        await go_system.teleport_to_place(user, place_name)
    
    @bot.command('goadd')
    async def go_add_command(user: User, args: list) -> None:
        """Add a new teleport location. Usage: !goadd [place_name]"""
        if not await go_system._is_owner(user.id):
            await bot.highrise.send_whisper(user.id, "❌ Only bot owners can use this command.")
            return
            
        if not args:
            await bot.highrise.send_whisper(user.id, "❌ Please specify a name for the place. Usage: !goadd [place_name]")
            return
            
        place_name = ' '.join(args).lower()
        await go_system.add_place(user, place_name)
    
    @bot.command('gorem')
    async def go_remove_command(user: User, args: list) -> None:
        """Remove a teleport location. Usage: !gorem [place_name]"""
        if not await go_system._is_owner(user.id):
            await bot.highrise.send_whisper(user.id, "❌ Only bot owners can use this command.")
            return
            
        if not args:
            await bot.highrise.send_whisper(user.id, "❌ Please specify a place to remove. Usage: !gorem [place_name]")
            return
            
        place_name = ' '.join(args).lower()
        await go_system.remove_place(user, place_name)
    
    @bot.command('places')
    async def places_command(user: User, *args) -> None:
        """List all available places to teleport to."""
        if not await go_system._is_owner(user.id):
            await bot.highrise.send_whisper(user.id, "❌ Only bot owners can use this command.")
            return
            
        await go_system.list_places(user)
    
    return go_system
