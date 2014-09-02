#!/system/xbin/bash

LOG=loadpages.log

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
echo "First page loads in 20 seconds. Last page will be "`tail -1 $2`
sleep 20

signal_spikes
sleep 5

while read line
do
	# Build URL
	line=$(build_url $line $PROTOCOL)
	
	# Load the URL 50 times
	for i in {0..50}
	do
		# Cleanup
		am kill-all   # kill all background procs
		am force-stop com.android.chrome  # stop Chrome
		su -c "rm -rf /data/data/com.android.chrome/cache"  # clear Chrome cache
		su -c "rm -rf /data/data/com.android.chrome/files"  # close Chrome tabs

		# Load page and wait
		echo -e `date +%s`"\t$line" >> $LOG
		am start -a android.intent.action.VIEW -d $line com.android.chrome
		sleep 20
	done
done < $2

sleep 5
signal_spikes
