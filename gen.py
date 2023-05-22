import genanki
import configparser
import random
import time

def generate_id():
    return str(random.randrange(1 << 30, 1 << 31))

config = configparser.ConfigParser()

config.read('config.ini')

if not config.has_section('model'):
    config.add_section('model')

model_config = config['model']

if not config.has_option('model', 'deck_id'):
    config['model']['deck_id'] = generate_id()

if not config.has_option('model', 'word_model_id'):
    config['model']['word_model_id'] = generate_id()

if not config.has_option('model', 'sentence_model_id'):
    config['model']['sentence_model_id'] = generate_id()

with open('config.ini', 'w') as configfile:
    config.write(configfile)

deck = genanki.Deck(
    model_config.getint('deck_id'),
    'Generated Mandarin Flashcards'
)

word_model = genanki.Model(
    model_config.getint('word_model_id'),
    'Mandarin Word',
    fields=[
        {'name': 'timestamp'},
        {'name': 'Hanzi'},
        {'name': 'Definition'},
        {'name': 'Audio'},
        {'name': 'Reading'},
        {'name': 'Related Words'}
    ],
    templates=[
        {
            'name': 'Listening',
            'qfmt': 'Listen.{{Audio}}',
            'afmt': '''
                {{FrontSide}}
                <hr id=answer>
                {{Hanzi}}<br>{{Reading}}<br>{{Definition}}
                <hr id=answer>
                {{Related Words}}
            '''
        },
        {
            'name': 'Reading',
            'qfmt': '{{Hanzi}}',
            'afmt': '''
                {{FrontSide}}
                <hr id=answer>
                {{Reading}}<br>{{Definition}}<br>{{Audio}}
                <hr id=answer>
                {{Related Words}}
            '''
        }
    ],
    css='''
        .card {
            font-family: arial;
            font-size: 20px;
            text-align: center;
            color: black;
            background-color: white;
        }
    '''
)
deck.add_model(word_model)

sentence_model = genanki.Model(
        model_config.getint('sentence_model_id'),
        'Mandarin Sentence',
        fields=[
            {'name': 'timestamp'},
            {'name': 'Hanzi'},
            {'name': 'Meaning'},
            {'name': 'Audio'},
            {'name': 'Reading'},
        ],
        templates=[
            {
                'name': 'Listening',
                'qfmt': 'Listen.{{Audio}}',
                'afmt': '''
                    {{FrontSide}}
                    <hr id=answer>
                    {{Hanzi}}<br>{{Reading}}<br>{{Meaning}}
                '''
            },
            {
                'name': 'Reading',
                'qfmt': '{{Hanzi}}',
                'afmt': '''
                    {{FrontSide}}
                    <hr id=answer>
                    {{Reading}}<br>{{Meaning}}<br>{{Audio}}
                '''
            }
        ],
        css='''
            .card {
                font-family: arial;
                font-size: 20px;
                text-align: center;
                color: black;
                background-color: white;
            }
        '''
    )
deck.add_model(sentence_model)

test_word_note = genanki.Note(
    model=word_model,
    fields=[
        str(time.time_ns()),
        '可以',
        'possible',
        '[sound:MinecraftOof.mp3]',
        'ㄎㄜˇ ㄧˇ',
        '可能, 以下'
    ]
)
deck.add_note(test_word_note)

test_sentence_note = genanki.Note(
    model=sentence_model,
    fields=[
        str(time.time_ns()),
        '你會講中文嗎?',
        'Do you speak Mandarin?',
        '[sound:MinecraftOof.mp3]',
        'ㄋㄧˇ ㄏㄨㄟˋ ㄐㄧㄤˇ ㄓㄨㄥ ㄨㄣˊ ㄇㄚ˙'
    ]
)
deck.add_note(test_sentence_note)

output_package = genanki.Package(deck)
output_package.media_files = ['MinecraftOof.mp3']
output_package.write_to_file('output.apkg')