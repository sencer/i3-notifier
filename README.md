# i3 Notification Manager

This is a notification manager inspired by 
[Rofication](https://github.com/DaveDavenport/Rofication) for i3 desktop 
environment. As Rofication, it implements Galago standard. 

## Differences from Rofication

- Notifications are stored in a tree structure, where they can be grouped 
  by, for example, the application that is sending the notification and 
  the subject. This is highly configurable. (No docs at the moment, but 
  see the bin/i3-notifier and how it configures to match a number 
  different notification categories by new classes that inherit Config)
- Allows bulk delete of notifications in a category.
- Implements "default" action.
- Shows icons.
- Does not use sockets, rather adds new dbus methods to show the 
  notifications and get the count of notifications.
- Code is modular, should be straight forward to use another GUI rather 
  than Rofi; or another data structure rather than tree structure.

## Usage

    # To install (also see the requirements.txt)
    pip install i3-notifier

    # To launch GUI
    dbus-send --session --print-reply --dest=org.freedesktop.Notifications /org/freedesktop/Notifications org.freedesktop.Notifications.ShowNotifications

    # To get notification count
    dbus-send --session --print-reply=literal --dest=org.freedesktop.Notifications /org/freedesktop/Notifications org.freedesktop.Notifications.ShowNotificationCount
