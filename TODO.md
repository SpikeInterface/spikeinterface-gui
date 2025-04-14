# TODO

### Sam
- [ ] remove compute
- [x] QT settings not more dialog
- [ ] remove custom docker
- [x] simple layout description
- [ ] generic toolbar : handle segments + settings + help
- [ ] handle segment change
- [ ] unit list with depth
- [ ] no trace on waveform view when non rec

debug dock/widget is_visible()
speedup similarity view
speedup amplitude view



### Alessio
- [x] handle similarity default compute
- [x] spike list + spike selection
- [x] curation view
- [x] add settings / more columns to panel unit list
- [x] unitlist: fix merge and delete with sorters
- [ ] implement default color toggle button




### Panel Views
- [ ] general
  - [x] fix settings cards
  - [ ] global settings (e.g. color options, layout)
- [x] unit list
    - [x] more columns to panel unit list
    - [x] add settings to select colums
    - [x] add sparsity and channel id
    - [x] visible only when clicking on select column
    - [x] make x-axis scrollable
- [ ] probe
  - [x] fix pan to move circles
  - [ ] add option to resize circles
- [ ] spike list
  - [x] add unit color 
  - [x] fix segment index
  - [x] fix spike selection
- [x] curation
- [x] merge
- [x] waveform
  - [x] zoom on wheel 
  - [x] flatten mode
- [x] trace
  - [x] fix multi-segment selection 
  - [x] zoom on wheel 
  - [x] fix spike at init
- [ ] spike amplitudes
  - [x] add selection
  - [ ] add option to scatter decimate
- [ ] NDscatter
  - [x] fix limits
  - [ ] add selection

### Discussion
* panel.param or Pydantic?
* plotly / bokeh?
