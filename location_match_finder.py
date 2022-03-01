#!/usr/bin/python3.6

import os
import re
import sys


# Argument validation
def argument_validation():
    if len(sys.argv) == 1:
        help_message()
    for argument in sys.argv[1:]:
        if 'config-file=' in argument:
            try:
                config_file = open(argument.partition('=')[2], 'r')
            except Exception as exc:
                print(exc, '\n')
                help_message()
        elif 'uri=' in argument:
            uri = argument.partition('=')[2]
        else:
            help_message()
    return uri, config_file


# Help message print
def help_message():
    print(
        'Unrecognized options!\n'
        'Please specify the required options:\n'
        '  --config-file=PATH	Path to Nginx configuration file containing locations\n'
        '  --uri=URI		Request URI in normalized form\n\n'
        'example: \'./location_finder.py config-file=/etc/nginx/sites-available/default uri=/index.html\''
    )
    quit()


# This function creates a table containing an indexed hierarchical structure of locations
def get_locations_table(config_file):
    # Create a hierarchical list of locations (HLL)
    HLL = []

    lvl_1_index = 0
    for line in config_file:
        # Search for first level locations
        if re.search('^\s{4}location', line) or re.search('^\tlocation', line):
            res = location_directive_parser(line)
            HLL.append({'index': lvl_1_index, 'lvl': 1, 'modifier': res[0], 'location_match': res[1],
                        'sub_location': []})
            lvl_1_index += 1
            lvl_2_index = 0

        # Search for second level locations
        if re.search('^\s{8}location', line) or re.search('^\t{2}location', line):
            res = location_directive_parser(line)
            HLL[(lvl_1_index - 1)]['sub_location'].append({'index': lvl_2_index, 'lvl': 2, 'modifier': res[0],
                                                           'location_match': res[1], 'sub_location': []})
            lvl_2_index += 1
            lvl_3_index = 0

        # Search for third-level locations
        if re.search('^\s{12}location', line) or re.search('^\t{3}location', line):
            res = location_directive_parser(line)
            HLL[(lvl_1_index - 1)]['sub_location'][(lvl_2_index - 1)]['sub_location'].append({'index': lvl_3_index,
                                                                                              'lvl': 3,
                                                                                              'modifier': res[0],
                                                                                              'location_match': res[1],
                                                                                              'sub_location': []})
            lvl_3_index += 1
    return HLL


# Return "modifier" and location match string specified in the Location directive.
def location_directive_parser(line):
    if re.match(r'=|~|~\*|\^~', line.split()[1]):
        modifier = line.split()[1]
        location_match = line.split()[2]
    else:
        modifier = None
        location_match = line.split()[1]
    return modifier, location_match


# Finding a location with a descent to deeper levels
def find_deepest_level_location(locations, uri, matching_method):
    current_route = []
    for lvl in range(3):
        if lvl == 0:
            # Finding location on the 1st level
            current_location = matching_method(locations, uri)
        else:
            # Finding location on sub location levels
            current_location = matching_method(current_location['sub_location'], uri)
        if current_location:
            # Saves the path that was laid as a result of the search
            current_route.append(current_location)
            if current_location['sub_location']:
                continue
            else:
                return current_route
        else:
            return current_route


# Finding an exact match or longest prefix location in a specific level list
def find_longest_prefix_location(locations_list, uri):
    current_prefix_location = None
    prev_found_prefix = ''
    for element in locations_list:
        modifier = element.get('modifier')
        location_match = element.get('location_match')
        # Finding exact match
        if modifier == '=':
            if uri == location_match:
                current_prefix_location = element
                return current_prefix_location
        # Finding the longest prefix
        elif modifier == None or modifier == '^~':
            current_prefix = os.path.commonprefix([uri, location_match])
            if current_prefix > prev_found_prefix:
                prev_found_prefix = current_prefix
                current_prefix_location = element
    return current_prefix_location


# This function climbs up the path taken as a result of the prefix location search.
def find_regexp_location(locations_list, uri, paved_route):
    if paved_route:
        lvl_count = len(paved_route)
    else:
        return
    if lvl_count == 3:
        # Case with 3-level paved route
        lvl_1_index = paved_route[0]['index']
        lvl_2_index = paved_route[1]['index']
        lvl_3_index = paved_route[2]['index']
        # Forming lists of sub locations of the 1st and 2nd levels
        lvl_1_sublocations_list = locations_list[lvl_1_index]['sub_location']
        lvl_2_sublocations_list = locations_list[lvl_1_index]['sub_location'][lvl_2_index]['sub_location']

        if lvl_2_sublocations_list[lvl_3_index]['modifier'] != "^~":
            # Search for the deepest location of the regular expression among the 3rd level locations of the paved route
            found_regexp_location = find_deepest_level_location(lvl_2_sublocations_list, uri, search_regexp_match)
            if found_regexp_location:
                return found_regexp_location
            if lvl_1_sublocations_list[lvl_2_index]['modifier'] != "^~":
                # Search for the deepest location of the regular expression among the 2rd level locations of the paved route
                found_regexp_location = find_deepest_level_location(lvl_1_sublocations_list, uri, search_regexp_match)
                if found_regexp_location:
                    return found_regexp_location

    elif lvl_count == 2:
        # Case with 2-level paved route
        lvl_1_index = paved_route[0]['index']
        lvl_2_index = paved_route[1]['index']
        # Forming lists of sub locations of the 1st level
        lvl_1_sublocations_list = locations_list[lvl_1_index]['sub_location']

        if lvl_1_sublocations_list[lvl_2_index]['modifier'] != "^~":
            # Search for the deepest location of the regular expression among the 2rd level locations of the paved route
            found_regexp_location = find_deepest_level_location(lvl_1_sublocations_list, uri, search_regexp_match)
            if found_regexp_location:
                return found_regexp_location

    # Search for regular expressions at the first level
    lvl_1_index = paved_route[0]['index']
    if locations_list[lvl_1_index]['modifier'] != "^~":
        # Search for the deepest location of the regular expression among the 1rd level locations of the paved route
        found_regexp_location = find_deepest_level_location(locations_list, uri, search_regexp_match)
        if found_regexp_location:
            return found_regexp_location


# Finding a regular expression match location
def search_regexp_match(locations, uri):
    for element in locations:
        modifier = element.get('modifier')
        if modifier == "~":
            found_match = re.search(element.get('location_match'), uri)
            if found_match:
                return element
        elif modifier == "~*":
            found_match = re.search(element.get('location_match'), uri, flags=re.IGNORECASE)
            if found_match:
                return element


# Formation of output information
def show_output(uri, prefix_route, regexp_route):
    if prefix_route or regexp_route:
        print('The following locations were traversed in the match searching process:')
        if prefix_route:
            show_route(prefix_route)
            route = prefix_route
        if regexp_route:
            try:
                if route[-1]['modifier'] == '=':
                    pass
                else:
                    show_route(regexp_route)
                    route += regexp_route
            except BaseException:
                pass
        print()
        print('Request [ {} ] will be processed by level {} location [ {} {} ]'.format(uri, route[-1]['lvl'],
                                                                                       route[-1]['modifier'],
                                                                              route[-1]['location_match']))
    else:
        print('No matching location found for request "{}"'.format(uri))


# Show a list of traversed locations
def show_route(locations):
    for element in locations:
        lvl = element['lvl']
        modifier = element['modifier']
        location_match = element['location_match']
        if modifier != None:
            print('{}Level {}: {} {}'.format('\t' * (lvl - 1), lvl, modifier, location_match))
        else:
            print('{}Level {}: {}'.format('\t' * (lvl - 1), lvl, location_match))


def main():
    URI, CONFIG_FILE = argument_validation()
    HLL = get_locations_table(CONFIG_FILE)
    PAVED_PREFIX_ROUTE = find_deepest_level_location(HLL, URI, find_longest_prefix_location)
    PAVED_REGEXP_ROUTE = find_regexp_location(HLL, URI, PAVED_PREFIX_ROUTE)
    show_output(URI, PAVED_PREFIX_ROUTE, PAVED_REGEXP_ROUTE)


main()
