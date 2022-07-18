#!/bin/bash

UNIT=1000

SCHEME=http
HOST=localhost
PORT=8080
ENDPOINT=something

OUTPUT_DIR=tests/performance/results
mkdir -p ${OUTPUT_DIR} ${OUTPUT_DIR}/plain ${OUTPUT_DIR}/extproc

echo "concurrency,rps plain,med plain,rps extproc,med extproc" > ${OUTPUT_DIR}/all.csv
# for C in $(seq 1 15); do
for C in 16; do

    COUNT=$(echo "${C} * ${UNIT}" | bc)
    WRITE="${C}"

    echo "Running ${COUNT} plain requests ${C} at a time"
    hey -n ${COUNT} -c ${C} -m GET ${SCHEME}://${HOST}:${PORT}/no-ext-procs/${ENDPOINT} > ${OUTPUT_DIR}/plain/${C}.txt
    RPS=$( sed -En 's/[[:space:]]+Requests\/sec:[[:space:]]([0-9]+(\.[0-9]+)?)/\1/p' ${OUTPUT_DIR}/plain/${C}.txt )
    MED=$( sed -En 's/[[:space:]]+50% in[[:space:]]([0-9]+(\.[0-9]+)?).*/\1/p' ${OUTPUT_DIR}/plain/${C}.txt )
    WRITE="${WRITE},${MED},${RPS}"

    echo "Running ${COUNT} extproc requests ${C} at a time"
    hey -n ${COUNT} -c ${C} -m GET ${SCHEME}://${HOST}:${PORT}/${ENDPOINT} > ${OUTPUT_DIR}/extproc/${C}.txt
    RPS=$( sed -En 's/[[:space:]]+Requests\/sec:[[:space:]]([0-9]+(\.[0-9]+)?)/\1/p' ${OUTPUT_DIR}/extproc/${C}.txt )
    MED=$( sed -En 's/[[:space:]]+50% in[[:space:]]([0-9]+(\.[0-9]+)?).*/\1/p' ${OUTPUT_DIR}/extproc/${C}.txt )
    WRITE="${WRITE},${MED},${RPS}"

    echo "${WRITE}" >> ${OUTPUT_DIR}/all.csv

done