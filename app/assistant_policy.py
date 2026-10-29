"""Explicit incident state; untrusted prose never confirms a resolved incident."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import unicodedata

CATALOGUE = Path(__file__).resolve().parents[1] / 'data' / 'assistant_runbooks.json'
QUESTIONS = {
    'network': {
        'link': ('Máy báo mất liên kết hay đã kết nối?', ['disconnected', 'connected', 'unknown']),
        'scope': ('Chỉ một máy hay nhiều máy bị?', ['single', 'multiple', 'unknown']),
        'internal': ('Tài nguyên nội bộ có truy cập được không?', ['works', 'fails', 'unknown']),
    },
    'printer': {
        'connection': ('Máy in nối USB hay qua mạng?', ['usb', 'network', 'unknown']),
        'scope': ('Chỉ máy bạn hay nhiều người không in được?', ['single', 'multiple', 'unknown']),
        'panel': ('Bảng điều khiển máy in có báo lỗi không?', ['error', 'no_error', 'unknown']),
    },
}


def fold(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower().replace('đ', 'd')) if unicodedata.category(c) != 'Mn')


def topic(text):
    text = fold(text)
    if any(x in text for x in ('bi chay', 'chay no', 'boc khoi', 'khet', 'dien giat', 'tia lua')):
        return 'hazard'
    if any(x in text for x in ('ma doc', 'ransomware', 'virus', 'lo mat khau', 'tan cong')):
        return 'security'
    if any(x in text for x in ('may photo', 'may in', 'may photocopy', 'photocopier', 'printer', 'print-')):
        return 'printer'
    if any(x in text for x in ('mang lan', 'rj45', 'mang day', 'day mang', 'cap mang', 'cap lan', 'cable', 'internet', 'ethernet', 'net-')):
        return 'network'
    if any(x in text for x in ('outlook', 'vpn', 'email', 'mfa', 'tai khoan', 'windows', 'wifi', 'wi-fi', 'ma doc', 'ransomware', 'virus', 'lo mat khau', 'tan cong', 'may tinh cham')):
        return 'other_it'
    return None


def approved_steps(incident, facts, role):
    """Only a server-controlled approved, versioned catalogue may supply steps."""
    try:
        entries = json.loads(CATALOGUE.read_text(encoding='utf-8'))['runbooks']
    except (OSError, ValueError, KeyError, TypeError):
        return [], []
    if not isinstance(entries, list):
        return [], []
    for entry in entries:
        if not isinstance(entry, dict) or entry.get('topic') != incident:
            continue
        required = ('id', 'version', 'reviewer', 'reviewed_at', 'source', 'source_version', 'section')
        if entry.get('status') != 'approved' or not all(isinstance(entry.get(k), str) and entry[k].strip() for k in required):
            continue
        conditions = entry.get('conditions')
        if not isinstance(conditions, dict) or set(conditions) != set(QUESTIONS[incident]):
            continue
        if not all(facts.get(k, {}).get('value') == v for k, v in conditions.items()):
            continue
        steps = entry.get('steps')
        if not isinstance(steps, list) or not 1 <= len(steps) <= 3:
            continue
        if not all(isinstance(s, dict) and isinstance(s.get('roles'), list) and role in s['roles']
                   and all(isinstance(s.get(k), str) and s[k].strip() for k in ('id', 'instruction', 'expected', 'stop')) for s in steps):
            continue
        source = {k: entry[k] for k in required}
        return deepcopy(steps), [source]
    return [], []


def handoff(context):
    facts = context['facts']
    lines = [context['initial_question'], 'Tác động/độ khẩn cấp: chưa xác minh.']
    lines += [f"Dữ kiện {k}: {v['value']} (người dùng, {v['at']})" for k, v in facts.items()]
    unknowns = [k for k in QUESTIONS.get(context['topic'], {}) if facts.get(k, {}).get('value', 'unknown') == 'unknown']
    lines.append('Chưa xác minh: ' + ', '.join(unknowns or ['không có dữ kiện bắt buộc còn thiếu']))
    lines.append('Bước được gợi ý (không tự coi đã thực hiện): ' + ', '.join(s['id'] for s in context.get('steps', [])))
    lines += [f"Kết quả bước {key}: {value} (người dùng xác nhận)" for key, value in context.get('step_results', {}).items()]
    lines.append('Kết quả chức năng người dùng xác nhận: ' + context.get('outcome', 'chưa xác nhận'))
    lines += [f"Nguồn: {s['source']} · phiên bản nguồn {s['source_version']} · runbook {s['version']} · mục {s['section']}" for s in context.get('sources', [])]
    lines.append('Lý do bàn giao: cần IT xác minh; ưu tiên tạm thời, cần xác nhận tác động.')
    # Keep user reports separate from confirmed diagnostic facts. The full
    # notes remain in incident context even when the ticket preview is bounded.
    if context.get('notes'):
        heading = 'Thông tin bổ sung do người dùng cung cấp, chưa xác minh:\n'
        notes = '\n'.join(f"{note['at']}: {note['text']}" for note in context['notes'])
        budget = max(0, 5000 - len('\n'.join(lines)) - len(heading) - 1)
        if len(notes) > budget:
            marker = '[Rút gọn; xem đầy đủ trong hội thoại.]\n'
            notes = marker[:budget] if budget <= len(marker) else marker + notes[-(budget - len(marker)):]
        lines.append(heading + notes)
    return {'title': context['initial_question'].replace('\n', ' ')[:160], 'description': '\n'.join(lines)[:5000], 'unknowns': unknowns}


def diagnose(question, context=None, *, action=None, answers=None, step_results=None, role='user'):
    context = deepcopy(context) if context else None
    current = topic(question)
    if context and action == 'confirm_switch':
        if not context.get('pending'):
            raise ValueError('Không có sự cố mới chờ xác nhận.')
        question = context['pending']['question']
        current = context['pending']['topic']
        context = None
    if not context and (not current or (current == "other_it" and action != "confirm_switch")):
        return None
    if context is None:
        context = {'topic': current, 'initial_question': question, 'facts': {}, 'state': 'CLARIFY', 'steps': [], 'sources': []}
    elif context.get('pending', {}).get('topic') in ('security', 'hazard'):
        return _result(context, 'CLARIFY', 'Dừng thao tác tự xử lý. Cần xác nhận sự cố nguy hiểm/bảo mật để bàn giao IT.', pending_topic=context['pending']['topic'])
    elif current and current != context['topic']:
        previous_state = context.get('pending', {}).get('previous_state', context['state'])
        context['pending'] = {'topic': current, 'question': question, 'previous_state': previous_state}
        return _result(context, 'CLARIFY', 'Dừng thao tác tự xử lý. Xác nhận sự cố nguy hiểm/bảo mật để bàn giao IT.' if current in ('security', 'hazard') else 'Bạn đang chuyển sang sự cố khác. Xác nhận bắt đầu sự cố mới hoặc tiếp tục sự cố hiện tại.', pending_topic=current)
    elif context.get('pending') and action != 'continue_incident':
        # Do not accept facts/outcomes while the incident boundary is unresolved.
        return _result(context, 'CLARIFY', 'Hãy xác nhận đổi sự cố hoặc tiếp tục sự cố hiện tại.', pending_topic=context['pending']['topic'])
    if action == 'continue_incident':
        pending = context.pop('pending', None)
        if pending:
            context['state'] = pending.get('previous_state', 'CLARIFY')
    if not action and not answers and not step_results and question != context['initial_question']:
        context.setdefault('notes', []).append({
            'text': question, 'source': 'user', 'at': datetime.now(timezone.utc).isoformat(),
        })
    if context['topic'] in ('security', 'hazard'):
        return _result(context, 'HANDOFF_PREVIEW', 'Dừng thao tác tự xử lý. Có dấu hiệu nguy hiểm hoặc sự cố bảo mật cần IT xác minh ngay; xem thông tin bàn giao.')
    if step_results:
        valid_ids = {s['id'] for s in context['steps']}
        if context['state'] != 'CHECK_RESULT' or any(k not in valid_ids or v not in ('not_attempted', 'attempted_success', 'attempted_failure') for k, v in step_results.items()):
            raise ValueError('Kết quả bước không hợp lệ hoặc không thuộc sự cố hiện tại.')
        context['step_results'] = step_results
    if action in ('confirm_resolved', 'still_failing'):
        if context['state'] != 'CHECK_RESULT':
            raise ValueError('Chưa có bước kiểm tra kết quả để xác nhận.')
        context['outcome'] = 'đã hoạt động trở lại' if action == 'confirm_resolved' else 'vẫn lỗi hoặc chưa thực hiện được'
        return _result(context, 'RESOLVED' if action == 'confirm_resolved' else 'HANDOFF_PREVIEW',
                       'Bạn đã xác nhận chức năng hoạt động trở lại.' if action == 'confirm_resolved' else 'Cần IT kiểm tra tiếp; xem lại thông tin trước khi gửi.')
    incident = context['topic']
    if answers and incident in QUESTIONS:
        for key, value in answers.items():
            if key not in QUESTIONS[incident] or value not in QUESTIONS[incident][key][1]:
                raise ValueError('Dữ kiện không thuộc câu hỏi hoặc giá trị được hỗ trợ.')
            context['facts'][key] = {'value': value, 'source': 'user', 'at': datetime.now(timezone.utc).isoformat()}
    if context['state'] in ('HANDOFF_PREVIEW', 'RESOLVED'):
        return _result(context, context['state'],
                       'Thông tin bàn giao đã được giữ lại; bạn có thể bổ sung và xem lại trước khi gửi IT.'
                       if context['state'] == 'HANDOFF_PREVIEW' else
                       'Sự cố đã được xác nhận hoạt động trở lại. Hãy mở phiên mới nếu cần xử lý sự cố khác.')
    if incident == 'other_it':
        return _result(context, 'IN_SCOPE_NO_SOURCE', 'Sự cố CNTT này chưa có quy trình chẩn đoán trong phạm vi hiện tại. Có thể đề nghị IT hỗ trợ.')
    if re.fullmatch(r'(toi )?(khong biet|khong kiem tra duoc)( loai ket noi)?[.! ]*', fold(question)):
        return _result(context, 'HANDOFF_PREVIEW', 'Bạn chưa thể cung cấp dữ kiện cần thiết. Có thể gửi IT với phần chưa biết được đánh dấu rõ.')
    if context['state'] == 'CHECK_RESULT' and not answers:
        return _result(context, 'CHECK_RESULT', 'Chức năng đã hoạt động trở lại chưa? Hãy xác nhận kết quả hiện tại; câu mô tả hoặc đánh giá hữu ích chưa được coi là hết lỗi.')
    missing = [k for k in QUESTIONS[incident] if k not in context['facts']]
    if missing:
        questions = [{'key': k, 'text': QUESTIONS[incident][k][0], 'options': QUESTIONS[incident][k][1]} for k in missing]
        return _result(context, 'CLARIFY', 'Chưa đủ dữ kiện để chọn hướng xử lý. Chọn dữ kiện quan sát được hoặc Không biết.', questions=questions)
    facts = context['facts']
    if any(v['value'] in ('unknown', 'multiple') for v in facts.values()) or facts.get('panel', {}).get('value') == 'error':
        return _result(context, 'HANDOFF_PREVIEW', 'Cần IT kiểm tra tiếp; không tự can thiệp hạ tầng hoặc thiết bị lỗi.')
    steps, sources = approved_steps(incident, facts, role)
    if not steps:
        return _result(context, 'HANDOFF_PREVIEW', 'Chưa có bước thao tác được phê duyệt phù hợp dữ kiện và quyền của bạn. Đề nghị IT xác minh.')
    context.update(steps=steps, sources=sources)
    answer = '\n'.join(f"{i+1}. {s['instruction']}\nQuan sát: {s['expected']}\nDừng khi: {s['stop']}" for i, s in enumerate(steps))
    return _result(context, 'CHECK_RESULT', answer, guide_state='GUIDE')


def _result(context, state, answer, **extra):
    context['state'] = state
    pending = context.get('pending')
    questions = [{'key': k, 'text': v[0], 'options': v[1]} for k, v in QUESTIONS.get(context['topic'], {}).items()
                 if k not in context['facts']] if state == 'CLARIFY' and not pending else []
    attempted = [{'id': k, 'result': v} for k, v in context.get('step_results', {}).items() if v != 'not_attempted']
    suggested = [s['id'] for s in context['steps'] if context.get('step_results', {}).get(s['id'], 'not_attempted') == 'not_attempted']
    safety_pending = pending and pending['topic'] in ('security', 'hazard')
    return {'safety_stop': bool(safety_pending or context['topic'] in ('security', 'hazard')), 'questions': questions, 'pending_topic': pending['topic'] if pending else None,
            'unknowns': handoff(context)['unknowns'], 'attempted_steps': attempted, 'suggested_only_steps': suggested,
            'rationale': answer, 'next_action': state, 'state': state, 'answer': answer, 'incident_topic': context['topic'], 'facts': context['facts'],
            'steps': [] if safety_pending else context['steps'], 'policy_sources': context['sources'], 'handoff': handoff(context),
            'context': context, **extra}


def snapshot(context):
    context = deepcopy(context)
    result = _result(context, context['state'], 'Tiếp tục sự cố từ dữ kiện đã lưu.')
    result.pop('context')
    result['revision'] = context.get('revision', 0)
    result['grounded'] = False
    result['triage'] = {'category': {'printer': 'hardware', 'network': 'network'}.get(context['topic'], 'general'),
                        'priority': 'medium', 'resolution_scope': 'ESCALATE_IT' if context['state'] in ('HANDOFF_PREVIEW', 'IN_SCOPE_NO_SOURCE') else context['state']}
    return result
