import time

import numpy as np

import json

from .base import ControllerBase
from .myqt import QT

from spikeinterface.widgets.utils import get_unit_colors
from spikeinterface import compute_sparsity
from spikeinterface.core import get_template_extremum_channel
import spikeinterface.postprocessing
import spikeinterface.qualitymetrics
from spikeinterface.core.sorting_tools import spike_vector_to_indices
from spikeinterface.curation import get_potential_auto_merge
from spikeinterface.core.core_tools import check_json



from .curation_tools import adding_group, default_label_definitions, empty_curation_data

spike_dtype =[('sample_index', 'int64'), ('unit_index', 'int64'), 
    ('channel_index', 'int64'), ('segment_index', 'int64'),
    ('visible', 'bool'), ('selected', 'bool'), ('rand_selected', 'bool')]



# TODO handle return_scaled


class  SpikeinterfaceController(ControllerBase):
    def __init__(self, analyzer=None,parent=None, verbose=False, save_on_compute=False,
                 curation=False, curation_data=None, label_definitions=None):
        ControllerBase.__init__(self, parent=parent)
        
        self.analyzer = analyzer
        assert self.analyzer.get_extension("random_spikes") is not None
        
        self.return_scaled = True
        self.save_on_compute = save_on_compute

        if verbose:
            t0 = time.perf_counter()
            print('open/compute extensions')

        # sparsity
        if self.analyzer.sparsity is None:
            self.external_sparsity = compute_sparsity(self.analyzer, method="radius",radius_um=90.)
            self.analyzer_sparsity = None
        else:
            self.external_sparsity = None
            self.analyzer_sparsity = self.analyzer.sparsity

        # Mandatory extensions : computation forced
        ext = analyzer.get_extension('noise_levels')
        if ext is None:
            print('Force compute "noise_levels" is needed')
            ext = analyzer.compute_one_extension('noise_levels')
        self.noise_levels = ext.get_data()

        temp_ext = self.analyzer.get_extension("templates")
        if temp_ext is None:
            temp_ext = self.analyzer.compute_one_extension("templates")
        self.nbefore, self.nafter = temp_ext.nbefore, temp_ext.nafter

        self.templates_average = temp_ext.get_templates(operator='average')
        self.templates_std = temp_ext.get_templates(operator='std')

        self.num_channels = self.analyzer.get_num_channels()

        ext = analyzer.get_extension('unit_locations')
        if ext is None:
            print('Force compute "unit_locations" is needed')
            ext = analyzer.compute_one_extension('unit_locations')
        # only 2D
        self.unit_positions = ext.get_data()[:, :2]

        # Non mandatory extensions :  can be None
        wf_ext = self.analyzer.get_extension('waveforms')
        self.waveforms_ext = wf_ext

        self.pc_ext = analyzer.get_extension('principal_components')
        self._pc_projections = None

        qm_ext = analyzer.get_extension('quality_metrics')
        if qm_ext is not None:
            self.metrics = qm_ext.get_data()
        else:
            self.metrics = None

        sa_ext = analyzer.get_extension('spike_amplitudes')
        if sa_ext is not None:
            self.spike_amplitudes = sa_ext.get_data()
        else:
            self.spike_amplitudes = None

        ccg_ext = analyzer.get_extension('correlograms')
        if ccg_ext is not None:
            self.correlograms, self.correlograms_bins = ccg_ext.get_data()
        else:
            self.correlograms, self.correlograms_bins = None, None

        isi_ext = analyzer.get_extension('isi_histograms')
        if isi_ext is not None:
            self.isi_histograms, self.isi_bins = isi_ext.get_data()
        else:
            self.isi_histograms, self.isi_bins = None, None

        self._similarity_by_method = {}
        ts_ext = analyzer.get_extension('template_similarity')
        if ts_ext is not None:
            method = ts_ext.params["method"]
            self._similarity_by_method[method] = ts_ext.get_data()
        else:
            if len(self.unit_ids) <= 64 and len(self.channel_ids) <= 64:
                # precompute similarity when low channel/units count
                method = 'cosine_similarity'
                ts_ext = analyzer.compute_one_extension('template_similarity', method=method)
                self._similarity_by_method[method] = ts_ext.get_data()
        
        self._potential_merges = None


        if verbose:
            t1 = time.perf_counter()
            print('open extensions', t1 - t0)

            t0 = time.perf_counter()

        self._extremum_channel = get_template_extremum_channel(self.analyzer, peak_sign='neg', outputs='index')

        # some direct attribute
        self.num_segments = self.analyzer.get_num_segments()
        self.sampling_frequency = self.analyzer.sampling_frequency


        self.colors = get_unit_colors(self.analyzer.sorting, color_engine='matplotlib', map_name='gist_ncar', 
                                      shuffle=True, seed=42)
        self.qcolors = {}
        for unit_id, color in self.colors.items():
            r, g, b, a = color
            self.qcolors[unit_id] = QT.QColor(int(r*255), int(g*255), int(b*255))

        self.unit_visible_dict = {unit_id:False for unit_id in self.unit_ids}
        self.unit_visible_dict[self.unit_ids[0]] = True
        

        if verbose:
            t0 = time.perf_counter()
            print('Gather all spikes')
        
        # make internal spike vector
        unit_ids = self.analyzer.unit_ids
        num_seg = self.analyzer.get_num_segments()
        self.num_spikes = self.analyzer.sorting.count_num_spikes_per_unit(outputs="dict")

        spike_vector = self.analyzer.sorting.to_spike_vector(concatenated=True, extremum_channel_inds=self._extremum_channel)
        
        random_spikes_indices = self.analyzer.get_extension("random_spikes").get_data()

        self.spikes = np.zeros(spike_vector.size, dtype=spike_dtype)        
        self.spikes['sample_index'] = spike_vector['sample_index']
        self.spikes['unit_index'] = spike_vector['unit_index']
        self.spikes['segment_index'] = spike_vector['segment_index']
        self.spikes['channel_index'] = spike_vector['channel_index']
        self.spikes['rand_selected'][:] = False
        self.spikes['rand_selected'][random_spikes_indices] = True

        self.num_spikes = self.analyzer.sorting.count_num_spikes_per_unit(outputs="dict")
        seg_limits = np.searchsorted(self.spikes["segment_index"], np.arange(num_seg + 1))
        self.segment_slices = {seg_index: slice(seg_limits[seg_index], seg_limits[seg_index + 1]) for seg_index in range(num_seg)}
        
        spike_vector2 = self.analyzer.sorting.to_spike_vector(concatenated=False)
        # this is dict of list because per segment spike_indices[segment_index][unit_id]
        spike_indices = spike_vector_to_indices(spike_vector2, unit_ids)
        # this is flatten
        spike_per_seg = [s.size for s in spike_vector2]
        self._spike_index_by_units = {}
        for unit_id in unit_ids:
            inds = []
            for seg_ind in range(num_seg):
                inds.append(spike_indices[seg_ind][unit_id] + int(np.sum(spike_per_seg[:seg_ind])))
            self._spike_index_by_units[unit_id] = np.concatenate(inds)

        if verbose:
            t1 = time.perf_counter()
            print('Gather all spikes', t1 - t0)
            
            t0 = time.perf_counter()
            print('similarity')

        self.visible_channel_inds = np.arange(self.analyzer.get_num_channels(), dtype='int64')

        self._spike_visible_indices = np.array([], dtype='int64')
        self._spike_selected_indices = np.array([], dtype='int64')
        self.update_visible_spikes()


        if verbose:
            t1 = time.perf_counter()
            print('similarity', t1 - t0)
            
            t0 = time.perf_counter()
            # print('')
        
        self.curation = curation
        # TODO: Reload the dictionary if it already exists
        if self.curation:
            # rules:
            #  * if curation_data alreadye exists in folder then it is reloaded and has precedance
            #  * if not, then use curation_data argument input
            #  * otherwise create an empty one

            if self.analyzer.format == "binary_folder":
                json_file = self.analyzer.folder / "spikeinterface_gui" / "curation_data.json"
                if json_file.exists():
                    with open(json_file, "r") as f:
                        curation_data = json.load(f)
            elif self.analyzer.format == "zarr":
                import zarr
                zarr_root = zarr.open(self.analyzer.folder, mode='r')
                if "spikeinterface_gui" in zarr_root.keys() and "curation_data" in zarr_root["spikeinterface_gui"].attrs.keys():
                    curation_data = zarr_root["spikeinterface_gui"].attrs["curation_data"]

            if curation_data is None:
                self.curation_data = empty_curation_data.copy()
            else:
                self.curation_data = curation_data
            
            if "label_definitions" not in self.curation_data:
                if label_definitions is not None:
                    self.curation_data["label_definitions"] = label_definitions
                else:
                    self.curation_data["label_definitions"] = default_label_definitions.copy()

        
    @property
    def channel_ids(self):
        return self.analyzer.channel_ids

    @property
    def unit_ids(self):
        return self.analyzer.sorting.unit_ids
    
    def get_extremum_channel(self, unit_id):
        chan_ind = self._extremum_channel[unit_id]
        return chan_ind

    def update_visible_spikes(self):
        #~ print('update_visible_spikes')
        #~ t0 = time.perf_counter()
        
        inds = []
        for unit_index, unit_id in enumerate(self.unit_ids):
            if self.unit_visible_dict[unit_id]:
                inds.append(self._spike_index_by_units[unit_id])
        
        if len(inds) > 0:
            inds = np.concatenate(inds)
            inds = np.sort(inds)
        else:
            inds = np.array([], dtype='int64')
        self._spike_visible_indices = inds
        
        self._spike_selected_indices = np.array([], dtype='int64')
        #~ t1 = time.perf_counter()
        #~ print('update_visible_spikes', t1-t0, self.spikes.size)
    
    def get_indices_spike_visible(self):
        return self._spike_visible_indices

    def get_indices_spike_selected(self):
        return self._spike_selected_indices
    
    def set_indices_spike_selected(self, inds):
        #~ self.controller.spikes['selected'][:] = False
        #~ self.controller.spikes['selected'][inds] = True
        self._spike_selected_indices = np.array(inds)

    def get_num_samples(self, segment_index):
        return self.analyzer.get_num_samples(segment_index=segment_index)
    
    def get_traces(self, trace_source='preprocessed', **kargs):
        # assert trace_source in ['preprocessed', 'raw']
        assert trace_source in ['preprocessed']
        
        if trace_source == 'preprocessed':
            rec = self.analyzer.recording
        elif trace_source == 'raw':
            raise NotImplemented
            # TODO get with parent recording the non process recording
            pass
        kargs['return_scaled'] = self.return_scaled
        traces = rec.get_traces(**kargs)
        return traces
    
    def get_contact_location(self):
        location = self.analyzer.get_channel_locations()
        return location
    
    def get_waveform_sweep(self):
        return self.nbefore, self.nafter
        
    def get_waveforms_range(self):
        return np.nanmin(self.templates_average), np.nanmax(self.templates_average)
    
    def get_waveforms(self, unit_id):
        wfs = self.waveforms_ext.get_waveforms_one_unit(unit_id, force_dense=False)
        if self.analyzer.sparsity is None:
            # dense waveforms
            chan_inds = np.arange(self.analyzer.recording.get_num_channels(), dtype='int64')
        else:
            # sparse waveforms
            chan_inds = self.analyzer.sparsity.unit_id_to_channel_indices[unit_id]
        return wfs, chan_inds

    def get_common_sparse_channels(self, unit_ids):
        sparsity_mask = self.get_sparsity_mask()
        unit_indexes = [list(self.unit_ids).index(u) for u in unit_ids]
        chan_inds, = np.nonzero(sparsity_mask[unit_indexes, :].sum(axis=0))
        return chan_inds
    
    def get_intersect_sparse_channels(self, unit_ids):
        sparsity_mask = self.get_sparsity_mask()
        unit_indexes = [list(self.unit_ids).index(u) for u in unit_ids]
        chan_inds, = np.nonzero(sparsity_mask[unit_indexes, :].sum(axis=0) == len(unit_ids))
        return chan_inds
    
    def detect_high_similarity(self, threshold=0.9):
        return
    
    def get_probe(self):
        return self.analyzer.get_probe()
        
    def set_channel_visibility(self, visible_channel_inds):
        self.visible_channel_inds = np.array(visible_channel_inds, copy=True)

    def has_extension(self, extension_name):
        if extension_name == 'recording':
            return self.analyzer.has_recording()
        else:
            return self.analyzer.has_extension(extension_name)

    def handle_metrics(self):
        return self.metrics is not None

    def get_all_pcs(self):

        if self._pc_projections is None:
            self._pc_projections, self._pc_indices = self.pc_ext.get_some_projections(
                channel_ids=self.analyzer.channel_ids,
                unit_ids=self.analyzer.unit_ids
            )

        return self._pc_indices, self._pc_projections
    
    

    def get_sparsity_mask(self):
        if self.external_sparsity is not None:
            return self.external_sparsity.mask
        else:
            return self.analyzer_sparsity.mask

    def get_similarity(self, method='cosine_similarity'):
        similarity = self._similarity_by_method.get(method, None)
        return similarity
    
    def compute_similarity(self, method='cosine_similarity'):
        # have internal cache
        if method in self._similarity_by_method:
            return self._similarity_by_method[method]
        ext = self.analyzer.compute("template_similarity", method=method, save=self.save_on_compute)
        self._similarity_by_method[method] = ext.get_data()
        return self._similarity_by_method[method]


    def compute_unit_positions(self, method, method_kwargs):
        ext = self.analyzer.compute_one_extension('unit_locations', save=self.save_on_compute, method=method, **method_kwargs)
        # 2D only
        self.unit_positions = ext.get_data()[:, :2]

    def get_correlograms(self):
        return self.correlograms, self.correlograms_bins

    def compute_correlograms(self, window_ms, bin_ms):
        ext = self.analyzer.compute("correlograms", save=self.save_on_compute, window_ms=window_ms, bin_ms=bin_ms)
        self.correlograms, self.correlograms_bins = ext.get_data()
        return self.correlograms, self.correlograms_bins
    
    def get_isi_histograms(self):
        return self.isi_histograms, self.isi_bins

    def compute_isi_histograms(self, window_ms, bin_ms):
        ext = self.analyzer.compute("isi_histograms", save=self.save_on_compute, window_ms=window_ms, bin_ms=bin_ms)
        self.isi_histograms, self.isi_bins = ext.get_data()
        return self.isi_histograms, self.isi_bins

    def get_merge_list(self):
        return self._potential_merges

    def compute_auto_merge(self, **params):

        potential_merges, extra = get_potential_auto_merge(
            self.analyzer,

            extra_outputs=True,
            steps=None,
            **params
        )
        return potential_merges, extra
    
    def curation_can_be_saved(self):
        return self.analyzer.format != "memory"

    def construct_final_curation(self):
        d = dict()
        d["unit_ids"] = self.unit_ids.tolist()
        d.update(self.curation_data.copy())
        return d

    def save_curation_in_analyzer(self):
        if self.analyzer.format == "memory":
            pass
        elif self.analyzer.format == "binary_folder":
            folder = self.analyzer.folder / "spikeinterface_gui"
            folder.mkdir(exist_ok=True, parents=True)
            json_file = folder / f"curation_data.json"
            with json_file.open("w") as f:
                json.dump(check_json(self.construct_final_curation()), f, indent=4)
        elif self.analyzer.format == "zarr":
            import zarr
            zarr_root = zarr.open(self.analyzer.folder, mode='r+')
            if "spikeinterface_gui" not in zarr_root.keys():
                sigui_group = zarr_root.create_group("spikeinterface_gui", overwrite=True)
            sigui_group = zarr_root["spikeinterface_gui"]
            sigui_group.attrs["curation_data"] = check_json(self.construct_final_curation())
    


    def make_manual_delete_if_possible(self, removed_unit_ids):
        """
        Check if a unit_ids can be removed.

        If unit are already deleted or in a merge group then the delete operation is skiped.
        """
        all_merged_units = sum(self.curation_data["merge_unit_groups"], [])
        for unit_id in removed_unit_ids:
            if unit_id in self.curation_data["removed_units"]:
                continue
            # TODO: check if unit is already in a merge group
            if unit_id in all_merged_units:
                continue
            self.curation_data["removed_units"].append(unit_id)
    
    def make_manual_restore(self, restire_unit_ids):
        """
        pop unit_ids from the removed_units list which is a restore.
        """
        for unit_id in restire_unit_ids:
            if unit_id in self.curation_data["removed_units"]:
                self.curation_data["removed_units"].remove(unit_id)

    def make_manual_merge_if_possible(self, merge_unit_ids):
        """
        Check if the a list of unit_ids can be added as a new merge to the curation_data.

        If some unit_ids are already in the removed list then the merge is skiped.

        If unit_ids are already is some other merge then the connectivity graph is resolved groups can be
        eventually merged.

        """
        if len(merge_unit_ids) < 2:
            return

        for unit_id in merge_unit_ids:
            if unit_id in self.curation_data["removed_units"]:
                return

        merged_groups = adding_group(self.curation_data["merge_unit_groups"], merge_unit_ids)
        self.curation_data["merge_unit_groups"] = merged_groups
    
    def make_manual_restore_merge(self, merge_group_index):
        del self.curation_data["merge_unit_groups"][merge_group_index]

    def get_curation_label_definitions(self):
        # give only label definition with exclusive
        label_definitions = {}
        for k, lbl_def in self.curation_data["label_definitions"].items():
            if lbl_def['exclusive']:
                label_definitions[k] = lbl_def.copy()
        return label_definitions

    def find_unit_in_manual_labels(self, unit_id):
        for ix, lbl in enumerate(self.curation_data["manual_labels"]):
            if lbl["unit_id"] == unit_id:
                    return ix

    def get_unit_label(self, unit_id, category):
        ix = self.find_unit_in_manual_labels(unit_id)
        if ix is None:
            return
        lbl = self.curation_data["manual_labels"][ix]
        if category in lbl:
            labels = lbl[category]
            return labels[0]

    def set_label_to_unit(self, unit_id, category, label):
        if label is None:
            self.remove_category_from_unit(unit_id, category)
            return

        ix = self.find_unit_in_manual_labels(unit_id)
        if ix is not None:
            lbl = self.curation_data["manual_labels"][ix]
            if category in lbl:
                lbl[category] = [label]
            else:
                lbl[category] = [label]
        else:
            lbl = {"unit_id": unit_id, category:[label]}
            self.curation_data["manual_labels"].append(lbl)

    def remove_category_from_unit(self, unit_id, category):
        ix = self.find_unit_in_manual_labels(unit_id)
        if ix is None:
            return
        lbl = self.curation_data["manual_labels"][ix]
        if category in lbl:
            lbl.pop(category)
            if len(lbl) == 1:
                # only unit_id in keys then no more labels, then remove then entry
                self.curation_data["manual_labels"].pop(ix)

