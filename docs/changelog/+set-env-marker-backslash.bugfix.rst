A ``set_env`` value ending in a backslash no longer swallows the environment marker that follows it. The trailing
backslash escaped the ``;`` introducing the marker, so the marker was read as part of the value and silently stopped
applying.
