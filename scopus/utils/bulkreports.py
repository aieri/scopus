from datetime import datetime
import os.path
import json
from scopus.utils import (config, download)

URL = 'https://api.elsevier.com/content/abstract/citations/'
API = 'CitationOverview'
CACHE_DIR = config.get('Directories', API)


def bulkreports(eids, start, end=datetime.now().year, refresh=False):
    '''
    Utility function to pre-seed the cache with citation reports
    A single scopus query will be run, but the response will be split per eid

    NOTE: the hindex of the individual eids cannot be retrieved from the
    aggregated query. Cached files will contain the global hindex of the entire
    query.

    Parameters
    ----------
    eids : list of strings
        The list of EIDs of the abstracts to fetch citation reports for

    start : str or int
        The first year for which the citation count should be loaded

    end : str or int (optional, default=datetime.now().year)
        The last year for which the citation count should be loaded.
        Default is the current year.

    Notes
    -----
    The files are cached in ~/.scopus/citation_overview/{eid}

    Your API Key needs to be approved by Elsevier to access this view.

    Almost equivalent to:
    for eid in eids:
        CitationOverview(eid, start=start, end=end)
    '''

    date = '{}-{}'.format(start, end)

    if refresh:
        scopus_ids = [eid.split('0-')[-1] for eid in eids]
    else:
        scopus_ids = []
        for eid in eids:
            qfile = os.path.join(CACHE_DIR, eid)
            if not os.path.exists(qfile):
                scopus_ids.append(eid.split('0-')[-1])

    params = {'date': date, 'scopus_id': scopus_ids}

    # Run a single scopus bulk query
    content = json.loads(download(url=URL, params=params, accept='json').text)

    data = content['abstract-citations-response']
    cite_infos = data['citeInfoMatrix']['citeInfoMatrixXML']['citationMatrix']['citeInfo']
    identifiers = data['identifier-legend']['identifier']

    # Split the bulk reply into individual citation reports
    for cite_info, identifier in zip(cite_infos, identifiers):
        _content = content.copy()
        _data = _content['abstract-citations-response']
        _data['citeInfoMatrix']['citeInfoMatrixXML']['citationMatrix']['citeInfo'] = [cite_info]
        _data['identifier-legend']['identifier'] = [identifier]
        totals = _data['citeColumnTotalXML']['citeCountHeader']
        totals['columnTotal'] = cite_info['cc']
        totals['laterColumnTotal'] = cite_info['lcc']
        totals['rangeColumnTotal'] = cite_info['rangeCount']
        totals['grandTotal'] = cite_info['rowTotal']
        qfile = os.path.join(CACHE_DIR,
                             '2-s2.0-{}'.format(identifier['scopus_id']))

        # Cache the split result for future fast instantiations of the
        # CitationOverview class
        with open(qfile, 'wb') as f:
            f.write(json.dumps(_content).encode('utf-8'))
