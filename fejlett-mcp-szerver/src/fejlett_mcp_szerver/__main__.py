"""A python -m fejlett_mcp_szerver parancs ezt a fájlt indítja.

A Dockerfile ezt használja. Helyben ugyanez a main() fut, mint a
server.py végén: az hívja a mcp.run()-t.
"""

from fejlett_mcp_szerver.server import main

if __name__ == "__main__":
    main()
