from highrise import BaseBot, User, Position, AnchorPosition
from typing import List, Optional, Dict, Set, Tuple
import asyncio
import re

class Follower:
    def __init__(self, bot):
        self.bot = bot
        self.following = False
        self.follow_target = None
        self.follow_task = None
        self.stop_event = asyncio.Event()
        self.last_position = None
        self.follow_distance = 1.5  # meters behind the target
        self.update_interval = 0.5  # seconds between position updates
        
    async def start_following(self, target_user: Optional[User] = None):
        """Start following a user."""
        if self.following:
            await self.stop_following()
            
        self.following = True
        self.stop_event.clear()
        self.follow_target = target_user
        
        # Start the follow loop
        self.follow_task = asyncio.create_task(self._follow_loop())
        
        target_name = target_user.username if target_user else "you"
        await self.bot.whisper(target_user if target_user else user, f"👣 Now following {target_name}!")        
        
    async def stop_following(self, user=None):
        """Stop following the current target."""
        if not self.following:
            return
            
        self.following = False
        self.stop_event.set()
        
        if self.follow_task:
            self.follow_task.cancel()
            try:
                await self.follow_task
            except asyncio.CancelledError:
                pass
            self.follow_task = None
            
        self.follow_target = None
        if user:
            await self.bot.whisper(user, "🛑 Stopped following.")
        else:
            await self.bot.highrise.chat("🛑 Stopped following.")
        
    async def _follow_loop(self):
        """Main follow loop that updates the bot's position to follow the target."""
        try:
            while not self.stop_event.is_set() and self.following:
                if not self.follow_target:
                    await asyncio.sleep(self.update_interval)
                    continue
                    
                try:
                    # Get current room users
                    room_users = await self.bot.highrise.get_room_users()
                    self.bot.safe_print(f"[DEBUG] Room users: {room_users}")
                    
                    if not hasattr(room_users, 'content') or not room_users.content:
                        self.bot.safe_print("[DEBUG] No room users content found")
                        await asyncio.sleep(self.update_interval)
                        continue
                    
                    # Find target user in the room
                    target_found = False
                    target_pos = None
                    target_facing = None
                    
                    for user_data in room_users.content:
                        if len(user_data) != 2:
                            self.bot.safe_print(f"[DEBUG] Unexpected user data format: {user_data}")
                            continue
                            
                        user, pos = user_data
                        self.bot.safe_print(f"[DEBUG] Checking user: {user.username}, pos type: {type(pos)}")
                        
                        if hasattr(user, 'id') and user.id == self.follow_target.id:
                            target_pos = pos
                            target_found = True
                            self.bot.safe_print(f"[DEBUG] Found target user. Position data: {pos}")
                            break
                    
                    if not target_found or target_pos is None:
                        if hasattr(self.bot, 'whisper') and hasattr(self.follow_target, 'id'):
                            await self.bot.whisper(self.follow_target, f"❌ Couldn't find you in the room. Stopping follow.")
                        else:
                            await self.bot.highrise.chat(f"❌ Couldn't find {self.follow_target.username} in the room.")
                        await self.stop_following(self.follow_target)
                        return
                    
                    # Get target position
                    self.bot.safe_print(f"[DEBUG] Target position object: {target_pos}, type: {type(target_pos)}")
                    
                    # Check if target_pos is a string (anchor position) or Position object
                    if isinstance(target_pos, str):
                        # Handle anchor position (teleport to the anchor)
                        try:
                            await self.bot.highrise.walk_to(AnchorPosition(target_pos))
                            continue
                        except Exception as e:
                            self.bot.safe_print(f"Error walking to anchor: {e}")
                            continue
                    
                    # Handle Position object
                    if hasattr(target_pos, 'x') and hasattr(target_pos, 'y') and hasattr(target_pos, 'z'):
                        try:
                            # Calculate target position behind the target
                            if hasattr(target_pos, 'facing') and target_pos.facing is not None:
                                facing = target_pos.facing
                                self.bot.safe_print(f"[DEBUG] Facing direction: {facing}")
                                
                                # Get angle from facing direction
                                angle = self._get_angle_from_facing(facing)
                                offset_x = -self.follow_distance * self._get_sin(angle)
                                offset_z = -self.follow_distance * self._get_cos(angle)
                                
                                target_x = target_pos.x + offset_x
                                target_z = target_pos.z + offset_z
                                target_y = target_pos.y  # Keep same height
                                
                                self.bot.safe_print(f"[DEBUG] Moving to position: x={target_x}, y={target_y}, z={target_z}")
                                target_position = Position(target_x, target_y, target_z)
                            else:
                                # Fallback: just use the target's position
                                target_position = Position(target_pos.x, target_pos.y, target_pos.z)
                            
                            # Move to the target position
                            await self.bot.highrise.walk_to(target_position)
                            
                        except Exception as e:
                            self.bot.safe_print(f"Error calculating or moving to position: {e}")
                            import traceback
                            self.bot.safe_print(traceback.format_exc())
                    
                except Exception as e:
                    self.bot.safe_print(f"Error in follow loop: {e}")
                
                # Wait before next update
                await asyncio.sleep(self.update_interval)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.bot.safe_print(f"Critical error in follow loop: {e}")
            await self.bot.highrise.chat("❌ An error occurred while following.")
        finally:
            await self.stop_following()
    
    def _get_facing_vector(self, facing_str: str) -> dict:
        """Convert facing string to direction vector."""
        facing_map = {
            'FrontRight': {'x': 1, 'z': 1},
            'FrontLeft': {'x': -1, 'z': 1},
            'BackRight': {'x': 1, 'z': -1},
            'BackLeft': {'x': -1, 'z': -1},
            'Front': {'x': 0, 'z': 1},
            'Back': {'x': 0, 'z': -1},
            'Right': {'x': 1, 'z': 0},
            'Left': {'x': -1, 'z': 0}
        }
        return facing_map.get(facing_str, {'x': 1, 'z': 0})
    
    def _get_angle_from_facing(self, facing) -> float:
        """Convert facing direction to angle in radians."""
        import math
        if isinstance(facing, str):
            vec = self._get_facing_vector(facing)
            return math.atan2(vec['x'], vec['z'])
        # For backward compatibility if facing is a vector
        return math.atan2(facing.x, facing.z)
    
    def _get_sin(self, angle: float) -> float:
        """Get sine with angle in radians."""
        import math
        return math.sin(angle)
    
    def _get_cos(self, angle: float) -> float:
        """Get cosine with angle in radians."""
        import math
        return math.cos(angle)

async def handle_follow(user: User, args: List[str], bot_instance) -> None:
    """Handle the follow command."""
    # Get bot instance from closure
    bot = bot_instance
    
    # Initialize follower if it doesn't exist
    if not hasattr(bot, 'follower'):
        bot.follower = Follower(bot)
    
    follower = bot.follower
    
    # Check for stop command
    if args and args[0].lower() == 'stop':
        await follower.stop_following()
        return
    
    # If no args, follow the command sender
    if not args:
        await follower.start_following(user)
        return
    
    # Check for username mention
    username = ' '.join(args).lstrip('@').strip()
    if not username:
        await follower.start_following(user)
        return
    
    # Find the target user in the room
    try:
        room_users = await bot.highrise.get_room_users()
        users = room_users.content
        
        for room_user, _ in users:
            if room_user.username.lower() == username.lower():
                await follower.start_following(room_user)
                return
        
        # If we get here, user not found
        await bot.highrise.chat(f"❌ Couldn't find user '{username}' in the room.")
    except Exception as e:
        bot.safe_print(f"Error in follow command: {e}")
        await bot.highrise.chat("❌ An error occurred while processing the follow command.")

def setup(bot):
    """Set up the follow command."""
    # Initialize follower
    if not hasattr(bot, 'follower'):
        bot.follower = Follower(bot)
    
    # Create a closure that includes the bot instance
    async def follow_wrapper(user: User, args: List[str]) -> None:
        return await handle_follow(user, args, bot)
    
    # Register command with the wrapper
    bot.command("follow")(follow_wrapper)
