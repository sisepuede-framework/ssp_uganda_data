#!/bin/bash
# run_loop_parallel.sh
# Runs the 100k_run_postprocessing_parallel.py script for multiple DIR_ID values

# Activate the conda environment (debe ser SIEMPRE ssp_uganda_env)
# Detecta la ruta de conda.sh automáticamente (anaconda3/miniconda3, en /opt o en $HOME).
CONDA_SH=""
for c in /opt/miniconda3 /opt/anaconda3 "$HOME/miniconda3" "$HOME/anaconda3"; do
    if [ -f "$c/etc/profile.d/conda.sh" ]; then CONDA_SH="$c/etc/profile.d/conda.sh"; break; fi
done
if [ -z "$CONDA_SH" ] && [ -n "$CONDA_EXE" ]; then
    CONDA_SH="$(dirname "$(dirname "$CONDA_EXE")")/etc/profile.d/conda.sh"
fi
if [ -z "$CONDA_SH" ] || [ ! -f "$CONDA_SH" ]; then
    echo "ERROR: no se encontró conda.sh. Ajusta la ruta manualmente en el script."; exit 1
fi
source "$CONDA_SH"
conda activate ssp_uganda_env || { echo "ERROR: no se pudo activar ssp_uganda_env"; exit 1; }
echo "Python en uso: $(which python)"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SUMMARY_LOG="${LOG_DIR}/summary_${TIMESTAMP}.txt"

mkdir -p "$LOG_DIR"

FAILED_IDS=()
SUCCESS_IDS=()

# --- AWS / run config (debe coincidir con el .py) ---
AWS_PROFILE="alexa"
BUCKET="sisepuede-data"
RUN_ID="sisepuede_run_2026-05-30t21;35;56.244639"

# --- Modo de corrida ---
# Uso: bash run_loop_parallel.sh [emissions|cb]   (por defecto: emissions)
#   emissions -> corre SOLO emisiones (--no-cb, rápido); "hecho" = decomposed_emissions_<id>
#   cb        -> corre con costo-beneficio;             "hecho" = cba/cb_<id>
MODE="${1:-emissions}"
WORKERS=10

if [ "$MODE" = "emissions" ]; then
    PY_FLAGS="--no-cb"
    DONE_LIST_URL="s3://${BUCKET}/run_database/${RUN_ID}/model_output_decomposed/region=uganda/"
    DONE_GREP='decomposed_emissions_[0-9]+'
    DONE_SED='s/decomposed_emissions_//'
elif [ "$MODE" = "cb" ]; then
    PY_FLAGS=""
    DONE_LIST_URL="s3://${BUCKET}/run_database/${RUN_ID}/cba/region=uganda/"
    DONE_GREP='cb_[0-9]+'
    DONE_SED='s/cb_//'
else
    echo "ERROR: modo inválido '$MODE'. Usa 'emissions' o 'cb'."
    exit 1
fi
echo "MODO: $MODE  |  flags python: '${PY_FLAGS:-(con CB)}'  |  workers: $WORKERS"

# Deriva la lista de dir_ids directamente de S3 (NO son contiguos: hay huecos).
# Cada subcarpeta model_output_<N> es una instancia a procesar.
echo "Listando dir_ids desde S3…"
ALL_DIR_IDS=$(aws s3 ls "s3://${BUCKET}/run_database/${RUN_ID}/model_output/region=uganda/" --profile "$AWS_PROFILE" \
    | grep -oE 'model_output_[0-9]+' | sed 's/model_output_//' | sort -n)

if [ -z "$ALL_DIR_IDS" ]; then
    echo "ERROR: no se encontraron dir_ids en S3. Revisa RUN_ID/perfil/bucket."
    exit 1
fi

# Lista los dir_ids YA procesados para este MODO (marca de "completado" en S3).
echo "Listando dir_ids ya procesados para modo '$MODE'…"
DONE_DIR_IDS=$(aws s3 ls "$DONE_LIST_URL" --profile "$AWS_PROFILE" \
    | grep -oE "$DONE_GREP" | sed "$DONE_SED" | sort -n)

# dir_ids pendientes = todos − ya procesados.
# comm compara líneas como TEXTO, así que ambas listas deben venir con el mismo
# orden lexicográfico; reordenamos el resultado a numérico al final.
DIR_IDS=$(comm -23 <(echo "$ALL_DIR_IDS" | sort) <(echo "$DONE_DIR_IDS" | sort) | sort -n)

TOTAL_ALL=$(echo "$ALL_DIR_IDS" | grep -c .)
TOTAL_DONE=$(echo "$DONE_DIR_IDS" | grep -c .)
TOTAL_PENDING=$(echo "$DIR_IDS" | grep -c .)
echo "Total instancias: ${TOTAL_ALL} | ya procesadas (${MODE}): ${TOTAL_DONE} | pendientes: ${TOTAL_PENDING}"

# Guarda la lista de pendientes de este modo a un archivo (referencia / reanudación)
PENDING_FILE="${LOG_DIR}/pending_${MODE}_${TIMESTAMP}.txt"
echo "$DIR_IDS" > "$PENDING_FILE"
echo "Lista de pendientes guardada en: $PENDING_FILE"

if [ -z "$DIR_IDS" ]; then
    echo "Nada pendiente para modo '$MODE': todas las instancias ya tienen salida."
    exit 0
fi

# Loop over the directory IDs found in S3
for i in $DIR_IDS
do
    RUN_LOG="${LOG_DIR}/dir_id_${i}_${TIMESTAMP}.txt"

    echo "==========================================="
    echo "Running postprocessing for DIR_ID = $i"
    echo "Log: $RUN_LOG"
    echo "==========================================="

    # Run the Python script — output goes to console AND individual log file
    python "${SCRIPT_DIR}/100k_run_postprocessing_parallel.py" --dir-id "$i" --workers "$WORKERS" $PY_FLAGS 2>&1 | tee "$RUN_LOG"
    EXIT_CODE=${PIPESTATUS[0]}

    if [ $EXIT_CODE -ne 0 ]; then
        # Si el fallo es por credenciales/token de AWS expirado, ABORTAR todo el loop
        # (si no, quemaría todas las instancias restantes fallando en segundos).
        if grep -qE "TokenRetrievalError|ExpiredToken|InvalidGrantException|Token has expired|Unable to locate credentials" "$RUN_LOG"; then
            echo ""
            echo "############################################################"
            echo "ABORTANDO: credenciales de AWS expiradas en DIR_ID=$i."
            echo "Renueva con:  aws sso login --profile ${AWS_PROFILE}"
            echo "Luego vuelve a lanzar el script; retomará donde quedó."
            echo "############################################################"
            FAILED_IDS+=("$i")
            break
        fi
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
