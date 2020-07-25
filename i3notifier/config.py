class Config:
    def should_apply(notification):
        return True

    def get_key(notification):
        return notification.app_name or "_"

    def get_keys(notification):
        return (notification.app_name or "_",)

    def update_notification(notification):
        return notification

    def sort_fn(notification):
        return lambda ns: sorted(ns, key=lambda x: x.created_at)

    def format_notification(notification):
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
