#!/usr/bin/env python

import json
import subprocess
import code
from pprint import pprint

def get_approved_patches():
    cmdstr = 'ssh -p 29418 review.gerrithub.io gerrit query --format=JSON --current-patch-set status:open project:geopm/geopm \(label:Verified=1 AND \(label:Code-Review=1 OR label:Code-Review=2\)\)'
    output = subprocess.check_output(cmdstr, shell=True).splitlines()

    a = []

    for line in output:
        a.append(json.loads(line))

    return a

def main():

    print "Patches with CR >= +1 and V+1:" 
    patches = get_approved_patches()
    for a in patches:
        try:
            print '[{}] {} - {}'.format(a['number'], a['subject'], a['owner']['name'])
        except KeyError:
            pass

    code.interact(local=dict(globals(), **locals()))

if __name__ == '__main__':
    main()
