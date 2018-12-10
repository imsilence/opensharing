#encoding: utf-8

import os
from collections import namedtuple
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand

from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import InventoryManager
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.plugins.callback import CallbackBase
import ansible.constants as C

from host.models import Host

class ResultCallback(CallbackBase):

    def v2_runner_on_ok(self, result, **kwargs):
        func = getattr(self, 'result_{0}'.format(result.task_name), None)
        if func:
            func(result._host, result._result)

    def result_fact(self, host, result):
        facts = result.get('ansible_facts', {})
        arch = facts.get('ansible_architecture', '')
        mem = facts.get('ansible_memtotal_mb', 0)
        cpu = facts.get('ansible_processor_vcpus', 0)
        os = facts.get('ansible_os_family', '')
        ip = facts.get('ansible_default_ipv4', {}).get('address', '')
        name = facts.get('ansible_nodename', host)
        Host.create_or_replace(name, ip, arch, os, mem, cpu)


class Command(BaseCommand):
    def handle(self, *args, **options):
        Options = namedtuple('Options', ['connection', 'module_path', 'forks', 'become', 'become_user', 'become_method', 'check', 'diff'])
        options = Options(connection='smart', module_path=[], forks=10, become=None, become_user=None,  become_method=None, check=False, diff=False)

        result_callback = ResultCallback()

        loader = DataLoader()
        inventory = InventoryManager(loader=loader, sources=os.path.join(settings.BASE_DIR, 'etc', 'hosts'))
        variable_manager = VariableManager(loader=loader, inventory=inventory)
        passwords = {}

        play_source = {
            'name' : 'fact',
            'hosts' : 'all',
            'gather_facts' : 'no',
            'tasks' : [
                {
                    'name' : 'fact',
                    'setup' : ''
                }
            ],
        }

        play = Play().load(play_source, variable_manager=variable_manager, loader=loader)

        tqm = None
        try:
            tqm = TaskQueueManager(
                    inventory=inventory,
                    variable_manager=variable_manager,
                    loader=loader,
                    options=options,
                    passwords=passwords,
                    stdout_callback=result_callback,
                )
            result = tqm.run(play)
        finally:
            if tqm:
                tqm.cleanup()
            shutil.rmtree(C.DEFAULT_LOCAL_TMP, True)