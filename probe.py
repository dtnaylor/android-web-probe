#! /usr/bin/env python

import os
import sys
import re
import glob
import logging
import argparse
import subprocess
import cPickle
import time
import string
import numpy
from collections import defaultdict
from multiprocessing import Pool

sys.path.append('../myplot')
import myplot

ADB = '/usr/bin/env adb'
TCPDUMP = '/data/local/tmp/tcpdump_armv7'   # location of tcpdump binary on phone
REMOTE_TRACEDIR = '/data/local/tmp/traces'  # temp dir on phone for storing pcap traces
TSHARK = '/usr/bin/env tshark'

def sanitize_url(url):
    return re.sub(r'[/\;,><&*:%=+@!#^()|?^]', '-', url)

def load_page(url, device, numtrials=10):
    '''Load a URL numtrials times and return a list of correspnding pcap traces'''
    logging.info('Loading URL %s %i times', url, numtrials)
    
    for i in range(0, numtrials):
        # cleanup: kill tcpdump, kill browser, clear cache on phone
        try:
            # kill tcpdump
            cmd = '%s -s %s shell su -c "killall tcpdump_armv7"' % (ADB, device)
            logging.debug(cmd)
            subprocess.check_output(cmd, shell=True)

            # kill chrome
            cmd = '%s -s %s shell am force-stop com.android.chrome' % (ADB, device)
            logging.debug(cmd)
            subprocess.check_output(cmd.split())

            # kill background processes
            cmd = '%s -s %s shell am kill-all' % (ADB, device)
            logging.debug(cmd)
            subprocess.check_output(cmd.split())

            # clear cache
            cmd = '%s -s %s shell su -c "rm -rf /data/data/com.android.chrome/cache"' % (ADB, device)
            logging.debug(cmd)
            subprocess.check_output(cmd, shell=True)

            # close tabs
            cmd = '%s -s %s shell su -c "rm -rf /data/data/com.android.chrome/files"' % (ADB, device)
            logging.debug(cmd)
            subprocess.check_output(cmd, shell=True)

            #cmd = '%s -s %s shell pm clear com.android.chrome' % (ADB, device)
            #logging.debug(cmd)
            #subprocess.check_output(cmd.split())
        except Exception as e:
            logging.error('Error clearing browser cache on phone. Skipping this trial. (%s)', e)
            time.sleep(5)
            continue


        ## click "Accept" on Chrome's agreement screen
        #try:
        #    launch = '%s -s %s shell am start com.android.chrome' % (ADB, device)
        #    tap = '%s -s %s shell input tap 200 750' % (ADB, device)

        #    subprocess.check_output(launch.split())
        #    time.sleep(6)
        #    subprocess.check_output(tap.split())  # accept agreement
        #    time.sleep(2)
        #    subprocess.check_output(tap.split())  # don't sign in
        #except Exception as e:
        #    logging.error('Error dismissing Chrome agreement. Skipping this trial. (%s)', e)
        #    time.sleep(5)
        #    continue
                


        # start tcpdump on phone
        remote_trace_file = os.path.join(REMOTE_TRACEDIR, '%s-%i.pcap' % (sanitize_url(url), i))
        tcpdump_proc = None
        try:
            cmd = '%s -s %s shell "mkdir -p %s"' % (ADB, device, REMOTE_TRACEDIR)
            logging.debug(cmd)
            subprocess.check_output(cmd, shell=True)

            cmd = '%s -s %s shell "su -c \'/data/local/tmp/tcpdump_armv7 -i rmnet0 -w %s port 80 or port 443 or port 10750\'"'\
                % (ADB, device, remote_trace_file)
            logging.debug(cmd)
            tcpdump_proc = subprocess.Popen(cmd, shell=True)
        except Exception as e:
            logging.error('Error starting tcpdump on phone. Skipping this trial. (%s)', e)
            if tcpdump_proc:
                logging.getLogger(__name__).debug('Stopping tcpdump')
                tcpdump_proc.kill()
                tcpdump_proc.wait()
            time.sleep(5)
            continue

        # load page
        try:
            # lanuch browser
            cmd = '%s -s %s shell am start -a android.intent.action.VIEW -d %s com.android.chrome'\
                % (ADB, device, url)
            logging.debug(cmd)
            subprocess.check_output(cmd.split())

            # pause while page loads TODO: can we find out when load is complete?
            time.sleep(15)
        except Exception as e:
            logging.error('Error loading page. Skipping this trial. (%s)', e)
            time.sleep(5)
            continue
        finally:
            if tcpdump_proc:
                logging.getLogger(__name__).debug('Stopping tcpdump')
                tcpdump_proc.kill()
                tcpdump_proc.wait()

        # get pcap trace and remove from phone
        try:
            # copy trace from phone
            cmd = '%s -s %s pull %s %s' % \
                (ADB, device, remote_trace_file, os.path.join(args.outdir, 'traces'))
            logging.debug(cmd)
            subprocess.check_output(cmd.split())
            
            # remove from phone
            cmd = '%s -s %s shell "rm %s"' % (ADB, device, remote_trace_file)
            logging.debug(cmd)
            subprocess.check_output(cmd, shell=True)
        except Exception as e:
            logging.error('Error retreiving trace from phone: %s', e)
            time.sleep(5)
            continue

        # make sure tcpdump is dead
        try:
            cmd = '%s -s %s shell su -c "killall tcpdump_armv7"' % (ADB, device)
            logging.debug(cmd)
            subprocess.check_output(cmd, shell=True)
        except Exception as e:
            logging.error('Error killing tcpdump: %s', e)


def analyze_trace(trace):
    '''Gather statistics from a pcap trace'''
    logging.debug('Analyzing trace %s', trace)

    url = '-'.join(os.path.splitext(os.path.split(trace)[1])[0].split('-')[:-1])

    output = None
    try:
        cmd = '%s -q -z io,stat,0 -r %s' % (TSHARK, trace)
        logging.debug(cmd)
        output = subprocess.check_output(cmd.split())
    except subprocess.CalledProcessError as e:
        logging.debug('tshark errored: %s', e)  # always error; problem with tcpdump_armv7?
        output = e.output
    except Exception as e:
        logging.error('Error analyzing trace %s: %s', trace, e)
        return None, None, None
        
    lines = output.split('\n')
    seconds = float(lines[4].split(':')[1].split('secs')[0].strip())
    bytes = int(lines[10].split('|')[3].strip())
    return url, seconds, bytes

def analyze_traces(traces):
    url_to_plts = defaultdict(list)
    url_to_sizes = defaultdict(list)
    results = []
    
    # process traces individually in separate processes
    pool = Pool()
    try:
        results = pool.map_async(analyze_trace, traces).get(0xFFFF)
    except KeyboardInterrupt:
        sys.exit()

    # each result is a tuple: (url, plt, size)
    for result in results:
        url, plt, size = result
        if url:
            url_to_plts[url].append(plt)
            url_to_sizes[url].append(size)

    # save the two dicts to a pickled results file
    with open(os.path.join(args.tracedir, 'results.pickle'), 'w') as f:
        cPickle.dump((url_to_plts, url_to_sizes), f)
    f.closed

def compare_results(result_files):
    '''Takes pickled result files (produced by analyze_traces) and plots stuff'''

    filename_to_plt_list_dict = {}  # filename -> url -> list of PLTs  (seconds)
    filename_to_size_list_dict = {}  # filename -> url -> list of sizes  (bytes)

    for result_file in result_files:
        with open(result_file, 'r') as f:
            url_to_plts, url_to_sizes = cPickle.load(f)
        f.closed

        filename_to_plt_list_dict[result_file] = url_to_plts
        filename_to_size_list_dict[result_file] = url_to_sizes


    # collapse stats for each URL into mean and median
    filename_to_plt_mean_dict = defaultdict(dict)  #filename -> url -> mean PLT
    filename_to_plt_median_dict = defaultdict(dict)  #filename -> url -> median PLT
    for filename, plt_list_dict in filename_to_plt_list_dict.iteritems():
        for url, plt_list in plt_list_dict.iteritems():
            filename_to_plt_mean_dict[filename][url] = numpy.mean(plt_list)
            filename_to_plt_median_dict[filename][url] = numpy.median(plt_list)

    filename_to_size_mean_dict = defaultdict(dict)  # filename -> url -> mean size
    filename_to_size_median_dict = defaultdict(dict)  # filename -> url -> median size
    for filename, size_list_dict in filename_to_size_list_dict.iteritems():
        for url, size_list in size_list_dict.iteritems():
            filename_to_size_mean_dict[filename][url] = numpy.mean(size_list) / 1000000.0  # bytes -> MB
            filename_to_size_median_dict[filename][url] = numpy.median(size_list) / 1000000.0  # bytes -> MB


    # plot CDFs
    mean_plts = []
    median_plts = []
    mean_sizes = []
    median_sizes = []
    labels = []
    for filename in result_files:
        name = os.path.splitext(os.path.split(filename)[1])[0]
        labels.append(string.replace(string.replace(name, 'SPDY', 'Compression Proxy'), 'NoProxy', 'No Proxy'))
        mean_plts.append(filename_to_plt_mean_dict[filename].values())
        median_plts.append(filename_to_plt_median_dict[filename].values())
        mean_sizes.append(filename_to_size_mean_dict[filename].values())
        median_sizes.append(filename_to_size_median_dict[filename].values())

    # mean PLTs
    myplot.cdf(mean_plts, height_scale=0.7,
        xlabel='Mean Page Load Time (seconds)', labels=labels,
        filename=os.path.join(args.outdir, 'mean_plt.pdf'))

    myplot.cdf(median_plts, height_scale=0.7,
        xlabel='Median Page Load Time (seconds)', labels=labels,
        filename=os.path.join(args.outdir, 'median_plt.pdf'))
    
    myplot.cdf(mean_sizes, height_scale=0.7,
        xlabel='Mean Total Data Exchanged (MB)', labels=labels,
        xlim=(0, 5),
        filename=os.path.join(args.outdir, 'mean_size.pdf'))

    myplot.cdf(median_sizes, height_scale=0.7,
        xlabel='Median Total Data Exchanged (MB)', labels=labels,
        xlim=(0, 5),
        filename=os.path.join(args.outdir, 'median_size.pdf'))


    combined_sizes = []
    combined_labels = []
    for i in range(len(result_files)):
        combined_sizes.append(mean_sizes[i])
        combined_labels.append('%s (Mean)' % labels[i])
        combined_sizes.append(median_sizes[i])
        combined_labels.append('%s (Median)' % labels[i])

    myplot.cdf(combined_sizes, height_scale=0.7,
        xlabel='Total Data Exchanged [MB]', labels=combined_labels,
        xlim=(0, 5), labelspacing=0.1, handletextpad=0.4,
        filename=os.path.join(args.outdir, 'size.pdf'))

    


def main():

    # make list of URLs to load
    urls = []
    if args.url_file:
        with open(args.url_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line != '': urls.append(line.strip())
        f.closed
    if args.load_pages:
        urls += args.load_pages

    # get android device ID
    if not args.device and len(urls) > 0:
        # use the first device ID listed in "adb devices"
        try:
            cmd = '%s devices' % ADB
            logging.debug(cmd)
            output = subprocess.check_output(cmd.split())
            devices = output.strip().split('\n')[1:]
            devices = map(lambda x: x.split('\t')[0], devices)

            if len(devices) == 0:
                logging.warn('No devices found')
            elif len(devices) > 1:
                logging.warn('Multiple devices found. Using the first one (%s).' % devices[0])
                args.device = devices[0]
            else:
                args.device = devices[0]
        except Exception as e:
            logging.error('Error listing Android devices: %s', e)
            sys.exit(1)

    # load URLs (if there are any)
    if args.device:
        for url in urls:
            load_page(url, args.device, args.numtrials)

    if args.tracedir and os.path.isdir(args.tracedir):
        traces = glob.glob(args.tracedir + '/*.pcap')
        analyze_traces(traces)

    if args.resultfiles:
        compare_results(args.resultfiles)



if __name__ == "__main__":
    # set up command line args
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,\
                                     description='Web page profiler.')
    parser.add_argument('-l', '--load_pages', nargs='+', help='URL(s) to load (to load multiple pages, separate URLs with spaces). A HAR will be generated for each page in outdir.')
    parser.add_argument('-f', '--url_file', default=None, help='Profile the URLs in the specified file (one URL per line)')
    parser.add_argument('-o', '--outdir', default='.', help='Destination directory for traces and plots.')
    parser.add_argument('-n', '--numtrials', default=10, type=int, help='Number of times to load each URL.')
    parser.add_argument('-t', '--tracedir', help='Directory of pcap traces to analyze.')
    parser.add_argument('-r', '--resultfiles', nargs='+', help='Pickled result files to compare.')
    parser.add_argument('-s', '--device', help='Specific android device ID (from "adb devices").')
    parser.add_argument('-q', '--quiet', action='store_true', default=False, help='only print errors')
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='print debug info. --quiet wins if both are present')
    args = parser.parse_args()

    if not os.path.isdir(args.outdir):
        try:
            os.makedirs(args.outdir)
            os.makedirs(os.path.join(args.outdir, 'traces'))
        except Exception as e:
            logging.getLogger(__name__).error('Error making output directory: %s' % args.outdir)
            sys.exit(-1)
    
    # set up logging
    if args.quiet:
        level = logging.WARNING
    elif args.verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    logging.basicConfig(
        format = "%(levelname) -10s %(asctime)s %(module)s:%(lineno) -7s %(message)s",
        level = level
    )

    main()
