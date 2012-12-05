#   Copyright 2012 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2012 Red Hat, Inc.
#
#   This is free software: you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful, but
#   WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see
#   <http://www.gnu.org/licenses/>.

ENABLE_PROFILE=0

import gcc

from sm.solver import Context, solve, SHOW_SUPERGRAPH

class IpaSmPass(gcc.IpaPass):
    def __init__(self, checkers, options, selftest):
        gcc.IpaPass.__init__(self, 'sm-ipa-pass')
        self.checkers = checkers
        self.options = options
        self.selftest = selftest

    def execute(self):
        if self.options.during_lto:
            # LTO pass:
            # Only run the analysis during the link, within lto1, not for each
            # cc1 invocation:
            if not gcc.is_lto():
                return

        if 0:
            from gccutils import callgraph_to_dot, invoke_dot
            dot = callgraph_to_dot()
            invoke_dot(dot)

        # Interprocedural implementation, using the supergraph of all calls:
        from gccutils.graph import Supergraph
        sg = Supergraph(split_phi_nodes=True)
        if SHOW_SUPERGRAPH:
            dot = sg.to_dot('supergraph')
            from gccutils import invoke_dot
            # print(dot)
            invoke_dot(dot)

        for checker in self.checkers:
            for sm in checker.sms:
                ctxt = Context(checker, sm, sg, self.options)

                def run():
                    solve(ctxt, 'solution', self.selftest)

                if ENABLE_PROFILE:
                    # Profiled version:
                    import cProfile
                    prof_filename = '%s.%s.sm-profile' % (gcc.get_dump_base_name(),
                                                          sm.name)
                    try:
                        cProfile.runctx('run()',
                                        globals(), locals(),
                                        filename=prof_filename)
                    finally:
                        import pstats
                        prof = pstats.Stats(prof_filename)
                        prof.sort_stats('cumulative').print_stats(20)
                else:
                    # Unprofiled version:
                    run()

class Options:
    """
    dump_json: if set to True, then error reports will be written out as
               JSON files with names of the form
                   "INPUTFILENAME.hash.sm.json"
               rather than to stderr, and the presence of such errors will
               not lead to gcc treating the compilation as a failure
    """
    def __init__(self,
                 cache_errors=True,
                 during_lto=False,
                 dump_json=False):
        self.cache_errors = cache_errors
        self.during_lto = during_lto
        self.dump_json = dump_json

def main(checkers, options=None, selftest=None):
    if not options:
        options = Options(cache_errors=True)

    # Run as an interprocedural pass (over SSA gimple), potentially
    # during lto1:
    ps = IpaSmPass(checkers, options, selftest)
    ps.register_before('whole-program')

