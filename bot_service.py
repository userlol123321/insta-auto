import time
import random
import threading
from typing import Optional
from config import Config, load_config, render_spintax
from database import Database
from instagram_client import InstagramClient

class BotService:
    def __init__(self, config: Optional[Config] = None, db: Optional[Database] = None):
        self.config = config or load_config()
        self.db = db or Database()
        self.client = InstagramClient(
            username=self.config.ig_username,
            password=self.config.ig_password,
            session_file=self.config.session_file,
            logger=self.db
        )
        self.is_running = False
        self._stop_event = threading.Event()
        self.worker_thread: Optional[threading.Thread] = None

    def _sleep_with_stop(self, seconds: float) -> bool:
        """Sleeps in short chunks so thread can exit immediately when stopped."""
        end_time = time.time() + seconds
        while time.time() < end_time:
            if self._stop_event.is_set():
                return False
            time.sleep(0.5)
        return True

    def process_cycle(self) -> None:
        """Executes one scan cycle across targeted posts."""
        today_dms = self.db.get_daily_dm_count()
        if today_dms >= self.config.max_dms_per_day:
            self.db.log_event(
                "WARNING",
                f"Daily DM quota reached ({today_dms}/{self.config.max_dms_per_day}). Skipping DMs until tomorrow."
            )
            return

        media_ids = self.client.get_target_media_ids(
            self.config.target_posts,
            self.config.monitor_latest_posts_count
        )

        if not media_ids:
            self.db.log_event("WARNING", "No active media posts found to monitor.")
            return

        self.db.log_event("INFO", f"Scanning {len(media_ids)} post(s) for new comments...")

        for media_id in media_ids:
            if self._stop_event.is_set():
                break

            comments = self.client.get_media_comments(media_id, amount=40)
            for comment in comments:
                if self._stop_event.is_set():
                    break

                comment_id = str(comment.pk)
                commenter_id = str(comment.user.pk)
                commenter_username = comment.user.username
                comment_text = comment.text.strip()

                # Ignore already handled comments
                if self.db.is_comment_processed(comment_id):
                    continue

                # Ignore comments posted by the bot account itself
                if str(commenter_id) == str(self.client.user_id):
                    self.db.record_processed_comment(
                        comment_id=comment_id,
                        media_id=media_id,
                        user_id=commenter_id,
                        username=commenter_username,
                        comment_text=comment_text,
                        matched_keyword="SELF",
                        is_follower=True,
                        status_message="Ignored own comment"
                    )
                    continue

                # Check if comment matches any campaign keyword
                match_result = self.config.find_matching_campaign(comment_text)

                if not match_result:
                    # Not a matching keyword. Mark as processed so we don't inspect it again.
                    self.db.record_processed_comment(
                        comment_id=comment_id,
                        media_id=media_id,
                        user_id=commenter_id,
                        username=commenter_username,
                        comment_text=comment_text,
                        matched_keyword="",
                        is_follower=False,
                        status_message="No keyword match"
                    )
                    continue

                campaign, matched_keyword = match_result
                self.db.log_event(
                    "INFO",
                    f"Matched keyword '{matched_keyword}' from @{commenter_username}: '{comment_text}'"
                )

                # Randomized human-like delay before inspecting/responding
                delay = random.uniform(self.config.action_delay_min, self.config.action_delay_max)
                if not self._sleep_with_stop(delay):
                    break

                # STEP 1: Verify whether the commenter is an active follower
                is_follower = self.client.is_user_following_me(commenter_id)
                self.db.log_event(
                    "INFO",
                    f"Follower check for @{commenter_username}: {'FOLLOWER' if is_follower else 'NOT FOLLOWING'}"
                )

                vars_dict = {
                    "username": commenter_username,
                    "my_username": self.client.username,
                    "keyword": matched_keyword
                }

                # Optionally like the comment
                if self.config.like_comment:
                    self.client.like_comment(comment_id)

                if is_follower:
                    # ==========================================
                    # FOLLOWER FLOW: Deliver link in DM!
                    # ==========================================
                    dm_text = render_spintax(campaign.follower_dm_template, vars_dict)
                    dm_success = self.client.send_dm(commenter_id, dm_text)

                    reply_success = False
                    if campaign.follower_comment_reply:
                        reply_text = render_spintax(campaign.follower_comment_reply, vars_dict)
                        # Small delay between DM and comment reply
                        time.sleep(random.uniform(2, 4))
                        reply_success = self.client.reply_to_comment(media_id, comment_id, reply_text)

                    status = "Delivered DM link to follower" if dm_success else "Failed sending DM"
                    self.db.record_processed_comment(
                        comment_id=comment_id,
                        media_id=media_id,
                        user_id=commenter_id,
                        username=commenter_username,
                        comment_text=comment_text,
                        matched_keyword=matched_keyword,
                        is_follower=True,
                        dm_sent=dm_success,
                        comment_replied=reply_success,
                        comment_liked=self.config.like_comment,
                        status_message=status
                    )

                    if dm_success:
                        self.db.increment_daily_stat("dms_sent")
                        self.db.increment_daily_stat("followers_served")
                    if reply_success:
                        self.db.increment_daily_stat("comments_replied")

                else:
                    # ==========================================
                    # NON-FOLLOWER FLOW: Block link, ask to follow
                    # ==========================================
                    reply_success = False
                    if campaign.non_follower_comment_reply:
                        reply_text = render_spintax(campaign.non_follower_comment_reply, vars_dict)
                        reply_success = self.client.reply_to_comment(media_id, comment_id, reply_text)

                    dm_success = False
                    if campaign.send_dm_to_non_followers and campaign.non_follower_dm_template:
                        non_follower_dm = render_spintax(campaign.non_follower_dm_template, vars_dict)
                        time.sleep(random.uniform(2, 4))
                        dm_success = self.client.send_dm(commenter_id, non_follower_dm)
                        if dm_success:
                            self.db.increment_daily_stat("dms_sent")

                    self.db.record_processed_comment(
                        comment_id=comment_id,
                        media_id=media_id,
                        user_id=commenter_id,
                        username=commenter_username,
                        comment_text=comment_text,
                        matched_keyword=matched_keyword,
                        is_follower=False,
                        dm_sent=dm_success,
                        comment_replied=reply_success,
                        comment_liked=self.config.like_comment,
                        status_message="Blocked link (Not a follower) - prompt sent"
                    )

                    self.db.increment_daily_stat("non_followers_blocked")
                    if reply_success:
                        self.db.increment_daily_stat("comments_replied")

                # Sleep slightly after finishing action on a comment
                time.sleep(random.uniform(3, 6))

    def run_loop(self) -> None:
        """Main service loop running 24/7."""
        self.is_running = True
        self._stop_event.clear()
        self.db.log_event("INFO", "Instagram Automator service started.")

        # Ensure login
        if not self.client.login():
            self.db.log_event("ERROR", "Initial login failed. Service cannot proceed.")
            self.is_running = False
            return

        while not self._stop_event.is_set():
            try:
                self.process_cycle()
            except Exception as e:
                self.db.log_event("ERROR", f"Unexpected cycle error: {str(e)}")

            if self._stop_event.is_set():
                break

            interval = random.randint(self.config.check_interval_min, self.config.check_interval_max)
            self.db.log_event("INFO", f"Sleeping for {interval}s before next scan cycle...")
            if not self._sleep_with_stop(interval):
                break

        self.is_running = False
        self.db.log_event("INFO", "Instagram Automator service stopped.")

    def start_background(self) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            return
        self.worker_thread = threading.Thread(target=self.run_loop, daemon=True)
        self.worker_thread.start()

    def stop(self) -> None:
        self.db.log_event("INFO", "Stopping automator service...")
        self._stop_event.set()
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
        self.is_running = False
