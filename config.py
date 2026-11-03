import os
import re
import random
import shutil
from typing import List, Dict, Any, Optional
import yaml

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
EXAMPLE_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml.example")

def render_spintax(text: str, variables: Optional[Dict[str, str]] = None) -> str:
    """
    Resolves spintax patterns like {Option1|Option2|Option3} recursively
    and replaces variables like {username}, {my_username}, {keyword}.
    """
    if not text:
        return ""

    # Replace Spintax choices {A|B|C}
    pattern = re.compile(r"\{([^{}]+)\}")
    while True:
        match = pattern.search(text)
        if not match:
            break
        options = match.group(1).split("|")
        # If it's not a spintax with pipes (e.g. might be a variable placeholder {username})
        if "|" in match.group(1):
            chosen = random.choice(options).strip()
            text = text[:match.start()] + chosen + text[match.end():]
        else:
            # Leave lone {variable} for variable substitution stage
            # Temporarily replace with temporary token to avoid infinite loop
            text = text[:match.start()] + f"__VAR__{match.group(1)}__" + text[match.end():]

    # Restore variable tokens
    text = re.sub(r"__VAR__([a-zA-Z0-9_]+)__", r"{\1}", text)

    # Replace variable placeholders
    if variables:
        for key, val in variables.items():
            text = text.replace(f"{{{key}}}", str(val))

    return text.strip()


class CampaignRule:
    def __init__(self, data: Dict[str, Any]):
        self.name: str = data.get("name", "Unnamed Campaign")
        self.keywords: List[str] = [k.strip().lower() for k in data.get("keywords", []) if k.strip()]
        self.follower_dm_template: str = data.get("follower_dm_template", "")
        self.follower_comment_reply: str = data.get("follower_comment_reply", "")
        self.non_follower_comment_reply: str = data.get("non_follower_comment_reply", "")
        self.send_dm_to_non_followers: bool = bool(data.get("send_dm_to_non_followers", False))
        self.non_follower_dm_template: str = data.get("non_follower_dm_template", "")

    def matches(self, comment_text: str) -> Optional[str]:
        """
        Checks if the comment contains any of the configured keywords.
        Returns the matched keyword or None.
        """
        cleaned = comment_text.lower()
        for kw in self.keywords:
            # Word boundary or substring check
            # Match if standalone word or clearly mentioned
            pattern = rf"(^|\s|#|@){re.escape(kw)}(\s|$|[!?,.;:]+)"
            if re.search(pattern, cleaned) or kw in cleaned:
                return kw
        return None


class Config:
    def __init__(self, config_dict: Dict[str, Any]):
        self.raw = config_dict
        
        # Instagram credentials
        ig_section = config_dict.get("instagram", {})
        self.ig_username: str = str(ig_section.get("username", "")).strip()
        self.ig_password: str = str(ig_section.get("password", "")).strip()
        self.session_file: str = ig_section.get("session_file", "session.json")

        # Bot runtime configuration
        bot_section = config_dict.get("bot", {})
        self.monitor_latest_posts_count: int = int(bot_section.get("monitor_latest_posts_count", 3))
        self.target_posts: List[str] = bot_section.get("target_posts", [])
        self.check_interval_min: int = int(bot_section.get("check_interval_min", 60))
        self.check_interval_max: int = int(bot_section.get("check_interval_max", 120))
        self.action_delay_min: int = int(bot_section.get("action_delay_min", 4))
        self.action_delay_max: int = int(bot_section.get("action_delay_max", 9))
        self.max_dms_per_day: int = int(bot_section.get("max_dms_per_day", 50))
        self.like_comment: bool = bool(bot_section.get("like_comment", True))

        # Campaigns
        campaigns_data = config_dict.get("campaigns", [])
        self.campaigns: List[CampaignRule] = [CampaignRule(c) for c in campaigns_data]

        # Web UI
        web_section = config_dict.get("web_ui", {})
        self.web_enabled: bool = bool(web_section.get("enabled", True))
        self.web_host: str = str(web_section.get("host", "0.0.0.0"))
        self.web_port: int = int(web_section.get("port", 8080))

    def find_matching_campaign(self, comment_text: str) -> Optional[tuple[CampaignRule, str]]:
        """
        Finds the first campaign rule matching the comment.
        Returns (rule, matched_keyword) or None.
        """
        for campaign in self.campaigns:
            kw = campaign.matches(comment_text)
            if kw:
                return campaign, kw
        return None


def load_config() -> Config:
    """Loads config.yaml, initializing it from config.yaml.example if needed."""
    if not os.path.exists(CONFIG_PATH):
        if os.path.exists(EXAMPLE_CONFIG_PATH):
            shutil.copy(EXAMPLE_CONFIG_PATH, CONFIG_PATH)
            print(f"[Config] Created '{CONFIG_PATH}' from example template.")
        else:
            raise FileNotFoundError(f"Neither '{CONFIG_PATH}' nor '{EXAMPLE_CONFIG_PATH}' exists.")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return Config(data)

def save_config(data: Dict[str, Any]) -> None:
    """Saves updated dictionary back to config.yaml."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
