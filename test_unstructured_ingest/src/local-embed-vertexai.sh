#!/usr/bin/env bash

set -e

SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=embed-vertexai
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
GCP_INGEST_SERVICE_KEY=${GCP_INGEST_SERVICE_KEY:-$GCP_INGEST_SERVICE_KEY}

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"
}
trap cleanup EXIT

if [ -z "$GCP_INGEST_SERVICE_KEY" ]; then
  echo "Skipping local vertexai ingest test because the GCP_INGEST_SERVICE_KEY env var is not set."
  exit 8
fi

RUN_SCRIPT=${RUN_SCRIPT:-unstructured-ingest}
PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" \
  local \
  --num-processes "$max_processes" \
  --metadata-exclude coordinates,filename,file_directory,metadata.data_source.date_created,metadata.data_source.date_modified,metadata.data_source.date_processed,metadata.data_source.filesize_bytes,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
  --verbose \
  --reprocess \
  --input-path example-docs/book-war-and-peace-1p.txt \
  --work-dir "$WORK_DIR" \
  --embedding-provider "vertexai" \
  --embedding-api-key "$GCP_INGEST_SERVICE_KEY" \
  --embedding-model-name "textembedding-gecko@001" \
  local \
  --output-dir "$OUTPUT_DIR"

set +e

"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME

"$SCRIPT_DIR"/evaluation-ingest-cp.sh "$OUTPUT_DIR" "$OUTPUT_FOLDER_NAME"
