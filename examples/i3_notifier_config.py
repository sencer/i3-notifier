from i3notifier.config import Config


def chromeapp_class(title, url, icon=None, use_body=True, make_closeable=False):
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
            return title, str(notification.body if use_body else notification.summary)

    return ChromeApp


config_list = [
    chromeapp_class("WhatsApp", "web.whatsapp.com", "web-whatsapp", False, True),
    chromeapp_class("Gmail", "mail.google.com", "gmail"),
    chromeapp_class("Chat", "chat.google.com", "chat"),
    chromeapp_class("Meet", "meet.google.com", "meet"),
    chromeapp_class("Twitter", "twitter.com", "twitter"),
]
