from distutils.core import setup

setup(
    name="i3-notifier",
    version="0.18",
    description="A notification daemon for i3",
    author="Sencer Selcuk",
    packages=["i3notifier", "tests"],
    scripts=["bin/i3-notifier", "bin/switch-to-urgent.py"],
    package_data={"i3notifier": ["rofi-theme/*.rasi"]},
    include_package_data=True,
)
