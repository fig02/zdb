# zdb
A gdb-like interface for Ocarina of Time Master Quest debug version in [Project64](https://www.pj64-emu.com/). Requires a linker map file to locate functions.

Currently supports managing function breakpoints, including handling overlays transparently.

# Install
1) Clone this repository.
2) Provide the missing information in `zdb.cfg_stub` and rename the file to `zdb.cfg`.
3) Copy `zdbServer.js` to the `Scripts` directory located in the same directory as your installation of Project64. If you haven't used a script with Project64 before, you may need to create the `Scripts` directory yourself.

# Usage
1) Run `zdbServer.js` from Project64's Debugger->Scripts menu.
2) Run `zdb.py` from your favorite terminal.
3) Type `help` to see what commands you can use.

# Known Issues
zdb cannot detect when a save state is loaded in Project64, so breakpoints for overlay functions set before a save state is loaded may be inaccurate after loading. Deleting and setting the problematic breakpoints again will fix the issue.
