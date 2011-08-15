#
# Author: Vinod Sharma
#
# vim:ts=4:sw=4:expandtab
######################################################################

"""Measures latency of visiting various websites."""

import subprocess, sys, os, time
import pickle
import random
import getopt
import atexit
import argparse
import logging
import browser
from logging import *
from browser import Browser
import re

def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.strip(),
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            add_help=False)
    parser.add_argument("-h", "--help", action="help",
                        help="Show this help message and exit")
    parser.add_argument("-t", "--timeout", type=int, default=5,
            help="Maximum # secs permitted for page loads")
    parser.add_argument("-u", "--url-file", default="sites.txt",
            help="List of URLs from to explore")
    parser.add_argument("-p", "--proxy", default=None,
            help="Proxy to use when generating load")
    parser.add_argument("--nr-trials", type=int, default=5,
            help="Number of times to measure site latencies")
    parser.add_argument("-o", "--outfile", default=None,
            help="File to dump pickled latency results to")
    args = parser.parse_args()
    return args

html_log = open("/tmp/html.log", "w")

def measure_latency(latencies_by_url):
    info("Measuring response times....")
    br = Browser()
    if args.proxy:
        info("Proxy address: " + args.proxy)
    for url, latencies in latencies_by_url.items():
        target_url = url
        if args.proxy:
            target_url = "%s/?q="%(args.proxy) + url
        start_time = time.time()
        try:
            _,_,html,_ = br.visit(target_url, timeout=args.timeout)
            html_log.write("-"*75 + "\n")
            html_log.write(url + "\n")
            html_log.write(html + "\n")
        except browser.TimeoutException:
            warn("Timed out while visiting %s"%(target_url))
            elapsed = "timeout"
        else:
            elapsed = time.time() - start_time
        latencies.append(elapsed)
    info("Measurement complete.")

if __name__ == '__main__':
    args = parse_args()
    logging.basicConfig(level=logging.INFO,
      format='[measure] %(levelname)s %(message)s',
      filename=None,
      stream=sys.stderr,
      filemode='w')

    latencies_by_url = {}
    with open(args.url_file, "r") as f:
        for line in f.readlines():
            url = "http://" + line.strip()
            latencies_by_url[url] = []

    for i in xrange(args.nr_trials):
        info("Starting trial %d."%(i+1))
        measure_latency(latencies_by_url)

    # Save pickled results to file (for charting).
    if args.nr_trials > 0 and args.outfile:
        with open(args.outfile, "w") as f:
            pickle.dump(latencies_by_url, f)
    info("Latency results: " + str(latencies_by_url))
