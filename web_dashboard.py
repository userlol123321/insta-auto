import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from config import load_config, save_config, CONFIG_PATH
from database import Database

def create_app(bot_service=None):
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static")
    )
    db = Database()

    @app.route("/")
    def index():
        config = load_config()
        stats = db.get_summary_stats()
        recent_activity = db.get_recent_activity(20)
        recent_logs = db.get_recent_logs(25)
        is_running = bot_service.is_running if bot_service else False
        is_logged_in = bot_service.client.is_session_valid() if bot_service else False
        return render_template(
            "index.html",
            config=config,
            stats=stats,
            recent_activity=recent_activity,
            recent_logs=recent_logs,
            is_running=is_running,
            is_logged_in=is_logged_in
        )

    # -------------------------------------------------------------
    # PWA Manifest & Service Worker for "Install as Android App"
    # -------------------------------------------------------------
    @app.route("/manifest.json")
    def manifest():
        manifest_data = {
            "name": "InstaAuto DM Automator",
            "short_name": "InstaAuto",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#0d1117",
            "theme_color": "#0d1117",
            "icons": [
                {
                    "src": "/static/icon.png",
                    "sizes": "192x192",
                    "type": "image/png"
                },
                {
                    "src": "/static/icon.png",
                    "sizes": "512x512",
                    "type": "image/png"
                }
            ]
        }
        return jsonify(manifest_data)

    @app.route("/sw.js")
    def service_worker():
        sw_code = """
        const CACHE_NAME = 'instaauto-v1';
        self.addEventListener('install', (e) => {
            self.skipWaiting();
        });
        self.addEventListener('activate', (e) => {
            e.waitUntil(clients.claim());
        });
        self.addEventListener('fetch', (e) => {
            e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
        });
        """
        return sw_code, 200, {"Content-Type": "application/javascript"}

    # -------------------------------------------------------------
    # Authentication Endpoints (Direct UI Login & 2FA without Code)
    # -------------------------------------------------------------
    @app.route("/api/auth/status")
    def auth_status():
        is_logged_in = bot_service.client.is_session_valid() if bot_service else False
        config = load_config()
        return jsonify({
            "is_logged_in": is_logged_in,
            "username": bot_service.client.username if bot_service else config.ig_username,
            "user_id": bot_service.client.user_id if bot_service else None
        })

    @app.route("/api/auth/login", methods=["POST"])
    def auth_login():
        data = request.json or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        code = data.get("verification_code", "").strip() or None

        if not username and not bot_service.client.username:
            return jsonify({"status": "error", "message": "Please enter your Instagram username."}), 400

        config = load_config()
        raw = config.raw

        # Save credentials automatically to config
        if username:
            raw["instagram"]["username"] = username
        if password:
            raw["instagram"]["password"] = password
        save_config(raw)

        target_user = username or raw["instagram"]["username"]
        target_pass = password or raw["instagram"]["password"]

        result = bot_service.client.login_with_credentials(target_user, target_pass, verification_code=code)
        return jsonify(result)

    @app.route("/api/auth/logout", methods=["POST"])
    def auth_logout():
        if bot_service:
            bot_service.client.logout()
        return jsonify({"status": "success", "message": "Logged out successfully and session deleted."})

    # -------------------------------------------------------------
    # Bot Control Endpoints
    # -------------------------------------------------------------
    @app.route("/api/stats")
    def api_stats():
        stats = db.get_summary_stats()
        stats["is_running"] = bot_service.is_running if bot_service else False
        stats["is_logged_in"] = bot_service.client.is_session_valid() if bot_service else False
        return jsonify(stats)

    @app.route("/api/logs")
    def api_logs():
        logs = db.get_recent_logs(30)
        return jsonify(logs)

    @app.route("/api/activity")
    def api_activity():
        activity = db.get_recent_activity(25)
        return jsonify(activity)

    @app.route("/api/bot/start", methods=["POST"])
    def api_bot_start():
        if bot_service:
            if not bot_service.is_running:
                bot_service.start_background()
                return jsonify({"status": "started", "message": "Bot background service started successfully."})
            return jsonify({"status": "already_running", "message": "Bot is already running."})
        return jsonify({"status": "error", "message": "Bot service not available."}), 500

    @app.route("/api/bot/stop", methods=["POST"])
    def api_bot_stop():
        if bot_service:
            if bot_service.is_running:
                bot_service.stop()
                return jsonify({"status": "stopped", "message": "Bot background service stopped."})
            return jsonify({"status": "not_running", "message": "Bot is not running."})
        return jsonify({"status": "error", "message": "Bot service not available."}), 500

    @app.route("/api/config/update", methods=["POST"])
    def api_config_update():
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data received."}), 400
        try:
            config = load_config()
            raw = config.raw

            # Optional API Key or Token
            if "api_key" in data:
                raw["instagram"]["api_key"] = data["api_key"]

            # Update limits
            if "max_dms_per_day" in data:
                raw["bot"]["max_dms_per_day"] = int(data["max_dms_per_day"])
            if "check_interval_min" in data:
                raw["bot"]["check_interval_min"] = int(data["check_interval_min"])
            if "check_interval_max" in data:
                raw["bot"]["check_interval_max"] = int(data["check_interval_max"])
            if "like_comment" in data:
                raw["bot"]["like_comment"] = bool(data["like_comment"])

            # Specific target post URL
            if "target_post_url" in data:
                url_val = data["target_post_url"].strip()
                raw["bot"]["target_posts"] = [url_val] if url_val else []

            # Update campaigns
            if raw.get("campaigns"):
                if "keywords" in data:
                    kw_list = [k.strip() for k in data["keywords"].split(",") if k.strip()]
                    raw["campaigns"][0]["keywords"] = kw_list
                if "follower_dm_template" in data:
                    raw["campaigns"][0]["follower_dm_template"] = data["follower_dm_template"]
                if "follower_comment_reply" in data:
                    raw["campaigns"][0]["follower_comment_reply"] = data["follower_comment_reply"]
                if "non_follower_comment_reply" in data:
                    raw["campaigns"][0]["non_follower_comment_reply"] = data["non_follower_comment_reply"]

            save_config(raw)

            # Reload bot config live
            if bot_service:
                bot_service.config = load_config()

            return jsonify({"status": "success", "message": "Settings saved successfully! No code changes needed."})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    return app
