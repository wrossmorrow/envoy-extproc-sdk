#!/bin/bash
VENV_LOC=$( poetry env info | grep -E '^Path' | awk '{print $2"/lib/python3.9/site-packages"}' )
echo "Removing generated code from ${VENV_LOC}"
for DIRECTORY in $(find generated/python/standardproto -type d -maxdepth 1 -mindepth 1) ; do
    INSTALL_NAME=${VENV_LOC}/$( basename $DIRECTORY )
    if [[ -d ${INSTALL_NAME} ]] ; then
        echo "removing ${INSTALL_NAME}"
        rm -rf ${INSTALL_NAME}
    fi
done
