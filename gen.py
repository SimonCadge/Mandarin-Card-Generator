import genanki
import configparser
import random
import time
from chinese import ChineseAnalyzer
from dragonmapper import transcriptions
import csv
from azure.core.exceptions import HttpResponseError
from azure.ai.translation.text import TextTranslationClient, TranslatorCredential
from azure.ai.translation.text.models import InputTextItem
import azure.cognitiveservices.speech as speechsdk
import pathlib
import unicodedata
import re
import os
import shutil

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

if not config.has_section('azure'):
    config.add_section('azure')

azure_config = config['azure']

if not config.has_option('azure', 'translator_api_key'):
    print('Missing Microsoft Azure Translator Config. See here: https://learn.microsoft.com/en-us/azure/cognitive-services/translator/text-sdk-overview?tabs=python')
    config['azure']['translator_api_key'] = input('Translator API Key: ')

if not config.has_option('azure', 'translator_api_endpoint'):
    print('Missing Microsoft Azure Translator Config. See here: https://learn.microsoft.com/en-us/azure/cognitive-services/translator/text-sdk-overview?tabs=python')
    config['azure']['translator_api_endpoint'] = input('Translator API Endpoint: ')

if not config.has_option('azure', 'speech_api_key'):
    print('Missing Microsoft Azure Speech Config. See here: https://learn.microsoft.com/en-GB/azure/cognitive-services/speech-service/get-started-text-to-speech?tabs=windows%2Cterminal&pivots=programming-language-python')
    config['azure']['speech_api_key'] = input('Speech API Key: ')

if not config.has_option('azure', 'speech_api_endpoint'):
    print('Missing Microsoft Azure Speech Config. See here: https://learn.microsoft.com/en-GB/azure/cognitive-services/speech-service/get-started-text-to-speech?tabs=windows%2Cterminal&pivots=programming-language-python')
    config['azure']['speech_api_endpoint'] = input('Speech API Endpoint: ')

if not config.has_option('azure', 'region'):
    print('Missing Microsoft Azure Config. See here: https://learn.microsoft.com/en-us/azure/cognitive-services/translator/text-sdk-overview?tabs=python')
    config['azure']['region'] = input('Azure Region: ')

if not config.has_option('azure', 'speech_api_voice_name'):
    config['azure']['speech_api_voice_name'] = 'zh-TW-YunJheNeural'

if not config.has_section('mandarin'):
    config.add_section('mandarin')

mandarin_config = config['mandarin']

if not config.has_option('mandarin', 'is_trad'):
    config['mandarin']['is_trad'] = 'false'

if not config.has_option('mandarin', 'reading_format'):
    config['mandarin']['reading_format'] = 'pinyin'

with open('config.ini', 'w') as configfile:
    config.write(configfile)

translator_credential = TranslatorCredential(azure_config.get('translator_api_key'), azure_config.get('region'))
text_translator = TextTranslationClient(endpoint=azure_config.get('translator_api_endpoint'), credential=translator_credential)

speech_config = speechsdk.SpeechConfig(subscription=azure_config.get('speech_api_key'), region=azure_config.get('region'))
speech_config.speech_synthesis_voice_name = azure_config.get('speech_api_voice_name')

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
        {'name': 'Reading'}
    ],
    templates=[
        {
            'name': 'Listening',
            'qfmt': 'Listen.{{Audio}}',
            'afmt': '''
                {{FrontSide}}
                <hr id=answer>
                {{Hanzi}}<br>{{Reading}}<br>{{Definition}}
            '''
        },
        {
            'name': 'Reading',
            'qfmt': '{{Hanzi}}',
            'afmt': '''
                {{FrontSide}}
                <hr id=answer>
                {{Reading}}<br>{{Definition}}<br>{{Audio}}
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

is_trad = mandarin_config.getboolean('is_trad')
reading_format = mandarin_config.get('reading_format')

try: #Make tmp directory if not exists
    os.makedirs('tmp')
except OSError as e:
    e
media_files = []

analyser = ChineseAnalyzer()

def build_word(hanzi, definition, audio, reading):
    word_note = genanki.Note(
                    model=word_model,
                    fields=[
                        str(time.time_ns()),
                        hanzi,
                        definition,
                        audio,
                        reading
                    ]
                )
    
    return word_note

def build_sentence(hanzi, definition, audio, reading):
    sentence_note = genanki.Note(
                    model=sentence_model,
                    fields=[
                        str(time.time_ns()),
                        hanzi,
                        definition,
                        audio,
                        reading
                    ]
                )
    
    return sentence_note

def transliterate_hanzi(hanzi):
    language = 'zh-Hant' if is_trad else 'zh-Hans'
    from_script = 'Hant' if is_trad else 'Hans'
    to_script = 'Latn'
    text_to_transliterate = [InputTextItem(text = hanzi)]

    transliteration_response = text_translator.transliterate(content=text_to_transliterate,
                                                                            language=language,
                                                                            from_script=from_script,
                                                                            to_script=to_script)
    transliteration = transliteration_response[0] if transliteration_response else None
    reading = transliteration.text if reading_format == 'pinyin' else transcriptions.pinyin_to_zhuyin(transliteration.text)
    return reading

def translate_hanzi(hanzi):
    from_script = 'Hant' if is_trad else 'Hans'
    from_language = 'zh-Hant' if is_trad else 'zh_Hans'
    target_languages = ['en']
    text_to_translate = [InputTextItem(text = hanzi)]
    translation_response = text_translator.translate(content=text_to_translate,
                                                                   from_parameter=from_language,
                                                                   from_script=from_script,
                                                                   to=target_languages)
    translation = translation_response[0] if translation_response else None

    if translation:
        first_translation = translation.translations[0]
        if first_translation:
            definition = first_translation.text
    return definition

def synthesize_text(text):
    # https://github.com/django/django/blob/master/django/utils/text.py
    normalised_text = unicodedata.normalize('NFKC', text)
    normalised_text = re.sub(r'[^\w\s-]', '', normalised_text.lower())
    normalised_text = re.sub(r'[-\s]+', '-', normalised_text).strip('-_')
    normalised_text += '.wav'

    path = pathlib.Path('tmp', normalised_text)

    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)

    result = speech_synthesizer.speak_text_async(text).get()
    stream = speechsdk.AudioDataStream(result)
    stream.save_to_wav_file(str(path))

    media_files.append(str(path))

    return '[sound:' + normalised_text + ']'

with open('input.csv', encoding='utf-8') as input_file:
    linereader = csv.reader(input_file)
    for row in linereader:
        if len(row) > 0:
            hanzi = row[0]
            analysis = analyser.parse(hanzi, traditional=is_trad)
            if len(analysis.tokens()) == 1: #Single Word
                word_info = analysis[hanzi][0]
                definition = ''
                if len(row) == 2:
                    definition = row[1]
                else:
                    definition = ', '.join(word_info.definitions)
                audio = synthesize_text(hanzi)
                reading = analysis.pinyin() if reading_format == 'pinyin' else transcriptions.pinyin_to_zhuyin(analysis.pinyin())
                word_note = build_word(hanzi, definition, audio, reading)
                deck.add_note(word_note)
            else: #Sentence
                definition = ''
                if len(row) == 2:
                    definition = row[1]
                else:
                    definition = translate_hanzi(hanzi)
                audio = synthesize_text(hanzi)
                reading = transliterate_hanzi(hanzi)
                sentence_note = build_sentence(hanzi, definition, audio, reading)
                deck.add_note(sentence_note)

output_package = genanki.Package(deck)
output_package.media_files = media_files
output_package.write_to_file('output.apkg')

shutil.rmtree('tmp')