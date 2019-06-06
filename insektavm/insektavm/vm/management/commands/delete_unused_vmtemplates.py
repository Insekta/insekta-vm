import fcntl
import os
import sys
import tempfile

from django.core.management.base import BaseCommand

from insektavm.vm.models import VMTemplate


class Command(BaseCommand):
    def handle(self, **options):
        lock_file =  os.path.join(tempfile.gettempdir(),
                                  'insekta-delete-unused-vmtemplates.lock')

        with open(lock_file, 'w') as f:
            try:
                fcntl.lockf(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                sys.exit(1)
            else:
                num_deleted = VMTemplate.cleanup_unused()
                print(num_deleted)
            finally:
                fcntl.lockf(f.fileno(), fcntl.LOCK_UN)
            sys.exit(0)
