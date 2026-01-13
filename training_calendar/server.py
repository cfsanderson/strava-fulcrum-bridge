#!/usr/bin/env python3
"""
Simple HTTP server to serve the training calendar for subscription.
Runs on port 8080.

Usage:
    python3 calendar/server.py [port]

Default port: 8080
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
import sys
import socket


class CalendarHandler(SimpleHTTPRequestHandler):
    """Handler for serving the calendar file with proper headers."""

    def do_GET(self):
        """Handle GET requests for the calendar file."""
        if self.path == '/training_calendar.ics' or self.path == '/' or self.path == '':
            # Serve the calendar file
            calendar_path = 'training_calendar.ics'

            if not os.path.exists(calendar_path):
                self.send_error(404, "Calendar file not found. Run: python3 calendar/generator.py")
                return

            try:
                with open(calendar_path, 'rb') as f:
                    content = f.read()

                self.send_response(200)
                self.send_header('Content-Type', 'text/calendar; charset=utf-8')
                self.send_header('Content-Disposition', 'inline; filename="training_calendar.ics"')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Expires', '0')
                self.end_headers()

                self.wfile.write(content)
            except Exception as e:
                self.send_error(500, f"Error serving calendar: {e}")
        else:
            self.send_error(404, "Not Found. Use: /training_calendar.ics")

    def log_message(self, format, *args):
        """Log requests with timestamp."""
        sys.stdout.write(f"[{self.log_date_time_string()}] {format % args}\n")


def get_local_ip():
    """Get the local IP address of this machine."""
    try:
        # Create a socket connection to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "raspberrypi.local"


def run_server(port=8080):
    """Run the calendar HTTP server."""

    # Change to calendar directory
    calendar_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(calendar_dir)

    # Check if calendar file exists
    if not os.path.exists('training_calendar.ics'):
        print("⚠️  Warning: Calendar file not found!")
        print("   Run: python3 calendar/generator.py")
        print()

    server_address = ('', port)

    try:
        httpd = HTTPServer(server_address, CalendarHandler)
    except OSError as e:
        if e.errno == 98:  # Address already in use
            print(f"✗ Port {port} is already in use.")
            print(f"  Try a different port or stop the existing service:")
            print(f"  sudo systemctl stop training-calendar.service")
            sys.exit(1)
        else:
            raise

    local_ip = get_local_ip()

    print(f"✓ Training Calendar Server")
    print(f"  Running on port {port}")
    print()
    print(f"📱 Subscribe in Apple Calendar:")
    print(f"   http://{local_ip}:{port}/training_calendar.ics")
    print(f"   or")
    print(f"   http://raspberrypi.local:{port}/training_calendar.ics")
    print()
    print(f"🔗 Test in browser:")
    print(f"   http://localhost:{port}/training_calendar.ics")
    print()
    print(f"Press Ctrl+C to stop")
    print("-" * 60)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n✓ Server stopped")
        sys.exit(0)


if __name__ == '__main__':
    port = 8080

    # Allow custom port from command line
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port: {sys.argv[1]}")
            print("Usage: python3 calendar/server.py [port]")
            sys.exit(1)

    run_server(port)
