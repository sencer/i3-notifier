from datetime import datetime

from .utils import strip_tags


class Config:
    pre_close_hooks = []
    post_close_hooks = []
    pre_action_hooks = []
    post_action_hooks = []

    # Ignore expiration by default.
    expires = False

    def should_apply(notification):
        # To group notifications and apply certain formatting inherit this
        # class and make sure should_apply(notification) is the first Config
        # that returns True to those notifications.
        return True

    def get_keys(notification):
        # Returns a tuple, each element of which corresponds to the group
        # name that the notification should be assigned at the
        # corresponding nesting level.
        return (notification.app_name or "_", notification.body)

    def update_notification(notification):
        # Edit the notification before saving it. By default no edits are
        # made.
        return notification

    def format_notification(notification):
        time = datetime.fromtimestamp(notification.created_at // 1e9).strftime("%H:%M")
        # Format the notification
        text = f"<b>{strip_tags(notification.summary)}</b> "
        text += f"<small>{time}</small>"
        text += f"<small> {notification.app_name}</small>"

        if notification.body:
            text += (
                "\n<i>"
                + strip_tags(notification.body.replace(r"\n", "").strip())
                + "</i>"
            )

        if notification.app_icon:
            return (
                text.encode("utf-8")
                + b"\x00icon\x1f"
                + notification.app_icon.encode("utf-8")
            )
        else:
            return text.encode("utf-8")
