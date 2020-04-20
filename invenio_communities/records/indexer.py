
from invenio_communities.records.api import RecordCommunitiesCollection


def indexer_receiver(sender, json=None, record=None,
                     index=None, **dummy_kwargs):
    """Connect to before_record_index signal to transform record for ES."""
    if not index.startswith('records-') or record.get('$schema') is None:
        return

    # Remove files from index if record is not open access.
    if json['access_right'] != 'open' and '_files' in json:
        del json['_files']

    json['communities'] = RecordCommunitiesCollection(record).as_dict()
