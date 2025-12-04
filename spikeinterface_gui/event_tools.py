import numpy as np

from spikeinterface.core import BaseEvent

def parse_events(events, controller, verbose=False):
    """Parse events input into a standard format.

    Parameters
    ----------
    events : dict | BaseEvent
        BaseEvent object or a dictionary where keys are event names and values are dictionaries with at least a 
        'samples' key or 'times' key.
    controller : Controller
        Controller object managing the event parsing.
    verbose : bool, default: False
        Whether to print verbose messages.

    Returns
    -------
    parsed_events : dict
        Parsed events dictionary. The keys are event names, and the values are lists of numpy arrays of event sample indices.
        Each element corresponds to a segment in the recording.
    """
    parsed_events = {}
    if isinstance(events, dict):
        for key, val in events.items():
            if not isinstance(val, dict):
                if verbose:
                    print(f'\tSkipping event {key}: not a dict')
                continue
            if 'samples' not in val and 'times' not in val:
                if verbose:
                    print(f'\tSkipping event {key}: missing samples or times')
                continue
            if 'times' in val:
                samples_data = val['times']
                convert_to_samples = True
            else:
                samples_data = val['samples']
                convert_to_samples = False
            if controller.num_segments > 1:
                if not len(samples_data) == controller.num_segments:
                    if verbose:
                        print(f'\tSkipping event {key}: inconsistent number of samples')
                    continue
            else:
                # here we make sure samples is a list of list
                if np.array(samples_data).ndim == 1:
                    samples_data = [samples_data]
            if convert_to_samples:
                parsed_events[key] = [np.array(controller.time_to_sample_index(s)) for s in samples_data]
            else:
                parsed_events[key] = [np.array(s) for s in samples_data]
    elif isinstance(events, BaseEvent):
        event_names = events.channel_ids
        parsed_events = {
            event_name: [] for event_name in event_names
        }
        for event_name in event_names:
            for segment_index in range(controller.num_segments):
                event_times_segment = events.get_event_times(
                    channel_id=event_name,
                    segment_index=segment_index
                )
                event_samples_segment = controller.time_to_sample_index(
                    event_times_segment
                )
                parsed_events[event_name].append(np.array(event_samples_segment))
    else:
        if verbose:
            print('\tSkipping events: not a dict or BaseEvent')
    
    return parsed_events