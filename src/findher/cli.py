import argparse
import json
import sys
from . import core

def main():
    parser = argparse.ArgumentParser(prog='findher', description='Find processes and their windows.')
    sub = parser.add_subparsers(dest='action', required=True)
    for name in ('processes', 'windows'):
        p = sub.add_parser(name)
        p.add_argument('--name', help='Case-insensitive name or window title substring')
        p.add_argument('--pid', type=int)
    p = sub.add_parser('launch', help='Launch an executable without a shell')
    p.add_argument('--wait', type=float, default=2)
    p.add_argument('command', nargs=argparse.REMAINDER, help='Executable and arguments, after --')
    sub.add_parser('mcp', help='Run the MCP server over stdio')
    args = parser.parse_args()
    try:
        if args.action == 'mcp':
            from .server import main as server_main
            server_main()
            return
        if args.action == 'launch':
            command = args.command
            if command and command[0] == '--':
                command = command[1:]
            result = core.launch(command, args.wait)
        else:
            result = getattr(core, args.action)(args.name, args.pid)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (core.FindHerError, ImportError) as exc:
        print(f'FindHer: {exc}', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
