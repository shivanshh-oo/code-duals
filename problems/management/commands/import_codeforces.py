import time
import requests
from django.db import close_old_connections
from django.core.management.base import BaseCommand, CommandError
from problems.codeforces import seed_curated_problems, sync_codeforces_catalogue


class Command(BaseCommand):
    help = (
        'Import Codeforces problems into CodeDuels.\n\n'
        'Two modes:\n'
        '  --curated   Seed the built-in curated set with auto-generated test cases (default)\n'
        '  --catalogue Sync metadata-only drafts from the Codeforces problemset API\n'
    )

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument(
            '--curated',
            action='store_true',
            default=True,
            help='Seed curated Codeforces problems with generated test cases (default)',
        )
        mode.add_argument(
            '--catalogue',
            action='store_true',
            default=False,
            help='Sync metadata-only drafts from the live Codeforces API',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Max problems to import (0 = all, catalogue mode only)',
        )
        parser.add_argument(
            '--tags',
            type=str,
            default='',
            help='Semicolon-separated Codeforces tags to filter by (catalogue mode only)',
        )
        parser.add_argument(
            '--watch',
            action='store_true',
            help='Keep running and re-sync periodically (catalogue mode only)',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=3600,
            help='Seconds between re-syncs in --watch mode (default 3600)',
        )
        parser.add_argument(
            '--sample',
            type=int,
            default=3,
            help='Number of visible sample test cases per problem (curated mode)',
        )
        parser.add_argument(
            '--hidden',
            type=int,
            default=32,
            help='Number of hidden test cases per problem (curated mode)',
        )

    def handle(self, *args, **options):
        if options['interval'] < 60:
            raise CommandError('--interval must be at least 60 seconds.')

        if options['catalogue']:
            self._run_catalogue(options)
        else:
            self._run_curated(options)

    def _run_curated(self, options):
        self.stdout.write('Seeding curated Codeforces problems with auto-generated test cases...')
        created, updated = seed_curated_problems(
            stdout=self.stdout,
            n_sample=options['sample'],
            n_hidden=options['hidden'],
        )
        total_tc = options['sample'] + options['hidden']
        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone! Processed problems ({created} created, {updated} updated). Each has {total_tc} test cases ({options["sample"]} sample, {options["hidden"]} hidden).'
            )
        )

    def _run_catalogue(self, options):
        tags = [t.strip() for t in options['tags'].split(';') if t.strip()] or None
        self.stdout.write(
            f"Syncing Codeforces catalogue "
            f"(limit={options['limit'] or 'all'}, tags={tags or 'none'}) ..."
        )
        try:
            while True:
                try:
                    created, updated = sync_codeforces_catalogue(
                        limit=options['limit'],
                        tags=tags,
                    )
                    self.stdout.write(f'codeforces: {created} new, {updated} refreshed')
                except (requests.RequestException, ValueError, KeyError, TypeError) as error:
                    msg = f'codeforces catalogue sync failed: {error}'
                    self.stderr.write(msg)
                    if not options['watch']:
                        raise CommandError(msg)

                if not options['watch']:
                    return

                close_old_connections()
                time.sleep(options['interval'])

        except KeyboardInterrupt:
            self.stdout.write('Codeforces sync stopped.')

