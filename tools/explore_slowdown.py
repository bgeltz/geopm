#!/usr/bin/env python3
"""Query GEOPM power allocation models for a given max-slowdown target.

Uses the server hook to predict the per-node power cap that corresponds
to a requested max-slowdown, and optionally uses the compute hook to
distribute the resulting job power budget across specific nodes.

Usage:
    # Print per-node power limit for a given slowdown target:
    python explore_slowdown.py --job-type nekbone --max-slowdown 0.1

    # Also print per-host power limits for a specific set of nodes:
    python explore_slowdown.py --job-type nekbone --max-slowdown 0.1 --nodelist nodes.txt

    # Use a custom model config path:
    python explore_slowdown.py --job-type hacc --max-slowdown 0.05 --model-path /path/to/model.json
"""

import argparse
import os
import sys
from unittest import mock

# Mock the pbs module before importing hook code
pbs_mock = mock.MagicMock()
pbs_mock.hook_config_filename = None
mock.patch.dict("sys.modules", pbs=pbs_mock).start()

# Add the hooks directory to sys.path so the hook modules can be imported
_HOOKS_DIR = os.path.join(os.path.dirname(__file__),
                          '..', 'integration', 'service', 'open_pbs')
if os.path.isdir(_HOOKS_DIR):
    sys.path.insert(0, os.path.abspath(_HOOKS_DIR))

import geopm_power_limit_server as server_hook
import geopm_power_limit_compute as compute_hook


def main():
    parser = argparse.ArgumentParser(
        description='Query GEOPM power models for a given max-slowdown target.')
    parser.add_argument('--max-slowdown', type=float, required=True,
                        help='Target max slowdown (0 = no slowdown, 1 = 100%% slower)')
    parser.add_argument('--job-type', type=str, required=True,
                        help='Profile name in the model config (e.g. hacc, nekbone)')
    parser.add_argument('--nodelist', type=str, default=None,
                        help='Path to a file with one vnode name per line')
    parser.add_argument('--model-path', type=str, default=None,
                        help='Path to model config JSON (default: /soft/geopm/model.json)')
    args = parser.parse_args()

    if args.model_path:
        server_hook._MODEL_PATH = args.model_path
        compute_hook._MODEL_PATH = args.model_path

    event_mock = mock.MagicMock()

    hook_config = server_hook.load_hook_config(event_mock)
    if hook_config is None:
        print('Error: Unable to load model config', file=sys.stderr)
        sys.exit(1)

    max_power = hook_config.get('max_power')
    if max_power is None:
        print('Error: max_power not found in model config', file=sys.stderr)
        sys.exit(1)

    # Use the server hook to predict per-node power cap at the given slowdown
    per_node_power = server_hook.predict_power_cap_at_performance_factor(
        event_mock, args.job_type, args.max_slowdown, 0, max_power)

    if args.nodelist is None:
        print(f'Per-node power limit: {per_node_power:.1f} W ({per_node_power / max_power * 100:.1f}%)')
        return

    with open(args.nodelist) as f:
        vnode_names = [line.strip() for line in f if line.strip()]

    num_nodes = len(vnode_names)
    job_power_limit = per_node_power * num_nodes

    print(f'Per-node power limit (aggregate model): {per_node_power:.1f} W ({per_node_power / max_power * 100:.1f}%)')
    print(f'Job power limit ({num_nodes} nodes): {job_power_limit:.1f} W')

    # Use the compute hook to distribute the budget across nodes
    host_models = compute_hook.get_model_from_config(
        event_mock, hook_config, args.job_type, per_host=True)

    if host_models is None:
        uniform = job_power_limit / num_nodes
        print(f'\nNo per-host models found. Uniform limit: {uniform:.1f} W')
        return

    model_type = host_models.get('model_type', 'original-quadratic')
    max_node_power = host_models['max_power']

    try:
        for host in vnode_names:
            if host not in host_models:
                raise KeyError(host)

        if model_type == 'piecewise-linear':
            host_curves = {h: host_models[h] for h in vnode_names}
            _, power_by_node = compute_hook.allocate_budget_to_nodes_piecewise(
                job_power_limit, max_node_power, host_curves, vnode_names)
        else:
            x0 = [host_models[h]['x0'] for h in vnode_names]
            A = [host_models[h]['A'] for h in vnode_names]
            B = [host_models[h]['B'] for h in vnode_names]
            C = [host_models[h]['C'] for h in vnode_names]
            _, power_by_node = compute_hook.allocate_budget_to_nodes(
                job_power_limit, max_node_power, x0, A, B, C)
    except KeyError as e:
        print(f'Error: No model for host {e}', file=sys.stderr)
        sys.exit(1)

    print('\nPer-host power limits:')
    for host, power in zip(vnode_names, power_by_node):
        print(f'{host} {power:.1f}')


if __name__ == '__main__':
    main()
