#!/system/xbin/bash

LOG=loadobjects.log
CURL=/data/local/tmp/curl

source loadcommon.sh


#
# MAIN
#

if [ "$#" -ne 2 ]; 
    then echo -e "Please specify a protocol and a URL file:\n$0 http|https urlfile"
    exit 1
fi
PROTOCOL=$1

echo -e `date +%s`"\t========== Script Launched: $0 $@ ==========" >> $LOG
echo "First object loads in 20 seconds. Each object will be loaded 100 times. Last object will be "`tail -1 $2`
sleep 20

signal_spikes
sleep 5

while read line
do
	# Build URL
	line=$(build_url $line $PROTOCOL)

	# Load the URL NUMTRIALS time
	for i in {1..100}
	do
		# Cleanup
		am kill-all   # kill all background procs
		
		# Load object
		echo -e `date +%s`"\t$line" >> $LOG
		$CURL -H "Cache-control: no-cache" --cacert /data/local/ssl/certs/ca-bundle.crt -o /dev/null $line
	done
done < $2

sleep 5
signal_spikes
