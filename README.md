# Python utility to find location match for given URI
#### Table of Contents
  - [Introduction](#introduction)
  - [Included content](#included-content)
  - [Requirements](#requirements)
  - [Usage](#usage)

## Introduction
The "location_match_finder" utility searches for a location that matches a given request. Location search is carried out in accordance with the [location block selection algorithm](https://nginx.org).

Testing was carried out on Nginx version 1.18.0


## Included content
  - Source code:
    - [location_match_finder.py](location_match_finder.py) - Script source code
  - Test suites:
    - [nginx-config-example.conf](tests/nginx-config-example.conf) - An example of the Nginx configuration file format
    - [uri.list](tests/uri.list) - List of URIs for script testing

## Requirements
To successfully run the "location_match_finder" utility, you must pass the required parameters:
  - "--config-file=PATH" - Path to Nginx configuration file containing locations
  - "--uri=URI" - Request URI in normalized form for which the search will be performed

To successfully parse the Nginx configuration file, all [location](http://nginx.org/en/docs/http/ngx_http_core_module.html#location) directives must be converted to the following format:
  - A line with a first-level directive must start with 4 spaces or 1 tab character
  - A line with a second-level directive must start with 8 spaces or 2 tab characters
  - A line with a third-level directive must start with 12 spaces or 3 tab characters
  - All processed directives must be in a single file ([include](http://nginx.org/ru/docs/ngx_core_module.html#include) directive are not supported)

See example [nginx-config-example.conf](tests/nginx-config-example.conf)

## Usage
Example of launching the Utility:
```bash
./location_finder.py config-file=tests/nginx-config-example.conf uri=/batchBoomer.xml
```

The result of the execution will be a hierarchical list of locations traversed during the search for a match
```bash
Level 1: /batch
        Level 2: /batchBoom
                Level 3: /batchBoomer
                Level 3: ~ .xml$
```
And a message indicating the final location where the request will be processed
```bash
Request [ /batchBoomer.xml ] will be processed by Level 3 location [ ~ .xml$ ]
```
