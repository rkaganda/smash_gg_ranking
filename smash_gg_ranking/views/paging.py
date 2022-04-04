from typing import Dict


def get_paging_info(sets, page_params: Dict):
    # paging
    participant_sets_count = sets.count()
    paging_info = {
        "page_num": page_params['page_num'],
        "max_page": (participant_sets_count // page_params['page_size']) + 1,  # math is hard?
        "page_size": page_params['page_size']
    }
    offset = (page_params['page_num'] - 1) * page_params['page_size']
    paging_info['offset'] = offset
    participant_sets = sets.offset(offset).limit(page_params['page_size'])

    return participant_sets, paging_info
