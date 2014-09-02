Android Page Load Probes
========================

This directory contains scripts that load a list of URLs on an Android device.
There are two variants: the first, designed to measure page load time, runs on
the computer and communicates with the phone using ADB; the second, designed to
measure energy consumption, runs on the device.


Page Load Time
--------------

The python script `probe.py` takes in a list of URLs, which it loads on an
Android phone via ADB. It captures pcap traces, which it can then analyze to
extract page load times and number of bytes transferred. Use it in three
stages:

1.	Capture Traces

	To capture traces, use either the `-l` flag followed by a list of URLs on
	the command line or the `-f` flag followed by a file containing a list of
	URLs, one per line.

		./probe.py -l <url1> <url2> ...
		./probe.py -f <urlfile>

2.	Analyze Traces
	
	To extract page load times and byte counts from the traces, use the `-t`
	option to point to the directory of traces created in step 1. The results
	are pickled and saved to disk (results.pickle), for use in step 3.

		./probe.py -t <tracedir>

3.	Plot Results
	
	To plot the results of one or more set of traces, use `-r` followed by a
	list of pickled results.pickle files created in step 2.

		./probe.py -r <results1> <results2> ...


Multiple instances of the probe can run at once if multiple devices are
connected. To see a list of connected devices IDs, use `adb devices`:

	$ adb devices
	List of devices attached
	0019fd9c28207e  device
	001921431bab7e  device

Then use the `-s` option to instruct the probe to use a specific device:

	./probe.py -f <urlfile> -s 0019fd9c28207e

For more options/help, run `./probe.py -h`.


Energy Usage
------------

Since the USB cable can't be connected during energy measurements, the scripts
driving energy experiments can't rely on ADB. Instead, we use bash scripts
which are launched as background process using an ADB shell, at which point the
USB cable can be disconnected. There are three scripts, one each for loading
Web objects, Web pages, and playing videos. 

The scripts share common utility code in `loadcommon.sh`. Each one logs its
activity to a file named identically to the script but with a `.log` extension
in place of `.sh`.  Each script begins and ends with three bursts of dummy CPU
activity, causing spikes to appear in the energy plot, framing the experiment
like bookends.  The scripts must be run in the background (e.g., using `&`) to
prevent them from being killed when the ADB shell dies when the USB cable is
disconnected.

1.	Objects

	`loadobjects.sh` loads individual objects using [curl for
	Android](http://curl.haxx.se/download.html). If the object is HTML,
	subresources are not loaded. Usage:

		./loadobjects.sh <protocol> <url file>

	`<protocol>` should be either "http" or "https". `<url file>` should be a
	text file containing a list of URLs, one per line. Each URL is loaded 100
	times using `<protocol>` (regardless of the protocol specified in the URL).


2. 	Pages
	
	`loadpages.sh` loads web pages using Chrome for Android.  Usage:

		./loadpages.sh <protocol> <url file>

	`<protocol>` should be either "http" or "https". `<url file>` should be a
	text file containing a list of URLs, one per line. Each URL is loaded 100
	times using `<protocol>` (regardless of the protocol specified in the URL).


3.	Videos

	`loadvideo.sh` plays a video from YouTube or Vimeo while simultaneously
	capturing a PCAP (this requires a binary of tcpdump for Android; the path
	to this binary must be set in `loadcommon.sh`). Usage:

		./loadvideo.sh [options] <video URL> <duration>

	The `<duration>` is the number of seconds the script should wait before
	terminating the PCAP (e.g., the length of the video plus a small amount of
	slack).

	Options:

	* `-v`: Video is from Vimeo (if not set, defaults to YouTube)
	* `-m`: Use the mobile version of the site (default is desktop). (NOTE:
	This flag does NOT set the user agent to force the browser to use the
	mobile site; you must do this manually. This flag only tells the script
	where on the screen it can find the Play button.)
	* `-i <interface>`: Interface for packet capture
	* `-p <seconds>`: Pause video after `<seconds>` seconds.
	* `-c <seconds>`: Close browser after `<seconds>` seconds.

	Example usage:

		./loadvideo.sh -i rmnet0 -v -m http://vimeo.com/66355682 324 &

### Power Monitor Analysis

The Monsoon Power Monitor can save logs in its own `.pt4` format or as CSV
files; our analysis script can process either.  To process the original .pt4
binary data, we use a [tool developed by
Brown](https://github.com/brownsys/pt4utils). To download pt4utils:

	git submodule init
	git submodule update

To analyze power monitor logs:

	./analyze.py log1 [log2 ...]
