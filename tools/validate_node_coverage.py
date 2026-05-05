#!/usr/bin/env python3
#
#  Copyright (c) 2015 - 2025 Intel Corporation
#  SPDX-License-Identifier: BSD-3-Clause
#
"""Validate that all nodes in a node list are present in a merged model config
for every profile that contains per-host models.

Exit code 0 if all nodes are covered; exit code 1 if any are missing.
"""

import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser(
        description='Check that selected nodes exist in all per-host profiles '
                    'of a merged model config.')
    parser.add_argument('config', help='Path to merged model config JSON file.')
    parser.add_argument('nodelist',
                        help='Path to node list file (one hostname per line), '
                             'e.g. output from select_uniform_nodes.py.')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Print detailed coverage information to stderr.')
    args = parser.parse_args()

    with open(args.config) as f:
        config = json.load(f)

    with open(args.nodelist) as f:
        nodes = set(line.strip() for line in f if line.strip())

    if not nodes:
        print('ERROR: Node list is empty.', file=sys.stderr)
        sys.exit(1)

    profiles = config.get('profiles', {})
    if not profiles:
        print('ERROR: No profiles found in config.', file=sys.stderr)
        sys.exit(1)

    has_failure = False
    profiles_with_hosts = 0

    for profile_name, profile_data in sorted(profiles.items()):
        hosts = profile_data.get('hosts', {})
        if not hosts:
            if args.verbose:
                print(f'  {profile_name}: no per-host models (profile-level '
                      f'only) — skipped', file=sys.stderr)
            continue

        profiles_with_hosts += 1
        model_hosts = set(hosts.keys())
        missing = sorted(nodes - model_hosts)
        extra = sorted(model_hosts - nodes) if args.verbose else []

        if missing:
            has_failure = True
            print(f'FAIL: {profile_name}: {len(missing)} node(s) from '
                  f'nodelist missing in model: {missing}', file=sys.stderr)
        else:
            print(f'OK:   {profile_name}: all {len(nodes)} node(s) present '
                  f'(model has {len(model_hosts)} hosts total)', file=sys.stderr)

        if extra and args.verbose:
            print(f'      {profile_name}: {len(extra)} extra host(s) in '
                  f'model not in nodelist', file=sys.stderr)

    if profiles_with_hosts == 0:
        print('WARNING: No profiles contain per-host models. Nothing to '
              'validate.', file=sys.stderr)
        sys.exit(1)

    if has_failure:
        sys.exit(1)
    else:
        print(f'All {len(nodes)} node(s) found in all {profiles_with_hosts} '
              f'per-host profile(s).', file=sys.stderr)
        sys.exit(0)


if __name__ == '__main__':
    main()
