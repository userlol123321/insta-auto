import sys
import argparse
import signal
from config import load_config
from database import Database

try:
    from bot_service import BotService
    from web_dashboard import create_app
    INSTAGRAPI_AVAILABLE = True
except ImportError as e:
    INSTAGRAPI_AVAILABLE = False
    MISSING_DEP_ERROR = str(e)


def signal_handler(sig, frame):
    print("\n[InstaAuto] Caught interrupt signal. Exiting gracefully...")
    sys.exit(0)

def check_dependencies():
    if not INSTAGRAPI_AVAILABLE:
        print("\n❌ Error: Missing required dependencies!")
        print(f"Details: {MISSING_DEP_ERROR}")
        print("\n👉 To install them automatically on Android Termux, run:")
        print("   ./termux_install.sh")
        print("\n👉 Or install manually via pip:")
        print("   pip install -r requirements.txt\n")
        sys.exit(1)

def cli_login():
    check_dependencies()
    config = load_config()

    db = Database()
    print("=" * 60)
    print(" INSTAGRAM LOGIN & SESSION INITIALIZATION")
    print("=" * 60)
    
    if not config.ig_username:
        username = input("Enter Instagram Username: ").strip()
    else:
        username = config.ig_username
        print(f"Username from config: @{username}")

    if not config.ig_password:
        import getpass
        password = getpass.getpass("Enter Instagram Password: ").strip()
    else:
        password = config.ig_password

    from instagram_client import InstagramClient
    client = InstagramClient(username, password, config.session_file, logger=db)
    success = client.login()
    if success:
        print("\n✅ Authentication successful! Session saved to session.json.")
        print("You can now start the bot daemon without entering your password every time.\n")
    else:
        print("\n❌ Login failed. Please check the logs above.\n")

def cli_check_follower(target_username: str):
    config = load_config()
    db = Database()
    from instagram_client import InstagramClient
    client = InstagramClient(config.ig_username, config.ig_password, config.session_file, logger=db)
    if not client.login():
        print("Login required to check follower status.")
        return

    try:
        user_id = client.cl.user_id_from_username(target_username)
        is_following = client.is_user_following_me(user_id)
        if is_following:
            print(f"✅ @{target_username} (ID: {user_id}) IS FOLLOWING @{client.username}!")
        else:
            print(f"🛡️ @{target_username} (ID: {user_id}) is NOT following @{client.username}.")
    except Exception as e:
        print(f"Error checking user: {e}")

def cli_stats():
    db = Database()
    stats = db.get_summary_stats()
    print("\n" + "=" * 45)
    print(" 📊 INSTAGRAM AUTOMATOR STATS")
    print("=" * 45)
    print(f"Date:                   {stats['today_date']}")
    print(f"Today's DMs Sent:       {stats['today_dms']}")
    print(f"Followers Delivered:    {stats['today_followers_served']}")
    print(f"Non-Followers Blocked:  {stats['today_non_followers_blocked']}")
    print(f"Total Comments Scanned: {stats['total_processed_comments']}")
    print(f"Total DMs Sent:         {stats['total_dms_sent']}")
    print("=" * 45 + "\n")

def run_web(host="0.0.0.0", port=8080, start_bot=True):
    check_dependencies()
    config = load_config()
    db = Database()
    bot = BotService(config, db)
    if start_bot:
        bot.start_background()

    app = create_app(bot)
    print(f"\n🚀 Web Dashboard running at: http://localhost:{port}")
    print(f"📱 If accessing from Android Chrome, open: http://127.0.0.1:{port}\n")
    try:
        app.run(host=host, port=port, debug=False, use_reloader=False)
    finally:
        bot.stop()

def run_bot_cli():
    check_dependencies()
    config = load_config()
    db = Database()
    bot = BotService(config, db)
    try:
        bot.run_loop()
    except KeyboardInterrupt:
        bot.stop()

def interactive_menu():
    while True:
        print("\n" + "=" * 50)
        print(" 🤖 INSTAGRAM FOLLOWER DM AUTOMATOR (ANDROID/TERMUX)")
        print("=" * 50)
        print(" 1. Start Automator Daemon (CLI Loop)")
        print(" 2. Start Web Dashboard (Mobile Browser UI)")
        print(" 3. Perform Instagram Login / Update Session")
        print(" 4. View Statistics & Activity Summary")
        print(" 5. Test Check User Follower Status")
        print(" 6. Exit")
        print("=" * 50)

        choice = input("Select an option [1-6]: ").strip()
        if choice == "1":
            run_bot_cli()
        elif choice == "2":
            config = load_config()
            run_web(config.web_host, config.web_port, start_bot=True)
        elif choice == "3":
            cli_login()
        elif choice == "4":
            cli_stats()
        elif choice == "5":
            target = input("Enter target username to test (without @): ").strip()
            if target:
                cli_check_follower(target)
        elif choice == "6":
            print("Goodbye!")
            break
        else:
            print("Invalid option. Please enter 1-6.")

def main():
    signal.signal(signal.SIGINT, signal_handler)
    parser = argparse.ArgumentParser(description="Instagram Follower-Gated DM Automator")
    parser.add_argument("--run", action="store_true", help="Run the automation daemon directly")
    parser.add_argument("--web", action="store_true", help="Launch the Web Dashboard with background bot")
    parser.add_argument("--login", action="store_true", help="Perform interactive login & save session")
    parser.add_argument("--stats", action="store_true", help="Display today's stats summary")
    parser.add_argument("--check-user", type=str, help="Check if an Instagram username follows your account")

    args = parser.parse_args()

    if args.login:
        cli_login()
    elif args.run:
        run_bot_cli()
    elif args.web:
        config = load_config()
        run_web(config.web_host, config.web_port, start_bot=True)
    elif args.stats:
        cli_stats()
    elif args.check_user:
        cli_check_follower(args.check_user)
    else:
        interactive_menu()

if __name__ == "__main__":
    main()
