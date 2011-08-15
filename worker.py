#!/usr/bin/env python
#
# vim:ts=4:sw=4:expandtab
######################################################################

"""Worker task: does the actual browsing work."""

import sys
import random
import time
import os
import argparse
import uuid
import logging
import browser
from collections import deque
from logging import *
from browser import Browser

workq = deque()

def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.strip(),
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            add_help=False)
    parser.add_argument("-h", "--help", action="help",
                        help="Show this help message and exit")
    parser.add_argument("-i", "--id", default=None,
            help="ID to assign to worker (for debugging)")
#    parser.add_argument("-l", "--logname", default="/tmp/worker",
#            help="Name of database to store results in")
    parser.add_argument("-m", "--branch-factor", type=int, default=5,
            help="Branching factor of crawl tree")
    parser.add_argument("-t", "--timeout", type=int, default=10,
            help="Maximum # of secs to wait for page load")
    parser.add_argument("-u", "--url-file", default="sites.txt",
            help="List of URLs from to explore")
    parser.add_argument("-p", "--proxy", default=None,
            help="Proxy to use when generating load")
    parser.add_argument("-w", "--wait-time", type=float, default=4.0,
            help="Average # seconds to pause between page visits.")
    args = parser.parse_args()
    return args


def do_browse_work(url):
    # Scrape the child urls first without going through the proxy.
    _,_,_,child_urls = no_proxy_browser.visit(url, timeout=args.timeout)
    workq.extend(child_urls)
    info("Added %d urls to workq."%(len(child_urls)))
    # Now generate load for the proxy.
    if args.proxy:
        br = Browser()
        target_url = "%s/?q="%(args.proxy) + url
        br.visit(target_url, timeout=args.timeout)

if __name__ == '__main__':
    args = parse_args()
    if args.id == None:
        args.id = str(uuid.uuid4())[0:2]

    logging.basicConfig(level=logging.INFO,
      format="[worker-%s] "%(args.id) + "%(levelname)s %(message)s",
      stream=sys.stderr,
      filemode='w')

    no_proxy_browser = Browser(args.branch_factor)
    info("Worker started")

    # Read the URLs and shuffle their order: we don't want all workers
    # visiting the same URLs at the same time. It's more realistic.
    with open(args.url_file, "r") as f:
        lines = f.readlines()
    random.shuffle(lines)
    for line in lines:
        url = "http://" + line.strip()
        workq.append(url)

    while len(workq):
        url = workq.popleft()
        try:
            do_browse_work(url)
        except browser.TimeoutException:
            warn("Timed out while visiting %s"%(url))
        else:
            time.sleep(random.normalvariate(args.wait_time, 0.5))
    info("Worker terminating.")
