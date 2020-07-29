# i3 Notification Manager

This is a notification manager for i3 desktop environment inspired by 
[Rofication](https://github.com/DaveDavenport/Rofication). Like 
Rofication, it implements the Galago standard. 

Also see the companion py3status module 
[py3-notifier](https://github.com/sencer/py3-notifier).

## Differences from Rofication

- Notifications are stored in a tree structure, where they can be grouped 
  by, for example, the application that is sending the notification and 
  the subject. This is highly configurable. (No docs at the moment, but 
  see the `examples/i3_notifier_config.py`; also see the comments in 
  `i3notifier/config.py`)
- Allows bulk delete of notifications in a category.
- Implements "default" action.
- Shows icons.
- Does not use sockets, rather adds new dbus methods to show the 
  notifications and get the count of notifications.
- Code is modular, should be straight forward to use another GUI rather 
  than Rofi; or another data structure rather than tree structure.

## Grouping in action

### Top Level
![top level](/images/1.png)

### Expand Whatsapp
![level 1](/images/2.png)

### Expand Person1
![level 2](/images/3.png)

## Usage

To install (also see the requirements.txt)
    pip install i3-notifier

To launch GUI; bind this to a shortcut
    dbus-send --session --print-reply --dest=org.freedesktop.Notifications /org/freedesktop/Notifications org.freedesktop.Notifications.ShowNotifications

Then use Enter to expand group / execute action; Ctrl + Delete to delete 
notification or notification group and Esc to exit.

To get notification count & urgency
    dbus-send --session --print-reply=literal --dest=org.freedesktop.Notifications /org/freedesktop/Notifications org.freedesktop.Notifications.ShowNotificationCount

One can use this with i3blocks to show notifications in the bar
or even better switch to py3status and install 
[py3-notifier](https://github.com/sencer/py3-notifier).

    command = "(dbus-send --session --print-reply=literal --dest=org.freedesktop.Notifications /org/freedesktop/Notifications org.freedesktop.Notifications.ShowNotificationCount 2>/dev/null || ($HOME/.local/bin/i3-notifier && echo '? ? ?'))|tr -s ' '|cut -d' ' -f 3"
