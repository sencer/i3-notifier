from i3notifier.config import Config

def chromeapp_class(title, url, icon=None, make_closeable=True):
    kChrome = "Google Chrome"
    kURL = f'<a href="https://{url}/">{url}</a>'
    lURL = len(kURL)
    icon = icon or "chrome"

    class ChromeApp(Config):
        def should_apply(notification):
            return (
                notification.body.startswith(kURL) and notification.app_name == kChrome
            )

        def update_notification(notification):
            notification.body = notification.body[lURL:].strip()
            notification.app_name = title
            notification.app_icon = icon

        def closeable(notification):
            return make_closeable

        def get_keys(notification):
            return title, str(notification.summary)

    return ChromeApp


config_list = [
    chromeapp_class("WhatsApp", "web.whatsapp.com", "web-whatsapp", True),
    chromeapp_class("Gmail", "mail.google.com", "gmail", False),
    chromeapp_class("Chat", "chat.google.com", "chat", False),
    chromeapp_class("Meet", "meet.google.com", "meet", False),
    chromeapp_class("Twitter", "twitter.com", "twitter", False),
]
