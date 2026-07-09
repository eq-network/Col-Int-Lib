"""cilib.lab — research payload: no stability promise.

You're one import away from the code behind specific papers, not the library.
Everything here is real (it runs, it's tested) but it moves at the pace of a
thesis chapter: names, APIs, and even results can change between commits
without a changelog entry.

    cilib.lab.paradigms   composed research models (active_inference, polycentric)
    cilib.lab.analysis    offline research math (effective information, causal emergence)

Nothing in the engine (``cilib.core``) or the catalogs imports from here —
the dependency arrow points one way, inward.

Landed here by accident while building a simulation? You probably want
``cilib.mechanisms`` / ``cilib.transformations`` / ``cilib.agents`` /
``cilib.environments`` instead — see EXTENDING.md. Those are the maintained
catalogs.

Here on purpose — reading the research, extending a paradigm, reproducing a
result from ``experiments/``? Carry on, but read the paradigm's own README
first (``lab/paradigms/<name>/README.md``); its internals are paper-specific,
not general contracts.

Import the submodule you need directly, e.g.::

    from cilib.lab import paradigms          # namespace only
    from cilib.lab.paradigms import polycentric as P
    from cilib.lab.analysis import causal_emergence as ce
"""
