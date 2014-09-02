#! /usr/bin/env python

import os
import sys
import logging
import argparse
import numpy

sys.path.append('pt4utils')
from pt4_filereader import Pt4FileReader

def last_line(filepath):
    with open(filepath, "rb") as f:
        f.seek(-2, 2)            # Jump to the second last byte.
        while f.read(1) != "\n": # Until EOL is found...
            f.seek(-2, 1)        # ...jump back the read byte plus one more.
        last = f.readline()      # Read last line.
    return last

class PowerMonitorLog(object):
    def __init__(self, filepath):
        self.filename = os.path.split(filepath)[1]

        # read current samples from file
        self._currents = self._get_currents_as_array(filepath)
        self._duration_seconds = self._read_duration(filepath)

        # look for a file named "<filepath>-baseline.csv"; if it exists, take
        # the median current in this file as the baseline
        fields = os.path.splitext(filepath)
        baseline_file = '%s-baseline%s' % fields
        if os.path.isfile(baseline_file):
            baseline_currents = self._get_currents_as_array(baseline_file)
            self._baseline = numpy.median(baseline_currents)
        else:
            self._baseline = 0

        

    def _get_currents_as_array(self, filepath):
        currents = []
        for current in self._read_currents(filepath):
            if current > 0:
                currents.append(current)
        return numpy.array(currents)

    def _read_currents(self, filepath):
        if filepath[-4:] == '.pt4':
            for smpl in Pt4FileReader.readAsVector(filepath):
                yield smpl[2].mainCurrent
        elif filepath[-4:] == '.csv':
            with open(filepath, 'r') as f:
                for line in f:
                    try:
                        current = float(line.split(',')[1])
                    except:
                        continue
                    yield current
            f.closed

    def _read_duration(self, filepath):
        if filepath[-4:] == '.pt4':
            logging.warn('Time from PT4 file not supported')
            return -1
        elif filepath[-4:] == '.csv':
            # get first timestamp
            with open(filepath, 'r') as f:
                count = 0
                for line in f:
                    if count == 0:
                        units = line.split('(')[1].split(')')[0]
                    elif count == 1:
                        first = float(line.split(',')[0])
                    else:
                        break
                    count += 1
            f.closed

            # get last timestamp
            lastline = last_line(filepath)
            last = float(lastline.split(',')[0])

            # adjust to seconds
            if units == 'min':
                duration = (last-first)*60
            else:
                duration = last-first

            return duration
        


    def _get_num_samples(self):
        return len(self._currents)
    num_samples = property(_get_num_samples)

    def _get_baseline(self):
        return self._baseline
    baseline = property(_get_baseline)
    
    def _get_min_current(self):
        return numpy.min(self._currents)
    min_current = property(_get_min_current)
    
    def _get_max_current(self):
        return numpy.max(self._currents)
    max_current = property(_get_max_current)

    def _get_mean_current(self):
        return numpy.mean(self._currents)
    mean_current = property(_get_mean_current)
    
    def _get_median_current(self):
        return numpy.median(self._currents)
    median_current = property(_get_median_current)
    
    def _get_stddev_current(self):
        return numpy.std(self._currents)
    stddev_current = property(_get_stddev_current)

    def _get_duration_seconds(self):
        return self._duration_seconds
    duration_seconds = property(_get_duration_seconds)

    def _get_energy_uAh(self, baseline=0):
        # charge = current * time
        seconds_per_sample = self.duration_seconds / float(self.num_samples)
        total_charge_mC = 0
        for current in self._currents:
            total_charge_mC += ((current-baseline) * seconds_per_sample)

        # 1 mC = 10^4/3600 * 10^-7 Ah
        #      = 10^4/3600 * 10^-7 * 10^6 uAh 
        #      = 10^3/3600 uAh 
        #      = 10/36 uAh
        total_charge_uAh = total_charge_mC * (10.0/36.0)
        return total_charge_uAh

    def _get_total_energy_uAh(self):
        return self._get_energy_uAh(0)
    total_energy_uAh = property(_get_total_energy_uAh)

    def _get_above_baseline_energy_uAh(self):
        return self._get_energy_uAh(self.baseline)
    above_baseline_energy_uAh = property(_get_above_baseline_energy_uAh)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        s = '========== %s ==========' % self.filename
        s += '\n%i samples, %f seconds' % (self.num_samples, self.duration_seconds)
        s += '\nENERGY\n  W/o Baseline:\t%f uAh\n  Total:\t%f uAh' % \
            (self.above_baseline_energy_uAh, self.total_energy_uAh)
        s += '\nCURRENT\n  Baseline:\t%f mA' % self.baseline
        s += '\n  Min:\t\t%f mA' % self.min_current
        s += '\n  Max:\t\t%f mA' % self.max_current
        s += '\n  Mean:\t\t%f mA' % self.mean_current
        s += '\n  Median:\t%f mA' % self.median_current

        return s



def main():
    
    for logfile in args.logs:
        log = PowerMonitorLog(logfile)
        print log


if __name__ == "__main__":
    # set up command line args
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,\
                                     description='Analyze power monitor logs.')
    parser.add_argument('logs', nargs='+', help='Power monitor file(s) to analyze (PT4 or CSV).')
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
