from highrise.__main__ import *
import time

"""
Bot Settings - Auto-configured
"""
room_id = "6868cdb9b301f133e1d8a2f8"  # Your room ID
bot_token = "7a9b4444daafe960140c75432fe67cf199df66a460742c0d3c0033476aff5297"  # Your bot token
bot_file = "bot"  # bot.py contains the main bot class
bot_class = "Bot"  # Main bot class in bot.py

if __name__ == "__main__":
    print("=" * 50)
    print("STARTING BOT INSTANCE")
    print("=" * 50)
    print(f"Bot Class: {bot_class} from {bot_file}.py")
    print(f"Room ID: {room_id}")
    
    try:
        # Create bot instance with room_id
        print("\n[DEBUG] Creating bot instance...")
        bot_class_obj = getattr(import_module(bot_file), bot_class)
        bot_instance = bot_class_obj(room_id=room_id)
        
        # Print instance information
        print("\n[DEBUG] Bot instance created successfully!")
        print(f"Instance ID: {id(bot_instance)}")
        print(f"Instance Type: {type(bot_instance)}")
        print(f"Instance Attributes: {dir(bot_instance)}\n")
        
        # Create bot definition
        print("[DEBUG] Creating bot definition...")
        definitions = [
            BotDefinition(
                bot_instance,
                room_id,
                bot_token
            )
        ]
        print("[DEBUG] Bot definition created successfully!")
        
    except Exception as e:
        print(f"\n[ERROR] Failed to initialize bot: {e}")
        import traceback
        print(traceback.format_exc())
        raise
    
    # More BotDefinition classes can be added to the definitions list
    while True:
        try:
            arun(main(definitions))
        except Exception as e:
            # Print the full traceback for the exception
            import traceback
            print("Caught an exception:")
            traceback.print_exc()  # This will print the full traceback
            time.sleep(1)
            continue
