#!/usr/bin/env python
# coding=utf-8
# $Id$

"""
branchdiff.py
--------
Usage: branchdiff.py versioned_file Class.function [-b branch1,branch2,...] [--ann] [--trunk] [-o url1,url2,...]

Compares the function 'Class.function' from versioned_file with the same
function as it appears in the same file on branches branch1, branch2 and so on.

If the -b argument is not used, it compares with all available branches.

eg.
$ python branchdiff.py branchdiff.py command_output
--- branchdiff.py
+++ https://svn.example.com/svn/branchdiff/branches/old/branchdiff.py
 def command_output(...):
-    \"\"\" This is a new line in my working copy \"\"\"
-    # This was added by a previous revision.
     some code
+    some code that has been removed in my working copy

--- branchdiff.py
+++ https://svn.example.com/svn/branchdiff/branches/empty/branchdiff.py (MISSING)
-def command_output(...):
-    \"\"\" This is a new line in my working copy \"\"\"
-    # This was added by a previous revision.
-    some code
$
"""

__author__ = "Richard Mitchell <richard.mitchell@isotoma.com>"
__version__ = "$Revision$"[11:-2]
__docformat__ = "restructuredtext en"

import difflib
import optparse
import tokenize
import re
import StringIO
import subprocess

def command_output(cmd):
    """ Capture a command's standard output. """
    return subprocess.Popen(cmd.split(),
                            stdout=subprocess.PIPE).communicate()[0]

def get_all_branches(branches_root):
    return [b[:-1] for b in command_output('svn ls %s' % (branches_root,)).split('\n') if b[:-1]]

def get_block_lines(code, block_name):
    """ Get start & end lines of a block of code for a given dotted Class / function name from the
        provided code string.
        
    """
    block_path = block_name.split('.')
    code_generator = StringIO.StringIO(code)
    tokens = tokenize.generate_tokens(code_generator.readline)
    level = 0
    start_line = 0
    start_level = None
    traverse_level = None
    end_line = None
    
    while (block_path or (start_line and not end_line)) and tokens:
        try:
            t = tokens.next()
        except StopIteration:
            break
        except tokenize.TokenError:
            print "Token error at line: %d" % (t[3][0],)
            break
        if t[0] == tokenize.INDENT:
            level += 1
        elif t[0] == tokenize.DEDENT:
            level -= 1
            if start_level is not None and level == start_level:
                end_line = t[3][0]
                break
            if traverse_level is not None and level<traverse_level:
                start_line = None
                break

        if t[1] in ('def', 'class'):
            name = tokens.next()
            if block_path and name[1] == block_path[0]:
                block_path = block_path[1:]
                traverse_level = level
                if not block_path:
                    # finished traversing
                    # begin counting
                    start_line = name[2][0]
                    start_level = level

    return (start_line, end_line)
    
def get_diffs(filename, block_name, branch_file_paths, show_ann=False):
    """ Returns a dict of diffs from the block block_name in file filename to
        the same block in the URLs listed in branch_file_paths.
        
    """
    diffs = {}
    file = open(filename, 'r')
    base_code = file.read()
    base_start, base_end = get_block_lines(base_code, block_name)
    base_ann = []
    if base_start is None or base_end is None:
        raise RuntimeError("Code block does not exist in given source.")
    base_block = base_code.split('\n')[base_start-1:base_end-1]
    if show_ann:
        base_block_ann = command_output('svn ann %s' % (filename,)).split('\n')[base_start-1:base_end-1]
    for path in branch_file_paths:
        branch_code = command_output('svn cat %s' % (path,))
        branch_ann = []
        if show_ann:
            branch_ann = command_output('svn ann %s' % (path,)).split('\n')
        (start_line, end_line) = get_block_lines(branch_code, block_name)
        branch_diff = []
        if start_line is not None and end_line is not None:
            codelines = branch_code.split('\n')
            branch_block = codelines[start_line-1:end_line-1]
            branch_diff = list(difflib.unified_diff(base_block, branch_block,
                                                    filename, path))
            if show_ann and branch_diff:
                branch_block_ann = branch_ann[start_line-1:end_line-1]
                branch_diff = list(difflib.unified_diff(base_block_ann, branch_block_ann,
                                                        filename, path))
            if not branch_diff:        
                branch_diff = ['--- %s' % (filename,), '', '+++ %s' % (path,), '', ' IDENTICAL ', '']
        else:
            branch_diff = ['--- %s' % (filename,), '', '+++ %s (MISSING)' % (path,),
                           ''] + ['-%s' % (line,) for line in base_block]
        diffs[path] = branch_diff
    return diffs

def main():
    usage = """usage: %prog [options] file (classname|classname.functionname|functionname|...)"""
    parser = optparse.OptionParser(usage = usage)
    parser.add_option("-b", "--branches", dest="branches", help="specify a comma-separated list of branch names")
    parser.add_option("-a", "--ann", action="store_true", dest="ann", default=False, help="show revision author information inline")
    parser.add_option("-t", "--trunk", action="store_true", dest="trunk", default=False, help="include diffs from trunk")
    parser.add_option("-o", "--others", dest="others", help="specify a comma-separated list of other URLs which should be diffed against the given file")
    (options, args) = parser.parse_args()
    if len(args) != 2:
        parser.error("incorrect number of arguments")
    filename = args[0]
    block = args[1]
    svn_url = re.search('URL:\s+(.*?)\n', command_output('svn info %s' % (filename,)))
    if not svn_url:
        parser.error("File %s is not versioned")
    svn_url = svn_url.group(1)
    svn_path = re.search('^(.*?)/(?:branches/[^/]*|trunk|tags/[^/]*)/(.*)$', svn_url)
    if not svn_path:
        parser.error("File %s is not in a 'branches', 'trunk' or 'tags' directory." % (filename,))
    branches_root = '%s/branches' % (svn_path.group(1),)
    relative_path = svn_path.group(2)
    branches = []
    if not options.branches:
        branches = get_all_branches(branches_root)
    else:
        branches = options.branches.split(',')
    branches = ['%s/%s/%s' % (branches_root, b, relative_path) for b in branches]
    if options.trunk:
        branches.append('%s/trunk/%s' % (svn_path.group(1), relative_path))
    if options.others:
        branches = branches + options.others.split(',')
    
    diffs = get_diffs(filename, block, branches, show_ann=options.ann)
    for path in diffs:
        for line in diffs[path]:
            print line
            
if __name__ == '__main__':
    main()
