import sys

from apps_parser import AppsFinder

try:
    print('You should have Firefox on your PC ! Ignore this message if you have it installed', end='\n')
    print('Enter keyword:')
    keyword = input()
    print('write the result to a file? y/n')
    write = input().replace(' ', '')
    write_result = False
    if len(write) > 0:
        if write == 'y':
            write_result = True
        elif write == 'n':
            write_result = False
        else:
            sys.exit()
        if len(keyword.replace(' ', '')) > 0:
            apps_finder = AppsFinder(keyword=keyword, write_result=write_result)
except KeyboardInterrupt:
    pass


