"""Localized names for the authored campaign; story IDs remain language-neutral."""

STORY_TITLES_EN = {
    'story1': 'Awakening of MAAT AI',
    'story2': 'Quest 2 – Calculate the Maat values',
    'story3': 'Quest 3 – The call to battle',
    'story4_boss1': 'Interlude – The first boss falls',
    'story5_boss3': 'Interlude – The flame grows heavy',
    'story6_final1': 'Interlude – A principle returns',
}


def story_entry(entry, language):
    result = dict(entry)
    if language == 'en':
        result['name'] = STORY_TITLES_EN.get(result.get('module'), result.get('name', 'Story'))
    return result
