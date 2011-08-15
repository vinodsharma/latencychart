#
# Author: Vinod Sharma
#
# vim:ts=4:sw=4:expandtab
######################################################################

"""Workload generator."""

import subprocess, sys, os, time
import argparse
import logging
import browser
import atexit
import select
from logging import *

def __ssh_options(args):
    if args.verbose >= 3:
        opts = "-v"
    else:
        opts = "-q"
    opts += " -o StrictHostKeyChecking=no -o BatchMode=yes -o CheckHostIP=no"
    opts += " -o UserKnownHostsFile=/dev/null"
    opts += " -o ConnectTimeout=120"
    if args.identity_file:
        opts += " -i %s"%(abspath(args.identity_file))
    return opts

# Run a command on a host through ssh, throwing an exception if ssh fails
def ssh_wrap(host, command, opts, use_tty=False):
    # Don't use the -t option: it breaks collectd startup.
    cmd = "ssh -A %s %s %s@%s '%s'"%("-t" if use_tty else "", 
            __ssh_options(opts), opts.user, host, command)
    return cmd


class Workers:
    def __init__(self, worker_bin, nr_workers):
        self.worker_bin = worker_bin
        self.nr_workers = nr_workers
        self.children = []

    def start(self):
        info("Starting %d worker(s)..."%(self.nr_workers))
        start = time.time()
        bin_path = os.path.join(args.project_home, self.worker_bin)
        for i in xrange(self.nr_workers):
            arg_list = [bin_path, "-i", str(i), "-t", str(args.timeout)]
            if args.proxy:
                arg_list.extend(["-p", args.proxy])
            # XXX: replace "localhost" with remote node hostname
            cmd = ssh_wrap("localhost", ' '.join(arg_list), args)
            debug("SSH command: %s"%(cmd))
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, shell=True)
            self.children.append(p)
        end = time.time()
        info("All workers started in %f seconds."%(end-start))


    def stop(self):
        info("Stopping all worker(s)...")
        while len(self.children):
            p = self.children.pop()
            p.terminate()
            code = p.wait()
            info("Worked stopped with error code %d."%(code))
        info("All worker(s) stopped.")

    def main(self):
        """ Monitor all the children--cleanup terminated children. """
        while len(self.children):
            child_by_fd = {}
            for p in self.children:
                child_by_fd[p.stdout.fileno()] = p
            fds = child_by_fd.keys()
            r, w, e = select.select(fds, [], fds)
            for fd in r:
                p = child_by_fd[fd]
                line = p.stdout.readline()
                if not line:
                    self.children.remove(p)
                    code = p.wait()
                    if code != 0:
                        warn("Worker terminate with error code %d."%(code))
                    else:
                        info("Worker terminated, %d remaining."%(len(self.children)))
                    break

def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.strip(),
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            add_help=False)
    parser.add_argument("-h", "--help", action="help",
                        help="Show this help message and exit")
    parser.add_argument("-n", "--nr-workers", type=int, default=1,
            help="Number of workers to run concurrently")
    parser.add_argument("-t", "--timeout", type=int, default=5,
            help="Maximum # secs permitted for page loads")
    parser.add_argument("-u", "--url-file", default="sites.txt",
            help="List of URLs for workers to explore")
    parser.add_argument("-p", "--proxy", default=None,
            help="Proxy to use when generating load")
    parser.add_argument("--user", default="root",
            help="SSH user id")
    parser.add_argument("-i", "--identity-file", default=None,
            help="SSH identity file to use")
    parser.add_argument("-v", "--verbose", type=int, default=0,
            help="Output diagnostics (for debugging)")
    parser.add_argument("project_home", 
            help="Root directory of project")
    args = parser.parse_args()
    return args

def do_cleanup():
    workers.stop()

if __name__ == '__main__':
    args = parse_args()
    logging.basicConfig(level=logging.INFO,
      format='[controller] %(levelname)s %(message)s',
      filename=None,
      stream=sys.stderr,
      filemode='w')

    latencies_by_url = {}
    with open(args.url_file, "r") as f:
        for line in f.readlines():
            url = "http://" + line.strip()
            latencies_by_url[url] = []

    workers = Workers("worker", args.nr_workers)
    workers.start()
    atexit.register(do_cleanup)
    info("Monitoring worker(s) (Ctrl+C to quit)...")
    workers.main()
