#!/bin/bash
VENV_LOC=$( poetry env info | grep -E '^Path' | awk '{print $2"/lib/python3.9/site-packages"}' )
echo "Installing generated code at ${VENV_LOC}"
for DIRECTORY in $(find generated/python/standardproto -type d -maxdepth 1 -mindepth 1) ; do
    INSTALL_NAME=${VENV_LOC}/$( basename ${DIRECTORY} )
    echo "  installing $( basename ${DIRECTORY} ) to ${INSTALL_NAME}"
    cp -r ${DIRECTORY} ${VENV_LOC}
done