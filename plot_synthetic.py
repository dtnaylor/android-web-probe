#! /usr/bin/env python

import os
import sys
import logging
import argparse
import numpy

sys.path.append('../myplot/')
import myplot

from analyze import PowerMonitorLog





def main():
    # will replace file paths with Log object
    http_bytes_to_log = {
        1000:'1kb-http.csv',
        10000:'10kb-http.csv',
        100000:'100kb-http.csv',
        1000000:'1mb-http.csv',
        10000000:'10mb-http.csv',
    }
    http_cache_bytes_to_log = {
        1000:'1kb-http-cache.csv',
        10000:'10kb-http-cache.csv',
        100000:'100kb-http-cache.csv',
        1000000:'1mb-http-cache.csv',
        10000000:'10mb-http-cache.csv',
    }
    https_bytes_to_log = {
        1000:'1kb-https.csv',
        10000:'10kb-https.csv',
        100000:'100kb-https.csv',
        1000000:'1mb-https.csv',
        10000000:'10mb-https.csv',
    }


    # load files and make log objects
    for size in http_bytes_to_log:
        path = os.path.join(args.logdir, http_bytes_to_log[size])
        log = PowerMonitorLog(path)
        http_bytes_to_log[size] = log
    
    for size in http_bytes_to_log:
        path = os.path.join(args.logdir, http_cache_bytes_to_log[size])

        # do we have stats from cache load?
        have_cache = os.path.exists(path)
        if not have_cache: break

        log = PowerMonitorLog(path)
        http_cache_bytes_to_log[size] = log
    
    for size in https_bytes_to_log:
        path = os.path.join(args.logdir, https_bytes_to_log[size])
        log = PowerMonitorLog(path)
        https_bytes_to_log[size] = log

    # plot stuff
    sizes = sorted(http_bytes_to_log.keys())
    xsizes = numpy.array(sizes)/1000.0

    # energy consumed
    http_extra_energy = []
    http_cache_extra_energy = []
    https_extra_energy = []
    http_duration = []
    http_cache_duration = []
    https_duration = []
    for size in sizes:
        http_log = http_bytes_to_log[size]
        http_extra_energy.append(http_log.above_baseline_energy_uAh / 1000.0 / 100.0)  # uAh -> mAh -> per object
        http_duration.append(http_log.duration_seconds / 100.0)  # per object time, not total
        
        if have_cache:
            http_cache_log = http_cache_bytes_to_log[size]
            http_cache_extra_energy.append(http_cache_log.above_baseline_energy_uAh / 1000.0 / 100.0)  # uAh -> mAh -> per object
            http_cache_duration.append(http_cache_log.duration_seconds / 100.0)  # per-object time, not total

        https_log = https_bytes_to_log[size]
        https_extra_energy.append(https_log.above_baseline_energy_uAh / 1000.0 / 100.0)  # uAh -> mAh -> per object
        https_duration.append(https_log.duration_seconds / 100.0)  # per-object time, not total

    if have_cache:
        myplot.plot([xsizes, xsizes, xsizes, xsizes, xsizes, xsizes],
            [https_extra_energy, https_duration, http_extra_energy, http_duration, http_cache_extra_energy, http_cache_duration],
            labels=['HTTPS Energy', 'HTTPS Time', 'HTTP Energy', 'HTTP Time', 'HTTP Cache Energy', 'HTTP Cache Time'],
            colors=['red', 'red', 'black', 'black', 'green', 'green'], linestyles=['-', '--', '-', '--', '-', '--'],
            axis_assignments=[0, 1, 0, 1, 0, 1],
            xlabel='File Size [kB]', ylabel='Energy per Object [mAh]',
            num_series_on_addl_y_axis=2, additional_ylabels=['Time per Object [s]'],
            xscale='log', height_scale=0.85, legend_text_size=16,
            legend='upper left', labelspacing=0.1, handletextpad=0.4,
            ylim=(0, 1.8), additional_ylims=[(0, 35)],
            filename=os.path.join(args.logdir, 'energy_consumption.pdf'))
    else:
        myplot.plot([xsizes, xsizes, xsizes, xsizes],
            [https_extra_energy, https_duration, http_extra_energy, http_duration],
            labels=['HTTPS Energy', 'HTTPS Time', 'HTTP Energy', 'HTTP Time'],
            colors=['red', 'red', 'black', 'black'], linestyles=['-', '--', '-', '--'],
            axis_assignments=[0, 1, 0, 1],
            xlabel='File Size [kB]', #ylabel='Energy per Object [mAh]',
            title='Wi-Fi',
            show_y_tick_labels = False,
            num_series_on_addl_y_axis=2, additional_ylabels=['Time per Object [s]'],
            legend='upper left', labelspacing=0.1, handletextpad=0.4,
            xscale='log', height_scale=0.7, width_scale=0.6, ylim=(0, 1.8), additional_ylims=[(0, 35)],
            filename=os.path.join(args.logdir, 'energy_consumption_small.pdf'))
        
        myplot.plot([xsizes, xsizes, xsizes, xsizes],
            [https_extra_energy, https_duration, http_extra_energy, http_duration],
            labels=['HTTPS Energy', 'HTTPS Time', 'HTTP Energy', 'HTTP Time'],
            colors=['red', 'red', 'black', 'black'], linestyles=['-', '--', '-', '--'],
            axis_assignments=[0, 1, 0, 1],
            xlabel='File Size [kB]', ylabel='Energy per Object [mAh]',
            #title='Wi-Fi',
            num_series_on_addl_y_axis=2, additional_ylabels=['Time per Object [s]'],
            #legend='upper left', 
            labelspacing=0.1, handletextpad=0.4,
            xscale='log', yscale='log', additional_yscales=['log'],
            height_scale=0.7, 
            #ylim=(0, 1.8), additional_ylims=[(0, 35)],
            filename=os.path.join(args.logdir, 'energy_consumption.pdf'))



    # average current
    http_mean_current = []
    https_mean_current = []
    http_stddev = []
    https_stddev = []
    http_mean_current_per_byte = []
    https_mean_current_per_byte = []
    http_stddev_per_byte = []
    https_stddev_per_byte = []
    for size in sizes:
        http_log = http_bytes_to_log[size]
        http_mean_current.append(http_log.mean_current - http_log.baseline)
        http_stddev.append(http_log.stddev_current)
        http_mean_current_per_byte.append((http_log.mean_current - http_log.baseline) / float(size))
        http_stddev_per_byte.append(http_log.stddev_current / float(size))

        https_log = https_bytes_to_log[size]
        https_mean_current.append(https_log.mean_current - https_log.baseline)
        https_stddev.append(https_log.stddev_current)
        https_mean_current_per_byte.append((https_log.mean_current - https_log.baseline) / float(size))
        https_stddev_per_byte.append(https_log.stddev_current / float(size))
    
    # average current
    myplot.plot([xsizes, xsizes], [https_mean_current, http_mean_current],
        labels=['HTTPS', 'HTTP'], yerrs=[https_stddev, http_stddev],
        linestyles=['-', '-'], colors=['red', 'black'],
        xlabel='File Size (kB)', ylabel='Mean Current (mA)',
        xscale='log', height_scale=0.7,
        filename=os.path.join(args.logdir, 'mean_current.pdf'))
    
    # average current per byte
    myplot.plot([xsizes, xsizes], [https_mean_current_per_byte, http_mean_current_per_byte],
        labels=['HTTPS', 'HTTP'], yerrs=[https_stddev_per_byte, http_stddev_per_byte],
        linestyles=['-', '-'], colors=['red', 'black'],
        xlabel='File Size (kB)', ylabel='Mean Current per Byte (mA/B)',
        xscale='log', height_scale=0.7,
        filename=os.path.join(args.logdir, 'mean_current_per_byte.pdf'))
    

if __name__ == "__main__":
    # set up command line args
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,\
                                     description='Plot power results from synthetic benchmarks.')
    parser.add_argument('logdir', default='.', help='Directory of power monitor files.')
    parser.add_argument('-q', '--quiet', action='store_true', default=False, help='only print errors')
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='print debug info. --quiet wins if both are present')
    args = parser.parse_args()

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
