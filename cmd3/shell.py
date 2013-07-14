#! /usr/bin/env python

"""
This project is about developing a dynamic CMD class based on cmd.CMD.
We assume the following directory structure::

  ./shell.py
  ./plugins/foo.py
  ./plugins/bar.py
  ./plugins/activate.py

We have provided examples of the classes in this document

foo and bar contain some classes that include he usual do_ methods. It
also includes an activate method that is called wih the acivation
module, so you can control its behavior upon startup.

To specify the plugins please use::

  plugins = ["foo", "bar","activate"]

Now you can set a name for your class::

  name = "CmCLI"

The rest is pretty simple::

  (cmd, plugin_objects) = DynamicCmd(name, plugins)
  cmd.activate(plugin_objects)
  cmd.cmdloop()

The activate method is not called automatically as to give more
flexibility during startup.

Here are the sample classes::

   class bar:

       def activate_bar(self):
           print "... activate bar"

       def do_that(self, arg):
           print "THAT", arg


   class foo:

       def do_this(self, arg):
           print "THIS", arg
           self.activate_status()

       def activate_foo(self):
           print "... activate foo"

   class activate:

       active = False

       def do_on(self, arg):
           self.active = True
           self.activate_status()

       def do_off(self, arg):
           self.active = False
           self.activate_status()

       def activate_status(self):
           print "Active:", self.active

       def activate(self, plugins):
           d = dir(self)
           result = []
           for key in d:
               if key.startswith("activate_"):
                   result.append(key)
           print result
           for key in result:
               print "> %s" % key.replace("_"," ")
               exec("self.%s()" % key)
"""
import pkg_resources  # part of setuptools
import sys
import cmd
import readline
import glob
import os
import getopt
import textwrap
from docopt import docopt
import inspect
from pprint import pprint
from compiler.ast import flatten

quiet = False

quiet = True

#
# SETTING UP A LOGGER
#

import logging
log = logging.getLogger('cmd3')
log.setLevel(logging.DEBUG)
formatter = logging.Formatter('CMD3: [%(levelname)s] %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
log.addHandler(handler)


#
# DYNAMIC COMMAND MANAGEMENT
#
#
# Gregor von Laszewski
#
# code insired from cyberaide and cogkit, while trying to develop a
# dynamic CMD that loads from plugin directory
#

def DynamicCmd(name, plugins):

    exec('class %s(cmd.Cmd):\n    prompt="cm> "' % name)
    plugin_objects = []
    for plugin in plugins:
        classprefix = plugin['class']
        plugin_list = plugin['plugins']
        plugin_objects = plugin_objects + \
            load_plugins(classprefix, plugin_list)

    cmd = make_cmd_class(name, *plugin_objects)()
    return (cmd, plugin_objects)


def make_cmd_class(name, *bases):
    return type(cmd.Cmd)(name, bases + (cmd.Cmd,), {})


def get_plugins(dir):
    # not just plugin_*.py
    plugins = []
    list = glob.glob(dir + "/*.py")
    for p in list:
        p = p.replace(dir + "/", "").replace(".py", "")
        if not p.startswith('_'):
            plugins.append(p)
    log.info("Loading Plugins from {0}".format(dir))
    log.info("   {0}".format(str(plugins)))
    return plugins


def load_plugins(classprefix, list):
    # classprefix "cmd3.plugins."
    plugins = []
    object = {}
    for plugin in list:
        try:
            object[plugin] = __import__(
                classprefix + "." + plugin, globals(), locals(), [plugin], -1)
            exec("cls = object['%s'].%s" % (plugin, plugin))
            plugins.append(cls)
        except:
            if not quiet:
                print "No module found", plugin, classprefix
    return plugins


#
# DECORATOR: COMMAND
#

def command(func):
    classname = inspect.getouterframes(inspect.currentframe())[1][3]
    name = func.__name__
    help_name = name.replace("do_", "help_")
    doc = textwrap.dedent(func.__doc__)

    def new(instance, args):
                # instance.new.__doc__ = doc
        try:
            arguments = docopt(doc, help=True, argv=args)
            func(instance, args, arguments)
        except SystemExit:
            if not args in ('-h', '--help'):
                print "Error: Wrong Format"
            print doc
    new.__doc__ = doc
    return new

#
# MAIN
#


def create_file(filename):
    expanded_filename = os.path.expanduser(os.path.expandvars(filename))
    if not os.path.exists(expanded_filename):
        open(expanded_filename, "a").close()


def create_dir(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


def main():
    """cm.

    Usage:
      cm [--file=SCRIPT] [--interactive] [--quiet] [COMMAND ...]
      cm [-f SCRIPT] [-i] [-q] [COMMAND ...]

    Arguments:
      COMMAND                  A command to be executed

    Options:
      --file=SCRIPT -f SCRIPT  Executes the scipt
      --interactive -i         After start keep the shell interactive, otherwise quit
      --quiet       -q         Surpress some of the informational messages.
    """

    #    __version__ = pkg_resources.require("cmd3")[0].version
    #arguments = docopt(main.__doc__, help=True, version=__version__)

    arguments = docopt(main.__doc__, help=True)

    script_file = arguments['--file']
    interactive = arguments['--interactive']
    quiet = arguments['--quiet']

    def get_plugins_from_dir(dir_path, classbase):
        """dir_path/classbase/plugins"""

        if dir_path == "sys":
            dir_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), 'plugins'))
            dir_plugins = get_plugins(dir_path)
            return {"dir": dir_path, "plugins": dir_plugins, "class": classbase}

        if dir_path == ".":
            dir_path = os.path.expanduser(
                os.path.expandvars(os.path.join(os.getcwd(), 'plugins')))
            dir_plugins = get_plugins(dir_path)
            return {"dir": dir_path, "plugins": dir_plugins, "class": classbase}
        else:

            dir_path = os.path.expanduser(os.path.expandvars(dir_path))
            prefix = "{0}/{1}".format(dir_path, classbase)

            user_path = "{0}/plugins".format(prefix)

            create_dir(user_path)
            create_file("{0}/__init__.py".format(prefix))
            create_file("{0}/plugins/__init__.py".format(prefix))
            sys.path.append(os.path.expanduser(dir_path))
            dir_plugins = get_plugins(user_path)
            return {"dir": dir_path, "plugins": dir_plugins, "class": classbase}

    plugins = []
    plugins.append(dict(get_plugins_from_dir("sys", "cmd3")))
    plugins.append(dict(get_plugins_from_dir("~/.futuregrid", "cmd3local")))
    #plugins.append(dict(get_plugins_from_dir (".", "dot")))

    for plugin in plugins:
        sys.path.append(os.path.expanduser(plugin['dir']))
    sys.path.append("../..")
    sys.path.append(".")
    sys.path.append("..")

    for plugin in plugins:
        plugin['class'] = plugin['class'] + ".plugins"

    pprint(plugins)
    pprint(sys.path)

    # sys.exit()
    name = "CmCli"

    #
    # not yet quite what i want, but falling back to a flatt array
    #

    (cmd, plugin_objects) = DynamicCmd(name, plugins)

    cmd.version()
    # cmd.set_verbose(quiet)
    cmd.activate()
    cmd.do_exec(script_file)

    if len(arguments['COMMAND']) > 0:
        try:
            user_cmd = " ".join(arguments['COMMAND'])
            print ">", user_cmd
            cmd.onecmd(user_cmd)
        except:
            print "'%s' is not recognized" % user_cmd
    elif not script_file or interactive:
        cmd.cmdloop()


def is_subcmd(opts, args):
    """if sys.argv[1:] does not match any getopt options,
    we simply assume it is a sub command to execute onecmd()"""

    if not opts and args:
        return True
    return False


if __name__ == "__main__":
    main()


"""
bash$ echo "help" | shell.py > output.txt

stupid example: shell.py metric analyze -y 2013

/trunk/cog-shell/src/cogkit/Shell/CoGCli.py?revision=3648&view=markup


386def runCLI(filename=None, silent=False, interactive=False):
387    if filename == None:
388        cli = CogShell(silent)
389        cli.cmdloop()
390    else:
391        cli = CogShell(silent=True)
392        cli.do_exec(filename)
393        if interactive:
394            cli.cmdloop()
395

69    cogkit.Shell.CoGCli.runCLI(script_file, quiet, interactive)
"""
