# Mersoz

Merge, Sort and Zip Files.

## Prerequsites

### [Ninja](https://ninja-build.org) (Build System)

    $ git clone git://github.com/ninja-build/ninja.git && cd ninja
    $ git checkout release
    $ ./configure —bootstrap
    $ cp ./ninja /usr/local/bin

### Ninja Syntax for Python

    $ pip install ninja_syntax

## Make Mersoz Config File

Make Mersoze config directory first.

    $ mkdir -p /etc/mersoz && cd /etc/mersoz

Then, edit your config file following the sample.

	$ vi {PROJ_NAME}.cfg

This is a sample config.

    # common settings
    [DEFAULT]
    # temp directory for sort
    tmp_dir=/logdata/c9/_var_/tmp/mersoz
    skip_dirs=_var_,dblog,lost+found
    
    # specific settings for GameServer file type
    [Type:GameServer]
    # directory where target files are located
    src_dir=/logdata/c9
    
    # filter files by path pattern
    path_ptrn=c9/(?P<node>[^/]+).*GameServer_(?P<proc>\d+)_(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2}).*_Log.txt
    
    # do merge, sort & zip task
    options=merge,sort,zip
    
    # merge keys
    merge_by={year},{month},{day}
    
    # merged file name
    merge_name=GameServer_{year}-{month}-{day}
    
    # convert target file's charset into UTF8 while merging
    merge_charset=cp949
    
    # merged file's head columns
    merge_line_head={node},{proc}
    
    # columns by which rows are to be sorted
    sort_col=3,4
    
    # destination directory 
    dest_dir=/logdata/.wrangled/c9/log/{year}/{month}
    
    # specific settings for TblLog file type
    [Type:TblLog]
    src_dir=/logdata/c9/dblog
    path_ptrn=c9/dblog/C9-(?P<node>[^/]+)/TblLogOpr_(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2}).csv
    options=sort,zip
    dest_dir=/logdata/.wrangled/c9/dblog/{node}/{year}/{month}
    sort_col=2
    # field seperator for line parser
    seperator=|

## Prepare Mersoz

Clone Mersoz and CD into it.

    $ git clone https://github.com/haje01/mersoz.git && cd mersoz

Make Ninja build file.

    $ python -m mersoz.makebuild /etc/mersoz/{PROJ_NAME}.cfg

## Run

Run Ninja build file, which will execute your tasks. (in parallel)

    $ sudo /usr/loca/bin/ninja

----

Have fun!
