import requests
import time
from django.db import close_old_connections
from problems.catalogue import sync_catalogue
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Sync external question catalogues once or periodically.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0, help='0 imports all questions')
        parser.add_argument('--source', choices=['leetcode', 'codeforces'], default='leetcode')
        parser.add_argument('--watch', action='store_true')
        parser.add_argument('--interval', type=int, default=3600)

    def handle(self, *args, **options):
        if options['limit'] < 0 or options['interval'] < 60:
            raise CommandError('Limit must be nonnegative; interval must be at least 60 seconds.')
        sources = [options['source']]
        try:
            while True:
                failures = []
                for source in sources:
                    try:
                        created, updated = sync_catalogue(source, options['limit'])
                        self.stdout.write(f'{source}: {created} new, {updated} refreshed')
                    except CommandError as error:
                        failures.append(str(error))
                        self.stderr.write(str(error))
                    except (requests.RequestException, ValueError, KeyError, TypeError) as error:
                        failures.append(f'{source}: {error}')
                        self.stderr.write(f'{source} failed; saved questions retained: {error}')
                if not options['watch']:
                    if failures:
                        raise CommandError('; '.join(failures))
                    return
                close_old_connections()
                time.sleep(options['interval'])
        except KeyboardInterrupt:
            self.stdout.write('Question sync stopped.')
