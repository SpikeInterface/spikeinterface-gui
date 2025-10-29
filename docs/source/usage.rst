Main usage
==========

The main idea is to make visible one or several units and visually inspect if they should be merged or removed.
For this visibility:

* ctrl + double click on a unit in *probeview*
* check the box visible in the *unitlist* 
* double click on one unit in *unitlist* unit visible alone
* move one of the roi in the *probeview*

Views can be reorganized by moving docks by clicking in the title bar of a docks.
Any dock (view) can be closed. And can be put back with right click in any title bar of any dock.

Every view has a **?** button which opens the contextual help. **These inplace docs are the most important stuff to be read**. (but they contain typos)

When some units are visible, the related spike list can be refresh.
Then selecting spike per spike can also refresh some views.
This enables a very quick and convenient spike per spike jump on traces.

Channel visibility can be handled with one of the roi in the probeview.

Shortcuts: many shortcuts are available, please read the **?** button in each view.

Curation mode
-------------

By default this tool is a viewer only. But you can turn it into a tool for manual curation using
the ``curation=True`` option.
This tool supports the `curation format from spikeinterface <https://spikeinterface.readthedocs.io/en/latest/modules/curation.html#manual-curation>`_.
This format enables to:

1. remove units
2. merge units
3. split units
4. create manual labels

When this mode is activated a new view is added on top left to maintain the list of removal and merges.
The curation format can be exported to json.