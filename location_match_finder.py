#!/usr/bin/python3

import re
import sys as system

# Constants for argument parsing and location levels
CONFIG_FILE_ARG_PREFIX = '--config-file='
URI_ARG_PREFIX = '--uri='
FIRST_LEVEL = 1
SECOND_LEVEL = 2
THIRD_LEVEL = 3


# Argument validation
def argument_validation():    
    # Check if any arguments are passed. If not, display help message and exit.
    if len(system.argv) == 1:
        help_message()
    
    config_file = None
    uri = None
    
    # Iterate through the arguments passed to the script.
    for argument in sys.argv[1:]:        
        if CONFIG_FILE_ARG_PREFIX in argument:
            config_file_path = argument.partition('=')[2]            
            
            # Attempt to open the config file in read mode.
            try:
                config_file = open(config_file_path, 'r')
            except Exception as exc:
                print(exc, '\n')
                help_message()
                
        elif URI_ARG_PREFIX in argument:

            # Extract the uri from the argument.
            uri = argument.partition('=')[2]
            
        else:
            # If an unrecognized option is provided, display help and exit.
            help_message()
            
    return uri, config_file


# Help message print
def help_message():
    print(
        'Unrecognized options!\n'
        'Please specify the required options:\n'
        '  --config-file=PATH	Path to Nginx configuration file containing locations\n'
        '  --uri=URI		Request URI in normalized form\n\n'
        'example: \'./location_finder.py --config-file=/etc/nginx/sites-available/default --uri=/index.html\''
    )
    quit()


# This function creates a table containing an indexed hierarchical structure of locations
def get_locations_table(config_file):
    hierarchical_locations = []
    first_level_index = 0
    
    for line in config_file:
        # Search for first level locations
        if re.search('^\s{4}location', line) or re.search('^\tlocation', line):
            directive = location_directive_parser(line)
            hierarchical_locations.append({'index': first_level_index, 'lvl': FIRST_LEVEL, 'modifier': directive[0], 'location_match': directive[1],
                        'sub_location': []})
            first_level_index += 1
            second_level_index = 0

        # Search for second level locations
        if re.search('^\s{8}location', line) or re.search('^\t{2}location', line):
            directive = location_directive_parser(line)
            hierarchical_locations[(first_level_index - 1)]['sub_location'].append({'index': second_level_index, 'lvl': SECOND_LEVEL, 'modifier': directive[0],
                                                                                       'location_match': directive[1], 'sub_location': []})
            second_level_index += 1
            third_level_index = 0

        # Search for third-level locations
        if re.search('^\s{12}location', line) or re.search('^\t{3}location', line):
            directive = location_directive_parser(line)
            hierarchical_locations[(first_level_index - 1)]['sub_location'][(second_level_index - 1)]['sub_location'].append({'index': third_level_index,
                                                                                              'lvl': THIRD_LEVEL, 'modifier': directive[0],
                                                                                              'location_match': directive[1], 'sub_location': []})
            third_level_index += 1
    return hierarchical_locations


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
    traversed_route = []
    for level in range(3):
        if level == 0:
            # Finding location on the 1st level
            current_location = matching_method(locations, uri)        
        else:
            # Finding location on sub location levels
            current_location = matching_method(current_location['sub_location'], uri)
            
        if current_location:
            traversed_route.append(current_location)
            if current_location['sub_location']:
                continue
            else:
                return current_route
        else:
            return current_route


# Finding an exact match or longest prefix location in a specific level list
def find_longest_prefix_location(locations_list, uri):
    current_prefix_location = None
    # Initialize an empty string to track the previously found prefix
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
            # Find a match for the longest prefix of the location
            current_prefix = re.match(location_match, uri)
            if current_prefix != None:
                current_prefix = current_prefix.group(0)
                if current_prefix > prev_found_prefix:
                    prev_found_prefix = current_prefix
                    current_prefix_location = element
    return current_prefix_location


# This function climbs up the path taken as a result of the prefix location search.
def find_regexp_location(locations_list, uri, paved_route):
    if not paved_route:
        return
    
    route_level_count = len(paved_route)
    
    if route_level_count == THIRD_LEVEL:
        # Case with 3-level paved route
        first_level_index = paved_route[0]['index']
        second_level_index = paved_route[1]['index']
        third_level_index = paved_route[2]['index']
        # Forming lists of sub locations of the 1st and 2nd levels
        first_level_sublocations_list = locations_list[first_level_index]['sub_location']
        second_level_sublocations_list = locations_list[first_level_index]['sub_location'][second_level_index]['sub_location']

        if second_level_sublocations_list[third_level_index]['modifier'] != "^~":
            # Search for the deepest location of the regular expression among the 3rd level locations of the paved route
            found_regexp_location = find_deepest_level_location(second_level_sublocations_list, uri, search_regexp_match)
            if found_regexp_location:
                return found_regexp_location
            if first_level_sublocations_list[second_level_index]['modifier'] != "^~":
                # Search for the deepest location of the regular expression among the 2rd level locations of the paved route
                found_regexp_location = find_deepest_level_location(first_level_sublocations_list, uri, search_regexp_match)
                if found_regexp_location:
                    return found_regexp_location

    elif route_level_count == SECOND_LEVEL:
        # Case with 2-level paved route
        first_level_index = paved_route[0]['index']
        second_level_index = paved_route[1]['index']
        # Forming lists of sub locations of the 1st level
        first_level_sublocations_list = locations_list[first_level_index]['sub_location']

        if first_level_sublocations_list[second_level_index]['modifier'] != "^~":
            # Search for the deepest location of the regular expression among the 2rd level locations of the paved route
            found_regexp_location = find_deepest_level_location(first_level_sublocations_list, uri, search_regexp_match)
            if found_regexp_location:
                return found_regexp_location

    # Search for regular expressions at the first level
    first_level_index = paved_route[0]['index']
    if locations_list[first_level_index]['modifier'] != "^~":
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
    # Step 1: Validate command-line arguments and get URI and config file
    uri, config_file = argument_validation()
    
    # Step 2: Parse the config file and build the hierarchical locations table
    hierarchical_locations_table = get_locations_table(config_file)
    
    # Step 3: Find the deepest level location based on prefix matching
    prefix_match_route = find_deepest_level_location(hierarchical_locations_table, uri, find_longest_prefix_location)
    
    # Step 4: Find a matching location using regular expressions, based on the prefix route
    regexp_match_route = find_regexp_location(hierarchical_locations_table, uri, prefix_match_route)
    
    # Step 5: Display the output, showing the traversed routes and the final matching location
    show_output(uri, prefix_match_route, regexp_match_route)

main()
