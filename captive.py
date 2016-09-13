import socket
import network
import time
import machine

ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid="Change my LED", authmode=1)

# PINs (5, 4, 0)
p1 = machine.Pin(5, machine.Pin.OUT, machine.Pin.PULL_UP)
p2 = machine.Pin(4, machine.Pin.OUT, machine.Pin.PULL_UP)
p3 = machine.Pin(0, machine.Pin.OUT, machine.Pin.PULL_UP)



CONTENT = b"""\
HTTP/1.0 200 OK

Hello #%d from MicroPython!
"""

class DNSQuery:
  def __init__(self, data):
    self.data=data
    self.dominio=''

    print("Reading datagram data...")
    m = data[2] # ord(data[2])
    tipo = (m >> 3) & 15   # Opcode bits
    if tipo == 0:                     # Standard query
      ini=12
      lon=data[ini] # ord(data[ini])
      while lon != 0:
        self.dominio+=data[ini+1:ini+lon+1].decode("utf-8") +'.'
        ini+=lon+1
        lon=data[ini] #ord(data[ini])

  def respuesta(self, ip):
    packet=b''
    print("Resposta {} == {}".format(self.dominio, ip))
    if self.dominio:
      packet+=self.data[:2] + b"\x81\x80"
      packet+=self.data[4:6] + self.data[4:6] + b'\x00\x00\x00\x00'   # Questions and Answers Counts
      packet+=self.data[12:]                                         # Original Domain Name Question
      packet+= b'\xc0\x0c'                                             # Pointer to domain name
      packet+= b'\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04'             # Response type, ttl and resource data length -> 4 bytes
      packet+=bytes(map(int,ip.split('.'))) # 4 bytes of IP
    return packet

def start():

    # DNS Server
    ip=ap.ifconfig()[0]
    print('DNS Server: dom.query. 60 IN A {:s}'.format(ip))

    udps = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udps.setblocking(False)
    udps.bind(('',53))

    # Web Server
    s = socket.socket()
    ai = socket.getaddrinfo(ip, 80)
    print("Web Server: Bind address info:", ai)
    addr = ai[0][-1]

    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(3)
    s.setblocking(False)
    print("Web Server: Listening http://{}:80/".format(ip))

    counter = 0

    try:
        while 1:
            # DNS Loop
            print("Before DNS...")
            try:
                data, addr = udps.recvfrom(1024)
                print("incomming datagram...")
                p=DNSQuery(data)
                udps.sendto(p.respuesta(ip), addr)
                print('Replying: {:s} -> {:s}'.format(p.dominio, ip))
            except:
                print("No dgram")

            # Web loop
            print("before accept...")
            try:
                res = s.accept()
                client_sock = res[0]
                client_addr = res[1]
                print("Client address:", client_addr)
                print("Client socket:", client_sock)

                client_stream = client_sock

                print("Request:")
                req = client_stream.readline()
                print(req)
                while True:
                    h = client_stream.readline()
                    if h == b"" or h == b"\r\n":
                        break
                    print(h)
                client_stream.write(CONTENT % counter)

                client_stream.close()
                counter += 1
            except:
                print("timeout for web... moving on...")
            print("loop")
            time.sleep_ms(300)
    except KeyboardInterrupt:
        print('Closing')
    udps.close()