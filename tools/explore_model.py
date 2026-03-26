#!/usr/bin/env python3

import unittest
from unittest import mock

pbs_mock=mock.MagicMock()
pbs_mock.hook_config_filename = None
mock.patch.dict("sys.modules", pbs=pbs_mock).start()
import geopm_power_limit_compute as compute_hook

import sys
import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
pd.set_option("display.float_format", "{:.4f}".format)

###########################################################

event_mock = mock.MagicMock()
hook_config = compute_hook.load_hook_config(event_mock)
# event_mock.call_args_list

with open(sys.argv[1]) as f:
    vnode_names = [line.strip() for line in f if line.strip()]

job_power_limit = len(vnode_names) * int(sys.argv[2])
print(f'Job power limit = {job_power_limit}; Average = {sys.argv[2]}')

use_uniform_limit = True
#  job_type = 'hacc'
job_type = 'nekbone'
if hook_config is not None and (job_type is not None or 'node_profile_name' in hook_config):
    if job_type is None:
        job_type = hook_config['node_profile_name']
    host_models = compute_hook.get_model_from_config(event_mock, hook_config, job_type, per_host=True)
    if host_models is not None:
        max_node_power = host_models['max_power']
        try:
            for host in vnode_names:
                if host not in host_models:
                    raise KeyError(host)
            x0 = [host_models[h]['x0'] for h in vnode_names]
            A = [host_models[h]['A'] for h in vnode_names]
            B = [host_models[h]['B'] for h in vnode_names]
            C = [host_models[h]['C'] for h in vnode_names]
        except (ValueError, KeyError) as e:
            print(f'{host}: {e}')
            sys.exit(1)
            #  pbs.logmsg(pbs.LOG_WARNING, f'{event.hook_name}: Incomplete model config for {e}. Using uniform power limits.')
        else:
            use_uniform_limit = False
            slowdown, power_by_node = compute_hook.allocate_budget_to_nodes(
                job_power_limit,
                max_node_power, x0, A, B, C)

            #  my_node_idx = vnode_names.index(pbs.get_local_nodename())
            #  power_limit = power_by_node[my_node_idx]

normalized_power_by_node = [x / max_node_power for x in power_by_node]
slowdown_by_node = [An * (x0n - power)**2 + Bn * (x0n - power) + Cn
                    for x0n, An, Bn, Cn, power in zip(x0, A, B, C, normalized_power_by_node)]

normalized_uniform_power = int(sys.argv[2]) / max_node_power
slowdown_by_node_uniform = [An * (x0n - normalized_uniform_power)**2 + Bn * (x0n - normalized_uniform_power) + Cn
                            for x0n, An, Bn, Cn in zip(x0, A, B, C)]

node_power = zip(vnode_names, power_by_node, slowdown_by_node, slowdown_by_node_uniform)
#  for host, power, sd, sdu in node_power:
#      print(f'{host}: {power} | {sd} | {sdu}')

worst_host = slowdown_by_node_uniform.index(max(slowdown_by_node_uniform))
slowdown_improvement = slowdown_by_node_uniform[worst_host] - slowdown_by_node[worst_host]
print(f'Worst node\'s slowdown improvement = {slowdown_improvement}')


#  df = pd.DataFrame({'power': power_by_node}, index=vnode_names)
df = pd.DataFrame({'host': vnode_names, 'power': power_by_node})

#  import code
#  code.interact(local=dict(globals(), **locals()))

