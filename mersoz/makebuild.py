#!/usr/bin/env python
import os
import re
import hashlib
from collections import OrderedDict
import StringIO
from optparse import OptionParser
import ConfigParser

from ninja_syntax import Writer


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MERGED_EXT = '.merged'


def process(cfgpath):
    cfg = ConfigParser.RawConfigParser(dict(tmp_dir='/tmp', seperator=' '))
    cfg.read(cfgpath)

    tmp_dir = cfg.get('DEFAULT', 'tmp_dir')

    build_info = {}
    for section in cfg.sections():
        if not section.startswith('Type'):
            continue

        src_dir = cfg.get(section, 'src_dir')
        tmp_dir = cfg.get(section, 'tmp_dir')
        dest_dir = cfg.get(section, 'dest_dir')
        skip_dirs = cfg.get(section, 'skip_dirs').split(',')
        seperator = cfg.get(section, 'seperator')
        options = cfg.get(section, 'options').split(',')

        if not os.path.isdir(tmp_dir):
            os.makedirs(tmp_dir)

        ftname = section.split(':')[1]
        ft_build_info = {}
        build_info[ftname] = ft_build_info
        path_ptrn = re.compile(cfg.get(section, 'path_ptrn'))

        ft_build_info['tmp_dir'] = tmp_dir
        ft_build_info['dest_dir'] = dest_dir
        ft_build_info['options'] = options
        ft_build_info['seperator'] = seperator
        if 'sort' in options:
            sort_col = cfg.get(section, 'sort_col')
            ft_build_info['sort_col'] = sort_col

        if 'merge' in options:
            merge_by = cfg.get(section, 'merge_by')
            cpaths, ginfos = make_merge_catalogs(merge_by, src_dir, tmp_dir,
                                                 skip_dirs, ftname, path_ptrn)
            ft_build_info['merge'] = (cpaths, ginfos)
            ft_build_info['merge_name'] = cfg.get(section, 'merge_name')
        elif 'sort' in options or 'zip' in options:
            sources = []
            ginfos = []
            for match, path in get_matching_files(src_dir, path_ptrn,
                                                  skip_dirs):
                sources.append(path)
                ginfos.append(match.groupdict())
            ft_build_info['sortorzip'] = (sources, ginfos)

    make_build(cfgpath, tmp_dir, build_info)


def get_matching_files(src_dir, path_ptrn, skip_dirs):
    for root, dirs, files in os.walk(src_dir, topdown=True):
        print root
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for afile in files:
            path = os.path.join(root, afile)
            match = path_ptrn.search(path)
            if match is not None:
                yield match, path


def make_merge_catalogs(merge_by, src_dir, tmp_dir, skip_dirs, ftname,
                        path_ptrn):
    catalogs = OrderedDict()
    cginfo = OrderedDict()
    for match, path in get_matching_files(src_dir, path_ptrn, skip_dirs):
        ginfo = match.groupdict()
        mkey = merge_by.format(**ginfo)
        if mkey not in catalogs:
            catalogs[mkey] = []
        assert path not in catalogs[mkey]
        if mkey not in cginfo:
            cginfo[mkey] = ginfo
        catalogs[mkey].append(path)

    cpaths = []
    ginfos = []
    for mkey, files in catalogs.iteritems():
        ginfos.append(cginfo[mkey])
        mkeys = mkey.split(',')
        cname = '{}_{}.mergecatalog'.format(ftname, '-'.join(mkeys))
        cpath = os.path.join(tmp_dir, cname)
        cpaths.append(cpath)

        _make_catalog(cpaths, cpath, files)

    return cpaths, ginfos


def _make_catalog(cpaths, cpath, files):
    # if catalog file already exists, get previous hash
    if os.path.isfile(cpath):
        hasher = hashlib.md5()
        with open(cpath, 'r') as pf:
            hasher.update(pf.read())
            prev_hash = hasher.digest()
    else:
        prev_hash = None

    hasher = hashlib.md5()
    buf = StringIO.StringIO()
    for afile in files:
        size = os.stat(afile).st_size
        buf.write('{}\t{}\n'.format(afile, size))
    hasher.update(buf.getvalue())
    cur_hash = hasher.digest()

    # write only when changed
    if cur_hash != prev_hash:
        with open(cpath, 'w') as f:
            f.write(buf.getvalue())

    buf.close()


def make_build(cfgpath, tmp_dir, build_info):
    merge_path = os.path.join(BASE_DIR, 'merge.py')

    with open('build.ninja', 'w') as f:
        n = Writer(f)

        for ftname, ft_build_info in build_info.iteritems():
            tmp_dir = ft_build_info['tmp_dir']
            dest_dir = ft_build_info['dest_dir']
            options = ft_build_info['options']
            sep = ft_build_info['seperator']
            cfgsect = 'Type:{}'.format(ftname)

            # declare rule
            cmds = []
            first = True
            if 'merge' in options:
                cmds.append('/usr/bin/env python ' + merge_path +
                            ' {} {} $in'.format(cfgpath, cfgsect))
                first = False
            if 'sort' in options:
                sortcol = ft_build_info['sort_col']
                cmds.append("sort -t \"`printf '{}'`\" -T {} -k{}".
                            format(sep, tmp_dir, sortcol) + (' $in' if first
                                                             else ''))
                first = False
            if 'zip' in options:
                cmds.append("gzip -kc" + (' $in' if first else ''))

            rule_name = '{}_rule'.format(ftname)
            n.rule(rule_name, command=' | '.join(cmds) + ' > $out')
            n.newline()

            # declare build
            _make_bulid_declare_build(n, options, dest_dir, ft_build_info,
                                      rule_name)
            n.newline()


def _make_bulid_declare_build(n, options, dest_dir, ft_build_info, rule_name):
    if 'merge' in options:
        cpaths, ginfos = ft_build_info['merge']
        for i, cpath in enumerate(cpaths):
            if 'merge' in options:
                merge_name = ft_build_info['merge_name']
                bname = merge_name.format(**ginfos[i]) + MERGED_EXT
            else:
                bname = os.path.basename(cpath).split('.')[0]
            _dest_dir = dest_dir.format(**ginfos[i])
            dpath = os.path.join(_dest_dir, bname) + \
                ('.gz' if 'zip' in options else '')
            n.build(dpath, rule_name, cpath)
    elif 'sort' in options or 'zip' in options:
        sources, ginfos = ft_build_info['sortorzip']
        for i, source in enumerate(sources):
            bname = os.path.basename(source)
            _dest_dir = dest_dir.format(**ginfos[i])
            dpath = os.path.join(_dest_dir, bname) + \
                ('.gz' if 'zip' in options else '')
            n.build(dpath, rule_name, source)


def main():
    parser = OptionParser("Usage: %prog [options] cfgpath")
    (options, args) = parser.parse_args()

    if len(args) == 0:
        parser.print_usage()
        return

    cfgpath = os.path.expanduser(args[0])
    process(cfgpath)


if __name__ == "__main__":
    main()
