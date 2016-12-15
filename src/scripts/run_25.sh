RUNS=100
ALGORITHM=random
WS=3648
TIME=60

until [ $RUNS -lt 1 ]; do
	echo "RUN : $RUNS"
	perf stat -e instructions,cycles,cache-references,cache-misses -o ../logs/$ALGORITHM/$RUNS.log ./../src/bandwidth -c 0 -m $WS -t $TIME -p -19 &> ../logs/$ALGORITHM/$RUNS.perf
	let RUNS-=1
done
