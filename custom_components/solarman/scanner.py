import socket


class InverterScanner:
    def __init__(self):
        self._ipaddress = None
        self._serial = None
        self._mac = None

    def _discover_inverters(self):
        request = "WIFIKIT-214028-READ"
        address = ("<broadcast>", 48899)
        try:
            with socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
            ) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.settimeout(1.0)

                sock.sendto(request.encode(), address)

                while True:
                    try:
                        data = sock.recv(1024)
                        a = data.decode().split(",")
                        if 3 == len(a):
                            self._ipaddress = a[0]
                            self._mac = a[1]
                            self._serial = int(a[2])
                    except socket.timout:
                        break
        except:
            return None

    def get_ipaddress(self):
        if not self._ipaddress:
            self._discover_inverters()
        return self._ipaddress

    def get_serialno(self):
        if not self._serial:
            self._discover_inverters()
        return self._serial
