import asyncio
import contextlib
import functools
import http.server as hs
import socket
import websockets


class QuietHandler(hs.SimpleHTTPRequestHandler):
  def log_message(self, format, *args):
    pass  # Disable logging from the server

  def end_headers(self):
    # Prevent caching on the client (for both HTTP/1.0 and HTTP/1.1)
    custom_headers = {
      'Cache-Control': 'no-cache, must-revalidate, max-age=0',
      'Expires': '0',
      'Pragma': 'no-cache',
    }
    for header_name, header_value in custom_headers.items():
      self.send_header(header_name, header_value)

    return super().end_headers()

class DualStackServer(hs.ThreadingHTTPServer):
  '''Simple http server that binds to both IPv4 and IPv6 addresses.'''

  def __init__(self, address_family, *args, **kwargs):
    self.address_family = address_family
    super().__init__(*args, **kwargs)

  def server_bind(self):
    with contextlib.suppress(Exception):
      self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
    return super().server_bind()


def http_server(host, port, directory):
  '''A simple http server that serves content from a directory.

  `host`: the hostname to bind to.

  `port`: the port number to bind to.

  `directory`: the directory to serve files from.
  '''

  infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM, flags=socket.AI_PASSIVE)
  address_family, _, _, _, sockaddr = next(iter(infos))

  handler_class = functools.partial(QuietHandler, directory=directory)
  handler_class.protocol_version = 'HTTP/1.1'

  return DualStackServer(address_family, sockaddr, handler_class)

async def websocket_server(ws_handler, host, port):
  '''A general-purpose websocket server that runs until stopped.

  `ws_handler`: a coroutine that handles incoming websocket messages.
  The coroutine must receive arguments `websocket` and `stop_future`.

  `host`: the hostname to bind to.

  `port`: the port number to bind to.
  '''

  loop = asyncio.get_running_loop()
  stop_future = loop.create_future()

  ws_handler = functools.partial(ws_handler, stop_future=stop_future)

  async with websockets.serve(ws_handler, host, port):
    await stop_future # Run until stop future is resolved
