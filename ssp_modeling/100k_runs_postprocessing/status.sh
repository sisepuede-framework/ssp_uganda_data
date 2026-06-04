#!/bin/bash
# status.sh — ¿la corrida de postprocesamiento está trabajando o colgada?
# Uso:  bash status.sh
#
# Detecta el proceso de 100k_run_postprocessing_parallel.py en curso y muestra:
#   1) si el proceso está vivo (PID, tiempo, CPU, memoria)
#   2) si la DESCARGA avanza (bytes recibidos en 2 muestras) y cuántas conexiones tiene
#   3) las últimas líneas del log de la instancia en curso
# Veredicto: TRABAJANDO si sube la red, sube la CPU, o el log cambió; si nada
# de eso se mueve durante el chequeo, posible COLGADO.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs"

# --- 1) Proceso en curso ---
PID=$(pgrep -f "100k_run_postprocessing_parallel.py" | head -1)
if [ -z "$PID" ]; then
    echo "No hay ningún proceso de 100k_run_postprocessing_parallel.py corriendo."
    echo "(Si esperabas uno, revisa la terminal donde lanzaste run_loop_parallel.sh.)"
    exit 0
fi

echo "=========================================================="
echo " PROCESO EN CURSO"
echo "=========================================================="
ps -o pid,etime,%cpu,rss,state -p "$PID" | tail -1 | \
    awk '{printf "PID=%s  tiempo=%s  cpu=%s%%  mem=%.0fMB  estado=%s\n", $1,$2,$3,$4/1024,$5}'
CPU1=$(ps -o %cpu= -p "$PID" | tr -d ' ')

# --- 2) Descarga / red ---
echo ""
echo "=========================================================="
echo " RED (¿avanza la descarga de S3?)"
echo "=========================================================="
CONNS=$(lsof -nP -p "$PID" 2>/dev/null | grep -c "ESTABLISHED")
echo "Conexiones de red abiertas: ${CONNS}"

read_bytes() { nettop -P -L 1 -t wifi 2>/dev/null | grep -i "\.${PID}," | awk -F',' '{print $5}'; }
B1=$(read_bytes)
for i in $(seq 1 4000000); do :; done   # pausa breve sin 'sleep'
B2=$(read_bytes)
if [ -n "$B1" ] && [ -n "$B2" ]; then
    DELTA=$(( B2 - B1 ))
    echo "Bytes recibidos: ${B1} -> ${B2}  (delta ~${DELTA} en el muestreo)"
    if [ "$DELTA" -gt 50000 ]; then
        NET_MOVING=1; echo "  -> la descarga ESTÁ avanzando"
    else
        NET_MOVING=0; echo "  -> la red casi no se mueve (puede que ya terminó el fetch y esté procesando)"
    fi
else
    NET_MOVING=0; echo "(sin datos de red para este proceso; quizá ya pasó la fase de descarga)"
fi

# --- 3) Log de la instancia en curso ---
echo ""
echo "=========================================================="
echo " LOG DE LA INSTANCIA EN CURSO"
echo "=========================================================="
LATEST=$(ls -t "${LOG_DIR}"/dir_id_*.txt 2>/dev/null | head -1)
if [ -z "$LATEST" ]; then
    echo "(no se encontraron logs en ${LOG_DIR})"
else
    echo "Archivo: ${LATEST}"
    LINES1=$(wc -l < "$LATEST")
    tail -8 "$LATEST"
    for i in $(seq 1 4000000); do :; done
    LINES2=$(wc -l < "$LATEST")
    [ "$LINES2" -gt "$LINES1" ] && LOG_MOVING=1 || LOG_MOVING=0
fi

# CPU de nuevo para ver si cambió
CPU2=$(ps -o %cpu= -p "$PID" 2>/dev/null | tr -d ' ')

# --- Veredicto ---
echo ""
echo "=========================================================="
CPU_ACTIVE=$(awk -v c="${CPU2:-0}" 'BEGIN{print (c+0>5)?1:0}')
if [ "${NET_MOVING:-0}" = "1" ] || [ "${LOG_MOVING:-0}" = "1" ] || [ "$CPU_ACTIVE" = "1" ]; then
    echo " VEREDICTO: TRABAJANDO ✅  (red, log o CPU en movimiento)"
else
    echo " VEREDICTO: SOSPECHOSO ⚠️  — sin avance visible en este chequeo."
    echo " Vuelve a correr 'bash status.sh' en ~3-5 min. Si sigue igual"
    echo " (misma red, mismo log, CPU baja), entonces sí está colgado:"
    echo " haz Ctrl+C en la terminal del loop y relanza (retoma donde quedó)."
fi
echo "=========================================================="
