import os
import json
import time
from typing import List, Optional, Any
from instagrapi import Client
from instagrapi.exceptions import (
    LoginRequired,
    TwoFactorRequired,
    ChallengeRequired,
    PleaseWaitFewMinutes,
    BadPassword,
    FeedbackRequired
)
from instagrapi.mixins.challenge import ChallengeChoice

class InstagramClient:
    def __init__(self, username: str, password: str, session_file: str = "session.json", logger=None):
        self.username = username
        self.password = password
        self.session_file = session_file
        self.logger = logger
        self.cl = Client()
        self.user_id = None
        
        # Configure client settings
        self.cl.delay_range = [2, 5]
        self.cl.challenge_code_handler = self._challenge_code_handler

    def _log(self, level: str, msg: str):
        if self.logger:
            self.logger.log_event(level, msg)
        else:
            print(f"[{level}] {msg}")

    def _challenge_code_handler(self, username: str, choice: ChallengeChoice):
        """
        Interactive callback when Instagram requires SMS or Email verification OTP.
        """
        method = "SMS" if choice == ChallengeChoice.SMS else "EMAIL"
        self._log("WARNING", f"Security Challenge detected! Instagram sent a verification code to your {method}.")
        try:
            code = input(f"Enter the Instagram verification code sent via {method}: ").strip()
            return code
        except Exception:
            return False

    def login(self) -> bool:
        """
        Logs in using cached session if valid, or performs a fresh login.
        """
        if not self.username or not self.password:
            self._log("ERROR", "Instagram username or password is missing in configuration.")
            return False

        # Attempt to load existing session
        if os.path.exists(self.session_file):
            try:
                self._log("INFO", f"Found existing session in '{self.session_file}'. Validating...")
                self.cl.load_settings(self.session_file)
                # Test if session is alive with a fast lightweight call
                self.cl.get_timeline_feed()
                self.user_id = self.cl.user_id
                self._log("INFO", f"Session restored successfully for @{self.username} (ID: {self.user_id}).")
                return True
            except (LoginRequired, Exception) as e:
                self._log("WARNING", f"Saved session expired or invalid ({str(e)}). Logging in again...")

        # Fresh login
        try:
            self._log("INFO", f"Logging into Instagram as @{self.username}...")
            self.cl.login(self.username, self.password)
            self.user_id = self.cl.user_id
            self.cl.dump_settings(self.session_file)
            self._log("INFO", f"Logged in successfully! Session saved to '{self.session_file}'.")
            return True

        except TwoFactorRequired:
            self._log("WARNING", "2FA / Two-Factor Authentication is enabled on this account.")
            code = input("Enter your 2FA Authenticator / SMS code: ").strip()
            try:
                self.cl.login(self.username, self.password, verification_code=code)
                self.user_id = self.cl.user_id
                self.cl.dump_settings(self.session_file)
                self._log("INFO", "2FA authentication successful! Session saved.")
                return True
            except Exception as ex:
                self._log("ERROR", f"Failed 2FA login: {str(ex)}")
                return False

    def login_with_credentials(self, username: str, password: str, verification_code: Optional[str] = None) -> dict:
        """
        Interactive/UI-friendly login method that returns status dictionary:
        {"status": "success" | "2fa_required" | "challenge_required" | "error", "message": str}
        """
        self.username = username
        self.password = password
        try:
            if verification_code:
                self._log("INFO", f"Submitting 2FA verification code for @{username}...")
                self.cl.login(username, password, verification_code=verification_code)
            else:
                self._log("INFO", f"Logging into Instagram as @{username} from UI...")
                self.cl.login(username, password)

            self.user_id = self.cl.user_id
            self.cl.dump_settings(self.session_file)
            self._log("INFO", f"Login successful for @{username}! Session saved.")
            return {"status": "success", "message": f"Successfully logged in as @{username}!"}

        except TwoFactorRequired:
            self._log("WARNING", "2FA required for login.")
            return {"status": "2fa_required", "message": "Two-Factor Authentication code required. Please enter your 6-digit 2FA code."}

        except ChallengeRequired:
            self._log("WARNING", "Security challenge required.")
            return {"status": "challenge_required", "message": "Instagram security challenge required. Check your SMS or email for the code."}

        except BadPassword:
            self._log("ERROR", "Incorrect Instagram password.")
            return {"status": "error", "message": "Incorrect Instagram password. Please check your credentials."}

        except PleaseWaitFewMinutes:
            self._log("ERROR", "Instagram rate-limited login.")
            return {"status": "error", "message": "Instagram requested to wait a few minutes. Please wait before retrying."}

        except Exception as e:
            self._log("ERROR", f"Login error: {str(e)}")
            return {"status": "error", "message": str(e)}

    def is_session_valid(self) -> bool:
        if not os.path.exists(self.session_file):
            return False
        try:
            self.cl.load_settings(self.session_file)
            self.cl.get_timeline_feed()
            self.user_id = self.cl.user_id
            return True
        except Exception:
            return False

    def logout(self) -> None:
        if os.path.exists(self.session_file):
            try:
                os.remove(self.session_file)
            except Exception:
                pass
        self.cl = Client()
        self.user_id = None
        self._log("INFO", "Logged out. Session cleared.")


    def get_target_media_ids(self, target_posts: List[str], latest_count: int = 3) -> List[str]:
        """
        Retrieves list of media PKs to monitor.
        If target_posts is populated, parses URLs or IDs.
        Otherwise fetches the user's latest N posts.
        """
        media_ids = []

        if target_posts:
            for item in target_posts:
                item_str = str(item).strip()
                if not item_str:
                    continue
                try:
                    if "instagram.com" in item_str:
                        media_pk = self.cl.media_pk_from_url(item_str)
                        media_ids.append(str(media_pk))
                    else:
                        media_ids.append(item_str)
                except Exception as e:
                    self._log("WARNING", f"Could not parse media target '{item_str}': {e}")
        else:
            try:
                self._log("INFO", f"Fetching latest {latest_count} posts for @{self.username}...")
                medias = self.cl.user_medias(self.user_id, amount=latest_count)
                for m in medias:
                    media_ids.append(str(m.pk))
            except Exception as e:
                self._log("ERROR", f"Error fetching latest posts: {e}")

        return media_ids

    def get_media_comments(self, media_id: str, amount: int = 50) -> List[Any]:
        """
        Fetches up to `amount` recent comments for a post/reel.
        """
        try:
            return self.cl.media_comments(media_id, amount=amount)
        except Exception as e:
            self._log("ERROR", f"Failed to fetch comments for media {media_id}: {e}")
            return []

    def is_user_following_me(self, user_id: str) -> bool:
        """
        CRITICAL CHECK: Queries Instagram friendship status to check if commenter
        is actively following the authenticated user.
        """
        try:
            friendship = self.cl.user_friendship_v1(int(user_id))
            return bool(friendship.followed_by)
        except Exception as e:
            self._log("WARNING", f"Could not determine friendship status for user {user_id}: {e}")
            return False

    def send_dm(self, user_id: str, text: str) -> bool:
        """
        Sends a Direct Message to a specific user.
        """
        try:
            self.cl.direct_send(text, user_ids=[int(user_id)])
            return True
        except FeedbackRequired as e:
            self._log("WARNING", f"Instagram feedback required/action block on DM: {e}")
            return False
        except Exception as e:
            self._log("ERROR", f"Failed to send DM to user {user_id}: {e}")
            return False

    def reply_to_comment(self, media_id: str, comment_id: str, text: str) -> bool:
        """
        Replies directly to a comment on a post/reel.
        """
        try:
            self.cl.media_comment(media_id, text, replied_to_comment_id=str(comment_id))
            return True
        except Exception as e:
            self._log("ERROR", f"Failed to reply to comment {comment_id}: {e}")
            return False

    def like_comment(self, comment_id: str) -> bool:
        """
        Likes a comment.
        """
        try:
            self.cl.comment_like(str(comment_id))
            return True
        except Exception as e:
            self._log("WARNING", f"Failed to like comment {comment_id}: {e}")
            return False
