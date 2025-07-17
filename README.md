# Highrise Bot

A modular bot for Highrise with a command handler system.

## Setup

1. Make sure you have Python 3.11 or higher installed.
2. Install the required packages:
   ```
   pip install highrise-bot-sdk
   ```

## Configuration

1. Get your bot token from [Highrise Bot Tokens](https://create.highrise.game/dashboard/credentials/api-keys)
2. Get your room ID from the Highrise game
3. Set environment variables:
   - Windows:
     ```
     set ROOM_ID=your_room_id
     set TOKEN=your_bot_token
     ```
   - Linux/Mac:
     ```
     export ROOM_ID=your_room_id
     export TOKEN=your_bot_token
     ```

## Running the Bot

```
python bot.py
```

## Adding Commands

1. Create a new Python file in the `commands` directory
2. Define your command functions
3. Register them in the `setup` function

Example command file (`commands/my_commands.py`):

```python
async def my_command(bot, user, args):
    """!mycommand - Description of what this command does"""
    await bot.highrise.chat("This is a custom command!")

def setup(bot):
    bot.command("mycommand")(my_command)
```

## Default Commands

- `!hello` - Say hello to the bot
- `!help` - Show all available commands
- `!tp <x> <y> <z>` - Teleport to specific coordinates

## License

MIT
