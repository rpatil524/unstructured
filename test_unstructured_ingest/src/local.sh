#!/usr/bin/env bash

set -e

SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=local
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"
}
trap cleanup EXIT

RUN_SCRIPT=${RUN_SCRIPT:-unstructured-ingest}
PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" \
  local \
  --num-processes "$max_processes" \
  --metadata-exclude coordinates,filename,file_directory,metadata.data_source.date_processed,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
  --strategy hi_res \
  --reprocess \
  --verbose \
  --file-glob "*.html" \
  --input-path example-docs \
  --work-dir "$WORK_DIR" \
  local \
  --output-dir "$OUTPUT_DIR"

"$SCRIPT_DIR"/check-num-files-output.sh 15 $OUTPUT_FOLDER_NAME

"$SCRIPT_DIR"/evaluation-ingest-cp.sh "$OUTPUT_DIR" "$OUTPUT_FOLDER_NAME"
