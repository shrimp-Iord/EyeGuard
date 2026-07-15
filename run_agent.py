#!/usr/bin/env python3
"""Launcher for the session agent in the locked-down (split) build.

The managed LaunchAgent runs THIS file by its absolute path:
    <python> /Library/Application Support/EyeGuard/run_agent.py

Launching via an absolute script path (not `-m`) puts this directory first on
sys.path, so the real root-owned `eyeguard` package always wins over any
PYTHONPATH/cwd a forger might set. The vault daemon's peer check pins the socket
to exactly this invocation, so nothing else can impersonate the agent.
"""
from eyeguard.menubar import main

if __name__ == "__main__":
    main()
