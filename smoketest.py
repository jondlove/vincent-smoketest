#!/usr/bin/env python
# Vincent Smoketest
# Written by Jonathan Love, 2013
# Copyright (c) Doubledot Media Ltd

import yaml
import requests
import json
import argparse
import logging
import re
import sys
from lxml import etree
from StringIO import StringIO

class tcol:
    SUCCESS = '\033[92m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

class SmokeAssertions:
    def responseCode(self, response, expected):
        logging.debug ("{} : test expected response code".format(domain))
        if response.status_code == expected:
            return True
        else:
            logging.error("{} : FAIL : response code mismatch [e: {} || got: {}]".format(domain, expected, response.status_code))
            return False
    
    def responseContains(self, response, expected):
        logging.debug ("{} : test expected response body".format(domain))
        if re.search(expected, response.content):
            return True
        else:
            logging.error("{} : FAIL : object not in response body [e: {}]".format(domain, expected))
            return False


    def responseEncoding(self, response, expected):
        logging.debug ("{} : test expected response encoding".format(domain))
        if 'content-encoding' in response.headers:
            if expected.lower() in response.headers['content-encoding'].lower():
                return True
            else:
                logging.error("{} : FAIL : content encoding mismatch [e: {} || got: {}]".format(domain, expected, response.headers['content-encoding']))
                return False
        else:
            logging.error("{} : FAIL : missing header [e: content-encoding]".format(domain, response.url))
            return False

    def responseFormat(self, response, expected):
        logging.debug ("{} : test response format", domain)
        if expected.lower() == 'json':
            try:
                r.json()
                return True
            except ValueError:
                logging.error("{} : FAIL : invalid format [e: json]".format(domain))
                return False
        
        logging.warn("cannot test for '{}'".format(expected))
        return False
    def responseUrl(self, response, expected):
        logging.debug ("{} : test expected response url".format(domain))
        if re.match(expected, response.url):
            return True
        else:
            logging.error("{} : FAIL : url mismatch [e: /{}/ || got: '{}']".format(domain, expected, response.url))
            return False

def var_substitute(body, var_bucket):
    for c in var_bucket:
        if '%{}%'.format(c) in body:
            logging.debug('{} : substitute %{}%'.format(domain, c))
            body = body.replace('%{}%'.format(c), str(capture_bucket[c]))
    return body


if __name__=="__main__":
    check = SmokeAssertions()

    # Parse Arguments
    parser = argparse.ArgumentParser(description="Smoke test a series of web endpoints")
    parser.add_argument('sites', type=file, help="Name of sites YAML file to load (Default=main.yml)")
    parser.add_argument('-q', '--quiet', action="store_true", help="Only show site-level pass/fails")
    parser.add_argument('--loglevel', metavar="LEVEL", help="Log level (higher is more verbose). Overrides --quiet")
    parser.add_argument('--version', action="version", version="%(prog)s 0.3", help="Program version")
    
    args = parser.parse_args()

    # Set up logging
    logging.addLevelName(100, "FINAL")

    loglevel = logging.INFO
    if args.loglevel is not None:
        if args.loglevel < 1:
            loglevel = logging.WARN
        elif args.loglevel > 1:
            loglevel = logging.DEBUG
    elif args.quiet:
        loglevel = 100
    logging.basicConfig(format='[%(levelname)7s] %(name)s : %(asctime)s : %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=loglevel)
    

    # Load in the main endpoint list
    sites = yaml.load (args.sites)

    # Validate that it is, in fact, a hosts list
    requests_module = requests #Store a reference to original requests module
    app_in_error = False
    for site in sites:
        site_in_error = 0
        #@TODO: Check the 'site' entry is valid
        domain = site['domain']
        protocol = 'https://' if site['secure'] else 'http://'
        logging.info("{} : begin test".format(domain))

        # Set up the cookie bucket
        #cookie_bucket = {} if 'cookies' in site and site['cookies'] is True else None
        requests = requests_module.session() if 'session' in site and site['session'] is True else requests_module

        # Variable capture bucket!
        capture_bucket = {}

        # Load variables
        if 'variables' in site:
            for variable in site['variables']:
                capture_bucket[variable] = site['variables'][variable]

        # Load endpoints
        endpoints = yaml.load(file(site['endpoints'], 'r'))
        #@TODO: Check the 'endpoints' entry is valid
        for endpoint in endpoints:
            
            # Set up the request
            url = ''.join([protocol, domain, endpoint['url']])
            url = var_substitute(url, capture_bucket)

            method = 'get' if not 'method' in endpoint else endpoint['method']
            allow_redirects = False if not 'options' in endpoint or not 'allow_redirects' in endpoint['options'] else endpoint['options']['allow_redirects']

            # Do we have any data?
            payload = None
            if 'data' in endpoint:
                if 'body' in endpoint['data']:
                    body = endpoint['data']['body']

                    # Parse for values in capture bucket
                    body = var_substitute(body, capture_bucket)

                    # Now decide if it's raw, or form fields
                    if 'mode' in endpoint['data'] and endpoint['data']['mode'] != 'form':
                        payload = body
                    else:
                        payload = json.loads(body)
                    

            # Run the method!
            r_method = getattr(requests, method)
            logging.info("{} : {} '{}'".format(domain, method.upper(), url))
            r = r_method (url, allow_redirects=allow_redirects, data=payload)


            #@TODO: Check the 'request' method is valid

            # Do we have variables to capture?
            if 'capture' in endpoint:
                for capture in endpoint['capture']:
                    mode = 'html' if not 'mode' in capture else capture['mode']
                    name = -1
                    name = name+1 if not 'name' in capture else capture['name']
                    capture_val = None

                    if mode == 'html':
                        parser = etree.HTMLParser()
                        root = etree.parse(StringIO(r.text), parser)
                        if 'path' in capture:
                            logging.debug('{} : capture {}'.format(domain, capture['path']))
                            results = root.xpath(capture['path'])
                            if len(results) == 0:
                                logging.warn("{} : captured nothing for {} ".format(domain, capture['path']))
                            else:
                                if len(results) > 1:
                                    capture_val = []

                                for i in results:
                                    if type(i) == etree._Element:
                                        cval = etree.tostring(i, pretty_print=True)
                                    else:
                                        cval = i
                                    
                                    if type(capture_val) is list:
                                        capture_val.append(cval)
                                    else:
                                        capture_val = cval
                    
                    
                    capture_bucket[name] = capture_val
                    logging.debug("{} : '{}' has value(s) '{}'".format(domain, name, capture_val))
                            

            # Are we asserting that the response is valid?
            if 'expected' in endpoint:
                # Not all endpoints require validations (e.g. those we're capturing from)
                expected = endpoint['expected']
                didPass = True
                if 'code' in expected:
                    didPass = didPass if check.responseCode(r, expected['code']) else False
                if 'contains' in expected:
                    didPass = didPass if check.responseContains(r, expected['contains']) else False
                if 'encoding' in expected:
                    didPass = didPass if check.responseEncoding(r, expected['encoding']) else False
                if 'validate_format' in expected:
                    didPass = didPass if check.responseFormat(r, expected['validate_format']) else False
                if 'url' in expected:
                    didPass = didPass if check.responseUrl(r, expected['url']) else False
                if didPass:
                    logging.debug("{} : PASS : {}".format(domain, r.url))
                else:
                    site_in_error = site_in_error + 1
                
                if not didPass and 'stop_on_fail' in expected and expected['stop_on_fail'] is True:
                    # We can't keep processing for this site
                    logging.error ("{} : STOP : cannot continue processing".format(domain))
                    break

        if site_in_error > 0:
            logging.log(100, "{} : {}FAIL{} : {} errors encountered".format(domain, tcol.FAIL, tcol.ENDC, site_in_error))
            app_in_error = True
        else: 
            logging.log(100, "{} : {}SUCCESS{} : all tests passed".format(domain, tcol.SUCCESS, tcol.ENDC))

    if app_in_error:
        sys.exit(1)
    else:
        sys.exit(0)