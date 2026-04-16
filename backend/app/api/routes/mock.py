from fastapi import APIRouter

router = APIRouter(tags=['mock'])


@router.get('/context')
def get_context():
    return {
        'artifact': '琴名「襄」',
        'mode': 'single',
        'evidence_pages': [12, 13, 14],
        'current_task': '判断候选层级是否合理',
    }


@router.get('/candidates')
def get_candidates():
    return {
        'items': [
            {
                'candidate_id': 'c_001',
                'label': '断纹',
                'value': '流水加牛毛断',
                'type': '属性',
                'layer': '特有层',
                'status': '待确认',
            },
            {
                'candidate_id': 'c_002',
                'label': '馆藏',
                'value': '故宫博物院',
                'type': '关系',
                'layer': '扩展层',
                'status': '推荐新增',
            },
        ]
    }
