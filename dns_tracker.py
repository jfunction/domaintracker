import time
import pickle
import logging
import threading
import sys
from threading import Timer
import ConfigParser
import DNS

""" This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
    
    http://creativecommons.org/licenses/GPL/2.0/
    
    RELEASE HISTORY/CHANGELOG:
    v1.03 (15 Aug 2010)
        fixed logging hierarchy!  now we can control console and file log levels!
    v1.02 (10 Aug 2010)
        added SERVFAIL to recognise as possible status
        changed DNS resolving fail behaviour: retry 1min later
        changed monitoring start behaviour (faster by using threads)
        orphaned threads will also stop themselves if the main thread's killed
    v1.01 (3 Aug 2010)
        demarcated editable options section ("##Editable options")
        changed logging to append instead of overwriting existing log
        remember that CNAMEs are also extracted for comparison of changes
        added in minimum delay checks to account for CNAMEs' TTL being 0
        adjusted logging levels for logfile, console still outputs everything
    v1.00 (2 Aug 2010) initial release
    
    TODO
    -   Perhaps migrating configurable options out to command line parameters 
        or a separate config file?  (J): working on it
"""

# TODO: Move this out to utils with param = sections as elements in list
def get_configuration_dict():
    config_reader = ConfigParser.ConfigParser()
    config_reader.readfp(open(r'settings.conf'))
    config = dict(config_reader.items("DNS"))
    # Now deal with the fact that all types were set as strings:
    for k in ['minimum_delay', 'maximum_delay', 'dns_fail_retry_wait']:
        config[k] = int(config[k])
    for k in ['use_server']:
        config[k] = True if config[k] not in ['False', 'false', '0', 'FALSE'] else False
    return config

def init():
    """inits anything needed, duh"""
    #logging!
    rl = logging.getLogger('')
    rl.setLevel(logging.DEBUG)
    #logging: console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)  # log levels that are emitted to sysout
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    rl.addHandler(ch)
    #logging: file handler
    fh = logging.FileHandler(config['logfile'])
    fh.setLevel(logging.INFO)  # log levels that are emitted to logfile
    fh.setFormatter(formatter)
    rl.addHandler(fh)
    #DNS
    if config['use_server'] != True:
        logging.debug('Using system configured DNS resolvers')
        DNS.DiscoverNameServers()
    else:
        logging.debug('Using configured DNS resolver at ' + config['server'])

def load_config():
    """loads any related config file"""
    #dns list
    logging.debug('Loading dns list...')
    dnslist = []
    with open(config['dnslist'], 'r') as f:
        data = f.readline()
        while data != '':
            data = data.strip()
            dnslist.append(data)
            logging.debug('dns entry: ' + data)
            data = f.readline()
    logging.debug('Done loading dns list')
    return dnslist

def mainthread_is_alive():
    """tells if the main thread is alive, for child threads auto-stopping"""
    for i in threading.enumerate():
        if i.getName() == 'MainThread':
            if i.isAlive():
                return True
    return False

def check_dns(dns, last_state=''):
    """does the actual work: querying DNS, comparing, logging and scheduling"""
    #kill off if main thread is dead
    if mainthread_is_alive() != True:
        return
    
    #prep variables
    lowest_ttl = sys.maxint
    last_state_results = []
    new_state_results = []
    
    #unpickle last_state if possible
    if last_state != '':
        last_state = pickle.loads(last_state)
        #extract CNAMEs, IPs and domain status from last_state
        for i in last_state.answers:
            last_state_results.append(i['data'])
        last_state_results.append(last_state.header['status'])
        
    last_state_results = set(last_state_results)
        
    #query DNS, catching for exceptions
    resp = ''
    while resp == '':
        logging.debug('Querying dns for ' + dns)
        try:
            if config['use_server']:
                resp = DNS.Request(name=dns, server=config['server']).req()
            else:
                resp = DNS.Request(name=dns).req()
        except:
            #kill off if main thread is dead
            if mainthread_is_alive() != True:
                return
            logging.warning("Error when querying DNS, retrying later...")
            if last_state == '':
                Timer(config['dns_fail_retry_wait'], check_dns, [dns]).start()
            else:
                Timer(config['dns_fail_retry_wait'], check_dns, [dns, pickle.dumps(last_state)]).start()
            return
    
    #kill off if main thread is dead
    if mainthread_is_alive() != True:
        return
    
    #extract CNAMEs, IPs and domain status from new state
    for i in resp.answers:
        new_state_results.append(i['data'])
        logging.info(dns + ' has A/CNAME of ' + i['data'])
    new_state_results.append(resp.header['status'])
    logging.info(dns + ' status is ' + resp.header['status'])
    
    new_state_results = set(new_state_results)
    
    #do comparisons only if not the first DNS lookup
    if last_state != '':
        #compare status if possible (if any change, log)
        possible_status = set(['NXDOMAIN', 'NOERROR', 'SERVFAIL'])
        if len((last_state_results ^ new_state_results) & possible_status) > 0:
            last_status = new_status = ''
            for i in (last_state_results & possible_status): last_status = i
            for i in (new_state_results & possible_status): new_status = i
            logging.info(dns + ' has changed status from ' + last_status + 'to ' + new_status)
            
        #compare IPs if possible/relevant (if any change, log)
        domain_exists = set(['NOERROR'])
        if len(new_state_results & domain_exists) == 1:
            ip_changes = (last_state_results ^ new_state_results) - possible_status
            if len(ip_changes) > 0:
                old_ips = ''
                for i in (ip_changes & last_state_results):
                    old_ips = old_ips + i + ' '
                new_ips = ''
                for i in (ip_changes & new_state_results):
                    new_ips = new_ips + i + ' '
                logging.info(dns + ' has changed A/CNAMEs from ' + old_ips + 'to ' + new_ips)
    
    #extract new lowest TTL
    for i in resp.answers:
        if i['ttl'] < lowest_ttl: lowest_ttl = i['ttl']
    
    # avoid requerying just before TTL expires, or too often (CNAME's TTLs are 0)
    lowest_ttl = min(max(lowest_ttl + 1, config['minimum_delay']), config['maximum_delay'])

    #schedule next check when TTL is up
    logging.debug('Setting next check for ' + dns + ' in ' + str(lowest_ttl) + ' seconds')
    Timer(lowest_ttl, check_dns, [dns, pickle.dumps(resp)]).start()

def start_monitoring():
    """inits, loads configs, starts monitoring threads, starts manager"""
    init()
    dnslist = load_config()
    delay = 0
    for i in dnslist:   #start DNS monitoring
        Timer(delay, check_dns, [i]).start()
        delay += 1
    run_manager()

def stop_monitoring():
    """stops threads for the terminating of program"""
    logging.debug('Stopping threads...please WAIT!')
    logging.shutdown()  #flush logfiles
    for i in threading.enumerate():
        try: i.cancel()
        except AttributeError: pass

def run_manager():
    """thread manager, calls stop_monitoring as needed too"""
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: pass
    finally:
        stop_monitoring()

config = get_configuration_dict()
if __name__ == "__main__":
    length = len(sys.argv)    
    if length == 1:
        start_monitoring()
    elif length == 2:
        config['dnslist'] = sys.argv[1]
        start_monitoring()
    else:
        print "Error! Usage is:\npython dns_tracker.py [dns list text file]"
