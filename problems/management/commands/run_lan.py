import ipaddress
import socket
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Run one arena server for computers on the same Wi-Fi.'

    def add_arguments(self, parser):
        parser.add_argument('--port', type=int, default=8000)

    def handle(self, *args, **options):
        port = options['port']
        if not 1 <= port <= 65535:
            raise CommandError('Port must be between 1 and 65535.')
        addresses = set()
        try:
            for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
                address = info[4][0]
                if ipaddress.ip_address(address).is_private and not ipaddress.ip_address(address).is_loopback:
                    addresses.add(address)
        except OSError:
            pass
        self.stdout.write('Connect every computer to the same Wi-Fi. Players open:')
        for address in sorted(addresses):
            self.stdout.write(f'  http://{address}:{port}/')
        self.stdout.write('If no address works, run ipconfig and use the Wi-Fi IPv4 address.')
        self.stdout.write('Allow Python on Private networks in Windows Firewall. Guest Wi-Fi client isolation must be off.')
        self.stdout.write('Register and sign in with a username and password.')
        call_command('runserver', f'0.0.0.0:{port}', use_reloader=False)
