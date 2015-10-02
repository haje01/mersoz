import os
import re
import codecs
from optparse import OptionParser
import ConfigParser
from StringIO import StringIO


def main():
    parser = OptionParser("Usage: %prog [options] cfgpath cfgsect "
                          "catalog-path")
    (options, args) = parser.parse_args()
    if len(args) < 3:
        parser.print_usage()
        return

    cfg = ConfigParser.RawConfigParser(dict(seperator=' ',
                                            merge_charset='utf8'))
    cfgpath = os.path.expanduser(args[0])
    cfg.read(cfgpath)
    cfgsect = args[1]
    catalog = args[2]

    path_ptrn = re.compile(cfg.get(cfgsect, 'path_ptrn'))
    charset = cfg.get(cfgsect, 'merge_charset')
    seperator = cfg.get(cfgsect, 'seperator')
    line_head = cfg.get(cfgsect, 'merge_line_head')

    with open(catalog, 'r') as cf:
        for cline in cf:
            afile = cline.rstrip().split('\t')[0]
            match = path_ptrn.search(afile)
            if match is None:
                continue

            ginfo = match.groupdict()
            lhead = seperator.join(line_head.format(**ginfo).split(','))
            buf = StringIO()
            with codecs.open(afile, 'r', charset, errors='ignore') as f:
                for line in f.readlines():
                    line = line.rstrip()
                    if len(line) > 0:
                        buf.write(u'{}{}{}\n'.format(lhead, seperator, line))
            print buf.getvalue().rstrip().encode('utf8')
            buf.close()


if __name__ == "__main__":
    main()
