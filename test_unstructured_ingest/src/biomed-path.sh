#!/usr/bin/env bash
# shellcheck disable=SC2317

set -e

SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=biomed-path
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"
}
trap cleanup EXIT

"$SCRIPT_DIR"/check-num-files-expected-output.sh 1 $OUTPUT_FOLDER_NAME 10k

RUN_SCRIPT=${RUN_SCRIPT:-unstructured-ingest}
PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" \
  biomed \
  --download-dir "$DOWNLOAD_DIR" \
  --metadata-exclude coordinates,filename,file_directory,metadata.last_modified,metadata.data_source.date_processed,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
  --num-processes "$max_processes" \
  --strategy hi_res \
  --preserve-downloads \
  --reprocess \
  --verbose \
  --max-request-time 30 \
  --max-retries 5 \
  --path "oa_pdf/07/07/sbaa031.073.PMC7234218.pdf" \
  --work-dir "$WORK_DIR" \
  local \
  --output-dir "$OUTPUT_DIR"

"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
