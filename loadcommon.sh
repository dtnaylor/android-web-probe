TCPDUMP=/data/local/tmp/tcpdump_armv7

# start tcpdump. 
# 	$1 = interface
# 	$2 = the output pcap file path
start_tcpdump()
{
	su -c "$TCPDUMP -i $1 -w $2" &
}

# stop tcpdump
stop_tcpdump()
{
	su -c "killall tcpdump_armv7"
}


# dummy CPU activity to cause spikes in power reading
signal_spikes()
{
	for i in {0..2}
	do
		for i in {0..9999}
		do
			echo $((13**99)) 1>/dev/null 2>&1
		done
		sleep 2
	done
}
	
# strip the protocol from the supplied URL (if there is one) and add the
# specified protocol instead
#	$1 = url		(e.g., "google.com" or "http://www.tid.es")
#	$2 = protocol	(e.g., "http" or "https")
build_url()
{
	url=$1
	protocol=$2

	if [[ $url == *://* ]]
	then
		url=$(echo $url | awk -F "://" '{print $2}')
	fi
	url=$protocol"://"$url
	echo $url
}
