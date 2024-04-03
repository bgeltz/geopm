#!/bin/bash

set -xe

# Build source distribution
python3 -m build --sdist | tee make-sdist.log
ARCHIVE=$(cat make-sdist.log | tail -n 1 | sed 's|^Successfully built ||')
VERSION=$(python3 -c "from setuptools_scm import get_version; print(get_version('..'))")

sed -e "s/@ARCHIVE@/${ARCHIVE}/" -e "s/@VERSION@/${VERSION}/" geopmdpy.spec.in > geopmdpy.spec

# On systems where rpmbuild is not available (i.e. GitHub CI builder used to create
# the distribution tarball that is uploaded to OBS) the following will be skipped.
if [ -x "$(command -v rpmbuild)" ]; then
    RPM_TOPDIR=${RPM_TOPDIR:-${HOME}/rpmbuild}
    mkdir -p ${RPM_TOPDIR}/SOURCES
    mkdir -p ${RPM_TOPDIR}/SPECS
    cp dist/${ARCHIVE} ${RPM_TOPDIR}/SOURCES
    cp geopmdpy.spec ${RPM_TOPDIR}/SPECS
    rpmbuild -ba ${RPM_TOPDIR}/SPECS/geopmdpy.spec
fi
