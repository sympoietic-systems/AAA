import sys


def disable_quick_edit() -> None:
    """Disable QuickEdit Mode in Windows Console to prevent the application
    from suspending/freezing when the user clicks inside the terminal window.
    """
    if sys.platform != "win32":
        return

    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        # -10 corresponds to STD_INPUT_HANDLE
        h_stdin = kernel32.GetStdHandle(-10)
        if h_stdin == -1 or h_stdin is None:
            return

        mode = ctypes.c_uint()
        if kernel32.GetConsoleMode(h_stdin, ctypes.byref(mode)):
            # ENABLE_QUICK_EDIT_MODE is 0x0040. We clear this bit.
            # We also clear ENABLE_INSERT_MODE (0x0020) for consistency.
            new_mode = mode.value & ~0x0040 & ~0x0020
            # We must also include ENABLE_EXTENDED_FLAGS (0x0080) to apply the change to QuickEdit
            new_mode |= 0x0080
            kernel32.SetConsoleMode(h_stdin, new_mode)
    except Exception:
        # Fail silently if not in a standard console or if ctypes call fails
        pass
