class Config:
    def should_apply(notification):
        # To group notifications and apply certain formatting inherit this
        # class and make sure should_apply(notification) is the first Config
        # that returns True to those notifications.
        return True

    def get_keys(notification):
        # Returns a tuple, each element of which corresponds to the group
        # name that the notification should be assigned at the
        # corresponding nesting level.
        return (notification.app_name or "_",)

    def update_notification(notification):
        # Edit the notification before saving it. By default no edits are
        # made.
        return notification

    def format_notification(notification):
        # Format the notification
        text = f"<b>{notification.summary}</b> "
        text += f"<small>{notification.app_name}</small>"

        if notification.body:
            text += "\n<i>" + notification.body.replace(r"\n", "").strip() + "</i>"

        if notification.app_icon:
            return (
                text.encode("utf-8")
                + b"\x00icon\x1f"
                + notification.app_icon.encode("utf-8")
            )
        else:
            return text.encode("utf-8")
