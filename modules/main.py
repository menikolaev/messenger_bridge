import datetime
import json
import time

import requests


def module(messages):
    def inner(func):
        def sub_inner(*args, **kwargs):
            if kwargs['message'].lower() in messages:
                return func(*args, **kwargs)

        return sub_inner

    return inner


group_map = {
    6767: 'УРПО',
    6768: 'Мобилки'
}


def get_group(message):
    if message == 'где пары?':
        return [6767, 6768]
    elif message == 'где пары урпо?':
        return [6767]
    elif message in ['где пары мобилки?', 'где пары прмп?']:
        return [6768]


@module(['где пары?', 'где пары урпо?', 'где пары мобилки?', 'где пары прмп?'])
def where_lessons(message):
    now = datetime.datetime.now()
    template = '{track} {start_time}-{end_time} {name} {lecturer} ({auditorium}) {kind}'
    url = 'https://www.hse.ru/api/timetable/lessons?fromdate={date}&todate={date}&groupoid={group}&receiverType=3'
    groups = get_group(message.lower())
    end_text = []
    for group in groups:
        result = None
        for i in range(1, 4):
            try:
                result = requests.get(url.format(**{'date': now.date().strftime('%Y.%m.%d'), 'group': group}))
                break
            except Exception as e:
                time.sleep(i * 0.8)
                print(e)

        if result is None:
            return {
                'user_name': 'System',
                'text': 'Информация не может быть получена'
            }

        lessons = json.loads(result.text)['Lessons']

        all_text = []
        for lesson in lessons:
            text = template.format(
                **{'track': group_map[group], 'start_time': lesson['beginLesson'], 'end_time': lesson['endLesson'],
                   'name': lesson['discipline'], 'lecturer': lesson['lecturer'], 'auditorium': lesson['auditorium'],
                   'kind': lesson['kindOfWork']}
            )
            all_text.append(text)

        if not lessons:
            all_text.append(group_map[group] + ': Ничего')

        end_text.append('\n'.join(all_text))
    return {
        'user_name': 'System',
        'text': '\n\n'.join(end_text)
    }


if __name__ == '__main__':
    print(where_lessons(message='где пары?'))
