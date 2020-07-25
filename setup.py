from distutils.core import setup

setup(
    name="i3-notifier",
    version="0.2",
    description="A notification daemon for i3",
    author="Sencer Selcuk",
    packages=["i3notifier", "tests"],
    scripts=["bin/i3-notifier"],
)
