#!/usr/bin/env python3

import sys
import os
sys.path.append('.')

from utils.data_loader import DataLoader

def test_data_loader():
    data_root = os.path.join('.', 'data')
    loader = DataLoader(data_root)

    print('=== TESTING DATA LOADER ===')
    print(f'Data root: {data_root}')

    # Test lesson plans loading
    lesson_plans = loader.load_lesson_plans('python', 'functions')
    print(f'Lesson plans loaded: {type(lesson_plans)}')
    print(f'Keys in lesson_plans: {list(lesson_plans.keys()) if lesson_plans else "None"}')

    if lesson_plans and 'lessons' in lesson_plans:
        lessons = lesson_plans['lessons']
        print(f'Number of lessons: {len(lessons)}')
        print(f'Lesson keys: {list(lessons.keys())}')
        
        # Check first lesson
        if lessons:
            first_key = list(lessons.keys())[0]
            first_lesson = lessons[first_key]
            print(f'First lesson key: "{first_key}"')
            print(f'First lesson type: {first_lesson.get("type", "NO_TYPE")}')
            print(f'First lesson title: {first_lesson.get("title", "NO_TITLE")}')
            
            # Check for remedial lessons
            remedial_lessons = [k for k, v in lessons.items() if v.get('type') == 'remedial']
            print(f'Remedial lessons: {remedial_lessons}')
            
            # Check for initial lessons
            initial_lessons = [k for k, v in lessons.items() if v.get('type') == 'initial']
            print(f'Initial lessons: {initial_lessons}')
    else:
        print('ERROR: No lessons found or lessons key missing!')

if __name__ == '__main__':
    test_data_loader()
