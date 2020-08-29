# i3 Notification Manager (Requires a recent version of rofi)

This is a notification manager for i3 desktop environment inspired by 
[Rofication](https://github.com/DaveDavenport/Rofication). Like 
Rofication, it implements the [Gnome Desktop Notifications 
Standard](https://developer.gnome.org/notification-spec/) standard. 

Also see the companion py3status module 
[py3-notifier](https://github.com/sencer/py3-notifier).

## Differences from Rofication

- Notifications are stored in a tree structure, where they can be grouped 
  by, for example, the application that is sending the notification and 
  the subject. This is highly configurable. (No docs at the moment, but 
  see the `examples/i3_notifier_config.py`; also see the comments in 
  `i3notifier/config.py`)
- Allows bulk deletion of notifications in a category.
- Implements "default" action.
- Shows icons.
- Does not use sockets, rather adds new dbus methods to show the 
  notifications and get the count of notifications.
- Code is modular, should be straight forward to use another GUI rather 
  than Rofi; or another data structure rather than tree structure.

## What does it look like?

![animation](/images/widget.gif)

## Usage

To install (also see the requirements.txt)

    pip install i3-notifier
    
Make sure you are not running any other notification daemon (if you are running `dunst` for example, kill it with `killall dunst`). Then start `i3-notifier`. You might want to make sure `i3-notifier` and its companion script `switch-to-urgent.py` are in the `$PATH`. You can confirm it is running by

    dbus-send --session --print-reply --dest=org.freedesktop.Notifications /org/freedesktop/Notifications org.freedesktop.Notifications.GetServerInformation

Then to launch GUI; bind this to a shortcut

    dbus-send --session --print-reply --dest=org.freedesktop.Notifications /org/freedesktop/Notifications org.freedesktop.Notifications.ShowNotifications

## Keybindings
|                  Key                        |               Action                |
|--------------------------------------------:|-------------------------------------|
`j`, `Down`, `Tab` or `Ctrl-N`                | Choose next
`k`, `Up` or `Ctrl-P`                         | Choose previous
`Enter`, `Space` or `Left Click`              | Expand if group; execute action if singleton
`Shift-Enter`                                 | Execute action
`Esc`, `Ctrl+[` or `Backspace`                | One level up or exit from top level
`` ` ``, `Ctrl+Backspace` or `Shift-Backspace`| Exit from any level.
`Delete`                                      | Delete notification or group

To get notification count & urgency

    dbus-send --session --print-reply=literal --dest=org.freedesktop.Notifications /org/freedesktop/Notifications org.freedesktop.Notifications.ShowNotificationCount

One can use this with i3blocks to show notifications in the bar
or even better switch to py3status and install 
[py3-notifier](https://github.com/sencer/py3-notifier).

    command = "(dbus-send --session --print-reply=literal --dest=org.freedesktop.Notifications /org/freedesktop/Notifications org.freedesktop.Notifications.ShowNotificationCount 2>/dev/null || ($HOME/.local/bin/i3-notifier && echo '? ? ?'))|tr -s ' '|cut -d' ' -f 3"
