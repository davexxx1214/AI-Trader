#!/usr/bin/env python3
"""
AI-Trader Web UI Launcher

A cross-platform script to start the Web UI server.
Supports both Windows and Linux/macOS.

Usage:
    python scripts/start_ui.py                  # Default: backtest mode (agent_data)
    python scripts/start_ui.py --mode backtest  # Backtest mode (agent_data)
    python scripts/start_ui.py --mode live      # Live trading mode (agent_data_live)
    python scripts/start_ui.py --mode alpaca    # Alpaca backtest mode (agent_data_alpaca)
    python scripts/start_ui.py --port 8080      # Custom port

Arguments:
    --mode, -m    Data mode: 'backtest' (default), 'live', or 'alpaca'
    --port, -p    Server port (default: 8888)
"""

import argparse
import http.server
import os
import socketserver
import sys
import webbrowser
from functools import partial
from pathlib import Path


class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler with quieter logging"""
    
    def log_message(self, format, *args):
        # Only log non-200 requests to reduce noise
        if args and '200' not in str(args[0]):
            super().log_message(format, *args)


def main():
    parser = argparse.ArgumentParser(
        description='Start AI-Trader Web UI server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    python scripts/start_ui.py                  # Default backtest mode
    python scripts/start_ui.py --mode live      # Live trading data
    python scripts/start_ui.py --mode alpaca    # Alpaca backtest data
    python scripts/start_ui.py -m live -p 9000  # Live mode on port 9000
        '''
    )
    parser.add_argument(
        '--mode', '-m',
        choices=['backtest', 'live', 'alpaca'],
        default='backtest',
        help='Data mode: backtest (agent_data), live (agent_data_live), or alpaca (agent_data_alpaca)'
    )
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=8888,
        help='Server port (default: 8888)'
    )
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='Do not automatically open browser'
    )
    
    args = parser.parse_args()
    
    # Get project root directory
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent
    data_dir = project_root / 'data'
    
    if not data_dir.exists():
        print(f"❌ Error: Data directory not found: {data_dir}")
        sys.exit(1)
    
    # Change to data directory
    os.chdir(data_dir)
    
    # Determine config file based on mode
    if args.mode == 'live':
        config_param = "?config=config_live.yaml"
    elif args.mode == 'alpaca':
        config_param = "?config=config_alpaca.yaml"
    else:
        config_param = ""
    url = f"http://localhost:{args.port}/index.html{config_param}"
    
    # Print startup info
    mode_emoji = "📊" if args.mode == 'backtest' else ("🔴" if args.mode == 'live' else "🦙")
    mode_name = "Backtest" if args.mode == 'backtest' else ("Live Trading" if args.mode == 'live' else "Alpaca Backtest")
    data_source = "agent_data" if args.mode == 'backtest' else ("agent_data_live" if args.mode == 'live' else "agent_data_alpaca")
    
    print()
    print("=" * 60)
    print(f"🌐 AI-Trader Web UI Server")
    print("=" * 60)
    print(f"{mode_emoji} Mode: {mode_name}")
    print(f"📁 Data Source: {data_source}")
    print(f"🔗 URL: {url}")
    print("-" * 60)
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    print()
    
    # Create handler with directory
    handler = partial(QuietHTTPRequestHandler, directory=str(data_dir))
    
    try:
        with socketserver.TCPServer(("", args.port), handler) as httpd:
            # Open browser if not disabled
            if not args.no_browser:
                try:
                    webbrowser.open(url)
                except Exception:
                    pass  # Ignore browser opening errors
            
            print(f"✅ Server started on port {args.port}")
            print(f"🌐 Access: {url}")
            print()
            httpd.serve_forever()
            
    except OSError as e:
        if "Address already in use" in str(e) or "通常每个套接字地址" in str(e):
            print(f"❌ Error: Port {args.port} is already in use.")
            print(f"   Try a different port: python scripts/start_ui.py -p 9000")
        else:
            print(f"❌ Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped")
        sys.exit(0)


if __name__ == '__main__':
    main()

