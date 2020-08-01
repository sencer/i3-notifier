import html
import threading
from html.parser import HTMLParser
from io import StringIO


class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = StringIO()

    def handle_data(self, d):
        self.text.write(d)

    def get_data(self):
        return self.text.getvalue()


def strip_tags(data):
    s = MLStripper()
    s.feed(html.escape(data))
    return s.get_data()


class RunAsync(threading.Thread):

    __slots__ = "args", "kwargs", "closure"

    def __init__(self, closure, *args, **kwargs):
        self.closure = closure
        self.args = args
        self.kwargs = kwargs
        threading.Thread.__init__(self)

    def run(self):
        return self.closure(*self.args, **self.kwargs)


class RunAsyncFactory:
    __slots__ = "closure"

    def __init__(self, closure):
        self.closure = closure

    def __call__(self, *args, **kwargs):
        return RunAsync(self.closure, *args, **kwargs).start()
