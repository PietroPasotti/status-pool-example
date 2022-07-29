This is a demo charm to showcase the basic usage of StatusPool.

Instructions:

> charmcraft pack
> juju deploy ./compound-status-demo_ubuntu-20.04-amd64.charm csd
> cd db-charm
> charmcraft pack
> juju deploy ./db-charm_ubuntu-20.04-amd64.charm db


At this point you should have a deployment. the status of the db relation is randomly determined by the csd charm, so there is a chance that things will start going to blocked as soon as you relate the charms.

> juju relate csd db

Now you can start fiddling with the set-status action to see how things play out.

For example, you can:
> juju run-action csd/0 set-status name=tls status=blocked message=whoopsie

This should bring the unit to `blocked` and display `(tls) whoopsie`.
> juju run-action csd/0 set-status name=workload status=blocked message=cya

This should keep the unit in `blocked` but change the message to `(workload) cya`, becuse workload has higher priority (implicitly).
Try setting manual priorities to change this behaviour!

If at some point some db relation blocks because of the `_is_healthy` randomness, you can always

> juju run-action csd/0 set-status name=db_db_charm_[id-of-blocking-unit] status=active message=happy

Happy hacking!