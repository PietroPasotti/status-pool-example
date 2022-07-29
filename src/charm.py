#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""Charm the service.

Refer to the following post for a quick-start guide that will help you
develop a new k8s charm using the Operator Framework:

    https://discourse.charmhub.io/t/4208
"""
import random

from ops.charm import ActionEvent, RelationJoinedEvent, RelationChangedEvent, \
    RelationDepartedEvent
from ops.main import main
from ops.model import Unit

from charms.compound_status.v0.compound_status import *

logger = logging.getLogger(__name__)


class MyPool(StatusPool):
    # statuses are prioritised by ordering: topmost are most important.
    # so if both workload and tls are blocked, workload will be displayed.
    workload = Status()
    tls = Status()
    database = Status()

    # If you want to override this ordering, you can pass `priority:int` to
    # Status. Caveat: you can't mix implicit and explicit. Pick one.
    # Either all statuses in a pool is passed a priority:int, or none does.


class OperatorTemplateCharm(CharmBase):
    """Charm the service."""

    def __init__(self, *args):
        super().__init__(*args)
        # this is how you typically want to initialize the pool.
        # All statuses in the pool start off at `unknown` until you set them
        self.status = MyPool(self)

        self.framework.observe(self.on.set_status_action,
                               self._on_set_status_action)
        self.framework.observe(self.on.db_relation_joined,
                               self._on_db_relation_joined)
        self.framework.observe(self.on.start,
                               self._on_start)

    def _on_start(self, _):
        self.unit.status = ActiveStatus('started')

    def _db_unit_to_status_name(self, unit: Unit):
        # create a predictable python identifier from a remote db unit instance.
        # we'll use these to assign a status to a relation with that unit.
        return 'db_' + unit.name.replace('-', '_').replace('/', '_')

    def _on_db_relation_joined(self, event: RelationJoinedEvent):
        # when a remote unit joins, we create a status instance and start
        # tracking it with maintenance.
        new_status = Status()
        attr = self._db_unit_to_status_name(event.unit)
        self.status.add_status(new_status, attr)
        self.status.set_status(attr, MaintenanceStatus('setting up'))
        self.status.commit()

    def _is_healthy(self, relation, unit):
        # here you determine if the relation is OK, e.g.: has the remote
        # side shared valid data?
        return random.random() > 0.2

    def _on_db_relation_changed(self, event: RelationChangedEvent):
        # update the status of all related units.
        for unit in event.relation.units:
            attr = self._db_unit_to_status_name(unit)
            my_status_for_this_unit = self.status.get_status(attr)
            if self._is_healthy(event.relation, unit):
                self.status.set_status(attr, ActiveStatus(f'{unit} is happy!'))
            else:
                self.status.set_status(attr, BlockedStatus(f'{unit} is broken!'))
        self.status.commit()

    def _on_db_relation_departed(self, event: RelationDepartedEvent):
        # when the relation departs, we get rid of the status (delete it)
        attr = self._db_unit_to_status_name(event.unit)
        self.status.remove_status(self.status.get_status(attr))
        self.status.commit()

    def _on_set_status_action(self, event: ActionEvent):
        # This is a hacky implementation of an action to allow you
        # to manipulate (statically defined) statuses from CLI.
        # example:
        # juju run-action charm name=tls status=blocked message=whoopsie

        status_name = event.params["name"]
        status_type = event.params["status"]
        status_message = event.params["message"]

        status_map = {
            'active': ActiveStatus,
            'waiting': WaitingStatus,
            'maintenance': MaintenanceStatus,
            'blocked': BlockedStatus
        }

        if status_type == 'unknown':
            # if you want to stop tracking a status (because it becomes irrelevant
            # or no longer applicable, you have to `unset()` it.)
            self.status.get_status(status_name).unset()
            self.status.commit()
            return

        status_class = status_map.get(status_type, None)
        if status_class is None:
            raise ValueError(f"unknown status type {status_type}")

        status_inst = status_class(status_message)
        self.status.set_status(status_name, status_inst)

        # we tell StatusPool to set self.unit.status for us
        # there is also a StatusPool class attr AUTO_COMMIT where this
        # will be automatically done for you when the hook is done running.
        self.status.commit()


if __name__ == "__main__":
    main(OperatorTemplateCharm)
