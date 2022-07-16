#!/bin/bash
VENV_LOC=$( poetry env info | grep -E '^Path' | awk '{print $2"/lib/python3.9/site-packages"}' )
echo "Installing generated code at ${VENV_LOC}"
cp -r generated/python/standardproto/* ${VENV_LOC}
