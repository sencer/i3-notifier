from i3ipc import Connection, Event


class I3:
    def __init__(self):
        self.i3 = Connection()

    def process_action(self, action):
        def switch_to_urgent(i3, data):
            i3.command(f"workspace {data.current.name}")
            i3.off(switch_to_urgent)

        self.i3.on(Event.WORKSPACE_URGENT, switch_to_urgent)
        action()
        self.i3.main(0.5)
