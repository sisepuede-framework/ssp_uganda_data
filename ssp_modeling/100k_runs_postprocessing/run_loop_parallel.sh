#!/bin/bash
# run_loop_parallel.sh
# Runs the 100k_run_postprocessing_parallel.py script for multiple DIR_ID values

# Activate your conda environment (adjust path if needed)
# source ~/anaconda3/etc/profile.d/conda.sh
# conda activate ssp_la

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SUMMARY_LOG="${LOG_DIR}/summary_${TIMESTAMP}.txt"

mkdir -p "$LOG_DIR"

FAILED_IDS=()
SUCCESS_IDS=()

# Loop over the directory IDs you want to process
for i in {302..303}
do
    RUN_LOG="${LOG_DIR}/dir_id_${i}_${TIMESTAMP}.txt"

    echo "==========================================="
    echo "Running postprocessing for DIR_ID = $i"
    echo "Log: $RUN_LOG"
    echo "==========================================="

    # Run the Python script — output goes to console AND individual log file
    python "${SCRIPT_DIR}/100k_run_postprocessing_parallel.py" --dir-id "$i" --workers 12 2>&1 | tee "$RUN_LOG"
    EXIT_CODE=${PIPESTATUS[0]}

    if [ $EXIT_CODE -ne 0 ]; then
        echo "WARNING: DIR_ID=$i failed (exit code $EXIT_CODE). Continuing to next..."
        FAILED_IDS+=("$i")
    else
        echo "Finished DIR_ID=$i"
        SUCCESS_IDS+=("$i")
    fi

    echo ""
done

# Write summary log
{
    echo "============================================"
    echo "RUN SUMMARY — $(date)"
    echo "============================================"
    echo ""
    echo "Successful (${#SUCCESS_IDS[@]}): ${SUCCESS_IDS[*]:-none}"
    echo "Failed     (${#FAILED_IDS[@]}): ${FAILED_IDS[*]:-none}"
    echo ""
    echo "Individual logs:"
    for id in "${SUCCESS_IDS[@]}"; do
        echo "  [OK]  DIR_ID=${id} -> ${LOG_DIR}/dir_id_${id}_${TIMESTAMP}.txt"
    done
    for id in "${FAILED_IDS[@]}"; do
        echo "  [ERR] DIR_ID=${id} -> ${LOG_DIR}/dir_id_${id}_${TIMESTAMP}.txt"
    done
    echo ""
    echo "Summary file: ${SUMMARY_LOG}"
} | tee "$SUMMARY_LOG"
