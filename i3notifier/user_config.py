import importlib.util
import logging
import os

logger = logging.getLogger(__name__)


class UserConfig:
    config_list = []
    theme = None


def read_user_config():

    config_path = os.path.join(
        os.environ["XDG_CONFIG_HOME"]
        if "XDG_CONFIG_HOME" in os.environ
        else os.path.join(os.environ["HOME"], ".config"),
        "i3",
        "i3_notifier_config.py",
    )

    if os.path.exists(config_path):
        logger.info(f"Loading user config from {config_path}")
        spec = importlib.util.spec_from_file_location("i3_notifier_config", config_path)
        userconfig = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(userconfig)
        return userconfig
    logger.info(f"File not found: {config_path}")


def get_user_config():
    userconfig = UserConfig()
    userconfig_ = read_user_config()

    if userconfig_ is not None:
        if hasattr(userconfig_, "config_list"):
            userconfig.config_list = userconfig_.config_list

        if hasattr(userconfig_, "theme"):
            userconfig.theme = userconfig_.theme

    return userconfig
