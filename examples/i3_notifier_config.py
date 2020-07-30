import subprocess
import time

from i3notifier.config import Config
from i3notifier.utils import RunAsyncFactory


class DefaultConfig(Config):
    pre_action_hooks = [
        # Start a script to listen for urgent workspaces & switch to it
        RunAsyncFactory(lambda n: subprocess.call("switch-to-urgent.py")),
        # Wait for the script become available
        lambda n: time.sleep(0.2),
    ]


def ChromeAppFactory(title, url, icon=None, second_key="body"):
    kChrome = "Google Chrome"
    kURL = f'<a href="https://{url}/">{url}</a>'
    lURL = len(kURL)
    icon = icon or "chrome"

    class ChromeApp(DefaultConfig):
        def should_apply(notification):
            return (
                notification.body.startswith(kURL) and notification.app_name == kChrome
            )

        def update_notification(notification):
            notification.body = notification.body[lURL:].strip()
            notification.app_name = title
            notification.app_icon = icon

        def get_keys(notification):
            return title, str(getattr(notification, second_key))

    return ChromeApp


Gmail = ChromeAppFactory("Gmail", "mail.google.com", "gmail")
Gmail.pre_close_hooks = ["ignore"]


config_list = [
    Gmail,
    ChromeAppFactory("WhatsApp", "web.whatsapp.com", "web-whatsapp", "summary"),
    ChromeAppFactory("Chat", "chat.google.com", "chat"),
    ChromeAppFactory("Meet", "meet.google.com", "meet"),
    ChromeAppFactory("Twitter", "twitter.com", "twitter"),
    ChromeAppFactory("Instagram", "instagram.com", "twitter"),
    DefaultConfig,
]
